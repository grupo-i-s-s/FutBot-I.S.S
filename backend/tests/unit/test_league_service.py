"""Reglas de ligas; los repositorios no ejecutan SQL en estos tests."""
import pytest
from datetime import timedelta, timezone
from fastapi import HTTPException
from types import SimpleNamespace
from unittest.mock import Mock

from app.errors import AppError
from app.schemas.league_schemas import CreateLeagueRequest, CreatePrivateLeagueRequest
from app.services import league_lineup_service as lineups, league_service as service
from primitives.behaviours import DEFAULT_CODES


@pytest.fixture
def leagues(monkeypatch, now, freeze_time):
    freeze_time(service)
    repository = Mock()
    players = Mock()
    monkeypatch.setattr(service, "league_repository", repository)
    monkeypatch.setattr(lineups, "player_repository", players)
    slots = [{"playerId": i, "behaviourId": 1} for i in range(1, 7)]
    lineup = {"formationId": 1, "starters": slots[:3], "substitutes": slots[3:]}
    monkeypatch.setattr(lineups.team_repository, "get_by_club", Mock(return_value=SimpleNamespace(line_up=lineup)))
    behaviour = SimpleNamespace(id=1, name="Equilibrado", code=DEFAULT_CODES["Equilibrado"],
                                kind="PLAYER", version=1, validation_status="VALID")
    monkeypatch.setattr(lineups.behaviour_repository, "get_all_behaviours", Mock(return_value=[behaviour]))
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
    return SimpleNamespace(repo=repository, players=players, row=league, lineup=lineup)


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
                        creator_club_id=7, creator_line_up=leagues.lineup)
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


def test_join_upgrades_legacy_player_ids_to_complete_lineup(db, leagues):
    selected = [1, 2, 3, 4, 5, 6]
    result = service.join_league(db, 42, 7, selected)
    leagues.repo.create_registration.assert_called_once_with(db, 42, 7, leagues.lineup)
    leagues.players.get_players_by_club.assert_called_once_with(db, 7)
    assert result["clubId"] == 7
    db.commit.assert_called_once()


@pytest.mark.parametrize("case, status", [
    ("missing", 404), ("closed", 409),
    ("full", 409), ("registered", 409), ("foreign_player", 400),
])
def test_join_rejects_unavailable_league_or_invalid_roster(db, leagues, now, case, status):
    selected = [1, 2, 3, 4, 5, 6]
    if case == "missing":
        leagues.repo.get_league_for_join.return_value = None
    elif case == "closed":
        leagues.row.status = "finished"
    elif case == "full":
        leagues.repo.count_registrations.return_value = leagues.row.max_teams
    elif case == "registered":
        leagues.repo.get_registration.return_value = SimpleNamespace(club_id=7)
    else:
        selected[-1] = 99
    codes = {"closed": "LEAGUE_CLOSED", "full": "LEAGUE_FULL", "registered": "ALREADY_REGISTERED"}
    with pytest.raises(AppError if case in codes else HTTPException) as error:
        service.join_league(db, 42, 7, selected)
    if case in codes:
        assert error.value.code == codes[case]
    else:
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


@pytest.mark.parametrize("supplied, valid", [(None, False), ("wrong", False), ("secret", True)])
def test_join_private_league_verifies_only_password_hash(db, leagues, supplied, valid):
    leagues.row.is_private = True
    leagues.row.password_hash = "encoded"
    service.verify_password.return_value = valid
    if valid:
        service.join_league(db, 42, 7, [1, 2, 3, 4, 5, 6], supplied)
        leagues.repo.create_registration.assert_called_once()
    else:
        with pytest.raises(AppError) as error:
            service.join_league(db, 42, 7, [1, 2, 3, 4, 5, 6], supplied)
        assert error.value.code == "LEAGUE_ACCESS_INVALID"
        leagues.repo.create_registration.assert_not_called()
    if supplied:
        service.verify_password.assert_called_once_with(supplied, "encoded")
    else:
        service.verify_password.assert_not_called()


def test_password_hash_takes_precedence_over_legacy_code(db, leagues):
    leagues.row.access_code = "secret"
    leagues.row.password_hash = "encoded"
    service.verify_password.return_value = False
    with pytest.raises(AppError):
        service.join_league(db, 42, 7, [1, 2, 3, 4, 5, 6], "secret")
    leagues.repo.create_registration.assert_not_called()


@pytest.mark.parametrize("private", [False, True])
def test_unmigrated_plaintext_password_never_allows_join(db, leagues, private):
    leagues.row.is_private = private
    leagues.row.access_code = "secret"
    with pytest.raises(AppError) as error:
        service.join_league(db, 42, 7, [1, 2, 3, 4, 5, 6], "secret")
    assert error.value.code == "LEAGUE_ACCESS_INVALID"
    service.verify_password.assert_not_called()
    leagues.repo.create_registration.assert_not_called()
    db.commit.assert_not_called()


def test_password_hash_protects_league_even_if_private_flag_is_missing(db, leagues):
    leagues.row.password_hash = "encoded"
    with pytest.raises(AppError) as error:
        service.join_league(db, 42, 7, [1, 2, 3, 4, 5, 6])
    assert error.value.code == "LEAGUE_ACCESS_INVALID"
    leagues.repo.create_registration.assert_not_called()


@pytest.mark.parametrize("case, status", [("missing", 404), ("closed", 409),
                                          ("started", 409), ("not_member", 409)])
def test_leave_rejects_without_removing_registration(db, leagues, now, case, status):
    if case == "missing":
        leagues.repo.get_league_by_id.return_value = None
    elif case == "closed":
        leagues.row.status = "running"
    elif case == "started":
        leagues.row.start_datetime = now
    with pytest.raises(HTTPException) as error:
        service.leave_league(db, 42, 7)
    assert error.value.status_code == status
    leagues.repo.delete_league.assert_not_called()
    leagues.repo.delete_registration.assert_not_called()
    db.commit.assert_not_called()


def test_creator_leaving_deletes_league_without_removing_only_their_registration(db, leagues):
    leagues.row.creator_club_id = 7

    result = service.leave_league(db, 42, 7)

    assert result["league_id"] == 42
    leagues.repo.delete_league.assert_called_once_with(db, leagues.row)
    leagues.repo.get_registration.assert_not_called()
    leagues.repo.delete_registration.assert_not_called()
    db.commit.assert_called_once()


def test_leave_removes_only_current_club_registration(db, leagues):
    registration = SimpleNamespace(club_id=7)
    leagues.repo.get_registration.return_value = registration
    assert service.leave_league(db, 42, 7)["league_id"] == 42
    leagues.repo.get_registration.assert_called_once_with(db, 42, 7)
    leagues.repo.delete_registration.assert_called_once_with(db, registration)
    leagues.repo.delete_league.assert_not_called()
    db.commit.assert_called_once()


def test_creator_can_cancel_open_league(db, leagues):
    assert service.leave_league(db, 42, leagues.row.creator_club_id)["league_id"] == 42
    leagues.repo.delete_league.assert_called_once_with(db, leagues.row)
    leagues.repo.delete_registration.assert_not_called()
    db.commit.assert_called_once()


@pytest.mark.parametrize("status", ["running", "finished"])
def test_creator_cannot_cancel_league_that_started(db, leagues, status):
    leagues.row.status = status
    with pytest.raises(HTTPException) as error:
        service.leave_league(db, 42, leagues.row.creator_club_id)
    assert error.value.status_code == 409
    leagues.repo.delete_league.assert_not_called()
    db.commit.assert_not_called()


def test_open_league_allows_join_and_leave_after_planned_start(db, leagues, now):
    leagues.row.start_datetime = now - timedelta(days=1)
    service.join_league(db, 42, 7, [1, 2, 3, 4, 5, 6])
    leagues.repo.get_registration.return_value = SimpleNamespace(club_id=7)
    service.leave_league(db, 42, 7)
    leagues.repo.create_registration.assert_called_once()
    leagues.repo.delete_registration.assert_called_once()


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


def test_running_lobby_includes_saved_standings(db, leagues):
    leagues.row.status = "running"
    leagues.repo.get_clubs_by_ids.return_value = [SimpleNamespace(id=1), SimpleNamespace(id=7)]
    standings = [SimpleNamespace(club_id=7, points=3)]
    leagues.repo.get_standings.return_value = standings
    result = service.get_league_lobby(db, 42, 7)
    assert result["standings"] == standings
    leagues.repo.get_standings.assert_called_once_with(db, 42)
    db.commit.assert_not_called()


def test_missing_lobby_is_not_found(db, leagues):
    leagues.repo.get_league_by_id.return_value = None
    with pytest.raises(HTTPException) as error:
        service.get_league_lobby(db, 42, 7)
    assert error.value.status_code == 404
    leagues.repo.get_clubs_by_ids.assert_not_called()


@pytest.mark.parametrize("name, normalized", [(None, None), ("  Demo  ", "Demo"), ("  ", "")])
def test_list_normalizes_filter_and_preserves_membership_capacity(db, leagues, name, normalized):
    leagues.repo.get_available_leagues.return_value = ([(leagues.row, 2, True)], None)
    listing = service.list_leagues(db, 7, name)
    leagues.repo.get_available_leagues.assert_called_once_with(db, 7, name=normalized, page=None, limit=None)
    item = listing.items[0]
    assert (item.id, item.registered_count, item.available_slots, item.is_member) == (42, 2, 6, True)
    assert "password_hash" not in item.model_dump()
    assert listing.total is None
    db.commit.assert_not_called()


@pytest.mark.parametrize("page, limit, expected_page, expected_limit", [(None, 10, 1, 10), (2, None, 2, 20)])
def test_list_defaults_missing_pagination_parameter(db, leagues, page, limit, expected_page, expected_limit):
    leagues.repo.get_available_leagues.return_value = ([], 41)
    listing = service.list_leagues(db, 7, page=page, limit=limit)
    leagues.repo.get_available_leagues.assert_called_once_with(
        db, 7, name=None, page=expected_page, limit=expected_limit,
    )
    assert listing.model_dump(by_alias=True) == {
        "items": [], "total": 41, "page": expected_page, "limit": expected_limit,
        "totalPages": 5 if expected_limit == 10 else 3,
    }
