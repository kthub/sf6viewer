import React from 'react';
import './SimpleTable.css';

class SimpleTable extends React.Component {
  render() {
    return (
      <table className="SimpleTable">
        <thead>
          <tr>
            <th>Header 1</th>
            <th>Header 2</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Row 1 Data 1</td>
            <td>Row 1 Data 2</td>
          </tr>
          <tr>
            <td>Row 2 Data 1</td>
            <td>Row 2 Data 2</td>
          </tr>
        </tbody>
      </table>
    );
  }
}

export default SimpleTable;

// Usage
// import SimpleTable from './SimpleTable';
// <SimpleTable />
