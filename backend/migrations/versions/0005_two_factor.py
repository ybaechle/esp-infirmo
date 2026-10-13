"""2FA optionnelle par e-mail ou SMS."""

import sqlalchemy as sa
from alembic import op

revision = "0005_two_factor"
down_revision = "0004_auth_sessions"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("phone", sa.String(20)))
    op.add_column("users", sa.Column("two_factor_channel", sa.String(5)))
    op.create_check_constraint(
        "ck_users_two_factor_channel",
        "users",
        "two_factor_channel IN ('email', 'sms')",
    )
    op.create_table(
        "two_factor_challenges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("purpose", sa.String(10), nullable=False),
        sa.Column("channel", sa.String(5), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade():
    op.drop_table("two_factor_challenges")
    op.drop_constraint("ck_users_two_factor_channel", "users", type_="check")
    op.drop_column("users", "two_factor_channel")
    op.drop_column("users", "phone")
