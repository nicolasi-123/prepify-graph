import React, { useState } from 'react';
import HelpTip from './HelpTip';

function calcRiskScore(pathInfo, subgraphNodes) {
  if (!pathInfo || !pathInfo.details) return { score: 0, level: 'low', insolvent: 0, foreign: 0 };

  const nodeMap = {};
  if (subgraphNodes) {
    subgraphNodes.forEach(n => {
      const d = n.data || n;
      nodeMap[d.id] = d;
    });
  }

  let insolventCount = 0;
  let foreignCount = 0;

  pathInfo.details.forEach(step => {
    // Try to find matching node in subgraph for extra data
    const nodeId = step.id || step.name;
    const nodeData = nodeMap[nodeId] || {};

    if (nodeData.insolvent || step.insolvent) insolventCount++;
    if ((nodeData.country && nodeData.country !== 'CZ') || (step.country && step.country !== 'CZ')) foreignCount++;
  });

  const score = insolventCount + foreignCount;
  const level = score === 0 ? 'low' : score <= 2 ? 'medium' : 'high';

  return { score, level, insolvent: insolventCount, foreign: foreignCount };
}

function PathResults({ pathData, subgraphNodes }) {
  const [compareMode, setCompareMode] = useState(false);

  if (!pathData || !pathData.found) {
    return null;
  }

  // Handle exploration mode differently
  if (pathData.exploration) {
    return (
      <div className="path-results">
        <h2>Exploration Mode</h2>
        <div className="exploration-info">
          <p><strong>Entity:</strong> {pathData.entity.name}</p>
          <p><strong>Type:</strong> {pathData.entity.type}</p>
          <p><strong>Connections:</strong> {pathData.neighbor_count}</p>
          <div className="exploration-hint">
            Right-click nodes in the graph to expand their connections
          </div>
        </div>
      </div>
    );
  }

  const hasMultiplePaths = pathData.paths && pathData.paths.length >= 2;

  // Find entities unique to each path for highlighting in compare mode
  const getUniqueEntities = () => {
    if (!hasMultiplePaths) return {};
    const allPathEntities = pathData.paths.map(p =>
      new Set(p.details.map(s => s.name))
    );
    const uniqueMap = {};
    pathData.paths.forEach((p, i) => {
      const otherSets = allPathEntities.filter((_, j) => j !== i);
      const uniqueToThis = new Set();
      p.details.forEach(s => {
        const inOther = otherSets.some(set => set.has(s.name));
        if (!inOther) uniqueToThis.add(s.name);
      });
      uniqueMap[i] = uniqueToThis;
    });
    return uniqueMap;
  };

  if (compareMode && hasMultiplePaths) {
    const uniqueEntities = getUniqueEntities();

    return (
      <div className="path-results">
        <div className="compare-header">
          <h2>Path Comparison</h2>
          <button className="compare-btn active" onClick={() => setCompareMode(false)}>
            Back to List
          </button>
        </div>

        <div className="comparison-container">
          {pathData.paths.map((pathInfo, index) => {
            const risk = calcRiskScore(pathInfo, subgraphNodes);
            const unique = uniqueEntities[index] || new Set();

            return (
              <div key={index} className="comparison-card">
                <div className="comparison-card-header">
                  <h4>Path #{index + 1}</h4>
                  <span className={`risk-badge ${risk.level}`}>
                    {risk.level === 'low' ? 'Low Risk' : risk.level === 'medium' ? 'Med Risk' : 'High Risk'}
                  </span>
                </div>

                <div className="comparison-stats">
                  <div className="comp-stat">
                    <span className="comp-stat-value">{pathInfo.length}</span>
                    <span className="comp-stat-label">Steps</span>
                  </div>
                  <div className="comp-stat">
                    <span className="comp-stat-value">{pathInfo.details.length}</span>
                    <span className="comp-stat-label">Entities</span>
                  </div>
                  <div className="comp-stat">
                    <span className="comp-stat-value">{risk.score}</span>
                    <span className="comp-stat-label">Risk</span>
                  </div>
                </div>

                {risk.score > 0 && (
                  <div className="risk-details">
                    {risk.insolvent > 0 && <span className="risk-tag insolvent">{risk.insolvent} insolvent</span>}
                    {risk.foreign > 0 && <span className="risk-tag foreign">{risk.foreign} foreign</span>}
                  </div>
                )}

                <div className="entity-list-compact">
                  {pathInfo.details.map((step, si) => (
                    <div key={si} className={`compact-entity ${unique.has(step.name) ? 'unique' : ''}`}>
                      <span className="compact-icon">{step.type === 'company' ? '\u{1F3E2}' : '\u{1F464}'}</span>
                      <span className="compact-name">{step.name}</span>
                      {step.relationship_to_next && (
                        <span className="compact-rel">{step.relationship_to_next}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className="path-results">
      <div className="compare-header">
        <h2>Paths Found ({pathData.count}) <HelpTip text="Risk score = count of insolvent + foreign entities in the path. Low (0), Medium (1-2), High (3+)." /></h2>
        {hasMultiplePaths && (
          <button className="compare-btn" onClick={() => setCompareMode(true)}>
            Compare Paths
          </button>
        )}
      </div>

      {pathData.paths.map((pathInfo, index) => {
        const risk = calcRiskScore(pathInfo, subgraphNodes);

        return (
          <div key={index} className="path-card">
            <div className="path-card-header">
              <h3>Path #{index + 1} - {pathInfo.length} {pathInfo.length === 1 ? 'step' : 'steps'}</h3>
              <span className={`risk-badge ${risk.level}`}>
                {risk.level === 'low' ? 'Low' : risk.level === 'medium' ? 'Med' : 'High'}
              </span>
            </div>

            <div className="path-steps">
              {pathInfo.details.map((step, stepIndex) => (
                <div key={stepIndex} className="step">
                  <div className="step-node">
                    <span className={`node-badge ${step.type}`}>
                      {step.type === 'company' ? '\u{1F3E2}' : '\u{1F464}'}
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
                      <span className="arrow">&darr;</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default PathResults;
