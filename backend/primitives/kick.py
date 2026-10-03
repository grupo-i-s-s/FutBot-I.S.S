import pymunk
from pymunk.vec2d import Vec2d


def kick(
        player: pymunk.Body,
        ball: pymunk.Body,
        target_position: tuple[float, float],
        speed: float,
        kick_range: float
) -> bool:
    """Patea si el centro de la pelota está al alcance."""
    if speed <= 0 or kick_range < 0:
        return False

    distance_to_ball = (ball.position - player.position).length
    if distance_to_ball > kick_range:
        return False

    target = Vec2d(*target_position)
    direction = target - ball.position

    if direction.length == 0:
        return False

    ball.velocity = direction.normalized() * speed
    return True
