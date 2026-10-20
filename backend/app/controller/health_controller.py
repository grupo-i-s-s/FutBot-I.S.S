from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import Annotated

from app.database import get_db
from app.migrate import get_migration_files

health_router = APIRouter(tags=["health"])


@health_router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@health_router.get(
    "/health/ready",
    responses={503: {"description": "Base de datos no disponible o migraciones pendientes"}},
)
def readiness(db: Annotated[Session, Depends(get_db)]):
    try:
        db.execute(text("SELECT 1"))
        history_exists = db.execute(
            text("SELECT to_regclass('schema_migrations')")
        ).scalar_one()
        applied = (
            set(db.execute(text("SELECT filename FROM schema_migrations")).scalars())
            if history_exists is not None
            else set()
        )
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "database": "unavailable",
            },
        )

    try:
        expected = {path.name for path in get_migration_files()}
    except (OSError, RuntimeError):
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "database": "ok",
                "migrations": "unavailable",
            },
        )

    pending = sorted(expected - applied)
    if pending:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "database": "ok",
                "migrations": "pending",
                "pending_migrations": pending,
            },
        )

    return {"status": "ok", "database": "ok", "migrations": "ok"}
