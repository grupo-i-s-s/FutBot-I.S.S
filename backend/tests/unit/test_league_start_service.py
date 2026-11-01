from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.services import league_service as service


@pytest.fixture
def league(monkeypatch, now, freeze_time):
    freeze_time(service)
    row = SimpleNamespace(
        id=42, creator_club_id=1, status="open", min_teams=3,
        draw_seed=None, start_datetime=now, round_interval="DAILY",
        registrations=[
            SimpleNamespace(club_id=id_, line_up=list(range(id_ * 10, id_ * 10 + 6)))
            for id_ in [1, 2, 3]
        ],
    )
    repository = Mock()
    repository.get_league_by_id.return_value = row
    monkeypatch.setattr(service, "league_repository", repository)
    monkeypatch.setattr(service.player_repository, "get_players_by_club", Mock(
        side_effect=lambda db, id_: [SimpleNamespace(id=i) for i in range(id_ * 10, id_ * 10 + 6)],
    ))
    monkeypatch.setattr(service.team_repository, "get_by_club", Mock(return_value=None))
    monkeypatch.setattr(service, "generate_league_rounds", Mock(wraps=service.generate_league_rounds))
    return SimpleNamespace(row=row, repo=repository)


@pytest.mark.parametrize("frequency, interval", [
    ("CONTINUOUS", timedelta(seconds=120)),
    ("DAILY", timedelta(days=1)),
    ("WEEKLY", timedelta(days=7)),
])
def test_start_creates_fixture_and_standings_before_single_commit(db, league, now, frequency, interval):
    league.row.round_interval = frequency
    result = service.start_league(db, 42, 1)

    assert result == {"league_id": 42, "status": "running"}
    assert league.row.status == "running"
    assert isinstance(league.row.draw_seed, int)
    league.repo.get_league_by_id.assert_called_once_with(db, 42)
    assert league.repo.create_round.call_count == 3
    assert league.repo.create_round_matches.call_count == 3
    for index, call in enumerate(league.repo.create_round.call_args_list):
        assert call.args[:4] == (db, 42, index + 1, now + index * interval)
    league.repo.create_standings.assert_called_once_with(db, 42, [1, 2, 3])
    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_repeated_start_returns_same_league_without_generating_again(db, league):
    first = service.start_league(db, 42, 1)
    seed = league.row.draw_seed

    assert service.start_league(db, 42, 1) == first
    assert league.row.draw_seed == seed
    service.generate_league_rounds.assert_called_once()
    league.repo.create_standings.assert_called_once()


@pytest.mark.parametrize("case, expected_status", [
    ("missing", 404), ("other_creator", 403), ("cancelled", 409),
    ("finished", 409), ("minimum", 409), ("incomplete", 409),
    ("duplicate_player", 409), ("foreign_player", 409),
])
def test_rejected_start_never_creates_resources(db, league, case, expected_status):
    if case == "missing":
        league.repo.get_league_by_id.return_value = None
    elif case == "other_creator":
        league.row.creator_club_id = 99
    elif case in {"cancelled", "finished"}:
        league.row.status = case
    elif case == "minimum":
        league.row.registrations.pop()
    elif case == "incomplete":
        league.row.registrations[1].line_up = []
    elif case == "duplicate_player":
        league.row.registrations[1].line_up = [20] * 6
    else:
        league.row.registrations[1].line_up = [10, 21, 22, 23, 24, 25]

    with pytest.raises(HTTPException) as error:
        service.start_league(db, 42, 1)

    assert error.value.status_code == expected_status
    service.generate_league_rounds.assert_not_called()
    league.repo.create_round.assert_not_called()
    league.repo.create_standings.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_called_once()


def test_creator_without_selected_lineup_uses_default_team(db, league):
    league.row.registrations[0].line_up = []
    service.team_repository.get_by_club.return_value = SimpleNamespace(line_up={
        "formationId": 1,
        "starters": [{"playerId": id_, "behaviourId": 1} for id_ in [10, 11, 12]],
        "substitutes": [{"playerId": id_, "behaviourId": 1} for id_ in [13, 14, 15]],
    })

    service.start_league(db, 42, 1)

    assert league.row.registrations[0].line_up == [10, 11, 12, 13, 14, 15]


@pytest.mark.parametrize("line_up", [None, {}, {"formationId": 1}])
def test_missing_or_invalid_default_team_rejects_start(db, league, line_up):
    league.row.registrations[0].line_up = []
    if line_up is not None:
        service.team_repository.get_by_club.return_value = SimpleNamespace(line_up=line_up)

    with pytest.raises(HTTPException) as error:
        service.start_league(db, 42, 1)

    assert error.value.status_code == 409
    db.commit.assert_not_called()
    league.repo.create_round.assert_not_called()


@pytest.mark.parametrize("failure_at", ["round", "match", "standings", "commit"])
def test_generation_or_commit_failure_rolls_back(db, league, failure_at):
    target = {
        "round": league.repo.create_round,
        "match": league.repo.create_round_matches,
        "standings": league.repo.create_standings,
        "commit": db.commit,
    }[failure_at]
    target.side_effect = RuntimeError("Error simulado")

    with pytest.raises(RuntimeError, match="Error simulado"):
        service.start_league(db, 42, 1)

    db.rollback.assert_called_once()
    if failure_at != "commit":
        db.commit.assert_not_called()


def test_start_after_planned_date_uses_current_time(db, league, now):
    league.row.start_datetime = now - timedelta(days=1)
    service.start_league(db, 42, 1)
    assert league.repo.create_round.call_args_list[0].args[3] == now
