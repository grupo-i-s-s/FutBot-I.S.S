from datetime import timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.schemas.league_schemas import LeagueFixtureRead
from app.services import league_fixture_service as service


@pytest.fixture
def fixture(monkeypatch, now):
    league = SimpleNamespace(id=42, status="running", round_interval="DAILY")
    rounds = [SimpleNamespace(
        id=number, number=number, scheduled_at=now + timedelta(days=number - 1),
        schedule_confirmed=number == 1, bye_club_id=None,
    ) for number in [1, 2, 3]]
    pairings = [(1, 2), (3, 4), (1, 3), (2, 4), (1, 4), (2, 3)]
    matches = [SimpleNamespace(
        match_id=index + 1, league_round_id=index // 2 + 1,
        creator_id=home, visitor_id=away, status="SCHEDULED",
        local_score=0, visitor_score=0, finished_at=None,
        init_date=rounds[index // 2].scheduled_at,
    ) for index, (home, away) in enumerate(pairings)]
    repository = Mock()
    repository.get_fixture_league.return_value = league
    repository.get_league_for_round.return_value = league
    repository.get_fixture_rounds.return_value = rounds
    repository.get_fixture_matches.return_value = matches
    repository.get_clubs_by_ids.return_value = [
        SimpleNamespace(id=id_, name=f"Club {id_}") for id_ in [1, 2, 3, 4]
    ]

    def update(db, round_, round_matches, scheduled_at, confirmed):
        round_.scheduled_at = scheduled_at
        round_.schedule_confirmed = confirmed
        for match in round_matches:
            match.init_date = scheduled_at

    repository.update_round_schedule.side_effect = update
    monkeypatch.setattr(service, "league_repository", repository)
    club_locks = Mock()
    monkeypatch.setattr(service.matches_repository, "get_clubs_for_update", club_locks)
    return SimpleNamespace(league=league, rounds=rounds, matches=matches, repo=repository, club_locks=club_locks)


def test_fixture_returns_rounds_clubs_results_and_next_match_without_writing(db, fixture):
    fixture.matches[0].local_score = 2
    result = service.get_league_fixture(db, 42, 1)

    assert [round_["number"] for round_ in result["rounds"]] == [1, 2, 3]
    assert result["rounds"][0]["matches"][0]["creator_club_name"] == "Club 1"
    assert result["rounds"][0]["matches"][0]["visitor_club_name"] == "Club 2"
    assert result["rounds"][0]["matches"][0]["local_score"] == 2
    assert result["next_match"]["match_id"] == 1
    assert result["next_match"]["round_number"] == 1
    assert result["next_match"]["schedule_confirmed"] is True
    fixture.repo.update_round_schedule.assert_not_called()
    db.commit.assert_not_called()
    db.flush.assert_not_called()


def test_next_match_skips_finished_running_and_cancelled_matches(db, fixture):
    fixture.matches[0].status = "FINISHED"
    fixture.matches[2].status = "RUNNING"
    result = service.get_league_fixture(db, 42, 1)
    assert result["next_match"]["match_id"] == 5
    fixture.matches[4].status = "CANCELLED"
    assert service.get_league_fixture(db, 42, 1)["next_match"] is None


def test_rest_is_explicit_and_next_match_can_be_in_a_later_round(db, fixture):
    fixture.rounds[0].bye_club_id = 1
    fixture.repo.get_fixture_matches.return_value = [fixture.matches[1], fixture.matches[2]]
    result = service.get_league_fixture(db, 42, 1)
    assert result["rounds"][0]["bye_club_id"] == 1
    assert result["next_match"]["round_number"] == 2


def test_finished_league_or_nonparticipant_has_no_next_match(db, fixture):
    assert service.get_league_fixture(db, 42, 99)["next_match"] is None
    fixture.league.status = "finished"
    assert service.get_league_fixture(db, 42, 1)["next_match"] is None


def test_open_league_returns_empty_fixture(db, fixture):
    fixture.league.status = "open"
    fixture.repo.get_fixture_rounds.return_value = []
    fixture.repo.get_fixture_matches.return_value = []
    assert service.get_league_fixture(db, 42, 1) == {
        "league_id": 42, "rounds": [], "next_match": None,
    }


def test_unknown_league_returns_not_found(db, fixture):
    fixture.repo.get_fixture_league.return_value = None
    with pytest.raises(HTTPException) as error:
        service.get_league_fixture(db, 42, 1)
    assert error.value.status_code == 404
    fixture.repo.get_fixture_rounds.assert_not_called()


@pytest.mark.parametrize("naive", [False, True])
def test_fixture_serializes_dates_in_utc(db, fixture, now, naive):
    fixture.rounds[0].scheduled_at = (
        now.replace(tzinfo=None) if naive
        else now.astimezone(timezone(timedelta(hours=-3)))
    )
    result = LeagueFixtureRead.model_validate(
        service.get_league_fixture(db, 42, 1),
    ).model_dump(mode="json", by_alias=True)
    assert result["rounds"][0]["scheduledAt"] == now.isoformat().replace("+00:00", "Z")
    assert result["nextMatch"]["scheduledAt"] == result["rounds"][0]["scheduledAt"]


@pytest.mark.parametrize("frequency, interval", [
    ("CONTINUOUS", timedelta(seconds=360)),
    ("DAILY", timedelta(days=1)),
    ("WEEKLY", timedelta(days=7)),
])
def test_last_finished_match_confirms_next_round_and_shifts_forecasts(db, fixture, now, frequency, interval):
    fixture.league.round_interval = frequency
    for index, match in enumerate(fixture.matches[:2]):
        match.status = "FINISHED"
        match.finished_at = now + timedelta(hours=index + 1)

    service.update_fixture_schedule(db, 1)

    expected = now + timedelta(hours=2) + interval
    assert fixture.rounds[1].scheduled_at == expected
    assert fixture.rounds[1].schedule_confirmed is True
    assert fixture.rounds[2].scheduled_at == expected + interval
    assert fixture.rounds[2].schedule_confirmed is False
    assert all(match.init_date == expected for match in fixture.matches[2:4])
    assert all(match.init_date == expected + interval for match in fixture.matches[4:])
    assert fixture.rounds[0].scheduled_at == now
    writes = fixture.repo.update_round_schedule.call_count
    service.update_fixture_schedule(db, 1)
    assert fixture.repo.update_round_schedule.call_count == writes
    fixture.club_locks.assert_called_once_with(db, (1, 2, 3, 4))
    db.commit.assert_not_called()


def test_incomplete_round_does_not_confirm_next_schedule(db, fixture, now):
    fixture.matches[0].status = "FINISHED"
    fixture.matches[0].finished_at = now + timedelta(hours=2)
    service.update_fixture_schedule(db, 1)
    fixture.repo.update_round_schedule.assert_not_called()
    fixture.club_locks.assert_not_called()


@pytest.mark.parametrize("already_confirmed", [False, True])
def test_confirmed_or_started_round_keeps_its_schedule(db, fixture, now, already_confirmed):
    for match in fixture.matches[:2]:
        match.status = "FINISHED"
        match.finished_at = now + timedelta(hours=2)
    if already_confirmed:
        fixture.rounds[1].schedule_confirmed = True
    else:
        fixture.matches[2].status = "RUNNING"

    service.update_fixture_schedule(db, 1)

    assert fixture.rounds[1].scheduled_at == now + timedelta(days=1)
    assert fixture.matches[2].init_date == now + timedelta(days=1)
