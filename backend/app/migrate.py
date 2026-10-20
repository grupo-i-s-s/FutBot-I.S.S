import os
import re
import time
from pathlib import Path

import psycopg


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

    with connect() as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (MIGRATION_LOCK,))

        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    filename TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)

            applied = {
                row[0]
                for row in conn.execute(
                    "SELECT filename FROM schema_migrations"
                )
            }

            for path in files:
                if path.name in applied:
                    print(f"Ya aplicada: {path.name}", flush=True)
                    continue

                sql = path.read_text(encoding="utf-8")

                match = re.fullmatch(
                    r"\s*BEGIN;\s*(.*?)\s*COMMIT;\s*",
                    sql,
                    flags=re.DOTALL | re.IGNORECASE,
                )

                if match is None:
                    raise RuntimeError(
                        f"{path.name} debe comenzar con BEGIN; "
                        "y terminar con COMMIT;"
                    )

                print(f"Aplicando: {path.name}", flush=True)

                with conn.transaction():
                    conn.execute(match.group(1), prepare=False)
                    conn.execute(
                        "INSERT INTO schema_migrations (filename) VALUES (%s)",
                        (path.name,),
                    )

            print("Migraciones al día.", flush=True)
        finally:
            conn.execute(
                "SELECT pg_advisory_unlock(%s)",
                (MIGRATION_LOCK,),
            )


if __name__ == "__main__":
    main()
