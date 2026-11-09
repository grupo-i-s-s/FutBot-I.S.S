import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.errors import AppError
from app.repository import league_repository, matches_repository
from app.services.league_fixture_service import PENDING_STATUSES, _utc, is_resolved_league_match
from app.services.league_lineup_service import capture_registration_lineup
from app.services.match_builder_service import build_match

logger = logging.getLogger(__name__)


def prepare_league_round(db: Session, league_id: int, now: datetime) -> list[int]:
    try:
        league = league_repository.get_league_by_id(db, league_id)
        if league is None or league.status != "running":
            db.rollback()
            return []

        rounds = league_repository.get_fixture_rounds(db, league_id)
        matches = league_repository.get_fixture_matches(db, league_id)
        for round_ in rounds:
            current = [match for match in matches if match.league_round_id == round_.id]
            if not current:
                raise AppError("LEAGUE_FIXTURE_INVALID", "La ronda no tiene partidos.")
            if all(is_resolved_league_match(match) for match in current):
                continue

            running = [match.match_id for match in current if match.status == "RUNNING"]
            if running:
                db.commit()
                return running
            if any(match.status not in PENDING_STATUSES for match in current):
                raise AppError("LEAGUE_FIXTURE_INVALID", "La ronda contiene un partido cancelado.")
            if not round_.schedule_confirmed or _utc(round_.scheduled_at) > _utc(now):
                db.commit()
                return []

            current = league_repository.get_round_matches_for_update(db, round_.id)
            club_ids = tuple(sorted({
                id_ for match in current for id_ in (match.creator_id, match.visitor_id)
            }))
            clubs = matches_repository.get_clubs_for_update(db, club_ids)
            if len(clubs) != len(club_ids):
                raise AppError("LEAGUE_FIXTURE_INVALID", "Falta un club de la ronda.")
            if matches_repository.clubs_have_running_match(db, club_ids):
                db.commit()
                return []

            registrations = {row.club_id: row for row in league.registrations}
            lineups = {}
            for club_id in club_ids:
                lineups[str(club_id)] = capture_registration_lineup(
                    db,
                    registrations[club_id],
                    league.creator_club_id,
                    allow_legacy_reorder=True,
                )
            simulations = [
                build_match(db, match.match_id, league_teams=registrations) for match in current
            ]
            league_repository.update_round_schedule(db, round_, current, now, True)
            for match, simulation in zip(current, simulations, strict=True):
                match.league_id = league.id
                match.lineup_snapshot = {
                    "leagueId": league.id,
                    "teams": {
                        str(club_id): lineups[str(club_id)]
                        for club_id in (match.creator_id, match.visitor_id)
                    },
                }
                snapshot = simulation.snapshot(match.sequence + 1, now.isoformat())
                matches_repository.save_progress(db, match, simulation, snapshot, now)
            db.commit()
            return [match.match_id for match in current]

        if matches:
            league.status = "finished"
        db.commit()
        return []
    except Exception:
        db.rollback()
        raise


def get_due_league_match_ids(db: Session, now: datetime) -> list[int]:
    match_ids = []
    for league_id in league_repository.get_running_league_ids(db):
        try:
            match_ids.extend(prepare_league_round(db, league_id, now))
        except Exception:
            # Una liga inválida no detiene las demás ligas ni los amistosos.
            logger.exception("No se pudo preparar la liga %s", league_id)
    return match_ids
