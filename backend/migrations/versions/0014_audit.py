"""Journal d'audit, immuable pendant sa durée de rétention."""

import sqlalchemy as sa
from alembic import op

revision = "0014_audit"
down_revision = "0013_transmissions"
branch_labels = None
depends_on = None

RETENTION_DAYS = 365


def upgrade():
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", sa.Uuid()),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("resource_type", sa.String(30)),
        sa.Column("resource_id", sa.Uuid()),
        sa.Column("outcome", sa.String(10), nullable=False),
        sa.CheckConstraint(
            "outcome IN ('success', 'denied', 'failure')", name="ck_audit_logs_outcome"
        ),
    )
    op.create_index("ix_audit_logs_at", "audit_logs", ["at"])
    op.create_index("ix_audit_logs_actor_at", "audit_logs", ["actor_id", "at"])
    # UPDATE interdit ; DELETE autorisé seulement une fois la rétention écoulée (purge RGPD).
    op.execute(
        f"""
        CREATE FUNCTION audit_logs_immutable() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'UPDATE' OR OLD.at > now() - interval '{RETENTION_DAYS} days' THEN
                RAISE EXCEPTION 'audit_logs is append-only during its retention period';
            END IF;
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER audit_logs_immutable BEFORE UPDATE OR DELETE ON audit_logs "
        "FOR EACH ROW EXECUTE FUNCTION audit_logs_immutable()"
    )


def downgrade():
    op.execute("DROP TRIGGER audit_logs_immutable ON audit_logs")
    op.execute("DROP FUNCTION audit_logs_immutable()")
    # Le trigger retiré, la table peut être supprimée malgré sa rétention.
    op.drop_index("ix_audit_logs_actor_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_at", table_name="audit_logs")
    op.drop_table("audit_logs")
