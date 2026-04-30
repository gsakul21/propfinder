"""
Fetches Montgomery County sheriff sale listings (active foreclosure events).

Source: CivilView — the Montgomery County Sheriff's official listing platform
  https://salesweb.civilview.com/Sales/SalesSearch?countyId=23

The page serves a static HTML table of all upcoming sales (no JS required).
Table columns (verified 2026-04-28):
  0: View Details  1: Sheriff #  2: Township  3: Sales Date
  4: Plaintiff     5: Defendant  6: Address

The address in column 6 has the form "80 Forrest Court Royersford PA 19468".
This fetcher strips the city/state/zip and matches the street address against
parcels already loaded in the database.

Run parcels ingest BEFORE this step so there are records to match against.

Output columns (matches workers/ingest/foreclosure.py):
  parcel_id, filing_date, case_number, stage, auction_date

Run:
  DATABASE_URL=... python -m workers.fetch.foreclosures --out data/foreclosures.csv
"""
import argparse
import csv
import re
import sys
from datetime import date, datetime
from pathlib import Path

import time

import requests
from bs4 import BeautifulSoup
from sqlalchemy import select

from workers.common.log import elapsed, log

_PREFIX = "fetch_foreclosures"

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from workers.common.db import get_session
from workers.common.models import Property

SHERIFF_URL = "https://salesweb.civilview.com/Sales/SalesSearch?countyId=23"

# Column indices in the CivilView table (0-based)
COL_SHERIFF  = 1
COL_DATE     = 3
COL_ADDRESS  = 6

DATE_FMTS = ("%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y")


def _parse_date(raw: str) -> str | None:
    raw = raw.strip()
    for fmt in DATE_FMTS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    return None


# PASDA stores abbreviated street types; CivilView uses full words. Map common ones.
_STREET_ABBREV = {
    "AVENUE": "AVE", "BOULEVARD": "BLVD", "CIRCLE": "CIR", "COURT": "CT",
    "DRIVE": "DR", "EXPRESSWAY": "EXPY", "HIGHWAY": "HWY", "LANE": "LN",
    "PARKWAY": "PKWY", "PLACE": "PL", "ROAD": "RD", "SQUARE": "SQ",
    "STREET": "ST", "TERRACE": "TER", "TRAIL": "TRL", "WAY": "WAY",
}


def _normalize_street_type(word: str) -> str:
    return _STREET_ABBREV.get(word.upper(), word.upper())


def _parse_address(cell: str) -> tuple[str, str | None]:
    """
    Convert "80 Forrest Court Royersford PA 19468" →
    ("80 FORREST CT", "19468") for DB lookup.

    Normalizes full street type words to PASDA abbreviations so the ILIKE
    prefix matches what's stored in the database.
    """
    zip_m = re.search(r"\b(\d{5})\b", cell)
    zip_code = zip_m.group(1) if zip_m else None

    # Strip " PA XXXXX..." from the end
    street_city = re.sub(r"\s+\bPA\b\s+\d{5}.*$", "", cell, flags=re.IGNORECASE).strip()

    parts = street_city.split()
    # Normalize street type word (3rd token is typically the street type)
    parts = [_normalize_street_type(p) if i == 2 else p.upper() for i, p in enumerate(parts)]

    if len(parts) >= 3:
        prefix = " ".join(parts[:3])
    elif len(parts) >= 2:
        prefix = " ".join(parts[:2])
    else:
        prefix = street_city.upper()

    return prefix, zip_code


def _address_to_parcel_id(address_cell: str, db) -> str | None:
    prefix, zip_code = _parse_address(address_cell)
    if len(prefix) < 4:
        return None

    q = select(Property).where(Property.address.ilike(f"{prefix}%"))
    if zip_code:
        q = q.where(Property.zip_code == zip_code)

    row = db.scalars(q).first()
    return str(row.parcel_id) if row else None


def fetch_all(out_path: str) -> int:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    http = requests.Session()
    http.headers["User-Agent"] = "PropFinder/1.0 public-data-ingestion"
    db = get_session()

    today      = date.today().isoformat()
    fieldnames = ["parcel_id", "filing_date", "case_number", "stage", "auction_date"]
    seen: set[str] = set()
    matched = 0
    scanned = 0

    start = time.time()
    log(_PREFIX, f"fetching CivilView: {SHERIFF_URL}")
    resp = http.get(SHERIFF_URL, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    # The page has 2 tables. Table 0 is a title banner. Table 1 has the listings.
    tables = soup.find_all("table")
    data_table = next(
        (t for t in tables if len(t.find_all("tr")) > 10),
        None,
    )
    if data_table is None:
        log(_PREFIX, "WARNING: data table not found on CivilView page — layout may have changed")
        db.close()
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=fieldnames).writeheader()
        return 0

    rows = data_table.find_all("tr")
    log(_PREFIX, f"found {len(rows) - 1} sale listings — matching to DB parcels...")

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows[1:]:  # skip header
            cells = [td.get_text(" ", strip=True) for td in row.find_all(["td", "th"])]
            if len(cells) <= COL_ADDRESS:
                continue
            scanned += 1

            address_cell = cells[COL_ADDRESS]
            if not address_cell:
                continue

            parcel_id = _address_to_parcel_id(address_cell, db)
            if not parcel_id or parcel_id in seen:
                continue

            case_num     = cells[COL_SHERIFF].strip() if len(cells) > COL_SHERIFF else ""
            auction_date = _parse_date(cells[COL_DATE]) if len(cells) > COL_DATE else None

            writer.writerow({
                "parcel_id":    parcel_id,
                "filing_date":  today,
                "case_number":  case_num,
                "stage":        "auction",
                "auction_date": auction_date or "",
            })
            seen.add(parcel_id)
            matched += 1

    db.close()
    log(_PREFIX, f"scanned {scanned:,} listings — matched {matched:,} to DB parcels → {out_path}  ({elapsed(start)})")
    if matched == 0 and scanned > 0:
        log(_PREFIX, "NOTE: 0 matches is expected until parcel ingest has run and populated the DB")
    return matched


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/foreclosures.csv")
    args = parser.parse_args()
    fetch_all(args.out)
