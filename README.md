# Prepify Graph

Czech Business Relationship Intelligence platform. Parses real company data from the OR justice.cz registry, builds a relationship graph of companies and persons, and provides an interactive visualization for exploring ownership structures and finding hidden connections.

## Features

### Data & Graph
- **Real OR data parsing** - Downloads and parses CSV from `dataor.justice.cz` (s.r.o. companies registered in Prague)
- **Java Map.toString() parser** - Custom recursive descent parser for the `udaje` field format used by the Czech Business Registry
- **Statutory body extraction** - Parses executives (jednatel) from company records with active/historical status
- **Shareholder extraction** - Parses company owners (SPOLECNIK) including natural and legal persons
- **ISIR insolvency checking** - Cross-references companies against the Czech Insolvency Registry
- **Foreign entity support** - Cyprus and Netherlands companies via OpenCorporates API
- **NetworkX graph** - Efficient path-finding with multi-point routing (up to 5 waypoints)

### Frontend
- **Interactive graph visualization** - Cytoscape.js with cola layout, animated edges, hover effects
- **Graph controls panel** - Node size / edge thickness sliders, fullscreen mode, fit-to-screen, export PNG
- **Entity detail modal** - Click any node to see full details, mini neighbor graph, grouped connections list
- **Path comparison** - Side-by-side comparison of alternative routes with risk scoring (insolvent / foreign entity count)
- **Exploration mode** - Single-entity search to explore a node's neighborhood interactively
- **Multi-point routing** - Chain up to 5 waypoints for complex path searches
- **Export controls** - PDF, SVG, PNG, and JSON export of graph and path data
- **Risk scoring** - Automatic risk assessment per path based on insolvent and offshore entities
- **Toast notifications & confetti** - Feedback on search results with celebration for complex path discoveries
- **Responsive design** - Works on desktop and mobile

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask, NetworkX, Python 3.10+ |
| Frontend | React, Cytoscape.js, Axios |
| Data source | OR justice.cz CKAN API, ISIR API, OpenCorporates API |
| Deployment | Gunicorn (production), Render-ready |

## Quick Start

```bash
# Backend
pip install -r requirements.txt
python backend/app.py

# Frontend
cd frontend
npm install
npm start
```

Set `USE_REAL_DATA=true` environment variable (or edit `backend/app.py`) to download and parse real registry data instead of sample data.

## Documentation

- [Real Data Integration Guide](REAL_DATA_INTEGRATION.md) - Detailed guide on OR data parsing, ISIR, and foreign registries
