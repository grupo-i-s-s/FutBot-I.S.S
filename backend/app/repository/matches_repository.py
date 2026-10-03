from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth_model import Club
from app.models.behaviour_model import Behavior
from app.models.matches_model import Matches
from app.models.player_model import Player


def get_starting_players(db: Session, club_id: int) -> list[Player]:
    return list(
        db.scalars(
            select(Player)
            .join(Behavior, Player.behavior_id == Behavior.id)
            .where(
                Player.club_id == club_id,
                Player.is_deleted.is_(False),
                Behavior.club_id == club_id,
                Behavior.is_deleted.is_(False),
            )
            .order_by(Player.id)
            .limit(3)
        )
    )


def get_club_names(db: Session, club_ids: tuple[int, int]) -> dict[int, str]:
    return dict(
        db.execute(
            select(Club.id, Club.name).where(Club.id.in_(club_ids))
        ).all()
    )


def get_by_id(db: Session, match_id: int) -> Matches | None:
    return db.get(Matches, match_id)


def get_by_id_for_update(db: Session, match_id: int) -> Matches | None:
    return db.scalar(select(Matches).where(Matches.match_id == match_id).with_for_update())


def list_available(db: Session, club_id: int, now: datetime):
    return db.execute(
        select(Matches, Club.name)
        .join(Club, Club.id == Matches.creator_id)
        .where(
            Matches.visitor_id.is_(None),
            Matches.creator_id != club_id,
            Matches.init_date > now,
        )
        .order_by(Matches.init_date, Matches.match_id)
    ).all()
