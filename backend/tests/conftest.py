from datetime import timezone

import pytest
from sqlalchemy import event

from app.models.matches_model import Matches


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
