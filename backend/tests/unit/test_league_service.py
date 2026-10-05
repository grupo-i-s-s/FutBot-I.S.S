"""Reglas de ligas; los repositorios no ejecutan SQL en estos tests."""
from datetime import timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.errors import AppError
from app.schemas.league_schemas import CreateLeagueRequest, CreatePrivateLeagueRequest
from app.services import league_service as service


@pytest.fixture
def leagues(monkeypatch, now, freeze_time):
    freeze_time(service)
    repository = Mock()
    players = Mock()
    monkeypatch.setattr(service, "league_repository", repository)
    monkeypatch.setattr(service, "player_repository", players)
    monkeypatch.setattr(service, "hash_password", Mock(return_value="hashed-secret"))
    monkeypatch.setattr(service, "verify_password", Mock(return_value=True))
    league = SimpleNamespace(
        id=42, name="Demo", creator_club_id=1, is_private=False,
        password_hash=None, access_code=None, min_teams=3, max_teams=8,
        round_interval="DAILY", status="open", start_datetime=now + timedelta(days=1),
        registrations=[SimpleNamespace(club_id=1), SimpleNamespace(club_id=7)],
    )
    repository.get_league_for_join.return_value = league
    repository.get_league_by_id.return_value = league
    repository.create_league.return_value = league
    repository.get_registration.return_value = None
    repository.count_registrations.return_value = 2
    players.get_players_by_club.return_value = [SimpleNamespace(id=i) for i in range(1, 7)]
    return SimpleNamespace(repo=repository, players=players, row=league)


def creation(now, **changes):
    return CreateLeagueRequest(name="  Demo  ", minTeams=3, maxTeams=8,
                               start_date=now + timedelta(days=1), roundInterval="DAILY").model_copy(update=changes)


@pytest.mark.parametrize("private", [False, True])
def test_create_preserves_creator_and_hashes_only_private_password(db, leagues, now, private):
    if private:
        data = CreatePrivateLeagueRequest(**creation(now).model_dump(), password="secret")
        result = service.create_private_league(db, data, 7)
    else:
        result = service.create_league(db, creation(now), 7)
    args = leagues.repo.create_league.call_args.kwargs
    assert args == dict(db=db, name="Demo", min_teams=3, max_teams=8,
                        start_date=now + timedelta(days=1), round_interval="DAILY",
                        is_private=private, password_hash="hashed-secret" if private else None,
                        creator_club_id=7)
    assert result["league_id"] == 42
    assert service.hash_password.call_count == int(private)
    db.commit.assert_called_once()


def test_create_treats_naive_start_as_utc(db, leagues, now):
    service.create_league(db, creation(now, start_date=(now + timedelta(days=1)).replace(tzinfo=None)), 7)
    assert leagues.repo.create_league.call_args.kwargs["start_date"].tzinfo == timezone.utc


@pytest.mark.parametrize("changes", [
    {"name": "   "}, {"name": "x" * 51}, {"min_teams": 2},
    {"max_teams": 2}, {"round_interval": "MONTHLY"},
    {"start_date": "past"}, {"start_date": "exactly_now"},
])
def test_invalid_configuration_never_writes(db, leagues, now, changes):
    if changes.get("start_date") in ("past", "exactly_now"):
        changes = {"start_date": now - timedelta(seconds=int(changes["start_date"] == "past"))}
    with pytest.raises(AppError) as error:
        service.create_league(db, creation(now, **changes), 7)
    assert error.value.code == "VALIDATION_ERROR"
    leagues.repo.create_league.assert_not_called()
    db.commit.assert_not_called()


def test_private_league_requires_nonblank_password(db, leagues, now):
    data = CreatePrivateLeagueRequest(**creation(now).model_dump(), password="   ")
    with pytest.raises(AppError) as error:
        service.create_private_league(db, data, 7)
    assert error.value.code == "VALIDATION_ERROR"
    service.hash_password.assert_not_called()
    leagues.repo.create_league.assert_not_called()


@pytest.mark.parametrize("constraint, expected", [("leagues_name_key", "LEAGUE_DUPLICATE"), ("other", None)])
def test_create_translates_only_known_constraint(db, leagues, now, integrity_error, constraint, expected):
    failure = integrity_error(constraint)
    leagues.repo.create_league.side_effect = failure
    with pytest.raises(AppError if expected else type(failure)) as error:
        service.create_league(db, creation(now), 7)
    if expected:
        assert error.value.code == expected
    else:
        assert error.value is failure
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_join_uses_six_selected_players_and_authenticated_club(db, leagues):
    selected = [6, 4, 2, 1, 3, 5]
    result = service.join_league(db, 42, 7, selected)
    leagues.repo.create_registration.assert_called_once_with(db, 42, 7, selected)
    leagues.players.get_players_by_club.assert_called_once_with(db, 7)
    assert result["clubId"] == 7
    db.commit.assert_called_once()


@pytest.mark.parametrize("case, status", [
    ("missing", 404), ("closed", 409), ("started", 409),
    ("full", 409), ("registered", 409), ("foreign_player", 400),
])
def test_join_rejects_unavailable_league_or_invalid_roster(db, leagues, now, case, status):
    if case == "missing":
        leagues.repo.get_league_for_join.return_value = None
    elif case == "closed":
        leagues.row.status = "finished"
    elif case == "started":
        leagues.row.start_datetime = now
    elif case == "full":
        leagues.repo.count_registrations.return_value = leagues.row.max_teams
    elif case == "registered":
        leagues.repo.get_registration.return_value = SimpleNamespace(club_id=7)
    else:
        leagues.players.get_players_by_club.return_value = [SimpleNamespace(id=i) for i in range(1, 6)]
    with pytest.raises(HTTPException) as error:
        service.join_league(db, 42, 7, [1, 2, 3, 4, 5, 6])
    assert error.value.status_code == status
    leagues.repo.create_registration.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("lineup", [None, (1, 2, 3, 4, 5, 6), [1, 2, 3], [1, 2, 3, 4, 5, 5],
                                        [1, 2, 3, 4, 5, 0], [1, 2, 3, 4, 5, -1],
                                        [True, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, "6"]])
def test_join_rejects_nonunique_or_noninteger_six_player_lineup(db, leagues, lineup):
    with pytest.raises(HTTPException) as error:
        service.join_league(db, 42, 7, lineup)
    assert error.value.status_code == 400
    leagues.players.get_players_by_club.assert_not_called()
    leagues.repo.create_registration.assert_not_called()


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("supplied, valid", [(None, False), ("wrong", False), ("secret", True)])
def test_join_private_access_password_or_legacy_code(db, leagues, legacy, supplied, valid):
    leagues.row.is_private = True
    leagues.row.access_code = "secret" if legacy else None
    leagues.row.password_hash = None if legacy else "encoded"
    service.verify_password.return_value = valid
    if valid:
        service.join_league(db, 42, 7, [1, 2, 3, 4, 5, 6], supplied)
        leagues.repo.create_registration.assert_called_once()
    else:
        with pytest.raises(HTTPException) as error:
            service.join_league(db, 42, 7, [1, 2, 3, 4, 5, 6], supplied)
        assert error.value.status_code == 409
        leagues.repo.create_registration.assert_not_called()
    if supplied and not legacy:
        service.verify_password.assert_called_once_with(supplied, "encoded")
    else:
        service.verify_password.assert_not_called()


def test_password_hash_takes_precedence_over_legacy_code(db, leagues):
    leagues.row.access_code = "secret"
    leagues.row.password_hash = "encoded"
    service.verify_password.return_value = False
    with pytest.raises(HTTPException):
        service.join_league(db, 42, 7, [1, 2, 3, 4, 5, 6], "secret")
    leagues.repo.create_registration.assert_not_called()


@pytest.mark.parametrize("case, status", [("missing", 404), ("creator", 409), ("closed", 409),
                                         ("started", 409), ("not_member", 409)])
def test_leave_rejects_without_removing_registration(db, leagues, now, case, status):
    if case == "missing":
        leagues.repo.get_league_by_id.return_value = None
    elif case == "creator":
        leagues.row.creator_club_id = 7
    elif case == "closed":
        leagues.row.status = "running"
    elif case == "started":
        leagues.row.start_datetime = now
    with pytest.raises(HTTPException) as error:
        service.leave_league(db, 42, 7)
    assert error.value.status_code == status
    leagues.repo.delete_registration.assert_not_called()
    db.commit.assert_not_called()


def test_leave_removes_only_current_club_registration(db, leagues):
    registration = SimpleNamespace(club_id=7)
    leagues.repo.get_registration.return_value = registration
    assert service.leave_league(db, 42, 7)["league_id"] == 42
    leagues.repo.get_registration.assert_called_once_with(db, 42, 7)
    leagues.repo.delete_registration.assert_called_once_with(db, registration)
    db.commit.assert_called_once()


@pytest.mark.parametrize("member", [True, False])
def test_lobby_counts_members_and_includes_creator_without_registration(db, leagues, member):
    leagues.row.registrations = [SimpleNamespace(club_id=7)] if member else []
    creator, visitor = SimpleNamespace(id=1), SimpleNamespace(id=7)
    leagues.repo.get_clubs_by_ids.return_value = [creator, visitor]
    result = service.get_league_lobby(db, 42, 7)
    assert result["creator_club"] is creator
    assert result["clubs"] == ([visitor] if member else [])
    assert result["registered_teams"] == int(member)
    assert result["remaining_slots"] == 8 - int(member)
    assert result["is_registered"] is member
    assert set(leagues.repo.get_clubs_by_ids.call_args.args[1]) == ({1, 7} if member else {1})
    assert "password_hash" not in result and "access_code" not in result
    db.commit.assert_not_called()


def test_lobby_handles_missing_club_and_never_reports_negative_capacity(db, leagues):
    leagues.row.max_teams = 1
    leagues.repo.get_clubs_by_ids.return_value = [SimpleNamespace(id=1)]
    result = service.get_league_lobby(db, 42, 7)
    assert len(result["clubs"]) == 1
    assert result["registered_teams"] == 2
    assert result["remaining_slots"] == 0


def test_missing_lobby_is_not_found(db, leagues):
    leagues.repo.get_league_by_id.return_value = None
    with pytest.raises(HTTPException) as error:
        service.get_league_lobby(db, 42, 7)
    assert error.value.status_code == 404
    leagues.repo.get_clubs_by_ids.assert_not_called()


@pytest.mark.parametrize("name, normalized", [(None, None), ("  Demo  ", "Demo"), ("  ", "")])
def test_list_normalizes_filter_and_derives_membership_capacity(db, leagues, name, normalized):
    leagues.row.max_teams = 1
    leagues.repo.get_all_available_leagues.return_value = [leagues.row]
    item = service.list_leagues(db, 7, name)[0]
    leagues.repo.get_all_available_leagues.assert_called_once_with(db, name=normalized)
    assert (item.id, item.registered_count, item.available_slots, item.is_member) == (42, 2, 0, True)
    assert "password_hash" not in item.model_dump()
    assert service.list_leagues(db, 99, name)[0].is_member is False
    db.commit.assert_not_called()
