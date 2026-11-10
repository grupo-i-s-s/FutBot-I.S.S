from copy import deepcopy
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models.planned_substitution_model import PlannedSubstitution
from app.repository import matches_repository
from app.schemas.matches_schemas import PlannedSubstitutionRequest, SubstitutionRequest
from app.services.matches_service import require_manual_match_control
from primitives.match_breaks import MatchBreaks


def _result(plan: PlannedSubstitution) -> dict:
    return {
        "pauseId": f"{plan.match_id}:{plan.pause_index}",
        "status": plan.status,
        "outPlayerId": plan.out_player_id,
        "inPlayerId": plan.in_player_id,
        "commandId": plan.command_id,
    }


def with_pending_substitutions(db: Session, match_id: int, snapshot: dict) -> dict:
    if "lineups" not in snapshot["state"]:
        return snapshot
    result = deepcopy(snapshot)
    state = result["state"]
    target = state.get("nextPause")
    dt_clubs = {team["id"] for team in state.get("teams", []) if team.get("dtActive") is True}
    pending = db.scalars(select(PlannedSubstitution).where(
        PlannedSubstitution.match_id == match_id, PlannedSubstitution.status == "PENDING",
    )).all()
    by_club = {
        plan.club_id: _result(plan) for plan in pending
        if plan.club_id not in dt_clubs and target and f"{match_id}:{plan.pause_index}" == target["pauseId"]
    }
    for lineup in state["lineups"]:
        lineup["pendingSubstitution"] = by_club.get(lineup["clubId"]) if state["status"] == "RUNNING" else None
    return result


def plan_substitution(db: Session, match_id: int, club_id: int, data: PlannedSubstitutionRequest) -> dict:
    return _save_substitution(db, match_id, club_id, data)


def request_substitution(db: Session, match_id: int, club_id: int, data: SubstitutionRequest) -> dict:
    return _save_substitution(db, match_id, club_id, data, immediate=True)


def _save_substitution(db: Session, match_id: int, club_id: int, data: PlannedSubstitutionRequest,
                       *, immediate: bool = False) -> dict:
    try:
        # El mismo bloqueo que usa el escritor evita leer un checkpoint a medio actualizar.
        match = matches_repository.get_by_id_for_update(db, match_id)
        if match is None:
            raise AppError("MATCH_NOT_FOUND", "El partido no existe.")
        if club_id not in (match.creator_id, match.visitor_id):
            raise AppError("MATCH_FORBIDDEN", "Tu club no participa del partido.")

        state = match.runtime_state
        team_key = "local_team" if club_id == match.creator_id else "visitor_team"
        team = state.get(team_key) if isinstance(state, dict) else None
        if match.status == "RUNNING":
            require_manual_match_control(team)

        plans = select(PlannedSubstitution).where(
            PlannedSubstitution.match_id == match_id, PlannedSubstitution.club_id == club_id,
        ).execution_options(populate_existing=True)
        previous = db.scalar(plans.where(PlannedSubstitution.command_id == data.command_id))
        if previous is not None:
            if ((previous.out_player_id, previous.in_player_id) != (data.out_player_id, data.in_player_id)
                    or data.pause_id != f"{match_id}:{previous.pause_index}"):
                raise AppError("SUBSTITUTION_COMMAND_CONFLICT", "El identificador ya se usó para otro cambio.")
            if match.status == "CANCELLED" and previous.status == "PENDING":
                # Repara cancelaciones guardadas antes de cerrar sus planes en la misma transacción.
                matches_repository.expire_pending_substitutions(db, match_id)
            result = {**_result(previous), "sequence": match.sequence}
            db.commit()
            return result

        if match.status != "RUNNING" or not state:
            raise AppError("PAUSE_CLOSED", "La pausa ya no admite este cambio.")
        try:
            breaks = MatchBreaks(**state["breaks"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AppError("MATCH_STATE_INVALID", "Falta un estado válido de pausas.") from exc
        if immediate:
            pause = breaks.next_index
            if not breaks.paused or data.pause_id != f"{match_id}:{pause}":
                raise AppError("PAUSE_CLOSED", "La pausa ya no está abierta.")
            if [club_id, pause] in state.get("substitution_pauses", []):
                raise AppError("SUBSTITUTION_QUOTA_USED", "Ya utilizaste el cambio de esta pausa.")
        else:
            pause = next((i + 1 for i in range(breaks.next_index, 3) if breaks.durations_ms[i] > 0), None)
            if breaks.paused or pause is None or data.pause_id != f"{match_id}:{pause}":
                raise AppError("PAUSE_CLOSED", "La pausa seleccionada ya no está disponible para planificar el cambio.")

        # El plantel capturado del partido es independiente del equipo default actual.
        if not team or team.get("club_id") != club_id or "substitutes" not in team:
            raise AppError("MATCH_STATE_INVALID", "El partido no conserva su banco de suplentes.")
        starters = {p["id"] for p in team.get("players", [])}
        substitutes = {p["id"] for p in team["substitutes"]}
        if data.out_player_id not in starters or data.in_player_id not in substitutes:
            raise AppError("SUBSTITUTION_INVALID_PLAYERS", "Elegí un titular y un suplente de tu partido.")

        pending = db.scalar(plans.where(
            PlannedSubstitution.pause_index == pause, PlannedSubstitution.status == "PENDING",
        ))
        if pending is not None:
            if immediate:
                raise AppError("SUBSTITUTION_QUOTA_USED", "Ya hay un cambio admitido para esta pausa.")
            pending.status = "REPLACED"
            db.flush()
        plan = PlannedSubstitution(
            match_id=match_id, club_id=club_id, pause_index=pause, command_id=data.command_id,
            out_player_id=data.out_player_id, in_player_id=data.in_player_id, status="PENDING",
        )
        db.add(plan)
        db.flush()
        if match.snapshot is not None:
            snapshot = with_pending_substitutions(db, match_id, match.snapshot)
            match.sequence += 1
            match.snapshot = {**snapshot, "sequence": match.sequence,
                              "sentAt": datetime.now(timezone.utc).isoformat()}
        result = {**_result(plan), "sequence": match.sequence}
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
