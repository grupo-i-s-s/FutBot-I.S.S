from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.errors import AppError
from app.repository import behaviour_repository, player_repository, team_repository
from app.schemas.team_schemas import Lineup
from primitives.behaviour_api.runtime import resolve_program
from primitives.formations import FORMATIONS

INCOMPLETE_LEGACY_LINEUP = "INCOMPLETE_LEGACY"


def is_legacy_lineup(saved: object) -> bool:
    return isinstance(saved, list) or _is_incomplete_lineup(saved)


def _is_incomplete_lineup(saved: object) -> bool:
    return isinstance(saved, dict) and saved.get("status") == INCOMPLETE_LEGACY_LINEUP


def _parse_lineup(raw: object) -> Lineup:
    try:
        return Lineup.model_validate(raw)
    except ValidationError as exc:
        raise AppError("LEAGUE_LINEUP_INVALID", "Hay una alineación incompleta o inválida.") from exc


def _default_lineup(db: Session, club_id: int) -> Lineup:
    team = team_repository.get_by_club(db, club_id)
    if team is None:
        raise AppError("LEAGUE_LINEUP_INVALID", "Configurá tu equipo predeterminado antes de continuar.")
    return _parse_lineup(team.line_up)


def _validate_lineup(db: Session, club_id: int, lineup: Lineup) -> None:
    if lineup.formation_id not in FORMATIONS:
        raise AppError("LEAGUE_LINEUP_INVALID", "La formación elegida no está disponible.")
    selections = lineup.starters + lineup.substitutes
    active_ids = {p.id for p in player_repository.get_players_by_club(db, club_id)}
    behaviours = {
        b.id: b for b in behaviour_repository.get_all_behaviours(db, club_id)
        if b.kind == "PLAYER" and b.validation_status == "VALID"
    }
    for slot in selections:
        if slot.player_id not in active_ids:
            raise AppError("LEAGUE_LINEUP_INVALID", "La alineación contiene jugadores no disponibles en el club.")
        behaviour = behaviours.get(slot.behaviour_id)
        if behaviour is None:
            raise AppError("LEAGUE_LINEUP_INVALID", "Un comportamiento de la alineación no está disponible en el club.")
        try:
            resolve_program(behaviour.code, behaviour.name, version=behaviour.version)
        except ValueError as exc:
            raise AppError("LEAGUE_LINEUP_INVALID", "Un comportamiento es incompatible con el motor del partido.") from exc


def _legacy_players_match(lineup: Lineup, saved: list, *, allow_reorder: bool = False) -> bool:
    if any(type(player_id) is not int for player_id in saved):
        return False
    players = [slot.player_id for slot in lineup.starters + lineup.substitutes]
    return sorted(saved) == sorted(players) if allow_reorder else saved == players


def snapshot_default_lineup(
        db: Session, club_id: int, submitted: Lineup | list[int] | None = None,
) -> dict:
    # Los cambios de equipo y la eliminación de comportamientos toman el mismo bloqueo.
    behaviour_repository.lock_club(db, club_id)
    lineup = _default_lineup(db, club_id)
    if isinstance(submitted, Lineup) and submitted != lineup:
        _validate_lineup(db, club_id, submitted)
        raise AppError(
            "LEAGUE_LINEUP_CHANGED",
            "Tu equipo predeterminado cambió. Volvé a cargarlo y confirmá la inscripción.",
        )
    if isinstance(submitted, list) and not _legacy_players_match(lineup, submitted):
        raise HTTPException(400, "Los jugadores deben coincidir en orden con tu equipo predeterminado.")
    _validate_lineup(db, club_id, lineup)
    return lineup.model_dump(by_alias=True)


def prepare_registration_lineup(
        db: Session, registration, creator_id: int | None, *, allow_legacy_reorder: bool = False,
) -> None:
    saved = registration.line_up
    is_creator = registration.club_id == creator_id
    if _is_incomplete_lineup(saved):
        if is_creator and saved.get("legacyPlayerIds") == []:
            saved = []
        else:
            raise HTTPException(
                409,
                f"La inscripción del club #{registration.club_id} está incompleta. "
                "El club debe abandonar la liga e inscribirse de nuevo con su equipo predeterminado.",
            )

    try:
        if isinstance(saved, list):
            lineup = _default_lineup(db, registration.club_id)
            if not (is_creator and saved == []) and not _legacy_players_match(
                lineup, saved, allow_reorder=allow_legacy_reorder,
            ):
                raise AppError("LEAGUE_LINEUP_INVALID", "Los jugadores inscriptos no coinciden con el equipo guardado.")
        else:
            lineup = _parse_lineup(saved)
        _validate_lineup(db, registration.club_id, lineup)
    except AppError as exc:
        correction = (
            "Configurá el equipo predeterminado del club para volver a intentar."
            if is_creator and saved == []
            else "Si la inscripción es antigua, el club puede abandonar la liga e inscribirse de nuevo."
        )
        raise HTTPException(409, f"Club #{registration.club_id}. {exc.message} {correction}") from exc
    if isinstance(saved, list):
        registration.line_up = lineup.model_dump(by_alias=True)
