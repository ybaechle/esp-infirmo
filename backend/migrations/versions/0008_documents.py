"""Documents légaux des professionnels (carte professionnelle, RIB, assurance)."""

import sqlalchemy as sa
from alembic import op

revision = "0008_documents"
down_revision = "0007_nursing_offices"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("doc_type", sa.String(20), nullable=False),
        sa.Column("storage_key", sa.String(32), nullable=False, unique=True),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column(
            "reviewed_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "doc_type", name="uq_documents_user_type"),
        sa.CheckConstraint(
            "doc_type IN ('carte_pro', 'rib', 'assurance')", name="ck_documents_type"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')", name="ck_documents_status"
        ),
    )


def downgrade():
    op.drop_table("documents")
