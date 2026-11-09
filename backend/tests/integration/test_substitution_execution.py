from contextlib import contextmanager
from copy import deepcopy
from threading import Event
from unittest.mock import Mock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from test_league_start import database, league_data
from test_planned_substitution import running_match, body
from app.models.matches_model import Matches
from app.models.planned_substitution_model import PlannedSubstitution
from app.repository import matches_repository
from app.schemas.matches_schemas import PlannedSubstitutionRequest
from app.services import match_execution_service as execution
from app.services.match_request_handler import clear_requests, enqueue_request, pending_requests
from app.services.match_snapshot_service import read_snapshot
from app.services.planned_substitution_service import plan_substitution
from primitives import match_simulation
from primitives.dt_behaviour import DEFAULT_DT_CODES
from primitives.match_simulation import Match


@pytest.fixture
def game(database, league_data, running_match, monkeypatch):
    monkeypatch.setattr(match_simulation, "step", lambda *_: None)
    monkeypatch.setattr(Match, "run_behaviour", lambda *_: None)
    monkeypatch.setattr(execution, "sleep", lambda _: None)
    if database.dialect.name == "postgresql":
        monkeypatch.setattr(matches_repository, "engine", database)
    else:
        @contextmanager
        def session(match_id):
            with Session(database, expire_on_commit=False) as db:
                yield db
        monkeypatch.setattr(matches_repository, "execution_session", session)

    with Session(database) as db:
        row = db.get(Matches, running_match)
        state = deepcopy(row.runtime_state)
        state["duration_ms"] = 1000
        state["breaks"].update(hydration_ms=100, half_ms=200)
        state["scorer"] = {"LOCAL": 2, "VISITANTE": 1}
        state["local_team"]["substitutes"][0]["strength"] = 80
        state["local_team"]["substitutes"][0]["behaviour_mode"] = "DEFENSIVE"
        state["local_team"]["substitutes"][0]["behaviour_version"] = 3
        state["next_kick_at"] = {str(league_data.lineups[0][0]): 99,
                                 str(league_data.lineups[0][3]): 99}
        row.duration_ms = 1000
        row.runtime_state = state
        db.commit()
    return running_match


def plan(database, data, match_id, club=0):
    with Session(database) as db:
        return plan_substitution(db, match_id, data.clubs[club],
                                 PlannedSubstitutionRequest.model_validate(body(data, club=club)))


def run_until_pause(match_id):
    stop = Mock(spec=Event)
    stop.is_set.return_value = False
    stop.wait.side_effect = [False, False, False, True]
    return execution.run_persisted_match(match_id, stop_event=stop)


def test_applies_both_clubs_once_preserves_positions_and_recovers(database, league_data, game):
    for club in (0, 1):
        plan(database, league_data, game, club)
    with Session(database) as db:
        initial = deepcopy(db.get(Matches, game).runtime_state)
    partial = run_until_pause(game)
    assert partial["state"]["phase"] == "HYDRATION_BREAK"
    events = partial["state"]["events"]
    assert len(events) == 2
    assert len({event["eventId"] for event in events}) == 2
    assert all(event["type"] == "SUBSTITUTION_APPLIED" for event in events)
    own = partial["state"]["lineups"][0]
    assert own["pendingSubstitution"] is None
    assert own["remainingSubstitutions"] == 0
    assert own["starters"][0]["playerId"] == league_data.lineups[0][3]
    assert own["substitutes"][0]["playerId"] == league_data.lineups[0][0]
    with Session(database) as db:
        row = db.get(Matches, game)
        restored = Match.from_checkpoint(row.runtime_state)
        for club, key, position_index in ((0, "local_team", 0), (1, "visitor_team", 3)):
            out_id, in_id = league_data.lineups[club][0], league_data.lineups[club][3]
            assert out_id not in restored.player_bodies
            assert tuple(restored.player_bodies[in_id].position) == tuple(initial["bodies"][position_index]["position"])
            assert row.runtime_state[key]["substitutes"][0]["id"] == out_id
            assert (league_data.clubs[club], 1) in restored.substitution_pauses
        incoming = restored.local_team.players[0]
        assert incoming.behaviour_version == 3
        assert incoming.behaviour_mode == "DEFENSIVE"
        assert restored.player_bodies[incoming.id].mass == pytest.approx(80 * 84 / 100)
        assert restored.next_kick_at == {}
        assert len(restored.world.players) == len(restored.player_bodies) == 6
        assert restored.scorer == {"LOCAL": 2, "VISITANTE": 1}
        assert all(p.status == "APPLIED" for p in db.scalars(select(PlannedSubstitution)))

    final = execution.run_persisted_match(game)
    assert final["state"]["status"] == "FINISHED"
    assert final["state"]["events"] == events
    assert execution.run_persisted_match(game) == final
    with Session(database) as db:
        restored = Match.from_checkpoint(db.get(Matches, game).runtime_state)
        assert len(restored.world.players) == 6
        assert restored.scorer == {"LOCAL": 2, "VISITANTE": 1}


def test_revalidation_failure_does_not_consume_quota(database, league_data, game):
    plan(database, league_data, game)
    with Session(database) as db:
        pending = db.scalar(select(PlannedSubstitution))
        pending.in_player_id = league_data.lineups[1][3]
        db.commit()
    snapshot = run_until_pause(game)
    event = snapshot["state"]["events"][0]
    assert event["type"] == "SUBSTITUTION_REJECTED"
    assert event["reason"] == "SUBSTITUTION_INVALID_PLAYERS"
    with Session(database) as db:
        assert db.scalar(select(PlannedSubstitution)).status == "REJECTED"
        restored = Match.from_checkpoint(db.get(Matches, game).runtime_state)
        assert restored.substitution_pauses == set()
        restored.substitute(league_data.clubs[0], league_data.lineups[0][0], league_data.lineups[0][3])
        assert len(restored.player_bodies) == 6


@pytest.mark.parametrize("published_mode", [None, False])
def test_recovery_discards_legacy_manual_actions_for_dt_but_applies_the_rivals(
    database, league_data, game, published_mode,
):
    local_id, visitor_id = league_data.clubs[:2]
    local_players, visitor_players = league_data.lineups[:2]
    with Session(database) as db:
        row = db.get(Matches, game)
        checkpoint = deepcopy(row.runtime_state)
        checkpoint["local_team"].update(dt_active=True, dt_code=DEFAULT_DT_CODES["No hacer nada"])
        checkpoint["dt_errors"] = {str(local_id): "La estrategia falló."}
        row.runtime_state = checkpoint
        legacy_snapshot = deepcopy(row.snapshot)
        public_team = legacy_snapshot["state"]["teams"][0]
        if published_mode is None:
            del public_team["dtActive"]
        else:
            public_team["dtActive"] = published_mode
        legacy_snapshot["state"]["lineups"][0]["pendingSubstitution"] = {
            "pauseId": f"{game}:1", "status": "PENDING", "commandId": "legacy-1",
            "outPlayerId": local_players[0], "inPlayerId": local_players[3],
        }
        row.snapshot = legacy_snapshot
        before_sequence = row.sequence
        for pause in (1, 2):
            db.add(PlannedSubstitution(
                match_id=game, club_id=local_id, pause_index=pause, command_id=f"legacy-{pause}",
                out_player_id=local_players[0], in_player_id=local_players[3],
            ))
        db.commit()

    with Session(database) as db:
        snapshot = read_snapshot(db, game, local_id)
        assert snapshot["state"]["teams"][0]["dtActive"] is True
        assert snapshot["state"]["lineups"][0]["pendingSubstitution"] is None
        row = db.get(Matches, game)
        assert row.snapshot == legacy_snapshot and row.sequence == before_sequence

    plan(database, league_data, game, club=1)
    for club_id, player_id in ((local_id, local_players[1]), (visitor_id, visitor_players[1])):
        enqueue_request(game, {
            "action": "CHANGE_BEHAVIOUR", "club_id": club_id, "player_id": player_id,
            "behaviour_id": 77, "program": {
                "behaviour_mode": "OFFENSIVE", "behaviour_code": None,
                "behaviour_version": 1, "behaviour_api_version": 1,
            },
        })
    try:
        paused = run_until_pause(game)["state"]
        assert paused["phase"] == "HYDRATION_BREAK"
        assert pending_requests(game) == []
    finally:
        clear_requests(game)

    rejected = [event for event in paused["events"] if event["clubId"] == local_id]
    assert {event["pauseId"] for event in rejected} == {f"{game}:1", f"{game}:2"}
    assert all(event["type"] == "SUBSTITUTION_REJECTED" and
               event["reason"] == "MATCH_DT_MANUAL_ACTION_FORBIDDEN" for event in rejected)
    accepted, = [event for event in paused["events"] if event["clubId"] == visitor_id]
    assert accepted["type"] == "SUBSTITUTION_APPLIED"
    assert accepted["inPlayerId"] == visitor_players[3]
    players = {player["id"]: player for player in paused["players"]}
    assert players[local_players[1]]["behaviourMode"] == "BALANCED"
    assert players[visitor_players[1]]["behaviourMode"] == "OFFENSIVE"
    assert paused["teams"][0]["dtError"] == "La estrategia falló."
    with Session(database) as db:
        saved = {(row.club_id, row.pause_index): row.status for row in db.scalars(select(PlannedSubstitution))}
        assert saved == {(local_id, 1): "REJECTED", (local_id, 2): "REJECTED", (visitor_id, 1): "APPLIED"}


@pytest.mark.parametrize("pause", [1, 2, 3])
def test_only_one_change_per_pause_even_when_previous_pauses_were_unused(database, league_data, game, pause):
    with Session(database) as db:
        row = db.get(Matches, game)
        state = deepcopy(row.runtime_state)
        state["breaks"]["next_index"] = pause
        state["breaks"]["remaining_seconds"] = 0.1
        state["time"] = pause * 0.25
        row.runtime_state = state
        db.add(PlannedSubstitution(match_id=game, club_id=league_data.clubs[0], pause_index=pause,
                                  command_id="first", out_player_id=league_data.lineups[0][0],
                                  in_player_id=league_data.lineups[0][3]))
        db.commit()
    stop = Mock(spec=Event)
    stop.is_set.return_value = False
    stop.wait.return_value = True
    first = execution.run_persisted_match(game, stop_event=stop)
    assert first["state"]["events"][0]["type"] == "SUBSTITUTION_APPLIED"
    with Session(database) as db:
        db.add(PlannedSubstitution(match_id=game, club_id=league_data.clubs[0], pause_index=pause,
                                  command_id="second", out_player_id=league_data.lineups[0][1],
                                  in_player_id=league_data.lineups[0][4]))
        db.commit()
    second = execution.run_persisted_match(game, stop_event=stop)
    assert second["state"]["events"][-1]["reason"] == "SUBSTITUTION_QUOTA_USED"
    assert sum(e["type"] == "SUBSTITUTION_APPLIED" for e in second["state"]["events"]) == 1
    with Session(database) as db:
        restored = Match.from_checkpoint(db.get(Matches, game).runtime_state)
        assert restored.substitution_pauses == {(league_data.clubs[0], pause)}
        assert len(restored.player_bodies) == 6


def test_short_pause_crossed_inside_one_batch_still_applies_once(database, league_data, game):
    with Session(database) as db:
        row = db.get(Matches, game)
        state = deepcopy(row.runtime_state)
        state["breaks"].update(hydration_ms=1, half_ms=1)
        row.runtime_state = state
        db.commit()
    plan(database, league_data, game)
    final = execution.run_persisted_match(game)
    assert len(final["state"]["events"]) == 1
    assert final["state"]["events"][0]["type"] == "SUBSTITUTION_APPLIED"


def test_stale_plan_expires_without_being_applied_at_next_pause(database, league_data, game):
    plan(database, league_data, game)
    with Session(database) as db:
        row = db.get(Matches, game)
        state = deepcopy(row.runtime_state)
        state["breaks"].update(next_index=2, remaining_seconds=0.1)
        state["time"] = 0.5
        row.runtime_state = state
        db.commit()
    final = execution.run_persisted_match(game)
    event = final["state"]["events"][0]
    assert event["type"] == "SUBSTITUTION_REJECTED"
    assert event["reason"] == "PAUSE_CLOSED"
    with Session(database) as db:
        assert db.scalar(select(PlannedSubstitution)).status == "EXPIRED"
        assert Match.from_checkpoint(db.get(Matches, game).runtime_state).substitution_pauses == set()


def test_three_pauses_allow_three_exchanges_without_duplicating_bodies(database, league_data, game):
    for index in range(3):
        if index:
            stop = Mock(spec=Event)
            stop.is_set.return_value = False
            stop.wait.side_effect = [False, True]
            assert execution.run_persisted_match(game, stop_event=stop)["state"]["phase"] == "PLAYING"
        payload = PlannedSubstitutionRequest(
            outPlayerId=league_data.lineups[0][index], inPlayerId=league_data.lineups[0][index + 3],
            commandId=f"pause-{index + 1}",
        )
        with Session(database) as db:
            assert plan_substitution(db, game, league_data.clubs[0], payload)["pauseId"] == f"{game}:{index + 1}"
        partial = run_until_pause(game)
        assert len(partial["state"]["events"]) == index + 1
    final = execution.run_persisted_match(game)
    assert len(final["state"]["events"]) == 3
    assert len({event["eventId"] for event in final["state"]["events"]}) == 3
    with Session(database) as db:
        restored = Match.from_checkpoint(db.get(Matches, game).runtime_state)
        assert [p.id for p in restored.local_team.players] == league_data.lineups[0][3:]
        assert [p.id for p in restored.local_team.substitutes] == league_data.lineups[0][:3]
        assert len(restored.substitution_pauses) == 3
        assert len(restored.player_bodies) == len(restored.world.players) == 6
        assert restored.scorer == {"LOCAL": 2, "VISITANTE": 1}


def test_failed_commit_rolls_back_exchange_plan_and_event(database, league_data, game, monkeypatch):
    plan(database, league_data, game)
    commit = Session.commit
    failed = []

    def fail_at_substitution(db):
        if not failed and db.scalar(select(PlannedSubstitution).where(PlannedSubstitution.status == "APPLIED")):
            failed.append(True)
            raise RuntimeError("simulated commit failure")
        return commit(db)

    monkeypatch.setattr(Session, "commit", fail_at_substitution)
    with pytest.raises(RuntimeError, match="simulated commit failure"):
        execution.run_persisted_match(game)
    with Session(database) as db:
        assert db.scalar(select(PlannedSubstitution)).status == "PENDING"
        restored = Match.from_checkpoint(db.get(Matches, game).runtime_state)
        assert restored.substitution_events == []
        assert restored.substitution_pauses == set()
        assert league_data.lineups[0][0] in restored.player_bodies
    monkeypatch.setattr(Session, "commit", commit)
    final = execution.run_persisted_match(game)
    assert len(final["state"]["events"]) == 1
    assert final["state"]["events"][0]["type"] == "SUBSTITUTION_APPLIED"
