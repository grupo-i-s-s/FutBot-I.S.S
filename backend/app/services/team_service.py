from sqlalchemy.orm import Session

from app.errors import AppError
from app.repository import (behaviour_repository, player_repository, team_repository)
from app.schemas.team_schemas import DefaultTeamRead, Lineup


FORMATIONS = {1: "Formación 1"}


def get_formations() -> dict:
    return {
        "items": [
            {"id": formation_id, "name": name}
            for formation_id, name in FORMATIONS.items()
        ]
    }


def get_default_team(db: Session, club_id: int) -> DefaultTeamRead:
    team = team_repository.get_by_club(db, club_id)

    if team is None:
        raise AppError(
            "ACCOUNT_INCOMPLETE",
            "El club todavía no tiene su equipo default guardado.",
        )

    return DefaultTeamRead.model_validate(team)


def update_default_team(db: Session, club_id: int, data: Lineup) -> DefaultTeamRead:
    try:
        if data.formation_id not in FORMATIONS:
            raise AppError(
                "VALIDATION_ERROR",
                "La formación seleccionada no existe.",
                {"formationId": "Seleccioná una formación disponible."},
            )

        players = player_repository.get_players_by_club(db, club_id)
        behaviours = behaviour_repository.get_all_behaviours(db, club_id)

        player_ids = {player.id for player in players}
        behaviour_ids = {behaviour.id for behaviour in behaviours}

        for group_name, group in (
            ("starters", data.starters),
            ("substitutes", data.substitutes),
        ):
            for index, selection in enumerate(group):
                if selection.player_id not in player_ids:
                    raise AppError(
                        "VALIDATION_ERROR",
                        "Hay un jugador que no está disponible en tu club.",
                        {
                            f"{group_name}.{index}.playerId":
                            "Seleccioná un jugador disponible de tu club."
                        },
                    )

                if selection.behaviour_id not in behaviour_ids:
                    raise AppError(
                        "VALIDATION_ERROR",
                        "Hay un comportamiento que no está disponible en tu club.",
                        {
                            f"{group_name}.{index}.behaviourId":
                            "Seleccioná un comportamiento disponible de tu club."
                        },
                    )

        team = team_repository.save(
            db,
            club_id,
            data.model_dump(by_alias=True),
        )

        result = DefaultTeamRead.model_validate(team)
        db.commit()
        return result

    except Exception:
        db.rollback()
        raise