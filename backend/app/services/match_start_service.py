from copy import deepcopy
from datetime import datetime

from sqlalchemy.orm import Session

from app.errors import AppError
from app.models.matches_model import Matches
from app.repository import matches_repository
from app.services.match_builder_service import build_match
from app.services.match_snapshot_service import read_snapshot
from primitives.match_simulation import Match


PENDING_STATUSES = ("WAITING", "WAITING_OPPONENT", "SCHEDULED")


def _cancel_match(db: Session, match: Matches, reason: str, now: datetime) -> None:
    snapshot = deepcopy(read_snapshot(db, match.match_id, match.creator_id))

    snapshot["sequence"] = match.sequence + 1
    snapshot["sentAt"] = now.isoformat()
    snapshot["state"]["status"] = "CANCELLED"
    snapshot["state"]["cancellationReason"] = reason

    match.status = "CANCELLED"
    match.cancellation_reason = reason
    match.sequence = snapshot["sequence"]
    match.snapshot = snapshot

    db.flush()


def prepare_match_start(db: Session, match: Matches, now: datetime, *, duration_ms: int | None = None) -> Match | None:
    if match.status not in PENDING_STATUSES:
        raise AppError("MATCH_STATE_INVALID", "El partido no está pendiente de inicio.")

    if match.init_date > now:
        return None

    if match.visitor_id is None:
        _cancel_match(db, match, "NO_OPPONENT", now)
        return None

    club_ids = (match.creator_id, match.visitor_id)
    clubs = matches_repository.get_clubs_for_update(db, club_ids)

    if len(clubs) != 2:
        _cancel_match(db, match, "INVALID_CLUBS", now)
        return None

    if matches_repository.clubs_have_running_match(db, club_ids, match.match_id):
        _cancel_match(db, match, "CLUB_BUSY", now)
        return None

    try:
        return build_match(db, match.match_id, duration_ms=duration_ms)
    except AppError as exc:
        if exc.code == "MATCH_INVALID_LINEUP":
            _cancel_match(db, match, "INVALID_LINEUP", now)
            return None
        if exc.code == "MATCH_INVALID_BEHAVIOUR":
            _cancel_match(db, match, "INVALID_BEHAVIOUR", now)
            return None
        raise