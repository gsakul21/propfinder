"""Shared SQLAlchemy model definitions for worker scripts."""
import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import Boolean, DateTime, Double, ForeignKey, Integer, Numeric, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from workers.common.db import Base


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parcel_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str | None] = mapped_column(Text)
    zip_code: Mapped[str | None] = mapped_column(Text)
    county: Mapped[str] = mapped_column(Text, nullable=False)
    property_type: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Double)
    longitude: Mapped[float | None] = mapped_column(Double)
    geom = mapped_column(Geography(geometry_type="POINT", srid=4326))
    assessed_value: Mapped[float | None] = mapped_column(Numeric)
    owner_name: Mapped[str | None] = mapped_column(Text)
    owner_mailing_address: Mapped[str | None] = mapped_column(Text)
    is_absentee: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    signals: Mapped[list["DistressSignal"]] = relationship("DistressSignal", back_populates="property", cascade="all, delete-orphan")
    score: Mapped["PropertyScore | None"] = relationship("PropertyScore", back_populates="property", uselist=False, cascade="all, delete-orphan")


class DistressSignal(Base):
    __tablename__ = "distress_signals"
    __table_args__ = (UniqueConstraint("property_id", "signal_type"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    signal_type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[float] = mapped_column(Numeric, nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)

    property: Mapped["Property"] = relationship("Property", back_populates="signals")


class PropertyScore(Base):
    __tablename__ = "property_scores"

    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), primary_key=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    tier: Mapped[str] = mapped_column(Text, nullable=False)
    reasons: Mapped[dict] = mapped_column(JSONB, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    property: Mapped["Property"] = relationship("Property", back_populates="score")
