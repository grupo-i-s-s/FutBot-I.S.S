from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.planned_substitution_model import PlannedSubstitution
from primitives.match_simulation import Match


def apply_planned_substitutions(db: Session, match_id: int, simulation: Match) -> bool:
    """El escritor ya bloqueó el partido; el commit incluye planes y checkpoint."""
    pending = db.scalars(select(PlannedSubstitution).where(
        PlannedSubstitution.match_id == match_id,
        PlannedSubstitution.status == "PENDING",
        PlannedSubstitution.pause_index <= simulation.pause_index,
    ).order_by(PlannedSubstitution.id)).all()
    for plan in pending:
        reason = None
        if plan.pause_index < simulation.pause_index or not simulation.paused:
            plan.status = "EXPIRED"
            reason = "PAUSE_CLOSED"
        else:
            try:
                simulation.substitute(plan.club_id, plan.out_player_id, plan.in_player_id)
                plan.status = "APPLIED"
            except ValueError as exc:
                plan.status = "REJECTED"
                reason = str(exc)
        event = {
            "eventId": f"substitution:{plan.id}",
            "type": "SUBSTITUTION_APPLIED" if plan.status == "APPLIED" else "SUBSTITUTION_REJECTED",
            "clubId": plan.club_id,
            "pauseId": f"{match_id}:{plan.pause_index}",
            "outPlayerId": plan.out_player_id,
            "inPlayerId": plan.in_player_id,
        }
        if reason:
            event["reason"] = reason
        simulation.substitution_events.append(event)
    db.flush()
    return bool(pending)
