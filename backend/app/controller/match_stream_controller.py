import asyncio
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect 
from starlette.concurrency import run_in_threadpool 

from app.config import settings
from app.database import SessionLocal
from app.errors import AppError
from app.services import match_stream_services

match_stream_router = APIRouter(prefix="/matches", tags=["matches"])
SESSION_CHECK_SECONDS = 15

def authorize_with_db(token: str|None, match_id:int) -> match_stream_services.StreamAccess:
    with SessionLocal() as db:
        return match_stream_services.authorize(db, token, match_id)

def session_active_with_db(session_hash:str) -> bool:
    with SessionLocal() as db:
        return match_stream_services.session_is_active(db, session_hash)     

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
            "MATCH_ACCOUNT_INCOMPLETE": 403,
            "MATCH_NOT_FOUND": 404
            }.get(exc.code, 403)
        raise HTTPException(status_code=status_code, detail=exc.message) from exc
    await websocket.accept()
    try: 
        while True:
            try:
                await asyncio.wait_for(websocket.recieve_text(), timeout=SESSION_CHECK_SECONDS)
            except TimeoutError:
                active = await run_in_threadpool(session_active_with_db, access.session_hash)
                if not active:
                    await websocket.close(code=1008, reason="Sesión vencida o revocada")
                    return
            except WebSocketDisconnect: 
                return
            else: 
                await websocket.close(code=1008, reason="Canal de solo lectura")
                return
    finally: 
        pass
    

            