from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.errors import AppError
from app.models.behaviour_model import Behavior
from app.repository import behaviour_repository
from app.schemas.behaviour_schemas import BehaviourCreate, BehaviourReadDetail, BehaviourUpdate
from primitives.behaviour_api.validation import validate_program
from primitives.behaviours import default_behaviour_mode
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

def _match_uses_behaviour(match: Matches, club_id: int, behaviour_id: int) -> bool:
    # Checkpoint privado: cada equipo contiene sus perfiles de jugadores.
    runtime = match.runtime_state
    if isinstance(runtime, dict):
        for key in ("local_team", "visitor_team"):
            team = runtime.get(key)
            if not isinstance(team, dict) or team.get("club_id") != club_id:
                continue
            if _contains_id(team, BEHAVIOUR_KEYS, behaviour_id):
                return True
            defaults = team.get("dt_default_behaviours")
            if isinstance(defaults, dict) and any(
                isinstance(entry, (list, tuple))
                and entry
                and type(entry[0]) is int
                and entry[0] == behaviour_id
                for entry in defaults.values()
            ):
                return True

    # Snapshot público: revisar únicamente los datos del propio club.
    snapshot = match.snapshot
    state = snapshot.get("state") if isinstance(snapshot, dict) else None
    if not isinstance(state, dict):
        return False

    for entries, club_key in ((state.get("players"), "teamId"), (state.get("teams"), "id")):
        if not isinstance(entries, list):
            continue
        if any(
            isinstance(entry, dict)
            and entry.get(club_key) == club_id
            and _contains_id(entry, BEHAVIOUR_KEYS, behaviour_id)
            for entry in entries
        ):
            return True
    return False


def _dt_preset_references(behaviour: Behavior) -> dict[str, str]:
    if behaviour.kind == "PLAYER" and default_behaviour_mode(behaviour.name, behaviour.code) is not None:
        return {"dtPreset": "Comportamiento predeterminado del DT"}
    return {}


def _require_custom_behaviour(behaviour: Behavior) -> None:
    references = _dt_preset_references(behaviour)
    if references:
        raise AppError(
            "BEHAVIOUR_IN_USE",
            "El DT necesita este comportamiento predeterminado. Creá uno personalizado si querés usar otro código.",
            fields=references,
        )


def _get_behaviour_references(db: Session, club_id: int, behaviour_id: int) -> dict[str, str]:
    players = behaviour_repository.get_players_using_behaviour(db, club_id, behaviour_id)
    assigned_player_ids = {player.id for player in players}

    references = {
        f"players.{player.id}": f"Jugador {player.name} (#{player.id})"
        for player in players
        if not player.is_deleted
    }

    default_team = behaviour_repository.get_default_team(db, club_id)

    if default_team and _lineup_uses_behaviour(default_team.line_up, behaviour_id, assigned_player_ids):
        references["defaultTeam"] = "Equipo predeterminado"

    for registration in behaviour_repository.get_active_league_lineups(db, club_id):
        if _lineup_uses_behaviour(registration.line_up, behaviour_id, assigned_player_ids):
            references[f"leagues.{registration.league_id}"] = (
                f"Alineación de liga #{registration.league_id}"
            )

    for match in behaviour_repository.get_active_matches(db, club_id):
        if _match_uses_behaviour(match, club_id, behaviour_id):
            references[f"matches.{match.match_id}"] = (
                f"Partido activo #{match.match_id}"
            )

    return references

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
        _require_custom_behaviour(behaviour)

        references = _get_behaviour_references(db, club_id, behaviour_id)

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

def update_behaviour(db: Session, club_id: int, behaviour_id: int, data: BehaviourUpdate) -> BehaviourReadDetail:
    try:
        original = behaviour_repository.get_behaviour_by_id(db, club_id, behaviour_id)
        if original is None:
            raise AppError("BEHAVIOUR_NOT_FOUND", "No se encontró el comportamiento.")
        _require_custom_behaviour(original)

        # El sandbox puede tardar. La comprobación de uso y versión se hace al adquirir el bloqueo.
        diagnostics = validate_program(data.code, kind=original.kind)
        if diagnostics:
            raise AppError(
                "BEHAVIOUR_INVALID",
                "El programa del comportamiento es inválido.",
                diagnostics=diagnostics,
            )

        behaviour_repository.lock_club(db, club_id)

        behaviour = behaviour_repository.get_behaviour_by_id(db, club_id, behaviour_id)
        if behaviour is None:
            raise AppError(
                "BEHAVIOUR_NOT_FOUND",
                "No se encontró el comportamiento.",
            )
        _require_custom_behaviour(behaviour)

        references = _get_behaviour_references(db, club_id, behaviour_id)
        if references:
            raise AppError(
                "BEHAVIOUR_IN_USE",
                "Reemplazá el comportamiento en sus asignaciones "
                "antes de editarlo.",
                fields=references,
            )

        if data.expected_version != behaviour.version:
            raise AppError(
                "VERSION_CONFLICT",
                "Otra edición cambió este comportamiento. "
                "Recargalo antes de guardar.",
            )

        updated = behaviour_repository.update_behaviour(db, behaviour, name=data.name, code=data.code)

        result = BehaviourReadDetail.model_validate(updated)
        db.commit()
        return result

    except IntegrityError as error:
        db.rollback()

        constraint = getattr(
            getattr(error.orig, "diag", None),
            "constraint_name",
            None,
        )

        if constraint == "uq_behaviors_club_name":
            message = (
                "Ya existe un comportamiento con ese nombre en tu club."
            )
            raise AppError(
                "BEHAVIOUR_NAME_DUPLICATE",
                message,
                fields={"name": message},
            ) from error

        raise

    except Exception:
        db.rollback()
        raise

#Consulta para saber si el comportamiento esta en uso.
def get_behaviour_usage(
    db: Session,
    club_id: int,
    behaviour_id: int,
) -> dict:
    behaviour = behaviour_repository.get_behaviour_by_id(
        db, club_id, behaviour_id
    )
    if behaviour is None:
        raise AppError(
            "BEHAVIOUR_NOT_FOUND",
            "No se encontró el comportamiento.",
        )

    references = _get_behaviour_references(db, club_id, behaviour_id)
    references.update(_dt_preset_references(behaviour))

    return {
        "inUse": bool(references),
        "references": references,
    }
