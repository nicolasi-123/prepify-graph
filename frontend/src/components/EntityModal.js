import React, { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';

const countryNames = {
  'CZ': 'Czech Republic',
  'CY': 'Cyprus',
  'NL': 'Netherlands'
};

function EntityModal({ entity, neighbors, onClose, onFindPaths }) {
  const miniGraphRef = useRef(null);
  const miniCyRef = useRef(null);

  useEffect(() => {
    if (!miniGraphRef.current || !entity || !neighbors || neighbors.length === 0) return;

    const nodes = [
      { data: { id: entity.id, label: entity.label || entity.id, type: entity.type } }
    ];
    const edges = [];

    neighbors.forEach(n => {
      nodes.push({
        data: { id: n.id, label: n.label || n.id, type: n.type }
      });
      edges.push({
        data: {
          id: `${entity.id}-${n.id}`,
          source: entity.id,
          target: n.id,
          type: n.edgeType || ''
        }
      });
    });

    const cy = cytoscape({
      container: miniGraphRef.current,
      elements: { nodes, edges },
      style: [
        {
          selector: 'node',
          style: {
            'background-color': function(ele) {
              if (ele.id() === entity.id) return '#667eea';
              return ele.data('type') === 'company' ? '#3498db' : '#e74c3c';
            },
            'label': function(ele) {
              const l = ele.data('label') || '';
              return l.length > 14 ? l.substring(0, 13) + '\u2026' : l;
            },
            'width': function(ele) { return ele.id() === entity.id ? 36 : 28; },
            'height': function(ele) { return ele.id() === entity.id ? 36 : 28; },
            'text-valign': 'bottom',
            'text-margin-y': 6,
            'font-size': '9px',
            'font-family': 'Inter, -apple-system, sans-serif',
            'color': '#4a5568',
            'text-outline-color': '#fff',
            'text-outline-width': 1.5,
            'shape': function(ele) {
              return ele.data('type') === 'company' ? 'round-rectangle' : 'ellipse';
            }
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 1.5,
            'line-color': '#cbd5e0',
            'target-arrow-color': '#cbd5e0',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'opacity': 0.6
          }
        }
      ],
      layout: {
        name: 'cose',
        animate: false,
        padding: 20,
        nodeRepulsion: 8000,
        idealEdgeLength: 80
      },
      userZoomingEnabled: false,
      userPanningEnabled: false,
      boxSelectionEnabled: false
    });

    miniCyRef.current = cy;

    return () => {
      if (miniCyRef.current) {
        try {
          miniCyRef.current.destroy();
          miniCyRef.current = null;
        } catch (e) {
          // safe to ignore
        }
      }
    };
  }, [entity, neighbors]);

  if (!entity) return null;

  const country = entity.country || 'CZ';

  // Group neighbors by relationship type
  const grouped = {};
  (neighbors || []).forEach(n => {
    const key = n.edgeType || 'connection';
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(n);
  });

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-row">
            <span className={`modal-type-badge ${entity.type}`}>
              {entity.type === 'company' ? '\u{1F3E2}' : '\u{1F464}'}
            </span>
            <div>
              <h2 className="modal-name">{entity.label || entity.id}</h2>
              <span className="modal-type-label">{entity.type}</span>
            </div>
          </div>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-details-grid">
          <div className="detail-item">
            <span className="detail-label">ID</span>
            <span className="detail-value mono">{entity.id}</span>
          </div>
          {entity.city && (
            <div className="detail-item">
              <span className="detail-label">City</span>
              <span className="detail-value">{entity.city}</span>
            </div>
          )}
          <div className="detail-item">
            <span className="detail-label">Country</span>
            <span className="detail-value">{countryNames[country] || country}</span>
          </div>
          {entity.insolvent && (
            <div className="detail-item warning">
              <span className="detail-label">Status</span>
              <span className="detail-value insolvent-status">INSOLVENT</span>
            </div>
          )}
        </div>

        {/* Mini graph */}
        {neighbors && neighbors.length > 0 && (
          <div className="modal-mini-graph-section">
            <h3>Network ({neighbors.length} connections)</h3>
            <div className="modal-mini-graph" ref={miniGraphRef} />
          </div>
        )}

        {/* Connections list grouped by type */}
        <div className="modal-connections">
          <h3>Connections</h3>
          {Object.keys(grouped).length === 0 ? (
            <p className="no-connections">No direct connections found</p>
          ) : (
            Object.entries(grouped).map(([relType, items]) => (
              <div key={relType} className="connection-group">
                <div className="connection-group-header">{relType}</div>
                {items.map((n, i) => (
                  <div key={i} className="connection-item">
                    <span className="connection-icon">
                      {n.type === 'company' ? '\u{1F3E2}' : '\u{1F464}'}
                    </span>
                    <span className="connection-name">{n.label || n.id}</span>
                    {n.edgeActive === false && (
                      <span className="connection-inactive">historical</span>
                    )}
                  </div>
                ))}
              </div>
            ))
          )}
        </div>

        {/* Action button */}
        <button className="modal-action-btn" onClick={() => onFindPaths(entity)}>
          Find Paths From Here
        </button>
      </div>
    </div>
  );
}

export default EntityModal;
