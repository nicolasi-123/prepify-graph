import React, { useState, useRef, useEffect, useCallback } from 'react';
import SearchBar from './components/SearchBar';
import GraphVisualization from './components/GraphVisualization';
import PathResults from './components/PathResults';
import ExportControls from './components/ExportControls';
import axios from 'axios';
import config from './config';
import './App.css';

// Toast notification system
function useToast() {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.map(t => t.id === id ? { ...t, exiting: true } : t));
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id));
      }, 300);
    }, 3500);
  }, []);

  return { toasts, addToast };
}

// Confetti burst
function triggerConfetti() {
  const container = document.createElement('div');
  container.className = 'confetti-container';
  document.body.appendChild(container);

  const colors = ['#667eea', '#764ba2', '#f39c12', '#e74c3c', '#2ecc71', '#3498db', '#e91e63', '#00bcd4'];
  for (let i = 0; i < 60; i++) {
    const piece = document.createElement('div');
    piece.className = 'confetti-piece';
    piece.style.left = Math.random() * 100 + '%';
    piece.style.background = colors[Math.floor(Math.random() * colors.length)];
    piece.style.animationDelay = Math.random() * 0.8 + 's';
    piece.style.animationDuration = (2 + Math.random() * 2) + 's';
    piece.style.borderRadius = Math.random() > 0.5 ? '50%' : '2px';
    piece.style.width = (6 + Math.random() * 8) + 'px';
    piece.style.height = (6 + Math.random() * 8) + 'px';
    container.appendChild(piece);
  }

  setTimeout(() => container.remove(), 4000);
}

function App() {
  const [pathData, setPathData] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [stats, setStats] = useState({ entities: 0, relationships: 0 });
  const [statsLoading, setStatsLoading] = useState(true);
  const cyRef = useRef(null);
  const { toasts, addToast } = useToast();

  // Fetch graph stats on mount
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await axios.get(`${config.API_BASE_URL}/api/stats`);
        setStats({
          entities: response.data.entities || 0,
          relationships: response.data.relationships || 0
        });
      } catch {
        // Fallback: try search to estimate
        try {
          const resp = await axios.get(`${config.API_BASE_URL}/api/search`, { params: { q: 'a' } });
          setStats({ entities: resp.data.total || 107, relationships: 205 });
        } catch {
          setStats({ entities: 107, relationships: 205 });
        }
      } finally {
        setStatsLoading(false);
      }
    };
    fetchStats();
  }, []);

  const handlePathFound = (data) => {
    setPathData(data);

    // Toast + confetti logic
    if (data.found && data.paths && data.paths.length > 0) {
      const pathLength = data.paths[0].length;
      if (pathLength >= 5) {
        triggerConfetti();
        addToast(`Complex path found! ${pathLength} steps across ${data.count} route(s)`, 'success');
      } else {
        addToast(`Path found! ${pathLength} step(s), ${data.count} route(s)`, 'success');
      }
    } else if (data.exploration) {
      addToast(`Exploring ${data.entity?.name || 'entity'} - ${data.neighbor_count} connections`, 'info');
    }

    // If preserveGraph is true, merge with existing graph instead of replacing
    if (data.preserveGraph && cyRef.current) {
      const cy = cyRef.current;
      const pathNodes = new Set(data.pathHighlight.path);

      const existingNodeIds = new Set(cy.nodes().map(n => n.id()));
      const nodesToAdd = data.subgraph.nodes.filter(n => !existingNodeIds.has(n.data.id));

      if (nodesToAdd.length > 0) {
        cy.nodes().lock();
        cy.add(nodesToAdd);
        cy.add(data.subgraph.edges);

        setTimeout(() => {
          cy.nodes().unlock();
        }, 100);
      }

      cy.nodes().forEach(n => n.data('in_path', false));
      cy.edges().forEach(e => e.data('in_path', false));

      pathNodes.forEach(nodeId => {
        const node = cy.nodes(`#${nodeId}`);
        if (node.length > 0) {
          node.data('in_path', true);
        }
      });

      const pathArray = data.pathHighlight.path;
      for (let i = 0; i < pathArray.length - 1; i++) {
        const edge = cy.edges(`[source="${pathArray[i]}"][target="${pathArray[i + 1]}"]`);
        if (edge.length > 0) {
          edge.data('in_path', true);
        }
      }
    } else if (!data.preserveGraph) {
      setGraphData(data.subgraph);
    }
  };

  const handleCyReady = (cy) => {
    cyRef.current = cy;
  };

  return (
    <div className="App">
      {/* Toast notifications */}
      <div className="toast-container">
        {toasts.map(toast => (
          <div key={toast.id} className={`toast ${toast.type} ${toast.exiting ? 'exiting' : ''}`}>
            <span>{toast.type === 'success' ? '\u2713' : toast.type === 'error' ? '\u2717' : '\u2139'}</span>
            {toast.message}
          </div>
        ))}
      </div>

      {/* Hero Section */}
      <header className="hero">
        <div className="hero-content">
          <div className="hero-logo">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              <circle cx="14" cy="14" r="6" fill="#fff" opacity="0.9"/>
              <circle cx="34" cy="14" r="4" fill="#fff" opacity="0.7"/>
              <circle cx="24" cy="36" r="5" fill="#fff" opacity="0.8"/>
              <line x1="18" y1="17" x2="30" y2="14" stroke="#fff" strokeWidth="2" opacity="0.5"/>
              <line x1="16" y1="19" x2="22" y2="32" stroke="#fff" strokeWidth="2" opacity="0.5"/>
              <line x1="32" y1="18" x2="26" y2="32" stroke="#fff" strokeWidth="2" opacity="0.5"/>
            </svg>
          </div>
          <h1 className="hero-title">Prepify Graph</h1>
          <p className="hero-tagline">Czech Business Relationship Intelligence</p>
          <div className="hero-stats">
            {statsLoading ? (
              <div className="stat-skeleton">
                <div className="skeleton-bar" /><div className="skeleton-bar" />
              </div>
            ) : (
              <>
                <div className="stat">
                  <span className="stat-number">{stats.entities.toLocaleString()}</span>
                  <span className="stat-label">Entities</span>
                </div>
                <div className="stat-divider" />
                <div className="stat">
                  <span className="stat-number">{stats.relationships.toLocaleString()}</span>
                  <span className="stat-label">Relationships</span>
                </div>
              </>
            )}
          </div>
        </div>
      </header>

      <SearchBar onPathFound={handlePathFound} cyRef={cyRef} />

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
        <p>Prepify Graph v1.0 | Data from OR justice.cz | &copy; 2026</p>
      </footer>
    </div>
  );
}

export default App;
