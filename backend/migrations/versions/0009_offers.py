"""Offres de remplacement publiées par les cabinets."""

import sqlalchemy as sa
from alembic import op

revision = "0009_offers"
down_revision = "0008_documents"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "offers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "office_id",
            sa.Uuid(),
            sa.ForeignKey("nursing_offices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("description", sa.String(2000), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_till", sa.DateTime(timezone=True), nullable=False),
        sa.Column("turnover", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("end_at > start_at", name="ck_offers_dates"),
        sa.CheckConstraint("valid_till <= start_at", name="ck_offers_valid_till"),
        sa.CheckConstraint("turnover >= 0", name="ck_offers_turnover"),
        sa.CheckConstraint(
            "status IN ('open', 'filled', 'in_progress', 'completed', 'cancelled')",
            name="ck_offers_status",
        ),
    )
    op.create_index("ix_offers_status_start", "offers", ["status", "start_at"])
    op.create_index("ix_offers_office_id", "offers", ["office_id"])
    op.create_table(
        "offer_cares",
        sa.Column(
            "offer_id",
            sa.Uuid(),
            sa.ForeignKey("offers.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "care_id",
            sa.Integer(),
            sa.ForeignKey("cares.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )


def downgrade():
    op.drop_table("offer_cares")
    op.drop_index("ix_offers_office_id", table_name="offers")
    op.drop_index("ix_offers_status_start", table_name="offers")
    op.drop_table("offers")
