from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.property_repository import get_property, list_properties
from app.schemas.property import PropertyDetail, PropertyListResponse, PropertySummary, ScoreBreakdown, SignalDetail

router = APIRouter()


def _to_summary(prop) -> PropertySummary:
    score_obj = prop.score
    return PropertySummary(
        id=prop.id,
        address=prop.address,
        city=prop.city,
        state=prop.state,
        zip_code=prop.zip_code,
        latitude=prop.latitude,
        longitude=prop.longitude,
        score=score_obj.score if score_obj else 0,
        tier=score_obj.tier if score_obj else "cold",
        signals=[s.signal_type for s in prop.signals],
        property_type=prop.property_type,
        assessed_value=float(prop.assessed_value) if prop.assessed_value else None,
        updated_at=prop.updated_at,
    )


def _to_detail(prop) -> PropertyDetail:
    summary = _to_summary(prop)
    score_obj = prop.score
    reasons = score_obj.reasons if score_obj else {}
    breakdown = ScoreBreakdown(
        tax=reasons.get("tax", 0),
        foreclosure=reasons.get("foreclosure", 0),
        absentee=reasons.get("absentee", 0),
        bonus=reasons.get("bonus", 0),
        penalty=reasons.get("penalty", 0),
    )
    signal_details = [
        SignalDetail(
            signal_type=s.signal_type,
            severity=float(s.severity),
            detected_at=s.detected_at,
            raw_data=s.raw_data,
        )
        for s in prop.signals
    ]
    return PropertyDetail(
        **summary.model_dump(),
        parcel_id=prop.parcel_id,
        county=prop.county,
        owner_name=prop.owner_name,
        owner_mailing_address=prop.owner_mailing_address,
        is_absentee=prop.is_absentee,
        score_breakdown=breakdown,
        signal_details=signal_details,
    )


@router.get("", response_model=PropertyListResponse)
def list_props(
    min_score: int | None = Query(None),
    county: str | None = Query(None),
    property_type: str | None = Query(None),
    distress_types: list[str] | None = Query(None),
    bbox: str | None = Query(None, description="min_lon,min_lat,max_lon,max_lat"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    parsed_bbox = None
    if bbox:
        try:
            parts = [float(x) for x in bbox.split(",")]
            if len(parts) != 4:
                raise ValueError
            parsed_bbox = tuple(parts)
        except ValueError:
            raise HTTPException(status_code=422, detail="bbox must be min_lon,min_lat,max_lon,max_lat")

    props, total = list_properties(
        db,
        min_score=min_score,
        county=county,
        property_type=property_type,
        distress_types=distress_types,
        bbox=parsed_bbox,
        page=page,
        limit=limit,
    )
    return PropertyListResponse(
        results=[_to_summary(p) for p in props],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{property_id}", response_model=PropertyDetail)
def get_prop(property_id: UUID, db: Session = Depends(get_db)):
    prop = get_property(db, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return _to_detail(prop)
