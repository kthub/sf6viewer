import React, { useState } from 'react';
import './SimpleForm.css';

function SimpleForm(props) {
  const [userCode, setUserCode] = useState('');

  const handleChange = (e) => {
    setUserCode(e.target.value);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    fetchData();
  };

  async function fetchData() {
    const url = `https://wcsppz000i.execute-api.ap-northeast-1.amazonaws.com/retrieveBattleLog?USER_CODE=${userCode}`;

    try {
      const response = await fetch(url, {
        headers: {
          'Accept-Encoding': 'gzip, deflate, br'
        }
      });
      if (!response.ok) {
        throw new Error('Network response was not ok ' + response.statusText);
      }
      const gameRecord = await response.json();

      // 取得したデータで親コンポーネントの状態を更新
      props.setGameRecord(gameRecord);

    } catch (error) {
      console.error('There has been a problem with your fetch operation:', error);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="form-content">
      <label>
        User Code: &nbsp;
        <input type="text"
               name="userCode"
               size="14"
               placeholder="1234567890"
               value={userCode}
               onChange={handleChange} />
      </label>
      <button type="submit">Submit</button>
    </form>
  );
}

export default SimpleForm;
