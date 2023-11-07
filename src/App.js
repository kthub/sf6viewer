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
        User Name: {gameRecord[0]?.ReplayReduced.fighter_id || 'XXXXXXXX'}
        <ul>
          <li>１週間の勝率（ランクマッチのみ）</li>
            <SimpleTable gameRecord={gameRecord} />
          <li>対戦キャラベスト10（直近１週間）</li>
            <SimpleList gameRecord={gameRecord} />
        </ul>
        <a
          className="App-link"
          href="https://www.streetfighter.com/6/buckler/ja-jp"
          target="_blank"
          rel="noopener noreferrer"
        >
          BUCKLER'S BOOT CAMP
        </a>
      </main>
    </div>
  );
}

export default App;