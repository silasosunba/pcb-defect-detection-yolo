"""Neon-compatible PostgreSQL storage. No embedded database fallback."""

import hashlib
from contextlib import contextmanager
from pathlib import Path

from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def open_pool(settings):

    if settings._pool is not None and not settings._pool.closed:

        return settings._pool

    if not settings.database_url:

        raise RuntimeError(
            "DATABASE_URL is required. Add your Neon PostgreSQL connection string to .env."
        )

    if not settings.database_url.startswith(("postgresql://", "postgres://")):

        raise RuntimeError("DATABASE_URL must be a PostgreSQL connection URL.")

    config = conninfo_to_dict(settings.database_url)

    if config.get("host", "").endswith(".neon.tech") and config.get("sslmode") not in {
        "require",
        "verify-ca",
        "verify-full",
    }:

        raise RuntimeError(
            "Neon connections require TLS. Use the connection string with sslmode=require or verify-full."
        )

    settings._pool = ConnectionPool(
        conninfo=settings.database_url,
        min_size=0,
        max_size=settings.database_pool_size,
        timeout=15,
        kwargs={
            "row_factory": dict_row,
            "prepare_threshold": None,
            "connect_timeout": 10,
        },
        check=ConnectionPool.check_connection,
        open=True,
    )

    return settings._pool



@contextmanager
def connect(settings):

    with open_pool(settings).connection() as db:

        # Transaction-local configuration also works with Neon's pooled endpoint.
        db.execute(
            sql.SQL("SET LOCAL search_path TO {}").format(
                sql.Identifier(settings.database_schema)
            )
        )
        yield db



def initialize(settings):

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "images").mkdir(exist_ok=True)

    with connect(settings) as db:

        db.execute(
            "SELECT pg_advisory_xact_lock(hashtext(current_schema() || ':pcb_migrations'))"
        )
        db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, checksum TEXT NOT NULL, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        applied = {
            r["version"]: r["checksum"]
            for r in db.execute(
                "SELECT version,checksum FROM schema_migrations"
            ).fetchall()
        }

        for path in sorted((Path(__file__).parent / "migrations").glob("*.sql")):

            content = path.read_text()
            checksum = hashlib.sha256(content.encode()).hexdigest()

            if path.name in applied:

                if applied[path.name] != checksum:

                    raise RuntimeError(
                        f"Applied migration was changed: {path.name}. Add a new migration instead."
                    )

                continue

            db.execute(content, prepare=False)
            db.execute(
                "INSERT INTO schema_migrations(version,checksum) VALUES (%s,%s)",
                (path.name, checksum),
            )



def close_pool(settings):

    if settings._pool is not None:

        settings._pool.close()
        settings._pool = None
