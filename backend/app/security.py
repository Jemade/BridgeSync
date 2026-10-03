import hashlib
import hmac
import secrets
import time
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from .db import api_keys, engine, sessions, users


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return salt.hex() + ":" + key.hex()


def verify_password(password: str, stored: str) -> bool:
    salt, expected = stored.split(":")
    actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
    return hmac.compare_digest(actual.hex(), expected)


def current_user(request: Request) -> dict:
    token = request.cookies.get("bridgesync_session")
    if not token:
        raise HTTPException(401, "Sign in to continue.")
    with engine.connect() as conn:
        row = (
            conn.execute(
                select(users)
                .join(sessions)
                .where(
                    sessions.c.token_hash == digest(token),
                    sessions.c.expires_at > time.time(),
                    users.c.active.is_(True),
                )
            )
            .mappings()
            .first()
        )
    if not row:
        raise HTTPException(401, "Your session has expired. Sign in again.")
    return dict(row)


def writer(user: dict = Depends(current_user)) -> dict:
    if user["role"] not in ("admin", "operator"):
        raise HTTPException(403, "This action requires an operator or administrator.")
    return user


def admin(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "This action requires an administrator.")
    return user


def webhook_org(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "An integration API key is required.")
    with engine.connect() as conn:
        row = conn.execute(
            select(api_keys.c.org_id).where(
                api_keys.c.token_hash == digest(auth[7:]),
                api_keys.c.revoked.is_(False),
            )
        ).first()
    if not row:
        raise HTTPException(401, "The integration API key is invalid.")
    return row[0]
