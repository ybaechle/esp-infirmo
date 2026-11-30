"""Candidatures des remplaçants aux offres."""

import sqlalchemy as sa
from alembic import op

revision = "0011_applications"
down_revision = "0010_matching"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "applications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "offer_id",
            sa.Uuid(),
            sa.ForeignKey("offers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("message", sa.String(500)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column(
            "decided_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.UniqueConstraint("offer_id", "user_id", name="uq_applications_offer_user"),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'withdrawn')",
            name="ck_applications_status",
        ),
    )
    op.create_index("ix_applications_user_id", "applications", ["user_id"])


def downgrade():
    op.drop_index("ix_applications_user_id", table_name="applications")
    op.drop_table("applications")
