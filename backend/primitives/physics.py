from dataclasses import dataclass


@dataclass
class Body:
    x: float
    y: float
    radius: float
    vx: float = 0.0
    vy: float = 0.0


@dataclass(frozen=True)
class Field:
    width: float
    height: float
    goal_width: float


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def step(
    field: Field,
    players: list[Body],
    ball: Body,
    dt: float,
) -> str | None:
    """Avanza dt segundos. Devuelve el equipo que anotó, o None."""
    if dt <= 0:
        raise ValueError("dt debe ser positivo")

    # Los jugadores reciben una orden nueva en cada paso.
    for player in players:
        player.x = clamp(
            player.x + player.vx * dt,
            player.radius,
            field.width - player.radius,
        )
        player.y = clamp(
            player.y + player.vy * dt,
            player.radius,
            field.height - player.radius,
        )
        player.vx = 0.0
        player.vy = 0.0

    # La pelota conserva su velocidad entre pasos.
    ball.x += ball.vx * dt
    ball.y += ball.vy * dt

    # Rebote en los lados superior e inferior.
    rebound = 0.8
    if ball.y < ball.radius:
        ball.y = ball.radius
        ball.vy = abs(ball.vy) * rebound
    elif ball.y > field.height - ball.radius:
        ball.y = field.height - ball.radius
        ball.vy = -abs(ball.vy) * rebound

    goal_top = (field.height - field.goal_width) / 2
    goal_bottom = (field.height + field.goal_width) / 2
    inside_goal = goal_top <= ball.y <= goal_bottom

    if inside_goal:
        if ball.x <= 0:
            return "RIGHT"  # El equipo de la derecha ataca hacia la izquierda.
        if ball.x >= field.width:
            return "LEFT"
    else:
        # Fuera de la abertura del arco, los laterales son paredes.
        if ball.x < ball.radius:
            ball.x = ball.radius
            ball.vx = abs(ball.vx) * rebound
        elif ball.x > field.width - ball.radius:
            ball.x = field.width - ball.radius
            ball.vx = -abs(ball.vx) * rebound

    # Rozamiento sencillo, expresado por segundo.
    friction = max(0.0, 1.0 - 0.8 * dt)
    ball.vx *= friction
    ball.vy *= friction

    return None