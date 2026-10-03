import pymunk
from primitives.physics import Field, create_world, step
from primitives.kick import kick
from primitives.run_to import run_to
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
        if len(local_team.players) < 3 or len(visitor_team.players) < 3:
            raise ValueError("Cada equipo necesita al menos tres jugadores activos.")

        self.player_profiles = local_team.players[:3] + visitor_team.players[:3]
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

    def restart(self):
        self.world.ball.position = self.init_ball_pos
        self.world.ball.velocity = (0, 0)
        for body, position in zip(self.world.players, self.init_players_pos):
            body.position = position
            body.velocity = (0, 0)

    def run_behaviour(self, player: pymunk.Body, profile: Player, target_goal, dt):
        run_to(player, self.world.ball.position, profile.speed, dt)
        kick(player, self.world.ball, target_goal, profile.power / 2, 15)

    def run_match(self, dt: float):
        for index, (player, profile) in enumerate(
            zip(self.world.players, self.player_profiles)
        ):
            target_goal = (width, height / 2) if index < 3 else (0, height / 2)
            self.run_behaviour(player, profile, target_goal, dt)

        next_step = step(self.world, dt)
        self.time += dt

        if next_step:
            if next_step == "RIGHT":
                self.scorer["VISITANTE"] += 1
            if next_step == "LEFT":
                self.scorer["LOCAL"] += 1
            self.restart()
            print("Goles", self.scorer)
