from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, load_only
from app.models.league_model import League, LeagueRegistration, TERMINAL_LEAGUE_STATUSES
from app.models.auth_model import Club
from app.models.matches_model import Matches
from app.models.player_model import Player
from app.models.team_model import DefaultTeam

from app.models.behaviour_model import Behavior
from primitives.behaviours import DEFAULT_CODES

DEFAULT_BEHAVIOURS = (
    ("Equilibrado", "El más cercano busca la pelota; los demás acompañan manteniendo su línea."),
    ("Ofensivo", "Busca la pelota en toda la cancha y patea hacia el arco rival."),
    ("Defensivo", "Protege su posición y busca la pelota cuando está en su mitad de cancha."),
)


def create_default_behaviours(db: Session, club_id: int) -> list[Behavior]:
    behaviors = [
        Behavior(
            club_id=club_id,
            name=name,
            description=description,
            code=DEFAULT_CODES[name],
            kind="PLAYER",
            version=1,
            validation_status="VALID",
        )
        for name, description in DEFAULT_BEHAVIOURS
    ]
    db.add_all(behaviors)
    db.flush()  # Necesitamos los IDs para asignarlos a los jugadores.

    return behaviors


def get_default_behaviour(db: Session, club_id: int) -> Behavior | None:
    return db.scalar(
        select(Behavior)
        .where(Behavior.club_id == club_id, Behavior.is_deleted.is_(False),
               Behavior.kind == "PLAYER",
               Behavior.validation_status=="VALID")
        .order_by(Behavior.id)
        .limit(1)
    )


def get_all_behaviours(db: Session, club_id: int, kind: str|None=None) -> list[Behavior]:
    query = (
        select(Behavior)
        .where(Behavior.club_id == club_id, Behavior.is_deleted.is_(False))
        .order_by(Behavior.id)
    )
    if kind is not None:
        query = query.where(Behavior.kind == kind)
    return list(db.scalars(query).all())


def get_behaviour_by_id(db: Session, club_id: int, behaviour_id: int) -> Behavior | None:
    return db.scalar(
        select(Behavior)
        .where(Behavior.club_id == club_id, Behavior.is_deleted.is_(False), Behavior.id == behaviour_id)
        .execution_options(populate_existing=True)
    )

def create_behaviour(db:Session, behaviour: Behavior) -> Behavior:
    db.add(behaviour)
    db.flush()
    return behaviour

def lock_club(db: Session, club_id: int) -> None:
    db.scalar(
        select(Club.id)
        .where(Club.id == club_id)
        .with_for_update()
    )

def get_players_using_behaviour( db:Session, club_id: int, behaviour_id: int) -> list[Player]:
    return list(
        db.scalars(
            select(Player)
            .where( Player.club_id == club_id, Player.behavior_id == behaviour_id)
            .order_by(Player.id)
            .execution_options(populate_existing=True)
        ).all()
    )

def get_active_matches(db: Session, club_id: int) -> list[Matches]:
    return list(
        db.scalars(
            select(Matches)
            .options(load_only(Matches.match_id, Matches.snapshot, Matches.runtime_state))
            .where(
                or_(Matches.creator_id == club_id, Matches.visitor_id == club_id),
                Matches.status.in_(("WAITING", "WAITING_OPPONENT", "SCHEDULED", "RUNNING"))
            )
            .order_by(Matches.match_id)
            .execution_options(populate_existing=True)
        ).all()
    )

def get_default_team(db: Session, club_id: int)-> DefaultTeam | None:
    return db.scalar(
        select(DefaultTeam)
        .where(DefaultTeam.club_id == club_id)
        .execution_options(populate_existing=True)
    )

def get_active_league_lineups(db: Session, club_id: int) -> list[LeagueRegistration]:
    return list(
        db.scalars(
            select(LeagueRegistration)
            .join(League, League.id == LeagueRegistration.league_id)
            .where(
                LeagueRegistration.club_id == club_id,
                func.lower(League.status).not_in(TERMINAL_LEAGUE_STATUSES),
            )
            .order_by(LeagueRegistration.id)
            .execution_options(populate_existing=True)
        ).all()
    )

def soft_delete(db: Session, behaviour: Behavior) -> None:
    behaviour.is_deleted = True
    db.flush()


def update_behaviour(db: Session, behaviour: Behavior, *, name: str, code: str) -> Behavior:
    behaviour.name = name
    behaviour.code = code
    behaviour.version += 1
    behaviour.validation_status = "VALID"

    db.flush()
    return behaviour
