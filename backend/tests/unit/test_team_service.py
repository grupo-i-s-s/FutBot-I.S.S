from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.errors import AppError
from app.schemas.team_schemas import Lineup
from app.services import team_service as service


@pytest.fixture
def team(monkeypatch):
    data = {
        "formationId": 1,
        "starters": [{"playerId": i, "behaviourId": 10} for i in (1, 2, 3)],
        "substitutes": [{"playerId": i, "behaviourId": 11} for i in (4, 5, 6)],
    }
    repos = SimpleNamespace(players=Mock(), behaviours=Mock(), teams=Mock())
    repos.players.get_players_by_club.return_value = [SimpleNamespace(id=i) for i in range(1, 7)]
    repos.behaviours.get_all_behaviours.return_value = [SimpleNamespace(id=i) for i in (10, 11)]
    repos.teams.get_by_club.return_value = SimpleNamespace(club_id=7, line_up=data)
    repos.teams.save.side_effect = lambda db, club_id, line_up: SimpleNamespace(club_id=club_id, line_up=line_up)
    monkeypatch.setattr(service, "player_repository", repos.players)
    monkeypatch.setattr(service, "behaviour_repository", repos.behaviours)
    monkeypatch.setattr(service, "team_repository", repos.teams)
    return data, repos


def test_default_team_is_scoped_to_authenticated_club(db, team):
    _, repos = team
    result = service.get_default_team(db, 7)
    assert result.club_id == 7
    assert [p.player_id for p in result.line_up.starters] == [1, 2, 3]
    repos.teams.get_by_club.assert_called_once_with(db, 7)


def test_missing_default_team_is_account_incomplete(db, team):
    _, repos = team
    repos.teams.get_by_club.return_value = None
    with pytest.raises(AppError) as error:
        service.get_default_team(db, 7)
    assert error.value.code == "ACCOUNT_INCOMPLETE"


def test_save_team_keeps_selected_starters_substitutes_and_behaviours(db, team):
    data, repos = team
    data["starters"], data["substitutes"] = data["substitutes"], data["starters"]
    result = service.update_default_team(db, 7, Lineup.model_validate(data))
    repos.teams.save.assert_called_once_with(db, 7, data)
    repos.players.get_players_by_club.assert_called_once_with(db, 7)
    repos.behaviours.get_all_behaviours.assert_called_once_with(db, 7)
    assert [p.player_id for p in result.line_up.starters] == [4, 5, 6]
    assert [p.behaviour_id for p in result.line_up.starters] == [11, 11, 11]
    db.commit.assert_called_once()
    db.rollback.assert_not_called()


@pytest.mark.parametrize("group,field", [
    ("starters", "playerId"), ("substitutes", "playerId"),
    ("starters", "behaviourId"), ("substitutes", "behaviourId"),
])
def test_foreign_or_inactive_selection_is_rejected_without_saving(db, team, group, field):
    data, repos = team
    data[group][1][field] = 999
    with pytest.raises(AppError) as error:
        service.update_default_team(db, 7, Lineup.model_validate(data))
    assert error.value.code == "VALIDATION_ERROR"
    assert f"{group}.1.{field}" in error.value.fields
    repos.teams.save.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_called_once()


def test_unknown_formation_is_rejected_before_loading_roster(db, team):
    data, repos = team
    data["formationId"] = 999
    with pytest.raises(AppError) as error:
        service.update_default_team(db, 7, Lineup.model_validate(data))
    assert "formationId" in error.value.fields
    repos.players.get_players_by_club.assert_not_called()
    repos.teams.save.assert_not_called()


@pytest.mark.parametrize("failure_at", ["save", "commit"])
def test_team_failure_rolls_back_and_propagates(db, team, failure_at):
    data, repos = team
    failure = RuntimeError("simulated write failure")
    target = repos.teams.save if failure_at == "save" else db.commit
    target.side_effect = failure
    with pytest.raises(RuntimeError) as error:
        service.update_default_team(db, 7, Lineup.model_validate(data))
    assert error.value is failure
    db.rollback.assert_called_once()


@pytest.mark.parametrize("group", ["starters", "substitutes"])
def test_lineup_cannot_select_same_player_twice(team, group):
    data, _ = team
    data[group][1]["playerId"] = data["starters"][0]["playerId"]
    with pytest.raises(ValidationError, match="distintos"):
        Lineup.model_validate(data)
