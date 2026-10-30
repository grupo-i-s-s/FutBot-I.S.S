from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models.auth_model import Club
from app.repository import club_repository
from app.schemas.club_schemas import ClubUpdate


def update_club(
        db: Session,
        club: Club,
        data: ClubUpdate,
) -> Club:
    try:
        updated = club_repository.update_club(
            db,
            club,
            **data.model_dump(),
        )
        db.commit()

    except IntegrityError as exc:
        db.rollback()

        constraint = getattr(
            getattr(exc.orig, "diag", None),
            "constraint_name",
            None,
        )

        if constraint == "clubs_name_key":
            message = "Ya existe un club con ese nombre."
            raise AppError(
                "CLUB_NAME_DUPLICATE",
                message,
                {"name": message},
            ) from exc

        raise

    except Exception:
        db.rollback()
        raise

    return updated


def list_joined_leagues(db: Session, club_id: int) -> dict:
    leagues = club_repository.get_joined_leagues(db, club_id)

    return {
        "items": [
            {
                "id": league.id,
                "name": league.name,
                "type": "PRIVATE" if league.is_private else "PUBLIC",
                "status": league.status,
                "teams": len(league.registrations),
                "max_teams": league.max_teams,
            }
            for league in leagues
        ]
    }
