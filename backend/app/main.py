import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from threading import Event

from app.controller import api_router
from app.database import engine
from app.dependencies import require_browser_write
from app.errors import AppError
from app.services.match_scheduler_service import run_match_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    stop_event = Event()
    scheduler_task = asyncio.create_task(run_match_scheduler(stop_event))

    try:
        yield
    finally:
        stop_event.set()
        try:
            await scheduler_task
        finally:
            engine.dispose()


app = FastAPI(
    title="FutBot API",
    description="Base de desarrollo de FutBot.",
    version="0.1.0",
    lifespan=lifespan,
    dependencies=[Depends(require_browser_write)],
)

app.include_router(api_router)

error_status = {
    "ACCOUNT_DUPLICATE": 400,
    "PASSWORD_INVALID": 400,
    "INVALID_CREDENTIALS": 401,
    "SESSION_INVALID": 401,
    "CSRF_INVALID": 403,
    "BEHAVIOUR_NOT_FOUND": 404,
    "PLAYER_NOT_FOUND": 404,
    "ACCOUNT_INCOMPLETE": 409,
    "MATCH_NOT_FOUND": 404,
    "MATCH_FORBIDDEN": 403,
    "MATCH_SELF_JOIN": 409,
    "MATCH_FULL": 409,
    "MATCH_STARTED": 409,
    "MATCH_INVALID_DATE": 400,
    "MATCH_NO_VISITOR": 409,
    "MATCH_INVALID_LINEUP": 409,
    "MATCH_INVALID_BEHAVIOUR": 409,
    "MATCH_ALREADY_RUNNING": 409,
    "MATCH_STATE_INVALID": 409,
    "MATCH_INVALID_DURATION": 400,
}


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=error_status.get(exc.code, 400),
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "fields": exc.fields,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
) -> JSONResponse:
    fields = {}
    for error in exc.errors():
        field = ".".join(
            str(part)
            for part in error["loc"]
            if part not in {"body", "query", "path"}
        ) or "form"
        fields[field] = error["msg"]

    # Do not return input values: the body may contain passwords.
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Revisá los datos ingresados.",
                "fields": fields,
            }
        },
    )
