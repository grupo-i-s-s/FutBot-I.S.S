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


def with_closed_match_pauses(snapshot: dict) -> dict:
    """Cierra las pausas y los cambios visibles sin modificar el snapshot de origen."""
    state = snapshot["state"]
    updates = {}
    if (
        state.get("phase") not in (None, "PLAYING")
        or state.get("breakIndex") is not None
        or state.get("breakRemainingMs", 0) != 0
    ):
        updates.update(phase="PLAYING", breakIndex=None, breakRemainingMs=0)
    if state.get("nextPause") is not None:
        updates["nextPause"] = None
    lineups = state.get("lineups", [])
    if any(
        lineup.get("pendingSubstitution") is not None or lineup.get("remainingSubstitutions")
        for lineup in lineups
    ):
        updates["lineups"] = [
            {**lineup, "pendingSubstitution": None, "remainingSubstitutions": 0} for lineup in lineups
        ]
    return {**snapshot, "state": {**state, **updates}} if updates else snapshot


def snapshot_from_match(db: Session, match: Matches) -> dict:
    """Lee el estado completo para operaciones internas, como la cancelación."""
    if match.snapshot is not None:
        snapshot = _with_match_control(match.snapshot, match)
        if snapshot["state"].get("status") == "CANCELLED":
            snapshot = with_closed_match_pauses(snapshot)
        return _with_club_avatars(db, snapshot)
    if match.status not in ("WAITING", "WAITING_OPPONENT", "SCHEDULED"):
        raise AppError("MATCH_STATE_INVALID", "Falta el snapshot persistido del partido.")
    return empty_match_snapshot(db, match, datetime.now(timezone.utc))


def _with_visible_substitutions(snapshot: dict, club_id: int) -> dict:
    state = snapshot["state"]
    lineups = state.get("lineups", [])
    events = state.get("events", [])
    visible_lineups = [
        {**lineup, "pendingSubstitution": None}
        if lineup.get("clubId") != club_id and lineup.get("pendingSubstitution") is not None else lineup
        for lineup in lineups
    ]
    visible_events = [
        event for event in events
        if event.get("type") != "SUBSTITUTION_REJECTED" or event.get("clubId") == club_id
    ]
    updates = {}
    if visible_lineups != lineups:
        updates["lineups"] = visible_lineups
    if len(visible_events) != len(events):
        updates["events"] = visible_events
    return {**snapshot, "state": {**state, **updates}} if updates else snapshot


def read_snapshot(db: Session, match_id: int, club_id: int) -> dict:
    match = matches_repository.get_by_id(db, match_id)
    if match is None:
        raise AppError("MATCH_NOT_FOUND", "El partido no existe.")
    if club_id not in (match.creator_id, match.visitor_id):
        raise AppError("MATCH_FORBIDDEN", "El club no participa de este partido.")
    return _with_visible_substitutions(snapshot_from_match(db, match), club_id)


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
