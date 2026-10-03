from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.errors import AppError
from app.repository import matches_repository
from primitives.match_simulation import goal_width, height, width


def read_snapshot(db: Session, match_id: int, club_id: int) -> dict:
    match = matches_repository.get_by_id(db, match_id)
    if match is None:
        raise AppError("MATCH_NOT_FOUND", "El partido no existe.")
    if club_id not in (match.creator_id, match.visitor_id):
        raise AppError("MATCH_FORBIDDEN", "El club no participa de este partido.")
    if match.snapshot is not None:
        return match.snapshot
    if match.status != "WAITING":
        raise AppError("MATCH_STATE_INVALID", "Falta el snapshot persistido del partido.")
    ids = (match.creator_id,) if match.visitor_id is None else (match.creator_id, match.visitor_id)
    names = matches_repository.get_club_names(db, ids)
    return {
        "schemaVersion": 1, "type": "match.snapshot", "matchId": match_id,
        "sequence": match.sequence, "sentAt": datetime.now(timezone.utc).isoformat(),
        "state": {
            "status": "WAITING", "clockMs": 0, "durationMs": match.duration_ms,
            "field": {"width": width, "height": height, "goalWidth": goal_width},
            "teams": [
                {"id": club, "name": names[club], "side": side, "score": 0, "color": color}
                for club, side, color in (
                    (match.creator_id, "LEFT", "#2563eb"),
                    (match.visitor_id, "RIGHT", "#dc2626"),
                ) if club is not None
            ],
            "players": [], "ball": None,
        },
    }
