from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.errors import AppError
from app.services import match_snapshot_service as snapshots
from app.services import match_stream_services as streams


@pytest.fixture
def access(monkeypatch, now):
    repo, users, sessions = Mock(), Mock(), Mock()
    row = SimpleNamespace(match_id=42, creator_id=1, visitor_id=7, snapshot=None,
                          status="SCHEDULED", sequence=5, duration_ms=60000)
    repo.get_by_id.return_value = row
    repo.get_club_names.return_value = {1: "Home", 7: "Away"}
    users.get_club.return_value = SimpleNamespace(id=7)
    authenticate = Mock(return_value=SimpleNamespace(user_id=3, session_hash="hashed-token"))
    monkeypatch.setattr(snapshots, "matches_repository", repo)
    monkeypatch.setattr(streams, "matches_repository", repo)
    monkeypatch.setattr(streams, "user_repository", users)
    monkeypatch.setattr(streams, "session_repository", sessions)
    monkeypatch.setattr(streams, "authenticate", authenticate)
    monkeypatch.setattr(streams, "utc_now", Mock(return_value=now))
    return SimpleNamespace(repo=repo, users=users, sessions=sessions, row=row, authenticate=authenticate)


@pytest.mark.parametrize("club_id", [1, 7])
def test_snapshot_returns_persisted_state_only_to_participants(db, access, club_id):
    access.row.snapshot = {"sequence": 5, "state": {"status": "RUNNING"}}
    assert snapshots.read_snapshot(db, 42, club_id) is access.row.snapshot
    access.repo.get_club_names.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("visitor", [None, 7])
def test_waiting_snapshot_contains_available_teams_and_does_not_start_match(db, access, now, freeze_time, visitor):
    freeze_time(snapshots)
    access.row.visitor_id = visitor
    result = snapshots.read_snapshot(db, 42, 1)
    assert (result["matchId"], result["sequence"], result["sentAt"]) == (42, 5, now.isoformat())
    state = result["state"]
    assert state["status"] == "WAITING" and state["clockMs"] == 0
    assert state["durationMs"] == 60000
    assert [(team["id"], team["side"], team["score"]) for team in state["teams"]] == (
        [(1, "LEFT", 0)] if visitor is None else [(1, "LEFT", 0), (7, "RIGHT", 0)])
    assert state["players"] == [] and state["ball"] is None
    assert access.row.status == "SCHEDULED"
    assert access.row.sequence == 5 and access.row.snapshot is None
    db.commit.assert_not_called()
    db.flush.assert_not_called()


@pytest.mark.parametrize("case, code", [("missing", "MATCH_NOT_FOUND"), ("outsider", "MATCH_FORBIDDEN"),
                                       ("running_without_snapshot", "MATCH_STATE_INVALID")])
def test_snapshot_rejects_missing_forbidden_or_inconsistent_state(db, access, case, code):
    if case == "missing":
        access.repo.get_by_id.return_value = None
    elif case == "running_without_snapshot":
        access.row.status = "RUNNING"
    with pytest.raises(AppError) as error:
        snapshots.read_snapshot(db, 42, 99 if case == "outsider" else 1)
    assert error.value.code == code
    access.repo.get_club_names.assert_not_called()


@pytest.mark.parametrize("club_id", [1, 7])
def test_stream_access_is_bound_to_authenticated_session_and_participating_club(db, access, club_id):
    access.users.get_club.return_value = SimpleNamespace(id=club_id)
    result = streams.authorize(db, "raw-token", 42)
    assert result == streams.StreamAccess("hashed-token", club_id)
    access.authenticate.assert_called_once_with(db, "raw-token")
    access.users.get_club.assert_called_once_with(db, 3)


@pytest.mark.parametrize("case, code", [("no_club", "ACCOUNT_INCOMPLETE"), ("missing", "MATCH_NOT_FOUND"),
                                       ("outsider", "MATCH_FORBIDDEN")])
def test_stream_rejects_incomplete_accounts_missing_matches_and_outsiders(db, access, case, code):
    if case == "no_club":
        access.users.get_club.return_value = None
    elif case == "missing":
        access.repo.get_by_id.return_value = None
    else:
        access.users.get_club.return_value = SimpleNamespace(id=99)
    with pytest.raises(AppError) as error:
        streams.authorize(db, "raw-token", 42)
    assert error.value.code == code
    db.commit.assert_not_called()


def test_stream_does_not_query_match_when_session_authentication_fails(db, access):
    failure = AppError("SESSION_INVALID", "expired")
    access.authenticate.side_effect = failure
    with pytest.raises(AppError) as error:
        streams.authorize(db, "expired-token", 42)
    assert error.value is failure
    access.users.get_club.assert_not_called()
    access.repo.get_by_id.assert_not_called()


@pytest.mark.parametrize("active", [True, False])
def test_stream_rechecks_current_session_at_poll_time(db, access, now, active):
    access.sessions.get_active.return_value = SimpleNamespace(user_id=3) if active else None
    assert streams.session_is_active(db, "hashed-token") is active
    access.sessions.get_active.assert_called_once_with(db, "hashed-token", now)
