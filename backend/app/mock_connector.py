"""A durable, idempotent test destination; never claims to be a real ERP."""

import hashlib
import json
import os
import sqlite3
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from .config import settings

app = FastAPI(title="BridgeSync test connector")
database = os.getenv("MOCK_DATABASE", "./connector.db")


class Incoming(BaseModel):
    id: str
    reference: str
    customer: str
    amount_cents: int = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")


@app.post("/orders")
def receive(
    data: Incoming,
    authorization: str = Header(""),
    idempotency_key: str = Header(""),
    x_demo_mode: str = Header("available"),
):
    import hmac

    if not settings.connector_token or not hmac.compare_digest(
        authorization, "Bearer " + settings.connector_token
    ):
        raise HTTPException(401, "Invalid connector credential")
    if x_demo_mode == "outage":
        raise HTTPException(503, "Simulated temporary outage")
    if x_demo_mode == "reject":
        raise HTTPException(422, "Simulated permanent rejection")
    if not idempotency_key or len(idempotency_key) > 160:
        raise HTTPException(422, "Idempotency key required")
    payload = json.dumps(data.model_dump(), sort_keys=True)
    fingerprint = hashlib.sha256(payload.encode()).hexdigest()
    with sqlite3.connect(database, timeout=30) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS received (key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, payload TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO received VALUES (?, ?, ?)", (idempotency_key, fingerprint, payload)
        )
        existing = conn.execute(
            "SELECT fingerprint FROM received WHERE key=?", (idempotency_key,)
        ).fetchone()[0]
        if existing != fingerprint:
            raise HTTPException(409, "Key reused with different data")
    return {"accepted": True, "reference": data.reference}
