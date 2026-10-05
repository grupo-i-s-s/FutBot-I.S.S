import asyncio
import logging
from datetime import datetime, timezone
from threading import Event

from app.database import SessionLocal
from app.errors import AppError
from app.repository import matches_repository
from app.services.match_execution_service import run_persisted_match


logger = logging.getLogger(__name__)
CHECK_INTERVAL_SECONDS = 1


def _get_due_match_ids() -> list[int]:
    with SessionLocal() as db:
        return matches_repository.get_due_match_ids(db, datetime.now(timezone.utc))


def _run_match(match_id: int, stop_event: Event) -> None:
    try:
        run_persisted_match(match_id, stop_event=stop_event)
    except AppError as exc:
        if exc.code not in ("MATCH_ALREADY_RUNNING", "MATCH_NOT_FOUND"):
            logger.exception("No se pudo ejecutar el partido %s", match_id)
    except Exception:
        logger.exception("Falló la ejecución del partido %s", match_id)


async def run_match_scheduler(stop_event: Event) -> None:
    active_tasks = {}

    try:
        while not stop_event.is_set():
            active_tasks = {
                match_id: task
                for match_id, task in active_tasks.items()
                if not task.done()
            }

            try:
                match_ids = await asyncio.to_thread(_get_due_match_ids)
            except Exception:
                logger.exception("No se pudieron consultar los partidos pendientes")
            else:
                for match_id in match_ids:
                    if stop_event.is_set():
                        break

                    if match_id not in active_tasks:
                        active_tasks[match_id] = asyncio.create_task(
                            asyncio.to_thread(_run_match, match_id, stop_event)
                        )

            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
    finally:
        stop_event.set()
        await asyncio.gather(*active_tasks.values(), return_exceptions=True)