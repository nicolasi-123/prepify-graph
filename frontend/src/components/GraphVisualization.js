import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import cola from 'cytoscape-cola';

cytoscape.use(cola);

function GraphVisualization({ graphData, onCyReady }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
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
              if (ele.data('highlighted')) return '#f39c12';
              return ele.data('in_path') ? '#e74c3c' : '#3498db';
            },
            'label': 'data(label)',
            'width': function(ele) {
              return ele.data('in_path') ? 60 : 40;
            },
            'height': function(ele) {
              return ele.data('in_path') ? 60 : 40;
            },
            'text-valign': 'center',
            'text-halign': 'center',
            'color': '#fff',
            'text-outline-color': '#000',
            'text-outline-width': 2,
            'font-size': '12px',
            'border-width': function(ele) {
              return ele.data('in_path') ? 4 : 0;
            },
            'border-color': '#c0392b',
            'transition-property': 'background-color, border-width',
            'transition-duration': '0.3s'
          }
        },
        {
          selector: 'node[type="company"]',
          style: {
            'shape': 'rectangle'
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
              return ele.data('in_path') ? 4 : 2;
            },
            'line-color': function(ele) {
              return ele.data('in_path') ? '#e74c3c' : '#95a5a6';
            },
            'target-arrow-color': function(ele) {
              return ele.data('in_path') ? '#e74c3c' : '#95a5a6';
            },
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(type)',
            'font-size': '10px',
            'text-rotation': 'autorotate',
            'text-margin-y': -10,
            'transition-property': 'line-color, width',
            'transition-duration': '0.3s'
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

    // Click handler for permanent highlighting
    cy.on('tap', 'node', function(evt) {
      const node = evt.target;
      
      // Toggle highlighting
      const isHighlighted = node.data('highlighted');
      
      // Reset all highlights
      cy.nodes().forEach(n => n.data('highlighted', false));
      cy.edges().forEach(e => e.data('highlighted', false));
      
      if (!isHighlighted) {
        // Highlight clicked node and neighbors
        node.data('highlighted', true);
        node.neighborhood().forEach(ele => {
          ele.data('highlighted', true);
        });
        
        setSelectedNode({
          id: node.id(),
          name: node.data('label'),
          type: node.data('type')
        });
      } else {
        setSelectedNode(null);
      }
    });

    cyRef.current = cy;
    
    // Pass cy reference to parent
    if (onCyReady) {
      onCyReady(cy);
    }

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, [graphData, onCyReady]);

  const handleZoomIn = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 1.2);
    }
  };

  const handleZoomOut = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 0.8);
    }
  };

  const handleResetView = () => {
    if (cyRef.current) {
      cyRef.current.fit();
      // Clear highlights
      cyRef.current.nodes().forEach(n => n.data('highlighted', false));
      cyRef.current.edges().forEach(e => e.data('highlighted', false));
      setSelectedNode(null);
    }
  };

  if (!graphData) {
    return (
      <div className="graph-container">
        <div className="no-data">
          <p>Enter two entities and click "Find path"</p>
        </div>
      </div>
    );
  }

  return (
    <div className="graph-container">
      <div ref={containerRef} style={{ width: '100%', height: '600px', position: 'relative' }} />
      
      {/* Zoom Controls */}
      <div className="zoom-controls">
        <button onClick={handleZoomIn} title="Zoom In">➕</button>
        <button onClick={handleZoomOut} title="Zoom Out">➖</button>
        <button onClick={handleResetView} title="Reset View">🔄</button>
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
          <strong>Selected:</strong> {selectedNode.name} ({selectedNode.type})
        </div>
      )}

      {/* Legend */}
      <div className="graph-legend">
        <div className="legend-item">
          <div className="legend-node company"></div>
          <span>Company (rectangle)</span>
        </div>
        <div className="legend-item">
          <div className="legend-node person"></div>
          <span>Person (circle)</span>
        </div>
        <div className="legend-item">
          <div className="legend-edge path"></div>
          <span>Path (red)</span>
        </div>
        <div className="legend-item">
          <div className="legend-edge normal"></div>
          <span>Other (gray)</span>
        </div>
        <div className="legend-item">
          <div className="legend-node highlighted"></div>
          <span>Highlighted (orange)</span>
        </div>
      </div>
    </div>
  );
}

export default GraphVisualization;