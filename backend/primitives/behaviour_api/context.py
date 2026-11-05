from collections.abc import Iterable
from dataclasses import dataclass
from math import hypot, isfinite

Point = tuple[float, float]


def to_point(value: Iterable[float]) -> Point:
    x, y = value
    return float(x), float(y)


MAX_POSSESSION_RELATIVE_SPEED = 12.0
PRESSURE_RADIUS = 5.0


def distance(a: Point, b: Point) -> float:
    return hypot(a[0] - b[0], a[1] - b[1])


@dataclass(frozen=True)
class PlayerView:
    id: int
    club_id: int

    position: Point
    velocity: Point
    base_position: Point

    kick_range: float
    next_kick_at: float

    real_speed: float
    shot_speed: float


@dataclass(frozen=True)
class TickSnapshot:
    time: float
    duration: float

    width: float
    height: float
    goal_width: float

    left_club_id: int
    scores: tuple[tuple[int, int], ...]

    players: tuple[PlayerView, ...]

    ball_position: Point
    ball_velocity: Point

    possessor_id: int | None

    def player(self, player_id: int) -> PlayerView:
        return next(player for player in self.players if player.id == player_id)

    def score(self, club_id: int) -> int:
        return next(score for team, score in self.scores if team == club_id)


def snapshot_from_match(match,
                        shot_base_speed: float,
                        shot_power_factor: float,
                        max_relative_speed: float = MAX_POSSESSION_RELATIVE_SPEED) -> TickSnapshot:
    if not isfinite(max_relative_speed) or max_relative_speed < 0:
        raise ValueError("El limite de velocidad relativa debe ser válido")

    players = tuple(
        PlayerView(
            id=profile.id,
            club_id=profile.club_id,
            position=to_point(
                match.player_bodies[profile.id].position
            ),
            velocity=to_point(
                match.player_bodies[profile.id].velocity
            ),
            base_position=to_point(
                match.home_positions[profile.id]
            ),
            kick_range=profile.kick_range,
            next_kick_at=match.next_kick_at.get(
                profile.id, 0.0
            ),
            real_speed=profile.real_speed,
            shot_speed=(
                    shot_base_speed
                    + profile.power * shot_power_factor
            ),
        )
        for profile in match.player_profiles
    )

    ball_position = tuple(match.world.ball.position)
    ball_velocity = tuple(match.world.ball.velocity)

    candidates = [
        player
        for player in players
        if (distance(player.position, to_point(ball_position)) <= player.kick_range)
           and (distance(player.velocity, to_point(ball_velocity)) <= max_relative_speed)
    ]

    possessor = min(
        candidates,
        key=lambda player: (
            distance(
                player.position,
                to_point(ball_position),
            ) / player.kick_range,
            player.id,
        ),
        default=None,
    )

    local_id = match.local_team.club_id
    visitor_id = match.visitor_team.club_id

    return TickSnapshot(
        time=match.time,
        duration=match.duration_ms / 1000,
        width=match.cord.width,
        height=match.cord.height,
        goal_width=match.cord.goal_width,
        left_club_id=(
            local_id
            if match.team_side(local_id) == "LEFT"
            else visitor_id
        ),
        scores=(
            (local_id, match.scorer["LOCAL"]),
            (visitor_id, match.scorer["VISITANTE"]),
        ),
        players=players,
        ball_position=to_point(ball_position),
        ball_velocity=to_point(ball_velocity),
        possessor_id=(
            None if possessor is None else possessor.id
        ),
    )

def snapshot_from_dict(data: dict) -> TickSnapshot:
    return TickSnapshot(
        time=data["time"],
        duration=data["duration"],
        width=data["width"],
        height=data["height"],
        goal_width=data["goal_width"],
        left_club_id=data["left_club_id"],
        scores=tuple(
            (int(club_id), int(score))
            for club_id, score in data["scores"]
        ),
        players=tuple(
            PlayerView(
                id=player["id"],
                club_id=player["club_id"],
                position=to_point(player["position"]),
                velocity=to_point(player["velocity"]),
                base_position=to_point(player["base_position"]),
                kick_range=player["kick_range"],
                next_kick_at=player["next_kick_at"],
                real_speed=player["real_speed"],
                shot_speed=player["shot_speed"],
            )
            for player in data["players"]
        ),
        ball_position=to_point(data["ball_position"]),
        ball_velocity=to_point(data["ball_velocity"]),
        possessor_id=data["possessor_id"]
    )

