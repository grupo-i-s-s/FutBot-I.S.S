import json
from dataclasses import replace
from functools import partial

import pytest

from primitives import match_simulation
from primitives.behaviour_api.runtime import BehaviourRuntime
from primitives.behaviours import BehaviourMode
from primitives.dt_behaviour import DEFAULT_DT_CODES, LEGACY_DT_CODES
from primitives.match_simulation import Match, PlayerProfile, Team


@pytest.fixture
def make_match(monkeypatch):
    monkeypatch.setattr(match_simulation, "step", lambda *_: None)
    monkeypatch.setattr(Match, "run_behaviour", lambda *_: None)
    monkeypatch.setattr(Match, "_run_custom_behaviour", lambda *_: None)
    monkeypatch.setattr(match_simulation, "BehaviourRuntime", partial(BehaviourRuntime, decision_timeout=0.5))
    matches = []

    def team(club_id, code):
        def player(index):
            return PlayerProfile(
                club_id * 10 + index, club_id, f"Jugador {index}",
                60, 60, 60, 60, 60, behaviour_id=club_id * 100 + 1,
            )

        return Team(
            club_id, f"Club {club_id}", tuple(player(index) for index in range(1, 4)),
            substitutes=(player(4),), dt_active=bool(code), dt_code=code,
            dt_default_behaviours={
                BehaviourMode.BALANCED: (club_id * 100 + 1, 1),
                BehaviourMode.OFFENSIVE: (club_id * 100 + 2, 2),
                BehaviourMode.DEFENSIVE: (club_id * 100 + 3, 3),
            },
        )

    def create(code=DEFAULT_DT_CODES["Remontada"], *, visitor_code=None, custom_player=False):
        local = team(1, code)
        if custom_player:
            local = replace(local, players=(
                replace(local.players[0], behaviour_id=199, behaviour_code=(
                    "def decide(observation):\n    return ir_a(direccion=(70, 30))"
                )), *local.players[1:],
            ))
        match = Match(local, team(2, visitor_code), match_id=10, duration_ms=4000,
                      hydration_break_ms=100, half_break_ms=100)
        matches.append(match)
        return match

    yield create

    for match in matches:
        match.close_runtime()


@pytest.mark.parametrize("code", [DEFAULT_DT_CODES["Remontada"], LEGACY_DT_CODES["Remontada"]])
def test_dt_changes_only_own_players_with_default_programs(make_match, code):
    match = make_match(code, custom_player=True)
    match.run_match(1 / 30)

    local = match.snapshot(1, "now")["state"]["players"][:3]
    assert [player["behaviourId"] for player in local] == [199, 102, 102]
    assert [player["behaviourMode"] for player in local] == ["CUSTOM", "OFFENSIVE", "OFFENSIVE"]
    assert [player["behaviourVersion"] for player in local] == [1, 2, 2]
    assert {player.behaviour_id for player in match.visitor_team.players} == {201}


def test_dt_halftime_changes_share_pause_rules_and_resume(make_match):
    match = make_match(visitor_code=DEFAULT_DT_CODES["Manejar la pelota"])
    match.on_pause = match.run_dt_pause
    match.run_match(2.1)

    assert match.pause_index == 2
    assert match.paused
    assert match.substitution_pauses == {(1, 2), (2, 2)}
    assert match.player_bodies.keys() == {11, 12, 14, 21, 22, 24}
    assert [event["source"] for event in match.substitution_events] == ["DT", "DT"]

    checkpoint = json.loads(json.dumps(match.checkpoint()))
    restored = Match.from_checkpoint(checkpoint)
    assert json.loads(json.dumps(restored.checkpoint())) == checkpoint
    assert restored.run_dt_pause() is False
    assert restored.snapshot(2, "now") == match.snapshot(2, "now")


def test_manual_substitution_and_rival_dt_can_act_in_the_same_pause(make_match):
    match = make_match(None, visitor_code=DEFAULT_DT_CODES["Remontada"])
    match.run_match(2.1)

    match.substitute(1, 11, 14)
    assert match.run_dt_pause()
    event, = match.substitution_events
    assert event["source"] == "DT" and event["clubId"] == 2
    assert match.substitution_pauses == {(1, 2), (2, 2)}
    assert [player.id for player in match.local_team.players] == [14, 12, 13]
    assert {player.behaviour_id for player in match.local_team.players} == {101}
    assert [player.behaviour_id for player in match.visitor_team.players] == [202, 202, 201]


def test_custom_dt_uses_real_worker_to_substitute_at_hydration_break(make_match):
    code = """from primitives.dt_behaviour import DtAction
from primitives.behaviours import BehaviourMode

def decide(obs):
    orders = [cambiar_comportamiento(obs.players_id[0], BehaviourMode.DEFENSIVE)]
    if obs.can_substitute and obs.pause_index == 1:
        return DtAction(orders, [sustituir(obs.players_id[1], obs.substitutes_id[0])])
    return DtAction(orders)
"""
    match = make_match(code)
    match.on_pause = match.run_dt_pause
    match.run_match(1)

    assert match.dt_errors == {}
    assert match.local_team.players[0].behaviour_id == 103
    assert [player.id for player in match.local_team.players] == [11, 14, 13]
    assert match.substitution_events[0]["pauseId"] == "10:1"


def test_invalid_dt_is_disabled_without_interrupting_the_match(make_match):
    match = make_match("import os\n\ndef decide(obs):\n    return None", visitor_code=DEFAULT_DT_CODES["Remontada"])
    match.run_match(1 / 30)

    assert match.dt_errors.keys() == {1}
    assert match.time == pytest.approx(1 / 30)
    assert match.visitor_team.players[0].behaviour_id == 202
    restored = Match.from_checkpoint(json.loads(json.dumps(match.checkpoint())))
    team = restored.snapshot(1, "now")["state"]["teams"][0]
    assert team["dtActive"] is True
    assert team["dtError"] == match.dt_errors[1]
