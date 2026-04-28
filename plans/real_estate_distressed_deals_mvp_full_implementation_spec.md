# Real Estate Distressed Deals MVP

## Executive Summary

Build a production-quality MVP for a B2B SaaS platform that identifies and ranks distressed residential real estate investment opportunities in the Philadelphia metropolitan area.

Target users are:
- Small real estate investors
- Wholesalers
- Local acquisition teams

The platform ingests public county data, detects distress signals, computes an explainable score, and presents opportunities via a map-driven web application.

---

# Product Goals

## Primary Objective

Enable a local real estate investor to identify high-probability acquisition opportunities in under five minutes.

## Core Value Proposition

Transform fragmented public records into a ranked, explainable, actionable deal feed.

## MVP Constraints

- Single market only (Philadelphia metro)
- Focus on one county initially
- Residential properties only
- Three distress signals only
- Deterministic scoring
- No machine learning

---

# Technical Architecture

```text
Public Data Sources
        |
        v
Ingestion Workers (ETL)
        |
        v
PostgreSQL + PostGIS
        |
        v
FastAPI Backend
        |
        v
Next.js Frontend
```

## Repository Structure

```text
real-estate-deals/
├── backend/
│   ├── app/
│   ├── alembic/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
│
├── workers/
│   ├── ingest/
│   ├── scoring/
│   ├── common/
│   └── requirements.txt
│
├── docker-compose.yml
└── README.md
```

---

# Technology Stack

## Backend

- Python 3.12
- FastAPI
- SQLAlchemy 2.0
- Pydantic v2
- Alembic
- PostgreSQL
- PostGIS

## Frontend

- Next.js 15
- TypeScript
- Tailwind CSS
- TanStack Query
- Mapbox GL JS
- Zustand

## Infrastructure

- Docker Compose (local)
- PostgreSQL 16
- Redis optional (future)
- GitHub Actions

---

# Geographic Scope

## Initial Launch Market

Montgomery County, Pennsylvania.

Rationale:
- Strong investor activity
- High data availability
- Large enough market
- Easier sales motion than Philadelphia proper

---

# Data Sources

## 1. Parcel and Ownership Data

Primary Source:
- Montgomery County Board of Assessment parcel records

Required Fields:
- Parcel ID
- Situs address
- Property type
- Owner name
- Owner mailing address
- Assessed value
- Latitude/Longitude (if available)

## 2. Tax Delinquency Data

Primary Sources:
- County Treasurer delinquent tax rolls
- Tax sale lists
- Public annual delinquency notices

Required Fields:
- Parcel ID
- Tax year
- Amount due
- Delinquency status
- Sale eligibility

## 3. Foreclosure Data

Primary Sources:
- County Court docket filings
- Lis Pendens records
- Sheriff's sale postings

Required Fields:
- Parcel ID or address
- Filing date
- Case number
- Foreclosure stage
- Auction date

---

# Database Schema

## properties

```sql
CREATE TABLE properties (
    id UUID PRIMARY KEY,
    parcel_id TEXT UNIQUE NOT NULL,
    address TEXT NOT NULL,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    county TEXT NOT NULL,
    property_type TEXT NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geom GEOGRAPHY(Point, 4326),
    assessed_value NUMERIC,
    owner_name TEXT,
    owner_mailing_address TEXT,
    is_absentee BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

## distress_signals

```sql
CREATE TABLE distress_signals (
    id UUID PRIMARY KEY,
    property_id UUID REFERENCES properties(id) ON DELETE CASCADE,
    signal_type TEXT NOT NULL,
    severity NUMERIC NOT NULL,
    raw_data JSONB NOT NULL,
    detected_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    UNIQUE(property_id, signal_type)
);
```

## property_scores

```sql
CREATE TABLE property_scores (
    property_id UUID PRIMARY KEY REFERENCES properties(id) ON DELETE CASCADE,
    score INTEGER NOT NULL,
    tier TEXT NOT NULL,
    reasons JSONB NOT NULL,
    computed_at TIMESTAMP NOT NULL
);
```

---

# Distress Signals

## Tax Delinquency

### Scoring

- Less than 1 year: +15
- 1 to 2 years: +25
- Greater than 2 years: +35

### Detection Logic

- Unpaid tax balance exists
- Delinquency status active

---

## Foreclosure

### Scoring

- Filing detected: +30
- Active foreclosure: +35
- Sheriff's sale scheduled: +40

### Detection Logic

- Open foreclosure case
- Lis pendens filing
- Auction posting

---

## Absentee Ownership

### Scoring

- Same county: +10
- Different county: +15
- Out of state: +20

### Detection Logic

- Owner mailing address differs from property address

---

# Composite Scoring Engine

## Formula

```python
final_score = (
    tax_score
    + foreclosure_score
    + absentee_score
    + stacking_bonus
    - conflict_penalty
)
```

## Stacking Bonus

- Two signals: +10
- Three signals: +15

## Conflict Penalty

- Recent transfer within 90 days: -20
- Foreclosure resolved: -30

## Tiering

- 80 to 100: hot
- 50 to 79: warm
- Below 50: cold

---

# Backend API

## GET /api/v1/properties

### Query Parameters

- min_score
- county
- property_type
- distress_types
- bbox
- page
- limit

### Response

```json
{
  "results": [],
  "total": 0,
  "page": 1,
  "limit": 50
}
```

---

## GET /api/v1/properties/{id}

Returns:
- Full property details
- Distress signals
- Score breakdown
- Ownership data
- Timeline

---

## POST /api/v1/exports

Exports filtered lead lists as CSV.

---

# Ingestion Workers

## Worker Structure

```text
workers/
├── ingest/
│   ├── parcels.py
│   ├── tax_delinquency.py
│   ├── foreclosure.py
│   └── absentee.py
```

## Execution Schedule

- Parcels: weekly
- Tax delinquency: daily
- Foreclosure: daily
- Absentee recomputation: weekly
- Score recomputation: nightly

---

# Backend Folder Structure

```text
backend/app/
├── api/
├── core/
├── db/
├── models/
├── schemas/
├── services/
├── repositories/
└── main.py
```

---

# Frontend Requirements

## Layout

- Left sidebar: filters
- Center: ranked property feed
- Right: interactive map
- Slide-over: property detail drawer

## Core Components

```text
src/components/
├── filters/
├── map/
├── properties/
├── layout/
└── shared/
```

---

# Core UI Features

## Property List

Each card displays:
- Address
- Score badge
- Distress badges
- Property type
- Last updated

## Interactive Map

- Cluster markers
- Heat-style scoring colors
- Bidirectional synchronization with list

## Property Detail Drawer

- Score breakdown
- Distress explanations
- Ownership details
- Export button

---

# State Management

Use Zustand for:
- Active filters
- Selected property
- Map bounds
- UI state

Use TanStack Query for:
- Property fetching
- Pagination
- Caching

---

# API Contracts

## Property Summary

```typescript
interface PropertySummary {
  id: string;
  address: string;
  latitude: number;
  longitude: number;
  score: number;
  tier: 'hot' | 'warm' | 'cold';
  signals: string[];
  propertyType: string;
}
```

## Property Detail

```typescript
interface PropertyDetail extends PropertySummary {
  assessedValue: number;
  ownerName: string;
  isAbsentee: boolean;
  scoreBreakdown: {
    tax: number;
    foreclosure: number;
    absentee: number;
    bonus: number;
  };
}
```

---

# MVP User Flow

1. User opens dashboard.
2. Map loads Montgomery County.
3. Top-ranked deals appear.
4. User applies filters.
5. User clicks property.
6. Detail drawer opens.
7. User exports shortlist.

---

# Success Metrics

## Product Metrics

- Time to first meaningful property: under 60 seconds
- Time to export leads: under 5 minutes
- Weekly active usage among beta users

## Business Metrics

- First paying customer within 30 days
- 3 pilot customers within 90 days

---

# Build Phases

## Phase 1

- PostgreSQL setup
- Parcel ingestion
- Basic FastAPI skeleton

## Phase 2

- Tax delinquency pipeline
- Absentee detection

## Phase 3

- Foreclosure pipeline
- Scoring engine

## Phase 4

- REST API endpoints
- Filtering
- Pagination

## Phase 5

- Next.js shell
- Property list
- Map integration

## Phase 6

- Detail drawer
- CSV export
- Authentication

---

# Non-Goals

Do not build in MVP:

- MLS integration
- Machine learning models
- Mobile apps
- Automated outreach
- Nationwide expansion
- CRM integrations

---

# Acceptance Criteria

A local investor can:

- Search distressed properties
- Filter by score and signal
- View properties on a map
- Understand why each property ranks highly
- Export targeted lead lists

All within five minutes of first login.

---

# Future Expansion

After validation:

- Additional counties
- Probate signals
- Code violations
- Equity estimation
- Automated mailing integrations
- Team collaboration

---

# Final Product Positioning

"Zillow for off-market distressed investment opportunities."

The competitive moat is not the interface.

The moat is:
- Data normalization
- Signal quality
- Geographic specialization
- Investor workflow fit

---

# Development Priority

Always optimize for:

1. Signal accuracy
2. Speed to insight
3. Investor trust
4. Ease of use

Pretty dashboards come later.
Useful dashboards win first.

