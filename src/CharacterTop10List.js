import React from 'react';
import * as Utils from './utils';

class CharacterTop10List extends React.Component {

  convertData(gameRecord) {
    if (!Array.isArray(gameRecord)) {
      return [];
    }

    const charNameCount = {};
    const recentRecords = Utils.getRecentRankedMatch(gameRecord);
    recentRecords.forEach(record => {
      let char_name = `${record.ReplayReduced.opponent.battle_input_type_name} ${record.ReplayReduced.opponent.character_name}`;
      if (!charNameCount[char_name]) {
        charNameCount[char_name] = {cnt: 1, win: record.ReplayReduced.result === "win" ? 1 : 0};
      } else {
        charNameCount[char_name].cnt += 1;
        if (record.ReplayReduced.result === "win") {
          charNameCount[char_name].win += 1;
        }
      }
    });

    // Convert object to array and sort by count
    let sortedEntries = Object.entries(charNameCount).sort((a, b) => b[1].cnt - a[1].cnt);

    // Process the top 10 entries
    let ret = sortedEntries.slice(0, 10).map(entry => {
      let [key, value] = entry;
      return `${key} (${value.cnt}回, 勝率: ${(value.win / value.cnt * 100).toFixed(1)}%)`;
    });

    // Now ret contains the top 10 most encountered characters along with their encounter counts and win rates

    return ret;
  }

  render() {
    if (!this.props.gameRecord ||
        !Array.isArray(this.props.gameRecord) ||
        this.props.gameRecord.length === 0 ||
        this.props.gameRecord[0].CharacterName === '__NO_DATA__') {
      return null;
    }
    return (
      <div>
        <ul>
          <li>対戦キャラベスト10（直近１週間）</li>
          <List dataList={this.convertData(this.props.gameRecord)} />
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