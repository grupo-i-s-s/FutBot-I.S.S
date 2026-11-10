from datetime import datetime, timezone
from sqlalchemy import and_, func, or_, select
from sqlalchemy.engine import Row
from sqlalchemy.orm import Session, load_only, selectinload
from typing import Optional

from app.models.auth_model import Club
from app.models.league_model import League, LeagueRegistration, LeagueRound, LeagueStanding
from app.models.matches_model import CHECKPOINT_UNRECOVERABLE, Matches
from app.models.behaviour_model import Behavior
from app.models.player_model import Player

def get_league_by_id(
        db: Session, league_id: int, *, load_registrations: bool = True,
) -> Optional[League]:
    query = (
        db.query(League)
        .filter(League.id == league_id)
        .with_for_update()
        .populate_existing()
    )
    if load_registrations:
        query = query.options(selectinload(League.registrations))
    return query.first()


def get_league_for_join(
        db: Session, league_id: int
) -> Optional[League]:
    return (
        db.query(League)
        .filter(League.id == league_id)
        .with_for_update()
        .populate_existing()
        .first()
    )


def count_registrations(db: Session, league_id: int) -> int:
    return (
        db.query(LeagueRegistration)
        .filter(LeagueRegistration.league_id == league_id)
        .count()
    )


def create_league(
        db: Session,
        name: str,
        min_teams: int,
        max_teams: int,
        start_date: datetime,
        round_interval: str,
        *,
        creator_club_id: int,
        creator_line_up: dict,
        is_private: bool = False,
        password_hash: str | None = None,
) -> League:
    league = League(
        name=name,
        min_teams=min_teams,
        max_teams=max_teams,
        start_datetime=start_date,
        round_interval=round_interval,
        creator_club_id=creator_club_id,
        is_private=is_private,
        password_hash=password_hash,
    )
    db.add(league)
    league.registrations.append(
        LeagueRegistration(club_id=creator_club_id, line_up=creator_line_up)
    )
    db.flush()
    return league


def get_clubs_by_ids(db: Session, club_ids: list[int]) -> list[Club]:
    if not club_ids:
        return []

    return db.query(Club).filter(Club.id.in_(club_ids)).all()


def create_round(
        db: Session, league_id: int, number: int,
        scheduled_at: datetime, bye_club_id: int | None,
        *, schedule_confirmed: bool = False,
) -> LeagueRound:
    round_ = LeagueRound(
        league_id=league_id, number=number,
        scheduled_at=scheduled_at, bye_club_id=bye_club_id,
        schedule_confirmed=schedule_confirmed,
    )
    db.add(round_)
    db.flush()
    return round_


def create_round_matches(
        db: Session, round_: LeagueRound, pairings: list[tuple[int, int]],
) -> None:
    for home_id, away_id in pairings:
        db.add(Matches(
            league_id=round_.league_id,
            league_round_id=round_.id,
            creator_id=home_id,
            visitor_id=away_id,
            init_date=round_.scheduled_at,
            status="SCHEDULED",
        ))
    db.flush()


def create_standings(db: Session, league_id: int, club_ids: list[int]) -> None:
    db.add_all([
        LeagueStanding(league_id=league_id, club_id=club_id)
        for club_id in club_ids
    ])
    db.flush()


def get_standings(db: Session, league_id: int) -> list[LeagueStanding]:
    return list(db.scalars(
        select(LeagueStanding)
        .where(LeagueStanding.league_id == league_id)
        .order_by(LeagueStanding.points.desc(), LeagueStanding.club_id)
    ).all())


def get_fixture_league(db: Session, league_id: int) -> League | None:
    return db.get(League, league_id)


def get_league_for_round(db: Session, round_id: int) -> League | None:
    return db.scalar(
        select(League)
        .join(LeagueRound, LeagueRound.league_id == League.id)
        .where(LeagueRound.id == round_id)
        .with_for_update(of=League)
        .execution_options(populate_existing=True)
    )


def get_fixture_rounds(db: Session, league_id: int) -> list[LeagueRound]:
    return list(db.scalars(
        select(LeagueRound)
        .where(LeagueRound.league_id == league_id)
        .order_by(LeagueRound.number)
    ).all())


def get_fixture_matches(db: Session, league_id: int) -> list[Matches]:
    return list(db.scalars(
        select(Matches)
        .options(load_only(
            Matches.match_id, Matches.league_round_id,
            Matches.creator_id, Matches.visitor_id, Matches.status,
            Matches.local_score, Matches.visitor_score, Matches.finished_at,
            Matches.cancellation_reason, raiseload=True,
        ))
        .join(LeagueRound, Matches.league_round_id == LeagueRound.id)
        .where(LeagueRound.league_id == league_id)
        .order_by(LeagueRound.number, Matches.match_id)
        .execution_options(populate_existing=True)
    ).all())


def get_first_unresolved_round(db: Session, league_id: int) -> LeagueRound | None:
    round_matches = select(Matches.match_id).where(Matches.league_round_id == LeagueRound.id)
    resolved = and_(
        Matches.finished_at.is_not(None),
        or_(
            Matches.status == "FINISHED",
            and_(Matches.status == "CANCELLED", Matches.cancellation_reason == CHECKPOINT_UNRECOVERABLE),
        ),
    )
    # Una ronda vacía también debe llegar al servicio para que detecte el fixture inválido.
    return db.scalar(
        select(LeagueRound)
        .where(
            LeagueRound.league_id == league_id,
            or_(~round_matches.exists(), round_matches.where(resolved.is_not(True)).exists()),
        )
        .order_by(LeagueRound.number)
        .limit(1)
        .execution_options(populate_existing=True)
    )


def has_fixture_rounds(db: Session, league_id: int) -> bool:
    return db.scalar(select(LeagueRound.id).where(LeagueRound.league_id == league_id).limit(1)) is not None


def get_round_match_states(db: Session, round_id: int):
    return db.execute(
        select(Matches.match_id, Matches.status)
        .where(Matches.league_round_id == round_id)
        .order_by(Matches.match_id)
    ).all()


def get_running_league_ids(db: Session) -> list[int]:
    return list(db.scalars(
        select(League.id).where(League.status == "running").order_by(League.id)
    ).all())


def get_round_matches_for_update(db: Session, round_id: int) -> list[Matches]:
    return list(db.scalars(
        select(Matches)
        .options(load_only(
            Matches.match_id, Matches.creator_id, Matches.visitor_id,
            Matches.duration_ms, Matches.sequence, Matches.started_at, Matches.finished_at,
            raiseload=True,
        ))
        .where(Matches.league_round_id == round_id)
        .order_by(Matches.match_id).with_for_update()
        .execution_options(populate_existing=True)
    ).all())


def get_round_registrations(db: Session, league_id: int, club_ids: tuple[int, ...]) -> list[LeagueRegistration]:
    return list(db.scalars(
        select(LeagueRegistration)
        .where(LeagueRegistration.league_id == league_id, LeagueRegistration.club_id.in_(club_ids))
        .execution_options(populate_existing=True)
    ).all())


def update_round_schedule(
        db: Session, round_: LeagueRound, matches: list[Matches],
        scheduled_at: datetime, confirmed: bool,
) -> None:
    round_.scheduled_at = scheduled_at
    round_.schedule_confirmed = confirmed
    for match in matches:
        match.init_date = scheduled_at
    db.flush()


def get_registration(
        db: Session, league_id: int, club_id: int
) -> Optional[LeagueRegistration]:
    return (
        db.query(LeagueRegistration)
        .filter(
            LeagueRegistration.league_id == league_id,
            LeagueRegistration.club_id == club_id,
        )
        .first()
    )


def delete_registration(
        db: Session, registration: LeagueRegistration
) -> None:
    db.delete(registration)


def create_registration(
        db: Session,
        league_id: int,
        club_id: int,
        line_up: dict,
) -> LeagueRegistration:
    registration = LeagueRegistration(
        league_id=league_id,
        club_id=club_id,
        joined_at=datetime.now(timezone.utc),
        line_up=line_up,
    )
    db.add(registration)
    db.flush()
    return registration


def get_available_leagues(
        db: Session,
        club_id: int,
        *,
        name: str | None = None,
        page: int | None = None,
        limit: int | None = None,
) -> tuple[list[Row[tuple[League, int, bool]]], int | None]:
    registered_count = (
        select(func.count(LeagueRegistration.id))
        .where(LeagueRegistration.league_id == League.id)
        .correlate(League)
        .scalar_subquery()
    )
    conditions = [League.status == "open", registered_count < League.max_teams]
    if name:
        conditions.append(League.name.icontains(name, autoescape=True))

    query = (
        select(
            League,
            registered_count,
            League.registrations.any(LeagueRegistration.club_id == club_id),
        )
        .where(*conditions)
        .order_by(League.id.desc())
    )
    total = None
    if page is not None and limit is not None:
        total = db.execute(select(func.count()).select_from(League).where(*conditions)).scalar_one()
        offset = (page - 1) * limit
        if offset >= total:
            return [], total
        query = query.offset(offset).limit(limit)

    return list(db.execute(query).all()), total

def get_completed_matches(league_id: int, db: Session):
    return db.scalars(
        select(Matches).join(LeagueRound, Matches.league_round_id == LeagueRound.id)
        .where(LeagueRound.league_id == league_id, Matches.status == "FINISHED")
    ).all()

def delete_league(db: Session, league: League) -> None:
    db.delete(league)

#Busca incscripcion de un club en una liga especifica
def get_lineup_context(db: Session, league_id: int, club_id: int, *, lock: bool = False):
    """Busca la liga y la inscripción del club autenticado."""
    league_query = (
        select(League)
        .where(League.id == league_id)
        .execution_options(populate_existing=True)
    )

    if lock:
        league_query = league_query.with_for_update()

    league = db.scalar(league_query)

    if league is None:
        return None, None

    registration_query = (
        select(LeagueRegistration)
        .where(
            LeagueRegistration.league_id == league_id,
            LeagueRegistration.club_id == club_id,
        )
        .execution_options(populate_existing=True)
    )

    if lock:
        registration_query = registration_query.with_for_update()

    return league, db.scalar(registration_query)


def get_lineup_catalogs(db: Session, club_id: int):
    """Lee registros propios y activos, bloqueando sus modificaciones."""
    catalogs = []

    for model in (Player, Behavior):
        rows = db.scalars(
            select(model)
            .where(
                model.club_id == club_id,
                model.is_deleted.is_(False),
            )
            .order_by(model.id)
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        ).all()

        catalogs.append({row.id: row for row in rows})

    return catalogs[0], catalogs[1]
