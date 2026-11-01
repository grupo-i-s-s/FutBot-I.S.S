import os
import re
import time
from pathlib import Path

import psycopg

from app.schema_state import SCHEMA_COLUMNS_SQL, find_schema_issues


MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
MIGRATION_LOCK = 746210001


def connect():
    for attempt in range(30):
        try:
            return psycopg.connect(
                host=os.getenv("POSTGRES_HOST", "db"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                dbname=os.environ["POSTGRES_DB"],
                user=os.environ["POSTGRES_USER"],
                password=os.environ["POSTGRES_PASSWORD"],
                connect_timeout=3,
                autocommit=True,
            )
        except psycopg.OperationalError:
            if attempt == 29:
                raise
            print("Esperando a PostgreSQL...", flush=True)
            time.sleep(2)


def get_migration_files() -> list[Path]:
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    if not files:
        raise RuntimeError(f"No hay migraciones en {MIGRATIONS_DIR}")

    return files


def main():
    files = get_migration_files()

    # Validar todos los archivos antes de modificar el historial o el esquema.
    statements = {}
    for path in files:
        match = re.fullmatch(
            r"\s*BEGIN;\s*(.*?)\s*COMMIT;\s*",
            path.read_text(encoding="utf-8"),
            flags=re.DOTALL | re.IGNORECASE,
        )
        if match is None:
            raise RuntimeError(
                f"{path.name} debe comenzar con BEGIN; y terminar con COMMIT;"
            )
        statements[path.name] = match.group(1)

    with connect() as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (MIGRATION_LOCK,))

        try:
            # La recuperación y las migraciones pendientes se confirman juntas.
            # Si falla el SQL o la validación, también se restaura el historial.
            with conn.transaction():
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        filename TEXT PRIMARY KEY,
                        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
                applied = {
                    row[0] for row in conn.execute("SELECT filename FROM schema_migrations")
                }
                unknown = applied - statements.keys()
                if unknown:
                    raise RuntimeError(
                        "El historial contiene migraciones no disponibles en esta versión: "
                        + ", ".join(sorted(unknown))
                    )

                relations = {
                    row[0] for row in conn.execute("""
                        SELECT relation.relname
                        FROM pg_catalog.pg_class AS relation
                        JOIN pg_catalog.pg_namespace AS namespace
                          ON namespace.oid = relation.relnamespace
                        WHERE namespace.nspname = current_schema()
                          AND relation.relkind IN ('r', 'p', 'v', 'm', 'f', 'S')
                    """)
                }
                if applied and relations == {"schema_migrations"}:
                    print(
                        "Solo existe el historial de migraciones; "
                        "reconstruyendo el esquema vacío de forma atómica.",
                        flush=True,
                    )
                    conn.execute("DELETE FROM schema_migrations")
                    applied.clear()

                for path in files:
                    if path.name in applied:
                        print(f"Ya aplicada: {path.name}", flush=True)
                        continue

                    print(f"Aplicando: {path.name}", flush=True)
                    conn.execute(statements[path.name], prepare=False)
                    conn.execute(
                        "INSERT INTO schema_migrations (filename) VALUES (%s)",
                        (path.name,),
                    )

                issues = find_schema_issues(conn.execute(SCHEMA_COLUMNS_SQL).fetchall())
                if issues["missing_tables"] or issues["missing_columns"]:
                    raise RuntimeError(
                        "El esquema no coincide con las migraciones registradas: "
                        f"{issues}. No se reinició el historial ni se borraron datos. "
                        "Revisá la base y restaurá los elementos faltantes desde una copia."
                    )

            print("Migraciones al día.", flush=True)
        finally:
            conn.execute(
                "SELECT pg_advisory_unlock(%s)",
                (MIGRATION_LOCK,),
            )


if __name__ == "__main__":
    main()
