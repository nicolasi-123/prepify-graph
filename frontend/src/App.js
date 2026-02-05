import React, { useState, useRef } from 'react';
import SearchBar from './components/SearchBar';
import GraphVisualization from './components/GraphVisualization';
import PathResults from './components/PathResults';
import ExportControls from './components/ExportControls';
import './App.css';

function App() {
  const [pathData, setPathData] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const cyRef = useRef(null);

  const handlePathFound = (data) => {
    setPathData(data);
    setGraphData(data.subgraph);
  };

  const handleCyReady = (cy) => {
    cyRef.current = cy;
  };

  return (
    <div className="App">
      <SearchBar onPathFound={handlePathFound} />
      
      <div className="main-content">
        <div className="graph-section">
          <GraphVisualization 
            graphData={graphData} 
            onCyReady={handleCyReady}
          />
          
          {pathData && (
            <ExportControls 
              cyRef={cyRef}
              pathData={pathData}
            />
          )}
        </div>
        
        <div className="results-section">
          <PathResults pathData={pathData} />
        </div>
      </div>

      <footer className="footer">
        <p>Prepify Graph v1.0 | Data from OR justice.cz | © 2026</p>
      </footer>
    </div>
  );
}

export default App;