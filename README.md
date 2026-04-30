# PropFinder

Distressed real estate investment opportunity platform for Montgomery County, PA.

Ingests public county data, computes explainable distress scores, and surfaces ranked leads via a map-driven web application.

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- No API keys required — the map uses free CARTO tiles (OpenStreetMap)

### 1. Start the stack

```bash
docker compose up --build
```

This starts:
- PostgreSQL 16 + PostGIS at `localhost:5432`
- FastAPI backend at `http://localhost:8000`
- Next.js frontend at `http://localhost:3000` (hot-reload enabled)

Migrations run automatically on startup.

### 2. Run the data pipeline

```bash
# Full county (~276k parcels, ~10 min)
docker compose --profile pipeline run --rm pipeline python workers/pipeline.py

# Capped run for development (faster)
docker compose --profile pipeline run --rm pipeline python workers/pipeline.py --parcel-limit 25000

# Re-ingest without re-fetching (reuses data/ CSVs)
docker compose --profile pipeline run --rm pipeline python workers/pipeline.py --skip-fetch

# Check source connectivity only
docker compose --profile pipeline run --rm pipeline python workers/pipeline.py --dry-run
```

Pipeline steps (in order):
1. Fetch parcels from PASDA ArcGIS → `data/parcels.csv`
2. Ingest parcels into DB
3. Fetch tax delinquency upset-sale PDFs → `data/tax_delinquency.csv`
4. Ingest tax delinquency records
5. Fetch sheriff sale listings → `data/foreclosures.csv`
6. Ingest foreclosure records
7. Detect absentee owners (address comparison)
8. Recompute distress scores

### 3. Open the app

Navigate to `http://localhost:3000`

---

## Architecture

```
Public Data Sources → Ingestion Workers → PostgreSQL + PostGIS → FastAPI → Next.js
```

| Service  | Technology              | Port |
|----------|-------------------------|------|
| Database | PostgreSQL 16 + PostGIS | 5432 |
| Backend  | FastAPI + SQLAlchemy    | 8000 |
| Frontend | Next.js 15              | 3000 |

---

## Data Sources

All sources are Montgomery County, PA public records — no accounts or scraping tokens required.

| Signal           | Source                                                                                     |
|------------------|--------------------------------------------------------------------------------------------|
| Parcels          | PASDA ArcGIS REST API (`mapservices.pasda.psu.edu`) — ~276k residential parcels            |
| Tax Delinquency  | [Tax Claim Bureau upset-sale PDFs](https://www.montgomerycountypa.gov/2635/Prior-Sales-Results) |
| Foreclosures     | [CivilView sheriff sale listings](https://salesweb.civilview.com/Sales/SalesSearch?countyId=23) |

---

## Scoring

Scores are deterministic and explainable. Every property's score decomposes into named components.

| Signal                    | Points |
|---------------------------|--------|
| Tax delinquency < 1 yr    | +15    |
| Tax delinquency 1–2 yrs   | +25    |
| Tax delinquency > 2 yrs   | +35    |
| Foreclosure (filing)      | +30    |
| Foreclosure (active)      | +35    |
| Foreclosure (auction)     | +40    |
| Absentee (same county)    | +10    |
| Absentee (different county) | +15  |
| Absentee (out of state)   | +20    |
| 2-signal stacking bonus   | +10    |
| 3-signal stacking bonus   | +15    |
| Recent transfer (< 90d)   | −20    |
| Foreclosure resolved      | −30    |

**Tiers:** Hot (≥ 65) · Warm (35–64) · Cold (< 35)

---

## API Reference

### `GET /api/v1/properties`

| Param            | Type     | Description                                          |
|------------------|----------|------------------------------------------------------|
| `min_score`      | integer  | Minimum distress score                               |
| `county`         | string   | Filter by county name                                |
| `property_type`  | string   | `residential`, `commercial`, etc.                    |
| `distress_types` | string[] | `tax_delinquency`, `foreclosure`, `absentee`         |
| `bbox`           | string   | `min_lon,min_lat,max_lon,max_lat`                    |
| `page`           | integer  | Page number (default: 1)                             |
| `limit`          | integer  | Results per page (default: 50, max: 1000)            |

### `GET /api/v1/properties/{id}`

Returns full property detail with score breakdown and all distress signal records.

### `POST /api/v1/exports`

Exports a filtered lead list as CSV. Accepts the same query parameters as the list endpoint.

---

## Development

### Backend (without Docker)

```bash
cd backend
pip install -r requirements.txt
DATABASE_URL=postgresql+psycopg2://propfinder:propfinder@localhost:5432/propfinder \
  alembic upgrade head
DATABASE_URL=... uvicorn app.main:app --reload
```

### Frontend (without Docker)

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

### Running individual pipeline workers

```bash
# Set DATABASE_URL for all worker commands
export DATABASE_URL=postgresql+psycopg2://propfinder:propfinder@localhost:5432/propfinder

python -m workers.fetch.parcels --out data/parcels.csv
python -m workers.ingest.parcels --file data/parcels.csv

python -m workers.fetch.tax_delinquency --out data/tax_delinquency.csv
python -m workers.ingest.tax_delinquency --file data/tax_delinquency.csv

python -m workers.fetch.foreclosures --out data/foreclosures.csv
python -m workers.ingest.foreclosure --file data/foreclosures.csv

python -m workers.ingest.absentee       # recomputes absentee flags
python -m workers.scoring.recompute     # recomputes all scores
```
