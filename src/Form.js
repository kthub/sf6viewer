import React, { useState } from 'react';
import './Form.css';

function Form(props) {
  const [userCode, setUserCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setUserCode(e.target.value);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    // check input
    const isValid = /^\d{10}$/.test(userCode);
    if (!isValid) {
      setError(`User Codeの形式が不正です。(User Code : ${userCode})`);
    } else {
      setIsLoading(true);
      fetchData();
    }
  };

  const ErrorMessage = ({ error }) => {
    if (!error) {
      return null;
    }

    return (
      <div style={{ color: 'red', margin: '10px 0' }}>
        {error}
      </div>
    );
  }

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
      } else {
        const gameRecord = await response.json();
        props.setGameRecord(gameRecord);
        setIsLoading(false)
      }
    } catch (error) {
      setError(error.message + ' : ' + error.message);
      setIsLoading(false);
    }
  }

  return (
    <div className="wholeform">
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
        <button type="submit" disabled={isLoading}>
          {isLoading ? <span className="loading-text">Loading...</span> : 'Submit'}
        </button>
      </form>
      <ErrorMessage error={error} />
    </div>
  );
}

export default Form;