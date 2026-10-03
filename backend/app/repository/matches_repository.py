from datetime import datetime
from contextlib import contextmanager

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.auth_model import Club
from app.models.behaviour_model import Behavior
from app.models.matches_model import Matches
from app.models.player_model import Player
from app.database import engine
from app.errors import AppError


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


def get_by_id(db: Session, match_id: int) -> Matches | None:
    return db.get(Matches, match_id)


def get_by_id_for_update(db: Session, match_id: int) -> Matches | None:
    return db.scalar(select(Matches).where(Matches.match_id == match_id).with_for_update().execution_options(populate_existing=True))


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


def list_available(db: Session, club_id: int, now: datetime):
    return db.execute(
        select(Matches, Club.name)
        .join(Club, Club.id == Matches.creator_id)
        .where(
            Matches.visitor_id.is_(None),
            Matches.creator_id != club_id,
            Matches.init_date > now,
            Matches.status == "WAITING",
        )
        .order_by(Matches.init_date, Matches.match_id)
    ).all()
