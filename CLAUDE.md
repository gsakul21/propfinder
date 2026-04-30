# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Ruthlessly Refine and Update To Optimize Quality and Performance

**Thoroughly reflect on sessions, generate insights about what went well, what went bad and update this file with your own rules to improve session for next time.**

After every session:
- Analyze the entire session, determine what went well and what didn't.
- Develop clear instructions to prevent the undesirable patterns from occurring.
- Update CLAUDE.md file with the clear instructions.

## 2. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 3. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 4. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 5. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

# Project Specific Information

Critical context. Update whenever implementation changes.

## Stack

| Layer    | Technology                              |
|----------|-----------------------------------------|
| Database | PostgreSQL 16 + PostGIS                 |
| ORM      | SQLAlchemy (sync, psycopg2)             |
| Backend  | FastAPI + Alembic migrations            |
| Frontend | Next.js 15, React Query, Zustand, MapLibre GL |
| Pipeline | Python workers in `workers/`            |

All services wired via Docker Compose. `DATABASE_URL` is the single env var shared across backend and workers.

## Data Pipeline

Orchestrated by `workers/pipeline.py`. Eight steps in order:

1. Fetch parcels (ArcGIS REST API via PASDA) → `data/parcels.csv`
2. Ingest parcels
3. Fetch tax delinquency (Montgomery County upset-sale PDFs) → `data/tax_delinquency.csv`
4. Ingest tax delinquency
5. Fetch foreclosures (CivilView sheriff sales) → `data/foreclosures.csv`
6. Ingest foreclosures
7. Detect absentee owners (address comparison, no external data)
8. Recompute distress scores

Key pipeline flags: `--parcel-limit N` (0 = full ~276k county), `--skip-fetch` (reuse CSVs), `--dry-run`.

Run with `--no-deps` to skip the migrate dependency on reruns where the schema is already applied:
```
docker compose run --rm --no-deps pipeline python workers/pipeline.py --skip-fetch
```

## Data Sources and Formats

**Parcels (PASDA ArcGIS REST):**
- `mapservices.pasda.psu.edu` — paginated 1000/batch via `resultOffset`
- Parcel IDs stored as 12-digit no-hyphen strings (e.g. `300034228005`)

**Tax Delinquency (PDF):**
- Source: `montgomerycountypa.gov/2635/Prior-Sales-Results`
- PDF parcel IDs are 5-segment hyphenated: `\d{2}-\d{2}-\d{5}-\d{2}-\d{1}` (e.g. `10-00-05252-00-3`)
- Always strip hyphens before DB lookup: `pid.replace("-", "")`

**Foreclosures (CivilView):**
- Source: `salesweb.civilview.com/Sales/SalesSearch?countyId=23`
- Addresses use full street-type words (COURT, ROAD, AVENUE)
- PASDA uses abbreviations (CT, RD, AVE) — normalize before matching via `_STREET_ABBREV`

## Scoring Thresholds

- **Hot:** score ≥ 65
- **Warm:** score 35–64
- **Cold:** score < 35

A single foreclosure-at-auction signal (40 pts) lands in warm. Reaching hot requires at least two overlapping signals plus the stacking bonus.

## DB Write Patterns

For large tables (100k+ rows), per-row Python loops with individual SQLAlchemy `execute()` calls are extremely slow:
- Use bulk `INSERT ... VALUES (batch)` with `on_conflict_do_update`
- For UPDATE, use **delta writes**: load current state, compute changed IDs, update only the diff
- Never do `UPDATE table SET col=X` (full-table reset) followed by targeted flips — at 275k rows this took 3+ hours vs 15s with delta approach

## Frontend State

- Zustand store (`frontend/src/lib/store.ts`): `filters`, `page`, `selectedPropertyId`
- Setting a filter resets `page` to 1
- Map uses `queryKey: ["properties-map", filters]` with `limit: 1000` — independent of list pagination
- List uses `queryKey: ["properties", filters, page]` with `limit: 50`

---

# CLAUDE Self-Generated Guidelines

## Diagnose before fixing data format issues

When a fetch/ingest step produces 0 records, run a live diagnostic script inside the container to inspect the actual raw data before touching any regex or parsing code. Download a sample, print it, identify the exact format, then fix. Guessing at formats wastes multiple iterations.

Example pattern:
```bash
docker compose run --rm --no-deps pipeline python -c "
import requests, pdfplumber, tempfile, pathlib
r = requests.get('<url>', timeout=60)
tmp = pathlib.Path('/tmp/test.pdf')
tmp.write_bytes(r.content)
with pdfplumber.open(str(tmp)) as pdf:
    for page in pdf.pages[:2]:
        print(page.extract_text()[:500])
"
```

## Validate scoring semantics against real data after first real pipeline run

After ingesting real data for the first time, query the tier distribution and the top-scoring properties. Check that the results match intuition:
- A property in active foreclosure should not be "cold"
- A property with all three signals should be "hot"

If they don't match, recalibrate thresholds — don't assume the initial numbers are correct.

## Bulk write patterns for large datasets

Never write a loop that calls `session.execute(update(...).where(id == x))` per row. Always:
1. Classify/compute in a pure Python loop (no DB calls)
2. Collect results into lists/dicts
3. Write to DB in batches using `INSERT ... VALUES (batch)` or `UPDATE ... WHERE id IN (batch)`

For `is_absentee` style flags: load current state → compute delta → update only changed IDs. On a fresh DB this means writing only the ~15% that are absentee, not resetting all 276k rows.

## Use `--no-deps` for pipeline reruns during development

`docker compose run pipeline` triggers the `migrate` dependency on every run, adding ~15s. Once the schema is applied, use:
```
docker compose run --rm --no-deps pipeline python workers/pipeline.py ...
```

## Don't background long commands when you need to monitor them

The `run_in_background` parameter makes output monitoring awkward (nested tail/poll loops). For pipeline runs that need active monitoring, run them foreground and let the tool stream output directly.

## Address normalization is a cross-cutting concern

Any time two data sources describe the same street address (CivilView + PASDA, upset-sale PDFs + PASDA, etc.), check for formatting differences before writing match logic:
- Street type words vs. abbreviations (COURT vs CT)
- Hyphen presence in parcel IDs
- City/township name variations
Mismatches here silently produce 0 matches with no error.
