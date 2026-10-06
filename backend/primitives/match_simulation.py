import logging
import pymunk
from dataclasses import asdict, dataclass
from math import isfinite

from primitives.behaviours import Action, BehaviourMode, Observation, decide
from primitives.kick import kick
from primitives.physics import Field, create_world, step
from primitives.run_to import run_to

width = 100.0
height = 60.0
goal_width = 15.0

line_up = [(18, 18), (18, 42), (30, 30), (82, 18), (82, 42), (70, 30)]
ball_pos = (50, 30)
SCORER_BY_SIDE = {"LEFT": "LOCAL", "RIGHT": "VISITANTE"}
KICK_RANGE = 2.5
KICK_COOLDOWN_SECONDS = 0.5
# Los atributos 20–100 se traducen a unidades de cancha por segundo.
# La pelota debe viajar más rápido que los jugadores para que un remate se libere.
PLAYER_BASE_SPEED = 8.0
PLAYER_SPEED_FACTOR = 0.15
SHOT_BASE_SPEED = 40.0
SHOT_POWER_FACTOR = 0.6
DEFAULT_DURATION_MS = 300_000
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
    def __init__(
            self, local_team: Team, visitor_team: Team,
            *, match_id: int | None = None, duration_ms: int = DEFAULT_DURATION_MS,
    ):
        if type(duration_ms) is not int or duration_ms <= 0:
            raise ValueError("La duración debe ser un entero positivo en milisegundos.")
        self.match_id = match_id
        self.duration_ms = duration_ms
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
        self.scorer = {"LOCAL": 0, "VISITANTE": 0}
        self.world = create_world(
            self.cord,
            self.kickoff_positions(),
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

        self.time = 0.0

    @property
    def finished(self) -> bool:
        return self.time >= self.duration_ms / 1000

    @property
    def status(self) -> str:
        return "FINISHED" if self.finished else "RUNNING"

    def snapshot(self, sequence: int, sent_at: str) -> dict:
        """Estado público completo; no contiene cuerpos ni objetos de Pymunk."""
        return {
            "schemaVersion": 1, "type": "match.snapshot", "matchId": self.match_id,
            "sequence": sequence, "sentAt": sent_at,
            "state": {
                "status": self.status,
                "clockMs": min(round(self.time * 1000), self.duration_ms),
                "durationMs": self.duration_ms,
                "field": {"width": width, "height": height, "goalWidth": goal_width},
                "teams": [
                    {"id": team.club_id, "name": team.name, "side": side,
                     "score": self.scorer[score_key], "color": color}
                    for team, side, score_key, color in (
                        (self.local_team, "LEFT", "LOCAL", "#2563eb"),
                        (self.visitor_team, "RIGHT", "VISITANTE", "#dc2626"),
                    )
                ],
                "players": [{**player, "radius": 1.4} for player in self.get_players_state()],
                "ball": {"x": float(self.world.ball.position.x),
                         "y": float(self.world.ball.position.y), "radius": 0.5},
            },
        }

    def checkpoint(self) -> dict:
        """Estado privado para retomar desde el último snapshot confirmado."""
        return {
            "version": 1, "match_id": self.match_id, "duration_ms": self.duration_ms,
            "local_team": asdict(self.local_team), "visitor_team": asdict(self.visitor_team),
            "time": self.time, "scorer": dict(self.scorer),
            "next_kick_at": {str(key): value for key, value in self.next_kick_at.items()},
            "bodies": [
                {"position": list(body.position), "velocity": list(body.velocity),
                 "angle": body.angle, "angular_velocity": body.angular_velocity}
                for body in (*self.world.players, self.world.ball)
            ],
        }

    @classmethod
    def from_checkpoint(cls, data: dict) -> "Match":
        if data["version"] != 1:
            raise ValueError("Versión de checkpoint incompatible.")

        def team_from_data(team: dict) -> Team:
            return Team(team["club_id"], team["name"], tuple(
                PlayerProfile(**{**player, "behaviour_mode": BehaviourMode(player["behaviour_mode"])})
                for player in team["players"]
            ))

        match = cls(
            team_from_data(data["local_team"]), team_from_data(data["visitor_team"]),
            match_id=data["match_id"], duration_ms=data["duration_ms"],
        )
        match.time = data["time"]
        match.scorer = dict(data["scorer"])
        match.next_kick_at = {int(key): value for key, value in data["next_kick_at"].items()}
        for body, state in zip((*match.world.players, match.world.ball), data["bodies"], strict=True):
            body.position = state["position"]
            body.velocity = state["velocity"]
            body.angle = state["angle"]
            body.angular_velocity = state["angular_velocity"]
        match.world.space.reindex_shapes_for_body(match.world.ball)
        for body in match.world.players:
            match.world.space.reindex_shapes_for_body(body)
        return match

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

    def kickoff_positions(self) -> list[tuple[float, float]]:
        positions = list(self.init_players_pos)
        # El saque inicial es local; luego alternamos para romper la simetría.
        local_kickoff = sum(self.scorer.values()) % 2 == 0
        positions[2 if local_kickoff else 5] = (42 if local_kickoff else 58, 30)
        return positions

    def restart(self) -> None:
        self.next_kick_at.clear()
        self.world.ball.position = self.init_ball_pos
        self.world.ball.velocity = (0, 0)
        for body, position in zip(
                self.world.players, self.kickoff_positions(), strict=True
        ):
            body.position = position
            body.velocity = (0, 0)
        for body in (*self.world.players, self.world.ball):
            body.angle = 0
            body.angular_velocity = 0
            self.world.space.reindex_shapes_for_body(body)

    def run_behaviour(
            self,
            player: pymunk.Body,
            profile: PlayerProfile,
            target_goal: tuple[float, float],
            dt: float,
    ) -> Action | None:
        ball_position = self.world.ball.position
        ball_in_own_half = (
            ball_position.x <= width / 2 if profile.club_id == self.local_team.club_id
            else ball_position.x >= width / 2
        )
        teammates = [teammate for teammate in self.player_profiles
                     if teammate.club_id == profile.club_id]
        chasers = [teammate for teammate in teammates
                   if ball_in_own_half or teammate.behaviour_mode != BehaviourMode.DEFENSIVE]
        closest_teammate = min(
            chasers or teammates,
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
            ball_in_own_half=ball_in_own_half,
            can_kick=(player.position - ball_position).length <= KICK_RANGE,
            field_size=(width, height),
            goal_width=goal_width,
        )
        try:
            action = decide(profile.behaviour_mode, observation)
            if not isinstance(action, Action):
                raise ValueError("El comportamiento debe devolver Action.")
            x, y = action.move_target
            if not (isfinite(x) and isfinite(y) and 0 <= x <= width and 0 <= y <= height):
                raise ValueError("Destino de movimiento fuera de la cancha.")
            if action.kick_target is not None:
                shot_x, shot_y = action.kick_target
                if not (isfinite(shot_x) and isfinite(shot_y)
                        and shot_x == target_goal[0]
                        and abs(shot_y - target_goal[1]) <= goal_width / 2 - 1):
                    raise ValueError("La patada debe apuntar dentro del arco rival.")
            speed = PLAYER_BASE_SPEED + profile.speed * PLAYER_SPEED_FACTOR
            run_to(player, action.move_target, speed, dt)
            return action
        except Exception:
            # Un error del programa deja quieto a ese jugador durante este paso.
            player.velocity = (0, 0)
            logger.exception("Falló el comportamiento del jugador %s", profile.id)
            return None

    def run_match(self, dt: float) -> None:
        if not isfinite(dt) or dt <= 0:
            raise ValueError("dt debe ser positivo y finito")
        if self.finished:
            return
        duration = self.duration_ms / 1000
        dt = min(dt, duration - self.time)
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
            shot_speed = SHOT_BASE_SPEED + profile.power * SHOT_POWER_FACTOR
            if kick(player, self.world.ball, target, shot_speed, KICK_RANGE):
                self.next_kick_at[profile.id] = self.time + KICK_COOLDOWN_SECONDS

        scoring_side = step(self.world, dt)
        self.time = min(duration, self.time + dt)
        # Evita un paso adicional por error de acumulación de floats.
        if duration - self.time < 1e-9:
            self.time = duration

        if scoring_side is not None:
            self.scorer[SCORER_BY_SIDE[scoring_side]] += 1
            self.restart()
            logger.info("Partido %s: goles %s", self.match_id, self.scorer)
