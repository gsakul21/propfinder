# PropFinder

Distressed real estate investment opportunity platform for Montgomery County, PA.

Ingests public county data, computes explainable distress scores, and presents ranked deals via a map-driven web application.

---

## Quick Start

### 1. Prerequisites

- Docker + Docker Compose
- No API keys required — the map uses free CARTO/OpenStreetMap tiles

### 2. Configure environment (optional)

```bash
cp .env.example .env
# Only needed if you want to change the default API key
```

### 3. Start the stack

```bash
docker compose up --build
```

This starts:
- PostgreSQL 16 + PostGIS at `localhost:5432`
- FastAPI backend at `http://localhost:8000`
- Next.js frontend at `http://localhost:3000`

Migrations run automatically on startup.

### 4. Seed sample data

The seed profile loads ~40 realistic Montgomery County properties with distress signals and scores.

```bash
docker compose --profile seed run --rm seed
```

### 5. Open the app

Navigate to `http://localhost:3000`

---

## Architecture

```
Public Data Sources → Ingestion Workers → PostgreSQL + PostGIS → FastAPI → Next.js
```

| Service    | Technology           | Port  |
|------------|----------------------|-------|
| Database   | PostgreSQL 16 + PostGIS | 5432 |
| Backend    | FastAPI + SQLAlchemy | 8000  |
| Frontend   | Next.js 15           | 3000  |

---

## API Reference

### GET /api/v1/properties

Query parameters:

| Param           | Type     | Description                                |
|-----------------|----------|--------------------------------------------|
| `min_score`     | integer  | Filter by minimum score                    |
| `county`        | string   | Filter by county name                      |
| `property_type` | string   | `residential`, `commercial`, etc.          |
| `distress_types`| string[] | `tax_delinquency`, `foreclosure`, `absentee` |
| `bbox`          | string   | `min_lon,min_lat,max_lon,max_lat`           |
| `page`          | integer  | Page number (default: 1)                   |
| `limit`         | integer  | Results per page (default: 50, max: 200)   |

### GET /api/v1/properties/{id}

Returns full property detail with score breakdown and distress signal details.

### POST /api/v1/exports

Exports filtered lead list as CSV. Accepts same query parameters as the list endpoint.

---

## Scoring

Scores are deterministic and explainable:

| Signal                    | Points  |
|---------------------------|---------|
| Tax delinquency < 1 yr    | +15     |
| Tax delinquency 1–2 yrs   | +25     |
| Tax delinquency > 2 yrs   | +35     |
| Foreclosure (filing)      | +30     |
| Foreclosure (active)      | +35     |
| Foreclosure (auction)     | +40     |
| Absentee (same county)    | +10     |
| Absentee (diff county)    | +15     |
| Absentee (out of state)   | +20     |
| 2-signal stacking bonus   | +10     |
| 3-signal stacking bonus   | +15     |
| Recent transfer (< 90d)   | −20     |
| Foreclosure resolved      | −30     |

**Tiers:** Hot (80–100) · Warm (50–79) · Cold (< 50)

---

## Workers

Run workers to ingest real county data:

```bash
# Ingest parcels from CSV
DATABASE_URL=... python -m workers.ingest.parcels --file parcels.csv

# Ingest tax delinquency records
DATABASE_URL=... python -m workers.ingest.tax_delinquency --file delinquent.csv

# Ingest foreclosure filings
DATABASE_URL=... python -m workers.ingest.foreclosure --file foreclosures.csv

# Recompute absentee ownership flags
DATABASE_URL=... python -m workers.ingest.absentee

# Recompute all property scores
DATABASE_URL=... python -m workers.scoring.recompute
```

### Expected CSV Formats

**parcels.csv:** `parcel_id, address, city, state, zip_code, property_type, assessed_value, owner_name, owner_mailing_address, latitude, longitude`

**delinquent.csv:** `parcel_id, tax_year, amount_due, delinquency_status, sale_eligible`

**foreclosures.csv:** `parcel_id, filing_date, case_number, stage, auction_date`

---

## Development

### Backend (without Docker)

```bash
cd backend
pip install -r requirements.txt
DATABASE_URL=postgresql+psycopg2://propfinder:propfinder@localhost:5432/propfinder alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend (without Docker)

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

---

## Data Sources

Montgomery County, PA public records:

- **Parcels:** [Montgomery County Board of Assessment](https://www.montcopa.org/193/Assessment)
- **Tax Delinquency:** County Treasurer delinquent tax rolls
- **Foreclosures:** [Montgomery County Court Dockets](https://ujsportal.pacourts.us/)
