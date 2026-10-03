"""Integra autenticación, Pymunk, persistencia y dos observadores reales WS."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models.auth_model import AuthSession, Club, User
from app.models.behaviour_model import Behavior
from app.models.matches_model import Matches
from app.models.player_model import Player
from app.repository import matches_repository
from app.security import hash_session_token, new_session_token
from app.services.match_execution_service import run_persisted_match
from app.controller import match_stream_controller
from primitives.behaviours import DEFAULT_CODES


def seed_match_database(engine, duration_ms=700):
    tables = [User.__table__, Club.__table__, AuthSession.__table__, Behavior.__table__, Player.__table__, Matches.__table__]
    Base.metadata.create_all(engine, tables=tables)
    tokens = [new_session_token(), new_session_token()]
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        for club_id, token, name in zip((1, 2), tokens, ('Los Pinos', 'El Ceibo'), strict=True):
            db.add(User(id=club_id, email=f'club{club_id}@test.example', password_hash='unused'))
            db.add(Club(id=club_id, user_id=club_id, name=name, avatar='avatar'))
            db.add(AuthSession(user_id=club_id, token_hash=hash_session_token(token), created_at=now, expires_at=now + timedelta(hours=1)))
            db.add(Behavior(id=club_id, club_id=club_id, name='Equilibrado', description='test', code=DEFAULT_CODES['Equilibrado']))
            for index in range(3):
                db.add(Player(id=club_id * 10 + index, club_id=club_id, behavior_id=club_id,
                              name=f'Jugador {club_id}-{index + 1}', power=60, agility=60,
                              control=60, speed=60, strength=60))
        db.add(Matches(match_id=42, creator_id=1, visitor_id=2, init_date=now, duration_ms=duration_ms))
        db.commit()
    return tokens


def test_live_stream_continues_after_one_observer_disconnects(tmp_path, monkeypatch):
    engine = create_engine(f'sqlite:///{tmp_path / "match.db"}', connect_args={'check_same_thread': False})
    tokens = seed_match_database(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)

    def database():
        with sessions() as db:
            yield db

    @contextmanager
    def execution_session(match_id):
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = database
    monkeypatch.setattr(match_stream_controller, 'SessionLocal', sessions)
    # El bloqueo PostgreSQL se prueba por separado; aquí usamos SQLite en disco
    # con conexiones independientes para lectores y el escritor.
    monkeypatch.setattr(matches_repository, 'execution_session', execution_session)
    try:
        with TestClient(app) as client, ThreadPoolExecutor(max_workers=1) as workers:
            client.cookies.set(settings.cookie_name, tokens[0])
            with client.websocket_connect('/matches/42/stream', headers={'Origin': next(iter(settings.allowed_origins))}) as local:
                client.cookies.set(settings.cookie_name, tokens[1])
                with client.websocket_connect('/matches/42/stream', headers={'Origin': next(iter(settings.allowed_origins))}) as visitor:
                    assert local.receive_json()['state']['status'] == 'WAITING'
                    assert visitor.receive_json()['state']['status'] == 'WAITING'
                    # Inicio explícito del test: nunca lo provoca una conexión.
                    execution = workers.submit(run_persisted_match, 42)
                    first = local.receive_json()
                    assert first['state']['status'] == 'RUNNING'
                    assert [player['id'] for player in first['state']['players']] == [10, 11, 12, 20, 21, 22]
                    local.close()
                    final = execution.result(timeout=5)
                    received = []
                    while True:
                        message = visitor.receive_json()
                        received.append(message['sequence'])
                        if message['state']['status'] == 'FINISHED':
                            break
                    assert received == sorted(set(received))
                    assert message == final
                    assert visitor.receive()['code'] == 1000
            assert client.get('/matches/42').json() == final
            client.cookies.set(settings.cookie_name, new_session_token())
            assert client.get('/matches/42').status_code == 401
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
