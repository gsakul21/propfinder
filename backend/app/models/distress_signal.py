import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


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
