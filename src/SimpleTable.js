import React from 'react';
import './SimpleTable.css';

class SimpleTable extends React.Component {

  calculateRank(lp) {
      const ranks = [
          { name: 'Master', base: 25000, step: 0 },
          { name: 'Diamond', base: 19000, step: 1200 },
          { name: 'Platinum', base: 13000, step: 1200 },
          { name: 'Gold', base: 9000, step: 800 },
          { name: 'Silver', base: 5000, step: 800 },
          { name: 'Bronze', base: 3000, step: 400 },
          { name: 'Iron', base: 1000, step: 400 },
          { name: 'Rookie', base: 0, step: 200 }
      ];

      for (let i = 0; i < ranks.length; i++) {
          const rank = ranks[i];
          if (lp >= rank.base) {
              const remainingLp = lp - rank.base;
              const divisions = Math.floor(remainingLp / rank.step) + 1;
              const stars = '☆'.repeat(divisions);
              return `${rank.name}${stars ? ' ' + stars : ''}`;
          }
      }
  }

  convertData(beforeData) {
    if (!Array.isArray(beforeData)) {
      return [];
    }

    // Get the current date and time in JST
    const jstOffset = 9 * 60 * 60 * 1000; // JST is UTC+9
    const nowJst = new Date(Date.now() + jstOffset);
    const oneWeekAgoJst = new Date(nowJst.getTime() - 7 * 24 * 60 * 60 * 1000);

    // Filter records from the last 7 days
    const recentRecords = beforeData.filter(record => {
      const uploadedDate = new Date(record.UploadedAt * 1000 + jstOffset);
      return uploadedDate >= oneWeekAgoJst;
    });

    // Sort records by date
    recentRecords.sort((a, b) => a.UploadedAt - b.UploadedAt);

    // Group records by date and calculate stats
    const statsByDate = {};
    recentRecords.forEach(record => {
      const dateStr = new Date(record.UploadedAt * 1000 + jstOffset).toISOString().split('T')[0];
      if (!statsByDate[dateStr]) {
        statsByDate[dateStr] = {
          win: 0,
          lose: 0,
          league_point_start: record.ReplayReduced.league_point,
          league_point_end: record.ReplayReduced.league_point
        };
      }

      statsByDate[dateStr].league_point_end = record.ReplayReduced.league_point;

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
        rank: this.calculateRank(lpEnd)
      };
    }).sort((a, b) => new Date(b.date) - new Date(a.date));

    return afterData;
  }

  /**
   * React render method.
   */
  render() {
    return (
      <Table dataList={this.convertData(this.props.gameRecord)} />
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
