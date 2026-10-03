import io
import time
from concurrent.futures import ThreadPoolExecutor
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from app.db import engine, jobs, orders
from app.main import app
from app.schemas import OrderInput
from app.services import accept_order
from app.worker import deliver
from conftest import HEADER, PASSWORD

PAYLOAD = {
    "event_id": "evt-001",
    "reference": "ORD-001",
    "customer": "Test retailer",
    "amount": "129.00",
    "currency": "USD",
}


def create(client, **changes):
    r = client.post("/api/orders", json=PAYLOAD | changes)
    assert r.status_code == 201, r.text
    with engine.connect() as conn:
        job = conn.execute(select(jobs.c.id).where(jobs.c.order_id == r.json()["id"])).scalar_one()
    return r.json(), job


def csv_upload(client, rows):
    return client.post(
        "/api/payments/import",
        files={
            "file": (
                "payments.csv",
                io.BytesIO(("reference,order_reference,amount,currency\n" + rows).encode()),
                "text/csv",
            )
        },
    )


def test_acceptance_is_atomic_and_duplicates_are_stable(client):
    first, _ = create(client)
    repeat, _ = create(client, amount="129")
    assert repeat["duplicate"] and repeat["id"] == first["id"]
    with engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(orders)).scalar_one() == 1
        assert conn.execute(select(func.count()).select_from(jobs)).scalar_one() == 1
    assert client.post("/api/orders", json=PAYLOAD | {"amount": "130.00"}).status_code == 409
    assert client.post("/api/orders", json=PAYLOAD | {"event_id": "other"}).status_code == 409


def test_parallel_duplicate_acceptance(org):
    data = OrderInput(**PAYLOAD)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: accept_order(org, data, "test"), range(12)))
    assert len({r["id"] for r in results}) == 1
    assert sum(not r["duplicate"] for r in results) == 1


def test_order_and_outbox_rollback_together(org, monkeypatch):
    import app.services as services

    def fail(*args):
        raise RuntimeError("Simulated audit write failure")

    monkeypatch.setattr(services, "record_audit", fail)
    import pytest

    with pytest.raises(RuntimeError):
        accept_order(org, OrderInput(**PAYLOAD), "test")
    with engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(orders)).scalar_one() == 0
        assert conn.execute(select(func.count()).select_from(jobs)).scalar_one() == 0


def test_delivery_success_and_duplicate_worker_tasks(client):
    _, job = create(client)
    seen = []

    def receiver(req):
        seen.append(req.headers["Idempotency-Key"])
        return httpx.Response(200, json={"accepted": True})

    transport = httpx.MockTransport(receiver)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: deliver(job, transport), range(4)))
    assert len(seen) == 1
    detail = client.get("/api/jobs/" + job).json()
    assert detail["job"]["status"] == "succeeded"
    assert len(detail["attempts"]) == 1


def test_temporary_failure_retries_then_recovers(client):
    _, job = create(client)
    deliver(job, httpx.MockTransport(lambda r: httpx.Response(503)))
    assert client.get("/api/jobs/" + job).json()["job"]["status"] == "retrying"
    # Retry is not eligible before its backoff expires.
    assert not deliver(job, httpx.MockTransport(lambda r: httpx.Response(200)))
    with engine.begin() as conn:
        conn.execute(update(jobs).where(jobs.c.id == job).values(next_attempt_at=0))
    deliver(job, httpx.MockTransport(lambda r: httpx.Response(200)))
    detail = client.get("/api/jobs/" + job).json()
    assert detail["job"]["status"] == "succeeded"
    assert detail["job"]["attempts"] == 2


def test_permanent_failure_requires_manual_retry(client):
    _, job = create(client)
    deliver(job, httpx.MockTransport(lambda r: httpx.Response(422)))
    assert client.get("/api/jobs/" + job).json()["job"]["status"] == "failed"
    assert client.post("/api/jobs/" + job + "/retry").status_code == 200
    assert client.post("/api/jobs/" + job + "/retry").status_code == 409
    deliver(job, httpx.MockTransport(lambda r: httpx.Response(200)))
    assert client.get("/api/jobs/" + job).json()["job"]["status"] == "succeeded"


def test_retry_exhaustion_and_expired_lease_recovery(client):
    _, job = create(client)
    transport = httpx.MockTransport(lambda r: httpx.Response(503))
    for _ in range(3):
        with engine.begin() as conn:
            conn.execute(update(jobs).where(jobs.c.id == job).values(next_attempt_at=0))
        deliver(job, transport)
    assert client.get("/api/jobs/" + job).json()["job"]["status"] == "failed"
    with engine.begin() as conn:
        conn.execute(
            update(jobs).where(jobs.c.id == job).values(status="running", lease_until=time.time() - 1)
        )
    assert deliver(job, httpx.MockTransport(lambda r: httpx.Response(200)))
    assert client.get("/api/jobs/" + job).json()["job"]["status"] == "succeeded"


def test_timeout_is_a_transient_failure(client):
    _, job = create(client)

    def timeout(r):
        raise httpx.ReadTimeout("upstream timeout")

    deliver(job, httpx.MockTransport(timeout))
    assert client.get("/api/jobs/" + job).json()["job"]["status"] == "retrying"


def test_tenant_isolation_across_orders_jobs_keys_and_members(client):
    _, job = create(client)
    key = client.post("/api/keys", json={"name": "store"}).json()
    member = client.post(
        "/api/members",
        json={"name": "Viewer", "email": "viewer@example.com", "password": PASSWORD, "role": "viewer"},
    )
    assert member.status_code == 201
    member_id = next(m["id"] for m in client.get("/api/members").json() if m["email"] == "viewer@example.com")
    with TestClient(app, headers=HEADER) as other:
        other.post("/api/auth/login", json={"email": "other@example.com", "password": PASSWORD})
        assert other.get("/api/orders").json()["total"] == 0
        assert other.get("/api/jobs/" + job).status_code == 404
        assert other.post("/api/jobs/" + job + "/retry").status_code == 409
        assert other.delete("/api/keys/" + key["id"]).status_code == 404
        assert other.delete("/api/members/" + member_id).status_code == 404
        assert other.get("/api/audit").json()["total"] == 0


def test_viewer_cannot_modify_and_disabled_session_is_revoked(client):
    client.post(
        "/api/members",
        json={"name": "Viewer", "email": "viewer@example.com", "password": PASSWORD, "role": "viewer"},
    )
    member = next(m for m in client.get("/api/members").json() if m["email"] == "viewer@example.com")
    with TestClient(app, headers=HEADER) as viewer:
        viewer.post("/api/auth/login", json={"email": "viewer@example.com", "password": PASSWORD})
        assert viewer.get("/api/orders").status_code == 200
        assert viewer.post("/api/orders", json=PAYLOAD).status_code == 403
        assert viewer.get("/api/keys").status_code == 403
        assert viewer.put("/api/connector", json={"mode": "outage"}).status_code == 403
        client.delete("/api/members/" + member["id"])
        assert viewer.get("/api/me").status_code == 401


def test_webhook_key_is_scoped_revocable_and_cannot_read(client):
    key = client.post("/api/keys", json={"name": "store"}).json()
    with TestClient(app) as integration:
        headers = {"Authorization": "Bearer " + key["token"]}
        assert integration.post("/api/webhooks/orders", headers=headers, json=PAYLOAD).status_code == 202
        assert integration.get("/api/orders", headers=headers).status_code == 401
        client.delete("/api/keys/" + key["id"])
        assert integration.post("/api/webhooks/orders", headers=headers, json=PAYLOAD).status_code == 401


def test_csrf_guard_logout_and_failed_login_throttle(client):
    assert client.post("/api/orders", headers={"X-BridgeSync-Request": ""}, json=PAYLOAD).status_code == 403
    assert client.delete("/api/members/" + client.get("/api/me").json()["id"]).status_code == 422
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/me").status_code == 401
    for _ in range(10):
        assert (
            client.post(
                "/api/auth/login", json={"email": "missing@example.com", "password": "bad"}
            ).status_code
            == 401
        )
    assert (
        client.post("/api/auth/login", json={"email": "missing@example.com", "password": "bad"}).status_code
        == 429
    )


def test_payment_import_matches_and_duplicates_are_ignored(client):
    create(client)
    text = "PAY-1,ORD-001,129.00,USD\nPAY-2,ORD-001,128.00,USD\nPAY-3,ORD-404,10.00,USD\n"
    result = csv_upload(client, text)
    assert result.status_code == 200
    assert result.json() == {"imported": 3, "duplicates": 0, "matched": 1, "mismatch": 1, "unmatched": 1}
    assert csv_upload(client, text).json()["duplicates"] == 3


def test_invalid_csv_is_atomic_and_money_validation_is_exact(client):
    result = csv_upload(client, "GOOD,ORD-001,10.00,USD\nBAD,ORD-002,NaN,USD\n")
    assert result.status_code == 422 and result.json()["errors"][0]["row"] == 3
    assert client.get("/api/payments").json()["total"] == 0
    for amount in ["-1", "0", "1.001", "Infinity"]:
        assert client.post("/api/orders", json=PAYLOAD | {"amount": amount}).status_code == 422
    assert client.post("/api/orders", json=PAYLOAD | {"customer": "  "}).status_code == 422


def test_matching_requires_exact_currency_and_amount_and_is_tenant_scoped(client):
    create(client)
    csv_upload(client, "PAY-1,ORD-404,129.00,USD\nPAY-2,ORD-001,129.00,ZAR\n")
    records = client.get("/api/payments").json()["items"]
    usd = next(p for p in records if p["currency"] == "USD")
    zar = next(p for p in records if p["currency"] == "ZAR")
    assert (
        client.post("/api/payments/" + zar["id"] + "/match", json={"order_reference": "ORD-001"}).status_code
        == 422
    )
    assert (
        client.post("/api/payments/" + usd["id"] + "/match", json={"order_reference": "ORD-001"}).status_code
        == 200
    )
    with TestClient(app, headers=HEADER) as other:
        other.post("/api/auth/login", json={"email": "other@example.com", "password": PASSWORD})
        assert (
            other.post(
                "/api/payments/" + usd["id"] + "/match", json={"order_reference": "ORD-001"}
            ).status_code
            == 404
        )


def test_pagination_search_and_currency_totals(client):
    for i in range(23):
        create(client, event_id=f"evt-{i}", reference=f"REF-{i}", currency="ZAR" if i % 2 else "USD")
    assert len(client.get("/api/orders?page=1").json()["items"]) == 20
    assert len(client.get("/api/orders?page=2").json()["items"]) == 3
    assert client.get("/api/orders?q=%25").json()["total"] == 0
    assert {t["currency"] for t in client.get("/api/overview").json()["totals"]} == {"USD", "ZAR"}


def test_receiver_deduplicates_even_after_response_loss(tmp_path, monkeypatch):
    import app.mock_connector as receiver

    monkeypatch.setattr(receiver, "database", str(tmp_path / "sink.db"))
    headers = {"Authorization": "Bearer test-only-connector-token", "Idempotency-Key": "organisation:order"}
    payload = {
        "id": "order",
        "reference": "ORD-001",
        "customer": "Test",
        "amount_cents": 12900,
        "currency": "USD",
    }
    with TestClient(receiver.app) as sink:
        assert sink.post("/orders", json=payload, headers=headers).status_code == 200
        assert sink.post("/orders", json=payload, headers=headers).status_code == 200
        assert (
            sink.post("/orders", json=payload | {"amount_cents": 13000}, headers=headers).status_code == 409
        )
    import sqlite3

    with sqlite3.connect(receiver.database) as conn:
        assert conn.execute("SELECT COUNT(*) FROM received").fetchone()[0] == 1


def test_conflicting_payment_reference_rolls_back_entire_import(client):
    create(client)
    assert csv_upload(client, "EXISTING,ORD-001,129.00,USD\n").status_code == 200
    assert csv_upload(client, "NEW,ORD-001,129.00,USD\nEXISTING,ORD-001,128.00,USD\n").status_code == 409
    assert client.get("/api/payments").json()["total"] == 1


def test_large_amount_remains_exact(client):
    create(client, amount="9999999999.99")
    assert client.get("/api/orders").json()["items"][0]["amount_cents"] == 999999999999


def test_broker_failure_does_not_remove_outbox_job(client, monkeypatch):
    from app.worker import dispatch, delivery_task
    import pytest

    _, job = create(client)

    def unavailable(*args):
        raise ConnectionError("broker unavailable")

    monkeypatch.setattr(delivery_task, "delay", unavailable)
    with pytest.raises(ConnectionError):
        dispatch()
    assert client.get("/api/jobs/" + job).json()["job"]["status"] == "pending"
