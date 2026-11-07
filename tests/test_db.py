import pytest

from backend.config import Settings
from backend.db import close_pool, connect, initialize, open_pool


def test_database_url_is_required_and_postgres_only():

    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):

        open_pool(Settings(database_url=""))

    with pytest.raises(RuntimeError, match="PostgreSQL"):

        open_pool(Settings(database_url="file:///tmp/not-postgres"))



def test_neon_requires_tls_before_opening_connection():

    with pytest.raises(RuntimeError, match="TLS"):

        open_pool(
            Settings(
                database_url="postgresql://user:placeholder@sample.neon.tech/neondb?sslmode=disable"
            )
        )



def test_migrations_are_repeatable_and_detections_are_jsonb(tmp_path, postgres_schema):

    url, schema = postgres_schema
    settings = Settings(database_url=url, database_schema=schema, data_dir=tmp_path)

    try:

        initialize(settings)
        initialize(settings)

        with connect(settings) as db:

            assert (
                db.execute(
                    "SELECT count(*) AS total FROM schema_migrations"
                ).fetchone()["total"]
                == 1
            )
            row = db.execute(
                "SELECT data_type FROM information_schema.columns WHERE table_schema=%s AND table_name='inspections' AND column_name='detections'",
                (schema,),
            ).fetchone()
            assert row["data_type"] == "jsonb"

    finally:

        close_pool(settings)
