"""Sessions d'authentification avec refresh tokens à rotation."""

import sqlalchemy as sa
from alembic import op

revision = "0004_auth_sessions"
down_revision = "0003_users"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("access_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("refresh_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("access_expires_at", sa.Integer(), nullable=False),
        sa.Column("refresh_expires_at", sa.Integer(), nullable=False),
        sa.Column("rotated_at", sa.Integer()),
        sa.Column("revoked_at", sa.Integer()),
    )
    op.create_index("ix_auth_sessions_family_id", "auth_sessions", ["family_id"])


def downgrade():
    op.drop_index("ix_auth_sessions_family_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
