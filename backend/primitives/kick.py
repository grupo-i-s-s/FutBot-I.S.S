from math import hypot

from primitives.physics import Body


def kick(
    player: Body,
    ball: Body,
    target_position: tuple[float, float],
    speed: float,
    kick_range: float,
) -> bool:
    """Da velocidad a la pelota si está al alcance del jugador."""
    if speed <= 0 or kick_range < 0:
        return False

    distance_to_ball = hypot(ball.x - player.x, ball.y - player.y)
    if distance_to_ball > kick_range:
        return False

    dx = target_position[0] - ball.x
    dy = target_position[1] - ball.y
    distance_to_target = hypot(dx, dy)

    if distance_to_target == 0:
        return False

    ball.vx = dx / distance_to_target * speed
    ball.vy = dy / distance_to_target * speed
    return True