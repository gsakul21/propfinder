import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import Boolean, DateTime, Double, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


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
