from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session
from types import SimpleNamespace

from app.errors import AppError
from app.repository import behaviour_repository, player_repository, team_repository, league_repository
from app.schemas.team_schemas import Lineup
from primitives.behaviour_api.runtime import resolve_program
from primitives.formations import FORMATIONS
from app.schemas.league_schemas import (LeagueLineupRead, LeagueLineupUpdate)


def prepare_registration_lineup(db: Session, registration, creator_id: int) -> None:
    saved = registration.line_up
    # Las inscripciones antiguas sólo identifican jugadores, sin indicar sus puestos.
    if isinstance(saved, list):
        team = team_repository.get_by_club(db, registration.club_id)
        raw = team.line_up if team else None
    else:
        raw = saved

    try:
        lineup = Lineup.model_validate(raw)
    except ValidationError as exc:
        raise HTTPException(409, "Hay una alineación incompleta o inválida.") from exc

    if lineup.formation_id not in FORMATIONS:
        raise HTTPException(409, "La formación guardada ya no está disponible.")
    selections = lineup.starters + lineup.substitutes
    if isinstance(saved, list) and not (saved == [] and registration.club_id == creator_id):
        ids = sorted(slot.player_id for slot in selections)
        if any(type(id_) is not int for id_ in saved) or sorted(saved) != ids:
            raise HTTPException(409, "Los jugadores inscriptos no coinciden con el equipo guardado.")

    active_ids = {p.id for p in player_repository.get_players_by_club(db, registration.club_id)}
    behaviours = {
        b.id: b for b in behaviour_repository.get_all_behaviours(db, registration.club_id)
        if b.kind == "PLAYER" and b.validation_status == "VALID"
    }
    for slot in selections:
        if slot.player_id not in active_ids:
            raise HTTPException(409, "Una alineación contiene jugadores no disponibles en su club.")
        behaviour = behaviours.get(slot.behaviour_id)
        if behaviour is None:
            raise HTTPException(409, "Un comportamiento de la alineación ya no está disponible.")
        try:
            resolve_program(behaviour.code, behaviour.name, version=behaviour.version)
        except ValueError as exc:
            raise HTTPException(409, "Un comportamiento es incompatible con el motor del partido.") from exc

    if isinstance(saved, list):
        registration.line_up = lineup.model_dump(by_alias=True)
        registration.lineup_version = (getattr(registration, "lineup_version", 0) + 1)

TERMINAL_LEAGUE_STATUSES = {"finished", "cancelled", "canceled"}

PLAYER_SNAPSHOT_FIELDS = (
    "id",
    "club_id",
    "name",
    "power",
    "agility",
    "control",
    "speed",
    "strength",
)

#Devuelve errores para liga inexistentet o club no inscripto.
def _require_context( db: Session, league_id: int, club_id: int, *, lock: bool = False):
    """Exige una liga existente y una inscripción del club autenticado."""
    league, registration = league_repository.get_lineup_context(
        db,
        league_id,
        club_id,
        lock=lock,
    )

    if league is None:
        raise AppError("LEAGUE_NOT_FOUND", "La liga no existe.")

    if registration is None:
        raise AppError(
            "LEAGUE_NOT_REGISTERED",
            "Tu club no está inscripto en esta liga.",
        )

    return league, registration


def _read_lineup(league, registration) -> LeagueLineupRead:
    """Serializa la inscripción sin convertir ni guardar datos antiguos."""
    try:
        lineup = Lineup.model_validate(registration.line_up)
    except ValidationError:
        lineup = None

    return LeagueLineupRead(
        league_id=league.id,
        league_name=league.name,
        club_id=registration.club_id,
        version=registration.lineup_version,
        editable=league.status.lower() not in TERMINAL_LEAGUE_STATUSES,
        line_up=lineup,
    )


def _checked_lineup(db: Session, registration, creator_id: int):
    """Valida usando catálogos actualizados y protegidos por bloqueos."""
    players, behaviours = league_repository.get_lineup_catalogs(
        db,
        registration.club_id,
    )

    prepare_registration_lineup(db, registration, creator_id)

    return (
        Lineup.model_validate(registration.line_up),
        players,
        behaviours,
    )


def get_lineup(
    db: Session,
    league_id: int,
    club_id: int,
) -> LeagueLineupRead:
    """Devuelve la alineación de ese club en esa liga."""
    league, registration = _require_context(db, league_id, club_id)
    return _read_lineup(league, registration)


def update_lineup( db: Session, league_id: int, club_id: int, data: LeagueLineupUpdate) -> LeagueLineupRead:
    """Guarda solamente si la versión del borrador sigue vigente."""
    try:
        league, registration = _require_context(
            db,
            league_id,
            club_id,
            lock=True,
        )

        if league.status.lower() in TERMINAL_LEAGUE_STATUSES:
            raise AppError(
                "LEAGUE_CLOSED",
                "La liga terminó o fue cancelada.",
            )

        if data.expected_version != registration.lineup_version:
            raise AppError(
                "LEAGUE_LINEUP_CONFLICT",
                "Otra edición cambió esta alineación. Recargala antes de guardar.",
            )

        behaviour_repository.lock_club(db, club_id)

        candidate = SimpleNamespace(
            club_id=club_id,
            line_up=data.model_dump(
                by_alias=True,
                exclude={"expected_version"},
            ),
        )

        lineup, _, _ = _checked_lineup( db, candidate, league.creator_club_id)

        registration.line_up = lineup.model_dump(by_alias=True)
        registration.lineup_version += 1

        db.flush()
        result = _read_lineup(league, registration)
        db.commit()

        return result

    except Exception:
        db.rollback()
        raise


def capture_registration_lineup( db: Session, registration, creator_id: int) -> dict:
    """Captura los seis jugadores y las versiones de sus comportamientos."""
    lineup, players, behaviours = _checked_lineup( db, registration, creator_id)
    selections = lineup.starters + lineup.substitutes

    return {
        "version": registration.lineup_version,
        "lineUp": lineup.model_dump(by_alias=True),
        "players": {
            str(selection.player_id): {
                field: getattr(players[selection.player_id], field)
                for field in PLAYER_SNAPSHOT_FIELDS
            }
            for selection in selections
        },
        "behaviours": {
            str(selection.behaviour_id): {
                "version": behaviours[selection.behaviour_id].version,
                "name": behaviours[selection.behaviour_id].name,
                "code": behaviours[selection.behaviour_id].code,
            }
            for selection in selections
        },
    }