import React, { useState } from 'react';
import './App.css';
import Form from './Form';
import UserInfo from './UserInfo';
import WinRateTable from './WinRateTable';
import CharacterTop10List from './CharacterTop10List';
import PlaytimeHistogram from './PlaytimeHistogram';

function App() {
  const [gameRecord, setGameRecord] = useState({});

  return (
    <div className="App">
      <header className="App-header">
        <span className="title">SF6 Viewer</span><span className="version">ver 1.1</span>
      </header>
      <main className="App-contents">
        <Form setGameRecord={setGameRecord} />
        <UserInfo gameRecord={gameRecord} />
        <WinRateTable gameRecord={gameRecord} />
        <CharacterTop10List gameRecord={gameRecord} />
        <PlaytimeHistogram gameRecord={gameRecord} />
      </main>
      <footer className="App-footer">
        <hr/>
        *** 使い方 ***
        <ul>
          <li>このツールはストリートファイター６の直近１週間の対戦情報を表示するツールです。</li>
          <li>User Codeを指定してSubmitボタンを押すと過去１週間分の対戦情報の集計結果が表示されます。</li>
          <li>自分のUser Codeは<a href="https://www.streetfighter.com/6/buckler/ja-jp" target="_blank" rel="noopener noreferrer" className="App-link">BUCKLER'S BOOT CAMP</a>で確認できます。</li>
          <li>データはユーザーごとに保持しています。初めて実行するユーザーはデータの取得に少し時間がかかります。</li>
          <li>ユーザーのデータは初回の実行以降３時間ごとに取得されるようになります。そのため最新の情報が反映されるまでには最大３時間かかります。</li>
          <li>対戦情報は過去100対戦分しか取得できないため初回実行後しばらくの間は１週間分の結果が見られない場合があります。遅くとも１週間後には見られるようになります。</li>
          <li>URLの最後に「?sid=xxxxxxxxxx」を付けるとURLから直接Submitを実行できます（sidはUser Codeのことです）。リンクを作っておくと便利です。</li>
          <li>URLの最後に「?sid=xxxxxxxxxx&fetchNow=true」を付けると即時で最新のデータを取得できます。少し時間がかかります。</li>
        </ul>
      </footer>
    </div>
  );
}

export default App;