"""Scheduler sin threads, esperas reales ni consultas a PostgreSQL."""
import asyncio
from contextlib import contextmanager
from threading import Event
from unittest.mock import Mock

import pytest

from app.errors import AppError
from app.services import match_scheduler_service as service


@pytest.mark.parametrize("code, logged", [("MATCH_ALREADY_RUNNING", False), ("MATCH_NOT_FOUND", False),
                                        ("MATCH_INVALID_LINEUP", True), (None, True)])
def test_worker_logs_only_unexpected_failures(monkeypatch, code, logged):
    failure = AppError(code, "failure") if code else RuntimeError("failure")
    run = Mock(side_effect=failure)
    logger = Mock()
    monkeypatch.setattr(service, "run_persisted_match", run)
    monkeypatch.setattr(service, "logger", logger)
    stop = Event()
    service._run_match(42, stop)
    run.assert_called_once_with(42, stop_event=stop)
    assert logger.exception.call_count == int(logged)


def test_due_query_closes_session_and_uses_utc_time(db, monkeypatch, now, freeze_time):
    freeze_time(service)
    closed = []

    @contextmanager
    def session():
        try:
            yield db
        finally:
            closed.append(True)

    repo = Mock(return_value=[42, 43])
    monkeypatch.setattr(service, "SessionLocal", session)
    monkeypatch.setattr(service.matches_repository, "get_due_match_ids", repo)
    assert service._get_due_match_ids() == [42, 43]
    repo.assert_called_once_with(db, now)
    assert closed == [True]


def test_scheduler_deduplicates_active_matches_and_waits_for_workers_on_stop(monkeypatch):
    async def scenario():
        stop = Event()
        release = asyncio.Event()
        started, ended = [], []
        polls = 0
        sleeps = 0
        real_sleep = asyncio.sleep

        async def to_thread(fn, *args):
            nonlocal polls
            if fn is service._get_due_match_ids:
                polls += 1
                return [42, 42, 43]
            assert fn is service._run_match
            match_id, worker_stop = args
            assert worker_stop is stop
            started.append(match_id)
            await release.wait()
            ended.append(match_id)

        async def pause(seconds):
            nonlocal sleeps
            assert seconds == service.CHECK_INTERVAL_SECONDS
            sleeps += 1
            await real_sleep(0)
            if sleeps == 2:
                stop.set()
                release.set()

        monkeypatch.setattr(service.asyncio, "to_thread", to_thread)
        monkeypatch.setattr(service.asyncio, "sleep", pause)
        await asyncio.wait_for(service.run_match_scheduler(stop), timeout=1)
        assert polls == 2
        assert sorted(started) == [42, 43]
        assert sorted(ended) == [42, 43]
        assert stop.is_set()

    asyncio.run(scenario())


def test_scheduler_retries_after_query_failure_and_releases_stop_event(monkeypatch):
    async def scenario():
        stop = Event()
        polls, workers = [], []
        real_sleep = asyncio.sleep
        logger = Mock()
        monkeypatch.setattr(service, "logger", logger)

        async def to_thread(fn, *args):
            if fn is service._get_due_match_ids:
                polls.append(True)
                if len(polls) == 1:
                    raise RuntimeError("query unavailable")
                return [42]
            workers.append(args[0])

        async def pause(seconds):
            await real_sleep(0)
            if len(polls) == 2:
                stop.set()

        monkeypatch.setattr(service.asyncio, "to_thread", to_thread)
        monkeypatch.setattr(service.asyncio, "sleep", pause)
        await asyncio.wait_for(service.run_match_scheduler(stop), timeout=1)
        assert len(polls) == 2
        assert workers == [42]
        logger.exception.assert_called_once()
        assert stop.is_set()

    asyncio.run(scenario())


def test_scheduler_does_not_dispatch_when_already_stopped(monkeypatch):
    stop = Event()
    stop.set()
    query = Mock(side_effect=AssertionError("should not query"))
    monkeypatch.setattr(service, "_get_due_match_ids", query)
    asyncio.run(service.run_match_scheduler(stop))
    query.assert_not_called()
