from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.errors import AppError
from app.repository import (
    behaviour_repository,
    matches_repository,
    player_repository,
    team_repository,
)
from app.schemas.team_schemas import Lineup
from primitives.behaviours import resolve_behaviour
from primitives.formations import FORMATIONS
from primitives.match_simulation import Match, PlayerProfile, Team


def _build_team(db: Session, club_id: int, name: str) -> Team:
    saved_team = team_repository.get_by_club(db, club_id)

    if saved_team is None:
        raise AppError(
            "MATCH_INVALID_LINEUP",
            "El club necesita configurar su equipo antes del partido.",
        )

    try:
        lineup = Lineup.model_validate(saved_team.line_up)
    except ValidationError as exc:
        raise AppError(
            "MATCH_INVALID_LINEUP",
            "El equipo guardado del club no es válido.",
        ) from exc

    if lineup.formation_id not in FORMATIONS:
        raise AppError(
            "MATCH_INVALID_LINEUP",
            "La formación guardada del club no está disponible.",
        )

    # Ambos repositorios filtran los registros eliminados y el club.
    players = {
        player.id: player
        for player in player_repository.get_players_by_club(db, club_id)
    }
    behaviours = {
        behaviour.id: behaviour
        for behaviour in behaviour_repository.get_all_behaviours(db, club_id)
    }

    profiles = []

    # Este orden asigna cada titular a su puesto de la formación.
    for selection in lineup.starters:
        player = players.get(selection.player_id)
        behaviour = behaviours.get(selection.behaviour_id)

        if player is None or behaviour is None:
            raise AppError(
                "MATCH_INVALID_LINEUP",
                "Hay titulares o comportamientos que ya no están disponibles.",
            )

        try:
            mode = resolve_behaviour(behaviour.code, behaviour.name)
        except ValueError as exc:
            raise AppError(
                "MATCH_INVALID_BEHAVIOUR",
                f"El jugador {player.name} tiene un comportamiento incompatible.",
            ) from exc

        profiles.append(
            PlayerProfile(
                id=player.id,
                club_id=player.club_id,
                name=player.name,
                speed=player.speed,
                power=player.power,
                behaviour_id=behaviour.id,
                behaviour_mode=mode,
            )
        )

    return Team(
        club_id=club_id,
        name=name,
        players=tuple(profiles),
        formation_id=lineup.formation_id,
    )


def build_match(
    db: Session,
    match_id: int,
    *,
    duration_ms: int | None = None,
) -> Match:
    match = matches_repository.get_by_id(db, match_id)

    if match is None:
        raise AppError("MATCH_NOT_FOUND", "El partido no existe.")

    if match.visitor_id is None:
        raise AppError(
            "MATCH_NO_VISITOR",
            "El partido todavía no tiene visitante.",
        )

    names = matches_repository.get_club_names(
        db,
        (match.creator_id, match.visitor_id),
    )

    return Match(
        _build_team(db, match.creator_id, names[match.creator_id]),
        _build_team(db, match.visitor_id, names[match.visitor_id]),
        match_id=match_id,
        duration_ms=(
            match.duration_ms
            if duration_ms is None
            else duration_ms
        ),
    )
