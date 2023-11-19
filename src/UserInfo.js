import React from 'react';

class UserInfo extends React.Component {
  render() {
    if (!this.props.gameRecord || !Array.isArray(this.props.gameRecord) || this.props.gameRecord.length === 0) {
      return null;
    }
    return (
      <span>
        User Name: {this.props.gameRecord[0].ReplayReduced.fighter_id} （{this.props.gameRecord[0].CharacterName}）
      </span>
    );
  }
}

export default UserInfo;