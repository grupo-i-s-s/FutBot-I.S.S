from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.repository import matches_repository
from app.services.league_fixture_service import _utc
from primitives.match_breaks import MatchBreaks

LEAGUE_SCHEDULE_CONFLICT = "LEAGUE_SCHEDULE_CONFLICT"
FRIENDLY_SCHEDULE_CONFLICT = "FRIENDLY_SCHEDULE_CONFLICT"
DEFAULT_BREAKS_MS = sum(MatchBreaks().durations_ms)


def _slot_end(start: datetime, duration_ms: int) -> datetime:
    return start + timedelta(milliseconds=duration_ms + DEFAULT_BREAKS_MS)


def find_league_schedule_conflict(
    db: Session, club_ids: tuple[int, ...], start: datetime, duration_ms: int,
) -> tuple[datetime, datetime] | None:
    start = _utc(start)
    end = _slot_end(start, duration_ms)
    for league_start, league_duration in matches_repository.get_confirmed_league_slots(db, club_ids, end):
        league_start = _utc(league_start)
        league_end = _slot_end(league_start, league_duration)
        if start < league_end:
            return league_start, league_end
    return None


def find_friendly_schedule_conflict(
    db: Session, club_ids: tuple[int, ...], start: datetime, duration_ms: int,
) -> tuple[datetime, datetime, tuple[int, int]] | None:
    start = _utc(start)
    end = _slot_end(start, duration_ms)
    for slot_start, slot_duration, creator_id, visitor_id in matches_repository.get_confirmed_friendly_slots(
        db, club_ids, end,
    ):
        slot_start = _utc(slot_start)
        slot_end = _slot_end(slot_start, slot_duration)
        if start < slot_end:
            return slot_start, slot_end, (creator_id, visitor_id)
    return None
