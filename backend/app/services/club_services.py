from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models.auth_model import Club
from app.repository import club_repository, player_repository
from app.schemas.club_schemas import ClubUpdate, ClubPublicRead, ClubListResponse, ClubProfileRead


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

def list_clubs( db: Session, *, user_id: int, name: str | None = None, page: int = 1, page_size: int = 20) -> ClubListResponse:
    normalized_name = name.strip() if name is not None else None

    clubs, total = club_repository.get_clubs(
        db,
        exclude_user_id=user_id,
        name=normalized_name,
        page=page,
        page_size=page_size,
    )

    return ClubListResponse(
        items=[
            ClubPublicRead.model_validate(club)
            for club in clubs
        ],
        page=page,
        page_size=page_size,
        total=total,
        has_next=page * page_size < total,
    )

def get_club_profile( db: Session, club_id: int) -> ClubProfileRead:
    data = club_repository.get_club_profile_data(db, club_id)

    if data is None:
        raise AppError(
            "CLUB_NOT_FOUND",
            "El club solicitado no existe.",
        )

    players = sorted(
        player_repository.get_players_by_club(db, club_id),
        key=lambda player: player.id,
    )

    return ClubProfileRead(
        id=data["id"],
        name=data["name"],
        avatar=data["avatar"],
        stats={
            "played": data["played"],
            "wins": data["wins"],
            "draws": data["draws"],
            "losses": data["losses"],
        },
        ranking={
            "position": data["position"],
            "points": data["points"],
        },
        players=players,
    )