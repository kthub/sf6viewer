import React, { useState } from 'react';
import SimpleTable from './SimpleTable';
import SimpleForm from './SimpleForm';
import SimpleList from './SimpleList';
import './App.css';

function App() {
  const [gameRecord, setGameRecord] = useState({});

  return (
    <div className="App">
      <header className="App-header">
        <span className="title">SF6 Viewer</span><span className="version">ver 0.9</span>
      </header>
      <main className="App-contents">
        <SimpleForm setGameRecord={setGameRecord} />
        <br/>
        User Name: {gameRecord[0]?.ReplayReduced.fighter_id || 'XXXXXXXX'} （{gameRecord[0]?.CharacterName || 'XXXX'}）
        <ul>
          <li>１週間の勝率（ランクマッチのみ）</li>
            <SimpleTable gameRecord={gameRecord} />
          <li>対戦キャラベスト10（直近１週間）</li>
            <SimpleList gameRecord={gameRecord} />
        </ul>
      </main>
      <footer className="App-footer">
        <hr/>
        *** 使い方 ***<br/>
        <ul>
          <li>User Codeを指定してSubmitボタンを押すと過去１週間分の対戦情報に基づく集計結果が表示されます。</li>
          <li>自分のUser Codeは<a href="https://www.streetfighter.com/6/buckler/ja-jp" target="_blank" rel="noopener noreferrer" className="App-link">BUCKLER'S BOOT CAMP</a>で確認できます。</li>
          <li>データはユーザーごとに保持しています。初めて実行するユーザーはデータの取得に少し時間がかかります。</li>
          <li>ユーザーのデータは初回の実行以降３時間ごとに取得されるようになります。最新の情報が反映されるまでには最大３時間かかります。</li>
          <li>対戦情報は過去100対戦分しか取得できないため初回実行後しばらくの間は１週間分の結果が見られない場合があります。最長１週間で見られるようになります。</li>
        </ul>
      </footer>
    </div>
  );
}

export default App;