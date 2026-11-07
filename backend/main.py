import io
import logging
import psycopg
import time
import uuid
import warnings
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from psycopg.types.json import Jsonb
from starlette.concurrency import run_in_threadpool

from backend.config import ROOT, Settings
from backend.assessment import assess
from backend.db import close_pool, connect, initialize
from backend.inference import Detector, ModelUnavailable
from backend.security import (
    COOKIE,
    DUMMY_HASH,
    admin_user,
    audit,
    current_user,
    digest,
    passwords,
    public_user,
    start_session,
)

logger = logging.getLogger(__name__)
Image.MAX_IMAGE_PIXELS = 20_000_000


class Credentials(BaseModel):

    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    remember_me: bool = False

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):

        return value.lower()



class Registration(Credentials):

    name: str = Field(min_length=2, max_length=80)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):

        value = value.strip()

        if len(value) < 2:

            raise ValueError("Enter at least two characters for your name.")

        return value



class UserUpdate(BaseModel):

    model_config = ConfigDict(extra="forbid")
    role: str = Field(pattern="^(user|admin)$")
    active: bool



def inspection_record(row):

    item = dict(row)
    item.pop("sequence", None)
    item["detections"] = assess(item["detections"])
    item["guidance_policy"] = "class-based-review-v1"
    item["image_url"] = f"/api/inspections/{item['id']}/image"
    item["original_url"] = f"/api/inspections/{item['id']}/image?original=true"

    return item



def create_app(settings=None, detector=None):

    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):

        try:

            initialize(settings)
            yield

        finally:

            close_pool(settings)


    app = FastAPI(
        title="PCB Detect API",
        version="0.2.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.detector = detector or Detector(settings)

    @app.middleware("http")
    async def request_guard(request: Request, call_next):

        if request.url.path.startswith("/api/"):

            if request.method in {"POST", "PATCH", "PUT", "DELETE"}:

                # A custom header forces cross-origin browser requests to preflight.
                # No CORS policy grants access; also validate Origin when supplied.
                origin = request.headers.get("origin")

                if request.headers.get("x-pcb-request") != "1" or (
                    origin and origin not in settings.allowed_origins
                ):

                    return JSONResponse(
                        {"detail": "Request origin could not be verified."},
                        status_code=403,
                    )

                # Bound the entire body, including multipart parser input.
                chunks, size = [], 0

                async for chunk in request.stream():

                    size += len(chunk)

                    if size > settings.max_upload + 64 * 1024:

                        return JSONResponse(
                            {"detail": "Maximum upload size is 20 MB."}, status_code=413
                        )

                    chunks.append(chunk)

                request._body = b"".join(chunks)

            response = await call_next(request)
            response.headers["Cache-Control"] = "no-store"

        else:

            response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self' https: http:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        )

        if request.url.path == "/api/docs":

            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; object-src 'none'; frame-ancestors 'none'"
            )

        return response


    def throttle(request, email):

        now = int(time.time())
        ip = request.client.host if request.client else "unknown"

        with connect(settings) as db:

            db.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))", ("pcb_auth:" + ip,)
            )
            db.execute("DELETE FROM auth_attempts WHERE created_at<%s", (now - 900,))
            total = db.execute(
                "SELECT count(*) AS total FROM auth_attempts WHERE ip=%s", (ip,)
            ).fetchone()["total"]
            account = db.execute(
                "SELECT count(*) AS total FROM auth_attempts WHERE ip=%s AND email=%s",
                (ip, email),
            ).fetchone()["total"]

            if total >= 50 or account >= 10:

                raise HTTPException(429, "Too many attempts. Try again in 15 minutes.")

            db.execute("INSERT INTO auth_attempts VALUES (%s,%s,%s)", (ip, email, now))

        # Independent transaction preserves attempts when authentication fails.

    @app.get("/api/health")
    def health():

        return {"status": "ok"}


    @app.post("/api/auth/register", status_code=201)
    def register(body: Registration, request: Request, response: Response):

        user_id = str(uuid.uuid4())
        throttle(request, body.email)

        with connect(settings) as db:

            try:

                db.execute(
                    "INSERT INTO users(id,name,email,password_hash,created_at,last_login) VALUES (%s,%s,%s,%s,%s,%s)",
                    (
                        user_id,
                        body.name,
                        body.email,
                        passwords.hash(body.password),
                        int(time.time()),
                        int(time.time()),
                    ),
                )

            except psycopg.errors.UniqueViolation:

                raise HTTPException(409, "An account with that email already exists.")

            start_session(db, user_id, response, settings)
            audit(db, user_id, "account.registered", user_id)

            return public_user(
                db.execute("SELECT * FROM users WHERE id=%s", (user_id,)).fetchone()
            )


    @app.post("/api/auth/login")
    def login(body: Credentials, request: Request, response: Response):

        throttle(request, body.email)

        with connect(settings) as db:

            user = db.execute(
                "SELECT * FROM users WHERE email=%s", (body.email,)
            ).fetchone()
            valid = passwords.verify(
                body.password, user["password_hash"] if user else DUMMY_HASH
            )

            if not user or not valid or not user["active"]:

                raise HTTPException(
                    401, "Email or password is incorrect, or the account is disabled."
                )

            old_token = request.cookies.get(COOKIE)

            if old_token:

                db.execute(
                    "DELETE FROM sessions WHERE token_hash=%s", (digest(old_token),)
                )

            db.execute(
                "UPDATE users SET last_login=%s WHERE id=%s",
                (int(time.time()), user["id"]),
            )
            start_session(db, user["id"], response, settings, body.remember_me)
            audit(db, user["id"], "account.login", user["id"])

            return public_user(
                db.execute("SELECT * FROM users WHERE id=%s", (user["id"],)).fetchone()
            )


    @app.get("/api/auth/me")
    def me(user=Depends(current_user)):

        return user


    @app.post("/api/auth/logout", status_code=204)
    def logout(request: Request, response: Response):

        with connect(settings) as db:

            db.execute(
                "DELETE FROM sessions WHERE token_hash=%s",
                (digest(request.cookies.get(COOKIE, "")),),
            )

        response.delete_cookie(
            COOKIE,
            path="/",
            secure=settings.secure_cookies,
            httponly=True,
            samesite="strict",
        )


    @app.get("/api/model")
    def model_status(user=Depends(current_user)):

        return app.state.detector.status()


    @app.get("/api/inspections")
    def list_inspections(
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
        user=Depends(current_user),
    ):

        with connect(settings) as db:

            total = db.execute(
                "SELECT count(*) AS total FROM inspections WHERE user_id=%s",
                (user["id"],),
            ).fetchone()["total"]
            rows = db.execute(
                "SELECT * FROM inspections WHERE user_id=%s ORDER BY created_at DESC, sequence DESC LIMIT %s OFFSET %s",
                (user["id"], limit, offset),
            ).fetchall()

        return {"items": [inspection_record(r) for r in rows], "total": total}


    @app.get("/api/dashboard")
    def dashboard(user=Depends(current_user)):

        today = datetime.now(timezone.utc).date()
        start = int(
            datetime.combine(
                today - timedelta(days=6), datetime.min.time(), tzinfo=timezone.utc
            ).timestamp()
        )

        with connect(settings) as db:

            summary = dict(
                db.execute(
                    "SELECT count(*) AS inspections, coalesce(sum(jsonb_array_length(detections)),0) AS defects, count(*) FILTER (WHERE jsonb_array_length(detections)=0) AS no_detections, coalesce(avg(duration_ms),0) AS average_duration_ms FROM inspections WHERE user_id=%s",
                    (user["id"],),
                ).fetchone()
            )
            summary["average_duration_ms"] = round(summary["average_duration_ms"], 1)
            labels = db.execute(
                "SELECT defect->>'label' AS label,count(*) AS total FROM inspections CROSS JOIN LATERAL jsonb_array_elements(detections) defect WHERE user_id=%s GROUP BY label ORDER BY total DESC",
                (user["id"],),
            ).fetchall()
            summary["class_counts"] = {row["label"]: row["total"] for row in labels}
            trend = db.execute(
                "SELECT to_char(to_timestamp(created_at) AT TIME ZONE 'UTC','YYYY-MM-DD') AS day,count(*) AS total FROM inspections WHERE user_id=%s AND created_at>=%s GROUP BY day",
                (user["id"], start),
            ).fetchall()
            totals = {row["day"]: row["total"] for row in trend}
            summary["trend"] = [
                {
                    "day": str(today - timedelta(days=6 - i)),
                    "total": totals.get(str(today - timedelta(days=6 - i)), 0),
                }
                for i in range(7)
            ]
            summary["recent_inspections"] = [
                inspection_record(r)
                for r in db.execute(
                    "SELECT * FROM inspections WHERE user_id=%s ORDER BY created_at DESC,sequence DESC LIMIT 5",
                    (user["id"],),
                ).fetchall()
            ]

        return summary


    @app.post("/api/inspections", status_code=201)
    async def inspect(
        file: UploadFile = File(...),
        confidence: float = Form(0.25, ge=0.05, le=0.95),
        user=Depends(current_user),
    ):

        content = await file.read(settings.max_upload + 1)
        await file.close()

        if len(content) > settings.max_upload:

            raise HTTPException(413, "Maximum upload size is 20 MB.")

        try:

            with warnings.catch_warnings():

                warnings.simplefilter("error", Image.DecompressionBombWarning)

                with Image.open(io.BytesIO(content)) as raw:

                    if raw.format not in {"PNG", "JPEG", "WEBP", "TIFF"}:

                        raise ValueError("Unsupported image format")

                    if raw.width * raw.height > 20_000_000:

                        raise ValueError("Image exceeds 20 megapixels")

                    image = ImageOps.exif_transpose(raw).convert("RGB")

        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ):

            raise HTTPException(
                422,
                "Upload a valid PNG, JPEG, TIFF or WebP image, up to 20 megapixels.",
            )

        try:

            detections, annotated, duration, sha = await run_in_threadpool(
                app.state.detector.predict, image, confidence
            )

        except ModelUnavailable as exc:

            raise HTTPException(503, str(exc))

        except Exception:

            logger.exception("PCB inference failed")

            raise HTTPException(
                503,
                "Inference failed. Ask an administrator to check the model runtime.",
            )

        inspection_id = str(uuid.uuid4())
        original = settings.data_dir / "images" / f"{inspection_id}.png"
        result = settings.data_dir / "images" / f"{inspection_id}-result.png"

        try:

            await run_in_threadpool(image.save, original, format="PNG")
            await run_in_threadpool(annotated.save, result, format="PNG")

            with connect(settings) as db:

                # Account may have been disabled while inference was running.

                if not db.execute(
                    "SELECT active FROM users WHERE id=%s", (user["id"],)
                ).fetchone()["active"]:

                    raise HTTPException(403, "Account disabled.")

                filename = Path((file.filename or "board").replace("\\", "/")).name[
                    :200
                ]
                db.execute(
                    "INSERT INTO inspections(id,user_id,filename,created_at,confidence,width,height,detections,duration_ms,model_sha256) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        inspection_id,
                        user["id"],
                        filename,
                        int(time.time()),
                        confidence,
                        image.width,
                        image.height,
                        Jsonb(detections),
                        duration,
                        sha,
                    ),
                )
                audit(db, user["id"], "inspection.created", inspection_id)

                return inspection_record(
                    db.execute(
                        "SELECT * FROM inspections WHERE id=%s", (inspection_id,)
                    ).fetchone()
                )

        except Exception:

            original.unlink(missing_ok=True)
            result.unlink(missing_ok=True)

            raise


    def get_inspection(inspection_id, user):

        with connect(settings) as db:

            row = db.execute(
                "SELECT * FROM inspections WHERE id=%s", (inspection_id,)
            ).fetchone()

        if not row or (row["user_id"] != user["id"] and user["role"] != "admin"):

            raise HTTPException(404, "Inspection not found.")

        return row


    @app.get("/api/inspections/{inspection_id}")
    def detail(inspection_id: uuid.UUID, user=Depends(current_user)):

        return inspection_record(get_inspection(str(inspection_id), user))


    @app.get("/api/inspections/{inspection_id}/image")
    def inspection_image(
        inspection_id: uuid.UUID, original: bool = False, user=Depends(current_user)
    ):

        get_inspection(str(inspection_id), user)
        path = (
            settings.data_dir
            / "images"
            / f"{inspection_id}{'' if original else '-result'}.png"
        )

        if not path.is_file():

            raise HTTPException(404, "Image file is unavailable.")

        return FileResponse(path, media_type="image/png")


    @app.get("/api/admin/overview")
    def overview(user=Depends(admin_user)):

        with connect(settings) as db:

            counts = dict(
                db.execute(
                    "SELECT count(*) AS users, count(*) FILTER (WHERE active) AS active_users, count(*) FILTER (WHERE role='admin') AS admins FROM users"
                ).fetchone()
            )
            counts["inspections"] = db.execute(
                "SELECT count(*) AS total FROM inspections"
            ).fetchone()["total"]
            rows = db.execute(
                "SELECT detections,duration_ms FROM inspections"
            ).fetchall()
            labels = {}

            for row in rows:

                for detection in row["detections"]:

                    labels[detection["label"]] = labels.get(detection["label"], 0) + 1

            counts["defects"] = sum(labels.values())
            counts["class_counts"] = labels
            counts["average_duration_ms"] = (
                round(sum(r["duration_ms"] for r in rows) / len(rows), 1) if rows else 0
            )
            counts["recent_inspections"] = [
                inspection_record(r)
                for r in db.execute(
                    "SELECT i.*,u.name AS user_name FROM inspections i JOIN users u ON i.user_id=u.id ORDER BY i.created_at DESC,i.sequence DESC LIMIT 10"
                ).fetchall()
            ]
            counts["audit"] = [
                dict(r)
                for r in db.execute(
                    "SELECT a.*,u.name AS actor_name FROM audit a LEFT JOIN users u ON a.actor_id=u.id ORDER BY a.id DESC LIMIT 30"
                ).fetchall()
            ]

        return counts


    @app.get("/api/admin/users")
    def users(
        q: str = Query("", max_length=80),
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
        user=Depends(admin_user),
    ):

        search = f"%{q}%"

        with connect(settings) as db:

            total = db.execute(
                "SELECT count(*) AS total FROM users WHERE name ILIKE %s OR email ILIKE %s",
                (search, search),
            ).fetchone()["total"]
            rows = db.execute(
                "SELECT u.*, (SELECT count(*) FROM inspections i WHERE i.user_id=u.id) AS inspection_count FROM users u WHERE name ILIKE %s OR email ILIKE %s ORDER BY created_at DESC,u.id DESC LIMIT %s OFFSET %s",
                (search, search, limit, offset),
            ).fetchall()

        return {
            "items": [
                {**public_user(r), "inspection_count": r["inspection_count"]}
                for r in rows
            ],
            "total": total,
        }


    @app.patch("/api/admin/users/{user_id}")
    def update_user(user_id: uuid.UUID, body: UserUpdate, user=Depends(admin_user)):

        user_id = str(user_id)

        with connect(settings) as db:

            db.execute("SELECT pg_advisory_xact_lock(181904314)")
            target = db.execute(
                "SELECT * FROM users WHERE id=%s", (user_id,)
            ).fetchone()

            if not target:

                raise HTTPException(404, "User not found.")

            if user_id == user["id"] and (not body.active or body.role != "admin"):

                raise HTTPException(
                    400, "You cannot disable or demote your own administrator account."
                )

            if (
                target["active"]
                and target["role"] == "admin"
                and (not body.active or body.role != "admin")
            ):

                if (
                    db.execute(
                        "SELECT count(*) AS total FROM users WHERE active=TRUE AND role='admin'"
                    ).fetchone()["total"]
                    <= 1
                ):

                    raise HTTPException(
                        400, "At least one active administrator is required."
                    )

            db.execute(
                "UPDATE users SET role=%s,active=%s WHERE id=%s",
                (body.role, body.active, user_id),
            )

            if not body.active or body.role != target["role"]:

                db.execute("DELETE FROM sessions WHERE user_id=%s", (user_id,))

            audit(
                db,
                user["id"],
                f"account.updated role={body.role} active={body.active}",
                user_id,
            )

            return public_user(
                db.execute("SELECT * FROM users WHERE id=%s", (user_id,)).fetchone()
            )


    dist = ROOT / "frontend/dist"

    if dist.is_dir():

        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/", include_in_schema=False)
        @app.get("/analyze", include_in_schema=False)
        @app.get("/dashboard", include_in_schema=False)
        @app.get("/history", include_in_schema=False)
        @app.get("/model", include_in_schema=False)
        @app.get("/admin", include_in_schema=False)
        @app.get("/account", include_in_schema=False)
        @app.get("/guide", include_in_schema=False)
        @app.get("/privacy", include_in_schema=False)
        @app.get("/auth/login", include_in_schema=False)
        @app.get("/auth/register", include_in_schema=False)
        def frontend():

            return FileResponse(dist / "index.html")


    return app



app = create_app()
