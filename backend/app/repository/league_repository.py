from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from typing import Optional

from app.models.auth_model import Club
from app.models.league_model import League, LeagueRegistration, LeagueRound, LeagueStanding
from app.models.matches_model import Matches


def get_league_by_id(db: Session, league_id: int) -> Optional[League]:
    return (
        db.query(League)
        .options(selectinload(League.registrations))
        .filter(League.id == league_id)
        .with_for_update()
        .populate_existing()
        .first()
    )


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
        LeagueRegistration(club_id=creator_club_id)
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
        .join(LeagueRound, Matches.league_round_id == LeagueRound.id)
        .where(LeagueRound.league_id == league_id)
        .order_by(LeagueRound.number, Matches.match_id)
        .execution_options(populate_existing=True)
    ).all())


def get_running_league_ids(db: Session) -> list[int]:
    return list(db.scalars(
        select(League.id).where(League.status == "running").order_by(League.id)
    ).all())


def get_round_matches_for_update(db: Session, round_id: int) -> list[Matches]:
    return list(db.scalars(
        select(Matches).where(Matches.league_round_id == round_id)
        .order_by(Matches.match_id).with_for_update()
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
        line_up: list | dict,
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


def get_all_available_leagues(
        db: Session,
        name: str | None = None,
) -> list[League]:
    query = (
        select(League)
        .options(selectinload(League.registrations))
        .order_by(League.id.desc())
    )

    if name:
        query = query.where(
            League.name.icontains(name, autoescape=True)
        )

    return list(db.scalars(query).all())

def get_completed_matches(league_id: int, db: Session):
    return db.scalars(
        select(Matches).join(LeagueRound, Matches.league_round_id == LeagueRound.id)
        .where(LeagueRound.league_id == league_id, Matches.status == "FINISHED")
    ).all()

def delete_league(db: Session, league: League) -> None:
    db.delete(league)
