"""
Absentee ownership detection worker.

Recomputes absentee status for all properties by comparing the property address
to the owner mailing address. No external data file needed.

Run:
  DATABASE_URL=... python -m workers.ingest.absentee
"""
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from workers.common.db import get_session
from workers.common.log import elapsed, log
from workers.common.models import DistressSignal, Property

_PREFIX      = "ingest_absentee"
COMMIT_EVERY = 2_000
LOG_EVERY    = 10_000


_PO_BOX_RE = re.compile(r'\bP\.?\s*O\.?\s*BOX\b', re.IGNORECASE)
_ZIP_RE     = re.compile(r'\b(\d{5})\b')


def _infer_location(prop: Property) -> str | None:
    """Return absentee location category, or None if owner is occupant."""
    if not prop.owner_mailing_address:
        return None

    mail = prop.owner_mailing_address.upper()
    addr = prop.address.upper()

    # Direct address match → owner-occupied
    if addr in mail or mail in addr:
        return None

    # PO BOX: we can't confirm the owner doesn't live at the property.
    # Only flag if the PO BOX is in a clearly different area.
    if _PO_BOX_RE.search(mail):
        mail_zip = (_ZIP_RE.search(mail) or type('', (), {'group': lambda *_: None})()).group(1)
        prop_zip = (prop.zip_code or "").strip()
        if mail_zip and prop_zip and mail_zip == prop_zip:
            return None  # same zip — inconclusive
        # Compare first word of city (e.g. "ABINGTON" from "Abington Township")
        if prop.city:
            city_first = prop.city.upper().split()[0]
            if city_first in mail:
                return None  # same city — inconclusive

    if prop.state and prop.state.upper() != "PA":
        return "out_of_state"
    if prop.county and prop.county.upper() in mail:
        return "same_county"
    return "different_county"


_LOCATION_SEVERITY = {"same_county": 10, "different_county": 15, "out_of_state": 20}

_BULK = 5_000


def recompute() -> None:
    start   = time.time()
    session = get_session()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    props = session.scalars(select(Property)).all()
    total = len(props)
    log(_PREFIX, f"scanning {total:,} properties for absentee ownership...")

    absentee_ids: list  = []
    signals: list[dict] = []

    for i, prop in enumerate(props, 1):
        location    = _infer_location(prop)
        is_absentee = location is not None
        if is_absentee:
            absentee_ids.append(prop.id)
            signals.append({
                "property_id": prop.id,
                "signal_type": "absentee",
                "severity":    _LOCATION_SEVERITY[location],
                "raw_data":    {"location": location},
                "detected_at": now,
            })

        if i % LOG_EVERY == 0:
            pct  = int(100 * i / total) if total else 0
            rate = int(i / (time.time() - start))
            log(_PREFIX, f"  {i:,}/{total:,} ({pct}%)  {rate:,}/s  absentee so far: {len(absentee_ids):,}")

    log(_PREFIX, f"  classified {total:,} — writing {len(absentee_ids):,} absentee flags to DB...")

    # Delta update: only touch rows whose is_absentee flag actually changes.
    # On a fresh DB all properties are false, so we only write the ~42k absentee rows.
    # On re-runs, only the diff is written — avoids a full 275k-row table UPDATE.
    new_absentee     = set(absentee_ids)
    current_absentee = set(
        session.scalars(select(Property.id).where(Property.is_absentee == True)).all()
    )
    to_set_true  = list(new_absentee - current_absentee)
    to_set_false = list(current_absentee - new_absentee)

    for off in range(0, len(to_set_true), _BULK):
        session.execute(update(Property).where(Property.id.in_(to_set_true[off:off+_BULK])).values(is_absentee=True))
    for off in range(0, len(to_set_false), _BULK):
        session.execute(update(Property).where(Property.id.in_(to_set_false[off:off+_BULK])).values(is_absentee=False))

    for off in range(0, len(signals), _BULK):
        batch = signals[off:off+_BULK]
        stmt  = insert(DistressSignal).values(batch)
        stmt  = stmt.on_conflict_do_update(
            index_elements=["property_id", "signal_type"],
            set_={
                "severity":    stmt.excluded.severity,
                "raw_data":    stmt.excluded.raw_data,
                "detected_at": stmt.excluded.detected_at,
            },
        )
        session.execute(stmt)

    session.commit()
    session.close()
    log(_PREFIX, f"processed {total:,} properties — {len(absentee_ids):,} marked absentee  ({elapsed(start)})")


if __name__ == "__main__":
    recompute()
