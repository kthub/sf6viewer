# AWS リソース一覧 (SF6 Viewer)

SF6 Viewer が使用している AWS リソースの一覧。IaC 管理はしていないため、リソースを追加・変更したらこのファイルを更新すること。

- アカウント: 572065744477 / リージョン: ap-northeast-1
- 最終更新: 2026-07-29（このプロジェクトと無関係なリソースは載せていない。例: export-cwlogs, aws-rest-demo 系）

## Lambda 関数（runtime: python3.11）

| 関数 | 役割 | 実行ロール | タイムアウト | 備考 |
|---|---|---|---|---|
| updateWrapper | 3時間毎バッチの起点 | service-role/updateWrapper-role-zovxb0ix | 900秒 | layer: web-scraping:3。2026-07-29 に 60秒 → 900秒（USER_LIMIT=30 × INVOKE_INTERVAL=3秒 が 60秒に収まらず、18ユーザー付近で頭打ちになるため） |
| updateBattleLog | スクレイピング本体 | service-role/updateBattleLog-role-lcy9kkda | 300秒 | layer: web-scraping:3。非同期リトライ2回・イベント最大保持1時間 |
| retrieveBattleLog | API の読み出し口 | service-role/retrieveBattleLog-role-rdm3ol1j | 300秒 | 実際の上限は API Gateway 側の統合タイムアウト30秒 |
| deleteBattleLog | ユーザーの全レコード削除（手動実行のみ） | service-role/deleteBattleLog-role-vt9iqckp | - | API 非公開 |
| monthlyReport | 月次レポートメール | monthlyReport-role | - | 2026-07 作成 |

- タイムアウト・メモリ等の関数設定はコンソール/CLI 管理で、リポジトリには入っていない。`deploy.sh`（`update-function-code` のみ）はこれらを上書きしないので、デプロイで元に戻ることはない。

- Lambda レイヤー: `web-scraping`（v3。requests, bs4 等。ソースは `lambda/layers/`）

## DynamoDB

| テーブル | キー | 備考 |
|---|---|---|
| User | PK: UserCode | WCU=RCU=5、オートスケーリング無効 |
| BattleLog | PK: UserCode, SK: UploadedAt | 同上 |

## API Gateway (HTTP API)

- API ID: `wcsppz000i` — ルートは `GET /retrieveBattleLog`（認証なし）のみ。→ retrieveBattleLog

## EventBridge Scheduler

| スケジュール | cron (Asia/Tokyo) | ターゲット | invoke ロール |
|---|---|---|---|
| UpdateBattleLog | `0 */3 * * ? *` | updateWrapper | service-role/Amazon_EventBridge_Scheduler_LAMBDA_28170bf077 |
| MonthlyReport | `0 9 1 * ? *` | monthlyReport | EventBridge_Scheduler_monthlyReport（2026-07 作成） |

## SNS

- トピック: `email-notification` — サブスクリプション: email → keiichi.tsuda@gmail.com

## CloudWatch アラーム（2026-07 作成）

| アラーム | 条件 | 意味 |
|---|---|---|
| updateBattleLog-update-dropped | AsyncEventsDropped >= 1 (Sum, 3h) | 更新1件がリトライ全滅で失われた |
| updateWrapper-batch-dropped | AsyncEventsDropped >= 1 (Sum, 3h) | バッチ丸ごと実行されなかった |

- 通知先: いずれも `email-notification`（ALARM / OK 両方）

## IAM（このプロジェクト向けに作成したもの）

| ロール | 用途 | 権限の要点 |
|---|---|---|
| monthlyReport-role | monthlyReport 実行 | Logs Insights（3ロググループ）読み取り、cloudwatch:GetMetricStatistics、sns:Publish（email-notification）、dynamodb:Scan（User）、＋AWSLambdaBasicExecutionRole |
| EventBridge_Scheduler_monthlyReport | Scheduler → monthlyReport | lambda:InvokeFunction（monthlyReport のみ） |

（各 Lambda の service-role/*-role-* はコンソール作成時の自動生成ロール）

- 管理ポリシー `sns-gmail-policy`（sns:Publish → email-notification のみ）は updateBattleLog と **updateWrapper** の両ロールにアタッチしている。updateWrapper の分は 2026-07-28 追加（buckler_id 失効時にバッチ開始時点で1通だけ通知するため）。

## CloudWatch Logs

- `/aws/lambda/<関数名>` が関数ごとに自動作成。保持期間は無期限（総量は monthlyReport が毎月報告）。

## AWS 外

- フロントエンド: Azure Static Web Apps（GitHub Actions で main への push 時にデプロイ）
