"""Nuestro protocolo de streaming, usando un socket y servicios simulados."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from starlette.websockets import WebSocketDisconnect

from app.controller import match_stream_controller as controller
from app.errors import AppError
from app.services.match_stream_services import StreamAccess


@pytest.fixture
def stream(monkeypatch):
    monkeypatch.setattr(controller, "settings", SimpleNamespace(
        allowed_origins={"https://futbot.example"}, cookie_name="futbot_session"))
    socket = SimpleNamespace(
        headers={"origin": "https://futbot.example"}, cookies={"futbot_session": "raw-token"},
        accept=AsyncMock(), send_json=AsyncMock(), close=AsyncMock(), receive=AsyncMock(),
    )

    async def receive():
        await asyncio.Future()

    socket.receive.side_effect = receive
    auth = Mock(return_value=StreamAccess("hashed-token", 7))
    snapshot = Mock(return_value={"sequence": 5, "state": {"status": "FINISHED"}})
    active = Mock(return_value=True)
    monkeypatch.setattr(controller, "authorize_with_db", auth)
    monkeypatch.setattr(controller, "snapshot_with_db", snapshot)
    monkeypatch.setattr(controller, "session_active_with_db", active)

    async def inline(fn, *args):
        return fn(*args)

    monkeypatch.setattr(controller, "run_in_threadpool", inline)
    return SimpleNamespace(socket=socket, auth=auth, snapshot=snapshot, active=active)


def run(stream):
    return asyncio.run(controller.stream_match(stream.socket, 42))


@pytest.mark.parametrize("origin", [None, "https://evil.example"])
def test_stream_rejects_origin_before_authentication(stream, origin):
    stream.socket.headers = {"origin": origin}
    with pytest.raises(HTTPException) as error:
        run(stream)
    assert error.value.status_code == 403
    stream.auth.assert_not_called()
    stream.socket.accept.assert_not_awaited()


@pytest.mark.parametrize("code, status", [("SESSION_INVALID", 401), ("MATCH_FORBIDDEN", 403),
                                         ("ACCOUNT_INCOMPLETE", 409), ("MATCH_NOT_FOUND", 404), ("UNKNOWN", 403)])
def test_stream_translates_authorization_errors_before_accepting(stream, code, status):
    stream.auth.side_effect = AppError(code, "denied")
    with pytest.raises(HTTPException) as error:
        run(stream)
    assert error.value.status_code == status
    stream.socket.accept.assert_not_awaited()
    stream.snapshot.assert_not_called()


@pytest.mark.parametrize("status", ["FINISHED", "CANCELLED"])
def test_terminal_snapshot_is_sent_before_normal_close(stream, status):
    stream.snapshot.return_value = {"sequence": 5, "state": {"status": status}}
    run(stream)
    stream.auth.assert_called_once_with("raw-token", 42)
    stream.snapshot.assert_called_once_with(42, 7)
    stream.socket.accept.assert_awaited_once()
    stream.socket.send_json.assert_awaited_once_with(stream.snapshot.return_value)
    stream.socket.close.assert_awaited_once_with(code=1000, reason="Partido finalizado o cancelado")


def test_unchanged_sequence_is_not_sent_twice(stream, monkeypatch):
    waiting = {"sequence": 5, "state": {"status": "WAITING"}}
    final = {"sequence": 6, "state": {"status": "FINISHED"}}
    stream.snapshot.side_effect = [waiting, waiting, final]

    async def nothing_received(*args, **kwargs):
        return set(), set()

    monkeypatch.setattr(controller.asyncio, "wait", nothing_received)
    run(stream)
    assert [call.args[0] for call in stream.socket.send_json.await_args_list] == [waiting, final]
    assert stream.snapshot.call_count == 3


@pytest.mark.parametrize("message, closes", [("websocket.disconnect", False), ("websocket.receive", True)])
def test_incoming_disconnect_ends_stream_and_client_writes_are_rejected(stream, monkeypatch, message, closes):
    stream.snapshot.return_value = {"sequence": 5, "state": {"status": "WAITING"}}
    stream.socket.receive.side_effect = None
    stream.socket.receive.return_value = {"type": message}
    real_sleep = asyncio.sleep

    async def received(tasks, **kwargs):
        await real_sleep(0)
        return tasks, set()

    monkeypatch.setattr(controller.asyncio, "wait", received)
    run(stream)
    if closes:
        stream.socket.close.assert_awaited_once_with(code=1008, reason="Canal de solo lectura")
    else:
        stream.socket.close.assert_not_awaited()
    stream.snapshot.assert_called_once()


def test_revoked_session_closes_before_reading_new_snapshot(stream, monkeypatch):
    monkeypatch.setattr(controller, "SESSION_CHECK_SECONDS", -1)
    stream.active.return_value = False
    run(stream)
    stream.active.assert_called_once_with("hashed-token")
    stream.snapshot.assert_not_called()
    stream.socket.close.assert_awaited_once_with(code=1008, reason="Sesión vencida o revocada")


def test_active_session_can_continue_to_final_snapshot(stream, monkeypatch):
    monkeypatch.setattr(controller, "SESSION_CHECK_SECONDS", -1)
    run(stream)
    stream.active.assert_called_once_with("hashed-token")
    stream.socket.send_json.assert_awaited_once()


def test_snapshot_domain_failure_closes_with_readable_reason(stream):
    stream.snapshot.side_effect = AppError("MATCH_NOT_FOUND", "El partido ya no existe.")
    run(stream)
    stream.socket.close.assert_awaited_once_with(code=1008, reason="El partido ya no existe.")
    stream.socket.send_json.assert_not_awaited()


def test_disconnected_socket_does_not_leak_exception_or_close_again(stream):
    stream.socket.send_json.side_effect = WebSocketDisconnect()
    run(stream)
    stream.socket.close.assert_not_awaited()
