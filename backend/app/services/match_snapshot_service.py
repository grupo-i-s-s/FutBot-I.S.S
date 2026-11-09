from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models.matches_model import Matches
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


def _with_match_control(snapshot: dict, match: Matches) -> dict:
    state = snapshot["state"]
    teams = state.get("teams", [])
    if state.get("status") != "RUNNING" or not teams:
        return snapshot

    modes: dict[int, bool] = {}
    checkpoint = match.runtime_state
    if (
        isinstance(checkpoint, dict)
        and checkpoint.get("match_id") == match.match_id
        and checkpoint.get("duration_ms") == match.duration_ms
    ):
        for key, club_id in (("local_team", match.creator_id), ("visitor_team", match.visitor_id)):
            team = checkpoint.get(key)
            if (
                club_id is None
                or not isinstance(team, dict)
                or team.get("club_id") != club_id
                or not isinstance(team.get("players"), (list, tuple))
            ):
                continue
            active = team.get("dt_active", False)
            if type(active) is bool:
                modes[club_id] = active

    public_teams = [
        {**team, "dtActive": modes[team["id"]]} if team["id"] in modes else team
        for team in teams
    ]
    dt_clubs = {team["id"] for team in public_teams if team.get("dtActive") is True}
    lineups = state.get("lineups", [])
    public_lineups = [
        {**lineup, "pendingSubstitution": None}
        if lineup["clubId"] in dt_clubs and lineup.get("pendingSubstitution") is not None else lineup
        for lineup in lineups
    ]
    if public_teams == teams and public_lineups == lineups:
        return snapshot

    public_state = {**state, "teams": public_teams}
    if "lineups" in state:
        public_state["lineups"] = public_lineups
    return {**snapshot, "state": public_state}


def read_snapshot(db: Session, match_id: int, club_id: int) -> dict:
    match = matches_repository.get_by_id(db, match_id)
    if match is None:
        raise AppError("MATCH_NOT_FOUND", "El partido no existe.")
    if club_id not in (match.creator_id, match.visitor_id):
        raise AppError("MATCH_FORBIDDEN", "El club no participa de este partido.")
    if match.snapshot is not None:
        return _with_club_avatars(db, _with_match_control(match.snapshot, match))
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
