"""A database outbox makes Redis failures recoverable. Claims are atomic."""

import logging
import time
import httpx
from celery import Celery
from sqlalchemy import and_, or_, select, update
from .config import settings
from .db import attempts, connectors, engine, jobs, orders
from .services import record_audit, uid

log = logging.getLogger(__name__)
celery = Celery("bridgesync", broker=settings.redis_url)
celery.conf.update(
    task_ignore_result=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={"dispatch-outbox": {"task": "dispatch", "schedule": 5.0}},
)


def eligible(now):
    return or_(
        and_(jobs.c.status.in_(["pending", "retrying"]), jobs.c.next_attempt_at <= now),
        and_(jobs.c.status == "running", jobs.c.lease_until < now),
    )


def deliver(job_id: str, transport=None) -> bool:
    now, token = time.time(), uid()
    with engine.begin() as conn:
        result = conn.execute(
            update(jobs)
            .where(
                jobs.c.id == job_id,
                eligible(now),
            )
            .values(
                status="running",
                lease_until=now + 120,
                lease_token=token,
                attempts=jobs.c.attempts + 1,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            return False
        job = conn.execute(select(jobs).where(jobs.c.id == job_id)).mappings().one()
        order = conn.execute(select(orders).where(orders.c.id == job["order_id"])).mappings().one()
        mode = conn.execute(
            select(connectors.c.mode).where(connectors.c.org_id == job["org_id"])
        ).scalar_one()
    started = time.monotonic()
    error, transient = None, False
    try:
        with httpx.Client(timeout=10, transport=transport, follow_redirects=False, trust_env=False) as client:
            response = client.post(
                settings.connector_url,
                json={
                    "id": order["id"],
                    "reference": order["reference"],
                    "customer": order["customer"],
                    "amount_cents": order["amount_cents"],
                    "currency": order["currency"],
                },
                headers={
                    "Authorization": "Bearer " + settings.connector_token,
                    "Idempotency-Key": job["org_id"] + ":" + order["id"],
                    "X-Demo-Mode": mode,
                },
            )
        if not 200 <= response.status_code < 300:
            error = f"Connector returned HTTP {response.status_code}."
            transient = response.status_code in (408, 429) or response.status_code >= 500
    except (httpx.TimeoutException, httpx.NetworkError):
        error, transient = "Connector unavailable or request timed out.", True
    except httpx.HTTPError:
        error = "Connector request could not be completed."
    retry = bool(error and transient and job["attempts"] < job["max_attempts"])
    status = "retrying" if retry else "failed" if error else "succeeded"
    with engine.begin() as conn:
        updated = conn.execute(
            update(jobs)
            .where(
                jobs.c.id == job_id,
                jobs.c.lease_token == token,
            )
            .values(
                status=status,
                last_error=error,
                lease_until=None,
                lease_token=None,
                next_attempt_at=time.time() + min(300, 5 * 2 ** min(job["attempts"], 6)),
                updated_at=time.time(),
            )
        )
        if updated.rowcount != 1:
            return False
        conn.execute(
            attempts.insert().values(
                id=uid(),
                org_id=job["org_id"],
                job_id=job_id,
                number=job["attempts"],
                outcome=status,
                detail=error or "Accepted by the test connector.",
                duration_ms=int((time.monotonic() - started) * 1000),
                created_at=time.time(),
            )
        )
        record_audit(conn, job["org_id"], "worker", "delivery." + status, order["reference"])
    log.info("delivery completed job=%s status=%s", job_id, status)
    return True


@celery.task(name="deliver")
def delivery_task(job_id):
    deliver(job_id)


@celery.task(name="dispatch")
def dispatch():
    with engine.connect() as conn:
        ids = conn.execute(select(jobs.c.id).where(eligible(time.time())).limit(100)).scalars().all()
    for job_id in ids:
        delivery_task.delay(job_id)


if __name__ == "__main__":
    # Local development without Redis; the same claim and delivery code.
    logging.basicConfig(level=logging.INFO)
    while True:
        with engine.connect() as conn:
            ids = conn.execute(select(jobs.c.id).where(eligible(time.time())).limit(100)).scalars().all()
        for job_id in ids:
            deliver(job_id)
        time.sleep(2)
