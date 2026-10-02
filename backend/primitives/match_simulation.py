import pymunk
from primitives.physics import Field, create_world, step
from primitives.kick import kick
from primitives.run_to import run_to
from app.repository.user_repository import get_club
from app.repository.player_repository import get_by_id
from app.models.player_model import Player

width = 100.00
height = 60.0
goal_width = 15.0

line_up = [(10, 20), (10, 40), (30, 30), (90, 10), (90, 40), (70, 30)]
ball_pos = (50, 30)


class Team:
    def __init__(self, name, players: list[Player]):
        self.name = name
        self.players = players


class Partido:
    def __init__(self, local_team, visitor_team):
        self.cord = Field(width, height, goal_width)
        self.init_players_pos = line_up
        self.init_ball_pos = ball_pos

        # creamos la cancha, los jugadores y la pelota
        self.world = create_world(
            self.cord, self.init_players_pos, self.init_ball_pos
        )  # Esto me devuelve un world que tiene cancha, espacio, pelota y lista de jugadores

        self.local_team = local_team
        self.visitor_team = visitor_team

        self.scorer = {"LOCAL": 0, "VISITANTE": 0}
        self.time = 0.00

    def restart(
        self,
    ):  # Falta agregar logica de restaurar player pos inicial, a lo mejor es mejor el caos
        self.world.ball.position = self.init_ball_pos
        self.world.ball.velocity = (0, 0)

    def run_behaviour(self, player: pymunk.Body, dt):
        run_to(player, self.world.ball.position, 50, dt)
        kick(player, self.world.ball, (100.0, 30), 30, 15)

    def run_match(self, dt: float):
        ball_pos = self.world.ball.position

        for player in (
            self.world.players[:3] + self.world.players[-3:]
        ):  # Me recorre los primeros 3 playes y despues los ultimos 3. Asegurar cargar primero un equipo y despues otro
            self.run_behaviour(player, dt)

        next_step = step(self.world, dt)
        self.time += dt

        if next_step:
            if next_step == "RIGHT":
                self.scorer["LOCAL"] += 1
            if next_step == "LEFT":
                self.scorer["VISITANTE"] += 1
            self.restart()
            print("Goles", self.scorer)
