import hashlib
import json
import time
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .db import audit, engine, jobs, orders
from .schemas import OrderInput


def uid():
    return str(uuid4())


def record_audit(conn, org_id, actor, action, detail):
    conn.execute(
        audit.insert().values(
            id=uid(),
            org_id=org_id,
            actor=actor,
            action=action,
            detail=detail[:240],
            created_at=time.time(),
        )
    )


def accept_order(org_id: str, data: OrderInput, actor: str) -> dict:
    payload = data.model_dump(mode="json")
    payload["amount"] = str(data.amount.quantize(__import__("decimal").Decimal("0.01")))
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    order_id, now = uid(), time.time()
    try:
        with engine.begin() as conn:
            conn.execute(
                orders.insert().values(
                    id=order_id,
                    org_id=org_id,
                    event_id=data.event_id,
                    reference=data.reference,
                    customer=data.customer,
                    amount_cents=int(data.amount * 100),
                    currency=data.currency,
                    payload_hash=fingerprint,
                    created_at=now,
                )
            )
            # This row is the durable outbox. Broker dispatch never deletes it.
            conn.execute(
                jobs.insert().values(
                    id=uid(),
                    org_id=org_id,
                    order_id=order_id,
                    status="pending",
                    attempts=0,
                    max_attempts=3,
                    next_attempt_at=now,
                    updated_at=now,
                )
            )
            record_audit(conn, org_id, actor, "order.accepted", data.reference)
        return {"id": order_id, "duplicate": False}
    except IntegrityError:
        with engine.connect() as conn:
            row = (
                conn.execute(
                    select(orders).where(
                        orders.c.org_id == org_id,
                        orders.c.event_id == data.event_id,
                    )
                )
                .mappings()
                .first()
            )
        if row and row["payload_hash"] == fingerprint:
            return {"id": row["id"], "duplicate": True}
        raise HTTPException(409, "This event or order reference already exists with different data.")
