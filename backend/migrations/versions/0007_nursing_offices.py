"""Cabinets infirmiers et appartenance des membres."""

import sqlalchemy as sa
from alembic import op

revision = "0007_nursing_offices"
down_revision = "0006_profiles"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "nursing_offices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("siret", sa.String(14), unique=True),
        sa.Column("address", sa.String(200), nullable=False),
        sa.Column("postcode", sa.String(5), nullable=False),
        sa.Column("city", sa.String(80), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_offices_latitude"),
        sa.CheckConstraint(
            "longitude BETWEEN -180 AND 180", name="ck_offices_longitude"
        ),
    )
    op.create_table(
        "office_members",
        sa.Column(
            "office_id",
            sa.Uuid(),
            sa.ForeignKey("nursing_offices.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("member_role", sa.String(10), nullable=False),
        sa.CheckConstraint(
            "member_role IN ('owner', 'member')", name="ck_members_role"
        ),
    )
    op.create_index("ix_office_members_user_id", "office_members", ["user_id"])


def downgrade():
    op.drop_index("ix_office_members_user_id", table_name="office_members")
    op.drop_table("office_members")
    op.drop_table("nursing_offices")
