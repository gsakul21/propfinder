"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-28
"""
from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("parcel_id", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("city", sa.Text()),
        sa.Column("state", sa.Text()),
        sa.Column("zip_code", sa.Text()),
        sa.Column("county", sa.Text(), nullable=False),
        sa.Column("property_type", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Double()),
        sa.Column("longitude", sa.Double()),
        sa.Column("geom", geoalchemy2.types.Geography(geometry_type="POINT", srid=4326)),
        sa.Column("assessed_value", sa.Numeric()),
        sa.Column("owner_name", sa.Text()),
        sa.Column("owner_mailing_address", sa.Text()),
        sa.Column("is_absentee", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parcel_id"),
    )
    op.create_index("ix_properties_county", "properties", ["county"])
    op.create_index("ix_properties_property_type", "properties", ["property_type"])
    op.create_index("ix_properties_geom", "properties", ["geom"], postgresql_using="gist")

    op.create_table(
        "distress_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_type", sa.Text(), nullable=False),
        sa.Column("severity", sa.Numeric(), nullable=False),
        sa.Column("raw_data", postgresql.JSONB(), nullable=False),
        sa.Column("detected_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime()),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("property_id", "signal_type"),
    )
    op.create_index("ix_distress_signals_property_id", "distress_signals", ["property_id"])
    op.create_index("ix_distress_signals_signal_type", "distress_signals", ["signal_type"])

    op.create_table(
        "property_scores",
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("tier", sa.Text(), nullable=False),
        sa.Column("reasons", postgresql.JSONB(), nullable=False),
        sa.Column("computed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("property_id"),
    )
    op.create_index("ix_property_scores_score", "property_scores", ["score"])
    op.create_index("ix_property_scores_tier", "property_scores", ["tier"])


def downgrade() -> None:
    op.drop_table("property_scores")
    op.drop_table("distress_signals")
    op.drop_table("properties")
