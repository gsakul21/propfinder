"""
Full data ingestion pipeline for PropFinder.

Execution order:
  1. fetch parcels           → data/parcels.csv
  2. ingest parcels
  3. fetch tax delinquency   → data/tax_delinquency.csv
  4. ingest tax delinquency
  5. fetch foreclosures      → data/foreclosures.csv  (needs parcels in DB)
  6. ingest foreclosures
  7. detect absentee owners
  8. recompute scores

Flags:
  --skip-fetch        Re-use existing CSVs in data/ (skips all fetch steps).
  --dry-run           Test HTTP connectivity to each source; do not ingest.
  --parcel-limit N    Cap parcel fetch at N records (default 50000).
                      Pass 0 to fetch all ~150k+ residential parcels.

Run:
  DATABASE_URL=... python workers/pipeline.py
  DATABASE_URL=... python workers/pipeline.py --parcel-limit 50000
  DATABASE_URL=... python workers/pipeline.py --parcel-limit 0   # full county
  DATABASE_URL=... python workers/pipeline.py --skip-fetch
  DATABASE_URL=... python workers/pipeline.py --dry-run
"""
import argparse
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workers.common.log import elapsed, log

DATA_DIR   = Path(__file__).resolve().parents[1] / "data"
TOTAL_STEPS = 8


def _banner(skip_fetch: bool, dry_run: bool, parcel_limit: int | None) -> None:
    cap = f"{parcel_limit:,}" if parcel_limit else "unlimited (full county)"
    mode = "dry-run" if dry_run else ("skip-fetch" if skip_fetch else "full")
    print(flush=True)
    print("=" * 60, flush=True)
    print("  PropFinder Ingestion Pipeline", flush=True)
    print(f"  mode: {mode}  |  parcel cap: {cap}", flush=True)
    print("=" * 60, flush=True)
    print(flush=True)


def _step_start(n: int, label: str) -> float:
    log("pipeline", f"step {n}/{TOTAL_STEPS}: {label}")
    return time.time()


def _step_done(n: int, label: str, start: float, ok: bool, detail: str = "") -> None:
    status  = "OK  " if ok else "FAIL"
    detail_str = f"  {detail}" if detail else ""
    log("pipeline", f"step {n}/{TOTAL_STEPS}: {label} [{status}] {elapsed(start)}{detail_str}")


def _run_step(n: int, label: str, fn, *args, **kwargs) -> bool:
    start = _step_start(n, label)
    try:
        fn(*args, **kwargs)
        _step_done(n, label, start, ok=True)
        return True
    except Exception as e:
        log("pipeline", f"  ERROR: {e}")
        traceback.print_exc()
        _step_done(n, label, start, ok=False)
        return False


def _check_connectivity() -> None:
    import requests
    from workers.fetch import parcels as fp
    from workers.fetch import tax_delinquency as ft
    from workers.fetch import foreclosures as ff

    sources = [
        ("ArcGIS parcels",   fp.ARCGIS_URL),
        ("Prior sale PDFs",  ft.PRIOR_RESULTS_URL),
        ("Sheriff sales",    ff.SHERIFF_URL),
    ]
    for name, url in sources:
        t0 = time.time()
        try:
            import requests as r
            resp = r.head(url, timeout=10, headers={"User-Agent": "PropFinder/1.0"})
            log("connectivity", f"{name}: HTTP {resp.status_code}  ({elapsed(t0)})")
        except Exception as e:
            log("connectivity", f"{name}: FAILED — {e}")


def run(
    skip_fetch:    bool = False,
    dry_run:       bool = False,
    parcel_limit:  int | None = 50_000,
) -> None:
    _banner(skip_fetch, dry_run, parcel_limit)

    if dry_run:
        log("pipeline", "checking connectivity to all data sources...")
        _check_connectivity()
        log("pipeline", "dry-run complete")
        return

    from workers.fetch   import parcels         as fetch_parcels
    from workers.fetch   import tax_delinquency as fetch_tax
    from workers.fetch   import foreclosures    as fetch_foreclosures
    from workers.ingest  import parcels         as ingest_parcels
    from workers.ingest  import tax_delinquency as ingest_tax
    from workers.ingest  import foreclosure     as ingest_foreclosure
    from workers.ingest  import absentee        as ingest_absentee
    from workers.scoring import recompute       as scoring

    parcels_csv     = str(DATA_DIR / "parcels.csv")
    tax_csv         = str(DATA_DIR / "tax_delinquency.csv")
    foreclosure_csv = str(DATA_DIR / "foreclosures.csv")

    results: dict[str, bool] = {}
    pipeline_start = time.time()

    # ── 1: Fetch parcels ─────────────────────────────────────────────────────
    if not skip_fetch:
        results["fetch_parcels"] = _run_step(
            1, "fetch parcels",
            fetch_parcels.fetch_all, parcels_csv, max_records=parcel_limit,
        )
    else:
        log("pipeline", "step 1/8: fetch parcels SKIPPED (--skip-fetch)")

    # ── 2: Ingest parcels ────────────────────────────────────────────────────
    if Path(parcels_csv).exists():
        results["ingest_parcels"] = _run_step(
            2, "ingest parcels",
            ingest_parcels.ingest, parcels_csv,
        )
    else:
        log("pipeline", f"step 2/8: ingest parcels SKIPPED — {parcels_csv} not found")

    # ── 3: Fetch tax delinquency ─────────────────────────────────────────────
    if not skip_fetch:
        results["fetch_tax"] = _run_step(
            3, "fetch tax delinquency",
            fetch_tax.fetch_all, tax_csv,
        )
    else:
        log("pipeline", "step 3/8: fetch tax delinquency SKIPPED (--skip-fetch)")

    # ── 4: Ingest tax delinquency ────────────────────────────────────────────
    if Path(tax_csv).exists():
        results["ingest_tax"] = _run_step(
            4, "ingest tax delinquency",
            ingest_tax.ingest, tax_csv,
        )
    else:
        log("pipeline", f"step 4/8: ingest tax delinquency SKIPPED — {tax_csv} not found")

    # ── 5: Fetch foreclosures ────────────────────────────────────────────────
    # Must run AFTER parcel ingest because it matches sale addresses to DB parcel IDs.
    if not skip_fetch:
        results["fetch_foreclosures"] = _run_step(
            5, "fetch foreclosures",
            fetch_foreclosures.fetch_all, foreclosure_csv,
        )
    else:
        log("pipeline", "step 5/8: fetch foreclosures SKIPPED (--skip-fetch)")

    # ── 6: Ingest foreclosures ───────────────────────────────────────────────
    if Path(foreclosure_csv).exists():
        results["ingest_foreclosures"] = _run_step(
            6, "ingest foreclosures",
            ingest_foreclosure.ingest, foreclosure_csv,
        )
    else:
        log("pipeline", f"step 6/8: ingest foreclosures SKIPPED — {foreclosure_csv} not found")

    # ── 7: Absentee detection ────────────────────────────────────────────────
    results["absentee"] = _run_step(7, "detect absentee owners", ingest_absentee.recompute)

    # ── 8: Score recomputation ───────────────────────────────────────────────
    results["scoring"] = _run_step(8, "recompute scores", scoring.recompute)

    # ── Summary ──────────────────────────────────────────────────────────────
    print(flush=True)
    print("=" * 60, flush=True)
    print(f"  Pipeline summary  (total: {elapsed(pipeline_start)})", flush=True)
    print("=" * 60, flush=True)
    for step, ok in results.items():
        status = "OK  " if ok else "FAIL"
        print(f"  [{status}] {step}", flush=True)
    print("=" * 60, flush=True)

    failed = [k for k, v in results.items() if not v]
    if failed:
        print(f"\n  {len(failed)} step(s) failed — see log above.", flush=True)
        sys.exit(1)
    else:
        print("\n  Pipeline complete.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PropFinder ingestion pipeline")
    parser.add_argument(
        "--skip-fetch", action="store_true",
        help="Skip fetch steps; use existing CSVs already in data/"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Check HTTP connectivity to all sources, then exit"
    )
    parser.add_argument(
        "--parcel-limit", type=int, default=50_000, metavar="N",
        help="Cap parcel fetch at N records (default 50000). Pass 0 for full county."
    )
    args = parser.parse_args()
    run(
        skip_fetch=args.skip_fetch,
        dry_run=args.dry_run,
        parcel_limit=args.parcel_limit or None,
    )
