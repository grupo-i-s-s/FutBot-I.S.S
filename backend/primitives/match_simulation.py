import logging
import pymunk
from dataclasses import asdict, dataclass, field, replace
from math import isfinite
import random

from primitives.behaviours import Action, BehaviourMode, Observation, decide
from primitives.formations import FORMATIONS
from primitives.physics import PLAYER_RADIUS, BALL_RADIUS
from primitives.kick import kick
from primitives.physics import Field, create_world, step
from primitives.run_to import run_to
from primitives.match_breaks import DEFAULT_HALF_BREAK_MS, DEFAULT_HYDRATION_BREAK_MS, MatchBreaks

from primitives.behaviour_api.actions import Command
from primitives.behaviour_api.context import snapshot_from_match
from primitives.behaviour_api.registry import API_VERSION
from primitives.behaviour_api.runtime import (
    BehaviourRuntime,
    BehaviourRuntimeError,
    BehaviourWorkerDead,
)
from primitives.behaviour_api.validation import (
    ExecutionError,
    normalize_action,
    validate_static,
)
from primitives.dt_behaviour import DtObservation, resolve_dt_behaviour, dt_decide

width = 100.0
height = 60.0
goal_width = 15.0

ball_pos = (50, 30)
KICK_RANGE = 2.5
KICK_COOLDOWN_SECONDS = 0.5
# Los atributos 20–100 se traducen a unidades de cancha por segundo.
# La pelota debe viajar más rápido que los jugadores para que un remate se libere.
SHOT_BASE_SPEED = 40.0
SHOT_POWER_FACTOR = 0.6
DEFAULT_DURATION_MS = 300_000
logger = logging.getLogger(__name__)


def _finite_number(value: object) -> bool:
    return type(value) in (int, float) and isfinite(value)


@dataclass(frozen=True)
class PlayerProfile:
    id: int
    club_id: int
    name: str
    speed: int
    power: int
    agility: int
    strength: int
    control: int
    behaviour_id: int | None = None
    behaviour_mode: BehaviourMode = BehaviourMode.BALANCED

    behaviour_code: str | None = None
    behaviour_version: int = 1
    behaviour_api_version: int = API_VERSION

    def __post_init__(self):
        if type(self.behaviour_version) is not int or self.behaviour_version < 1:
            raise ValueError("Versión de comportamiento inválida.")

        if type(self.behaviour_api_version) is not int or self.behaviour_api_version != API_VERSION:
            raise ValueError("Versión de API de comportamientos incompatible.")

        if self.behaviour_code is not None:
            diagnostics = validate_static(self.behaviour_code)

            if diagnostics:
                raise ValueError(diagnostics[0]["message"])

    #Esto me srive para definir el significado de control en un jugador. 100pts son 2mts y 20 son 0.4mts
    @property
    def kick_range(self) -> float:
        return PLAYER_RADIUS + BALL_RADIUS + ((self.control * 2)/100)

    #Esto me define la velocidad real del jugador. 100pts son 28,8m/s + 4 de base_speed, 20pts son 5,76m/s + 4
    @property
    def real_speed(self) -> float:
        return ((self.speed * 28.8) / 100) + 4.0

    #Esto define la strength real del jugador. 100pts son 84kg por R9, 20pts son 16,8kg. Se escalan a 0.2 por el motor
    @property
    def real_strength(self) -> float:
        return (self.strength * 84 / 100)

    @property
    def real_agility(self) -> float:
        return (100 / self.agility)


@dataclass(frozen=True)
class Team:
    club_id: int
    name: str
    players: tuple[PlayerProfile, ...]
    formation_id: int = 1
    formation_positions: tuple[tuple[float, float], ...] | None = None
    avatar: str | None = None
    substitutes: tuple[PlayerProfile, ...] = ()

    dt_active: bool = False
    dt_code: str | None = None
    dt_default_behaviours: dict[BehaviourMode, tuple[int, int]] = field(default_factory=dict)

    def __post_init__(self):
        positions = self.formation_positions

        if positions is None:
            try:
                positions = FORMATIONS[self.formation_id].positions
            except KeyError as exc:
                raise ValueError("La formación seleccionada no existe.") from exc

        positions = tuple(
            (float(x), float(y))
            for x, y in positions
        )

        if len(positions) != 3 or any(
            not (0 < x < 0.5 and 0 < y < 1)
            for x, y in positions
        ):
            raise ValueError(
                "La formación necesita tres posiciones válidas en su mitad."
            )

        object.__setattr__(self, "formation_positions", positions)

        if type(self.dt_active) is not bool or (self.dt_code is not None and type(self.dt_code) is not str):
            raise ValueError("Configuración de DT inválida.")
        if not isinstance(self.dt_default_behaviours, dict):
            raise ValueError("Catálogo de comportamientos del DT inválido.")

        defaults = {
            BehaviourMode(mode): tuple(program)
            for mode, program in self.dt_default_behaviours.items()
        }
        if any(len(program) != 2 or any(type(value) is not int or value <= 0 for value in program)
               for program in defaults.values()):
            raise ValueError("Identificador o versión de comportamiento del DT inválidos.")
        object.__setattr__(self, "dt_default_behaviours", defaults)


class Match:
    def __init__(
            self, local_team: Team, visitor_team: Team,
            *, match_id: int | None = None,
            duration_ms: int = DEFAULT_DURATION_MS,
            hydration_break_ms: int = DEFAULT_HYDRATION_BREAK_MS,
            half_break_ms: int = DEFAULT_HALF_BREAK_MS,
    ):
        if type(duration_ms) is not int or duration_ms <= 0:
            raise ValueError("La duración debe ser un entero positivo en milisegundos.")
        self.match_id = match_id
        self.duration_ms = duration_ms
        if len(local_team.players) != 3 or len(visitor_team.players) != 3:
            raise ValueError("Cada equipo necesita exactamente tres titulares.")

        if any(player.club_id != local_team.club_id for player in local_team.players):
            raise ValueError("Hay un jugador ajeno al equipo local.")

        if any(
            player.club_id != visitor_team.club_id for player in visitor_team.players
        ):
            raise ValueError("Hay un jugador ajeno al equipo visitante.")

        self.local_team = local_team
        self.visitor_team = visitor_team
        self.sides_swapped = False
        self.kickoff_club_id = local_team.club_id
        self.player_profiles = local_team.players + visitor_team.players

        ids = [profile.id for profile in self.player_profiles]
        if len(set(ids)) != len(ids):
            raise ValueError("Un jugador no puede ocupar dos lugares en la cancha.")

        self.cord = Field(width, height, goal_width)
        local_positions = tuple(
            (x * width, y * height)
            for x, y in local_team.formation_positions
        )

        visitor_positions = tuple(
            ((1 - x) * width, y * height)
            for x, y in visitor_team.formation_positions
        )

        self.init_players_pos = local_positions + visitor_positions
        self.init_ball_pos = ball_pos
        self.scorer = {"LOCAL": 0, "VISITANTE": 0}

        # Aca uso el strength de los jugadores para pasarselos cuando instanciemos el mundo, me devuelve [(posicion, strenght)]
        players_data = []
        for profile, position in zip(
            self.player_profiles, self.kickoff_positions(), strict=True
        ):
            players_data.append((position, profile.real_strength))

        # Ahora le paso esa lista para instanciar el mundo
        self.world = create_world(
            self.cord,
            players_data,
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

        self._behaviour_runtime: BehaviourRuntime | None = None
        self.behaviour_errors: dict[int, dict] = {}
        self._dt_runtime: BehaviourRuntime | None = None
        self.dt_errors: dict[int, str] = {}
        self._dt_pauses: dict[int, int] = {}

        self._breaks = MatchBreaks(
            hydration_ms=hydration_break_ms,
            half_ms=half_break_ms,
        )
        self.on_pause = None
        self.substitution_pauses: set[tuple[int, int]] = set()
        self.substitution_events: list[dict] = []

    @property
    def paused(self) -> bool:
        return self._breaks.paused

    @property
    def pause_index(self) -> int:
        return self._breaks.next_index

    def substitute(self, club_id: int, out_player_id: int, in_player_id: int) -> None:
        if not self.paused:
            raise ValueError("PAUSE_CLOSED")
        key = (club_id, self.pause_index)
        if key in self.substitution_pauses:
            raise ValueError("SUBSTITUTION_QUOTA_USED")
        team = next((t for t in (self.local_team, self.visitor_team) if t.club_id == club_id), None)
        outgoing = next((p for p in team.players if p.id == out_player_id), None) if team else None
        incoming = next((p for p in team.substitutes if p.id == in_player_id), None) if team else None
        if outgoing is None or incoming is None or incoming.club_id != club_id or in_player_id in self.player_bodies:
            raise ValueError("SUBSTITUTION_INVALID_PLAYERS")

        updated = replace(
            team,
            players=tuple(incoming if p.id == out_player_id else p for p in team.players),
            substitutes=tuple(outgoing if p.id == in_player_id else p for p in team.substitutes),
        )
        if club_id == self.local_team.club_id:
            self.local_team = updated
        else:
            self.visitor_team = updated
        self.player_profiles = self.local_team.players + self.visitor_team.players
        # Reutilizar el cuerpo conserva su posición y evita duplicar objetos físicos.
        body = self.player_bodies.pop(out_player_id)
        body.mass = incoming.real_strength
        body.moment = pymunk.moment_for_circle(body.mass, 0, PLAYER_RADIUS)
        body.velocity = (0, 0)
        body.angular_velocity = 0
        body.force = (0, 0)
        body.torque = 0
        self.player_bodies[in_player_id] = body
        self.home_positions[in_player_id] = self.home_positions.pop(out_player_id)
        for player_id in (out_player_id, in_player_id):
            self.next_kick_at.pop(player_id, None)
            self.behaviour_errors.pop(player_id, None)
        self._close_player_runtime()
        self.substitution_pauses.add(key)

    def team_side(self, club_id: int) -> str:
        if club_id not in (self.local_team.club_id, self.visitor_team.club_id):
            raise ValueError("El club no participa del partido.")
        on_left = (club_id == self.local_team.club_id) != self.sides_swapped
        return "LEFT" if on_left else "RIGHT"

    def _set_sides(self, swapped: bool) -> None:
        if self.sides_swapped == swapped:
            return
        self.sides_swapped = swapped
        self.init_players_pos = tuple(
            (width - x, y) for x, y in self.init_players_pos
        )
        self.home_positions = dict(zip(
            (profile.id for profile in self.player_profiles),
            self.init_players_pos,
            strict=True,
        ))

    def start_second_half(self) -> None:
        """Cambia de arco y rearma la formación una sola vez por partido."""
        if self.sides_swapped:
            return
        self._set_sides(True)
        self.restart(kickoff_club_id=self.visitor_team.club_id)

    @property
    def finished(self) -> bool:
        return self.time >= self.duration_ms / 1000

    @property
    def status(self) -> str:
        return "FINISHED" if self.finished else "RUNNING"

    def snapshot(self, sequence: int, sent_at: str) -> dict:
        """Estado público completo; no contiene cuerpos ni objetos de Pymunk."""
        next_pause = next((i + 1 for i in range(self.pause_index, 3)
                           if self._breaks.durations_ms[i] > 0), None) if not self.finished else None
        quota_pause = self.pause_index if self.paused else next_pause
        return {
            "schemaVersion": 1,
            "type": "match.snapshot",
            "matchId": self.match_id,
            "sequence": sequence,
            "sentAt": sent_at,
            "state": {
                "status": self.status,
                "clockMs": min(round(self.time * 1000), self.duration_ms),
                "durationMs": self.duration_ms,
                "period": 2 if self.sides_swapped else 1,
                **self._breaks.public_state(),
                "events": [dict(event) for event in self.substitution_events],
                "nextPause": {"pauseId": f"{self.match_id}:{next_pause}", "number": next_pause}
                if next_pause is not None else None,
                "lineups": [
                    {
                        "clubId": team.club_id,
                        "starters": [{"playerId": p.id, "name": p.name} for p in team.players],
                        "substitutes": [{"playerId": p.id, "name": p.name} for p in team.substitutes],
                        "remainingSubstitutions": int(quota_pause is not None
                                                      and (team.club_id, quota_pause) not in self.substitution_pauses),
                        "pendingSubstitution": None,
                    }
                    for team in (self.local_team, self.visitor_team)
                ],
                "field": {"width": width, "height": height, "goalWidth": goal_width},
                "teams": [
                    {"id": team.club_id, "name": team.name, "avatar": team.avatar,
                     "side": self.team_side(team.club_id),
                     "score": self.scorer[score_key], "color": color,
                     "dtActive": team.dt_active, "dtConfigured": bool(team.dt_code),
                     "dtError": self.dt_errors.get(team.club_id)}
                    for team, score_key, color in (
                        (self.local_team, "LOCAL", "#2563eb"),
                        (self.visitor_team, "VISITANTE", "#dc2626"),
                    )
                ],
                "players": [
                    {**player, "radius": PLAYER_RADIUS} for player in self.get_players_state()
                ],
                "ball": {
                    "x": float(self.world.ball.position.x),
                    "y": float(self.world.ball.position.y),
                    "radius": BALL_RADIUS,
                },
            },
        }

    def checkpoint(self) -> dict:
        """Estado privado para retomar desde el último snapshot confirmado."""
        return {
            "version": 6,
            "match_id": self.match_id,
            "duration_ms": self.duration_ms,
            "local_team": asdict(self.local_team),
            "visitor_team": asdict(self.visitor_team),
            "time": self.time,
            "scorer": dict(self.scorer),
            "breaks": self._breaks.checkpoint(),
            "substitution_pauses": [list(key) for key in sorted(self.substitution_pauses)],
            "substitution_events": [dict(event) for event in self.substitution_events],
            "dt_pauses": {str(club_id): pause for club_id, pause in self._dt_pauses.items()},
            "dt_errors": {str(club_id): error for club_id, error in self.dt_errors.items()},
            "sides_swapped": self.sides_swapped,
            "kickoff_club_id": self.kickoff_club_id,
            "next_kick_at": {
                str(key): value
                for key, value in self.next_kick_at.items()
            },
            "bodies": [
                {
                    "position": list(body.position),
                    "velocity": list(body.velocity),
                    "angle": body.angle,
                    "angular_velocity": body.angular_velocity,
                }
                for body in (*self.world.players, self.world.ball)
            ],
            "behaviour_errors": {
                str(player_id): error
                for player_id, error in self.behaviour_errors.items()
            },
        }

    @classmethod
    def from_checkpoint(cls, data: object) -> "Match":
        if not isinstance(data, dict):
            raise ValueError("El checkpoint debe ser un objeto.")
        version = data.get("version")

        if type(version) is not int or version not in (1, 2, 3, 4, 5, 6):
            raise ValueError("Versión de checkpoint incompatible.")

        def player_from_data(player: dict) -> PlayerProfile:
            profile = PlayerProfile(**{**player, "behaviour_mode": BehaviourMode(player["behaviour_mode"])})
            attributes = (profile.speed, profile.power, profile.agility, profile.strength, profile.control)
            if (
                not all(map(_finite_number, attributes))
                or profile.agility <= 0
                or not 0 < profile.real_strength < float("inf")
            ):
                raise ValueError("Atributos inválidos en el checkpoint del jugador.")
            return profile

        def team_from_data(team: dict) -> Team:
            return Team(
                club_id=team["club_id"],
                name=team["name"],
                players=tuple(player_from_data(player) for player in team["players"]),
                formation_id=team.get("formation_id", 1),
                formation_positions=team.get("formation_positions"),
                avatar=team.get("avatar"),
                substitutes=tuple(player_from_data(player) for player in team.get("substitutes", [])),
                dt_active=team.get("dt_active", False),
                dt_code=team.get("dt_code"),
                dt_default_behaviours=team.get("dt_default_behaviours", {}),
            )

        match = cls(
            team_from_data(data["local_team"]),
            team_from_data(data["visitor_team"]),
            match_id=data["match_id"],
            duration_ms=data["duration_ms"],
        )

        if "breaks" in data:
            match._breaks = MatchBreaks(**data["breaks"])
        elif version < 3:
            # v2 también fue usado por formaciones, sin información de pausas.
            match._breaks = MatchBreaks(
                hydration_ms=0,
                half_ms=0,
                next_index=3,
            )
        else:
            raise ValueError("Falta el estado de pausas del partido.")

        elapsed = data["time"]
        if not _finite_number(elapsed) or not 0 <= elapsed <= match.duration_ms / 1000:
            raise ValueError("Reloj inválido en el checkpoint.")
        scores = dict(data["scorer"])
        if scores.keys() != match.scorer.keys() or any(
            type(score) is not int or score < 0 for score in scores.values()
        ):
            raise ValueError("Marcador inválido en el checkpoint.")
        match.time = elapsed
        match.scorer = scores
        swapped = data.get("sides_swapped", False)
        if type(swapped) is not bool:
            raise ValueError("Estado de cambio de arco inválido.")
        match._set_sides(swapped)
        match.kickoff_club_id = data.get(
            "kickoff_club_id",
            match.local_team.club_id if sum(match.scorer.values()) % 2 == 0
            else match.visitor_team.club_id,
        )
        match.team_side(match.kickoff_club_id)
        match.next_kick_at = {
            int(key): value for key, value in data["next_kick_at"].items()
        }
        if any(not _finite_number(value) or value < 0 for value in match.next_kick_at.values()):
            raise ValueError("Tiempo de próximo remate inválido en el checkpoint.")
        for body, state in zip(
            (*match.world.players, match.world.ball), data["bodies"], strict=True
        ):
            position, velocity = state["position"], state["velocity"]
            angle, angular_velocity = state["angle"], state["angular_velocity"]
            for vector in (position, velocity):
                if (
                    not isinstance(vector, (list, tuple)) or len(vector) != 2
                    or not all(map(_finite_number, vector))
                ):
                    raise ValueError("Posición o velocidad inválida en el checkpoint.")
            if not _finite_number(angle) or not _finite_number(angular_velocity):
                raise ValueError("Rotación inválida en el checkpoint.")
            body.position = position
            body.velocity = velocity
            body.angle = angle
            body.angular_velocity = angular_velocity

        match.world.space.reindex_shapes_for_body(match.world.ball)

        for body in match.world.players:
            match.world.space.reindex_shapes_for_body(body)

        errors = data.get("behaviour_errors", {})

        if type(errors) is not dict:
            raise ValueError(
                "Estado de errores inválido."
            )

        custom_ids = {
            profile.id
            for profile in match.player_profiles
            if profile.behaviour_code is not None
        }

        restored_errors = {}

        for player_id, error in errors.items():
            player_id = int(player_id)

            if (
                    player_id not in custom_ids
                    or type(error) is not dict
                    or type(error.get("code")) is not str
                    or type(error.get("message")) is not str
            ):
                raise ValueError(
                    "Estado de errores inválido."
                )

            restored_errors[player_id] = error

        match.behaviour_errors = restored_errors

        valid_clubs = {match.local_team.club_id, match.visitor_team.club_id}
        if version >= 6:
            pauses = data["substitution_pauses"]
            if any(len(key) != 2 or key[0] not in valid_clubs or key[1] not in (1, 2, 3) for key in pauses):
                raise ValueError("Cuota de sustituciones inválida.")
            match.substitution_pauses = {tuple(key) for key in pauses}
            events = data["substitution_events"]
            if not isinstance(events, list) or any(not isinstance(e, dict) or not e.get("eventId") for e in events):
                raise ValueError("Eventos de sustitución inválidos.")
            match.substitution_events = [dict(event) for event in events]

        dt_pauses = data.get("dt_pauses", {})
        dt_errors = data.get("dt_errors", {})
        if not isinstance(dt_pauses, dict) or not isinstance(dt_errors, dict):
            raise ValueError("Estado del DT inválido.")
        match._dt_pauses = {int(club_id): pause for club_id, pause in dt_pauses.items()}
        match.dt_errors = {int(club_id): error for club_id, error in dt_errors.items()}
        if (
            (match._dt_pauses.keys() | match.dt_errors.keys()) - valid_clubs
            or any(type(pause) is not int or not 1 <= pause <= match.pause_index for pause in match._dt_pauses.values())
            or any(type(error) is not str for error in match.dt_errors.values())
        ):
            raise ValueError("Estado del DT inválido.")

        if version < 4 and custom_ids:
            raise ValueError(
                "El checkpoint no admite comportamientos custom."
            )

        return match

    def get_players_state(self) -> list[dict]:
        return [
            {
                "id": profile.id,
                "teamId": profile.club_id,
                "name": profile.name,
                "behaviourId": profile.behaviour_id,
                "behaviourMode": "CUSTOM" if profile.behaviour_code is not None else profile.behaviour_mode,
                "behaviourVersion": profile.behaviour_version,
                "x": float(body.position.x),
                "y": float(body.position.y),
            }
            for profile, body in zip(
                self.player_profiles, self.world.players, strict=True
            )
        ]

    def kickoff_positions(self) -> list[tuple[float, float]]:
        positions = list(self.init_players_pos)
        local_kickoff = self.kickoff_club_id == self.local_team.club_id
        side = self.team_side(self.kickoff_club_id)
        positions[2 if local_kickoff else 5] = (42 if side == "LEFT" else 58, 30)
        return positions

    def restart(self, *, kickoff_club_id: int | None = None) -> None:
        self.kickoff_club_id = kickoff_club_id if kickoff_club_id is not None else (
            self.local_team.club_id if sum(self.scorer.values()) % 2 == 0
            else self.visitor_team.club_id
        )
        self.team_side(self.kickoff_club_id)
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
        apply_movement: bool = True
    ) -> Action | None:
        ball_position = self.world.ball.position
        ball_in_own_half = (
            ball_position.x <= width / 2 if self.team_side(profile.club_id) == "LEFT"
            else ball_position.x >= width / 2
        )
        teammates = [
            teammate
            for teammate in self.player_profiles
            if teammate.club_id == profile.club_id
        ]
        chasers = [
            teammate
            for teammate in teammates
            if ball_in_own_half or teammate.behaviour_mode != BehaviourMode.DEFENSIVE
        ]
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
            can_kick=(player.position - ball_position).length <= profile.kick_range,
            field_size=(width, height),
            goal_width=goal_width,
        )
        try:
            action = decide(profile.behaviour_mode, observation)
            if not isinstance(action, Action):
                raise ValueError("El comportamiento debe devolver Action.")
            x, y = action.move_target
            if not (
                isfinite(x) and isfinite(y) and 0 <= x <= width and 0 <= y <= height
            ):
                raise ValueError("Destino de movimiento fuera de la cancha.")
            if action.kick_target is not None:
                shot_x, shot_y = action.kick_target
                if not (
                    isfinite(shot_x)
                    and isfinite(shot_y)
                    and shot_x == target_goal[0]
                    and 0 <= shot_y <= height                                   #Ahora no se pide que vaya adentro del arco, solo que vaya dentro de la cancha
                ):
                    raise ValueError("La patada debe apuntar dentro del arco rival.")
            if apply_movement:
                run_to(player, action.move_target, profile.real_speed, dt)

            return action

        except Exception:
            # Un error del programa deja quieto a ese jugador durante este paso.
            player.velocity = (0, 0)
            logger.exception("Falló el comportamiento del jugador %s", profile.id)
            return None

    def run_dt_pause(self) -> bool:
        if not self.paused:
            return False

        evaluated = False
        for team in (self.local_team, self.visitor_team):
            if (team.dt_active and team.dt_code and team.club_id not in self.dt_errors
                    and self._dt_pauses.get(team.club_id) != self.pause_index):
                self._dt_pauses[team.club_id] = self.pause_index
                self.run_dt(team)
                evaluated = True
        return evaluated

    def run_dt(self, team: Team) -> None:
        if not team.dt_active or not team.dt_code or team.club_id in self.dt_errors:
            return

        local = team.club_id == self.local_team.club_id
        obs = DtObservation(
            time_played=int(self.time),
            my_goals=self.scorer["LOCAL" if local else "VISITANTE"],
            rival_goals=self.scorer["VISITANTE" if local else "LOCAL"],
            players_id=[player.id for player in team.players],
            substitutes_id=[player.id for player in team.substitutes],
            can_substitute=self.paused and bool(team.substitutes)
            and (team.club_id, self.pause_index) not in self.substitution_pauses,
            pause_index=self.pause_index if self.paused else None,
        )

        try:
            mode = resolve_dt_behaviour(team.dt_code, "DT")
        except ValueError:
            try:
                if self._dt_runtime is None:
                    self._dt_runtime = BehaviourRuntime()
                key = self._dt_runtime.load(team.dt_code, kind="DT")
                action = self._dt_runtime.dt_decide(key, obs)
            except BehaviourRuntimeError as error:
                self.dt_errors[team.club_id] = str(error)[:256]
                if isinstance(error, BehaviourWorkerDead):
                    self._close_dt_runtime()
                logger.warning("Comportamiento de DT deshabilitado: club=%s error=%s", team.club_id, error.code)
                return
        else:
            action = dt_decide(mode, obs)

        players = {player.id: player for player in team.players}
        for change in action.tactical_changes:
            target = players.get(change["player_id"])
            mode = BehaviourMode(change["mode"])
            if target is None or target.behaviour_code is not None:
                continue

            # Un club anterior puede haber perdido el preset sin perder el modo del motor.
            behaviour_id, version = team.dt_default_behaviours.get(mode, (None, 1))
            if (target.behaviour_id, target.behaviour_version, target.behaviour_mode) != (behaviour_id, version, mode):
                self.change_behaviour(
                    target.id,
                    club_id=team.club_id,
                    behaviour_id=behaviour_id,
                    behaviour_mode=mode,
                    behaviour_code=None,
                    behaviour_version=version,
                    behaviour_api_version=API_VERSION,
                )

        if not obs.can_substitute or not action.substitutions:
            return

        change = action.substitutions[0]
        out_player_id = change["outgoing_player_id"]
        in_player_id = change["incoming_player_id"]
        try:
            self.substitute(team.club_id, out_player_id, in_player_id)
        except ValueError as error:
            logger.warning("Sustitución del DT rechazada: club=%s error=%s", team.club_id, error)
            return
        self.substitution_events.append({
            "eventId": f"dt-substitution:{self.match_id}:{self.pause_index}:{team.club_id}",
            "type": "SUBSTITUTION_APPLIED",
            "source": "DT",
            "clubId": team.club_id,
            "pauseId": f"{self.match_id}:{self.pause_index}",
            "outPlayerId": out_player_id,
            "inPlayerId": in_player_id,
        })

    def change_behaviour(
            self,
            player_id: int,
            *,
            club_id: int,
            behaviour_id: int | None,
            behaviour_mode: BehaviourMode,
            behaviour_code: str | None,
            behaviour_version: int,
            behaviour_api_version: int
    ) -> None:
        target = next(
            (
                profile
                for profile in self.player_profiles
                if profile.id == player_id
            ), None)

        if target is None or target.club_id != club_id:
            raise ValueError("El jugador no pertenece al equipo indicado.")

        updated = replace(
            target,
            behaviour_id=behaviour_id,
            behaviour_mode=BehaviourMode(behaviour_mode),
            behaviour_code=behaviour_code,
            behaviour_version=behaviour_version,
            behaviour_api_version=behaviour_api_version,
        )

        if club_id == self.local_team.club_id:
            self.local_team = replace(
                self.local_team,
                players=tuple(
                    updated if profile.id == player_id else profile
                    for profile in self.local_team.players
                ),
            )

        else:
            self.visitor_team = replace(
                self.visitor_team,
                players=tuple(
                    updated if profile.id == player_id else profile
                    for profile in self.visitor_team.players
                ),
            )

        self.player_profiles = self.local_team.players + self.visitor_team.players

        self.behaviour_errors.pop(player_id, None)


    def _run_play(self, dt: float) -> None:
        if not isfinite(dt) or dt <= 0:
            raise ValueError("dt debe ser positivo y finito")

        if self.finished:
            return

        duration = self.duration_ms / 1000
        dt = min(dt, duration - self.time)

        if self.time == 0 or int(self.time + dt) > int(self.time):
            self.run_dt(self.local_team)
            self.run_dt(self.visitor_team)

        snapshot = snapshot_from_match(
            self,
            SHOT_BASE_SPEED,
            SHOT_POWER_FACTOR,
        )

        commands = []
        shots = []

        # Primero se obtienen todas las decisiones.
        for player, profile in zip(
                self.world.players,
                self.player_profiles,
                strict=True,
        ):
            if profile.behaviour_code is not None:
                command = self._run_custom_behaviour(
                    profile,
                    snapshot,
                )

            else:
                target_goal = (
                    (width, height / 2)
                    if self.team_side(profile.club_id) == "LEFT"
                    else (0, height / 2)
                )

                action = self.run_behaviour(
                    player,
                    profile,
                    target_goal,
                    dt,
                    False,
                )

                if action is None:
                    continue

                try:
                    command = normalize_action(
                        action,
                        snapshot,
                        profile.id,
                    )

                except ExecutionError:
                    player.velocity = (0, 0)

                    logger.exception(
                        "Acción predeterminada inválida: jugador=%s",
                        profile.id,
                    )
                    continue

            if command is not None:
                commands.append((
                    player,
                    profile,
                    command,
                ))

        # Después se aplican movimientos y se reúnen patadas.
        for player, profile, command in commands:
            run_to(
                player,
                command.move_target,
                profile.real_speed,
                dt,
            )

            distance_to_ball = (
                    player.position
                    - self.world.ball.position
            ).length

            if (command.kick_target is not None
                and command.kick_speed is not None
                and distance_to_ball <= profile.kick_range
                and self.time >= self.next_kick_at.get(profile.id, 0)
                and (pymunk.Vec2d(*command.kick_target) - self.world.ball.position).length > 0):
                shots.append((
                    distance_to_ball / profile.kick_range,
                    random.random(),
                    player,
                    profile,
                    command.kick_target,
                    command.kick_speed))

        if shots:
            (_, _, player, profile, target, shot_speed,) = min(shots,
                key=lambda shot: (
                    shot[0],
                    shot[1],
                )
            )

            if kick(player, self.world.ball, target, shot_speed, profile.kick_range):
                self.next_kick_at[profile.id] = (self.time + profile.real_agility)

        scoring_side = step(self.world, dt)

        self.time = min(duration, self.time + dt,)

        if duration - self.time < 1e-9:
            self.time = duration

        if scoring_side is not None:
            scorer_by_side = {
                self.team_side(self.local_team.club_id): "LOCAL",

                self.team_side(self.visitor_team.club_id): "VISITANTE",
            }

            self.scorer[scorer_by_side[scoring_side]] += 1

            self.restart()

            logger.info(
                "Partido %s: goles %s",
                self.match_id,
                self.scorer,
            )
    def run_match(self, dt: float) -> None:
        """Avanza el encuentro, incluyendo tiempo de juego y descansos."""
        self._breaks.advance(self, dt)

    def close_runtime(self) -> None:
        self._close_player_runtime()
        self._close_dt_runtime()

    def _close_player_runtime(self) -> None:
        runtime = self._behaviour_runtime
        self._behaviour_runtime = None
        if runtime is not None:
            runtime.close()

    def _close_dt_runtime(self) -> None:
        runtime = self._dt_runtime
        self._dt_runtime = None
        if runtime is not None:
            runtime.close()

    def _run_custom_behaviour(self, profile: PlayerProfile, snapshot) -> Command | None:
        if profile.id in self.behaviour_errors:
            self.player_bodies[profile.id].velocity = (0, 0)
            return None

        try:
            if self._behaviour_runtime is None:
                self._behaviour_runtime = BehaviourRuntime()

            key = self._behaviour_runtime.load(profile.behaviour_code)

            return self._behaviour_runtime.decide(key, snapshot, profile.id)

        except BehaviourRuntimeError as error:
            self.behaviour_errors[profile.id] = {
                "code": error.code,
                "message": str(error)[:256],
                "diagnostics": error.diagnostics,
            }

            self.player_bodies[profile.id].velocity = (0, 0)

            if isinstance(error, BehaviourWorkerDead):
                self._close_player_runtime()

            logger.warning(
                "Comportamiento deshabilitado: jugador=%s error=%s",
                profile.id,
                error.code,
            )

            return None
