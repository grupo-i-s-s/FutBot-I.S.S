from math import ceil
from threading import Lock
from time import monotonic

from app.errors import AppError


_attempts: dict[tuple[int, int], list[float]] = {}
_lock = Lock()


def check_access_limit(club_id: int, league_id: int) -> None:
    # Cada cuenta tiene un único club. Las claves de otras ligas son independientes.
    with _lock:
        now = monotonic()
        for key in list(_attempts):
            recent = [at for at in _attempts[key] if at > now - 60]
            if recent:
                _attempts[key] = recent
            else:
                del _attempts[key]

        attempts = _attempts.setdefault((club_id, league_id), [])
        if len(attempts) >= 5:
            retry_after = ceil(attempts[0] + 60 - now)
            raise AppError(
                "LEAGUE_ACCESS_RATE_LIMIT",
                "Alcanzaste el límite de intentos. Esperá para volver a intentarlo.",
                {"retryAfter": str(retry_after)},
            )
        attempts.append(now)
