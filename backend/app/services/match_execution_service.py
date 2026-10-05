"""Ejecución explícita. No registra tareas ni programa el inicio de partidos."""
from datetime import datetime, timezone
from time import monotonic, sleep
from threading import Event

from sqlalchemy.orm import Session

from app.errors import AppError
from app.repository import matches_repository
from app.services.match_start_service import prepare_match_start
from primitives.match_simulation import Match

PHYSICS_DT = 1 / 30
STEPS_PER_SNAPSHOT = 3


def _persist(db: Session, row, simulation: Match) -> dict:
    now = datetime.now(timezone.utc)
    snapshot = simulation.snapshot(row.sequence + 1, now.isoformat())
    matches_repository.save_progress(db, row, simulation, snapshot, now)
    db.commit()
    return snapshot


def _execute(db: Session, match_id: int, duration_ms: int | None, stop_event: Event | None = None) -> dict | None:
    row = matches_repository.get_by_id_for_update(db, match_id)

    if row is None:
        raise AppError("MATCH_NOT_FOUND", "El partido no existe.")

    if row.status in ("FINISHED", "CANCELLED"):
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

        now = datetime.now(timezone.utc)
        simulation = prepare_match_start(db, row, now, duration_ms=chosen_duration)

        if simulation is None:
            if row.status == "CANCELLED":
                snapshot = row.snapshot
                db.commit()
                return snapshot

            db.rollback()
            return None

        snapshot = _persist(db, row, simulation)

    deadline = monotonic()

    while not simulation.finished:
        interval = min(STEPS_PER_SNAPSHOT * PHYSICS_DT, simulation.duration_ms / 1000 - simulation.time)
        deadline += interval
        delay = max(0, deadline - monotonic())

        if stop_event is None:
            sleep(delay)
        elif stop_event.wait(delay):
            return snapshot

        for _ in range(STEPS_PER_SNAPSHOT):
            simulation.run_match(PHYSICS_DT)
            if simulation.finished:
                break

        row = matches_repository.get_by_id_for_update(db, match_id)

        if row is None:
            raise AppError("MATCH_NOT_FOUND", "El partido fue eliminado durante la ejecución.")

        snapshot = _persist(db, row, simulation)
        deadline = max(deadline, monotonic())

    return snapshot


def run_persisted_match(match_id: int, *, duration_ms: int | None = None, stop_event: Event | None = None) -> dict | None:
    """Inicia o reanuda explícitamente y devuelve el snapshot final persistido.

    Llamar desde un worker/thread: esta función bloquea hasta finalizar. El
    programador de inicio debe invocarla; ningún controller ni WebSocket lo hace.
    Si falla, otra llamada retoma el último checkpoint confirmado, manteniendo
    titulares, marcador, reloj y secuencia.
    """
    if stop_event is not None and stop_event.is_set():
        return None

    with matches_repository.execution_session(match_id) as db:
        return _execute(db, match_id, duration_ms, stop_event)
