import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import * as Utils from '../utils';
import './PlaytimeHistogram.css';

class PlaytimeHistogram extends React.Component {

  calculateHistogramData(gameRecord) {
    const winsMap = {};
    const lossesMap = {};
    const hoursMap = {};
    for (let hour = 0; hour < 24; hour++) {
      const hourString = `${hour.toString().padStart(2, '0')}:00`;
      winsMap[hourString] = 0;
      lossesMap[hourString] = 0;
      hoursMap[hourString] = 0;
    }

    let recentRecords = Utils.getRecentRankedMatch(gameRecord);
    recentRecords.forEach(record => {
      const hourString = Utils.getJSTHour(record.UploadedAt);
      hoursMap[hourString]++;
      if (record.ReplayReduced.result === "win") {
        winsMap[hourString]++;
      } else {
        lossesMap[hourString]++;
      }
    });

    return Object.entries(hoursMap).map(([hour, count]) => {
      const wins = winsMap[hour];
      const losses = lossesMap[hour];
      const winRate = wins + losses > 0 ? (wins / (wins + losses)) * 100 : 0;
      return { hour, count, winRate };
    });
  }

  renderTooltip = (props) => {
    if (props.active && props.payload && props.payload.length) {
      const data = props.payload[0].payload;
      return (
        <div className="custom-tooltip">
          <p>{`時間帯: ${data.hour}`}</p>
          <p>{`勝率: ${data.winRate.toFixed(2)}%`}</p>
        </div>
      );
    }
    return null;
  };

  render() {
    if (!this.props.gameRecord ||
      !Array.isArray(this.props.gameRecord) ||
      this.props.gameRecord.length === 0 ||
      this.props.gameRecord[0].CharacterName === '__NO_DATA__' ||
      !this.props.gameRecord[0].ReplayReduced) {
      return null;
    }
    return (
      <div>
        <ul>
          <li>ランクマやってる時間帯と勝率（直近１週間）</li>
          <ResponsiveContainer width="90%" height={300}>
            <BarChart data={this.calculateHistogramData(this.props.gameRecord)}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hour" />
              <YAxis hide={true}/>
              <Tooltip content={this.renderTooltip} />
              <Bar dataKey="count" fill="#8884d8" />
            </BarChart>
          </ResponsiveContainer>
        </ul>
      </div>
    );
  }
}

export default PlaytimeHistogram;