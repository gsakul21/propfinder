"""
Parcel ingestion worker.

Expected CSV columns (from Montgomery County Board of Assessment via PASDA):
  parcel_id, address, city, state, zip_code, property_type,
  assessed_value, owner_name, owner_mailing_address, latitude, longitude

Run:
  DATABASE_URL=... python -m workers.ingest.parcels --file parcels.csv
"""
import argparse
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy.dialects.postgresql import insert

from workers.common.db import get_session
from workers.common.log import elapsed, log
from workers.common.models import Property

_PREFIX      = "ingest_parcels"
COMMIT_EVERY = 1_000   # commit in batches to avoid a single giant transaction
LOG_EVERY    = 5_000   # print progress line every N rows


def ingest(csv_path: str) -> None:
    start   = time.time()
    session = get_session()
    loaded  = 0

    # Count total rows for progress percentage
    with open(csv_path, newline="", encoding="utf-8") as f:
        total_rows = sum(1 for _ in f) - 1  # subtract header
    log(_PREFIX, f"loading {total_rows:,} rows from {csv_path}")

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lat  = float(row["latitude"])  if row.get("latitude")  else None
            lon  = float(row["longitude"]) if row.get("longitude") else None
            geom = from_shape(Point(lon, lat), srid=4326) if lat and lon else None

            stmt = insert(Property).values(
                parcel_id=row["parcel_id"],
                address=row["address"],
                city=row.get("city"),
                state=row.get("state", "PA"),
                zip_code=row.get("zip_code"),
                county="Montgomery",
                property_type=row.get("property_type", "residential"),
                assessed_value=float(row["assessed_value"]) if row.get("assessed_value") else None,
                owner_name=row.get("owner_name"),
                owner_mailing_address=row.get("owner_mailing_address"),
                latitude=lat,
                longitude=lon,
                geom=geom,
            ).on_conflict_do_update(
                index_elements=["parcel_id"],
                set_={
                    "address":               row["address"],
                    "assessed_value":        float(row["assessed_value"]) if row.get("assessed_value") else None,
                    "owner_name":            row.get("owner_name"),
                    "owner_mailing_address": row.get("owner_mailing_address"),
                    "latitude":              lat,
                    "longitude":             lon,
                    "geom":                  geom,
                },
            )
            session.execute(stmt)
            loaded += 1

            if loaded % COMMIT_EVERY == 0:
                session.commit()

            if loaded % LOG_EVERY == 0:
                pct  = int(100 * loaded / total_rows) if total_rows else 0
                rate = int(loaded / (time.time() - start))
                log(_PREFIX, f"  {loaded:,}/{total_rows:,} ({pct}%)  {rate:,}/s")

    session.commit()
    session.close()
    log(_PREFIX, f"ingested {loaded:,} parcels  ({elapsed(start)})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to parcels CSV")
    args = parser.parse_args()
    ingest(args.file)
