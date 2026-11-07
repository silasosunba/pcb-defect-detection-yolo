import hashlib
import secrets
import time

from fastapi import HTTPException, Request
from pwdlib import PasswordHash

from backend.db import connect

passwords = PasswordHash.recommended()
DUMMY_HASH = passwords.hash("unused-password-for-timing")
COOKIE = "pcb_session"


def digest(token):

    return hashlib.sha256(token.encode()).hexdigest()



def public_user(row):

    return {
        k: row[k]
        for k in ("id", "name", "email", "role", "active", "created_at", "last_login")
    }



def current_user(request: Request):

    token = request.cookies.get(COOKIE, "")

    with connect(request.app.state.settings) as db:

        user = db.execute(
            "SELECT u.* FROM users u JOIN sessions s ON u.id=s.user_id WHERE s.token_hash=%s AND s.expires_at>%s AND u.active=TRUE",
            (digest(token), int(time.time())),
        ).fetchone()

    if user is None:

        raise HTTPException(401, "Please sign in to continue.")

    return public_user(user)



def admin_user(request: Request):

    user = current_user(request)

    if user["role"] != "admin":

        raise HTTPException(403, "Administrator access required.")

    return user



def start_session(db, user_id, response, settings, remember_me=False):

    token = secrets.token_urlsafe(48)
    now = int(time.time())
    db.execute("DELETE FROM sessions WHERE expires_at<=%s", (now,))
    lifetime = 30 * 86400 if remember_me else settings.session_seconds
    db.execute(
        "INSERT INTO sessions VALUES (%s,%s,%s)",
        (digest(token), user_id, now + lifetime),
    )
    response.set_cookie(
        COOKIE,
        token,
        max_age=lifetime if remember_me else None,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="strict",
        path="/",
    )



def audit(db, actor, action, target):

    db.execute(
        "INSERT INTO audit(actor_id,action,target,created_at) VALUES (%s,%s,%s,%s)",
        (actor, action, target, int(time.time())),
    )
