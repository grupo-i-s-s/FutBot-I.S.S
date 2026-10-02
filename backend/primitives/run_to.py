from primitives.physics import Body


def run_to(
    player: Body,
    target_position: tuple[float, float],
    speed: float,
    dt: float,
) -> None:
    """Prepara el movimiento del jugador para el próximo paso."""
    if dt <= 0:
        raise ValueError("dt debe ser positivo")
    if speed < 0:
        raise ValueError("speed no puede ser negativa")

    dx = target_position[0] - player.x
    dy = target_position[1] - player.y
    distance = hypot(dx, dy)

    if distance == 0 or speed == 0:
        player.vx = 0.0
        player.vy = 0.0
        return

    # Cerca del destino, reduce la velocidad para no pasarse.
    actual_speed = min(speed, distance / dt)
    player.vx = dx / distance * actual_speed
    player.vy = dy / distance * actual_speed