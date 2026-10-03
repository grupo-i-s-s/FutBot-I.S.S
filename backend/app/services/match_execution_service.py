"""Ejecución explícita. No registra tareas ni programa el inicio de partidos."""
from datetime import datetime, timezone
from time import monotonic, sleep

from sqlalchemy.orm import Session

from app.errors import AppError
from app.repository import matches_repository
from app.services.match_builder_service import build_match
from primitives.match_simulation import Match

PHYSICS_DT = 1 / 30
STEPS_PER_SNAPSHOT = 3


def _persist(db: Session, row, simulation: Match) -> dict:
    now = datetime.now(timezone.utc)
    snapshot = simulation.snapshot(row.sequence + 1, now.isoformat())
    matches_repository.save_progress(db, row, simulation, snapshot, now)
    db.commit()
    return snapshot


def _execute(db: Session, match_id: int, duration_ms: int | None) -> dict:
    row = matches_repository.get_by_id_for_update(db, match_id)
    if row is None:
        raise AppError("MATCH_NOT_FOUND", "El partido no existe.")
    if row.status == "FINISHED":
        # No reconstruir equipos, incrementar secuencia ni volver a finalizar.
        snapshot = row.snapshot
        db.rollback()
        return snapshot
    if row.status == "RUNNING":
        if row.runtime_state is None:
            raise AppError("MATCH_STATE_INVALID", "Falta el estado para reanudar el partido.")
        simulation = Match.from_checkpoint(row.runtime_state)
        if duration_ms is not None and duration_ms != simulation.duration_ms:
            raise AppError("MATCH_INVALID_DURATION", "No se puede cambiar la duración de un partido iniciado.")
        snapshot = row.snapshot
        db.rollback()
    else:
        chosen_duration = row.duration_ms if duration_ms is None else duration_ms
        if type(chosen_duration) is not int or chosen_duration <= 0:
            raise AppError("MATCH_INVALID_DURATION", "La duración debe ser un entero positivo en milisegundos.")
        simulation = build_match(db, match_id, duration_ms=chosen_duration)
        snapshot = _persist(db, row, simulation)

    deadline = monotonic()
    while not simulation.finished:
        interval = min(STEPS_PER_SNAPSHOT * PHYSICS_DT, simulation.duration_ms / 1000 - simulation.time)
        deadline += interval
        sleep(max(0, deadline - monotonic()))
        for _ in range(STEPS_PER_SNAPSHOT):
            simulation.run_match(PHYSICS_DT)
            if simulation.finished:
                break
        row = matches_repository.get_by_id_for_update(db, match_id)
        if row is None:
            raise AppError("MATCH_NOT_FOUND", "El partido fue eliminado durante la ejecución.")
        snapshot = _persist(db, row, simulation)
        # Si la base tarda más que el intervalo, el reloj simulado se ralentiza.
        # No procesar una ráfaga de pasos para compensar una interrupción.
        deadline = max(deadline, monotonic())
    return snapshot


def run_persisted_match(match_id: int, *, duration_ms: int | None = None) -> dict:
    """Inicia o reanuda explícitamente y devuelve el snapshot final persistido.

    Llamar desde un worker/thread: esta función bloquea hasta finalizar. El
    programador de inicio debe invocarla; ningún controller ni WebSocket lo hace.
    Si falla, otra llamada retoma el último checkpoint confirmado, manteniendo
    titulares, marcador, reloj y secuencia.
    """
    with matches_repository.execution_session(match_id) as db:
        return _execute(db, match_id, duration_ms)
