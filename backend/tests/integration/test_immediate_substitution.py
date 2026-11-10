from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import os
from threading import Barrier, Event

import pytest
from sqlalchemy.orm import Session

from test_league_start import database, league_data
from test_planned_substitution import api, body, plans, running_match
from test_substitution_execution import game, plan, run_until_pause
from app.errors import AppError
from app.models.matches_model import Matches
from app.repository import matches_repository
from app.schemas.matches_schemas import SubstitutionRequest
from app.services import match_execution_service as execution
from app.services.planned_substitution_service import request_substitution
from primitives.match_simulation import Match


def open_pause(database, match_id, index=1, remaining=0.05):
    with Session(database) as db:
        row = db.get(Matches, match_id)
        state = deepcopy(row.runtime_state)
        state["time"] = index * 0.25
        state["breaks"].update(next_index=index, remaining_seconds=remaining)
        execution._persist(db, row, Match.from_checkpoint(state))


def payload(data, match_id, command="manual-1", club=0, pause=1):
    return body(data, match_id, command, club, pause)


def submit(database, data, match_id, **kwargs):
    with Session(database) as db:
        return request_substitution(db, match_id, data.clubs[0],
                                    SubstitutionRequest.model_validate(payload(data, match_id, **kwargs)))


@pytest.mark.parametrize("pause", [1, 2, 3])
def test_accepts_without_a_plan_and_applies_before_resuming(api, database, league_data, game, pause):
    open_pause(database, game, pause)
    with Session(database) as db:
        before = deepcopy(db.get(Matches, game).runtime_state)
    url = f"/matches/{game}/substitutions"
    response = api.client.post(url, json=payload(league_data, game, pause=pause))
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "PENDING"
    with Session(database) as db:
        assert db.get(Matches, game).runtime_state == before
        assert len(plans(db)) == 1
    final = execution.run_persisted_match(game)
    event = final["state"]["events"][0]
    assert event["type"] == "SUBSTITUTION_APPLIED"
    assert event["pauseId"] == f"{game}:{pause}"
    assert final["state"]["lineups"][0]["starters"][0]["playerId"] == league_data.lineups[0][3]
    assert len(final["state"]["events"]) == 1
    assert api.client.post(url, json=payload(league_data, game, pause=pause)).json()["status"] == "APPLIED"


def test_running_writer_applies_a_request_received_during_the_pause(database, league_data, game, monkeypatch):
    open_pause(database, game)
    accepted = []
    run_play = Match._run_play

    def during_wait(_):
        if not accepted:
            accepted.append(submit(database, league_data, game))

    def resume(simulation, dt):
        assert simulation.substitution_events[0]["type"] == "SUBSTITUTION_APPLIED"
        return run_play(simulation, dt)

    monkeypatch.setattr(execution, "sleep", during_wait)
    monkeypatch.setattr(Match, "_run_play", resume)
    final = execution.run_persisted_match(game)
    assert accepted[0]["status"] == "PENDING"
    assert final["state"]["events"][0]["type"] == "SUBSTITUTION_APPLIED"
    assert final["state"]["events"][0]["pauseId"] == f"{game}:1"


def test_planned_and_manual_changes_share_the_quota(api, database, league_data, game):
    plan(database, league_data, game)
    run_until_pause(game)
    response = api.client.post(f"/matches/{game}/substitutions", json=payload(league_data, game))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SUBSTITUTION_QUOTA_USED"
    with Session(database) as db:
        assert len(plans(db)) == 1


def test_quota_from_the_engine_also_blocks_manual_changes(api, database, league_data, game):
    open_pause(database, game)
    with Session(database) as db:
        row = db.get(Matches, game)
        simulation = Match.from_checkpoint(row.runtime_state)
        simulation.substitute(league_data.clubs[0], league_data.lineups[0][0], league_data.lineups[0][3])
        execution._persist(db, row, simulation)
    response = api.client.post(f"/matches/{game}/substitutions", json=payload(league_data, game))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SUBSTITUTION_QUOTA_USED"


def test_retries_are_idempotent_and_a_second_command_cannot_replace_an_admitted_change(api, database, league_data, game):
    open_pause(database, game)
    url = f"/matches/{game}/substitutions"
    first = payload(league_data, game)
    accepted = api.client.post(url, json=first)
    assert accepted.status_code == 202
    assert api.client.post(url, json=first).json() == accepted.json()
    for altered in ({"inPlayerId": league_data.lineups[0][4]}, {"pauseId": f"{game}:2"}):
        response = api.client.post(url, json={**first, **altered})
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "SUBSTITUTION_COMMAND_CONFLICT"
    response = api.client.post(url, json=payload(league_data, game, command="manual-2"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SUBSTITUTION_QUOTA_USED"
    with Session(database) as db:
        assert len(plans(db)) == 1
        assert plans(db)[0].command_id == "manual-1"


def test_each_participant_has_its_own_quota_and_outsiders_cannot_change(api, database, league_data, game):
    open_pause(database, game)
    url = f"/matches/{game}/substitutions"
    for club in (0, 1):
        api.club[0] = league_data.clubs[club]
        assert api.client.post(url, json=payload(league_data, game, club=club)).status_code == 202
    api.club[0] = league_data.clubs[2]
    assert api.client.post(url, json=payload(league_data, game, club=2)).status_code == 403
    assert api.client.post("/matches/999999/substitutions", json=payload(league_data, game)).status_code == 404
    final = execution.run_persisted_match(game)
    assert len(final["state"]["events"]) == 2
    assert all(event["type"] == "SUBSTITUTION_APPLIED" for event in final["state"]["events"])


@pytest.mark.parametrize("out_club,out_index,in_club,in_index", [
    (1, 0, 0, 3), (0, 0, 1, 3), (0, 3, 0, 4), (0, 0, 0, 1),
])
def test_only_own_starter_and_substitute_are_allowed(api, database, league_data, game,
                                                   out_club, out_index, in_club, in_index):
    open_pause(database, game)
    data = {**payload(league_data, game), "outPlayerId": league_data.lineups[out_club][out_index],
            "inPlayerId": league_data.lineups[in_club][in_index]}
    response = api.client.post(f"/matches/{game}/substitutions", json=data)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SUBSTITUTION_INVALID_PLAYERS"
    with Session(database) as db:
        assert plans(db) == []


@pytest.mark.parametrize("paused,requested_pause", [(False, 1), (True, 2), (True, 0)])
def test_closed_or_different_pause_is_rejected(api, database, league_data, game, paused, requested_pause):
    if paused:
        open_pause(database, game)
    response = api.client.post(f"/matches/{game}/substitutions", json=payload(league_data, game, pause=requested_pause))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PAUSE_CLOSED"
    with Session(database) as db:
        assert plans(db) == []


@pytest.mark.parametrize("alteration", [
    {"pauseId": None}, {"pauseId": " "}, {"pauseId": 1},
    {"outPlayerId": "1"}, {"clubId": 1},
])
def test_invalid_requests_are_rejected(api, league_data, game, alteration):
    response = api.client.post(f"/matches/{game}/substitutions", json={**payload(league_data, game), **alteration})
    assert response.status_code == 422


@pytest.mark.parametrize("accept_first", [True, False])
@pytest.mark.skipif(not os.getenv("LEAGUE_TEST_DATABASE_URL"), reason="Requiere PostgreSQL")
def test_acceptance_and_pause_closure_are_serialized(database, league_data, game, monkeypatch, accept_first):
    open_pause(database, game)
    locked, release, competing = Event(), Event(), Event()
    original_commit, original_run = Session.commit, Match.run_match
    original_lock = matches_repository.get_by_id_for_update

    def hold_commit(db):
        if db.info.get("hold_acceptance"):
            locked.set()
            assert release.wait(10)
        return original_commit(db)

    def hold_closure(simulation, dt):
        if not accept_first and simulation.paused and not locked.is_set():
            locked.set()
            assert release.wait(10)
        return original_run(simulation, dt)

    def lock(db, match_id):
        if locked.is_set():
            competing.set()
        return original_lock(db, match_id)

    monkeypatch.setattr(Session, "commit", hold_commit)
    monkeypatch.setattr(Match, "run_match", hold_closure)
    monkeypatch.setattr(matches_repository, "get_by_id_for_update", lock)

    def send():
        with Session(database) as db:
            db.info["hold_acceptance"] = accept_first
            try:
                return request_substitution(db, game, league_data.clubs[0],
                                            SubstitutionRequest.model_validate(payload(league_data, game)))
            except AppError as exc:
                return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(send) if accept_first else pool.submit(execution.run_persisted_match, game)
        try:
            assert locked.wait(10)
            second = pool.submit(execution.run_persisted_match, game) if accept_first else pool.submit(send)
            assert competing.wait(10)
        finally:
            release.set()
        first_result, second_result = first.result(timeout=15), second.result(timeout=15)
    response, final = (first_result, second_result) if accept_first else (second_result, first_result)
    if accept_first:
        assert response["status"] == "PENDING"
        assert final["state"]["events"][0]["type"] == "SUBSTITUTION_APPLIED"
        assert final["state"]["events"][0]["pauseId"] == f"{game}:1"
    else:
        assert response == "PAUSE_CLOSED"
        assert final["state"]["events"] == []


@pytest.mark.skipif(not os.getenv("LEAGUE_TEST_DATABASE_URL"), reason="Requiere PostgreSQL")
@pytest.mark.parametrize("same_command", [True, False])
def test_concurrent_requests_do_not_duplicate_or_replace_accepted_commands(database, league_data, game, same_command):
    open_pause(database, game)
    barrier = Barrier(2)

    def send(index):
        barrier.wait(timeout=10)
        try:
            return submit(database, league_data, game, command="shared" if same_command else f"manual-{index}")
        except AppError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(send, range(2)))
    with Session(database) as db:
        assert len(plans(db)) == 1
    if same_command:
        assert results[0] == results[1]
    else:
        assert sum(result == "SUBSTITUTION_QUOTA_USED" for result in results) == 1
