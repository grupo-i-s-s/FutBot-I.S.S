import os
from datetime import timezone

import pytest
from sqlalchemy import event, URL

from app.models.matches_model import Matches

TEST_DATABASE_URL = ("postgresql+psycopg://futbot_test:futbot_test@test-db:5432/futbot_test")
os.environ["TEST_DATABASE_URL"] = TEST_DATABASE_URL
os.environ["LEAGUE_TEST_DATABASE_URL"] = TEST_DATABASE_URL

@pytest.fixture(autouse=True)
def isolated_league_access_attempts(monkeypatch):
    from app.services import league_access_service
    monkeypatch.setattr(league_access_service, "_attempts", {})


@pytest.fixture
def sqlite_match_dates():
    def restore_timezone(match, context):
        if context.session.get_bind().dialect.name == "sqlite":
            if match.init_date.tzinfo is None:
                match.init_date = match.init_date.replace(tzinfo=timezone.utc)

    event.listen(Matches, "load", restore_timezone)
    try:
        yield
    finally:
        event.remove(Matches, "load", restore_timezone)
