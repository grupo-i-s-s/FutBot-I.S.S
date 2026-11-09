from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.errors import AppError
from app.models.behaviour_model import Behavior
from app.repository import behaviour_repository
from app.schemas.behaviour_schemas import BehaviourCreate
from primitives.behaviour_api.validation import validate_program
from app.models.league_model import LeagueRegistration
from app.models.matches_model import Matches

def list_behaviours(db: Session, club_id: int, kind: str|None=None) -> list[Behavior]:
    return behaviour_repository.get_all_behaviours(db, club_id, kind=kind)


def behaviour_id(db: Session, club_id: int, behaviour_id: int) -> Behavior:
    behaviour = behaviour_repository.get_behaviour_by_id(db, club_id, behaviour_id)

    if behaviour is None:
        raise AppError(
            "BEHAVIOUR_NOT_FOUND",
            "No se encontro el comportamiento.")
    return behaviour

def create_behaviour(db: Session, club_id: int, data: BehaviourCreate)-> Behavior:
    diagnostics = validate_program(data.code, kind=data.kind)

    if diagnostics:
        raise AppError("BEHAVIOUR_INVALID", "El programa del comportamiento es inválido.", diagnostics=diagnostics)
        
    behavior = Behavior(
        club_id=club_id,
        name=data.name,
        description="",
        code=data.code,
        kind=data.kind,
        version=1,
        validation_status="VALID",
        is_deleted=False,
    )
    try:
        created = behaviour_repository.create_behaviour(db, behavior)
        db.commit()
    except IntegrityError as error:
        db.rollback()

        constraint = getattr(
            getattr(error.orig, "diag", None),
            "constraint_name",
            None,
        )

        if constraint == "uq_behaviors_club_name":
            message = "Ya existe un comportamiento con ese nombre en tu club."

            raise AppError(
                "BEHAVIOUR_NAME_DUPLICATE",
                message,
                fields={"name": message},
            ) from error

        raise
    except Exception:
        db.rollback()
        raise
    return created


BEHAVIOUR_KEYS = {
    "behaviourId",
    "behaviorId",
    "behaviour_id",
    "behavior_id",
}

PLAYER_KEYS = {"playerId", "player_id"}

#Busca un ID dentro de la estructura JSON.

def _contains_id(value: object, keys: set[str], target: int) -> bool:
    if isinstance(value, dict):
        return any(
            (key in keys and type(item) is int and item == target)
            or _contains_id(item, keys, target)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_id(item, keys, target) for item in value)

    return False

def _lineup_uses_behaviour( lineup: object, behaviour_id: int, assigned_player_ids: set[int],) -> bool:

    if isinstance(lineup, dict):
        if any( key in BEHAVIOUR_KEYS  
               and type(value) is int 
               and value == behaviour_id 
               for key, value in lineup.items()):
            return True

         # Si la selección tiene comportamiento explícito, ese prevalece.
        if not BEHAVIOUR_KEYS.intersection(lineup):
            if any(
                key in PLAYER_KEYS
                and type(value) is int
                and value in assigned_player_ids
                for key, value in lineup.items()
            ):
                return True
            
        return any(
            _lineup_uses_behaviour(
                value, behaviour_id, assigned_player_ids
            )
            for value in lineup.values()
            if isinstance(value, (dict, list))
        )
    
    if isinstance(lineup, list):
        return any(
            (type(item) is int and item in assigned_player_ids)
            or _lineup_uses_behaviour(
                item, behaviour_id, assigned_player_ids
            )
            for item in lineup
        )
    return False

def _match_uses_behaviour( match: Matches, club_id: int, behaviour_id: int) -> bool:
    # Checkpoint privado: cada equipo contiene sus perfiles de jugadores.
    runtime = match.runtime_state or {}

    for key in ("local_team", "visitor_team"):
        team = runtime.get(key, {})
        if team.get("club_id") != club_id:
            continue
        if _contains_id(team, BEHAVIOUR_KEYS, behaviour_id) or any(
            isinstance(entry, (list, tuple)) and entry and entry[0] == behaviour_id
            for entry in team.get("dt_default_behaviours", {}).values()
        ):
            return True

    # Snapshot público: revisar únicamente los datos del propio club.
    state = (match.snapshot or {}).get("state", {})

    own_players = [
        player
        for player in state.get("players", [])
        if player.get("teamId") == club_id
    ]
    own_teams = [
        team
        for team in state.get("teams", [])
        if team.get("id") == club_id
    ]

    return _contains_id(
        own_players + own_teams,
        BEHAVIOUR_KEYS,
        behaviour_id,
    )


def delete_behaviour(db: Session, club_id: int, behaviour_id: int) -> None:
    try:
        behaviour_repository.lock_club(db, club_id)

        behaviour = behaviour_repository.get_behaviour_by_id(
            db, club_id, behaviour_id
        )
        if behaviour is None:
            raise AppError( 
                "BEHAVIOUR_NOT_FOUND",
                "No se encontró el comportamiento."
            )

        players = behaviour_repository.get_players_using_behaviour(db, club_id, behaviour_id)
        
        assigned_player_ids = {player.id for player in players}

        references = {
            f"players.{player.id}": (
                f"Jugador {player.name} (#{player.id})"
            )
            for player in players
            if not player.is_deleted
        }


        default_team = behaviour_repository.get_default_team(db, club_id)

        if default_team and _lineup_uses_behaviour( default_team.line_up, behaviour_id, assigned_player_ids):
            references["defaultTeam"] = "Equipo predeterminado"

        for registration in behaviour_repository.get_league_lineups(db, club_id):
            if _lineup_uses_behaviour( registration.line_up, behaviour_id, assigned_player_ids):
                references[f"leagues.{registration.league_id}"] = (
                    f"Alineación de liga #{registration.league_id}"
                )

        for match in behaviour_repository.get_active_matches(db, club_id):
            if _match_uses_behaviour(match, club_id, behaviour_id):
                references[f"matches.{match.match_id}"] = (
                    f"Partido activo #{match.match_id}"
                )

        if references:
            raise AppError(
                "BEHAVIOUR_IN_USE",
                "Reemplazá el comportamiento en sus asignaciones "
                "antes de eliminarlo.",
                fields=references,
            )

        behaviour_repository.soft_delete(db, behaviour)
        db.commit()

    except Exception:
        db.rollback()
        raise
