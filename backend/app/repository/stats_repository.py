from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth_model import Club
from app.models.stats_model import Stats


def get_club_stats(db: Session, club_id: int) -> dict:
    query = select(
        Stats.points,
        Stats.played,
        Stats.wins,
        Stats.losses,
        Stats.draws,
        Stats.gF,
        Stats.gA,
    ).where(Stats.club_id == club_id)
    return db.execute(query).mappings().first()


def get_rankings(db: Session, limit: int = 100):
    query = (
        select(
            Club.id,
            Club.name,
            Club.avatar,
            Stats.points,
            Stats.played,
            Stats.wins,
            Stats.draws,
            Stats.losses,
            (Stats.gF - Stats.gA).label("dg"),
        )
        .join(Club.stats)
        .order_by(
            Stats.points.desc(),
            (Stats.gF - Stats.gA).desc(),
            Stats.gF.desc(),
            Club.name.asc(),
        )
        .limit(limit)
    )
    return db.execute(query).mappings().all()


def increment_club_stats(
    db: Session,
    club_id: int,
    points: int,
    win: int,
    draw: int,
    loss: int,
    gf: int,
    ga: int,
) -> None:
    stats = db.scalar(select(Stats).where(Stats.club_id == club_id).with_for_update())
    if stats:
        stats.points += points
        stats.played += 1
        stats.wins += win
        stats.draws += draw
        stats.losses += loss
        stats.gF += gf
        stats.gA += ga
        db.flush()
