import logging
from dataclasses import dataclass
from math import isfinite

import pymunk

from primitives.behaviours import Action, BehaviourMode, Observation, decide
from primitives.kick import kick
from primitives.physics import Field, create_world, step
from primitives.run_to import run_to

width = 100.0
height = 60.0
goal_width = 15.0

line_up = [(10, 20), (10, 40), (30, 30), (90, 10), (90, 40), (70, 30)]
ball_pos = (50, 30)
SCORER_BY_SIDE = {"LEFT": "LOCAL", "RIGHT": "VISITANTE"}
KICK_RANGE = 2.5
KICK_COOLDOWN_SECONDS = 0.5
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlayerProfile:
    id: int
    club_id: int
    name: str
    speed: int
    power: int
    behaviour_id: int | None = None
    behaviour_mode: BehaviourMode = BehaviourMode.BALANCED


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
        self.home_positions = dict(zip(ids, self.init_players_pos, strict=True))
        self.next_kick_at: dict[int, float] = {}

        self.scorer = {"LOCAL": 0, "VISITANTE": 0}
        self.time = 0.0

    def get_players_state(self) -> list[dict]:
        return [
            {
                "id": profile.id,
                "teamId": profile.club_id,
                "name": profile.name,
                "behaviourId": profile.behaviour_id,
                "behaviourMode": profile.behaviour_mode,
                "x": float(body.position.x),
                "y": float(body.position.y),
            }
            for profile, body in zip(
                self.player_profiles, self.world.players, strict=True
            )
        ]

    def restart(self) -> None:
        self.next_kick_at.clear()
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
    ) -> Action | None:
        ball_position = self.world.ball.position
        closest_teammate = min(
            (teammate for teammate in self.player_profiles if teammate.club_id == profile.club_id),
            key=lambda teammate: (
                (self.player_bodies[teammate.id].position - ball_position).length,
                teammate.id,
            ),
        )
        observation = Observation(
            player_position=tuple(player.position),
            ball_position=tuple(ball_position),
            home_position=self.home_positions[profile.id],
            opponent_goal=target_goal,
            is_closest_teammate=closest_teammate.id == profile.id,
            ball_in_own_half=(
                ball_position.x < width / 2 if profile.club_id == self.local_team.club_id
                else ball_position.x > width / 2
            ),
            can_kick=(player.position - ball_position).length <= KICK_RANGE,
        )
        try:
            action = decide(profile.behaviour_mode, observation)
            if not isinstance(action, Action):
                raise ValueError("El comportamiento debe devolver Action.")
            x, y = action.move_target
            if not (isfinite(x) and isfinite(y) and 0 <= x <= width and 0 <= y <= height):
                raise ValueError("Destino de movimiento fuera de la cancha.")
            if action.kick_target is not None and action.kick_target != target_goal:
                raise ValueError("La patada debe apuntar al arco rival.")
            run_to(player, action.move_target, profile.speed, dt)
            return action
        except Exception:
            # Un error del programa deja quieto a ese jugador durante este paso.
            player.velocity = (0, 0)
            logger.exception("Falló el comportamiento del jugador %s", profile.id)
            return None

    def run_match(self, dt: float) -> None:
        if not isfinite(dt) or dt <= 0:
            raise ValueError("dt debe ser positivo y finito")
        shots = []
        for player, profile in (
            zip(self.world.players, self.player_profiles, strict=True)
        ):
            target_goal = (
                (width, height / 2) if profile.club_id == self.local_team.club_id
                else (0, height / 2)
            )
            action = self.run_behaviour(player, profile, target_goal, dt)
            distance = (player.position - self.world.ball.position).length
            if (action is not None and action.kick_target is not None
                    and distance <= KICK_RANGE and self.time >= self.next_kick_at.get(profile.id, 0)):
                shots.append((distance, profile.id, player, profile, action.kick_target))

        # Sólo el candidato más cercano puede patear; el ID desempata de forma estable.
        if shots:
            _, _, player, profile, target = min(shots, key=lambda shot: (shot[0], shot[1]))
            if kick(player, self.world.ball, target, profile.power / 2, KICK_RANGE):
                self.next_kick_at[profile.id] = self.time + KICK_COOLDOWN_SECONDS

        scoring_side = step(self.world, dt)
        self.time += dt

        if scoring_side is not None:
            self.scorer[SCORER_BY_SIDE[scoring_side]] += 1
            self.restart()
            print("Goles", self.scorer)
