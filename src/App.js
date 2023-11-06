import React, { useState } from 'react';
import SimpleTable from './SimpleTable';
import SimpleForm from './SimpleForm';
import SimpleList from './SimpleList';
import './App.css';

function App() {
  // Initial state of user information
  const [gameRecord, setGameRecord] = useState({});

  return (
    <div className="App">
      <header className="App-header">
        <p className="title">
          SF6 Viewer
        </p>
        <div className="App-contents">
          <SimpleForm setGameRecord={setGameRecord} />
          <br />
          User Name: {gameRecord[0]?.ReplayReduced.fighter_id || 'XXXXXXXX'}
          <ul>
            <li>1週間の勝率</li>
              <SimpleTable gameRecord={gameRecord} />
            <li>対戦キャラベスト10（直近1週間）</li>
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
        </div>
      </header>
    </div>
  );
}

export default App;
