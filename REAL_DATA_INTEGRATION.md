# Real Data Integration Guide

## Overview

Prepify Graph parses real company data from the Czech Business Registry (OR justice.cz), extracts relationships between companies and persons (executives, shareholders), checks insolvency status via ISIR, and supports foreign entities from Cyprus and Netherlands.

Data sources:
1. **OR Justice.cz** - Czech Business Registry CSV via CKAN API (`dataor.justice.cz`)
2. **ISIR** - Czech Insolvency Registry API (`isir.justice.cz`)
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
1. Connects to `dataor.justice.cz` CKAN API
2. Finds the latest CSV dataset (`sro-full-praha-2026`)
3. Downloads the CSV file (~200MB, cached for 7 days)
4. Parses CSV with auto-encoding detection (UTF-8, Windows-1250, ISO-8859-2)

CSV columns: `ico, nazev, udaje, vymazDatum, zapisDatum`

**Cache location:**
- Windows: `%LOCALAPPDATA%\prepify\or-cache\`
- Linux: `/var/cache/prepify/or-cache/`

**Configuration:**
```python
# In or_parser.py
max_companies = 100  # Start small, increase to 500-5000 later
```

### 2. Java Map.toString() Parser

The `udaje` field in the CSV uses **Java Map.toString() format**, not JSON:
- Format: `{key=value;key2={nested=val}}`
- Lists: `[{...}, {...}]`
- Separator: `;` between map entries, `,` between list items

A custom recursive descent parser (`parse_java_map()` in `or_parser.py`) handles this format. Key detail: the parser uses lookahead to distinguish separators from text content (e.g., `;` is only a separator when followed by `identifier=`).

### 3. Relationship Extraction

The parser extracts real relationships from the `udaje` field:

**Statutory bodies (executives):**
- `udajTyp.kod = STATUTARNI_ORGAN` → `podudaje[]` → `STATUTARNI_ORGAN_CLEN`
- Person data: `osoba.jmeno`, `osoba.prijmeni`, `osoba.narozDatum` (names are UPPERCASE)
- Function: `funkce` field (e.g., "Jednatel")
- Active/historical: `vymazDatum` present means deleted

**Shareholders (owners):**
- `udajTyp.kod = SPOLECNIK` → `podudaje[]` → `SPOLECNIK_OSOBA` or `SPOLECNIK_PRAVNICKA_OSOBA`
- Natural persons: same `osoba` structure
- Legal persons: referenced by IČO

**Registered address:**
- `udajTyp.kod = SIDLO` → `adresa.obec` for city

### 4. ISIR Insolvency Checking

For each company loaded from OR, the system:
1. Calls ISIR API: `https://isir.justice.cz/isir/common/api/v1/subjects`
2. Checks if company has insolvency proceedings
3. Caches results to avoid repeated API calls
4. Rate-limits to 10 requests/second (0.5s delay per batch)

Companies with insolvency → `insolvent: true` (red node in graph).

### 5. OpenCorporates Foreign Entities

For international companies (Cyprus, Netherlands):
1. Queries `api.opencorporates.com`
2. Fetches company name, city, status
3. Checks if dissolved/liquidated → marks as insolvent
4. Caches results

Supported jurisdictions: `cy` (Cyprus), `nl` (Netherlands).

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
  "id": "RC_NOVAK_JAN_19850115",
  "name": "Jan Novak",
  "type": "person",
  "country": "CZ",
  "insolvent": false
}
```

Person IDs follow the format `RC_SURNAME_NAME_DATE` (derived from parsed OR data).

### Relationship
```json
{
  "source": "RC_NOVAK_JAN_19850115",
  "target": "45274649",
  "type": "jednatel",
  "active": true
}
```

## Performance Considerations

### First Run with Real Data
- **Download Time**: 2-5 minutes (CSV file, ~200MB)
- **Parsing Time**: 10-30 seconds (100 companies)
- **ISIR Checks**: 5-10 seconds (100 companies with rate limiting)
- **OpenCorporates**: 2-4 seconds (foreign entities with rate limiting)
- **Total**: ~5-10 minutes first run

### Subsequent Runs
- CSV cached locally (7-day expiry) - no re-download needed
- ISIR results are cached
- OpenCorporates results are cached

### Scaling
```python
# Start small
max_companies = 100  # ~336 entities, ~552 relationships

# Medium dataset
max_companies = 500  # ~20-30 minutes

# Large dataset
max_companies = 5000  # ~2-3 hours
```

## Current Limitations

1. **OpenCorporates Rate Limit**: Free API has rate limits
2. **CSV Structure**: OR CSV format may vary by year/release
3. **Person deduplication**: Same person with slightly different name spelling may create duplicate nodes

### Possible Future Improvements
- [ ] Add more foreign jurisdictions
- [ ] Implement relationship caching
- [ ] Add progress indicators for long downloads
- [ ] Person entity deduplication / fuzzy matching

## Troubleshooting

### Download Fails
```
Error downloading dataset
```
**Solution**: Check internet connection, dataor.justice.cz may be down. Falls back to sample data automatically.

### Encoding Errors
```
Could not determine file encoding
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
- `POST /api/shortest-path` - Find path between entities (supports multi-point routing)
- `GET /api/stats` - Get graph statistics (entity/relationship counts)

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
curl http://localhost:5000/api/stats

# 4. Search for a real company
curl http://localhost:5000/api/search?q=avast

# 5. Find path between real entities
curl -X POST http://localhost:5000/api/shortest-path \
  -H "Content-Type: application/json" \
  -d '{"source": "45274649", "target": "00001834"}'
```

---

**Last Updated**: 2026-02-09
**Version**: 1.1
