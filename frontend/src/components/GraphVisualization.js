import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import cola from 'cytoscape-cola';
import axios from 'axios';
import config from '../config';

cytoscape.use(cola);

function truncateLabel(label, max = 18) {
  if (!label || label.length <= max) return label;
  return label.substring(0, max - 1) + '\u2026';
}

function GraphVisualization({ graphData, onCyReady }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [expandedNode, setExpandedNode] = useState(null);
  const [tooltip, setTooltip] = useState({ visible: false, x: 0, y: 0, content: '' });

  useEffect(() => {
    if (!graphData || !containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,

      elements: {
        nodes: graphData.nodes || [],
        edges: graphData.edges || []
      },

      style: [
        {
          selector: 'node',
          style: {
            'background-color': function(ele) {
              const data = ele.data();
              if (data.highlighted) return '#f39c12';
              if (data.insolvent) return '#c0392b';
              if (data.country && data.country !== 'CZ') return '#9b59b6';
              if (data.in_path) return '#e74c3c';
              return '#3498db';
            },
            'label': function(ele) {
              return truncateLabel(ele.data('label'));
            },
            'width': function(ele) {
              return ele.data('in_path') ? 56 : 40;
            },
            'height': function(ele) {
              return ele.data('in_path') ? 56 : 40;
            },
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-margin-y': 8,
            'color': '#2d3748',
            'text-outline-color': '#fff',
            'text-outline-width': 2,
            'font-size': '11px',
            'font-family': 'Inter, -apple-system, sans-serif',
            'border-width': function(ele) {
              const data = ele.data();
              if (data.insolvent) return 4;
              if (data.in_path) return 3;
              if (data.expanded) return 3;
              return 0;
            },
            'border-color': function(ele) {
              if (ele.data('expanded')) return '#f39c12';
              return ele.data('insolvent') ? '#e74c3c' : '#c0392b';
            },
            'border-style': function(ele) {
              return ele.data('insolvent') ? 'double' : 'solid';
            },
            'opacity': function(ele) {
              return ele.data('dimmed') ? 0.15 : 1;
            },
            'cursor': 'pointer',
            'transition-property': 'background-color, border-width, opacity, width, height',
            'transition-duration': '0.5s',
            'transition-timing-function': 'ease-in-out-sine'
          }
        },
        {
          selector: 'node[type="company"]',
          style: {
            'shape': 'round-rectangle',
            'border-width': function(ele) {
              const data = ele.data();
              if (data.insolvent) return 4;
              if (data.in_path) return 3;
              if (data.expanded) return 3;
              return 2;
            },
            'border-color': function(ele) {
              const data = ele.data();
              if (data.expanded) return '#f39c12';
              if (data.insolvent) return '#e74c3c';
              if (data.in_path) return '#c0392b';
              return 'rgba(52, 152, 219, 0.3)';
            }
          }
        },
        {
          selector: 'node[type="person"]',
          style: {
            'shape': 'ellipse'
          }
        },
        {
          selector: 'edge',
          style: {
            'width': function(ele) {
              return ele.data('in_path') ? 4 : 1.5;
            },
            'line-color': function(ele) {
              return ele.data('in_path') ? '#e74c3c' : '#cbd5e0';
            },
            'target-arrow-color': function(ele) {
              return ele.data('in_path') ? '#e74c3c' : '#cbd5e0';
            },
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'line-style': function(ele) {
              return ele.data('active') === false ? 'dashed' : 'solid';
            },
            'opacity': function(ele) {
              if (ele.data('dimmed')) return 0.08;
              return ele.data('active') === false ? 0.4 : 0.7;
            },
            'label': 'data(type)',
            'font-size': '9px',
            'font-family': 'Inter, -apple-system, sans-serif',
            'color': '#a0aec0',
            'text-outline-color': '#fff',
            'text-outline-width': 1.5,
            'text-rotation': 'autorotate',
            'text-margin-y': -10,
            'transition-property': 'line-color, width, opacity',
            'transition-duration': '0.5s',
            'transition-timing-function': 'ease-in-out-sine'
          }
        }
      ],

      layout: {
        name: 'cola',
        animate: true,
        randomize: false,
        maxSimulationTime: 2000,
        nodeSpacing: function() { return 50; },
        edgeLength: 150,
        padding: 50
      },

      minZoom: 0.3,
      maxZoom: 3,
      wheelSensitivity: 0.2
    });

    // Tooltip handlers
    cy.on('mouseover', 'node', function(evt) {
      const node = evt.target;
      const nodeData = node.data();
      const position = evt.renderedPosition;

      let content = `<strong>${nodeData.label}</strong><br/>`;
      content += `Type: ${nodeData.type}<br/>`;
      content += `ID: ${node.id()}<br/>`;

      if (nodeData.city) {
        content += `City: ${nodeData.city}<br/>`;
      }

      const country = nodeData.country || 'CZ';
      const countryNames = {
        'CZ': 'Czech Republic',
        'CY': 'Cyprus',
        'NL': 'Netherlands'
      };
      content += `Country: ${countryNames[country] || country}<br/>`;

      if (nodeData.insolvent === true) {
        content += `<span style="color: #fc8181; font-weight: bold;">INSOLVENT</span><br/>`;
      }

      content += `Connections: ${node.degree()}`;

      setTooltip({
        visible: true,
        x: position.x,
        y: position.y,
        content: content
      });
    });

    cy.on('mouseout', 'node', function() {
      setTooltip({ visible: false, x: 0, y: 0, content: '' });
    });

    // Double-tap handler for expansion mode with dynamic loading
    cy.on('dbltap', 'node', async function(evt) {
      const node = evt.target;
      const nodeId = node.id();

      const isExpanded = node.data('expanded');
      const isLoaded = node.data('neighbors_loaded');

      if (!isLoaded && !isExpanded) {
        try {
          const visibleNodeIds = cy.nodes().map(n => n.id()).join(',');

          const response = await axios.get(`${config.API_BASE_URL}/api/explore/${nodeId}`, {
            params: { existing_nodes: visibleNodeIds }
          });

          const newNodes = response.data.subgraph.nodes;
          const newEdges = response.data.subgraph.edges;

          const existingNodeIds = new Set(cy.nodes().map(n => n.id()));
          const nodesToAdd = newNodes.filter(n => !existingNodeIds.has(n.data.id));

          if (nodesToAdd.length > 0 || newEdges.length > 0) {
            cy.nodes().lock();

            cy.add(nodesToAdd);
            cy.add(newEdges);

            cy.layout({
              name: 'cola',
              animate: true,
              randomize: false,
              maxSimulationTime: 1000,
              nodeSpacing: function() { return 50; },
              edgeLength: 150,
              padding: 50,
              fit: false
            }).run();

            setTimeout(() => {
              cy.nodes().unlock();
            }, 1100);
          }

          node.data('neighbors_loaded', true);

        } catch (error) {
          console.error('Error loading neighbors:', error);
          return;
        }
      }

      if (isExpanded) {
        node.data('expanded', false);

        const expandedNodes = cy.nodes().filter(n => n.data('expanded'));

        if (expandedNodes.length === 0) {
          cy.nodes().forEach(n => n.data('dimmed', false));
          cy.edges().forEach(e => e.data('dimmed', false));
          setExpandedNode(null);
          setSelectedNode(null);
        } else {
          const visibleNodes = new Set();
          const visibleEdges = new Set();

          expandedNodes.forEach(expNode => {
            visibleNodes.add(expNode.id());
            expNode.neighborhood().nodes().forEach(n => visibleNodes.add(n.id()));
            expNode.neighborhood().edges().forEach(e => visibleEdges.add(e.id()));
          });

          cy.nodes().forEach(n => {
            n.data('dimmed', !visibleNodes.has(n.id()));
          });
          cy.edges().forEach(e => {
            e.data('dimmed', !visibleEdges.has(e.id()));
          });

          const firstExpanded = expandedNodes[0];
          setExpandedNode(firstExpanded.id());
          setSelectedNode({
            id: firstExpanded.id(),
            name: firstExpanded.data('label'),
            type: firstExpanded.data('type'),
            connections: firstExpanded.neighborhood().nodes().length
          });
        }
      } else {
        const neighbors = node.neighborhood();
        const neighborNodes = neighbors.nodes();
        const neighborEdges = neighbors.edges();

        const alreadyExpandedNodes = cy.nodes().filter(n => n.data('expanded'));

        if (alreadyExpandedNodes.length === 0) {
          cy.nodes().forEach(n => n.data('dimmed', true));
          cy.edges().forEach(e => e.data('dimmed', true));
        }

        node.data('expanded', true);
        node.data('dimmed', false);

        neighborNodes.forEach(n => {
          n.data('dimmed', false);
        });

        neighborEdges.forEach(e => {
          e.data('dimmed', false);
        });

        setExpandedNode(nodeId);
        setSelectedNode({
          id: nodeId,
          name: node.data('label'),
          type: node.data('type'),
          connections: neighborNodes.length
        });
      }
    });

    // Store reference
    cyRef.current = cy;

    if (typeof window !== 'undefined') {
      window.cy = cy;
    }

    if (onCyReady) {
      onCyReady(cy);
    }

    return () => {
      if (cyRef.current) {
        try {
          cyRef.current.removeAllListeners();
          cyRef.current.destroy();
          cyRef.current = null;
        } catch (e) {
          // Cleanup error - safe to ignore
        }
      }
    };
  }, [graphData, onCyReady]);

  const animateZoom = (targetZoom) => {
    if (!cyRef.current) return;
    cyRef.current.animate({
      zoom: {
        level: targetZoom,
        renderedPosition: { x: cyRef.current.width() / 2, y: cyRef.current.height() / 2 }
      }
    }, { duration: 250, easing: 'ease-in-out-sine' });
  };

  const handleZoomIn = () => {
    if (cyRef.current) {
      animateZoom(cyRef.current.zoom() * 1.3);
    }
  };

  const handleZoomOut = () => {
    if (cyRef.current) {
      animateZoom(cyRef.current.zoom() * 0.7);
    }
  };

  const handleResetView = () => {
    if (cyRef.current) {
      cyRef.current.animate({ fit: { padding: 50 } }, { duration: 400, easing: 'ease-in-out-sine' });
      cyRef.current.nodes().forEach(n => {
        n.data('expanded', false);
        n.data('dimmed', false);
        n.data('highlighted', false);
      });
      cyRef.current.edges().forEach(e => {
        e.data('dimmed', false);
        e.data('highlighted', false);
      });
      setSelectedNode(null);
      setExpandedNode(null);
    }
  };

  const handleResetExpansion = () => {
    if (cyRef.current) {
      cyRef.current.nodes().forEach(n => {
        n.data('expanded', false);
        n.data('dimmed', false);
      });
      cyRef.current.edges().forEach(e => {
        e.data('dimmed', false);
      });
      setSelectedNode(null);
      setExpandedNode(null);
    }
  };

  if (!graphData) {
    return (
      <div className="graph-container">
        <div className="no-data">
          <svg width="80" height="80" viewBox="0 0 80 80" fill="none" style={{ marginBottom: 20 }}>
            <circle cx="24" cy="24" r="10" fill="#667eea" opacity="0.6"/>
            <circle cx="56" cy="24" r="7" fill="#764ba2" opacity="0.5"/>
            <circle cx="40" cy="58" r="9" fill="#667eea" opacity="0.55"/>
            <line x1="32" y1="28" x2="50" y2="24" stroke="#cbd5e0" strokeWidth="2"/>
            <line x1="28" y1="32" x2="36" y2="50" stroke="#cbd5e0" strokeWidth="2"/>
            <line x1="52" y1="30" x2="44" y2="50" stroke="#cbd5e0" strokeWidth="2"/>
            <circle cx="24" cy="24" r="10" stroke="#667eea" strokeWidth="2" fill="none" opacity="0.3"/>
            <circle cx="56" cy="24" r="7" stroke="#764ba2" strokeWidth="2" fill="none" opacity="0.3"/>
            <circle cx="40" cy="58" r="9" stroke="#667eea" strokeWidth="2" fill="none" opacity="0.3"/>
          </svg>
          <h3>No Graph Data Yet</h3>
          <p>Search for entities and find connections to visualize the relationship graph</p>

          <div className="no-data-tips">
            <h4>Get Started:</h4>
            <ul>
              <li>Search for a company or person using the search bar above</li>
              <li>Select two entities to find the shortest path between them</li>
              <li>Use Exploration Mode to manually browse connections</li>
              <li>Use filters to refine your search</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="graph-container">
      <div
        ref={containerRef}
        className="graph-canvas"
        style={{ width: '100%', height: '600px', position: 'relative' }}
      />

      {/* Zoom Controls */}
      <div className="zoom-controls">
        <button onClick={handleZoomIn} title="Zoom In">+</button>
        <button onClick={handleZoomOut} title="Zoom Out">&minus;</button>
        <button onClick={handleResetView} title="Reset View">&#8634;</button>
        {expandedNode && (
          <button onClick={handleResetExpansion} title="Reset Expansion" className="reset-expansion">
            &#8617;
          </button>
        )}
      </div>

      {/* Tooltip */}
      {tooltip.visible && (
        <div
          className="graph-tooltip"
          style={{
            position: 'absolute',
            left: tooltip.x + 10,
            top: tooltip.y + 10,
            pointerEvents: 'none'
          }}
          dangerouslySetInnerHTML={{ __html: tooltip.content }}
        />
      )}

      {/* Selected Node Info */}
      {selectedNode && (
        <div className="selected-node-info">
          <strong>{expandedNode ? 'Expanded:' : 'Selected:'}</strong> {selectedNode.name} ({selectedNode.type})
          {selectedNode.connections !== undefined && (
            <span className="connection-count"> &middot; {selectedNode.connections} connections</span>
          )}
          {expandedNode && (
            <span className="expand-hint"> &middot; Double-click again to collapse</span>
          )}
        </div>
      )}

      {/* Exploration Hint */}
      {graphData && !expandedNode && (
        <div className="exploration-hint">
          Tip: Double-click any node to explore its connections
        </div>
      )}

      {/* Legend */}
      <div className="graph-legend">
        <div className="legend-item">
          <div className="legend-node company"></div>
          <span>Company</span>
        </div>
        <div className="legend-item">
          <div className="legend-node person"></div>
          <span>Person</span>
        </div>
        <div className="legend-item">
          <div className="legend-node insolvent"></div>
          <span>Insolvent</span>
        </div>
        <div className="legend-item">
          <div className="legend-node foreign"></div>
          <span>Foreign</span>
        </div>
        <div className="legend-item">
          <div className="legend-edge path"></div>
          <span>Path</span>
        </div>
        <div className="legend-item">
          <div className="legend-edge inactive"></div>
          <span>Historical</span>
        </div>
      </div>
    </div>
  );
}

export default GraphVisualization;
