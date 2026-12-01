"""Cycle de vie d'une mission (F3.4) : une seule table de transitions autorisées."""

from app.errors import ApiError

TRANSITIONS = {
    ("open", "cancel"): "cancelled",
    ("filled", "cancel"): "cancelled",
    ("filled", "start"): "in_progress",
    ("in_progress", "complete"): "completed",
}


def next_status(current: str, action: str) -> str:
    try:
        return TRANSITIONS[(current, action)]
    except KeyError:
        raise ApiError(
            409, "invalid_transition", f"Cannot {action} a mission that is {current}"
        ) from None
