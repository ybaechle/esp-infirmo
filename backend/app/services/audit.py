"""Journal d'audit. Ne jamais y mettre de contenu : identifiants et nature de l'action seulement."""

import uuid

from sqlalchemy.orm import Session

from app.models import AuditLog


def record(
    db: Session,
    actor_id: uuid.UUID | None,
    action: str,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    outcome: str = "success",
) -> None:
    """Ajoute la trace à la transaction en cours : elle est validée avec l'action qu'elle décrit."""
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
        )
    )


def record_now(db: Session, *args, **kwargs) -> None:
    """Pour les lectures et les refus, où aucune transaction ne sera validée ensuite."""
    record(db, *args, **kwargs)
    db.commit()
