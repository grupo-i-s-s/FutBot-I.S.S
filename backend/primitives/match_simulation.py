from dataclasses import dataclass

import pymunk

from primitives.kick import kick
from primitives.physics import Field, create_world, step
from primitives.run_to import run_to

width = 100.0
height = 60.0
goal_width = 15.0

line_up = [(10, 20), (10, 40), (30, 30), (90, 10), (90, 40), (70, 30)]
ball_pos = (50, 30)


@dataclass(frozen=True)
class PlayerProfile:
    id: int
    club_id: int
    name: str
    speed: int
    power: int


@dataclass(frozen=True)
class Team:
    club_id: int
    name: str
    players: tuple[PlayerProfile, ...]


class Match:
    def __init__(self, local_team: Team, visitor_team: Team):
        if len(local_team.players) != 3 or len(visitor_team.players) != 3:
            raise ValueError("Cada equipo necesita exactamente tres titulares.")

        if any(player.club_id != local_team.club_id for player in local_team.players):
            raise ValueError("Hay un jugador ajeno al equipo local.")

        if any(player.club_id != visitor_team.club_id for player in visitor_team.players):
            raise ValueError("Hay un jugador ajeno al equipo visitante.")

        self.local_team = local_team
        self.visitor_team = visitor_team
        self.player_profiles = local_team.players + visitor_team.players

        ids = [profile.id for profile in self.player_profiles]
        if len(set(ids)) != len(ids):
            raise ValueError("Un jugador no puede ocupar dos lugares en la cancha.")

        self.cord = Field(width, height, goal_width)
        self.init_players_pos = tuple(line_up)
        self.init_ball_pos = ball_pos
        self.world = create_world(
            self.cord,
            list(self.init_players_pos),
            self.init_ball_pos,
        )

        # El orden de los perfiles coincide con el de los cuerpos creados.
        self.player_bodies = {
            profile.id: body
            for profile, body in zip(
                self.player_profiles, self.world.players, strict=True
            )
        }

        self.scorer = {"LOCAL": 0, "VISITANTE": 0}
        self.time = 0.0

    def get_players_state(self) -> list[dict]:
        return [
            {
                "id": profile.id,
                "teamId": profile.club_id,
                "name": profile.name,
                "x": float(body.position.x),
                "y": float(body.position.y),
            }
            for profile, body in zip(
                self.player_profiles, self.world.players, strict=True
            )
        ]

    def restart(self) -> None:
        self.world.ball.position = self.init_ball_pos
        self.world.ball.velocity = (0, 0)
        for body, position in zip(
            self.world.players, self.init_players_pos, strict=True
        ):
            body.position = position
            body.velocity = (0, 0)

    def run_behaviour(
        self,
        player: pymunk.Body,
        profile: PlayerProfile,
        target_goal: tuple[float, float],
        dt: float,
    ) -> None:
        run_to(player, self.world.ball.position, profile.speed, dt)
        kick(player, self.world.ball, target_goal, profile.power / 2, 15)

    def run_match(self, dt: float) -> None:
        for index, (player, profile) in enumerate(
            zip(self.world.players, self.player_profiles, strict=True)
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
