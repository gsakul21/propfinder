"""
Tax delinquency ingestion worker.

Expected CSV columns:
  parcel_id, tax_year, amount_due, delinquency_status, sale_eligible

Run:
  DATABASE_URL=... python -m workers.ingest.tax_delinquency --file delinquent.csv
"""
import argparse
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from workers.common.db import get_session
from workers.common.log import elapsed, log
from workers.common.models import DistressSignal, Property

_PREFIX      = "ingest_tax"
COMMIT_EVERY = 500
LOG_EVERY    = 500


def _years_delinquent(tax_year: int) -> float:
    return (datetime.now(timezone.utc).year - tax_year)


def ingest(csv_path: str) -> None:
    start   = time.time()
    session = get_session()
    loaded, skipped = 0, 0
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with open(csv_path, newline="", encoding="utf-8") as f:
        total_rows = sum(1 for _ in f) - 1
    log(_PREFIX, f"loading {total_rows:,} rows from {csv_path}")

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            prop = session.scalars(select(Property).where(Property.parcel_id == row["parcel_id"])).first()
            if not prop:
                skipped += 1
                continue

            years = _years_delinquent(int(row["tax_year"]))
            severity = 35 if years >= 2 else (25 if years >= 1 else 15)

            stmt = insert(DistressSignal).values(
                property_id=prop.id,
                signal_type="tax_delinquency",
                severity=severity,
                raw_data={
                    "tax_year": int(row["tax_year"]),
                    "amount_due": float(row.get("amount_due", 0)),
                    "delinquency_status": row.get("delinquency_status", "active"),
                    "sale_eligible": row.get("sale_eligible", "false").lower() == "true",
                    "years_delinquent": years,
                },
                detected_at=now,
            ).on_conflict_do_update(
                index_elements=["property_id", "signal_type"],
                set_={
                    "severity": severity,
                    "raw_data": {
                        "tax_year": int(row["tax_year"]),
                        "amount_due": float(row.get("amount_due", 0)),
                        "delinquency_status": row.get("delinquency_status", "active"),
                        "sale_eligible": row.get("sale_eligible", "false").lower() == "true",
                        "years_delinquent": years,
                    },
                    "detected_at": now,
                },
            )
            session.execute(stmt)
            loaded += 1

            if loaded % COMMIT_EVERY == 0:
                session.commit()

            if loaded % LOG_EVERY == 0:
                pct  = int(100 * (loaded + skipped) / total_rows) if total_rows else 0
                rate = int(loaded / (time.time() - start))
                log(_PREFIX, f"  {loaded:,} loaded, {skipped:,} skipped ({pct}%)  {rate:,}/s")

    session.commit()
    session.close()
    log(_PREFIX, f"ingested {loaded:,} tax delinquency records, skipped {skipped:,}  ({elapsed(start)})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    args = parser.parse_args()
    ingest(args.file)
