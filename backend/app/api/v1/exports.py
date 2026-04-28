import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.property_repository import list_for_export

router = APIRouter()


@router.post("")
def export_csv(
    min_score: int | None = Query(None),
    county: str | None = Query(None),
    property_type: str | None = Query(None),
    distress_types: list[str] | None = Query(None),
    db: Session = Depends(get_db),
):
    props = list_for_export(
        db,
        min_score=min_score,
        county=county,
        property_type=property_type,
        distress_types=distress_types,
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "id", "address", "city", "state", "zip_code", "county", "property_type",
        "score", "tier", "signals", "assessed_value", "owner_name",
        "owner_mailing_address", "is_absentee", "latitude", "longitude",
    ])
    for p in props:
        score_obj = p.score
        writer.writerow([
            p.id,
            p.address,
            p.city,
            p.state,
            p.zip_code,
            p.county,
            p.property_type,
            score_obj.score if score_obj else "",
            score_obj.tier if score_obj else "",
            "|".join(s.signal_type for s in p.signals),
            float(p.assessed_value) if p.assessed_value else "",
            p.owner_name,
            p.owner_mailing_address,
            p.is_absentee,
            p.latitude,
            p.longitude,
        ])

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=propfinder_leads.csv"},
    )
