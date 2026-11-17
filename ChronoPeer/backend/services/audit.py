"""Append-only audit trail. There is deliberately no update or delete helper."""
from dataclasses import dataclass

from ..models import AuditLog


@dataclass(frozen=True)
class Actor:
    role: str  # "investigator" | "reviewer" | "system"
    name: str


SYSTEM = Actor("system", "ChronoPeer")


def record(db, actor: Actor, case_id, action_type: str, record_id, description: str) -> None:
    db.add(
        AuditLog(
            case_id=case_id,
            actor_role=actor.role,
            actor_name=actor.name,
            action_type=action_type,
            record_id=record_id,
            description=description,
        )
    )
