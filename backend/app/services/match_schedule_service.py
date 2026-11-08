from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.repository import matches_repository
from app.services.league_fixture_service import _utc
from primitives.match_breaks import MatchBreaks

LEAGUE_SCHEDULE_CONFLICT = "LEAGUE_SCHEDULE_CONFLICT"
DEFAULT_BREAKS_MS = sum(MatchBreaks().durations_ms)


def find_league_schedule_conflict(
    db: Session, club_ids: tuple[int, ...], start: datetime, duration_ms: int,
) -> tuple[datetime, datetime] | None:
    start = _utc(start)
    end = start + timedelta(milliseconds=duration_ms + DEFAULT_BREAKS_MS)
    for league_start, league_duration in matches_repository.get_confirmed_league_slots(db, club_ids, end):
        league_start = _utc(league_start)
        league_end = league_start + timedelta(milliseconds=league_duration + DEFAULT_BREAKS_MS)
        if start < league_end:
            return league_start, league_end
    return None
