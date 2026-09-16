"""Synthetic accounts and revocable sessions."""

from alembic import op
import sqlalchemy as sa

revision = "0001_demo"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "demo_accounts",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(80), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("city", sa.String(80), nullable=False),
        sa.CheckConstraint("role IN ('titulaire', 'remplacant')"),
    )
    op.create_table(
        "demo_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column(
            "account_id",
            sa.String(32),
            sa.ForeignKey("demo_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.Integer(), nullable=False),
    )


def downgrade():
    op.drop_table("demo_sessions")
    op.drop_table("demo_accounts")
