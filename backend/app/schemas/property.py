from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class ScoreBreakdown(BaseModel):
    tax: int
    foreclosure: int
    absentee: int
    bonus: int
    penalty: int


class SignalDetail(BaseModel):
    signal_type: str
    severity: float
    detected_at: datetime
    raw_data: dict


class PropertySummary(BaseModel):
    id: UUID
    address: str
    city: str | None
    state: str | None
    zip_code: str | None
    latitude: float | None
    longitude: float | None
    score: int
    tier: Literal["hot", "warm", "cold"]
    signals: list[str]
    property_type: str
    assessed_value: float | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class PropertyDetail(PropertySummary):
    parcel_id: str
    county: str
    owner_name: str | None
    owner_mailing_address: str | None
    is_absentee: bool
    score_breakdown: ScoreBreakdown
    signal_details: list[SignalDetail]

    model_config = {"from_attributes": True}


class PropertyListResponse(BaseModel):
    results: list[PropertySummary]
    total: int
    page: int
    limit: int
