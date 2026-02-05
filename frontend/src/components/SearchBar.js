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
  const [maxPathLength, setMaxPathLength] = useState(5);
  const [topK, setTopK] = useState(3);
  const [excludeInsolvent, setExcludeInsolvent] = useState(false);
  const [excludeForeign, setExcludeForeign] = useState(false);

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
    setSourceQuery(`${entity.name} (${entity.id})`);
    setShowSourceResults(false);
  };

  const selectTarget = (entity) => {
    setSelectedTarget(entity);
    setTargetQuery(`${entity.name} (${entity.id})`);
    setShowTargetResults(false);
  };

const findPath = async () => {
    if (!selectedSource || !selectedTarget) {
      alert('Please select both entities');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${config.API_BASE_URL}/api/top-paths`, {
        source: selectedSource.id,
        target: selectedTarget.id,
        k: topK,
        exclude_insolvent: excludeInsolvent,
        exclude_foreign: excludeForeign
      });

      // Filter paths by max length if set
      if (response.data.paths) {
        response.data.paths = response.data.paths.filter(
          path => path.length <= maxPathLength
        );
        response.data.count = response.data.paths.length;
      }

      onPathFound(response.data);
    } catch (error) {
      console.error('Error finding path:', error);
      alert('Error finding path');
    } finally {
      setLoading(false);
    }
  };

  const renderEntityResult = (entity) => {
    // Show entity with ID and type for disambiguation
    return (
      <div className="result-item-content">
        <div className="result-main">
          <strong>{entity.name}</strong>
          <span className="entity-id">ID: {entity.id}</span>
        </div>
        <span className={`entity-type ${entity.type}`}>
          {entity.type === 'company' ? '🏢 Company' : '👤 Person'}
        </span>
      </div>
    );
  };

  return (
    <div className="search-container">
      <h1>Prepify Graph - Relationship Visualization</h1>
      <p className="subtitle">Find the shortest path between companies and people</p>

      <div className="search-boxes">
        <div className="search-box">
          <label>From (person/company):</label>
          <input
            type="text"
            value={sourceQuery}
            onChange={handleSourceChange}
            onFocus={() => sourceQuery && setShowSourceResults(true)}
            placeholder="Start typing name or ID..."
          />
          {showSourceResults && sourceResults.length > 0 && (
            <div className="results-dropdown">
              {sourceResults.map((entity) => (
                <div
                  key={entity.id}
                  className="result-item"
                  onClick={() => selectSource(entity)}
                >
                  {renderEntityResult(entity)}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="search-box">
          <label>To (person/company):</label>
          <input
            type="text"
            value={targetQuery}
            onChange={handleTargetChange}
            onFocus={() => targetQuery && setShowTargetResults(true)}
            placeholder="Start typing name or ID..."
          />
          {showTargetResults && targetResults.length > 0 && (
            <div className="results-dropdown">
              {targetResults.map((entity) => (
                <div
                  key={entity.id}
                  className="result-item"
                  onClick={() => selectTarget(entity)}
                >
                  {renderEntityResult(entity)}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

{/* Advanced Filters */}
      <div className="search-filters">
        <div className="filter-group">
          <label>Max path length:</label>
          <select value={maxPathLength} onChange={(e) => setMaxPathLength(Number(e.target.value))}>
            <option value={3}>3 steps</option>
            <option value={4}>4 steps</option>
            <option value={5}>5 steps</option>
            <option value={10}>10 steps</option>
            <option value={999}>No limit</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Number of paths:</label>
          <select value={topK} onChange={(e) => setTopK(Number(e.target.value))}>
            <option value={1}>1 path</option>
            <option value={3}>Top 3 paths</option>
            <option value={5}>Top 5 paths</option>
          </select>
        </div>

        <div className="filter-group checkbox-filter">
          <label>
            <input 
              type="checkbox" 
              checked={excludeInsolvent}
              onChange={(e) => setExcludeInsolvent(e.target.checked)}
            />
            <span>Exclude insolvent entities ⚠️</span>
          </label>
        </div>

        <div className="filter-group checkbox-filter">
          <label>
            <input 
              type="checkbox" 
              checked={excludeForeign}
              onChange={(e) => setExcludeForeign(e.target.checked)}
            />
            <span>Exclude foreign entities 🌍</span>
          </label>
        </div>
      </div>

      <button
        onClick={findPath}
        disabled={!selectedSource || !selectedTarget || loading}
        className="find-path-btn"
      >
        {loading ? 'Searching...' : 'Find Path'}
      </button>

      {/* Selected entities display */}
      {(selectedSource || selectedTarget) && (
        <div className="selected-entities">
          {selectedSource && (
            <div className="selected-entity">
              <span className="label">From:</span>
              <span className="value">{selectedSource.name}</span>
              <span className="id">({selectedSource.id})</span>
            </div>
          )}
          {selectedTarget && (
            <div className="selected-entity">
              <span className="label">To:</span>
              <span className="value">{selectedTarget.name}</span>
              <span className="id">({selectedTarget.id})</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default SearchBar;