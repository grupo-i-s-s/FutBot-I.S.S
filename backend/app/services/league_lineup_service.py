from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.repository import behaviour_repository, player_repository, team_repository
from app.schemas.team_schemas import Lineup
from primitives.behaviour_api.runtime import resolve_program
from primitives.formations import FORMATIONS


def prepare_registration_lineup(db: Session, registration, creator_id: int) -> None:
    saved = registration.line_up
    # Las inscripciones antiguas sólo identifican jugadores, sin indicar sus puestos.
    if isinstance(saved, list):
        team = team_repository.get_by_club(db, registration.club_id)
        raw = team.line_up if team else None
    else:
        raw = saved

    try:
        lineup = Lineup.model_validate(raw)
    except ValidationError as exc:
        raise HTTPException(409, "Hay una alineación incompleta o inválida.") from exc

    if lineup.formation_id not in FORMATIONS:
        raise HTTPException(409, "La formación guardada ya no está disponible.")
    selections = lineup.starters + lineup.substitutes
    if isinstance(saved, list) and not (saved == [] and registration.club_id == creator_id):
        ids = sorted(slot.player_id for slot in selections)
        if any(type(id_) is not int for id_ in saved) or sorted(saved) != ids:
            raise HTTPException(409, "Los jugadores inscriptos no coinciden con el equipo guardado.")

    active_ids = {p.id for p in player_repository.get_players_by_club(db, registration.club_id)}
    behaviours = {
        b.id: b for b in behaviour_repository.get_all_behaviours(db, registration.club_id)
        if b.kind == "PLAYER" and b.validation_status == "VALID"
    }
    for slot in selections:
        if slot.player_id not in active_ids:
            raise HTTPException(409, "Una alineación contiene jugadores no disponibles en su club.")
        behaviour = behaviours.get(slot.behaviour_id)
        if behaviour is None:
            raise HTTPException(409, "Un comportamiento de la alineación ya no está disponible.")
        try:
            resolve_program(behaviour.code, behaviour.name, version=behaviour.version)
        except ValueError as exc:
            raise HTTPException(409, "Un comportamiento es incompatible con el motor del partido.") from exc

    if isinstance(saved, list):
        registration.line_up = lineup.model_dump(by_alias=True)
