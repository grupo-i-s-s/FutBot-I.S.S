from dataclasses import dataclass
from math import isfinite

from primitives.behaviour_api.context import Point
from primitives.behaviour_api.queries import Queries
from primitives.physics import PLAYER_RADIUS


@dataclass(frozen=True)
class Command:
    move_target: Point
    kick_target: Point | None = None
    kick_speed: float | None = None


class Actions:
    def __init__(self, queries: Queries):
        self.queries = queries

    def _point(self, value):
        snapshot = self.queries.snapshot

        if type(value) not in (tuple, list) or len(value) != 2:
            raise ValueError("El destino debe ser un punto (x,y)")

        if any(type(number) not in (int, float) for number in value):
            raise ValueError("Las coordenadas deben ser números")

        x, y = value

        if not (isfinite(x) and isfinite(y) and 0 <= x <= snapshot.width and 0 <= y <= snapshot.height):
            raise ValueError("El destino debe estar adentro de la cancha")

        return float(x), float(y)

    def _movement_point(self, value) -> Point:
        x, y = self._point(value)
        snapshot = self.queries.snapshot

        return (max(PLAYER_RADIUS, min(snapshot.width - PLAYER_RADIUS, x)),
                max(PLAYER_RADIUS, min(snapshot.height - PLAYER_RADIUS, y)))

    def go_to(self, direction) -> Command:
        return Command(self._movement_point(direction))

    def go_to_ball(self) -> Command:
        return self.go_to(self.queries.ball_position())

    def stay(self, position) -> Command:
        return self.go_to(position)

    def cover_goal(self) -> Command:
        snapshot = self.queries.snapshot

        on_left = snapshot.left_club_id == self.queries.me.club_id

        x = 2.5 if on_left else snapshot.width - 2.5

        top = (snapshot.height - snapshot.goal_width) / 2

        bottom = (snapshot.height + snapshot.goal_width) / 2

        y = max(top, min(bottom, snapshot.ball_position[1]))

        return self.go_to((x, y))

    def dribble_to(self, direction):
        target = self._point(direction)

        if not self.queries.ball_possession():
            return self.go_to_ball()

        movement = self._movement_point(target)

        if not self.queries.can_kick():
            return Command(movement)

        return Command(
            move_target=movement,
            kick_target=target,
            kick_speed=min(self.queries.me.real_speed, 12.0)
        )

    def kick_to(self, direction):
        return Command(
            move_target=self.queries.my_position(),
            kick_target=self._point(direction),
            kick_speed=self.queries.me.shot_speed
        )
