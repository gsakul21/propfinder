"""
Fetches Montgomery County residential parcel/assessment data from PASDA
(Pennsylvania Spatial Data Access, Penn State).

Source: PASDA MontgomeryCounty MapServer Layer 14
  https://www.pasda.psu.edu/uci/DataSummary.aspx?dataset=1960
  Updated monthly from the county assessment database.

Verified field names (from live schema query 2026-04-28):
  PARCEL       → parcel_id     (12-char string, no hyphens, e.g. "300034228005")
  LOCATION1    → address       (pre-assembled: "1183 JERICHO RD")
  Muni_Name    → city          ("Abington Township")
  LOC_ZIP1_Z   → zip_code      (property location zip)
  CLASS        → class_code    ("R" = residential)
  TOTAL_ASSE   → assessed_value
  OWN1         → owner_name
  ADDR1        → owner mailing street line
  ADDR3        → owner mailing city/state/zip  ("ABINGTON PA 19001")

Output columns (matches workers/ingest/parcels.py):
  parcel_id, address, city, state, zip_code, property_type,
  assessed_value, owner_name, owner_mailing_address, latitude, longitude

Run:
  python -m workers.fetch.parcels --out data/parcels.csv
"""
import argparse
import csv
import time
from pathlib import Path

import requests

from workers.common.log import elapsed, log

_PREFIX = "fetch_parcels"

# ── Configuration ─────────────────────────────────────────────────────────────
ARCGIS_URL = (
    "https://mapservices.pasda.psu.edu/server/rest/services"
    "/pasda/MontgomeryCounty/MapServer/14/query"
)

# Verified against live schema. If the service is updated and fields change,
# run: ARCGIS_URL + ?f=json&where=1%3D1&outFields=*&resultRecordCount=1
FIELDS = {
    "parcel_id":   "PARCEL",
    "location":    "LOCATION1",   # pre-assembled address "1183 JERICHO RD"
    "city":        "Muni_Name",   # municipality name "Abington Township"
    "zip":         "LOC_ZIP1_Z",  # property zip code
    "class_code":  "CLASS",       # "R" = residential
    "assessed":    "TOTAL_ASSE",
    "owner":       "OWN1",
    "owner_mail":  "ADDR1",       # owner mailing street line
    "owner_city":  "ADDR3",       # owner mailing city/state/zip
}

RESIDENTIAL_WHERE = "CLASS = 'R'"
PAGE_SIZE   = 1000
DELAY_S     = 0.5
# Set to None to fetch all residential parcels (~150k+). Use a number like
# 50_000 to cap early and prove the pipeline end-to-end before a full run.
DEFAULT_MAX = 50_000
# ──────────────────────────────────────────────────────────────────────────────


def _centroid(geometry: dict) -> tuple[float | None, float | None]:
    """Return (lat, lon) from ArcGIS polygon geometry rings."""
    if not geometry:
        return None, None
    # Point geometry
    if "x" in geometry and "y" in geometry:
        return geometry["y"], geometry["x"]
    # Polygon → naive centroid from first ring
    rings = geometry.get("rings", [])
    if rings:
        pts = rings[0]
        return (
            sum(p[1] for p in pts) / len(pts),
            sum(p[0] for p in pts) / len(pts),
        )
    return None, None


def fetch_all(out_path: str, max_records: int | None = DEFAULT_MAX) -> int:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = "PropFinder/1.0 public-data-ingestion"

    out_fields = ",".join(v for v in FIELDS.values())
    fieldnames = [
        "parcel_id", "address", "city", "state", "zip_code",
        "property_type", "assessed_value", "owner_name",
        "owner_mailing_address", "latitude", "longitude",
    ]

    if max_records:
        log(_PREFIX, f"capped at {max_records:,} records (pass max_records=None for full county)")
    else:
        log(_PREFIX, "fetching all residential parcels — this may take several minutes")

    total = 0
    start = time.time()
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        offset = 0
        while True:
            if max_records and total >= max_records:
                log(_PREFIX, f"cap reached — stopping at {total:,} records")
                break
            resp = session.get(
                ARCGIS_URL,
                params={
                    "where":             RESIDENTIAL_WHERE,
                    "outFields":         out_fields,
                    "returnGeometry":    "true",
                    "returnCentroid":    "true",
                    "outSR":             "4326",
                    "f":                 "json",
                    "resultOffset":      offset,
                    "resultRecordCount": (
                        min(PAGE_SIZE, max_records - total)
                        if max_records else PAGE_SIZE
                    ),
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                code = data["error"].get("code")
                msg  = data["error"].get("message", "")
                raise RuntimeError(
                    f"ArcGIS error {code}: {msg}\n"
                    f"Re-inspect schema: {ARCGIS_URL}"
                    f"?f=json&where=1%3D1&outFields=*&resultRecordCount=1"
                )

            features = data.get("features", [])
            if not features:
                break

            for feat in features:
                a = feat.get("attributes", {})

                # Coordinates: prefer centroid key, fall back to polygon rings
                geom       = feat.get("centroid") or feat.get("geometry", {})
                lat, lon   = _centroid(geom)

                mail1      = str(a.get(FIELDS["owner_mail"]) or "").strip()
                mail_city  = str(a.get(FIELDS["owner_city"]) or "").strip()
                full_mail  = ", ".join(filter(None, [mail1, mail_city]))

                writer.writerow({
                    "parcel_id":             a.get(FIELDS["parcel_id"], ""),
                    "address":               str(a.get(FIELDS["location"]) or "").strip(),
                    "city":                  str(a.get(FIELDS["city"]) or "").strip(),
                    "state":                 "PA",
                    "zip_code":              str(a.get(FIELDS["zip"]) or "").strip(),
                    "property_type":         "residential",
                    "assessed_value":        a.get(FIELDS["assessed"]),
                    "owner_name":            str(a.get(FIELDS["owner"]) or "").strip(),
                    "owner_mailing_address": full_mail,
                    "latitude":              lat,
                    "longitude":             lon,
                })
                total += 1

            secs = time.time() - start
            rate = int(total / secs) if secs > 0 else 0
            if max_records:
                pct = int(100 * total / max_records)
                log(_PREFIX, f"offset={offset:,}  batch={len(features):,}  total={total:,}/{max_records:,} ({pct}%)  {rate}/s")
            else:
                log(_PREFIX, f"offset={offset:,}  batch={len(features):,}  total={total:,}  {rate}/s")

            if not data.get("exceededTransferLimit"):
                break
            offset += PAGE_SIZE
            time.sleep(DELAY_S)

    log(_PREFIX, f"wrote {total:,} residential parcels → {out_path}  ({elapsed(start)})")
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/parcels.csv")
    args = parser.parse_args()
    fetch_all(args.out)
