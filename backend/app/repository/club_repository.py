from sqlalchemy import select, func, case, union_all
from sqlalchemy.orm import Session, selectinload
from app.models.league_model import League, LeagueRegistration, LeagueRound
from app.models.matches_model import Matches

from app.models.auth_model import Club
from app.models.league_model import League, LeagueRegistration


def update_club(
        db: Session,
        club: Club,
        *,
        name: str,
        avatar: str,
        friendly_available: bool,
) -> Club:
    club.name = name
    club.avatar = avatar
    club.friendly_available = friendly_available
    db.flush()
    return club


def get_joined_leagues(db: Session, club_id: int) -> list[League]:
    query = (
        select(League)
        .where(
            League.registrations.any(
                LeagueRegistration.club_id == club_id
            )
        )
        .options(selectinload(League.registrations))
        .order_by(League.id)
    )

    return list(db.scalars(query).all())

def get_clubs( db: Session, *, exclude_user_id: int, name: str | None, page: int, page_size: int) -> tuple[list[Club], int]:
    query = select(Club).where( Club.user_id != exclude_user_id)

    if name:
        query = query.where(
            Club.name.icontains(name, autoescape=True)
        )

    total = db.scalar(
        select(func.count()).select_from(query.subquery())
    )

    clubs = db.scalars(
        query
        .order_by(Club.name, Club.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return list(clubs), total

def get_club_profile_data(db: Session, club_id: int) -> dict | None:
    # Los partidos de liga actuales se relacionan mediante su ronda.
    finished = (
        select(
            Matches.creator_id.label("home_id"),
            Matches.visitor_id.label("away_id"),
            Matches.local_score.label("home_score"),
            Matches.visitor_score.label("away_score"),
            func.coalesce(
                LeagueRound.league_id,
                Matches.league_id,
            ).label("league_id"),
        )
        .select_from(Matches)
        .outerjoin(
            LeagueRound,
            LeagueRound.id == Matches.league_round_id,
        )
        .where(
            Matches.status == "FINISHED",
            Matches.finished_at.is_not(None),
            Matches.visitor_id.is_not(None),
        )
        .subquery("finished_matches")
    )

    # Cada partido aporta una fila para cada club participante.
    results = union_all(
        select(
            finished.c.home_id.label("club_id"),
            finished.c.home_score.label("goals_for"),
            finished.c.away_score.label("goals_against"),
            finished.c.league_id,
        ),
        select(
            finished.c.away_id.label("club_id"),
            finished.c.away_score.label("goals_for"),
            finished.c.home_score.label("goals_against"),
            finished.c.league_id,
        ),
    ).subquery("club_results")

    won = results.c.goals_for > results.c.goals_against
    drawn = results.c.goals_for == results.c.goals_against
    lost = results.c.goals_for < results.c.goals_against
    is_public = League.is_private.is_(False)

    match_points = case(
        (won, 3),
        (drawn, 1),
        else_=0,
    )

    summary = (
        select(
            Club.id,
            Club.name,
            Club.avatar,
            func.count(results.c.club_id).label("played"),
            func.sum(case((won, 1), else_=0)).label("wins"),
            func.sum(case((drawn, 1), else_=0)).label("draws"),
            func.sum(case((lost, 1), else_=0)).label("losses"),
            func.sum(
                case((is_public, match_points), else_=0)
            ).label("points"),
            func.sum(
                case((is_public, results.c.goals_for), else_=0)
            ).label("goals_for"),
            func.sum(
                case((is_public, results.c.goals_against), else_=0)
            ).label("goals_against"),
        )
        .select_from(Club)
        .outerjoin(results, results.c.club_id == Club.id)
        .outerjoin(League, League.id == results.c.league_id)
        .group_by(Club.id, Club.name, Club.avatar)
        .subquery("club_summary")
    )

    goal_difference = summary.c.goals_for - summary.c.goals_against

    ranked = select(
        summary,
        func.row_number().over(
            order_by=(
                summary.c.points.desc(),
                goal_difference.desc(),
                summary.c.goals_for.desc(),
                summary.c.goals_against.asc(),
                summary.c.id.asc(),
            )
        ).label("position"),
    ).subquery("ranked_clubs")

    # Filtramos después de calcular las posiciones globales.
    row = db.execute(
        select(ranked).where(ranked.c.id == club_id)
    ).mappings().one_or_none()

    return dict(row) if row is not None else None