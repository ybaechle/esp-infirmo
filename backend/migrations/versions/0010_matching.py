"""Disponibilités des remplaçants et index géographique des cabinets."""

import sqlalchemy as sa
from alembic import op

revision = "0010_matching"
down_revision = "0009_offers"
branch_labels = None
depends_on = None

GEO_INDEX = "ix_nursing_offices_geography"


def upgrade():
    op.create_table(
        "availabilities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("end_at > start_at", name="ck_availabilities_dates"),
    )
    op.create_index(
        "ix_availabilities_user_start", "availabilities", ["user_id", "start_at"]
    )
    # Expression identique à app.geo.point : sans elle, ST_DWithin ne peut pas utiliser l'index.
    op.execute(
        f"CREATE INDEX {GEO_INDEX} ON nursing_offices USING gist "
        "((ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography))"
    )


def downgrade():
    op.execute(f"DROP INDEX {GEO_INDEX}")
    op.drop_index("ix_availabilities_user_start", table_name="availabilities")
    op.drop_table("availabilities")
