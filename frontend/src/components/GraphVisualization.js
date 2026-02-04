import React, { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';
import cola from 'cytoscape-cola';

// Register layout
cytoscape.use(cola);

function GraphVisualization({ graphData }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);

  useEffect(() => {
    if (!graphData || !containerRef.current) return;

    // Initialize Cytoscape
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
            'border-color': '#c0392b'
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
            'text-margin-y': -10
          }
        },
        {
          selector: ':selected',
          style: {
            'background-color': '#f39c12',
            'line-color': '#f39c12',
            'target-arrow-color': '#f39c12',
            'border-width': 3,
            'border-color': '#e67e22'
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

    // Add click handler for nodes
    cy.on('tap', 'node', function(evt) {
      const node = evt.target;
      console.log('Clicked node:', node.data());
      
      // Highlight clicked node and neighbors
      cy.elements().removeClass('highlighted');
      node.addClass('highlighted');
      node.neighborhood().addClass('highlighted');
    });

    // Store reference
    cyRef.current = cy;

    // Cleanup
    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, [graphData]);

  if (!graphData) {
    return (
      <div className="graph-container">
        <div className="no-data">
          <p>Zadejte dvì entity a kliknìte na "Najít cestu"</p>
        </div>
      </div>
    );
  }

  return (
    <div className="graph-container">
      <div ref={containerRef} style={{ width: '100%', height: '600px' }} />
      <div className="graph-legend">
        <div className="legend-item">
          <div className="legend-node company"></div>
          <span>Firma (obdélník)</span>
        </div>
        <div className="legend-item">
          <div className="legend-node person"></div>
          <span>Osoba (kruh)</span>
        </div>
        <div className="legend-item">
          <div className="legend-edge path"></div>
          <span>Cesta (èervená)</span>
        </div>
        <div className="legend-item">
          <div className="legend-edge normal"></div>
          <span>Ostatní vztahy (šedá)</span>
        </div>
      </div>
    </div>
  );
}

export default GraphVisualization;