from uuid import UUID

from geoalchemy2.functions import ST_MakeEnvelope, ST_Within
from geoalchemy2.types import Geometry
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.property import Property
from app.models.property_score import PropertyScore


def list_properties(
    db: Session,
    *,
    min_score: int | None = None,
    county: str | None = None,
    property_type: str | None = None,
    distress_types: list[str] | None = None,
    bbox: tuple[float, float, float, float] | None = None,
    page: int = 1,
    limit: int = 50,
) -> tuple[list[Property], int]:
    base = (
        select(Property)
        .join(PropertyScore, Property.id == PropertyScore.property_id, isouter=True)
        .options(selectinload(Property.signals), selectinload(Property.score))
    )

    if min_score is not None:
        base = base.where(PropertyScore.score >= min_score)
    if county:
        base = base.where(Property.county == county)
    if property_type:
        base = base.where(Property.property_type == property_type)
    if distress_types:
        from app.models.distress_signal import DistressSignal
        sub = select(DistressSignal.property_id).where(DistressSignal.signal_type.in_(distress_types))
        base = base.where(Property.id.in_(sub))
    if bbox:
        min_lon, min_lat, max_lon, max_lat = bbox
        envelope = ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
        base = base.where(ST_Within(cast(Property.geom, Geometry), envelope))

    count_q = select(func.count()).select_from(base.subquery())
    total = db.scalar(count_q) or 0

    base = base.order_by(PropertyScore.score.desc().nulls_last())
    base = base.offset((page - 1) * limit).limit(limit)

    rows = db.scalars(base).all()
    return list(rows), total


def get_property(db: Session, property_id: UUID) -> Property | None:
    q = (
        select(Property)
        .where(Property.id == property_id)
        .options(selectinload(Property.signals), selectinload(Property.score))
    )
    return db.scalars(q).first()


def list_for_export(
    db: Session,
    *,
    min_score: int | None = None,
    county: str | None = None,
    property_type: str | None = None,
    distress_types: list[str] | None = None,
) -> list[Property]:
    props, _ = list_properties(
        db,
        min_score=min_score,
        county=county,
        property_type=property_type,
        distress_types=distress_types,
        page=1,
        limit=10000,
    )
    return props
