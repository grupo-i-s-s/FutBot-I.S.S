from sqlalchemy.orm import Session

from app.errors import AppError
from app.models.behaviour_model import Behavior
from app.repository import behaviour_repository
from app.schemas.behaviour_schemas import BehaviourCreate
from app.services.behaviour_validation_service import validate_program
from app.models.league_model import LeagueRegistration
from app.models.matches_model import Matches
from app.models.player_model import Player
from app.models.team_model import DefaultTeam

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
    diagnostics = validate_program(data.code)

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

ACTIVE_MATCH_STATUSES = {
    "WAITING",
    "WAITING_OPPONENT",
    "SCHEDULED",
    "RUNNING",
}

#Busca un ID dentro de la estructura JSON.

def _contains_id(value, keys: set[str], target: int) -> bool: 
    if isinstance(value,dict):
        return any(
            (key in keys and type(item) is int and item == target)
            or _contains_id(item,keys, target) 
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_id(item, keys, target) for item in value)

    return False


def _player_ids(value) -> set[int]:
    if isinstance(value, dict):
        result = {item 
                  for key, item in value.items()
                  if key in PLAYER_KEYS and type(item) is int
                  }
        for item  in value.values():
            result.update(_player_ids(item))

        return result

    if isinstance(value, list):
        result = {item for item in value if type(item) is int}}

        for item in value:
            result.update(_player_ids(item))

        return result

    return set()

def delete_behaiour(db: Session, club_id:int, behaviour_id: int) -> None: 
    try: 
        behaviour = behaviour_repository.get_behaviour_by_id(db, club_id, behaviour_id)

        if behaviour is None: 
            raise AppError("BEHAVIOUR_NOT_FOUND", "No se encontró el comportamiento.")

        references = []

        players = behaviour_repository.get_players_using:behaviour(db, club_id, behaviour_id)
        references.extend(f"jugador {player.name} (#{player.id})" for player in players)

        default_team = behaviour_repository.get_default_team(db, club_id)

        if default_team and _contains_id( default_team.line_up, BEHAVIOUR_KEYS, behaviour_id):
            references.append("equipo predeterminado")