"""Messages vocaux : transcription chiffrée et statut de validation."""

import sqlalchemy as sa
from alembic import op

revision = "0016_voice_messages"
down_revision = "0015_notifications"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("messages", sa.Column("transcript", sa.Text()))
    op.add_column("messages", sa.Column("transcript_status", sa.String(11)))
    op.create_check_constraint(
        "ck_messages_transcript_status",
        "messages",
        "transcript_status IN ('unavailable', 'ready', 'validated')",
    )


def downgrade():
    op.drop_constraint("ck_messages_transcript_status", "messages", type_="check")
    op.drop_column("messages", "transcript_status")
    op.drop_column("messages", "transcript")
