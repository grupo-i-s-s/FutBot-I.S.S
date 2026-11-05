import asyncio
from contextlib import suppress
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.database import SessionLocal
from app.dependencies import CurrentClub, Database
from app.errors import AppError
from app.services import match_stream_services, behaviour_service
from app.services.match_snapshot_service import read_snapshot
from app.schemas.matches_schemas import LiveRequests
from app.repository import matches_repository
from app.services.match_request_handler import enqueue_request
from primitives.behaviour_api.runtime import resolve_program

match_stream_router = APIRouter(prefix="/matches", tags=["matches"])
SESSION_CHECK_SECONDS = 15


@match_stream_router.get("/{match_id}")
def get_match_snapshot(match_id: int, db: Database, club: CurrentClub):
    return read_snapshot(db, match_id, club.id)


def authorize_with_db(token: str | None, match_id: int) -> match_stream_services.StreamAccess:
    with SessionLocal() as db:
        return match_stream_services.authorize(db, token, match_id)


def session_active_with_db(session_hash: str) -> bool:
    with SessionLocal() as db:
        return match_stream_services.session_is_active(db, session_hash)


def snapshot_with_db(match_id: int, club_id: int) -> dict:
    with SessionLocal() as db:
        return read_snapshot(db, match_id, club_id)


@match_stream_router.websocket("/{match_id}/stream")
async def stream_match(websocket: WebSocket, match_id: int) -> None:
    origin = websocket.headers.get("origin")
    if origin not in settings.allowed_origins:
        raise HTTPException(status_code=403, detail="Origen no permitido.")
    token = websocket.cookies.get(settings.cookie_name)
    try:
        access = await run_in_threadpool(authorize_with_db, token, match_id)
    except AppError as exc:
        status_code = {
            "SESSION_INVALID": 401,
            "MATCH_FORBIDDEN": 403,
            "ACCOUNT_INCOMPLETE": 409,
            "MATCH_NOT_FOUND": 404
        }.get(exc.code, 403)
        raise HTTPException(status_code=status_code, detail=exc.message) from exc
    await websocket.accept()
    incoming = asyncio.create_task(websocket.receive())
    next_session_check = asyncio.get_running_loop().time() + SESSION_CHECK_SECONDS
    last_sequence = None
    try:
        while True:
            if asyncio.get_running_loop().time() >= next_session_check:
                active = await run_in_threadpool(session_active_with_db, access.session_hash)
                if not active:
                    await websocket.close(code=1008, reason="Sesión vencida o revocada")
                    return
                next_session_check = asyncio.get_running_loop().time() + SESSION_CHECK_SECONDS
            snapshot = await run_in_threadpool(snapshot_with_db, match_id, access.club_id)
            if snapshot["sequence"] != last_sequence:
                await websocket.send_json(snapshot)
                last_sequence = snapshot["sequence"]
            if snapshot["state"]["status"] in ("FINISHED", "CANCELLED"):
                await websocket.close(code=1000, reason="Partido finalizado o cancelado")
                return
            done, _ = await asyncio.wait({incoming}, timeout=0.1)
            if done:
                if incoming.result()["type"] == "websocket.disconnect":
                    return
                await websocket.close(code=1008, reason="Canal de solo lectura")
                return
    except WebSocketDisconnect:
        return
    except AppError as exc:
        await websocket.close(code=1008, reason=exc.message)
    finally:
        incoming.cancel()
        with suppress(asyncio.CancelledError, WebSocketDisconnect):
            await incoming

@match_stream_router.post("/{match_id}/live_request")
def update_behaviour(
    match_id: int,
    data: LiveRequests,
    db: Database,
    club: CurrentClub,
):
    match = matches_repository.get_by_id(
        db,
        match_id,
    )

    if match is None:
        raise AppError(
            "MATCH_NOT_FOUND",
            "El partido no existe.",
        )

    if club.id not in (
        match.creator_id,
        match.visitor_id,
    ):
        raise AppError(
            "MATCH_FORBIDDEN",
            "El club no participa del partido.",
        )

    if match.status != "RUNNING" or not match.runtime_state:
        raise AppError(
            "MATCH_STATE_INVALID",
            "El partido no admite cambios en este momento.",
        )

    own_team = next(
        (
            match.runtime_state[key]
            for key in ("local_team", "visitor_team")
            if match.runtime_state.get(key, {}).get("club_id")
            == club.id
        ),
        None,
    )

    if own_team is None or not any(
        player["id"] == data.player_id
        for player in own_team.get("players", [])
    ):
        raise AppError(
            "MATCH_FORBIDDEN",
            "El jugador no es titular de tu equipo.",
        )

    behaviour = behaviour_service.behaviour_id(
        db,
        club.id,
        data.behaviour_id,
    )

    if (
        behaviour.kind != "PLAYER"
        or behaviour.validation_status != "VALID"
    ):
        raise AppError(
            "BEHAVIOUR_INVALID",
            "El comportamiento no está habilitado.",
        )

    try:
        program = resolve_program(
            behaviour.code,
            behaviour.name,
            version=behaviour.version,
        )

    except ValueError as error:
        raise AppError(
            "BEHAVIOUR_INVALID",
            str(error),
        ) from error

    request_id = enqueue_request(
        match_id,
        {
            "action": "CHANGE_BEHAVIOUR",
            "player_id": data.player_id,
            "club_id": club.id,
            "behaviour_id": behaviour.id,
            "program": program,
        },
    )

    return {
        "queued": True,
        "requestId": request_id,
    }