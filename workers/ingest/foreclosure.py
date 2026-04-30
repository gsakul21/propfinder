"""
Foreclosure ingestion worker.

Expected CSV columns:
  parcel_id, filing_date, case_number, stage (filing|active|auction), auction_date

Run:
  DATABASE_URL=... python -m workers.ingest.foreclosure --file foreclosures.csv
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

_PREFIX         = "ingest_foreclosure"
COMMIT_EVERY    = 200
_STAGE_SEVERITY = {"filing": 30, "active": 35, "auction": 40}


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

            stage = row.get("stage", "filing")
            severity = _STAGE_SEVERITY.get(stage, 30)

            stmt = insert(DistressSignal).values(
                property_id=prop.id,
                signal_type="foreclosure",
                severity=severity,
                raw_data={
                    "case_number": row.get("case_number"),
                    "filing_date": row.get("filing_date"),
                    "stage": stage,
                    "auction_date": row.get("auction_date"),
                },
                detected_at=now,
            ).on_conflict_do_update(
                index_elements=["property_id", "signal_type"],
                set_={
                    "severity": severity,
                    "raw_data": {
                        "case_number": row.get("case_number"),
                        "filing_date": row.get("filing_date"),
                        "stage": stage,
                        "auction_date": row.get("auction_date"),
                    },
                    "detected_at": now,
                },
            )
            session.execute(stmt)
            loaded += 1

            if loaded % COMMIT_EVERY == 0:
                session.commit()

    session.commit()
    session.close()
    log(_PREFIX, f"ingested {loaded:,} foreclosure records, skipped {skipped:,}  ({elapsed(start)})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    args = parser.parse_args()
    ingest(args.file)
