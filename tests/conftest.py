"""Use an explicitly selected PostgreSQL test database and isolated schemas."""

import os
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env.test")


@pytest.fixture
def postgres_schema():

    url = os.getenv("TEST_DATABASE_URL")

    if not url:

        pytest.skip(
            "Set TEST_DATABASE_URL to a dedicated PostgreSQL test database; SQLite is not used."
        )

    schema = "pcb_test_" + uuid.uuid4().hex

    with psycopg.connect(url, autocommit=True) as db:

        db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))

    try:

        yield url, schema

    finally:

        with psycopg.connect(url, autocommit=True) as db:

            db.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
