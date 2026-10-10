"""Extension PostGIS pour la recherche géographique des offres."""

from alembic import op

revision = "0002_postgis"
down_revision = "0001_demo"
branch_labels = None
depends_on = None


def upgrade():
    # Schéma explicite : l'extension est partagée par la base, pas par le schéma courant.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis SCHEMA public")


def downgrade():
    # L'extension est partagée par toute la base : on ne la supprime pas ici.
    pass
