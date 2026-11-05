"""Persistencia y reanudación con simulación, reloj y repositorio controlados."""
import pytest
from contextlib import contextmanager
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

from app.errors import AppError
from app.services import match_execution_service as service
from app.services.match_request_handler import enqueue_request, pending_requests


class Simulation:
    def __init__(self, steps=1):
        self.finished = steps == 0
        self.duration_ms = 1000
        self.time = 0
        self.steps_left = steps
        self.steps = []
        self.close_calls = 0
        self.behaviour_changes = []

    def snapshot(self, sequence, sent_at):
        return {"sequence": sequence, "sentAt": sent_at,
                "state": {"status": "FINISHED" if self.finished else "RUNNING"}}

    def run_match(self, dt):
        self.steps.append(dt)
        self.time += dt
        self.steps_left -= 1
        self.finished = self.steps_left == 0

    def close_runtime(self):
        self.close_calls += 1

    def change_behaviour(self, player_id, **program):
        self.behaviour_changes.append((player_id, program))


@pytest.fixture
def execution(monkeypatch, db, now, freeze_time):
    service.clear_requests(42)
    freeze_time(service)
    simulation = Simulation()
    row = SimpleNamespace(match_id=42, status="SCHEDULED", duration_ms=1000,
                          sequence=8, snapshot=None, runtime_state=None)
    repo = Mock()
    repo.get_by_id_for_update.return_value = row

    def save(db, row, simulation, snapshot, now):
        row.sequence = snapshot["sequence"]
        row.snapshot = snapshot
        row.status = snapshot["state"]["status"]

    repo.save_progress.side_effect = save
    monkeypatch.setattr(service, "matches_repository", repo)
    monkeypatch.setattr(service, "prepare_match_start", Mock(return_value=simulation))
    monkeypatch.setattr(service, "Match", Mock())
    service.Match.from_checkpoint.return_value = simulation
    monkeypatch.setattr(service, "monotonic", Mock(return_value=0))
    monkeypatch.setattr(service, "sleep", Mock())
    yield SimpleNamespace(row=row, repo=repo, simulation=simulation)
    service.clear_requests(42)


def test_execution_persists_initial_and_final_snapshots_and_stops_at_finish(db, execution, now):
    result = service._execute(db, 42, None)
    assert result["state"]["status"] == "FINISHED"
    assert result["sequence"] == 10
    assert execution.simulation.steps == [service.PHYSICS_DT]
    assert execution.repo.save_progress.call_count == 2
    assert db.commit.call_count == 2
    service.prepare_match_start.assert_called_once_with(db, execution.row, now, duration_ms=1000)
    service.sleep.assert_called_once_with(service.STEPS_PER_SNAPSHOT * service.PHYSICS_DT)
    assert execution.simulation.close_calls == 1


def test_execution_batches_steps_and_preserves_sequence(db, execution):
    simulation = Simulation(steps=4)
    service.prepare_match_start.return_value = simulation
    result = service._execute(db, 42, 1000)
    assert len(simulation.steps) == 4
    assert result["sequence"] == 11
    assert execution.repo.save_progress.call_count == 3
    assert service.sleep.call_count == 2
    assert simulation.close_calls == 1


@pytest.mark.parametrize("duration", [0, -1, True, 1.5, "1000"])
def test_invalid_duration_never_starts_or_persists(db, execution, duration):
    with pytest.raises(AppError) as error:
        service._execute(db, 42, duration)
    assert error.value.code == "MATCH_INVALID_DURATION"
    service.prepare_match_start.assert_not_called()
    execution.repo.save_progress.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("status", ["FINISHED", "CANCELLED"])
def test_terminal_match_returns_saved_snapshot_without_replaying(db, execution, status):
    execution.row.status = status
    execution.row.snapshot = {"sequence": 8}
    assert service._execute(db, 42, None) is execution.row.snapshot
    db.rollback.assert_called_once()
    assert execution.simulation.close_calls == 0
    service.prepare_match_start.assert_not_called()
    execution.repo.save_progress.assert_not_called()


def test_future_match_releases_transaction_without_writing(db, execution):
    service.prepare_match_start.return_value = None
    assert service._execute(db, 42, None) is None
    db.rollback.assert_called_once()
    db.commit.assert_not_called()
    execution.repo.save_progress.assert_not_called()


def test_cancelled_start_commits_cancellation_snapshot(db, execution):
    def cancel(*args, **kwargs):
        execution.row.status = "CANCELLED"
        execution.row.snapshot = {"sequence": 9, "state": {"status": "CANCELLED"}}

    service.prepare_match_start.side_effect = cancel
    assert service._execute(db, 42, None) is execution.row.snapshot
    db.commit.assert_called_once()
    execution.repo.save_progress.assert_not_called()


def test_running_match_requires_checkpoint(db, execution):
    execution.row.status = "RUNNING"
    with pytest.raises(AppError) as error:
        service._execute(db, 42, None)
    assert error.value.code == "MATCH_STATE_INVALID"
    service.Match.from_checkpoint.assert_not_called()


def test_resume_uses_saved_checkpoint_without_rebuilding_lineup(db, execution):
    execution.row.status = "RUNNING"
    execution.row.runtime_state = {"frozen": "lineup-and-behaviours"}
    execution.row.snapshot = {"sequence": 8}
    result = service._execute(db, 42, 1000)
    service.Match.from_checkpoint.assert_called_once_with(execution.row.runtime_state)
    service.prepare_match_start.assert_not_called()
    assert result["sequence"] == 9
    assert db.commit.call_count == 1
    db.rollback.assert_called_once()
    assert execution.simulation.close_calls == 1


def test_resume_cannot_change_duration(db, execution):
    execution.row.status = "RUNNING"
    execution.row.runtime_state = {"checkpoint": True}
    with pytest.raises(AppError) as error:
        service._execute(db, 42, 2000)
    assert error.value.code == "MATCH_INVALID_DURATION"
    execution.repo.save_progress.assert_not_called()
    db.commit.assert_not_called()
    assert execution.simulation.close_calls == 1


def test_stop_during_execution_returns_last_persisted_snapshot(db, execution):
    stop = Mock(spec=Event)
    stop.wait.return_value = True
    result = service._execute(db, 42, None, stop)
    assert result["sequence"] == 9
    assert execution.simulation.steps == []
    assert execution.repo.save_progress.call_count == 1
    service.sleep.assert_not_called()
    assert execution.simulation.close_calls == 1


def test_stop_before_start_does_not_acquire_execution_session(execution):
    stop = Event()
    stop.set()
    assert service.run_persisted_match(42, stop_event=stop) is None
    execution.repo.execution_session.assert_not_called()


@pytest.mark.parametrize("deleted_during_run", [False, True])
def test_missing_match_stops_with_domain_error(db, execution, deleted_during_run):
    execution.repo.get_by_id_for_update.side_effect = [execution.row, None] if deleted_during_run else [None]
    with pytest.raises(AppError) as error:
        service._execute(db, 42, None)
    assert error.value.code == "MATCH_NOT_FOUND"
    assert execution.repo.save_progress.call_count == int(deleted_during_run)


def test_commit_failure_never_advances_simulation(db, execution):
    failure = RuntimeError("commit failed")
    db.commit.side_effect = failure
    with pytest.raises(RuntimeError) as error:
        service._execute(db, 42, None)
    assert error.value is failure
    assert execution.simulation.steps == []
    assert execution.simulation.close_calls == 1


@pytest.mark.parametrize("error_type", [ValueError, TypeError, KeyError])
def test_invalid_checkpoint_becomes_domain_error(db, execution, error_type):
    execution.row.status = "RUNNING"
    execution.row.runtime_state = {"invalid": True}
    service.Match.from_checkpoint.side_effect = error_type("invalid checkpoint")

    with pytest.raises(AppError) as error:
        service._execute(db, 42, None)

    assert error.value.code == "MATCH_STATE_INVALID"
    execution.repo.save_progress.assert_not_called()
    db.commit.assert_not_called()


def test_simulation_failure_closes_runtime(db, execution):
    failure = RuntimeError("simulation failed")
    execution.simulation.run_match = Mock(side_effect=failure)

    with pytest.raises(RuntimeError) as error:
        service._execute(db, 42, None)

    assert error.value is failure
    assert execution.simulation.close_calls == 1
    assert execution.repo.save_progress.call_count == 1


def test_custom_change_is_acknowledged_only_after_persisting(db, execution):
    program = {
        "behaviour_mode": "BALANCED",
        "behaviour_code": "def decide(observation):\n    return ir_a_pelota()",
        "behaviour_version": 2,
        "behaviour_api_version": 1,
    }
    request_id = enqueue_request(42, {
        "action": "CHANGE_BEHAVIOUR",
        "player_id": 74,
        "club_id": 7,
        "behaviour_id": 99,
        "program": program,
    })
    pending_at_commit = []
    db.commit.side_effect = lambda: pending_at_commit.append(
        [request["request_id"] for request in pending_requests(42)]
    )

    service._execute(db, 42, None)

    assert execution.simulation.behaviour_changes == [
        (74, {"club_id": 7, "behaviour_id": 99, **program})
    ]
    assert pending_at_commit == [[request_id], [request_id]]
    assert pending_requests(42) == []
    assert execution.simulation.close_calls == 1


def test_failed_commit_keeps_custom_change_pending(db, execution):
    request_id = enqueue_request(42, {
        "action": "CHANGE_BEHAVIOUR",
        "player_id": 74,
        "club_id": 7,
        "behaviour_id": 99,
        "program": {
            "behaviour_mode": "BALANCED",
            "behaviour_code": "def decide(observation):\n    return ir_a_pelota()",
            "behaviour_version": 2,
            "behaviour_api_version": 1,
        },
    })
    db.commit.side_effect = [None, RuntimeError("commit failed")]

    with pytest.raises(RuntimeError, match="commit failed"):
        service._execute(db, 42, None)

    assert [request["request_id"] for request in pending_requests(42)] == [request_id]
    assert len(execution.simulation.behaviour_changes) == 1
    assert execution.simulation.close_calls == 1


@pytest.mark.parametrize("fails", [False, True])
def test_execution_session_is_closed_on_success_and_failure(db, execution, monkeypatch, fails):
    events = []

    @contextmanager
    def session(match_id):
        events.append(("open", match_id))
        try:
            yield db
        finally:
            events.append(("close", match_id))

    execution.repo.execution_session.side_effect = session
    execute = Mock(return_value={"sequence": 42})
    monkeypatch.setattr(service, "_execute", execute)
    stop = Event()
    if fails:
        execute.side_effect = AppError("MATCH_STATE_INVALID", "bad state")
        with pytest.raises(AppError):
            service.run_persisted_match(42, duration_ms=500, stop_event=stop)
    else:
        assert service.run_persisted_match(42, duration_ms=500, stop_event=stop) == {"sequence": 42}
    execute.assert_called_once_with(db, 42, 500, stop)
    assert events == [("open", 42), ("close", 42)]
