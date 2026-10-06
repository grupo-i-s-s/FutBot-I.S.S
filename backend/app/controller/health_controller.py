from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import Annotated

from app.database import get_db

health_router = APIRouter(tags=["health"])


@health_router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@health_router.get(
    "/health/ready",
    responses={503: {"description": "Base de datos no disponible"}},
)
def readiness(db: Annotated[Session, Depends(get_db)]):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "database": "unavailable",
            },
        )

    return {"status": "ok", "database": "ok"}
