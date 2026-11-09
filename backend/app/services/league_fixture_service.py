from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repository import league_repository

ROUND_INTERVALS = {
    "CONTINUOUS": timedelta(seconds=360),
    "DAILY": timedelta(days=1),
    "WEEKLY": timedelta(days=7),
}
PENDING_STATUSES = {"WAITING", "WAITING_OPPONENT", "SCHEDULED"}


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_league_fixture(db: Session, league_id: int, club_id: int) -> dict:
    league = league_repository.get_fixture_league(db, league_id)
    if league is None:
        raise HTTPException(404, "La liga no existe.")

    rounds = league_repository.get_fixture_rounds(db, league_id)
    matches = league_repository.get_fixture_matches(db, league_id)
    club_ids = {id_ for match in matches for id_ in (match.creator_id, match.visitor_id)}
    clubs = league_repository.get_clubs_by_ids(db, list(club_ids))
    names = {club.id: club.name for club in clubs}
    matches_by_round = {round_.id: [] for round_ in rounds}
    for match in matches:
        matches_by_round[match.league_round_id].append(match)

    result = {"league_id": league_id, "rounds": [], "next_match": None}
    for round_ in rounds:
        round_data = {
            "number": round_.number,
            "scheduled_at": _utc(round_.scheduled_at),
            "schedule_confirmed": round_.schedule_confirmed,
            "bye_club_id": round_.bye_club_id,
            "matches": [],
        }
        for match in matches_by_round[round_.id]:
            match_data = {
                "match_id": match.match_id,
                "creator_club_id": match.creator_id,
                "creator_club_name": names[match.creator_id],
                "visitor_club_id": match.visitor_id,
                "visitor_club_name": names[match.visitor_id],
                "status": match.status,
                "local_score": match.local_score,
                "visitor_score": match.visitor_score,
            }
            round_data["matches"].append(match_data)
            if (
                result["next_match"] is None
                and league.status == "running"
                and club_id in (match.creator_id, match.visitor_id)
                and match.status in PENDING_STATUSES
            ):
                result["next_match"] = {
                    **match_data,
                    "round_number": round_.number,
                    "scheduled_at": round_data["scheduled_at"],
                    "schedule_confirmed": round_.schedule_confirmed,
                }
        result["rounds"].append(round_data)
    return result


def update_fixture_schedule(db: Session, round_id: int) -> None:
    """Se llama al finalizar un partido, dentro de la misma transacción."""
    league = league_repository.get_league_for_round(db, round_id)
    if league is None or league.status != "running":
        return

    rounds = league_repository.get_fixture_rounds(db, league.id)
    matches = league_repository.get_fixture_matches(db, league.id)
    if matches and all(match.status == "FINISHED" for match in matches):
        league.status = "finished"
        return
    matches_by_round = {round_.id: [] for round_ in rounds}
    for match in matches:
        matches_by_round[match.league_round_id].append(match)

    interval = ROUND_INTERVALS[league.round_interval]
    for previous, current in zip(rounds, rounds[1:]):
        current_matches = matches_by_round[current.id]
        # Conservar horarios ya confirmados y partidos que ya comenzaron.
        if current.schedule_confirmed or any(
            match.status not in PENDING_STATUSES for match in current_matches
        ):
            continue

        previous_matches = matches_by_round[previous.id]
        confirmed = bool(previous_matches) and all(
            match.status == "FINISHED" and match.finished_at is not None
            for match in previous_matches
        )
        if confirmed:
            scheduled_at = max(_utc(match.finished_at) for match in previous_matches) + interval
        else:
            scheduled_at = _utc(previous.scheduled_at) + interval

        if scheduled_at != _utc(current.scheduled_at) or confirmed != current.schedule_confirmed:
            league_repository.update_round_schedule(
                db, current, current_matches, scheduled_at, confirmed,
            )
