"""Nuestros límites y decisiones de movimiento; sin motor de física."""
from types import SimpleNamespace

import pytest
from pymunk.vec2d import Vec2d

from primitives.kick import kick
from primitives.run_to import run_to


def body(x, y):
    return SimpleNamespace(position=Vec2d(x, y), velocity=Vec2d(3, 4))


@pytest.mark.parametrize("distance, expected_speed", [(100, 10), (0.5, 5)])
def test_run_to_limits_speed_to_avoid_overshooting(distance, expected_speed):
    player = body(0, 0)
    run_to(player, (distance, 0), speed=10, dt=0.1)
    assert tuple(player.velocity) == (expected_speed, 0)
    assert tuple(player.position) == (0, 0)


@pytest.mark.parametrize("target, speed", [((0, 0), 10), ((10, 0), 0)])
def test_run_to_stops_at_target_or_zero_speed(target, speed):
    player = body(0, 0)
    run_to(player, target, speed, 0.1)
    assert tuple(player.velocity) == (0, 0)


@pytest.mark.parametrize("speed, dt", [(10, 0), (10, -1), (-1, 0.1)])
def test_invalid_movement_preserves_previous_velocity(speed, dt):
    player = body(0, 0)
    with pytest.raises(ValueError):
        run_to(player, (10, 0), speed, dt)
    assert tuple(player.velocity) == (3, 4)


@pytest.mark.parametrize("ball_x, target, speed, reach", [
    (2.01, (10, 0), 10, 2), (2, (10, 0), 0, 2),
    (2, (10, 0), -1, 2), (2, (10, 0), 10, -1), (2, (2, 0), 10, 2),
])
def test_invalid_or_out_of_range_kick_does_not_change_ball(ball_x, target, speed, reach):
    ball = body(ball_x, 0)
    assert kick(body(0, 0), ball, target, speed, reach) is False
    assert tuple(ball.velocity) == (3, 4)


def test_kick_at_exact_range_aims_from_ball_and_preserves_player():
    player, ball = body(0, 0), body(2, 0)
    assert kick(player, ball, (2, 10), speed=20, kick_range=2) is True
    assert tuple(ball.velocity) == (0, 20)
    assert tuple(ball.position) == (2, 0)
    assert tuple(player.velocity) == (3, 4)
