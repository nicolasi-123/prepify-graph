import React, { useState } from 'react';
import axios from 'axios';
import config from '../config';

function SearchBar({ onPathFound }) {
  const [sourceQuery, setSourceQuery] = useState('');
  const [targetQuery, setTargetQuery] = useState('');
  const [sourceResults, setSourceResults] = useState([]);
  const [targetResults, setTargetResults] = useState([]);
  const [selectedSource, setSelectedSource] = useState(null);
  const [selectedTarget, setSelectedTarget] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showSourceResults, setShowSourceResults] = useState(false);
  const [showTargetResults, setShowTargetResults] = useState(false);

  const searchEntities = async (query, setResults) => {
    if (query.length < 2) {
      setResults([]);
      return;
    }

    try {
      const response = await axios.get(`${config.API_BASE_URL}/api/search`, {
        params: { q: query }
      });
      setResults(response.data.results || []);
    } catch (error) {
      console.error('Search error:', error);
      setResults([]);
    }
  };

  const handleSourceChange = (e) => {
    const value = e.target.value;
    setSourceQuery(value);
    setShowSourceResults(true);
    searchEntities(value, setSourceResults);
  };

  const handleTargetChange = (e) => {
    const value = e.target.value;
    setTargetQuery(value);
    setShowTargetResults(true);
    searchEntities(value, setTargetResults);
  };

  const selectSource = (entity) => {
    setSelectedSource(entity);
    setSourceQuery(entity.name);
    setShowSourceResults(false);
  };

  const selectTarget = (entity) => {
    setSelectedTarget(entity);
    setTargetQuery(entity.name);
    setShowTargetResults(false);
  };

  const findPath = async () => {
    if (!selectedSource || !selectedTarget) {
      alert('Vyberte prosím obě entity');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${config.API_BASE_URL}/api/top-paths`, {
        source: selectedSource.id,
        target: selectedTarget.id,
        k: 3
      });

      onPathFound(response.data);
    } catch (error) {
      console.error('Error finding path:', error);
      alert('Chyba při hledání cesty');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="search-container">
      <h1>Prepify Graph - Vizualizace vztahu</h1>
      <p className="subtitle">Najdete nejkratsi cestu mezi firmami a osobami</p>
      <div className="search-boxes">
        <div className="search-box">
          <label>Z (osoba/firma):</label>
          <input
            type="text"
            value={sourceQuery}
            onChange={handleSourceChange}
            onFocus={() => sourceQuery && setShowSourceResults(true)}
            placeholder="Začněte psát jméno..."
          />
          {showSourceResults && sourceResults.length > 0 && (
            <div className="results-dropdown">
              {sourceResults.map((entity) => (
                <div
                  key={entity.id}
                  className="result-item"
                  onClick={() => selectSource(entity)}
                >
                  <strong>{entity.name}</strong>
                  <span className="entity-type">{entity.type}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="search-box">
          <label>Do (osoba/firma):</label>
          <input
            type="text"
            value={targetQuery}
            onChange={handleTargetChange}
            onFocus={() => targetQuery && setShowTargetResults(true)}
            placeholder="Začněte psát jméno..."
          />
          {showTargetResults && targetResults.length > 0 && (
            <div className="results-dropdown">
              {targetResults.map((entity) => (
                <div
                  key={entity.id}
                  className="result-item"
                  onClick={() => selectTarget(entity)}
                >
                  <strong>{entity.name}</strong>
                  <span className="entity-type">{entity.type}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <button
        onClick={findPath}
        disabled={!selectedSource || !selectedTarget || loading}
        className="find-path-btn"
      >
        {loading ? 'Hledám...' : 'Najít cestu'}
      </button>
    </div>
  );
}

export default SearchBar;