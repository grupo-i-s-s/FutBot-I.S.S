from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from unittest.mock import Mock

from app import migrate
from app.controller.health_controller import health_router
from app.database import engine, get_db
from app.main import app


def test_liveness_does_not_need_database():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_checks_real_database():
    with TestClient(app) as client:
        response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "migrations": "ok"}


def test_readiness_reports_database_failure_without_leaking_details():
    session = Mock()
    session.execute.side_effect = OperationalError("SELECT 1", {}, Exception("secret"))
    app.dependency_overrides[get_db] = lambda: session
    try:
        with TestClient(app) as client:
            response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable", "database": "unavailable"}
        assert "secret" not in response.text
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def isolated_readiness():
    """Prueba el endpoint en un esquema temporal, sin modificar el historial real."""
    test_app = FastAPI()
    test_app.include_router(health_router)
    schema = "health_check_" + uuid4().hex

    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            with Session(bind=connection) as session:
                test_app.dependency_overrides[get_db] = lambda: session
                with TestClient(test_app) as client:
                    yield client, session
        finally:
            transaction.rollback()


def record_migrations(session, filenames):
    session.execute(text("CREATE TABLE schema_migrations (filename TEXT PRIMARY KEY)"))
    for filename in filenames:
        session.execute(
            text("INSERT INTO schema_migrations (filename) VALUES (:filename)"),
            {"filename": filename},
        )


def test_readiness_accepts_all_applied_migrations(isolated_readiness):
    client, session = isolated_readiness
    record_migrations(session, [path.name for path in migrate.get_migration_files()])

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "migrations": "ok"}


def test_readiness_detects_new_migration_after_success(isolated_readiness, monkeypatch, tmp_path):
    client, session = isolated_readiness
    filenames = [path.name for path in migrate.get_migration_files()]
    record_migrations(session, filenames)
    for filename in filenames:
        (tmp_path / filename).write_text("BEGIN; SELECT 1; COMMIT;", encoding="utf-8")
    monkeypatch.setattr(migrate, "MIGRATIONS_DIR", tmp_path)
    assert client.get("/health/ready").status_code == 200

    (tmp_path / "010_new.sql").write_text("BEGIN; SELECT 1; COMMIT;", encoding="utf-8")
    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "database": "ok",
        "migrations": "pending",
        "pending_migrations": ["010_new.sql"],
    }
    session.execute(
        text("INSERT INTO schema_migrations (filename) VALUES ('010_new.sql')")
    )
    assert client.get("/health/ready").status_code == 200


@pytest.mark.parametrize("empty_history", [False, True])
def test_readiness_requires_migration_history(isolated_readiness, empty_history):
    client, session = isolated_readiness
    if empty_history:
        record_migrations(session, [])

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "database": "ok",
        "migrations": "pending",
        "pending_migrations": [path.name for path in migrate.get_migration_files()],
    }


def test_readiness_rejects_missing_migration_files(isolated_readiness, monkeypatch, tmp_path):
    client, session = isolated_readiness
    record_migrations(session, [path.name for path in migrate.get_migration_files()])
    monkeypatch.setattr(migrate, "MIGRATIONS_DIR", tmp_path)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "database": "ok",
        "migrations": "unavailable",
    }
