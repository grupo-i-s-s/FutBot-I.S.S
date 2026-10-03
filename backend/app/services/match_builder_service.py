from sqlalchemy.orm import Session

from app.errors import AppError
from app.repository import matches_repository
from primitives.match_simulation import Match, PlayerProfile, Team


def build_match(db: Session, match_id: int) -> Match:
    match = matches_repository.get_by_id(db, match_id)

    if match is None:
        raise AppError("MATCH_NOT_FOUND", "El partido no existe.")

    if match.visitor_id is None:
        raise AppError("MATCH_NO_VISITOR", "El partido todavía no tiene visitante.")

    local_rows = matches_repository.get_starting_players(
        db, match.creator_id
    )
    visitor_rows = matches_repository.get_starting_players(
        db, match.visitor_id
    )

    if len(local_rows) != 3 or len(visitor_rows) != 3:
        raise AppError(
            "MATCH_INVALID_LINEUP",
            "Cada club necesita tres jugadores activos con comportamiento.",
        )

    names = matches_repository.get_club_names(
        db, (match.creator_id, match.visitor_id)
    )

    def profile(player) -> PlayerProfile:
        return PlayerProfile(
            id=player.id,
            club_id=player.club_id,
            name=player.name,
            speed=player.speed,
            power=player.power,
        )

    return Match(
        Team(
            club_id=match.creator_id,
            name=names[match.creator_id],
            players=tuple(profile(player) for player in local_rows),
        ),
        Team(
            club_id=match.visitor_id,
            name=names[match.visitor_id],
            players=tuple(profile(player) for player in visitor_rows),
        ),
    )
