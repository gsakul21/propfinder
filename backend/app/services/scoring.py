"""Deterministic scoring engine. Follows the spec exactly."""
from datetime import datetime, timezone

from app.models.distress_signal import DistressSignal
from app.models.property import Property
from app.models.property_score import PropertyScore


def _tax_score(signal: DistressSignal) -> int:
    years = signal.raw_data.get("years_delinquent", 0)
    if years >= 2:
        return 35
    if years >= 1:
        return 25
    return 15


def _foreclosure_score(signal: DistressSignal) -> int:
    stage = signal.raw_data.get("stage", "filing")
    if stage == "auction":
        return 40
    if stage == "active":
        return 35
    return 30


def _absentee_score(signal: DistressSignal) -> int:
    location = signal.raw_data.get("location", "same_county")
    if location == "out_of_state":
        return 20
    if location == "different_county":
        return 15
    return 10


_SIGNAL_SCORERS = {
    "tax_delinquency": _tax_score,
    "foreclosure": _foreclosure_score,
    "absentee": _absentee_score,
}


def compute_score(prop: Property) -> PropertyScore:
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    tax, foreclosure, absentee = 0, 0, 0
    active_signals: list[str] = []

    for signal in prop.signals:
        if signal.expires_at and signal.expires_at < now:
            continue
        scorer = _SIGNAL_SCORERS.get(signal.signal_type)
        if scorer is None:
            continue
        pts = scorer(signal)
        if signal.signal_type == "tax_delinquency":
            tax = pts
        elif signal.signal_type == "foreclosure":
            foreclosure = pts
        elif signal.signal_type == "absentee":
            absentee = pts
        active_signals.append(signal.signal_type)

    signal_count = sum(1 for v in [tax, foreclosure, absentee] if v > 0)
    bonus = 15 if signal_count >= 3 else (10 if signal_count >= 2 else 0)

    # Conflict penalties
    penalty = 0
    for signal in prop.signals:
        rd = signal.raw_data
        if rd.get("recent_transfer"):
            penalty += 20
        if rd.get("foreclosure_resolved"):
            penalty += 30

    raw = tax + foreclosure + absentee + bonus - penalty
    final = max(0, min(100, raw))

    tier = "hot" if final >= 80 else ("warm" if final >= 50 else "cold")

    reasons = {
        "tax": tax,
        "foreclosure": foreclosure,
        "absentee": absentee,
        "bonus": bonus,
        "penalty": penalty,
    }

    return PropertyScore(
        property_id=prop.id,
        score=final,
        tier=tier,
        reasons=reasons,
        computed_at=now,
    )
