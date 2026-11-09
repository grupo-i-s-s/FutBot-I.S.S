from datetime import datetime, timezone
from sqlalchemy.orm import Session
from threading import Event
from time import monotonic, sleep

from app.errors import AppError
from app.repository import matches_repository
from app.services.match_start_service import prepare_match_start
from app.services.league_fixture_service import update_fixture_schedule
from app.services.substitution_execution_service import apply_planned_substitutions
from app.services.planned_substitution_service import with_pending_substitutions
from primitives.match_simulation import Match
from app.services.match_request_handler import live_request
import logging

from contextlib import ExitStack

from app.services.match_request_handler import acknowledge_requests, clear_requests, pending_requests


logger = logging.getLogger(__name__)
PHYSICS_DT = 1 / 30
STEPS_PER_SNAPSHOT = 3


def _persist(db: Session, row, simulation: Match) -> dict:
    now = datetime.now(timezone.utc)
    snapshot = simulation.snapshot(row.sequence + 1, now.isoformat())
    snapshot = with_pending_substitutions(db, row.match_id, snapshot)
    matches_repository.save_progress(db, row, simulation, snapshot, now)
    if simulation.finished and row.league_round_id is not None:
        update_fixture_schedule(db, row.league_round_id)
    db.commit()
    return snapshot


def _execute(
    db: Session,
    match_id: int,
    duration_ms: int | None,
    stop_event: Event | None = None,
) -> dict | None:

    with ExitStack() as resources:
        row = matches_repository.get_by_id_for_update(db, match_id,)

        if row is None:
            raise AppError(
                "MATCH_NOT_FOUND",
                "El partido no existe.",
            )

        if row.status in ("FINISHED", "CANCELLED"):
            snapshot = row.snapshot
            db.rollback()
            return snapshot

        if row.status == "RUNNING":
            if row.runtime_state is None:
                raise AppError(
                    "MATCH_STATE_INVALID",
                    "Falta el estado para reanudar el partido.",
                )

            try:
                simulation = Match.from_checkpoint(row.runtime_state)

            except (ValueError, TypeError, KeyError) as error:
                raise AppError(
                    "MATCH_STATE_INVALID",
                    "El estado guardado del partido es inválido.",
                ) from error

            resources.callback(simulation.close_runtime)

            if duration_ms is not None and duration_ms != simulation.duration_ms:
                raise AppError(
                    "MATCH_INVALID_DURATION",
                    "No se puede cambiar la duración de un partido iniciado.",
                )

            snapshot = row.snapshot
            db.rollback()

        else:
            chosen_duration = row.duration_ms if duration_ms is None else duration_ms

            if type(chosen_duration) is not int or chosen_duration <= 0:
                raise AppError(
                    "MATCH_INVALID_DURATION",
                    "La duración debe ser un entero positivo en milisegundos.",
                )

            now = datetime.now(timezone.utc)

            simulation = prepare_match_start(db, row, now, duration_ms=chosen_duration)

            if simulation is None:
                if row.status == "CANCELLED":
                    snapshot = row.snapshot
                    db.commit()
                    return snapshot

                db.rollback()
                return None

            resources.callback(simulation.close_runtime)

            snapshot = _persist(db, row, simulation)

        def on_pause():
            current = matches_repository.get_by_id_for_update(db, match_id)
            if current is None or current.status != "RUNNING":
                return False
            return apply_planned_substitutions(db, match_id, simulation)

        simulation.on_pause = on_pause
        if simulation.pause_index:
            if on_pause():
                snapshot = _persist(db, row, simulation)
            else:
                db.rollback()

        deadline = monotonic()

        while not simulation.finished:
            interval = STEPS_PER_SNAPSHOT * PHYSICS_DT

            deadline += interval
            delay = max(0, deadline - monotonic())

            if stop_event is None:
                sleep(delay)

            elif stop_event.wait(delay):
                return snapshot

            batch = pending_requests(match_id)

            for request in batch:
                if request["action"] != "CHANGE_BEHAVIOUR":
                    continue

                try:
                    simulation.change_behaviour(
                        request["player_id"],
                        club_id=request["club_id"],
                        behaviour_id=request["behaviour_id"],
                        **request["program"],
                    )

                except (ValueError, TypeError, KeyError):
                    logger.exception(
                        "Cambio de comportamiento rechazado: partido=%s",
                        match_id,
                    )

            for _ in range(STEPS_PER_SNAPSHOT):
                simulation.run_match(PHYSICS_DT)

                if simulation.finished:
                    break

            row = matches_repository.get_by_id_for_update(db, match_id)

            if row is None:
                raise AppError(
                    "MATCH_NOT_FOUND",
                    "El partido fue eliminado durante la ejecución.",
                )

            if row.status == "CANCELLED":
                snapshot = row.snapshot
                db.rollback()
                clear_requests(match_id)
                return snapshot

            snapshot = _persist(db, row, simulation)

            acknowledge_requests(
                match_id,
                {
                    request["request_id"]
                    for request in batch
                },
            )

            deadline = max(deadline, monotonic())

        clear_requests(match_id)

        return snapshot

def run_persisted_match(match_id: int, *, duration_ms: int | None = None,
                        stop_event: Event | None = None) -> dict | None:
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
