# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

SF6 Viewer — 指定ユーザーの過去1週間の勝率を表示するアプリケーション。対戦データはカプコンの BUCKLER'S BOOT CAMP (https://www.streetfighter.com/6/buckler/) をスクレイピングして取得する。**公式 API ではない**ため、サーバーに負荷をかけない・行儀よくリクエストすることが最重要の運用制約（README 曰く「カプコンに怒られたらすぐに公開停止します」）。

- フロントエンド: React (Create React App / react-scripts)。Azure Static Web Apps 上で動作。GitHub Actions で main への push 時に自動ビルド・自動デプロイ。
- バックエンド: AWS (Lambda[Python] + DynamoDB + API Gateway + EventBridge)。ソースは `lambda/` 以下。**デプロイは手動**。
- AWS リソースは IaC 管理していない。一覧は `doc/aws-resources.md`（リソースを追加・変更したら必ず更新すること）。

## コマンド

```bash
# フロントエンド
npm start                  # 開発サーバー
npm run build              # ビルド
npm test                   # テスト (watch モード)
npm test -- <pattern>      # 単一テスト

# Lambda のデプロイ（関数ごとに手動、aws CLI 必要）
lambda/functions/<関数名>/deploy.sh
# 実体は lambda/scripts/deploy_lambda.sh。関数ディレクトリの *.py だけを zip して
# update-function-code する。ライブラリ依存 (requests, bs4 等) は Lambda レイヤー側
# (lambda/layers/) にあり、deploy.sh では更新されない。

# Python の構文チェック（Python 用のテスト・リンタは無い）
python3 -m py_compile lambda/functions/<関数名>/lambda_function.py

# ユーザーをバッチ更新対象から除外/復帰（--list で一覧）
lambda/scripts/set-user-disabled.sh <UserCode> on|off

# buckler_id の更新（失効時。ブラウザで手動ログインして環境変数を更新）
# 手順は下記「buckler_id の更新」を参照。スクリプトは使わない。
```

- Python は 2 スペースインデント。
- CI (GitHub Actions) では React のデフォルト警告でビルドが落ちるため警告を無視する設定になっている。

## アーキテクチャ

### データフロー

```
EventBridge (3時間毎)
  → updateWrapper: Buckler トップページから buildId をスクレイピング
      → 変わっていれば updateBattleLog の環境変数 BUILD_ID を更新（反映完了を待つ）
      → buckler_id の有効性を1回だけ確認（check_buckler_id）
        → 失効していれば SNS 1通だけ送ってバッチ全体を中止（invoke しない）
      → User テーブルの各ユーザーについて updateBattleLog を非同期 invoke
        (INVOKE_INTERVAL 秒間隔・USER_LIMIT 件まで)
  → updateBattleLog: battlelog.json を最大10ページ取得 → BattleLog テーブルに書き込み
      → 新着があれば play.json も取得して User テーブルを更新

フロントエンド → API Gateway → retrieveBattleLog: DB から対戦履歴を返す。
  未登録ユーザーまたは FETCH_NOW=true の場合は updateBattleLog を同期 invoke してから返す
  （これで新規ユーザーが User テーブルに載り、3時間毎の更新対象になる）
```

### Lambda 関数 (`lambda/functions/`)

- `updateWrapper` — バッチの起点。BUILD_ID の動的更新、buckler_id の事前チェック、ユーザーごとの invoke。環境変数: `USER_LIMIT`（デフォルト30、無料枠のコスト制約）, `INVOKE_INTERVAL`（デフォルト3秒）。注意: 実行時間は「ユーザー数 × INVOKE_INTERVAL」。関数のタイムアウトは900秒（2026-07-29 に60秒から変更。`USER_LIMIT=30` は60秒に収まらず18ユーザー付近で切れていた）。`check_buckler_id()` は updateBattleLog の環境変数（`BUCKLER_ID`/`GID`）を `get_function_configuration` で読むので、buckler_id 更新時に触る場所は updateBattleLog 側の1箇所だけでよい。
- `updateBattleLog` — スクレイピング本体。環境変数: `BUILD_ID`（updateWrapper が自動更新）, `BUCKLER_ID`（手動更新、下記）, `GID`, `REQUEST_INTERVAL`（ページ間待機、デフォルト1秒）。`replay_utils.py` の `transform_to_replay_reduced()` が ReplayReduced（縮約レコード）を生成する。
- `retrieveBattleLog` — API Gateway から呼ばれる読み出し口。環境変数: `FETCH_COOLDOWN`（デフォルト180秒）。fetchNow でも最終取得（User の `LastFetchedAt`、updateBattleLog が成功のたびに記録）からこの秒数以内なら DB から返すだけにする。公開エンドポイント経由で Buckler にバーストを撃たせられないようにするための制限なので削らないこと。`RETRIEVE_OPTION`（取得日数）は 1〜366 にクランプ。同期 invoke した updateBattleLog が失敗したかどうかは `FunctionError` キーで判定すること（`ResponseMetadata.HTTPStatusCode` は invoke API 自体の成否で、関数が例外を投げても 200。ここを見誤ると全ての失敗が「成功」に見えて古いデータを黙って返す。2026-07-29 修正）。失敗時は DB のデータを返しつつ全アイテムに `UpdateFailed: true` を載せる（未登録ユーザーは返せるものが無いので例外にする）。
- `deleteBattleLog` — 指定ユーザーの全レコード削除。
- `monthlyReport` — 毎月1日 9:00 JST（EventBridge Scheduler `MonthlyReport`）に前月の利用状況・エラー・ログ使用量を SNS でメール。データソースは CloudWatch メトリクス / Logs Insights（スキャンは対象月のみに限定しているのでログを無期限に残してもコストは増えない）/ User テーブル。手動テスト: `aws lambda invoke --function-name monthlyReport --payload '{"REPORT_MONTH":"YYYY-MM"}' ...`

### DynamoDB

- `User` (PK: UserCode) — 更新対象ユーザーのリスト + FighterId/CharacterName/CurrentLP。`Disabled=true` を付けたユーザーは updateWrapper のバッチ更新対象から外れる（手動管理。`set-user-disabled.sh` で付け外し。閲覧・履歴・fetchNow はそのまま使える）。この属性を消さないよう User テーブルへの書き込みは put_item ではなく update_item で行うこと。
- `BattleLog` (PK: UserCode, SK: UploadedAt) — `Replay`（元 JSON まるごと）と `ReplayReduced`（縮約版）の両方を保持。
- オートスケーリング無効、WCU=RCU=5（無料枠の制約）。大量書き込みは batch_write（25件ずつ）で行う。
- update 処理は冪等（最新 UploadedAt より新しいレコードだけ書く）なので重複実行対策は意図的に無い。

### フロントエンドとの結合点

`src/utils/replayReducedUtils.js` は ReplayReduced のスキーマに依存している。`lambda/functions/updateBattleLog/replay_utils.py` の `transform_to_replay_reduced()` を変更する場合はフロント側との整合を確認すること。

retrieveBattleLog のレスポンスは**フラットな配列**であること。`UserInfo.js` / `WinRateTable.js` / `CharacterTop10List.js` / `PlaytimeHistogram.js` と `lambda/scripts/dump-replayreduced-as-csv.py` がいずれも配列前提で `[0]` を参照するので、ユーザー単位の情報（`CharacterName` / `CurrentLP` / `UpdateFailed`）は冗長でも全アイテムに載せる方式にしてある。`UpdateFailed` は `Form.js` が `gameRecord[0]` を見て警告を出す。

## Buckler スクレイピングの知見（重要）

`updateBattleLog` の `fetch_json()` にエラー切り分けとリトライを実装済み。**以下のエラー挙動は 2026-07 に実サーバーで検証済み**。安易に書き換えないこと。

| サーバーの応答 | 原因 | 処理 |
|---|---|---|
| HTTP 404 | BUILD_ID が古い | 即時エラー（リトライ無意味）。`TransientError`: "BUILD_ID is likely stale" |
| HTTP 403 + JSON ボディで `pageProps.common.statusCode == 403` | **buckler_id の失効・無効** | 即時エラー。`ActionRequiredError`: "buckler_id is likely expired" |
| HTTP 403（上記ペイロードなし） | WAF・ブロックの可能性 | リトライ |
| HTTP 429/5xx、接続エラー、404以外の非JSON応答 | レートリミット・メンテナンス等の一時障害 | 指数バックオフ(1/2/4秒)で最大3回リトライ。`Retry-After` ヘッダーを尊重。リトライ全滅で `TransientError` |

### 通知設計（アラート疲れを起こさないこと）

「人間の対応が必要なときだけメールが来る」を守る。2026-07 に整理済み（それ以前は自己回復するエラーも全部メールしていて S/N 比が壊れていた）。

- **buckler_id 失効** → updateWrapper の `check_buckler_id()` がバッチ開始時に1回だけ検出し、SNS メール1通（件名 "[ACTION REQUIRED] buckler_id is likely expired"）を送ってバッチを中止する。SNS トピック: `email-notification`
- **updateBattleLog の `ActionRequiredError`** → ERROR ログのみ、**SNS しない**（上記の1通でカバーされるため）。全ユーザーで同時に発生する種類のエラーなので、invoke ごとに publish すると「ユーザー数 × 非同期リトライ回数」通のメールになる（2026-07-28 に13ユーザーで39通の実績。これがこの設計の理由）
- **想定外の例外**（バグ等）→ 即時 SNS メール（件名 "[ACTION REQUIRED]"）
- **`TransientError`**（一時障害・BUILD_ID 404 など自己回復する類）→ ERROR ログのみ、**SNS しない**。Lambda の非同期自動リトライ（updateBattleLog は2回）と次バッチで回復する
- **自己回復に失敗した**（リトライ全滅でイベント破棄）→ CloudWatch アラーム `updateBattleLog-update-dropped` / `updateWrapper-batch-dropped`（`AsyncEventsDropped >= 1`、period 3時間）が1通だけ通知。障害が続いてもアラーム状態が続くだけでメールは増えない。回復時に OK 通知
- 新しいエラーを追加するときは必ずこの分類に沿わせること。「とりあえず SNS」はアラートを壊す

特に注意すべき罠:

- **buckler_id 失効は JSON パースエラーにならない**。403 でも正常な JSON（`replay_list` なし）が返るため、明示的に検出しないと「新着なし」と区別がつかず、エラーも出ずに全ユーザーの更新が静かに止まる。`fetch_json()` の 403 チェックはこれを防ぐためのもの。
- BUILD_ID は updateWrapper がバッチごとにチェックし、**変わったときだけ**環境変数を更新する。`update_function_configuration` は非同期のため、更新後は waiter (`function_updated_v2`) で反映完了を待ってから invoke を開始する（2026-07 対応。これが無いと更新直後の invoke が旧環境変数の warm コンテナで走り 404 になる）。なお、バッチ間（最大3時間）に Capcom 側で buildId が変わった場合、その窓の間の fetchNow / 新規ユーザー登録は 404 になり得る（次のバッチで自己回復する）。
- レスポンスの生ボディ・ステータスは `fetch_json()` がエラーメッセージに含める設計。エラー調査はまず SNS メール / CloudWatch の warning ログを見る。
- buckler_id 失効の通知は**バッチ経路にしか無い**。retrieveBattleLog 経由（fetchNow・新規ユーザー登録）の updateBattleLog が失効に当たってもログだけで SNS は飛ばない。次のバッチの事前チェックが最大3時間以内に検知するので放置で構わないが、「fetchNow が失敗したのにメールが来ない」のは仕様。代わりに retrieveBattleLog が `UpdateFailed` フラグを返し、フロントが「最新データの取得に失敗しました」と表示する（2026-07-29 追加）。公開エンドポイントなのでここから SNS を撃つとメール増幅器になる。

### サーバーへの配慮（削らないこと）

- ページ取得間の `REQUEST_INTERVAL` 待機、updateWrapper の `INVOKE_INTERVAL`、`requests.Session` による接続再利用は、バースト的なアクセスを避けるための意図的な実装。
- リクエスト元 URL の形式: `https://www.streetfighter.com/6/buckler/_next/data/{BUILD_ID}/ja-jp/profile/{user_code}/battlelog.json?sid={user_code}&page={n}`（Next.js のデータエンドポイント）。取得できるのは直近100件（10ページ）のみ。全履歴の保持が DynamoDB を置いている理由。

## buckler_id の更新

`buckler_id` は Buckler のログイン Cookie で、一定期間で失効する。失効したら（SNS メールで "buckler_id is likely expired" が届いたら）**ブラウザから手動で取り直して** updateBattleLog の環境変数 `BUCKLER_ID` を更新する。

1. ブラウザで Buckler にログインする
2. DevTools → Application → Cookies → `buckler_id` の行を選択し、**下部の Cookie Value ペイン**から値をコピーする
3. `aws lambda update-function-configuration` で updateBattleLog の `BUCKLER_ID` を更新する（触るのはこの1箇所だけ。updateWrapper は updateBattleLog の環境変数を読むので更新不要）

注意点:

- **値は 64 文字**。`-` `_` を含む base64url。Application パネルの**表のセルから直接コピーすると切り詰められる**ことがあり、2026-07-28 には 60 文字（`-`/`_` が全欠落）の値が入って「取り直しても直らない」状態になった。貼る前に必ず長さを確認すること。Network タブのリクエストヘッダからコピーしても良い。
- 反映前に手元で検証できる:

```sh
BID='<コピーした値>'
echo "len=${#BID}"   # 64 でなければコピーミス
BUILD=$(curl -s https://www.streetfighter.com/6/buckler/ | grep -o '"buildId":"[^"]*"' | head -1 | cut -d'"' -f4)
curl -s -o /dev/null -w '%{http_code}\n' -H "Cookie: buckler_id=${BID}" \
  "https://www.streetfighter.com/6/buckler/_next/data/${BUILD}/ja-jp/profile/1654444812/battlelog.json?sid=1654444812"
# 200 なら有効、403 ならまだダメ
```

- Cookie 属性は `HttpOnly; Secure` なので、Console の `document.cookie` では取得できない。
- `lambda/scripts/update-buckler-id.sh` / `update-buckler-id.py`（playwright 版）は**使っていない**（実行環境に playwright が無い）。残置してあるだけなので参照しないこと。
