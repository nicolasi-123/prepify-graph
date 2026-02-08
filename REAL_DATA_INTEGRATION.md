# Real Data Integration Guide

## Overview

The Prepify Graph application now supports real data integration from three sources:
1. **OR Justice.cz** - Czech Business Registry (Obchodní rejstřík)
2. **ISIR** - Czech Insolvency Registry
3. **OpenCorporates** - International company registry (Cyprus, Netherlands)

## Quick Start

### Using Sample Data (Default)

By default, the application uses curated sample data with 19 entities. This is fast and reliable for testing.

```bash
# No configuration needed - just run the app
python backend/app.py
```

### Using Real Data

To download and use real data from OR justice.cz:

**Option 1: Environment Variable**
```bash
# Windows
set USE_REAL_DATA=true
python backend/app.py

# Linux/Mac
USE_REAL_DATA=true python backend/app.py
```

**Option 2: Code Configuration**
Edit `backend/app.py` and change:
```python
USE_REAL_DATA = True  # Set to True for real data
```

**Option 3: API Endpoint (Runtime)**
```bash
# Enable real data via API
curl -X POST http://localhost:5000/api/debug/enable-real-data
```

## How It Works

### 1. OR Justice.cz Data Download

When real data is enabled, the system:
1. Connects to `dataor.justice.cz` API
2. Finds the latest CSV dataset (2025/2026)
3. Downloads the CSV file (~50-200MB, may take 2-5 minutes)
4. Decompresses if gzipped
5. Parses CSV with auto-encoding detection (UTF-8, Windows-1250, ISO-8859-2)

**Configuration:**
```python
# In or_parser.py
max_companies = 100  # Start small, increase to 500-5000 later
```

### 2. ISIR Insolvency Checking

For each company loaded from OR, the system:
1. Calls ISIR API: `https://isir.justice.cz/isir/common/api/v1/subjects`
2. Checks if company has insolvency proceedings
3. Caches results to avoid repeated API calls
4. Rate-limits to 10 requests/second (0.5s delay per batch)

**Example Response:**
- Company has insolvency record → `insolvent: true` (red node)
- No insolvency found → `insolvent: false` (default color)

### 3. OpenCorporates Foreign Entities

For international companies (Cyprus, Netherlands):
1. Queries `api.opencorporates.com`
2. Fetches company name, city, status
3. Checks if dissolved/liquidated → marks as insolvent
4. Caches results

**Supported Jurisdictions:**
- `cy` - Cyprus
- `nl` - Netherlands

### 4. Graph Population

The system:
1. Loads Czech companies from OR CSV
2. Batch-checks ISIR insolvency
3. Adds foreign entities from OpenCorporates
4. Adds sample persons (3 individuals)
5. Creates relationships (currently sample relationships)

## Data Structure

### Company Entity
```json
{
  "id": "45274649",
  "name": "Avast Software s.r.o.",
  "type": "company",
  "city": "Praha",
  "country": "CZ",
  "insolvent": false
}
```

### Person Entity
```json
{
  "id": "RC001",
  "name": "Jan Novák",
  "type": "person",
  "city": "Praha",
  "country": "CZ",
  "insolvent": false
}
```

### Relationship
```json
{
  "source": "RC001",
  "target": "45274649",
  "type": "jednatel",
  "active": true
}
```

## Performance Considerations

### First Run with Real Data
- **Download Time**: 2-5 minutes (CSV file)
- **Parsing Time**: 10-30 seconds (100 companies)
- **ISIR Checks**: 5-10 seconds (100 companies with rate limiting)
- **OpenCorporates**: 2-4 seconds (4 foreign entities with rate limiting)
- **Total**: ~5-10 minutes first run

### Subsequent Runs
- CSV parsing is fast once downloaded
- ISIR results are cached
- OpenCorporates results are cached

### Scaling
```python
# Start small
max_companies = 100  # ~5-10 minutes

# Medium dataset
max_companies = 500  # ~20-30 minutes

# Large dataset
max_companies = 5000  # ~2-3 hours
```

## Limitations & Future Work

### Current Limitations
1. **Relationships**: Currently using sample relationships. Real relationship extraction from OR CSV is complex (statutory bodies, shareholders data is in separate columns/files)
2. **OpenCorporates Rate Limit**: Free API has rate limits
3. **CSV Structure**: OR CSV format varies by year/release

### Planned Improvements
- [ ] Parse statutory body data from OR CSV
- [ ] Parse shareholder data from OR CSV
- [ ] Add more foreign jurisdictions
- [ ] Implement relationship caching
- [ ] Add progress indicators for long downloads
- [ ] Support XML parsing (as CSV alternative)

## Troubleshooting

### Download Fails
```
❌ Error downloading dataset
```
**Solution**: Check internet connection, dataor.justice.cz may be down. Falls back to sample data automatically.

### Encoding Errors
```
❌ Could not determine file encoding
```
**Solution**: OR CSV uses Windows-1250 encoding. The parser tries multiple encodings automatically.

### ISIR API Errors
```
Warning: ISIR check failed for 12345678
```
**Solution**: ISIR API may be slow or rate-limiting. The system marks as "not insolvent" and caches the result. Not critical.

### OpenCorporates API Errors
```
Warning: OpenCorporates fetch failed for cy:HE123456
```
**Solution**: Free API has rate limits. Falls back to sample foreign entities.

## API Endpoints

### Standard Endpoints
- `GET /api/search?q=avast` - Search entities
- `POST /api/shortest-path` - Find path between entities
- `GET /api/graph-stats` - Get graph statistics

### Debug Endpoints
- `POST /api/debug/reload` - Reload data
- `POST /api/debug/enable-real-data` - Enable real data and reload

## Example Usage

### Test Real Data Integration
```bash
# 1. Start with real data
set USE_REAL_DATA=true
python backend/app.py

# 2. Wait for download and parsing (~5-10 minutes)
# Watch console output for progress

# 3. Check stats
curl http://localhost:5000/api/graph-stats

# 4. Search for a real company
curl http://localhost:5000/api/search?q=avast

# 5. Find path between real entities
curl -X POST http://localhost:5000/api/shortest-path \
  -H "Content-Type: application/json" \
  -d '{"source": "45274649", "target": "00001834"}'
```

## Contact & Support

For issues or questions about data integration:
1. Check logs in console output
2. Verify API connectivity to dataor.justice.cz and isir.justice.cz
3. Try with smaller `max_companies` value (e.g., 50)
4. Check ISIR and OpenCorporates API status

---

**Last Updated**: 2026-02-06
**Version**: 1.0
