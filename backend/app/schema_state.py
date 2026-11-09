from app.models.auth_model import PasswordResetRequest, AuthSession, Club, User, PendingEmailVerification
from app.models.behaviour_model import Behavior
from app.models.dt_model import Dt, DtBehaviour
from app.models.league_model import League, LeagueRegistration, LeagueRound, LeagueStanding
from app.models.matches_model import Matches
from app.models.player_model import Player
from app.models.planned_substitution_model import PlannedSubstitution
from app.models.team_model import DefaultTeam


REQUIRED_COLUMNS = {
    model.__tablename__: frozenset(column.name for column in model.__table__.columns)
    for model in (
        User, Club, AuthSession, Behavior, Player, League, LeagueRegistration,
        LeagueRound, LeagueStanding, DefaultTeam, Matches, PlannedSubstitution,
        PendingEmailVerification, Dt, DtBehaviour, PasswordResetRequest
    )
}

SCHEMA_COLUMNS_SQL = """
    SELECT relation.relname, attribute.attname
    FROM pg_catalog.pg_class AS relation
    JOIN pg_catalog.pg_namespace AS namespace ON namespace.oid = relation.relnamespace
    JOIN pg_catalog.pg_attribute AS attribute ON attribute.attrelid = relation.oid
    WHERE namespace.nspname = current_schema()
      AND relation.relkind IN ('r', 'p')
      AND attribute.attnum > 0
      AND NOT attribute.attisdropped
"""


def find_schema_issues(rows) -> dict:
    actual = {}
    for table, column in rows:
        actual.setdefault(table, set()).add(column)

    return {
        "missing_tables": sorted(REQUIRED_COLUMNS.keys() - actual.keys()),
        "missing_columns": {
            table: sorted(required - actual[table])
            for table, required in sorted(REQUIRED_COLUMNS.items())
            if table in actual and required - actual[table]
        },
    }
