import io
import json
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.config import Settings
from backend.db import connect
from backend.main import create_app

HEADERS = {"X-PCB-Request": "1", "Origin": "http://localhost:5173"}
PASSWORD = "A-real-test-password-123"


from tests.fixtures import FixtureDetector


@pytest.fixture
def app(tmp_path, postgres_schema):

    url, schema = postgres_schema
    settings = Settings(
        database_url=url,
        database_schema=schema,
        data_dir=tmp_path / "data",
        model_path=tmp_path / "best.pt",
        manifest_path=tmp_path / "model-manifest.json",
    )

    return create_app(settings, FixtureDetector())



@pytest.fixture
def client(app):

    with TestClient(app, headers=HEADERS) as client:

        yield client



def register(client, email="one@example.com", **extra):

    response = client.post(
        "/api/auth/register",
        json={"name": "Test Inspector", "email": email, "password": PASSWORD, **extra},
    )
    assert response.status_code == 201, response.text

    return response.json()



def picture():

    data = io.BytesIO()
    Image.new("RGB", (32, 32), "green").save(data, format="PNG")

    return data.getvalue()



def inspect(client, **kwargs):

    return client.post(
        "/api/inspections",
        files={"file": ("board.png", picture(), "image/png")},
        **kwargs,
    )



def test_registration_session_and_logout(client):

    assert client.get("/api/auth/me").status_code == 401
    user = register(client, "ONE@example.com")
    assert user["role"] == "user" and user["email"] == "one@example.com"
    assert "password_hash" not in user
    assert client.get("/api/auth/me").json()["id"] == user["id"]
    assert (
        "HttpOnly"
        in client.cookies.jar._cookies["testserver.local"]["/"]["pcb_session"]._rest
    )
    assert client.get("/api/admin/overview").status_code == 403
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    assert (
        client.post(
            "/api/auth/login", json={"email": user["email"], "password": PASSWORD}
        ).status_code
        == 200
    )



def test_cannot_assign_admin_on_registration(client):

    response = client.post(
        "/api/auth/register",
        json={
            "name": "Attacker",
            "email": "bad@example.com",
            "password": PASSWORD,
            "role": "admin",
        },
    )
    assert response.status_code == 422



def test_csrf_and_origins(client):

    body = {"name": "Test", "email": "test@example.com", "password": PASSWORD}
    assert (
        client.post(
            "/api/auth/register", json=body, headers={"X-PCB-Request": ""}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/auth/register",
            json=body,
            headers={"Origin": "https://attacker.example"},
        ).status_code
        == 403
    )
    assert client.post("/api/auth/register", json=body).status_code == 201



def test_email_unique_and_password_policy(client):

    register(client)
    response = client.post(
        "/api/auth/register",
        json={"name": "Test", "email": "ONE@example.com", "password": PASSWORD},
    )
    assert response.status_code == 409
    assert (
        client.post(
            "/api/auth/register",
            json={"name": "Test", "email": "two@example.com", "password": "short"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "one@example.com", "password": "wrong-long-password"},
        ).status_code
        == 401
    )



def test_inspection_persistence_and_user_isolation(client, app):

    owner = register(client)
    response = inspect(client, data={"confidence": "0.45"})
    assert response.status_code == 201, response.text
    item = response.json()
    assert item["confidence"] == 0.45 and item["detections"][0]["label"] == "short"
    assert item["width"] == 32 and item["model_sha256"] == "a" * 64
    assert client.get(item["image_url"]).status_code == 200
    assert client.get(item["original_url"]).headers["content-type"] == "image/png"
    assert client.get("/api/inspections").json()["total"] == 1
    client.post("/api/auth/logout")
    register(client, "other@example.com")
    assert client.get("/api/inspections").json()["total"] == 0
    assert client.get(f"/api/inspections/{item['id']}").status_code == 404
    assert client.get(item["image_url"]).status_code == 404
    assert (
        client.patch(
            f"/api/admin/users/{owner['id']}", json={"role": "admin", "active": True}
        ).status_code
        == 403
    )

    with connect(app.state.settings) as db:

        assert (
            db.execute("SELECT count(*) AS total FROM inspections").fetchone()["total"]
            == 1
        )



def test_admin_counts_roles_and_session_revocation(client, app):

    account = register(client)
    inspect(client)
    client.post("/api/auth/logout")
    admin = register(client, "admin@example.com")

    with connect(app.state.settings) as db:

        db.execute("UPDATE users SET role='admin' WHERE id=%s", (admin["id"],))

    overview = client.get("/api/admin/overview").json()
    assert overview["users"] == 2 and overview["active_users"] == 2
    assert overview["inspections"] == 1 and overview["defects"] == 1
    assert overview["class_counts"] == {"short": 1}
    item = overview["recent_inspections"][0]
    assert client.get(item["image_url"]).status_code == 200
    assert (
        client.patch(
            f"/api/admin/users/{admin['id']}", json={"role": "user", "active": True}
        ).status_code
        == 400
    )

    with TestClient(app, headers=HEADERS) as other:

        assert (
            other.post(
                "/api/auth/login",
                json={"email": account["email"], "password": PASSWORD},
            ).status_code
            == 200
        )
        response = client.patch(
            f"/api/admin/users/{account['id']}", json={"role": "user", "active": False}
        )
        assert response.status_code == 200
        assert other.get("/api/auth/me").status_code == 401
        assert (
            other.post(
                "/api/auth/login",
                json={"email": account["email"], "password": PASSWORD},
            ).status_code
            == 401
        )

    directory = client.get("/api/admin/users?q=admin").json()
    assert directory["total"] == 1 and "password_hash" not in json.dumps(directory)



def test_upload_validation(client):

    register(client)
    assert (
        client.post(
            "/api/inspections",
            files={"file": ("board.png", b"<svg>bad</svg>", "image/png")},
        ).status_code
        == 422
    )
    assert inspect(client, data={"confidence": "0.99"}).status_code == 422
    assert (
        client.post(
            "/api/inspections",
            files={"file": ("large.png", b"x" * (20 * 1024 * 1024 + 1), "image/png")},
        ).status_code
        == 413
    )
    assert (
        client.post(
            "/api/inspections",
            files={"file": ("large.png", b"x" * (21 * 1024 * 1024), "image/png")},
        ).status_code
        == 413
    )



def test_personal_dashboard_uses_postgres_jsonb_and_isolates_users(client):

    register(client)
    assert inspect(client).status_code == 201
    data = client.get("/api/dashboard").json()
    assert data["inspections"] == 1 and data["defects"] == 1
    assert data["class_counts"] == {"short": 1}
    assert len(data["trend"]) == 7 and sum(day["total"] for day in data["trend"]) == 1
    detection = data["recent_inspections"][0]["detections"][0]
    assert (
        detection["box"] == [1, 1, 12, 12]
        and detection["review_priority"] == "critical"
    )
    assert detection["explanation"] and detection["recommendation"]
    client.post("/api/auth/logout")
    register(client, "fresh@example.com")
    fresh = client.get("/api/dashboard").json()
    assert fresh["inspections"] == 0 and fresh["class_counts"] == {}



def test_tiff_upload_and_remember_me_cookie(client):

    user = register(client)
    image = io.BytesIO()
    Image.new("RGB", (32, 32), "green").save(image, format="TIFF")
    response = client.post(
        "/api/inspections",
        files={"file": ("board.tiff", image.getvalue(), "image/tiff")},
    )
    assert response.status_code == 201
    client.post("/api/auth/logout")
    response = client.post(
        "/api/auth/login",
        json={"email": user["email"], "password": PASSWORD, "remember_me": True},
    )
    assert (
        response.status_code == 200
        and "Max-Age=2592000" in response.headers["set-cookie"]
    )



def test_missing_model_returns_honest_status(client, app):

    from backend.inference import Detector

    app.state.detector = Detector(app.state.settings)
    register(client)
    assert client.get("/api/model").json()["available"] is False
    assert inspect(client).status_code == 503
    assert client.get("/api/inspections").json()["total"] == 0



def test_rate_limit_and_expired_sessions(client, app):

    register(client)

    with connect(app.state.settings) as db:

        db.execute("UPDATE sessions SET expires_at=%s", (int(time.time()) - 1,))
        db.cursor().executemany(
            "INSERT INTO auth_attempts VALUES (%s,%s,%s)",
            [("testclient", "one@example.com", int(time.time()))] * 10,
        )

    assert client.get("/api/auth/me").status_code == 401
    assert (
        client.post(
            "/api/auth/login", json={"email": "one@example.com", "password": PASSWORD}
        ).status_code
        == 429
    )



def test_pagination_and_safe_image_paths(client):

    register(client)
    assert client.get("/api/inspections?limit=101").status_code == 422
    assert client.get("/api/inspections?offset=-1").status_code == 422
    assert client.get("/api/inspections/not-a-uuid/image").status_code == 422
    assert client.get("/api/auth/me").headers["cache-control"] == "no-store"
    assert client.get("/api/docs").status_code == 200
    assert client.get("/api/openapi.json").status_code == 200
