from types import SimpleNamespace
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from app import migrate
from primitives.dt_behaviour import DEFAULT_DT_CODES


APPLICATION_TABLES = {
    "users", "clubs", "auth_sessions", "pending_email_verifications", "behaviors",
    "players", "leagues", "league_registrations", "league_rounds", "league_standings",
    "matches", "default_teams", "planned_substitutions", "dt", "dt_behaviours", "Club_Stats",
    "password_reset_requests",
}


@pytest.fixture
def migration_database(monkeypatch):
    connect = migrate.connect
    schema = "migration_test_" + uuid4().hex
    with connect() as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))

    def isolated_connection():
        connection = connect()
        connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        return connection

    monkeypatch.setattr(migrate, "connect", isolated_connection)
    try:
        yield SimpleNamespace(connect=isolated_connection)
    finally:
        with connect() as connection:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def tables(connection):
    return {
        row[0] for row in connection.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = current_schema()"
        )
    }


def history(connection):
    return connection.execute(
        "SELECT filename, applied_at FROM schema_migrations ORDER BY filename"
    ).fetchall()


def record_history(connection, files):
    connection.execute("""
        CREATE TABLE schema_migrations (
            filename TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    for path in files:
        connection.execute(
            "INSERT INTO schema_migrations (filename, applied_at) VALUES (%s, '2001-01-01T00:00:00Z')",
            (path.name,),
        )


def insert_user(connection):
    return connection.execute(
        "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id",
        ("migration-test@example.com", "synthetic-hash"),
    ).fetchone()[0]


def test_fresh_database_creates_application_tables_and_records_migrations(migration_database):
    files = migrate.get_migration_files()

    migrate.main()

    with migration_database.connect() as connection:
        assert tables(connection) == APPLICATION_TABLES | {"schema_migrations"}
        assert [filename for filename, _ in history(connection)] == [path.name for path in files]
        assert connection.execute(
            "SELECT cancellation_reason, runtime_state FROM matches LIMIT 0"
        ).fetchall() == []


def test_rerun_preserves_existing_data_and_migration_timestamps(migration_database):
    migrate.main()
    with migration_database.connect() as connection:
        user_id = insert_user(connection)
        original_history = history(connection)

    migrate.main()

    with migration_database.connect() as connection:
        assert history(connection) == original_history
        assert connection.execute(
            "SELECT email, password_hash FROM users WHERE id = %s", (user_id,),
        ).fetchone() == ("migration-test@example.com", "synthetic-hash")


def test_stats_backfill_adds_existing_clubs_and_preserves_recorded_points(migration_database):
    files = [path for path in migrate.get_migration_files() if path.name < "017_club_stats_defaults.sql"]
    with migration_database.connect() as connection:
        for path in files:
            connection.execute(path.read_text(encoding="utf-8"), prepare=False)
        record_history(connection, files)
        user_id = insert_user(connection)
        club_id = connection.execute(
            "INSERT INTO clubs (user_id, name, avatar) VALUES (%s, 'Club anterior', 'avatar-01.png') RETURNING id",
            (user_id,),
        ).fetchone()[0]
        ranked_user = connection.execute("""
            INSERT INTO users (email, password_hash)
            VALUES ('club-rankeado@example.com', 'synthetic-hash') RETURNING id
        """).fetchone()[0]
        ranked_club = connection.execute(
            "INSERT INTO clubs (user_id, name, avatar) VALUES (%s, 'Club con puntos', 'avatar-01.png') RETURNING id",
            (ranked_user,),
        ).fetchone()[0]
        connection.execute('INSERT INTO "Club_Stats" (club_id, points) VALUES (%s, 3)', (ranked_club,))

    migrate.main()

    with migration_database.connect() as connection:
        assert connection.execute('SELECT club_id, points FROM "Club_Stats" ORDER BY club_id').fetchall() == [
            (club_id, 0), (ranked_club, 3),
        ]


def test_history_without_any_application_tables_is_rebuilt(migration_database):
    files = migrate.get_migration_files()
    with migration_database.connect() as connection:
        record_history(connection, files)
        original_history = history(connection)

    migrate.main()

    with migration_database.connect() as connection:
        assert tables(connection) == APPLICATION_TABLES | {"schema_migrations"}
        repaired_history = history(connection)
        assert [row[0] for row in repaired_history] == [path.name for path in files]
        assert repaired_history != original_history
        assert connection.execute("SELECT count(*) FROM users WHERE email = %s",("oponente-prueba@local.invalid",)).fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM users WHERE email <> %s",("oponente-prueba@local.invalid",)).fetchone()[0] == 0


def test_history_with_an_unrelated_table_is_not_automatically_reset(migration_database):
    with migration_database.connect() as connection:
        record_history(connection, migrate.get_migration_files())
        connection.execute("CREATE TABLE other_work (message TEXT NOT NULL)")
        connection.execute("INSERT INTO other_work VALUES ('keep this data')")
        original_history = history(connection)

    with pytest.raises(RuntimeError):
        migrate.main()

    with migration_database.connect() as connection:
        assert tables(connection) == {"schema_migrations", "other_work"}
        assert history(connection) == original_history
        assert connection.execute("SELECT message FROM other_work").fetchall() == [("keep this data",)]


def test_unknown_recorded_migration_is_refused_without_resetting_history(migration_database):
    with migration_database.connect() as connection:
        record_history(connection, migrate.get_migration_files())
        connection.execute(
            "INSERT INTO schema_migrations (filename) VALUES ('999_unavailable.sql')"
        )
        original_history = history(connection)

    with pytest.raises(RuntimeError, match="999_unavailable.sql"):
        migrate.main()

    with migration_database.connect() as connection:
        assert tables(connection) == {"schema_migrations"}
        assert history(connection) == original_history


@pytest.mark.parametrize("damage, missing_name", [
    ("DROP TABLE matches CASCADE", "matches"),
    ("ALTER TABLE matches DROP COLUMN cancellation_reason CASCADE", "cancellation_reason"),
])
def test_partial_schema_damage_is_refused_without_changing_data_or_history(
    migration_database, damage, missing_name,
):
    migrate.main()
    with migration_database.connect() as connection:
        user_id = insert_user(connection)
        connection.execute(damage)
        original_history = history(connection)
        original_tables = tables(connection)

    with pytest.raises(RuntimeError, match=missing_name):
        migrate.main()

    with migration_database.connect() as connection:
        assert history(connection) == original_history
        assert tables(connection) == original_tables
        assert connection.execute(
            "SELECT email FROM users WHERE id = %s", (user_id,),
        ).fetchone() == ("migration-test@example.com",)
        if missing_name == "cancellation_reason":
            assert connection.execute("""
                SELECT count(*) FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'matches' AND column_name = 'cancellation_reason'
            """).fetchone()[0] == 0


def test_pending_migrations_can_add_missing_columns_to_an_older_schema(migration_database):
    files = migrate.get_migration_files()
    prefix = [path for path in files if path.name < "008_match_results.sql"]
    with migration_database.connect() as connection:
        for path in prefix:
            connection.execute(path.read_text(encoding="utf-8"), prepare=False)
        record_history(connection, prefix)
        user_id = insert_user(connection)

    migrate.main()

    with migration_database.connect() as connection:
        assert [row[0] for row in history(connection)] == [path.name for path in files]
        assert connection.execute(
            "SELECT cancellation_reason, status FROM matches LIMIT 0"
        ).fetchall() == []
        assert connection.execute(
            "SELECT email FROM users WHERE id = %s", (user_id,),
        ).fetchone() == ("migration-test@example.com",)


def test_dt_backfill_provisions_existing_clubs_and_preserves_assigned_strategies(migration_database):
    files = [path for path in migrate.get_migration_files() if path.name < "016_dt_defaults.sql"]
    with migration_database.connect() as connection:
        for path in files:
            connection.execute(path.read_text(encoding="utf-8"), prepare=False)
        record_history(connection, files)
        user_id = insert_user(connection)
        club_id = connection.execute(
            "INSERT INTO clubs (user_id, name, avatar) VALUES (%s, 'Club anterior', 'avatar-01.png') RETURNING id",
            (user_id,),
        ).fetchone()[0]
        assigned = connection.execute("""
            INSERT INTO dt_behaviours (user_id, name, code)
            SELECT user_id, 'Mi estrategia', 'def decide(observation): return DtAction()' FROM clubs WHERE id = 999
            RETURNING id
        """).fetchone()[0]
        connection.execute("INSERT INTO dt (club_id, is_active, behaviour_id) VALUES (999, true, %s)", (assigned,))

    migrate.main()
    migrate.main()

    with migration_database.connect() as connection:
        strategies = connection.execute("SELECT name, code FROM dt_behaviours WHERE user_id = %s", (user_id,)).fetchall()
        assert len(strategies) == len(DEFAULT_DT_CODES)
        assert dict(strategies) == DEFAULT_DT_CODES
        assert connection.execute("""
            SELECT dt.is_active, dt_behaviours.name FROM dt
            JOIN dt_behaviours ON dt_behaviours.id = dt.behaviour_id WHERE dt.club_id = %s
        """, (club_id,)).fetchone() == (False, "No hacer nada")
        assert connection.execute("SELECT is_active, behaviour_id FROM dt WHERE club_id = 999").fetchone() == (True, assigned)


@pytest.mark.parametrize("last_sql", [
    "BEGIN; SELECT * FROM missing_migration_test_table; COMMIT;",
    "BEGIN; ALTER TABLE matches DROP COLUMN runtime_state; COMMIT;",
], ids=["sql_error", "incomplete_schema"])
def test_failed_rebuild_rolls_back_ddl_and_preserves_original_history(
    migration_database, monkeypatch, tmp_path, last_sql,
):
    files = migrate.get_migration_files()
    with migration_database.connect() as connection:
        record_history(connection, files)
        original_history = history(connection)
    for path in files:
        (tmp_path / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "014_pending_email_verifications.sql").write_text(
        last_sql, encoding="utf-8",
    )
    monkeypatch.setattr(migrate, "MIGRATIONS_DIR", tmp_path)

    with pytest.raises((psycopg.Error, RuntimeError)):
        migrate.main()

    with migration_database.connect() as connection:
        assert tables(connection) == {"schema_migrations"}
        assert history(connection) == original_history
