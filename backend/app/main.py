from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import app.models.auth_model  # noqa: F401
import app.models.player  # noqa: F401
from app.controllers.player_controller import router as player_router
from app.database import engine, get_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    engine.dispose()


app = FastAPI(
    title="FutBot API",
    description="Base de desarrollo de FutBot.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(player_router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/health/ready",
    tags=["health"],
    responses={503: {"description": "Base de datos no disponible"}},
)
def readiness(db: Annotated[Session, Depends(get_db)]):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "database": "unavailable"},
        )
    return {"status": "ok", "database": "ok"}
