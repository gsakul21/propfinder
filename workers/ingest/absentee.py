"""
Absentee ownership detection worker.

Recomputes absentee status for all properties by comparing the property address
to the owner mailing address. No external data file needed.

Run:
  DATABASE_URL=... python -m workers.ingest.absentee
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from workers.common.db import get_session
from workers.common.models import DistressSignal, Property


def _infer_location(prop: Property) -> str | None:
    """Return absentee location category, or None if owner is occupant."""
    if not prop.owner_mailing_address:
        return None
    mail = prop.owner_mailing_address.upper()
    if prop.address.upper() in mail or mail in prop.address.upper():
        return None  # same address → owner-occupied
    if prop.state and prop.state.upper() != "PA":
        return "out_of_state"
    # crude county check: look for county name in mailing address
    if prop.county and prop.county.upper() in mail:
        return "same_county"
    return "different_county"


_LOCATION_SEVERITY = {"same_county": 10, "different_county": 15, "out_of_state": 20}


def recompute() -> None:
    session = get_session()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    props = session.scalars(select(Property)).all()

    updated, signaled = 0, 0
    for prop in props:
        location = _infer_location(prop)
        is_absentee = location is not None
        session.execute(update(Property).where(Property.id == prop.id).values(is_absentee=is_absentee))
        updated += 1

        if is_absentee:
            severity = _LOCATION_SEVERITY[location]
            stmt = insert(DistressSignal).values(
                property_id=prop.id,
                signal_type="absentee",
                severity=severity,
                raw_data={"location": location},
                detected_at=now,
            ).on_conflict_do_update(
                index_elements=["property_id", "signal_type"],
                set_={"severity": severity, "raw_data": {"location": location}, "detected_at": now},
            )
            session.execute(stmt)
            signaled += 1

    session.commit()
    session.close()
    print(f"Processed {updated} properties, {signaled} marked absentee")


if __name__ == "__main__":
    recompute()
