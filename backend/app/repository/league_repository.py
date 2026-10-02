from typing import Optional

from sqlalchemy.orm import Session, joinedload

from datetime import datetime

from app.models.league_model import League, LeagueRegistration


def get_league_by_id(db: Session, league_id: int) -> Optional[League]:
    return (
        db.query(League)
        .options(joinedload(League.registrations))
        .filter(League.id == league_id)
        .with_for_update()
        .first()
    )


def get_league_for_join(
    db: Session, league_id: int
) -> Optional[League]:
    return (
        db.query(League)
        .filter(League.id == league_id)
        .with_for_update()
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
) -> League:
    league = League(
        name=name,
        min_teams=min_teams,
        max_teams=max_teams,
        start_datetime=start_date,
        round_interval=round_interval,
    )
    db.add(league)
    db.flush()
    return league


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
        line_up=line_up,
    )
    db.add(registration)
    db.flush()
    return registration