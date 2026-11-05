"""Programas custom reales: worker aislado, física, fallos y recuperación JSON."""
import json
from dataclasses import replace
from functools import partial

import pytest

from primitives import match_simulation as simulation
from primitives.behaviour_api.context import snapshot_from_match
from primitives.behaviour_api.queries import Queries
from primitives.behaviour_api.registry import API_VERSION
from primitives.behaviour_api.runtime import BehaviourRuntime, resolve_program
from primitives.behaviour_api.validation import validate_program
from primitives.behaviours import BehaviourMode, DEFAULT_CODES


ROSTER_QUERY_CASES = (
    ("compañeros()[0]", (10.0, 10.0)),
    ("compañeros()[1]", (10.0, 50.0)),
    ("compañero_mas_cercano()", (10.0, 10.0)),
    ("rivales()[0]", (90.0, 10.0)),
    ("rivales()[1]", (90.0, 50.0)),
    ("rivales()[2]", (80.0, 50.0)),
)


@pytest.fixture
def make_match(monkeypatch):
    # Las pruebas funcionales no dependen de la latencia del planificador de CI.
    # El caso de bucle infinito configura su propio presupuesto pequeño.
    monkeypatch.setattr(
        simulation, "BehaviourRuntime",
        partial(BehaviourRuntime, decision_timeout=0.5),
    )
    created = []

    def create(source, *, second_source=None):
        def player(player_id, club_id, code=None):
            return simulation.PlayerProfile(
                id=player_id, club_id=club_id, name=f"Jugador {player_id}",
                speed=60, power=60, agility=60, strength=60, control=60,
                behaviour_id=100 + player_id, behaviour_code=code,
                behaviour_version=2 if code is not None else 1,
            )

        match = simulation.Match(
            simulation.Team(1, "Local", (
                player(1, 1, source), player(2, 1, second_source), player(3, 1),
            )),
            simulation.Team(2, "Visitante", (
                player(4, 2), player(5, 2), player(6, 2),
            )),
            duration_ms=2_000, hydration_break_ms=0, half_break_ms=0,
        )
        created.append(match)
        positions = {
            1: (20, 30), 2: (10, 10), 3: (10, 50),
            4: (90, 10), 5: (90, 50), 6: (80, 50),
        }
        for player_id, position in positions.items():
            match.player_bodies[player_id].position = position
        match.world.ball.position = (85, 30)
        return match

    yield create

    for match in created:
        match.close_runtime()


def test_validated_custom_drives_movement_and_reuses_worker(make_match):
    source = "def decide(observation):\n    return ir_a(direccion=(70, 30))"
    assert validate_program(source) == []
    match = make_match(source)
    body = match.player_bodies[1]
    before = body.position.x

    match.run_match(1 / 30)
    process = match._behaviour_runtime._process

    assert body.position.x > before
    assert match.behaviour_errors == {}
    assert process.poll() is None

    match.run_match(1 / 30)

    assert match._behaviour_runtime._process is process
    match.close_runtime()
    match.close_runtime()
    assert process.poll() is not None
    assert match._behaviour_runtime is None


@pytest.mark.parametrize("expression", [case[0] for case in ROSTER_QUERY_CASES])
def test_validation_accepts_public_roster_queries(expression):
    source = f"def decide(observation):\n    return ir_a({expression})"

    assert validate_program(source) == []


@pytest.mark.parametrize("expression, target", ROSTER_QUERY_CASES)
def test_public_roster_queries_drive_real_worker(
    make_match, monkeypatch, expression, target,
):
    source = f"def decide(observation):\n    return ir_a({expression})"
    match = make_match(source)
    body = match.player_bodies[1]
    before = tuple(body.position)
    actual_run_to = simulation.run_to
    recorded_targets = []

    def record_target(player, position, speed, dt):
        if player is body:
            recorded_targets.append(tuple(position))
        return actual_run_to(player, position, speed, dt)

    monkeypatch.setattr(simulation, "run_to", record_target)

    match.run_match(1 / 30)

    assert match.behaviour_errors == {}
    assert recorded_targets == [target]
    assert tuple(body.position) != before
    assert match._behaviour_runtime._process.poll() is None


@pytest.mark.parametrize("swapped", [False, True])
def test_custom_goal_query_respects_current_team_side(make_match, swapped):
    match = make_match("def decide(observation):\n    return ir_a(arco_rival())")
    if swapped:
        match.start_second_half()
    body = match.player_bodies[1]
    body.position = (50, 30)
    match.world.ball.position = (50, 55)

    match.run_match(1 / 30)

    assert (body.position.x < 50) if swapped else (body.position.x > 50)
    assert match.behaviour_errors == {}


@pytest.mark.parametrize("action, speed_limit", [
    ("patear_a((60, 30))", None),
    ("conducir_hacia((60, 30))", 12.0),
    ("Action((30, 30), (60, 30))", None),
])
def test_custom_interior_kicks_preserve_command_speed(
    make_match, monkeypatch, action, speed_limit,
):
    source = (
        "from primitives.behaviours import Action\n"
        f"def decide(observation):\n    return {action}"
    )
    match = make_match(source)
    match.player_bodies[1].position = (30, 30)
    match.world.ball.position = (32.2, 30)
    actual_kick = simulation.kick
    recorded = []

    def record_kick(player, ball, target, speed, kick_range):
        recorded.append((tuple(target), speed))
        return actual_kick(player, ball, target, speed, kick_range)

    monkeypatch.setattr(simulation, "kick", record_kick)

    match.run_match(1 / 30)

    expected_speed = speed_limit or (
        simulation.SHOT_BASE_SPEED
        + match.player_profiles[0].power * simulation.SHOT_POWER_FACTOR
    )
    assert recorded == [((60.0, 30.0), expected_speed)]
    assert match.world.ball.velocity.x > 0
    assert match.next_kick_at[1] > match.time
    assert match.behaviour_errors == {}


def test_queries_and_motor_both_respect_kick_cooldown(make_match, monkeypatch):
    match = make_match("def decide(observation):\n    return patear_a(arco_rival())")
    match.player_bodies[1].position = (30, 30)
    match.world.ball.position = (32.2, 30)
    match.next_kick_at[1] = 10.0
    snapshot = snapshot_from_match(
        match, simulation.SHOT_BASE_SPEED, simulation.SHOT_POWER_FACTOR,
    )
    calls = []
    monkeypatch.setattr(simulation, "kick", lambda *args: calls.append(args))

    assert Queries(snapshot, 1).can_kick() is False
    match.run_match(1 / 30)

    assert calls == []
    assert match.next_kick_at[1] == 10.0
    assert match.behaviour_errors == {}


def test_timeout_disables_only_culprit_and_survives_checkpoint(
    make_match, monkeypatch,
):
    source = (
        "def decide(observation):\n"
        "    if tiempo_jugado() < 1:\n"
        "        while True:\n"
        "            pass\n"
        "    return ir_a_pelota()"
    )
    assert validate_program(source) == []
    monkeypatch.setattr(
        simulation, "BehaviourRuntime",
        partial(BehaviourRuntime, decision_timeout=0.05),
    )
    match = make_match(source)
    teammate_before = tuple(match.player_bodies[2].position)

    match.run_match(1 / 30)

    assert set(match.behaviour_errors) == {1}
    assert match.behaviour_errors[1]["code"] == "TIMEOUT"
    assert tuple(match.player_bodies[2].position) != teammate_before
    assert match._behaviour_runtime is None

    restored = simulation.Match.from_checkpoint(
        json.loads(json.dumps(match.checkpoint()))
    )
    try:
        def forbidden_restart():
            pytest.fail("Se volvió a ejecutar un comportamiento deshabilitado.")

        monkeypatch.setattr(simulation, "BehaviourRuntime", forbidden_restart)
        restored.run_match(1 / 30)

        assert restored.time > match.time
        assert restored.behaviour_errors == match.behaviour_errors
    finally:
        restored.close_runtime()


def test_checkpoint_preserves_source_version_cooldown_and_physical_state(make_match):
    source = "def decide(observation):\n    return ir_a((70, 30))"
    match = make_match(source)
    match.next_kick_at[1] = 0.75
    match.run_match(1 / 30)
    checkpoint = json.loads(json.dumps(match.checkpoint()))

    restored = simulation.Match.from_checkpoint(checkpoint)
    try:
        profile = restored.player_profiles[0]
        assert checkpoint["version"] == 4
        assert profile.behaviour_code == source
        assert profile.behaviour_version == 2
        assert profile.behaviour_api_version == API_VERSION
        assert restored.next_kick_at == match.next_kick_at
        assert restored.scorer == match.scorer
        assert restored.time == match.time
        assert tuple(restored.player_bodies[1].position) == tuple(match.player_bodies[1].position)
        assert restored._behaviour_runtime is None

        before = restored.player_bodies[1].position.x
        restored.run_match(1 / 30)

        assert restored.player_bodies[1].position.x > before
        assert restored.behaviour_errors == {}
    finally:
        restored.close_runtime()


def test_failed_custom_can_be_replaced_then_changed_back_to_default(make_match):
    failing_source = (
        "def decide(observation):\n"
        "    if tiempo_jugado() < 1:\n"
        "        return None\n"
        "    return ir_a_pelota()"
    )
    match = make_match(failing_source)
    match.run_match(1 / 30)
    assert match.behaviour_errors[1]["code"] == "INVALID_ACTION"

    source = "def decide(observation):\n    return ir_a((70, 30))"
    match.change_behaviour(
        1, club_id=1, behaviour_id=500,
        **resolve_program(source, "Personalizado", version=3),
    )
    match.run_match(1 / 30)

    assert match.behaviour_errors == {}
    public = next(player for player in match.get_players_state() if player["id"] == 1)
    assert public["behaviourId"] == 500
    assert public["behaviourVersion"] == 3
    assert public["behaviourMode"] == "CUSTOM"

    match.change_behaviour(
        1, club_id=1, behaviour_id=600,
        **resolve_program(DEFAULT_CODES["Defensivo"], "Defensivo"),
    )

    profile = match.player_profiles[0]
    assert profile.behaviour_id == 600
    assert profile.behaviour_code is None
    assert profile.behaviour_mode == BehaviourMode.DEFENSIVE
    match.run_match(1 / 30)
    assert match.behaviour_errors == {}


@pytest.mark.parametrize("player_id, club_id", [(1, 2), (999, 1)])
def test_change_rejects_foreign_or_absent_player(make_match, player_id, club_id):
    match = make_match("def decide(observation):\n    return ir_a_pelota()")
    profiles = match.player_profiles

    with pytest.raises(ValueError, match="jugador"):
        match.change_behaviour(
            player_id, club_id=club_id, behaviour_id=900,
            **resolve_program(DEFAULT_CODES["Equilibrado"], "Equilibrado"),
        )

    assert match.player_profiles == profiles


def test_profile_rejects_incompatible_api_version(make_match):
    match = make_match("def decide(observation):\n    return ir_a_pelota()")

    with pytest.raises(ValueError, match="API"):
        replace(match.player_profiles[0], behaviour_api_version=API_VERSION + 1)
