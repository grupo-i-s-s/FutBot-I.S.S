from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.auth_model import Club
from app.models.behaviour_model import Behavior
from app.models.league_model import League
from app.security import hash_password


def migrate_league_passwords(db: Session) -> int:
    try:
        leagues = db.scalars(
            select(League)
            .where(League.access_code.is_not(None))
            .order_by(League.id)
            .with_for_update()
        ).all()
        for league in leagues:
            if not league.password_hash:
                league.password_hash = hash_password(league.access_code)
            league.is_private = True
            league.access_code = None
        db.commit()
        return len(leagues)
    except Exception:
        db.rollback()
        raise


if __name__ == "__main__":
    with SessionLocal() as db:
        count = migrate_league_passwords(db)
    print(f"Ligas migradas: {count}")
