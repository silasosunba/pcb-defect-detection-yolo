"""Temporary PostgreSQL browser-test server. Never uses the live DATABASE_URL."""

import io
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import psycopg
import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, Response
from PIL import Image, ImageDraw
from psycopg import sql

from backend.config import Settings
from backend.db import close_pool, connect, initialize
from backend.main import create_app
from backend.security import admin_user, passwords
from tests.fixtures import FixtureDetector


if __name__ == "__main__":

    load_dotenv(ROOT / ".env.test")
    url = os.getenv("TEST_DATABASE_URL")

    if not url:

        raise SystemExit(
            "TEST_DATABASE_URL is required. Use a dedicated PostgreSQL test database, never production."
        )

    schema = "pcb_browser_" + uuid.uuid4().hex

    with psycopg.connect(url, autocommit=True) as db:

        db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))

    settings = None

    try:

        with tempfile.TemporaryDirectory(prefix="pcb-browser-tests-") as temporary:

            root = Path(temporary)
            settings = Settings(
                database_url=url,
                database_schema=schema,
                data_dir=root,
                model_path=root / "missing.pt",
                manifest_path=root / "missing.json",
                allowed_origins=("http://127.0.0.1:5175",),
            )
            initialize(settings)

            with connect(settings) as db:

                db.execute(
                    "INSERT INTO users(id,name,email,password_hash,role,created_at) VALUES (%s,%s,%s,%s,%s,%s)",
                    (
                        str(uuid.uuid4()),
                        "Test Administrator",
                        "admin@example.com",
                        passwords.hash("Browser-test-password-123"),
                        "admin",
                        int(time.time()),
                    ),
                )

            app = create_app(settings)

            # Test-only routes are defined here, never in the production application.

            @app.post("/api/__test__/enable-inference")
            def enable_fixture(user=Depends(admin_user)):

                app.state.detector = FixtureDetector()

                return {"fixture": True}


            @app.get("/api/__test__/sample.png")
            def sample_image():

                image = Image.new("RGB", (64, 64), "#183e30")
                draw = ImageDraw.Draw(image)

                for y in range(8, 64, 12):

                    draw.line((4, y, 60, y), fill="#bdaf78", width=2)

                content = io.BytesIO()
                image.save(content, format="PNG")

                return Response(content.getvalue(), media_type="image/png")


            uvicorn.run(app, host="127.0.0.1", port=8011)

    finally:

        if settings is not None:

            close_pool(settings)

        with psycopg.connect(url, autocommit=True) as db:

            db.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
