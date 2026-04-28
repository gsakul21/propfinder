"""
Nightly scoring recomputation worker.

Recomputes scores for all properties with signals.

Run:
  DATABASE_URL=... python -m workers.scoring.recompute
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from workers.common.db import get_session
from workers.common.models import DistressSignal, Property, PropertyScore


def _tax_score(signal) -> int:
    years = signal.raw_data.get("years_delinquent", 0)
    return 35 if years >= 2 else (25 if years >= 1 else 15)


def _foreclosure_score(signal) -> int:
    stage = signal.raw_data.get("stage", "filing")
    return 40 if stage == "auction" else (35 if stage == "active" else 30)


def _absentee_score(signal) -> int:
    loc = signal.raw_data.get("location", "same_county")
    return 20 if loc == "out_of_state" else (15 if loc == "different_county" else 10)


_SCORERS = {"tax_delinquency": _tax_score, "foreclosure": _foreclosure_score, "absentee": _absentee_score}


def _compute(prop) -> dict:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    tax, foreclosure, absentee = 0, 0, 0

    for sig in prop.signals:
        if sig.expires_at and sig.expires_at < now:
            continue
        scorer = _SCORERS.get(sig.signal_type)
        if not scorer:
            continue
        pts = scorer(sig)
        if sig.signal_type == "tax_delinquency":
            tax = pts
        elif sig.signal_type == "foreclosure":
            foreclosure = pts
        elif sig.signal_type == "absentee":
            absentee = pts

    n = sum(1 for v in [tax, foreclosure, absentee] if v > 0)
    bonus = 15 if n >= 3 else (10 if n >= 2 else 0)
    penalty = sum(
        (20 if s.raw_data.get("recent_transfer") else 0) + (30 if s.raw_data.get("foreclosure_resolved") else 0)
        for s in prop.signals
    )

    raw = tax + foreclosure + absentee + bonus - penalty
    final = max(0, min(100, raw))
    tier = "hot" if final >= 80 else ("warm" if final >= 50 else "cold")

    return {
        "score": final,
        "tier": tier,
        "reasons": {"tax": tax, "foreclosure": foreclosure, "absentee": absentee, "bonus": bonus, "penalty": penalty},
        "computed_at": now,
    }


def recompute() -> None:
    session = get_session()
    props = session.scalars(
        select(Property).options(selectinload(Property.signals))
    ).all()

    count = 0
    for prop in props:
        result = _compute(prop)
        stmt = insert(PropertyScore).values(
            property_id=prop.id,
            **result,
        ).on_conflict_do_update(
            index_elements=["property_id"],
            set_=result,
        )
        session.execute(stmt)
        count += 1

    session.commit()
    session.close()
    print(f"Recomputed scores for {count} properties")


if __name__ == "__main__":
    recompute()
