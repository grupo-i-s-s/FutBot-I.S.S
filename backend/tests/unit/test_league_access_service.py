from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from app.errors import AppError
from app.services import league_access_service as service


def test_sliding_window_expires_attempts_and_reports_wait(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(service, "monotonic", lambda: clock[0])
    for at in (100, 110, 120, 130, 140):
        clock[0] = at
        service.check_access_limit(1, 42)

    clock[0] = 159.5
    with pytest.raises(AppError) as error:
        service.check_access_limit(1, 42)
    assert error.value.code == "LEAGUE_ACCESS_RATE_LIMIT"
    assert error.value.fields == {"retryAfter": "1"}
    clock[0] = 160
    service.check_access_limit(1, 42)
    with pytest.raises(AppError):
        service.check_access_limit(1, 42)

    clock[0] = 221
    service.check_access_limit(2, 43)
    assert service._attempts == {(2, 43): [221]}


def test_accounts_and_leagues_have_independent_limits():
    for _ in range(5):
        service.check_access_limit(1, 42)
    service.check_access_limit(2, 42)
    service.check_access_limit(1, 43)
    with pytest.raises(AppError):
        service.check_access_limit(1, 42)


def test_simultaneous_requests_share_the_five_attempt_limit():
    barrier = Barrier(10, timeout=10)

    def attempt(_):
        barrier.wait()
        try:
            service.check_access_limit(1, 42)
            return True
        except AppError:
            return False

    with ThreadPoolExecutor(max_workers=10) as pool:
        assert sum(pool.map(attempt, range(10))) == 5
