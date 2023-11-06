import React from 'react';
//import './SimpleList.css';
import * as Utils from './utils';

class SimpleList extends React.Component {

  convertData(gameRecord) {
    if (!Array.isArray(gameRecord)) {
      return ['XXXXX'];
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
    return (
      <List dataList={this.convertData(this.props.gameRecord)} />
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

export default SimpleList;

// Usage
// import SimpleList from './SimpleList';
// <SimpleList />
