# SF6 Viewer
<img src="doc/logo.png" width="80px">  

[SF6 Viewer](https://orange-bay-0720d2e00.4.azurestaticapps.net/)は指定したユーザーの過去１週間の勝率を表示するアプリケーションです。  
集計の元となる対戦情報のデータはカプコンの[BUCKLER'S BOOT CAMP](https://www.streetfighter.com/6/buckler/ja-jp)から取得しています。（カプコンに怒られたらすぐに公開停止します）

### アプリケーション概要
SF6 Viewerはフロントエンドとバックエンドから構成されます。
- フロントエンド  
Microsoft Azure Static Web Apps上で動作するReactアプリケーションです。ソースはこのGitHubリポジトリで管理されています。GitHub Actionsにより自動ビルド・自動デプロイが行われます。
- バックエンド  
AWS(Lambda, DynamoDB, API Gateway, EventBridge)上に構築しています。Lambdaの実装言語はPythonです。ソースはこのGitHub上のlambdaディレクトリ以下で管理されています。デプロイは手動です。  
- 全体アーキテクチャ図  
<img src="doc/pic/ArchitectureOverview.png" width="800px">

### 特記事項
- BUCKLER'S BOOT CAMPから取得可能な対戦情報のデータは過去100件分のみであることから、全ての過去のデータを保持するためにDB(AWS DynamoDB)を配置する。また、BUCKLER'S BOOT CAMPから定期的にDBにデータを取得するバッチ処理を実装する。（最速で100試合するのに４時間弱かかるため、定期処理は３時間毎に実行する）
- フロントエンドは対戦情報の取得元としてこのDBを使用する。
- データを取得する対象のユーザーリストを保持するテーブル(User)を配置する。バッチ処理ではこのユーザーリストにあるユーザーについてのみ対戦情報の取得を行う。また、リストにないユーザーがツールを実行した場合は即時で対戦情報（直近100件）の取得を行い、ユーザーをこのリストに追加する。（これにより３時間ごとの更新対象に含まれるようになる）
- DBを更新するLambda関数には重複実行を防ぐための仕組みを用意しない。  
  これは以下の理由により正当化される。
  - update処理は冪等性が担保されているため重複して実行されても問題ない
  - 登録対象レコードは最新のレコードより新しいものという条件で抽出している。登録されていない未来の時間が取得されることはないため登録漏れは発生しない。
- バッチ処理で更新するユーザーの数に上限を設ける。初期値は100とする。（無料枠内で運用するためのコスト上の制約）
- CI環境でのビルドの警告は無視する。（Reactのプロジェクトがデフォルトで警告を出力してしまうため。無視しないとGitHub Actionsによるビルドが成功しない）
- DB(BattleLogテーブル)のオートスケーリングは無効とする。またCapacity Unitは下記の通りとする。（無料枠内で運用するためのコスト上の制約）
  - Write Capacity Unit (WCU) = 10
  - Read Capacity Unit (RCU) = 10