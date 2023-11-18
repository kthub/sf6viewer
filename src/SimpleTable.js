import React from 'react';
import './SimpleTable.css';
import * as Utils from './utils';

class SimpleTable extends React.Component {

  convertData(beforeData) {
    if (!Array.isArray(beforeData)) {
      return [];
    }

    const statsByDate = {};
    let recentRecords = Utils.getRecentRankedMatch(beforeData);

    // add league point after battle
    Utils.addLeaguePointAfter(recentRecords, recentRecords[0].CurrentLP);

    recentRecords.forEach(record => {
      const jstOffset = 9 * 60 * 60 * 1000; // JST is UTC+9
      const dateStr = new Date(record.UploadedAt * 1000 + jstOffset).toISOString().split('T')[0];
      if (!statsByDate[dateStr]) {
        statsByDate[dateStr] = {
          win: 0,
          lose: 0,
          league_point_start: record.ReplayReduced.league_point,
          league_point_end: record.ReplayReduced.league_point_after
        };
      }

      statsByDate[dateStr].league_point_end = record.ReplayReduced.league_point_after;

      if (record.ReplayReduced.result === 'win') {
        statsByDate[dateStr].win += 1;
      } else if (record.ReplayReduced.result === 'lose') {
        statsByDate[dateStr].lose += 1;
      }
      // "Unknown" results are not counted for win or losses
    });

    const afterData = Object.keys(statsByDate).map(date => {
      const lpStart = statsByDate[date].league_point_start;
      const lpEnd = statsByDate[date].league_point_end;
      const lpChange = lpEnd - lpStart;
      const lpChangeFormatted = `${lpEnd} (${lpChange >= 0 ? '+' : ''}${lpChange})`;

      return {
        date,
        win: statsByDate[date].win,
        lose: statsByDate[date].lose,
        winRate: ((statsByDate[date].win / (statsByDate[date].win + statsByDate[date].lose)) * 100).toFixed(1) + '%',
        lpChange: lpChangeFormatted,
        rank: Utils.calculateRank(lpEnd)
      };
    }).sort((a, b) => new Date(b.date) - new Date(a.date));

    return afterData;
  }

  /**
   * React render method.
   */
  render() {
    if (!this.props.gameRecord || !Array.isArray(this.props.gameRecord) || this.props.gameRecord.length === 0) {
      return null;
    }
    return (
      <div>
        <li>１週間の勝率（ランクマッチのみ）</li>
        <Table dataList={this.convertData(this.props.gameRecord)} />
      </div>
    );
  }
}

function TableRow({ data }) {
  return (
    <tr>
      <td>{data.date}</td>
      <td>{data.win}</td>
      <td>{data.lose}</td>
      <td>{data.winRate}</td>
      <td>{data.lpChange > 0 ? `+${data.lpChange}` : data.lpChange}</td>
      <td>{data.rank}</td>
    </tr>
  );
}

function Table({ dataList }) {
  return (
    <table className="SimpleTable">
      <thead>
        <tr>
          <th>日付</th>
          <th>勝ち</th>
          <th>負け</th>
          <th>勝率</th>
          <th>LP増減</th>
          <th>ランク</th>
        </tr>
      </thead>
      <tbody>
        {dataList.map((data, index) => (
          <TableRow key={index} data={data} />
        ))}
      </tbody>
    </table>
  );
}

export default SimpleTable;

// Usage
// import SimpleTable from './SimpleTable';
// <SimpleTable />
