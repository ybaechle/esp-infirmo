"""Comptes professionnels (infirmiers titulaires et remplaçants)."""

import sqlalchemy as sa
from alembic import op

revision = "0003_users"
down_revision = "0002_postgis"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("first_name", sa.String(80), nullable=False),
        sa.Column("last_name", sa.String(80), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("order_number", sa.String(11), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("role IN ('titulaire', 'remplacant')", name="ck_users_role"),
        sa.CheckConstraint(
            "status IN ('active', 'suspended', 'deleted')", name="ck_users_status"
        ),
    )


def downgrade():
    op.drop_table("users")
