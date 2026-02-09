# Prepify Graph API

Flask REST API for Czech business relationship graph queries.

## Base URL

```
http://localhost:5000
```

## Endpoints

### Search

#### `GET /api/search?q=<query>`

Search entities by name, ICO, or city. Returns up to 20 results, sorted by relevance.

**Query Parameters:**

| Param | Type   | Required | Description |
|-------|--------|----------|-------------|
| `q`   | string | yes      | Search query (min 2 characters) |

**Response:**
```json
{
  "results": [
    {
      "id": "45274649",
      "name": "Avast Software s.r.o.",
      "type": "company",
      "city": "Praha",
      "country": "CZ",
      "insolvent": false
    }
  ]
}
```

**Errors:**
- `400` - Missing `q` parameter

---

### Path Finding

#### `POST /api/top-paths`

Find top K shortest paths between two entities with optional filters.

**Request Body:**
```json
{
  "source": "45274649",
  "target": "00001834",
  "k": 3,
  "exclude_insolvent": false,
  "exclude_foreign": false,
  "exclude_inactive": false
}
```

| Field              | Type    | Default | Description |
|--------------------|---------|---------|-------------|
| `source`           | string  | -       | Source entity ID (required) |
| `target`           | string  | -       | Target entity ID (required) |
| `k`                | integer | 3       | Number of alternative paths |
| `exclude_insolvent`| boolean | false   | Skip paths through insolvent entities |
| `exclude_foreign`  | boolean | false   | Skip paths through non-CZ entities |
| `exclude_inactive` | boolean | false   | Skip paths with historical relationships |

**Response (found):**
```json
{
  "found": true,
  "count": 2,
  "paths": [
    {
      "path": ["45274649", "RC_NOVAK_JAN_19850115", "00001834"],
      "length": 2,
      "details": [
        { "name": "Avast Software s.r.o.", "type": "company", "relationship_to_next": "jednatel" },
        { "name": "Jan Novak", "type": "person", "relationship_to_next": "spolecnik" },
        { "name": "Target s.r.o.", "type": "company" }
      ]
    }
  ],
  "subgraph": { "nodes": [...], "edges": [...] }
}
```

**Response (not found):**
```json
{
  "found": false,
  "message": "No paths found between 45274649 and 00001834"
}
```

**Errors:**
- `400` - Missing `source` or `target`

---

#### `POST /api/multi-path`

Find a path through multiple ordered waypoints.

**Request Body:**
```json
{
  "waypoints": ["45274649", "RC_NOVAK_JAN_19850115", "00001834"],
  "exclude_insolvent": false,
  "exclude_foreign": false,
  "exclude_inactive": false
}
```

| Field      | Type     | Description |
|------------|----------|-------------|
| `waypoints`| string[] | Ordered list of entity IDs to pass through (min 2) |

**Response:** Same structure as `/api/top-paths` but always returns 1 path.

**Errors:**
- `400` - Fewer than 2 waypoints

---

#### `POST /api/shortest-path`

Simple shortest path between two entities (no filters, no alternatives).

**Request Body:**
```json
{
  "source": "45274649",
  "target": "00001834"
}
```

**Response:**
```json
{
  "found": true,
  "path": ["45274649", "RC_NOVAK_JAN_19850115", "00001834"],
  "path_length": 2,
  "details": [...],
  "subgraph": { "nodes": [...], "edges": [...] }
}
```

---

### Exploration

#### `GET /api/explore/<entity_id>`

Get an entity and all its direct neighbors for interactive exploration.

**Query Parameters:**

| Param           | Type   | Description |
|-----------------|--------|-------------|
| `existing_nodes`| string | Comma-separated list of already-visible node IDs (for cross-edges) |

**Response:**
```json
{
  "entity": { "id": "45274649", "name": "Avast Software s.r.o.", "type": "company" },
  "subgraph": { "nodes": [...], "edges": [...] },
  "neighbor_count": 5
}
```

**Errors:**
- `404` - Entity not found
- `500` - Server error

---

### Entity Details

#### `GET /api/entities/<entity_id>`

Get detailed information about a specific entity and its neighbors.

**Response:**
```json
{
  "id": "45274649",
  "name": "Avast Software s.r.o.",
  "type": "company",
  "neighbors": [
    { "id": "RC_NOVAK_JAN_19850115", "name": "Jan Novak", "type": "person", "relationship": "jednatel" }
  ],
  "neighbor_count": 3
}
```

**Errors:**
- `404` - Entity not found

---

### Statistics

#### `GET /api/stats`

Simplified entity/relationship counts for the frontend.

```json
{ "entities": 336, "relationships": 552 }
```

#### `GET /api/graph-stats`

Full graph statistics from NetworkX.

```json
{
  "total_nodes": 336,
  "total_edges": 552,
  "companies": 100,
  "persons": 225,
  "components": 86
}
```

#### `GET /api/health`

Health check endpoint (used by Render for monitoring).

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "entities": 336,
  "relationships": 552,
  "uptime_seconds": 3621
}
```

---

### Debug Endpoints

#### `POST /api/debug/reload`

Reload graph data from source.

#### `POST /api/debug/enable-real-data`

Switch to real OR data and reload the graph.

---

## Error Format

All error responses follow this structure:

```json
{
  "error": "Description of what went wrong"
}
```

Common HTTP status codes:
- `200` - Success
- `400` - Bad request (missing parameters)
- `404` - Entity not found
- `500` - Server error

## Rate Limits

No explicit rate limits on the API itself. External data sources have limits:
- **ISIR API**: 10 requests/second (handled internally with delays)
- **OpenCorporates**: Free tier rate limits apply

## Running

```bash
pip install -r requirements.txt
python app.py              # Development (port 5000)
gunicorn wsgi:app          # Production
```

Set `USE_REAL_DATA=true` to download real data from OR justice.cz on startup.
