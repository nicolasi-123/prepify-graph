import React from 'react';

function PathResults({ pathData }) {
  if (!pathData || !pathData.found) {
    return null;
  }

  // Handle exploration mode differently
  if (pathData.exploration) {
    return (
      <div className="path-results">
        <h2>🔍 Exploration Mode</h2>
        <div className="exploration-info">
          <p><strong>Entity:</strong> {pathData.entity.name}</p>
          <p><strong>Type:</strong> {pathData.entity.type}</p>
          <p><strong>Connections:</strong> {pathData.neighbor_count}</p>
          <div className="exploration-hint">
            💡 Double-click nodes in the graph to explore their connections
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="path-results">
      <h2>Nalezené cesty ({pathData.count})</h2>

      {pathData.paths.map((pathInfo, index) => (
        <div key={index} className="path-card">
          <h3>Cesta #{index + 1} - {pathInfo.length} {pathInfo.length === 1 ? 'krok' : pathInfo.length < 5 ? 'kroky' : 'kroků'}</h3>
          
          <div className="path-steps">
            {pathInfo.details.map((step, stepIndex) => (
              <div key={stepIndex} className="step">
                <div className="step-node">
                  <span className={`node-badge ${step.type}`}>
                    {step.type === 'company' ? '🏢' : '👤'}
                  </span>
                  <div className="step-info">
                    <strong>{step.name}</strong>
                    <span className="step-type">{step.type}</span>
                  </div>
                </div>
                
                {step.relationship_to_next && (
                  <div className="step-arrow">
                    <span className="relationship-label">
                      {step.relationship_to_next}
                    </span>
                    <span className="arrow">↓</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default PathResults;