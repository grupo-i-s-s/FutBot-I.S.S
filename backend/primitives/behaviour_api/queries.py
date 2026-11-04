from primitives.behaviour_api.context import PRESSURE_RADIUS, PlayerView, Point, TickSnapshot, distance


class Queries:
    def __init__(self, snapshot: TickSnapshot, player_id: int):
        self.snapshot = snapshot
        self.me = snapshot.player(player_id)

    def _teammates(self) -> tuple[PlayerView, ...]:
        return tuple(player for player in self.snapshot.players
                     if player.club_id == self.me.club_id and player.id != self.me.id)

    def _opponents(self) -> tuple[PlayerView, ...]:
        return tuple(player for player in self.snapshot.players
                     if player.club_id != self.me.club_id)

    def _possessor(self) -> PlayerView | None:
        player_id = self.snapshot.possessor_id

        if player_id is None:
            return None

        return self.snapshot.player(player_id)

    def _on_left(self) -> bool:
        return self.snapshot.left_club_id == self.me.club_id

    def _other_score(self) -> int:
        return next(score for club_id, score in self.snapshot.scores
                    if club_id != self.me.club_id)

    def _closest_position(self, players) -> Point | None:
        closest = min(players, key=lambda player: (
            distance(self.me.position, player.position), player.id), default=None)

        if closest is None:
            return None

        return closest.position

    def played_time(self) -> float:
        return self.snapshot.time

    def remaining_time(self) -> float:
        return max(0.0, self.snapshot.duration - self.snapshot.time)

    def winning(self) -> bool:
        return self.snapshot.score(self.me.club_id) > self._other_score()

    def drawing(self) -> bool:
        return self.snapshot.score(self.me.club_id) == self._other_score()

    def ball_possession(self) -> bool:
        return self.snapshot.possessor_id == self.me.id

    def team_has_possession(self) -> bool:
        possessor = self._possessor()

        return possessor is not None and possessor.club_id == self.me.club_id

    def ball_on_our_side(self) -> bool:
        x = self.snapshot.ball_position[0]
        middle = self.snapshot.width / 2

        if self._on_left():
            return x < middle

        return x > middle

    def ball_on_their_side(self) -> bool:
        x = self.snapshot.ball_position[0]
        middle = self.snapshot.width / 2

        if self._on_left():
            return x > middle

        return x < middle

    def attacking(self) -> bool:
        return self.team_has_possession() and self.ball_on_their_side()

    def defending(self) -> bool:
        possessor = self._possessor()

        return possessor is not None and possessor.club_id != self.me.club_id and self.ball_on_our_side()

    def under_pressure(self) -> bool:
        return any(distance(self.me.position, rival.position) <= PRESSURE_RADIUS for rival in self._opponents())

    def loose_ball(self) -> bool:
        return self.snapshot.possessor_id is None

    def can_kick(self) -> bool:
        return distance(self.me.position, self.snapshot.ball_position) <= self.me.kick_range

    def my_position(self) -> Point:
        return self.me.position

    def ball_position(self) -> Point:
        return self.snapshot.ball_position

    def base_position(self) -> Point:
        return self.me.base_position

    def our_goal(self) -> Point:
        return (0.0 if self._on_left() else self.snapshot.width), self.snapshot.height / 2

    def their_goal(self) -> Point:
        return self.snapshot.width if self._on_left() else 0.0, self.snapshot.height / 2

    def teammates(self) -> list[Point]:
        return [player.position for player in self._teammates()]

    def opponents(self) -> list[Point]:
        return [player.position for player in self._opponents()]

    def closer_teammate(self) -> Point | None:
        return self._closest_position(self._teammates())

    def closest_opponent(self) -> Point | None:
        return self._closest_position(self._opponents())
