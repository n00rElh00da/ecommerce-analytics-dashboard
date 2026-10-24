import time
from datetime import datetime, timezone

import jwt
from fastapi import Depends, HTTPException, Request

from . import config
from .db import shared_db
from .roles import role_for_email

COOKIE = "session"
SESSION_SECONDS = 8 * 3600


def db_dep():
    return shared_db()


def verify_google_credential(credential):
    """Verify a Google ID token (signature, audience, expiry). Raises ValueError if invalid."""
    from google.auth.transport import requests as g_requests
    from google.oauth2 import id_token
    info = id_token.verify_oauth2_token(credential, g_requests.Request(), config.GOOGLE_CLIENT_ID)
    if not info.get("email_verified") or not info.get("email"):
        raise ValueError("Google email is not verified")
    return info


def upsert_user(db, info):
    now = datetime.now(timezone.utc)
    db.users.update_one(
        {"google_sub": info["sub"]},
        {"$set": {"email": info["email"].lower(), "name": info.get("name") or info["email"],
                  "picture": info.get("picture"), "last_login": now},
         "$setOnInsert": {"created_at": now}},
        upsert=True)
    return db.users.find_one({"google_sub": info["sub"]}, {"_id": 0})


def make_session_token(sub):
    return jwt.encode({"sub": sub, "exp": int(time.time()) + SESSION_SECONDS}, config.JWT_SECRET, algorithm="HS256")


def public(user):
    return {"email": user["email"], "name": user["name"], "picture": user.get("picture"),
            "role": role_for_email(user["email"])}


def current_user(request: Request, db=Depends(db_dep)):
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Not signed in")
    try:
        sub = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])["sub"]
    except jwt.PyJWTError:
        raise HTTPException(401, "Session expired or invalid. Sign in again.")
    user = db.users.find_one({"google_sub": sub}, {"_id": 0})
    if not user:
        raise HTTPException(401, "Account not found. Sign in again.")
    user["role"] = role_for_email(user["email"])  # re-evaluated from env on every request
    return user


def require_admin(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "Administrator access required")
    return user
