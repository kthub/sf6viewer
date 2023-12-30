import React from 'react';
import * as Utils from '../utils';
import './CharacterTop10List.css';

class CharacterTop10List extends React.Component {

  convertData(gameRecord) {
    if (!Array.isArray(gameRecord)) {
      return { topCharacters: [], cmRatio: { C: 0, M: 0 }, cmWinRate: { C: 0, M: 0 } };
    }

    const charNameCount = {};
    const cmCount = { C: 0, M: 0 };
    const cmWinCount = { C: 0, M: 0 };
    const recentRecords = Utils.getRecentRankedMatch(gameRecord);

    recentRecords.forEach(record => {
      let inputType = record.ReplayReduced.opponent.battle_input_type_name;
      let char_name = `${inputType} ${record.ReplayReduced.opponent.character_name}`;
      let isWin = record.ReplayReduced.result === "win";

      // Update character count and wins
      if (!charNameCount[char_name]) {
        charNameCount[char_name] = { cnt: 1, win: isWin ? 1 : 0 };
      } else {
        charNameCount[char_name].cnt += 1;
        if (isWin) {
          charNameCount[char_name].win += 1;
        }
      }

      // Update CM count and wins
      if (inputType === 'C' || inputType === 'M') {
        cmCount[inputType] += 1;
        if (isWin) {
          cmWinCount[inputType] += 1;
        }
      }
    });

    // Calculate CM ratios and win rates
    let totalCMCount = cmCount.C + cmCount.M;
    let cmRatio = {
      C: totalCMCount > 0 ? (cmCount.C / totalCMCount * 100).toFixed(1) : 0,
      M: totalCMCount > 0 ? (cmCount.M / totalCMCount * 100).toFixed(1) : 0
    };

    let cmWinRate = {
      C: cmCount.C > 0 ? (cmWinCount.C / cmCount.C * 100).toFixed(1) : 0,
      M: cmCount.M > 0 ? (cmWinCount.M / cmCount.M * 100).toFixed(1) : 0
    };

    // Convert object to array and sort by count
    let sortedEntries = Object.entries(charNameCount).sort((a, b) => b[1].cnt - a[1].cnt);

    // Process the top 10 entries
    let topCharacters = sortedEntries.slice(0, 10).map(entry => {
      let [key, value] = entry;
      return `${key} (${value.cnt}回, 勝率: ${(value.win / value.cnt * 100).toFixed(1)}%)`;
    });

    return { topCharacters, cmRatio, cmWinRate };
  }

  render() {
    if (!this.props.gameRecord ||
        !Array.isArray(this.props.gameRecord) ||
        this.props.gameRecord.length === 0 ||
        this.props.gameRecord[0].CharacterName === '__NO_DATA__' ||
        !this.props.gameRecord[0].ReplayReduced) {
      return null;
    }

    const { topCharacters, cmRatio, cmWinRate } = this.convertData(this.props.gameRecord);

    return (
      <div className="list-container">
        <ul className="list">
          <li>対戦キャラベスト10（直近１週間）</li>
          <List dataList={topCharacters} />
        </ul>
        <ul className="list">
          <li>対戦相手のCM比率と勝率（直近１週間）</li>
          <ol>操作タイプClassic : {cmRatio.C}% (勝率: {cmWinRate.C}%)</ol>
          <ol>操作タイプModern : {cmRatio.M}% (勝率: {cmWinRate.M}%)</ol>
        </ul>
      </div>
    );
  }
}

function List({ dataList }) {
  return (
    <ol>
      {dataList.map((data, index) => (
        <li key={index}>{data}</li>
      ))}
    </ol>
  );
}

export default CharacterTop10List;