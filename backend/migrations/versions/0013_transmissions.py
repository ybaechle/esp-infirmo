"""Patients d'un cabinet et transmissions chiffrées à durée de vie limitée."""

import sqlalchemy as sa
from alembic import op

revision = "0013_transmissions"
down_revision = "0012_messaging"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "patients",
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
        sa.Column("first_name", sa.Text()),
        sa.Column("last_name", sa.Text()),
        sa.Column("birth_date", sa.Text()),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("anonymized_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_patients_office_id", "patients", ["office_id"])
    op.create_table(
        "transmissions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "patient_id",
            sa.Uuid(),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_transmissions_patient_created",
        "transmissions",
        ["patient_id", "created_at"],
    )
    op.create_index("ix_transmissions_expires_at", "transmissions", ["expires_at"])


def downgrade():
    op.drop_index("ix_transmissions_expires_at", table_name="transmissions")
    op.drop_index("ix_transmissions_patient_created", table_name="transmissions")
    op.drop_table("transmissions")
    op.drop_index("ix_patients_office_id", table_name="patients")
    op.drop_table("patients")
