"""La suite unitaria no requiere PostgreSQL ni permite abrir conexiones reales."""
import os
import pytest
from datetime import datetime, timezone
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from types import SimpleNamespace
from unittest.mock import Mock

# database.py construye su URL al importar; estos valores no abren una conexión.
for name, value in {
    "POSTGRES_USER": "unit_test",
    "POSTGRES_PASSWORD": "unit_test",
    "POSTGRES_DB": "unit_test",
    "POSTGRES_HOST": "unused.invalid",
}.items():
    os.environ.setdefault(name, value)


@pytest.fixture(autouse=True)
def forbid_database_connections(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Un test unitario intentó conectarse a una base real.")

    monkeypatch.setattr(Engine, "connect", forbidden)
    monkeypatch.setattr(Engine, "raw_connection", forbidden)


@pytest.fixture
def db():
    return Mock(spec=Session)


@pytest.fixture
def now():
    return datetime(2030, 1, 1, 12, tzinfo=timezone.utc)


@pytest.fixture
def freeze_time(monkeypatch, now):
    def freeze(module):
        clock = Mock(wraps=datetime)
        clock.now.return_value = now
        monkeypatch.setattr(module, "datetime", clock)
        return clock

    return freeze


@pytest.fixture
def integrity_error():
    from sqlalchemy.exc import IntegrityError

    def make(constraint):
        original = Exception("simulated write failure")
        original.diag = SimpleNamespace(constraint_name=constraint)
        return IntegrityError("unused", {}, original)

    return make
