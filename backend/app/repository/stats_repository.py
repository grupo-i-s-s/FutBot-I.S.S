from sqlalchemy import and_, case, func, select, union_all
from sqlalchemy.orm import Session

from app.models.auth_model import Club
from app.models.league_model import League, LeagueRound
from app.models.matches_model import Matches, TEST_OPPONENT_CLUB_ID


def _ranked_clubs():
    # Las rondas identifican la liga de los partidos nuevos. Los históricos
    # pueden tener solo el vínculo directo y se cuentan con la misma regla.
    finished = (
        select(
            Matches.creator_id.label("home_id"),
            Matches.visitor_id.label("away_id"),
            Matches.local_score.label("home_score"),
            Matches.visitor_score.label("away_score"),
            func.coalesce(LeagueRound.league_id, Matches.league_id).label("league_id"),
        )
        .select_from(Matches)
        .outerjoin(LeagueRound, LeagueRound.id == Matches.league_round_id)
        .where(
            Matches.status == "FINISHED",
            Matches.finished_at.is_not(None),
            Matches.visitor_id.is_not(None),
            Matches.creator_id != TEST_OPPONENT_CLUB_ID,
            Matches.visitor_id != TEST_OPPONENT_CLUB_ID,
        )
        .cte("finished_matches")
    )
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
    public = League.is_private.is_(False)
    points = case((won, 3), (drawn, 1), else_=0)

    def count_where(condition):
        return func.sum(case((condition, 1), else_=0))

    summary = (
        select(
            Club.id,
            Club.name,
            Club.avatar,
            func.count(results.c.club_id).label("played"),
            count_where(won).label("wins"),
            count_where(drawn).label("draws"),
            count_where(lost).label("losses"),
            count_where(public).label("ranked_played"),
            count_where(and_(public, won)).label("ranked_wins"),
            count_where(and_(public, drawn)).label("ranked_draws"),
            count_where(and_(public, lost)).label("ranked_losses"),
            func.sum(case((public, points), else_=0)).label("points"),
            func.sum(case((public, results.c.goals_for), else_=0)).label("goals_for"),
            func.sum(case((public, results.c.goals_against), else_=0)).label("goals_against"),
        )
        .select_from(Club)
        .outerjoin(results, results.c.club_id == Club.id)
        .outerjoin(League, League.id == results.c.league_id)
        .where(Club.id != TEST_OPPONENT_CLUB_ID)
        .group_by(Club.id, Club.name, Club.avatar)
    ).subquery("club_summary")
    goal_difference = summary.c.goals_for - summary.c.goals_against

    return select(
        summary,
        goal_difference.label("dg"),
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


def get_club_profile_stats(db: Session, club_id: int) -> dict | None:
    ranked = _ranked_clubs()
    # El filtro debe aplicarse después de calcular el puesto de todos los clubes.
    row = db.execute(select(ranked).where(ranked.c.id == club_id)).mappings().one_or_none()
    return dict(row) if row is not None else None


def get_rankings(db: Session, *, page: int, page_size: int) -> tuple[list[dict], int]:
    ranked = _ranked_clubs()
    query = (
        select(
            ranked.c.id,
            ranked.c.name,
            ranked.c.avatar,
            ranked.c.position,
            ranked.c.points,
            ranked.c.ranked_played.label("played"),
            ranked.c.ranked_wins.label("wins"),
            ranked.c.ranked_draws.label("draws"),
            ranked.c.ranked_losses.label("losses"),
            ranked.c.goals_for,
            ranked.c.goals_against,
            ranked.c.dg,
        )
        .order_by(ranked.c.position)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    total = db.scalar(select(func.count(Club.id)).where(Club.id != TEST_OPPONENT_CLUB_ID))
    return [dict(row) for row in db.execute(query).mappings()], total
