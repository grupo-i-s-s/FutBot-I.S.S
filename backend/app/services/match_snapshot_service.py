from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.errors import AppError
from app.repository import matches_repository
from app.schemas.avatar_schemas import DEFAULT_AVATAR
from primitives.match_simulation import goal_width, height, width


def _with_club_avatars(db: Session, snapshot: dict) -> dict:
    teams = snapshot["state"].get("teams", [])
    missing_ids = tuple(team["id"] for team in teams if not team.get("avatar"))
    if not missing_ids:
        return snapshot

    # Los snapshots anteriores al campo avatar siguen siendo legibles sin
    # reescribir el JSON persistido ni alterar su secuencia.
    avatars = matches_repository.get_club_avatars(db, missing_ids)
    return {
        **snapshot,
        "state": {
            **snapshot["state"],
            "teams": [
                {**team, "avatar": team.get("avatar") or avatars.get(team["id"], DEFAULT_AVATAR)}
                for team in teams
            ],
        },
    }


def read_snapshot(db: Session, match_id: int, club_id: int) -> dict:
    match = matches_repository.get_by_id(db, match_id)
    if match is None:
        raise AppError("MATCH_NOT_FOUND", "El partido no existe.")
    if club_id not in (match.creator_id, match.visitor_id):
        raise AppError("MATCH_FORBIDDEN", "El club no participa de este partido.")
    if match.snapshot is not None:
        return _with_club_avatars(db, match.snapshot)
    if match.status not in ("WAITING", "WAITING_OPPONENT", "SCHEDULED"):
        raise AppError("MATCH_STATE_INVALID", "Falta el snapshot persistido del partido.")
    return empty_match_snapshot(db, match, datetime.now(timezone.utc))


def empty_match_snapshot(db: Session, match, now: datetime, *, status: str = "WAITING") -> dict:
    ids = (match.creator_id,) if match.visitor_id is None else (match.creator_id, match.visitor_id)
    names = matches_repository.get_club_names(db, ids)
    avatars = matches_repository.get_club_avatars(db, ids)
    cancelled = status == "CANCELLED"
    scores = (match.local_score, match.visitor_score) if cancelled else (0, 0)
    state = {
        "status": status, "clockMs": match.clock_ms if cancelled else 0, "durationMs": match.duration_ms,
        "field": {"width": width, "height": height, "goalWidth": goal_width},
        "teams": [
            {"id": club, "name": names[club], "avatar": avatars.get(club, DEFAULT_AVATAR),
             "side": side, "score": score, "color": color}
            for club, side, score, color in (
                (match.creator_id, "LEFT", scores[0], "#2563eb"),
                (match.visitor_id, "RIGHT", scores[1], "#dc2626"),
            ) if club is not None
        ],
        "players": [], "ball": None,
    }
    if cancelled:
        state["cancellationReason"] = match.cancellation_reason
    return {
        "schemaVersion": 1, "type": "match.snapshot", "matchId": match.match_id,
        "sequence": match.sequence, "sentAt": now.isoformat(), "state": state,
    }
