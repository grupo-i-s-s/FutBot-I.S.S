"""Reglas de amistosos sin HTTP ni base de datos."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.errors import AppError
from app.repository import matches_repository
from app.services import matches_service


def test_create_persists_authenticated_club_id():
    db = Mock()
    db.refresh.side_effect = lambda match: setattr(match, "match_id", 42)
    data = SimpleNamespace(start_datetime=datetime.now(timezone.utc) + timedelta(hours=1))

    result = matches_service.create_friendly_match(db, 7, data)

    match = db.add.call_args.args[0]
    assert match.creator_id == 7
    assert result["match_id"] == 42
    db.commit.assert_called_once()


def test_create_rejects_past_date_without_writing():
    db = Mock()
    data = SimpleNamespace(start_datetime=datetime.now(timezone.utc) - timedelta(hours=1))

    with pytest.raises(AppError) as error:
        matches_service.create_friendly_match(db, 7, data)

    assert error.value.code == "MATCH_INVALID_DATE"
    db.add.assert_not_called()


@pytest.mark.parametrize("match, code", [
    (None, "MATCH_NOT_FOUND"),
    (SimpleNamespace(match_id=3, creator_id=7, visitor_id=None,
                     init_date=datetime.now(timezone.utc) + timedelta(hours=1)), "MATCH_SELF_JOIN"),
    (SimpleNamespace(match_id=3, creator_id=1, visitor_id=2,
                     init_date=datetime.now(timezone.utc) + timedelta(hours=1)), "MATCH_FULL"),
    (SimpleNamespace(match_id=3, creator_id=1, visitor_id=None,
                     status="WAITING", init_date=datetime.now(timezone.utc) - timedelta(hours=1)), "MATCH_STARTED"),
    (SimpleNamespace(match_id=3, creator_id=1, visitor_id=None,
                     status="FINISHED", init_date=datetime.now(timezone.utc) + timedelta(hours=1)), "MATCH_STARTED"),
])
def test_join_rejects_invalid_matches(monkeypatch, match, code):
    db = Mock()
    monkeypatch.setattr(matches_repository, "get_by_id_for_update", lambda *_: match)

    with pytest.raises(AppError) as error:
        matches_service.join_match(db, 3, 7)

    assert error.value.code == code
    db.commit.assert_not_called()


def test_join_sets_visitor_once(monkeypatch):
    db = Mock()
    match = SimpleNamespace(
        match_id=3, creator_id=1, visitor_id=None,
        sequence=0,
        status="WAITING",
        init_date=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    monkeypatch.setattr(matches_repository, "get_by_id_for_update", lambda *_: match)

    result = matches_service.join_match(db, 3, 7)

    assert match.visitor_id == 7
    assert match.sequence == 1
    assert result["match_id"] == 3
    db.commit.assert_called_once()


@pytest.mark.parametrize("start_kind", ["naive", "offset"])
def test_create_accepts_future_start_without_changing_requested_instant(db, now, freeze_time, start_kind):
    freeze_time(matches_service)
    start = now + timedelta(hours=1)
    supplied = start.replace(tzinfo=None) if start_kind == "naive" else start.astimezone(timezone(timedelta(hours=-3)))
    db.refresh.side_effect = lambda row: setattr(row, "match_id", 42)
    result = matches_service.create_friendly_match(db, 7, SimpleNamespace(start_datetime=supplied))
    row = db.add.call_args.args[0]
    assert row.init_date == start
    assert row.status == "WAITING_OPPONENT"
    assert row.visitor_id is None
    assert result["match_id"] == 42


def test_create_rejects_exact_start_boundary(db, now, freeze_time):
    freeze_time(matches_service)
    with pytest.raises(AppError) as error:
        matches_service.create_friendly_match(db, 7, SimpleNamespace(start_datetime=now))
    assert error.value.code == "MATCH_INVALID_DATE"
    db.add.assert_not_called()


@pytest.mark.parametrize("status", ["WAITING", "WAITING_OPPONENT"])
def test_successful_join_schedules_match_and_cannot_be_repeated(db, now, freeze_time, monkeypatch, status):
    freeze_time(matches_service)
    row = SimpleNamespace(match_id=42, creator_id=1, visitor_id=None, sequence=8,
                          status=status, init_date=now + timedelta(seconds=1))
    monkeypatch.setattr(matches_repository, "get_by_id_for_update", Mock(return_value=row))
    matches_service.join_match(db, 42, 7)
    assert (row.visitor_id, row.status, row.sequence) == (7, "SCHEDULED", 9)
    with pytest.raises(AppError) as error:
        matches_service.join_match(db, 42, 99)
    assert error.value.code == "MATCH_FULL"
    assert (row.visitor_id, row.sequence) == (7, 9)
    db.commit.assert_called_once()


def test_join_at_start_time_is_rejected_without_mutating_row(db, now, freeze_time, monkeypatch):
    freeze_time(matches_service)
    row = SimpleNamespace(match_id=42, creator_id=1, visitor_id=None, sequence=8,
                          status="WAITING_OPPONENT", init_date=now)
    monkeypatch.setattr(matches_repository, "get_by_id_for_update", Mock(return_value=row))
    with pytest.raises(AppError) as error:
        matches_service.join_match(db, 42, 7)
    assert error.value.code == "MATCH_STARTED"
    assert (row.visitor_id, row.status, row.sequence) == (None, "WAITING_OPPONENT", 8)
    db.commit.assert_not_called()


def test_my_matches_marks_creator_and_preserves_joined_finished_matches(db, now, monkeypatch):
    own = SimpleNamespace(match_id=42, creator_id=7, init_date=now, status="WAITING_OPPONENT")
    joined = SimpleNamespace(match_id=43, creator_id=1, init_date=now, status="FINISHED")
    repo = Mock(return_value=[(own, "Mine", None), (joined, "Other", "Mine")])
    monkeypatch.setattr(matches_repository, "list_for_club", repo)
    result = matches_service.list_for_club(db, 7)
    repo.assert_called_once_with(db, 7)
    assert [(r["match_id"], r["is_creator"], r["visitor_club_name"], r["status"]) for r in result] == [
        (42, True, None, "WAITING_OPPONENT"), (43, False, "Mine", "FINISHED")]
    db.commit.assert_not_called()


def test_available_matches_use_current_club_and_time(db, now, freeze_time, monkeypatch):
    freeze_time(matches_service)
    repo = Mock(return_value=[(SimpleNamespace(match_id=42, init_date=now), "Other")])
    monkeypatch.setattr(matches_repository, "list_available", repo)
    assert matches_service.list_available(db, 7) == [
        {"match_id": 42, "creator_club_name": "Other", "start_datetime": now}]
    repo.assert_called_once_with(db, 7, now)


@pytest.mark.parametrize("club_id", [1, 7])
def test_match_state_access_for_both_participants(db, monkeypatch, club_id):
    row = SimpleNamespace(creator_id=1, visitor_id=7, status="RUNNING",
                          local_score=2, visitor_score=1, duration_ms=60000)
    monkeypatch.setattr(matches_repository, "get_by_id", Mock(return_value=row))
    result = matches_service.get_match_state(db, 42, club_id)
    assert (result.status, result.local_score, result.visitor_score, result.duration_ms) == ("RUNNING", 2, 1, 60000)
    db.commit.assert_not_called()


@pytest.mark.parametrize("missing, status", [(True, 404), (False, 403)])
def test_match_state_rejects_missing_or_unrelated_match(db, monkeypatch, missing, status):
    row = None if missing else SimpleNamespace(creator_id=1, visitor_id=2)
    monkeypatch.setattr(matches_repository, "get_by_id", Mock(return_value=row))
    with pytest.raises(HTTPException) as error:
        matches_service.get_match_state(db, 42, 7)
    assert error.value.status_code == status
