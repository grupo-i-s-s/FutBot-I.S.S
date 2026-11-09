from sqlalchemy.orm import Session

from app.models.matches_model import Matches
from app.repository import league_repository, stats_repository
from app.services.matches_service import TEST_OPPONENT_CLUB_ID


def process_match_for_global_ranking(db: Session, match: Matches) -> None:
    local_id = match.creator_id
    visitor_id = match.visitor_id
    if visitor_id is None or TEST_OPPONENT_CLUB_ID in (local_id, visitor_id):
        return

    if match.league_round_id is not None or match.league_id is not None:
        league = (
            league_repository.get_league_for_round(db, match.league_round_id)
            if match.league_round_id is not None
            else league_repository.get_fixture_league(db, match.league_id)
        )
        if league is None or league.is_private:
            return

    local_score = match.local_score
    visitor_score = match.visitor_score

    if local_score > visitor_score:
        local_pts, visitor_pts = 3, 0
        local_res, visitor_res = (1, 0, 0), (0, 0, 1)
    elif local_score < visitor_score:
        local_pts, visitor_pts = 0, 3
        local_res, visitor_res = (0, 0, 1), (1, 0, 0)
    else:
        local_pts, visitor_pts = 1, 1
        local_res, visitor_res = (0, 1, 0), (0, 1, 0)

    stats_repository.increment_club_stats(
        db, local_id, local_pts, *local_res, local_score, visitor_score
    )

    stats_repository.increment_club_stats(
        db, visitor_id, visitor_pts, *visitor_res, visitor_score, local_score
    )
