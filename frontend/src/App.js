import React, { useState } from 'react';
import SearchBar from './components/SearchBar';
import GraphVisualization from './components/GraphVisualization';
import PathResults from './components/PathResults';
import './App.css';

function App() {
  const [pathData, setPathData] = useState(null);
  const [graphData, setGraphData] = useState(null);

  const handlePathFound = (data) => {
    setPathData(data);
    setGraphData(data.subgraph);
  };

  return (
    <div className="App">
      <SearchBar onPathFound={handlePathFound} />
      
      <div className="main-content">
        <div className="graph-section">
          <GraphVisualization graphData={graphData} />
        </div>
        
        <div className="results-section">
          <PathResults pathData={pathData} />
        </div>
      </div>

      <footer className="footer">
        <p>Prepify Graph v1.0 | Data z OR justice.cz | © 2026</p>
      </footer>
    </div>
  );
}

export default App;