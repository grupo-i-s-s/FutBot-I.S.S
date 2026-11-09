from types import SimpleNamespace

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models.behaviour_model import Behavior
from app.models.league_model import TERMINAL_LEAGUE_STATUSES
from app.models.player_model import Player
from app.repository import behaviour_repository, league_repository, player_repository, team_repository
from app.schemas.league_schemas import LeagueLineupRead, LeagueLineupUpdate
from app.schemas.team_schemas import Lineup
from primitives.behaviour_api.runtime import resolve_program
from primitives.formations import FORMATIONS

INCOMPLETE_LEGACY_LINEUP = "INCOMPLETE_LEGACY"
PLAYER_SNAPSHOT_FIELDS = ("id", "club_id", "name", "power", "agility", "control", "speed", "strength")
LineupCatalogs = tuple[dict[int, Player], dict[int, Behavior]]


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


def _validate_lineup(
        db: Session, club_id: int, lineup: Lineup, *, catalogs: LineupCatalogs | None = None,
) -> None:
    if lineup.formation_id not in FORMATIONS:
        raise AppError("LEAGUE_LINEUP_INVALID", "La formación elegida no está disponible.")
    if catalogs is None:
        players = {p.id: p for p in player_repository.get_players_by_club(db, club_id)}
        behaviours = {b.id: b for b in behaviour_repository.get_all_behaviours(db, club_id)}
    else:
        players, behaviours = catalogs

    for slot in lineup.starters + lineup.substitutes:
        if slot.player_id not in players:
            raise AppError("LEAGUE_LINEUP_INVALID", "La alineación contiene jugadores no disponibles en el club.")
        behaviour = behaviours.get(slot.behaviour_id)
        if behaviour is None or behaviour.kind != "PLAYER" or behaviour.validation_status != "VALID":
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
        db: Session, registration, creator_id: int | None, *,
        allow_legacy_reorder: bool = False, catalogs: LineupCatalogs | None = None,
) -> Lineup:
    saved = registration.line_up
    is_creator = registration.club_id == creator_id
    if _is_incomplete_lineup(saved):
        if is_creator and saved.get("legacyPlayerIds") == []:
            saved = []
        else:
            raise HTTPException(
                409,
                f"La inscripción del club #{registration.club_id} está incompleta. "
                "El club debe guardar su plantel para esta liga.",
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
        _validate_lineup(db, registration.club_id, lineup, catalogs=catalogs)
    except AppError as exc:
        correction = (
            "Configurá el equipo predeterminado del club para volver a intentar."
            if is_creator and saved == []
            else "Revisá el plantel del club para esta liga."
        )
        raise HTTPException(409, f"Club #{registration.club_id}. {exc.message} {correction}") from exc
    if isinstance(saved, list):
        registration.line_up = lineup.model_dump(by_alias=True)
        registration.lineup_version = getattr(registration, "lineup_version", 0) + 1
    return lineup


def _require_context(db: Session, league_id: int, club_id: int, *, lock: bool = False):
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


def _checked_lineup(
        db: Session, registration, creator_id: int | None, *, allow_legacy_reorder: bool = False,
):
    """Valida usando catálogos actualizados y protegidos por bloqueos."""
    catalogs = league_repository.get_lineup_catalogs(db, registration.club_id)
    lineup = prepare_registration_lineup(
        db, registration, creator_id,
        allow_legacy_reorder=allow_legacy_reorder, catalogs=catalogs,
    )
    return lineup, *catalogs


def get_lineup(
    db: Session,
    league_id: int,
    club_id: int,
) -> LeagueLineupRead:
    """Devuelve la alineación de ese club en esa liga."""
    league, registration = _require_context(db, league_id, club_id)
    return _read_lineup(league, registration)


def update_lineup(db: Session, league_id: int, club_id: int, data: LeagueLineupUpdate) -> LeagueLineupRead:
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

        lineup, _, _ = _checked_lineup(db, candidate, league.creator_club_id)

        registration.line_up = lineup.model_dump(by_alias=True)
        registration.lineup_version += 1

        db.flush()
        result = _read_lineup(league, registration)
        db.commit()

        return result

    except Exception:
        db.rollback()
        raise


def capture_registration_lineup(
        db: Session, registration, creator_id: int | None, *, allow_legacy_reorder: bool = False,
) -> dict:
    """Captura los seis jugadores y las versiones de sus comportamientos."""
    lineup, players, behaviours = _checked_lineup(
        db, registration, creator_id, allow_legacy_reorder=allow_legacy_reorder,
    )
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
