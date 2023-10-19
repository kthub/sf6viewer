import SimpleTable from './SimpleTable';
import './App.css';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <p>
          SF6 Viewer Prototype
        </p>
        Win rate table
        <SimpleTable />
        <br />
        <a
          className="App-link"
          href="https://www.streetfighter.com/6/buckler/ja-jp"
          target="_blank"
          rel="noopener noreferrer"
        >
          STREET FIGHTER : BUCKLER's
        </a>
      </header>
    </div>
  );
}

function MyButton() {
  return (
    <button>I'm a button</button>
  );
}

export default App;
