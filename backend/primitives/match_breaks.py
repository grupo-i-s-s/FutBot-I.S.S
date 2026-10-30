from dataclasses import asdict, dataclass
from math import ceil, isfinite


DEFAULT_HYDRATION_BREAK_MS = 15_000
DEFAULT_HALF_BREAK_MS = 30_000
EPSILON = 1e-9


@dataclass
class MatchBreaks:
    hydration_ms: int = DEFAULT_HYDRATION_BREAK_MS
    half_ms: int = DEFAULT_HALF_BREAK_MS

    next_index: int = 0

    remaining_seconds: float = 0.0

    def __post_init__(self):
        for duration in (self.hydration_ms, self.half_ms):
            if type(duration) is not int or duration < 0:
                raise ValueError(
                    "La duración de las pausas debe ser un entero no negativo."
                )

        if type(self.next_index) is not int or not 0 <= self.next_index <= 3:
            raise ValueError("Índice de pausa inválido.")

        if (
            not isinstance(self.remaining_seconds, (int, float))
            or not isfinite(self.remaining_seconds)
            or self.remaining_seconds < 0
        ):
            raise ValueError("Tiempo restante de pausa inválido.")

        if self.remaining_seconds > 0:
            if self.next_index == 0:
                raise ValueError("La pausa actual no fue iniciada.")

            maximum = self.durations_ms[self.next_index - 1] / 1000
            if self.remaining_seconds > maximum + EPSILON:
                raise ValueError("El tiempo restante supera la duración de la pausa.")

    @property
    def durations_ms(self) -> tuple[int, int, int]:
        return self.hydration_ms, self.half_ms, self.hydration_ms

    @property
    def paused(self) -> bool:
        return self.remaining_seconds > EPSILON

    @property
    def phase(self) -> str:
        if not self.paused:
            return "PLAYING"

        return "HALF_BREAK" if self.next_index == 2 else "HYDRATION_BREAK"

    def public_state(self) -> dict:
        remaining_ms = (
            max(0, ceil(self.remaining_seconds * 1000 - 1e-6))
            if self.paused
            else 0
        )

        return {
            "phase": self.phase,
            # 1: hidratación 1; 2: entretiempo; 3: hidratación 2.
            "breakIndex": self.next_index if self.paused else None,
            "breakRemainingMs": remaining_ms,
        }

    def checkpoint(self) -> dict:
        return asdict(self)

    def advance(self, match, dt: float) -> None:
        if not isfinite(dt) or dt <= 0:
            raise ValueError("dt debe ser positivo y finito")

        remaining = dt
        duration = match.duration_ms / 1000

        while remaining > EPSILON and not match.finished:
            if self.paused:
                consumed = min(remaining, self.remaining_seconds)
                self.remaining_seconds -= consumed
                remaining -= consumed

                if self.remaining_seconds <= EPSILON:
                    self.remaining_seconds = 0.0

                continue

            # Una duración de cero desactiva esa pausa.
            while (
                self.next_index < 3
                and self.durations_ms[self.next_index] == 0
            ):
                self.next_index += 1

            boundary = (
                duration * (self.next_index + 1) / 4
                if self.next_index < 3
                else duration
            )

            until_boundary = boundary - match.time

            if until_boundary > EPSILON:
                consumed = min(remaining, until_boundary)
                match._run_play(consumed)
                remaining -= consumed

            # Normaliza errores de acumulación de floats y dispara cada pausa
            # exactamente una vez, incluso si dt atraviesa un límite.
            if match.time >= boundary - EPSILON:
                match.time = boundary

                if self.next_index < 3:
                    self.remaining_seconds = (
                        self.durations_ms[self.next_index] / 1000
                    )
                    self.next_index += 1