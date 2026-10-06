"""Decisiones previas al inicio; no se simula física ni se usa SQL."""
import pytest
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

from app.errors import AppError
from app.services import match_start_service as service


@pytest.fixture
def start(monkeypatch, now):
    row = SimpleNamespace(match_id=42, creator_id=1, visitor_id=7,
                          status="SCHEDULED", init_date=now, sequence=3, snapshot=None)
    snapshot = {"sequence": 3, "state": {"status": "WAITING", "teams": [{"id": 1}]}}
    repository = Mock()
    repository.get_clubs_for_update.return_value = [SimpleNamespace(id=1), SimpleNamespace(id=7)]
    repository.clubs_have_running_match.return_value = False
    builder = Mock(return_value=object())
    monkeypatch.setattr(service, "matches_repository", repository)
    monkeypatch.setattr(service, "build_match", builder)
    monkeypatch.setattr(service, "read_snapshot", Mock(return_value=snapshot))
    return SimpleNamespace(row=row, repo=repository, builder=builder, snapshot=snapshot)


@pytest.mark.parametrize("status", ["WAITING", "WAITING_OPPONENT", "SCHEDULED"])
def test_due_pending_match_uses_locked_clubs_and_requested_duration(db, start, now, status):
    start.row.status = status
    assert service.prepare_match_start(db, start.row, now, duration_ms=9000) is start.builder.return_value
    start.repo.get_clubs_for_update.assert_called_once_with(db, (1, 7))
    start.repo.clubs_have_running_match.assert_called_once_with(db, (1, 7), 42)
    start.builder.assert_called_once_with(db, 42, duration_ms=9000)
    db.commit.assert_not_called()


def test_future_match_is_untouched(db, start, now):
    start.row.init_date = now + timedelta(microseconds=1)
    assert service.prepare_match_start(db, start.row, now) is None
    assert (start.row.status, start.row.sequence) == ("SCHEDULED", 3)
    start.repo.get_clubs_for_update.assert_not_called()
    start.builder.assert_not_called()
    db.flush.assert_not_called()


@pytest.mark.parametrize("status", ["RUNNING", "FINISHED", "CANCELLED"])
def test_nonpending_match_cannot_start_again(db, start, now, status):
    start.row.status = status
    with pytest.raises(AppError) as error:
        service.prepare_match_start(db, start.row, now)
    assert error.value.code == "MATCH_STATE_INVALID"
    start.builder.assert_not_called()
    db.flush.assert_not_called()


@pytest.mark.parametrize("reason", ["NO_OPPONENT", "INVALID_CLUBS", "CLUB_BUSY", "INVALID_LINEUP", "INVALID_BEHAVIOUR"])
def test_cancellation_publishes_new_sequence_without_mutating_previous_snapshot(db, start, now, reason):
    before = deepcopy(start.snapshot)
    if reason == "NO_OPPONENT":
        start.row.visitor_id = None
    elif reason == "INVALID_CLUBS":
        start.repo.get_clubs_for_update.return_value = [SimpleNamespace(id=1)]
    elif reason == "CLUB_BUSY":
        start.repo.clubs_have_running_match.return_value = True
    else:
        start.builder.side_effect = AppError(f"MATCH_{reason}", "Invalid configuration")
    assert service.prepare_match_start(db, start.row, now) is None
    assert (start.row.status, start.row.cancellation_reason, start.row.sequence) == ("CANCELLED", reason, 4)
    assert start.row.snapshot["state"]["cancellationReason"] == reason
    assert start.row.snapshot["state"]["status"] == "CANCELLED"
    assert start.row.snapshot["sentAt"] == now.isoformat()
    assert start.row.snapshot["sequence"] == 4
    assert start.snapshot == before
    assert start.row.snapshot is not start.snapshot
    service.read_snapshot.assert_called_once_with(db, 42, 1)
    db.flush.assert_called_once()
    db.commit.assert_not_called()
    if reason in {"NO_OPPONENT", "INVALID_CLUBS", "CLUB_BUSY"}:
        start.builder.assert_not_called()


@pytest.mark.parametrize("failure", [AppError("OTHER", "unexpected"), RuntimeError("unexpected")])
def test_unexpected_builder_failure_is_not_converted_into_cancellation(db, start, now, failure):
    start.builder.side_effect = failure
    with pytest.raises(type(failure)) as error:
        service.prepare_match_start(db, start.row, now)
    assert error.value is failure
    assert start.row.status == "SCHEDULED"
    db.flush.assert_not_called()
