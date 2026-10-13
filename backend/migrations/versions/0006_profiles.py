"""Profils professionnels, zone d'intervention et référentiel de soins."""

import sqlalchemy as sa
from alembic import op

revision = "0006_profiles"
down_revision = "0005_two_factor"
branch_labels = None
depends_on = None

CARES = [
    ("pansements", "Pansements"),
    ("injections", "Injections"),
    ("prises_de_sang", "Prises de sang"),
    ("perfusions", "Perfusions"),
    ("toilette", "Toilette et nursing"),
    ("glycemie", "Surveillance de la glycémie"),
    ("post_operatoire", "Suivi post-opératoire"),
    ("soins_palliatifs", "Soins palliatifs"),
]


def upgrade():
    cares = op.create_table(
        "cares",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False, unique=True),
        sa.Column("label", sa.String(80), nullable=False),
    )
    op.bulk_insert(cares, [{"code": c, "label": label} for c, label in CARES])
    op.create_table(
        "profiles",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("city", sa.String(80)),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("radius_km", sa.Integer()),
        sa.Column("min_turnover", sa.Integer()),
        sa.Column("bio", sa.String(1000)),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_profiles_latitude"),
        sa.CheckConstraint(
            "longitude BETWEEN -180 AND 180", name="ck_profiles_longitude"
        ),
        sa.CheckConstraint("radius_km BETWEEN 1 AND 200", name="ck_profiles_radius"),
        sa.CheckConstraint("min_turnover >= 0", name="ck_profiles_min_turnover"),
    )
    op.create_table(
        "profile_cares",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("profiles.user_id", ondelete="CASCADE"),
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
    op.drop_table("profile_cares")
    op.drop_table("profiles")
    op.drop_table("cares")
