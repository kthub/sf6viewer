import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import * as Utils from './utils';

class PlaytimeHistogram extends React.Component {

  // エポックタイムをJSTに変換して時間帯を計算する
  convertEpochToJSTHour(epoch) {
    const date = new Date(epoch * 1000);
    // UTC時間に変換した後、JST（UTC+9）に変換
    const jstDate = new Date(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate(), date.getUTCHours(), date.getUTCMinutes(), date.getUTCSeconds());
    jstDate.setHours(jstDate.getHours() + 9);

    // 時間のフォーマットを改善（例：0 -> 00:00, 15 -> 15:00）
    const hour = jstDate.getHours();
    return `${hour.toString().padStart(2, '0')}:00`;
  }

  // プレイ時間のデータを集計する
  calculateHistogramData(gameRecord) {
    // キーが時間（'00:00', '01:00', ..., '23:00'）で、値がカウントのオブジェクトを初期化
    const hoursMap = {};
    for (let hour = 0; hour < 24; hour++) {
      hoursMap[`${hour.toString().padStart(2, '0')}:00`] = 0;
    }

    let recentRecords = Utils.getRecentRankedMatch(gameRecord);

    recentRecords.forEach(record => {
      const hourString = this.convertEpochToJSTHour(record.UploadedAt);
      hoursMap[hourString]++;
    });

    // recharts が理解できる形式にデータを変換
    return Object.entries(hoursMap).map(([hour, count]) => ({ hour, count }));
  }

  render() {
    if (!this.props.gameRecord ||
      !Array.isArray(this.props.gameRecord) ||
      this.props.gameRecord.length === 0 ||
      this.props.gameRecord[0].CharacterName === '__NO_DATA__') {
      return null;
    }

    const histogramData = this.calculateHistogramData(this.props.gameRecord);
    return (
      <div>
        <ul>
          <li>ランクマやってる時間帯（直近１週間）</li>
          <ResponsiveContainer width="90%" height={300}>
            <BarChart data={histogramData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hour" />
              <YAxis hide={true}/>
              <Tooltip />
              <Bar dataKey="count" fill="#8884d8" />
            </BarChart>
          </ResponsiveContainer>
        </ul>
      </div>
    );
  }
}

export default PlaytimeHistogram;