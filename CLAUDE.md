# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

SF6 Viewer — 指定ユーザーの過去1週間の勝率を表示するアプリケーション。対戦データはカプコンの BUCKLER'S BOOT CAMP (https://www.streetfighter.com/6/buckler/) をスクレイピングして取得する。**公式 API ではない**ため、サーバーに負荷をかけない・行儀よくリクエストすることが最重要の運用制約（README 曰く「カプコンに怒られたらすぐに公開停止します」）。

- フロントエンド: React (Create React App / react-scripts)。Azure Static Web Apps 上で動作。GitHub Actions で main への push 時に自動ビルド・自動デプロイ。
- バックエンド: AWS (Lambda[Python] + DynamoDB + API Gateway + EventBridge)。ソースは `lambda/` 以下。**デプロイは手動**。

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

# buckler_id の更新（失効時。playwright でログインして環境変数を更新）
lambda/scripts/update-buckler-id.sh
# パスワードは update-buckler-id-secrets.sh に直接記載（Git には .template のみ）
```

- Python は 2 スペースインデント。
- CI (GitHub Actions) では React のデフォルト警告でビルドが落ちるため警告を無視する設定になっている。

## アーキテクチャ

### データフロー

```
EventBridge (3時間毎)
  → updateWrapper: Buckler トップページから buildId をスクレイピング
      → 変わっていれば updateBattleLog の環境変数 BUILD_ID を更新（反映完了を待つ）
      → User テーブルの各ユーザーについて updateBattleLog を非同期 invoke
        (INVOKE_INTERVAL 秒間隔・USER_LIMIT 件まで)
  → updateBattleLog: battlelog.json を最大10ページ取得 → BattleLog テーブルに書き込み
      → 新着があれば play.json も取得して User テーブルを更新

フロントエンド → API Gateway → retrieveBattleLog: DB から対戦履歴を返す。
  未登録ユーザーまたは FETCH_NOW=true の場合は updateBattleLog を同期 invoke してから返す
  （これで新規ユーザーが User テーブルに載り、3時間毎の更新対象になる）
```

### Lambda 関数 (`lambda/functions/`)

- `updateWrapper` — バッチの起点。BUILD_ID の動的更新とユーザーごとの invoke。環境変数: `USER_LIMIT`（デフォルト30、無料枠のコスト制約）, `INVOKE_INTERVAL`（デフォルト3秒）。注意: 実行時間は「ユーザー数 × INVOKE_INTERVAL」なので Lambda の15分制限に注意。
- `updateBattleLog` — スクレイピング本体。環境変数: `BUILD_ID`（updateWrapper が自動更新）, `BUCKLER_ID`（手動更新、下記）, `GID`, `REQUEST_INTERVAL`（ページ間待機、デフォルト1秒）。エラー時は SNS トピック `email-notification` にメール通知。`replay_utils.py` の `transform_to_replay_reduced()` が ReplayReduced（縮約レコード）を生成する。
- `retrieveBattleLog` — API Gateway から呼ばれる読み出し口。
- `deleteBattleLog` — 指定ユーザーの全レコード削除。

### DynamoDB

- `User` (PK: UserCode) — 更新対象ユーザーのリスト + FighterId/CharacterName/CurrentLP。`Disabled=true` を付けたユーザーは updateWrapper のバッチ更新対象から外れる（手動管理。`set-user-disabled.sh` で付け外し。閲覧・履歴・fetchNow はそのまま使える）。この属性を消さないよう User テーブルへの書き込みは put_item ではなく update_item で行うこと。
- `BattleLog` (PK: UserCode, SK: UploadedAt) — `Replay`（元 JSON まるごと）と `ReplayReduced`（縮約版）の両方を保持。
- オートスケーリング無効、WCU=RCU=5（無料枠の制約）。大量書き込みは batch_write（25件ずつ）で行う。
- update 処理は冪等（最新 UploadedAt より新しいレコードだけ書く）なので重複実行対策は意図的に無い。

### フロントエンドとの結合点

`src/utils/replayReducedUtils.js` は ReplayReduced のスキーマに依存している。`lambda/functions/updateBattleLog/replay_utils.py` の `transform_to_replay_reduced()` を変更する場合はフロント側との整合を確認すること。

## Buckler スクレイピングの知見（重要）

`updateBattleLog` の `fetch_json()` にエラー切り分けとリトライを実装済み。**以下のエラー挙動は 2026-07 に実サーバーで検証済み**。安易に書き換えないこと。

| サーバーの応答 | 原因 | 処理 |
|---|---|---|
| HTTP 404 | BUILD_ID が古い | 即時エラー（リトライ無意味）。メッセージ: "BUILD_ID is likely stale" |
| HTTP 403 + JSON ボディで `pageProps.common.statusCode == 403` | **buckler_id の失効・無効** | 即時エラー。メッセージ: "buckler_id is likely expired" |
| HTTP 403（上記ペイロードなし） | WAF・ブロックの可能性 | リトライ |
| HTTP 429/5xx、接続エラー、404以外の非JSON応答 | レートリミット・メンテナンス等の一時障害 | 指数バックオフ(1/2/4秒)で最大3回リトライ。`Retry-After` ヘッダーを尊重。リトライ中は warning ログのみで SNS 通知しない |

特に注意すべき罠:

- **buckler_id 失効は JSON パースエラーにならない**。403 でも正常な JSON（`replay_list` なし）が返るため、明示的に検出しないと「新着なし」と区別がつかず、エラーも出ずに全ユーザーの更新が静かに止まる。`fetch_json()` の 403 チェックはこれを防ぐためのもの。
- BUILD_ID は updateWrapper がバッチごとにチェックし、**変わったときだけ**環境変数を更新する。`update_function_configuration` は非同期のため、更新後は waiter (`function_updated_v2`) で反映完了を待ってから invoke を開始する（2026-07 対応。これが無いと更新直後の invoke が旧環境変数の warm コンテナで走り 404 になる）。なお、バッチ間（最大3時間）に Capcom 側で buildId が変わった場合、その窓の間の fetchNow / 新規ユーザー登録は 404 になり得る（次のバッチで自己回復する）。
- レスポンスの生ボディ・ステータスは `fetch_json()` がエラーメッセージに含める設計。エラー調査はまず SNS メール / CloudWatch の warning ログを見る。

### サーバーへの配慮（削らないこと）

- ページ取得間の `REQUEST_INTERVAL` 待機、updateWrapper の `INVOKE_INTERVAL`、`requests.Session` による接続再利用は、バースト的なアクセスを避けるための意図的な実装。
- リクエスト元 URL の形式: `https://www.streetfighter.com/6/buckler/_next/data/{BUILD_ID}/ja-jp/profile/{user_code}/battlelog.json?sid={user_code}&page={n}`（Next.js のデータエンドポイント）。取得できるのは直近100件（10ページ）のみ。全履歴の保持が DynamoDB を置いている理由。

## buckler_id の更新

`buckler_id` は Buckler のログイン Cookie で、一定期間で失効する。失効したら（SNS メールで "buckler_id is likely expired" が届いたら）`lambda/scripts/update-buckler-id.sh` を実行する。playwright(python) でログインを自動化し、Lambda の環境変数 `BUCKLER_ID` を更新する。
