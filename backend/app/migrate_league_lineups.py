from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.league_model import LeagueRegistration
from app.repository import league_repository, matches_repository
from app.services.league_lineup_service import INCOMPLETE_LEGACY_LINEUP, prepare_registration_lineup


def migrate_league_lineups(db: Session) -> tuple[int, int]:
    json_type = func.json_typeof if db.get_bind().dialect.name == "postgresql" else func.json_type
    migrated = incomplete = 0
    try:
        league_ids = db.scalars(
            select(LeagueRegistration.league_id)
            .where(json_type(LeagueRegistration.line_up) == "array")
            .distinct()
            .order_by(LeagueRegistration.league_id)
        ).all()
        for league_id in league_ids:
            # El mismo orden que la inscripción y el scheduler. Confirmar cada liga
            # libera sus bloqueos y permite retomar si se interrumpe el arranque.
            league = league_repository.get_league_by_id(db, league_id)
            if league is None:
                db.rollback()
                continue
            legacy = [row for row in league.registrations if isinstance(row.line_up, list)]
            if legacy:
                matches_repository.get_clubs_for_update(db, tuple(sorted(row.club_id for row in legacy)))
            for registration in legacy:
                try:
                    prepare_registration_lineup(db, registration, league.creator_club_id)
                except HTTPException:
                    if league.status == "open":
                        registration.line_up = {
                            "status": INCOMPLETE_LEGACY_LINEUP,
                            "legacyPlayerIds": registration.line_up,
                        }
                        incomplete += 1
                else:
                    migrated += 1
            db.commit()
        return migrated, incomplete
    except Exception:
        db.rollback()
        raise


if __name__ == "__main__":
    with SessionLocal() as db:
        migrated, incomplete = migrate_league_lineups(db)
    print(f"Alineaciones migradas: {migrated}. Inscripciones incompletas: {incomplete}.")
