import pymunk
from dataclasses import dataclass

PLAYER = 0b0001
BALL = 0b0010
FIELD_WALL = 0b0100
PLAYER_WALL = 0b1000

BALL_RADIUS = 0.5
PLAYER_RADIUS = 1.5

@dataclass(frozen=True)
class Field:
    width: float
    height: float
    goal_width: float


@dataclass
class World:
    field: Field
    space: pymunk.Space
    players: list[pymunk.Body]
    ball: pymunk.Body


def create_world(
    field: Field,
    player_data: list[tuple],  # Aca tiene (posicion, strenght)
    ball_position: tuple[float, float],
) -> World:
    if field.width <= 0 or field.height <= 0 or not 0 < field.goal_width < field.height:
        raise ValueError("Dimensiones de cancha inválidas")

    space = pymunk.Space()
    space.gravity = (0, 0)
    space.damping = 0.7

    goal_top = (field.height - field.goal_width) / 2
    goal_bottom = (field.height + field.goal_width) / 2

    def add_wall(
        start: tuple[float, float],
        end: tuple[float, float],
        category: int,
        mask: int,
    ) -> None:
        wall = pymunk.Segment(space.static_body, start, end, 0.05)
        wall.elasticity = 0.8
        wall.friction = 0.5
        wall.filter = pymunk.ShapeFilter(categories=category, mask=mask)
        space.add(wall)

    # Bordes que frenan tanto a jugadores como a pelota.
    common_walls = [
        ((0, 0), (field.width, 0)),
        ((0, field.height), (field.width, field.height)),
        ((0, 0), (0, goal_top)),
        ((0, goal_bottom), (0, field.height)),
        ((field.width, 0), (field.width, goal_top)),
        ((field.width, goal_bottom), (field.width, field.height)),
    ]
    for start, end in common_walls:
        add_wall(start, end, FIELD_WALL, PLAYER | BALL)

    # Cierran la abertura del arco sólo para los jugadores.
    add_wall((0, goal_top), (0, goal_bottom), PLAYER_WALL, PLAYER)
    add_wall(
        (field.width, goal_top),
        (field.width, goal_bottom),
        PLAYER_WALL,
        PLAYER,
    )

    def add_circle(
        position: tuple[float, float],
        radius: float,
        mass: float,
        category: int,
        mask: int,
    ) -> pymunk.Body:
        moment = pymunk.moment_for_circle(mass, 0, radius)
        body = pymunk.Body(mass, moment)
        body.position = position

        shape = pymunk.Circle(body, radius)
        shape.elasticity = 0.8
        shape.friction = 0.5
        shape.filter = pymunk.ShapeFilter(categories=category, mask=mask)
        shape.collision_type = category

        space.add(body, shape)
        return body

    players = [
        add_circle(
            position,
            radius=PLAYER_RADIUS,
            mass=strenght,
            category=PLAYER,
            mask=PLAYER | BALL | FIELD_WALL | PLAYER_WALL,
        )
        for position, strenght in player_data
    ]
    ball = add_circle(
        ball_position,
        radius=BALL_RADIUS,
        mass=1,
        category=BALL,
        mask=PLAYER | FIELD_WALL,
    )

    space.on_collision(PLAYER,PLAYER, post_solve = chesting)

    return World(field=field, space=space, players=players, ball=ball)


def step(world: World, dt: float) -> str | None:
    """Avanza dt segundos y devuelve el lado del equipo que anotó.

    LEFT ataca el arco derecho (x = width); RIGHT ataca el izquierdo (x = 0).
    Devuelve None si no hubo gol.
    """
    if dt <= 0:
        raise ValueError("dt debe ser positivo")

    goal_top = (world.field.height - world.field.goal_width) / 2
    goal_bottom = (world.field.height + world.field.goal_width) / 2
    scorer = None

    # Pasos pequeños reducen el riesgo de atravesar paredes a gran velocidad.
    substeps = 4
    for _ in range(substeps):
        world.space.step(dt / substeps)

        x, y = world.ball.position
        if goal_top <= y <= goal_bottom:
            if x <= 0:
                scorer = "RIGHT"
            elif x >= world.field.width:
                scorer = "LEFT"

        if scorer is not None:
            break

    if world.ball.velocity.length > 60.0:
        world.ball.velocity = world.ball.velocity.normalized() * 60
    return scorer

#Funcion para detectar las colisiones y hacer los rebotes. Es un post_solve() de pymunk.
# NO HACE FALTA LLAMAR A LA FUNCION.
def chesting(arbiter: pymunk.Arbiter, space: pymunk.Space, data: dict) -> None:

    shape_playerA, shape_playerB = arbiter.shapes
    body_playerA = shape_playerA.body
    body_playerB = shape_playerB.body

    normal = arbiter.contact_point_set.normal

    #En mass ya teniamos la real_strength asi que el pacss tiene efecto real
    bounce_playerA = -normal * body_playerB.mass * 20
    bounce_playerB = normal * body_playerA.mass * 20

    body_playerA.apply_impulse_at_world_point(bounce_playerA, body_playerA.position)
    body_playerB.apply_impulse_at_world_point(bounce_playerB, body_playerB.position)

    return
