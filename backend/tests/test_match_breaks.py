import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services import match_execution_service as execution
from primitives import match_simulation
from primitives.match_simulation import Match, PlayerProfile, Team


def make_team(club_id):
    return Team(
        club_id=club_id,
        name=f"Club {club_id}",
        players=tuple(
            PlayerProfile(
                id=club_id * 10 + index,
                club_id=club_id,
                name=f"Jugador {index}",
                speed=60,
                power=60,
            )
            for index in range(3)
        ),
    )


@pytest.fixture
def match(monkeypatch):
    # Estas pruebas aíslan las reglas temporales de las reglas de física.
    monkeypatch.setattr(match_simulation, "step", lambda *_: None)
    monkeypatch.setattr(Match, "run_behaviour", lambda *_: None)

    return Match(
        make_team(1),
        make_team(2),
        match_id=42,
        duration_ms=1000,
        hydration_break_ms=100,
        half_break_ms=200,
    )


def public_state(match):
    return match.snapshot(1, "now")["state"]


def test_breaks_happen_once_in_the_correct_order(match):
    match.run_match(0.25)
    state = public_state(match)

    assert state["clockMs"] == 250
    assert state["status"] == "RUNNING"
    assert state["phase"] == "HYDRATION_BREAK"
    assert state["breakIndex"] == 1
    assert state["breakRemainingMs"] == 100

    match.run_match(0.1)
    assert public_state(match)["phase"] == "PLAYING"
    assert match.time == pytest.approx(0.25)

    match.run_match(0.25)
    state = public_state(match)

    assert state["clockMs"] == 500
    assert state["phase"] == "HALF_BREAK"
    assert state["breakIndex"] == 2
    assert state["breakRemainingMs"] == 200

    match.run_match(0.2)
    assert public_state(match)["phase"] == "PLAYING"

    match.run_match(0.25)
    state = public_state(match)

    assert state["clockMs"] == 750
    assert state["phase"] == "HYDRATION_BREAK"
    assert state["breakIndex"] == 3

    match.run_match(0.1)
    match.run_match(0.25)

    assert match.finished
    assert match.time == pytest.approx(1)
    assert public_state(match)["status"] == "FINISHED"


def test_pause_freezes_clock_physics_and_score(match, monkeypatch):
    physics = Mock(return_value=None)
    monkeypatch.setattr(match_simulation, "step", physics)

    match.run_match(0.25)

    bodies = match.checkpoint()["bodies"]
    score = dict(match.scorer)
    calls = physics.call_count

    match.run_match(0.05)

    assert match.time == pytest.approx(0.25)
    assert match.checkpoint()["bodies"] == bodies
    assert match.scorer == score
    assert physics.call_count == calls
    assert public_state(match)["breakRemainingMs"] == 50


def test_checkpoint_preserves_active_break_and_remaining_time(match):
    match.run_match(0.29)

    checkpoint = json.loads(json.dumps(match.checkpoint()))
    restored = Match.from_checkpoint(checkpoint)

    assert checkpoint["version"] == 3
    assert json.loads(json.dumps(restored.checkpoint())) == checkpoint
    assert restored.snapshot(5, "now") == match.snapshot(5, "now")
    assert public_state(restored)["breakRemainingMs"] == 60

    restored.run_match(0.06)

    assert restored.time == pytest.approx(0.25)
    assert public_state(restored)["phase"] == "PLAYING"

    restored.run_match(0.25)

    assert public_state(restored)["phase"] == "HALF_BREAK"
    assert public_state(restored)["clockMs"] == 500


def test_one_tick_can_cross_multiple_boundaries(match):
    # 1 segundo de juego + 0.1 + 0.2 + 0.1 de pausas.
    match.run_match(1.4)

    assert match.finished
    assert match.time == pytest.approx(1)
    assert public_state(match)["breakRemainingMs"] == 0


def test_legacy_checkpoint_keeps_match_without_breaks(match):
    legacy = match.checkpoint()
    legacy["version"] = 1
    legacy.pop("breaks")

    restored = Match.from_checkpoint(legacy)
    restored.run_match(1)

    assert restored.finished
    assert public_state(restored)["phase"] == "PLAYING"


@pytest.mark.parametrize("duration", [-1, True, 1.5])
def test_invalid_break_duration_is_rejected(duration):
    with pytest.raises(ValueError, match="pausas"):
        Match(
            make_team(1),
            make_team(2),
            hydration_break_ms=duration,
        )


def test_executor_keeps_publishing_during_break(match, monkeypatch):
    # Pausa suficientemente larga para observar varios snapshots congelados.
    match._breaks.hydration_ms = 1000

    row = SimpleNamespace(
        sequence=0,
        status="WAITING",
        duration_ms=1000,
        runtime_state=None,
        snapshot=None,
    )

    persisted = []

    def save_progress(db, current_row, simulation, snapshot, now):
        current_row.sequence = snapshot["sequence"]
        current_row.status = simulation.status
        current_row.snapshot = snapshot
        persisted.append(snapshot)

    monkeypatch.setattr(
        execution.matches_repository,
        "get_by_id_for_update",
        lambda *_: row,
    )
    monkeypatch.setattr(
        execution.matches_repository,
        "save_progress",
        save_progress,
    )
    monkeypatch.setattr(
        execution,
        "prepare_match_start",
        lambda *args, **kwargs: match,
    )

    stop = Mock()
    stop.wait.side_effect = [False, False, False, False, True]

    result = execution._execute(Mock(), 42, None, stop)

    previous = persisted[-2]
    current = persisted[-1]

    assert previous["state"]["phase"] == "HYDRATION_BREAK"
    assert current["state"]["phase"] == "HYDRATION_BREAK"
    assert previous["state"]["clockMs"] == current["state"]["clockMs"] == 250
    assert current["sequence"] > previous["sequence"]
    assert (
        current["state"]["breakRemainingMs"]
        < previous["state"]["breakRemainingMs"]
    )
    assert result == current
