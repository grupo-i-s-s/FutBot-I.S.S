import pymunk
from pymunk.vec2d import Vec2d


def run_to(
    player: pymunk.Body,
    target_position: tuple[float, float],
    speed: float,
    dt: float
) -> None:
    """Prepara la velocidad del jugador para el próximo step."""
    if dt <= 0:
        raise ValueError("dt debe ser positivo")
    if speed < 0:
        raise ValueError("speed no puede ser negativa")

    target = Vec2d(*target_position)
    direction = target - player.position
    distance = direction.length

    if distance == 0 or speed == 0:
        player.velocity = (0, 0)
        return

    # Reduce la velocidad cerca del destino para evitar pasarse.
    actual_speed = min(speed, distance / dt)
    player.velocity = direction.normalized() * actual_speed