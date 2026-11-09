import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.errors import AppError
from app.repository import league_repository, matches_repository
from app.services.league_fixture_service import PENDING_STATUSES, _utc
from app.services.league_lineup_service import capture_registration_lineup
from app.services.match_builder_service import build_match

logger = logging.getLogger(__name__)


def prepare_league_round(db: Session, league_id: int, now: datetime) -> list[int]:
    try:
        league = league_repository.get_league_by_id(db, league_id, load_registrations=False)
        if league is None or league.status != "running":
            db.rollback()
            return []

        round_ = league_repository.get_first_unresolved_round(db, league_id)
        if round_ is None:
            if league_repository.has_fixture_rounds(db, league_id):
                league.status = "finished"
            db.commit()
            return []

        states = league_repository.get_round_match_states(db, round_.id)
        if not states:
            raise AppError("LEAGUE_FIXTURE_INVALID", "La ronda no tiene partidos.")

        running = [match_id for match_id, status in states if status == "RUNNING"]
        if running:
            db.commit()
            return running
        if any(status not in PENDING_STATUSES for _, status in states):
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

        registrations = {
            row.club_id: row for row in league_repository.get_round_registrations(db, league_id, club_ids)
        }
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
        started_ids = [match.match_id for match in current]
        db.commit()
        return started_ids
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
