from contextlib import contextmanager
from datetime import datetime
from sqlalchemy import func, or_, select, text, update
from sqlalchemy.orm import Session, aliased

from app.database import engine
from app.errors import AppError
from app.models.auth_model import Club
from app.models.behaviour_model import Behavior
from app.models.league_model import League, LeagueRound
from app.models.matches_model import Matches, TEST_OPPONENT_CLUB_ID
from app.models.player_model import Player
from app.models.planned_substitution_model import PlannedSubstitution


def get_starting_players(db: Session, club_id: int) -> list[tuple[Player, Behavior]]:
    return list(
        db.execute(
            select(Player, Behavior)
            .join(Behavior, Player.behavior_id == Behavior.id)
            .where(
                Player.club_id == club_id,
                Player.is_deleted.is_(False),
                Behavior.club_id == club_id,
                Behavior.is_deleted.is_(False),
            )
            .order_by(Player.id)
            .limit(3)
        ).all()
    )


def get_club_names(db: Session, club_ids: tuple[int, ...]) -> dict[int, str]:
    return dict(
        db.execute(
            select(Club.id, Club.name).where(Club.id.in_(club_ids))
        ).all()
    )


def get_club_avatars(db: Session, club_ids: tuple[int, ...]) -> dict[int, str]:
    return dict(
        db.execute(
            select(Club.id, Club.avatar).where(Club.id.in_(club_ids))
        ).all()
    )


def get_by_id(db: Session, match_id: int) -> Matches | None:
    return db.get(Matches, match_id)


def get_by_id_for_update(db: Session, match_id: int) -> Matches | None:
    return db.scalar(
        select(Matches).where(Matches.match_id == match_id).with_for_update().execution_options(populate_existing=True))


def expire_pending_substitutions(db: Session, match_id: int) -> None:
    """Cierra los planes pendientes bajo el bloqueo del partido."""
    db.execute(
        update(PlannedSubstitution)
        .where(PlannedSubstitution.match_id == match_id, PlannedSubstitution.status == "PENDING")
        .values(status="EXPIRED")
    )


@contextmanager
def execution_session(match_id: int):
    """Un escritor por partido, incluso entre distintos procesos del backend.

    El bloqueo de sesión vive en esta conexión durante toda la ejecución y se
    libera antes de devolverla al pool. Un commit de un snapshot no lo libera.
    """
    params = {"namespace": 46001, "match_id": match_id}
    with engine.connect() as connection:
        try:
            acquired = connection.scalar(text("SELECT pg_try_advisory_lock(:namespace, :match_id)"), params)
            connection.commit()
        except Exception:
            connection.invalidate()
            raise
        if not acquired:
            raise AppError("MATCH_ALREADY_RUNNING", "Otro ejecutor está simulando este partido.")
        try:
            with Session(bind=connection, expire_on_commit=False) as db:
                yield db
        finally:
            try:
                connection.rollback()
                connection.execute(text("SELECT pg_advisory_unlock(:namespace, :match_id)"), params)
                connection.commit()
            except Exception:
                # No devolver al pool una sesión PostgreSQL que conserve el lock.
                connection.invalidate()
                raise


def save_progress(db: Session, row: Matches, simulation, snapshot: dict, now: datetime) -> None:
    row.status = simulation.status
    row.clock_ms = snapshot["state"]["clockMs"]
    row.duration_ms = simulation.duration_ms
    row.local_score = simulation.scorer["LOCAL"]
    row.visitor_score = simulation.scorer["VISITANTE"]
    row.sequence = snapshot["sequence"]
    row.snapshot = snapshot
    row.runtime_state = simulation.checkpoint()
    if row.started_at is None:
        row.started_at = now
    if simulation.finished and row.finished_at is None:
        row.finished_at = now
    db.add(row)


def list_available(db: Session, club_id: int, now: datetime, *, creator_name: str | None = None,
                   page: int = 1, page_size: int = 20):
    query = (
        select(Matches, Club.name)
        .join(Club, Club.id == Matches.creator_id)
        .where(
            Club.friendly_available.is_(True),
            Matches.visitor_id.is_(None),
            Matches.creator_id != club_id,
            Matches.init_date > now,
            Matches.status.in_(("WAITING", "WAITING_OPPONENT")),
        )
    )
    if creator_name:
        query = query.where(Club.name.icontains(creator_name, autoescape=True))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.execute(query.order_by(Matches.init_date, Matches.match_id)
                       .offset((page - 1) * page_size).limit(page_size)).all()
    return items, total


def list_for_club(db: Session, club_id: int):
    creator = aliased(Club)
    visitor = aliased(Club)
    return db.execute(
        select(Matches, creator.name, visitor.name)
        .join(creator, creator.id == Matches.creator_id)
        .outerjoin(visitor, visitor.id == Matches.visitor_id)
        .where(
            or_(Matches.creator_id == club_id, Matches.visitor_id == club_id),
            Matches.league_round_id.is_(None),
            Matches.creator_id != TEST_OPPONENT_CLUB_ID,
            Matches.visitor_id.is_distinct_from(TEST_OPPONENT_CLUB_ID),
        )
        .order_by(Matches.init_date.desc(), Matches.match_id.desc())
    ).all()


def get_due_match_ids(db: Session, now: datetime) -> list[int]:
    return list(
        db.scalars(
            select(Matches.match_id)
            .where(
                Matches.league_round_id.is_(None),
                Matches.init_date <= now,
                Matches.status.in_(("WAITING", "WAITING_OPPONENT", "SCHEDULED", "RUNNING")),
            )
            .order_by(Matches.init_date, Matches.match_id)
        ).all()
    )


def get_confirmed_league_slots(db: Session, club_ids: tuple[int, ...], before: datetime):
    # Las escrituras de horarios se sincronizan por club. No bloquear partidos
    # ajenos aquí: sus ejecutores adquieren primero la fila de su partido.
    return db.execute(
        select(LeagueRound.scheduled_at, Matches.duration_ms)
        .join(LeagueRound, LeagueRound.id == Matches.league_round_id)
        .join(League, League.id == LeagueRound.league_id)
        .where(
            League.status == "running",
            LeagueRound.schedule_confirmed.is_(True),
            Matches.status.not_in(("FINISHED", "CANCELLED")),
            LeagueRound.scheduled_at < before,
            or_(Matches.creator_id.in_(club_ids), Matches.visitor_id.in_(club_ids)),
        )
        .order_by(LeagueRound.scheduled_at, Matches.match_id)
    ).all()


def get_confirmed_friendly_slots(db: Session, club_ids: tuple[int, ...], before: datetime):
    # El join ya bloqueó ambos clubes. Leer sin bloquear otros partidos evita
    # competir con otro join que haya adquirido primero la fila de su invitación.
    return db.execute(
        select(Matches.init_date, Matches.duration_ms, Matches.creator_id, Matches.visitor_id)
        .where(
            Matches.league_round_id.is_(None),
            Matches.league_id.is_(None),
            Matches.status.not_in(("FINISHED", "CANCELLED")),
            # Las confirmaciones anteriores a SCHEDULED conservan WAITING con visitante.
            Matches.visitor_id.is_not(None),
            Matches.creator_id != TEST_OPPONENT_CLUB_ID,
            Matches.visitor_id != TEST_OPPONENT_CLUB_ID,
            Matches.init_date < before,
            or_(Matches.creator_id.in_(club_ids), Matches.visitor_id.in_(club_ids)),
        )
        .order_by(Matches.init_date, Matches.match_id)
    ).all()


def get_clubs_for_update(db: Session, club_ids: tuple[int, ...]) -> list[Club]:
    return list(
        db.scalars(
            select(Club)
            .where(Club.id.in_(club_ids))
            .order_by(Club.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).all()
    )

def clubs_have_running_match(db: Session, club_ids: tuple[int, ...], match_id: int | None = None) -> bool:
    query = (
        select(Matches.match_id)
        .where(
            Matches.status == "RUNNING",
            or_(
                Matches.creator_id.in_(club_ids),
                Matches.visitor_id.in_(club_ids),
            ),
        )
        .limit(1)
    )
    if match_id is not None:
        query = query.where(Matches.match_id != match_id)
    return db.scalar(query) is not None

def get_active_test_match(db: Session, club_id: int, bot_club_id: int) -> Matches | None:
    return db.scalar(
        select(Matches)
        .where(
            Matches.creator_id == club_id,
            Matches.visitor_id == bot_club_id,
            Matches.league_round_id.is_(None),
            Matches.status.in_(
                ("WAITING", "WAITING_OPPONENT", "SCHEDULED", "RUNNING")
            ),
        )
        .order_by(Matches.match_id)
        .limit(1)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
