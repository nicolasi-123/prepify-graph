import React, { useState } from 'react';
import axios from 'axios';
import config from '../config';

function SearchBar({ onPathFound, cyRef }) {
  const [waypoints, setWaypoints] = useState([
    { id: 0, query: '', results: [], selected: null, showResults: false },
    { id: 1, query: '', results: [], selected: null, showResults: false }
  ]);
  const [loading, setLoading] = useState(false);
  const [maxPathLength, setMaxPathLength] = useState(5);
  const [topK, setTopK] = useState(3);
  const [excludeInsolvent, setExcludeInsolvent] = useState(false);
  const [excludeForeign, setExcludeForeign] = useState(false);
  const [excludeInactive, setExcludeInactive] = useState(false);
  const [useMultiPoint, setUseMultiPoint] = useState(false);
  const [explorationMode, setExplorationMode] = useState(false);
  const [explorationStarted, setExplorationStarted] = useState(false);
  const [targetQuery, setTargetQuery] = useState('');
  const [targetResults, setTargetResults] = useState([]);
  const [selectedTarget, setSelectedTarget] = useState(null);
  const [showTargetResults, setShowTargetResults] = useState(false);
  const [pathLoading, setPathLoading] = useState(false);

  const searchEntities = async (query, waypointId) => {
    if (query.length < 2) {
      updateWaypoint(waypointId, { results: [] });
      return;
    }

    try {
      const response = await axios.get(`${config.API_BASE_URL}/api/search`, {
        params: { q: query }
      });
      updateWaypoint(waypointId, { results: response.data.results || [] });
    } catch (error) {
      console.error('Search error:', error);
      updateWaypoint(waypointId, { results: [] });
    }
  };

  const updateWaypoint = (waypointId, updates) => {
    setWaypoints(prev => prev.map(wp =>
      wp.id === waypointId ? { ...wp, ...updates } : wp
    ));
  };

  const handleWaypointChange = (waypointId, value) => {
    updateWaypoint(waypointId, { query: value, showResults: true });
    searchEntities(value, waypointId);
  };

  const selectWaypoint = (waypointId, entity) => {
    updateWaypoint(waypointId, {
      selected: entity,
      query: `${entity.name} (${entity.id})`,
      showResults: false
    });
  };

  const addWaypoint = () => {
    if (waypoints.length < 5) {
      setWaypoints([...waypoints, {
        id: Date.now(),
        query: '',
        results: [],
        selected: null,
        showResults: false
      }]);
    }
  };

  const removeWaypoint = (waypointId) => {
    if (waypoints.length > 2) {
      setWaypoints(waypoints.filter(wp => wp.id !== waypointId));
    }
  };

const exploreEntity = async () => {
    // In exploration mode, only need first waypoint
    if (!waypoints[0].selected) {
      alert('⚠️ Please select an entity to explore');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.get(`${config.API_BASE_URL}/api/explore/${waypoints[0].selected.id}`);

      // Format response to match path format for consistency
      onPathFound({
        found: true,
        exploration: true,
        entity: response.data.entity,
        subgraph: response.data.subgraph,
        neighbor_count: response.data.neighbor_count
      });

      setExplorationStarted(true);
    } catch (error) {
      console.error('Error exploring entity:', error);
      const errorMsg = error.response?.data?.error || error.message || 'Unknown error';
      alert(`❌ Failed to load entity: ${errorMsg}\n\n💡 Tip: Make sure the entity exists in the database.`);
    } finally {
      setLoading(false);
    }
  };

  const searchTargetEntities = async (query) => {
    if (query.length < 2) {
      setTargetResults([]);
      return;
    }

    try {
      const response = await axios.get(`${config.API_BASE_URL}/api/search`, {
        params: { q: query }
      });
      setTargetResults(response.data.results || []);
    } catch (error) {
      console.error('Search error:', error);
      setTargetResults([]);
    }
  };

  const handleTargetChange = (value) => {
    setTargetQuery(value);
    setShowTargetResults(true);
    searchTargetEntities(value);
  };

  const selectTarget = (entity) => {
    setSelectedTarget(entity);
    setTargetQuery(`${entity.name} (${entity.id})`);
    setShowTargetResults(false);
  };

  const findPathInExploration = async () => {
    if (!selectedTarget) {
      alert('⚠️ Please select a target entity to find path to');
      return;
    }

    // Get visible nodes from the graph (passed via callback)
    if (!cyRef || !cyRef.current) {
      alert('❌ Graph not initialized. Please start exploration first.');
      return;
    }

    const cy = cyRef.current;
    const visibleNodes = cy.nodes().filter(n => !n.data('dimmed')).map(n => n.id());

    if (visibleNodes.length === 0) {
      alert('⚠️ No visible nodes found.\n\n💡 Double-click nodes in the graph to expand and show connections first.');
      return;
    }

    setPathLoading(true);
    try {
      // Find shortest path from any visible node to target
      let shortestPath = null;
      let shortestLength = Infinity;
      let bestSourceId = null;

      for (const sourceId of visibleNodes) {
        try {
          const response = await axios.post(`${config.API_BASE_URL}/api/top-paths`, {
            source: sourceId,
            target: selectedTarget.id,
            k: 1,
            exclude_insolvent: false,
            exclude_foreign: false,
            exclude_inactive: false
          });

          if (response.data.found && response.data.paths.length > 0) {
            const pathLength = response.data.paths[0].length;
            if (pathLength < shortestLength) {
              shortestLength = pathLength;
              shortestPath = response.data;
              bestSourceId = sourceId;
            }
          }
        } catch (error) {
          // Continue to next source
          continue;
        }
      }

      if (shortestPath) {
        // Merge this path with existing graph without destroying it
        onPathFound({
          found: true,
          exploration: true,
          preserveGraph: true,
          pathHighlight: shortestPath.paths[0],
          entity: { id: bestSourceId, name: 'Path Search' },
          subgraph: shortestPath.subgraph,
          neighbor_count: 0,
          pathFrom: bestSourceId,
          pathTo: selectedTarget.id
        });

        const sourceNode = cy.nodes(`#${bestSourceId}`);
        const sourceName = sourceNode.length > 0 ? sourceNode.data('label') : bestSourceId;
        alert(`✅ Path found!\n\nFrom: ${sourceName}\nTo: ${selectedTarget.name}\nLength: ${shortestLength} steps\n\nThe path is now highlighted in red on the graph.`);
      } else {
        alert(`🔍 No path found from any visible node to ${selectedTarget.name}\n\n💡 Tips:\n• Try expanding more nodes to increase coverage\n• The target might be in a different network component\n• Check if there are any connections at all`);
      }
    } catch (error) {
      console.error('Error finding path:', error);
      const errorMsg = error.response?.data?.error || error.message || 'Unknown error';
      alert(`❌ Error during path search: ${errorMsg}`);
    } finally {
      setPathLoading(false);
    }
  };

const findPath = async () => {
    // Check that all waypoints are selected
    const allSelected = waypoints.every(wp => wp.selected);
    if (!allSelected) {
      alert('⚠️ Please select all waypoints before searching');
      return;
    }

    setLoading(true);
    try {
      let response;

      if (useMultiPoint && waypoints.length > 2) {
        // Multi-point routing
        response = await axios.post(`${config.API_BASE_URL}/api/multi-path`, {
          waypoints: waypoints.map(wp => wp.selected.id),
          exclude_insolvent: excludeInsolvent,
          exclude_foreign: excludeForeign,
          exclude_inactive: excludeInactive
        });

        // Convert single path response to match top-paths format
        if (response.data.found) {
          response.data.paths = [{
            path: response.data.path,
            length: response.data.path_length,
            details: response.data.details
          }];
          response.data.count = 1;
        }
      } else {
        // Standard 2-point routing with top K paths
        response = await axios.post(`${config.API_BASE_URL}/api/top-paths`, {
          source: waypoints[0].selected.id,
          target: waypoints[1].selected.id,
          k: topK,
          exclude_insolvent: excludeInsolvent,
          exclude_foreign: excludeForeign,
          exclude_inactive: excludeInactive
        });

        // Filter paths by max length if set
        if (response.data.paths) {
          response.data.paths = response.data.paths.filter(
            path => path.length <= maxPathLength
          );
          response.data.count = response.data.paths.length;
        }
      }

      // Handle no path found
      if (!response.data.found || (response.data.paths && response.data.paths.length === 0)) {
        const message = response.data.message || 'No connection found';
        alert(`🔍 ${message}\n\n💡 Tips:\n• Try removing some filters\n• Check if entities are in the same network\n• Increase max path length`);
        return;
      }

      onPathFound(response.data);
    } catch (error) {
      console.error('Error finding path:', error);
      const errorMsg = error.response?.data?.error || error.message || 'Unknown error';
      alert(`❌ Failed to find path: ${errorMsg}\n\n💡 Make sure both entities exist in the database.`);
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

      {/* Mode Selection */}
      <div className="mode-toggles">
        <div className="multi-point-toggle">
          <label>
            <input
              type="checkbox"
              checked={explorationMode}
              onChange={(e) => {
                setExplorationMode(e.target.checked);
                if (e.target.checked) {
                  setUseMultiPoint(false);
                }
              }}
            />
            <span>🔍 Exploration Mode (search single entity, manually explore)</span>
          </label>
        </div>

        {!explorationMode && (
          <div className="multi-point-toggle">
            <label>
              <input
                type="checkbox"
                checked={useMultiPoint}
                onChange={(e) => setUseMultiPoint(e.target.checked)}
              />
              <span>Enable multi-point routing (3+ waypoints)</span>
            </label>
          </div>
        )}
      </div>

      {/* Waypoints */}
      <div className="waypoints-container">
        {waypoints.map((waypoint, index) => {
          // In exploration mode, only show first waypoint
          if (explorationMode && index > 0) return null;

          return (
          <div key={waypoint.id} className="search-box waypoint-box">
            <label>
              {explorationMode
                ? 'Entity to explore:'
                : index === 0 ? 'Start' : index === waypoints.length - 1 ? 'End' : `Waypoint ${index}`}:
            </label>
            <div className="waypoint-input-group">
              <input
                type="text"
                value={waypoint.query}
                onChange={(e) => handleWaypointChange(waypoint.id, e.target.value)}
                onFocus={() => waypoint.query && updateWaypoint(waypoint.id, { showResults: true })}
                placeholder="Start typing name or ID..."
              />
              {waypoints.length > 2 && (
                <button
                  className="remove-waypoint-btn"
                  onClick={() => removeWaypoint(waypoint.id)}
                  title="Remove waypoint"
                >
                  ✕
                </button>
              )}
            </div>
            {waypoint.showResults && waypoint.results.length > 0 && (
              <div className="results-dropdown">
                {waypoint.results.map((entity) => (
                  <div
                    key={entity.id}
                    className="result-item"
                    onClick={() => selectWaypoint(waypoint.id, entity)}
                  >
                    {renderEntityResult(entity)}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
        })}
      </div>

      {/* Add waypoint button */}
      {!explorationMode && useMultiPoint && waypoints.length < 5 && (
        <button className="add-waypoint-btn" onClick={addWaypoint}>
          + Add waypoint
        </button>
      )}

{/* Advanced Filters */}
      {!explorationMode && (
        <div className="search-filters">
          {!useMultiPoint && (
            <>
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
            </>
          )}

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

          <div className="filter-group checkbox-filter">
            <label>
              <input
                type="checkbox"
                checked={excludeInactive}
                onChange={(e) => setExcludeInactive(e.target.checked)}
              />
              <span>Show only active relationships ⏱️</span>
            </label>
          </div>
        </div>
      )}

      <button
        onClick={explorationMode ? exploreEntity : findPath}
        disabled={explorationMode ? !waypoints[0].selected || loading : !waypoints.every(wp => wp.selected) || loading}
        className="find-path-btn"
      >
        {loading ? (
          <>
            <span className="loading-spinner"></span>
            Searching...
          </>
        ) : explorationMode ? '🔍 Explore Entity' : useMultiPoint && waypoints.length > 2 ? 'Find Multi-Point Path' : 'Find Path'}
      </button>

      {/* Selected entities display */}
      {waypoints.some(wp => wp.selected) && (
        <div className="selected-entities">
          {waypoints.map((waypoint, index) => waypoint.selected && (
            <div key={waypoint.id} className="selected-entity">
              <span className="label">
                {index === 0 ? 'Start:' : index === waypoints.length - 1 ? 'End:' : `Point ${index}:`}
              </span>
              <span className="value">{waypoint.selected.name}</span>
              <span className="id">({waypoint.selected.id})</span>
            </div>
          ))}
        </div>
      )}

      {/* Path finding within exploration mode */}
      {explorationMode && explorationStarted && (
        <div className="exploration-path-search">
          <h3>🎯 Find Path to Node</h3>
          <p className="exploration-path-hint">
            Search for a target entity and find the shortest path from any currently visible node
          </p>

          <div className="search-box">
            <label>Target entity:</label>
            <input
              type="text"
              value={targetQuery}
              onChange={(e) => handleTargetChange(e.target.value)}
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

          <button
            onClick={findPathInExploration}
            disabled={!selectedTarget || pathLoading}
            className="find-path-btn exploration-path-btn"
          >
            {pathLoading ? (
              <>
                <span className="loading-spinner"></span>
                Searching paths...
              </>
            ) : '🔍 Find Path from Visible Nodes'}
          </button>

          {selectedTarget && (
            <div className="selected-target-display">
              <strong>Target:</strong> {selectedTarget.name} ({selectedTarget.id})
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default SearchBar;