"""Tenant-scoped HTTP API and the production frontend entry point."""

import csv
import io
import secrets
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from sqlalchemy import case, delete, func, select, update
from sqlalchemy.exc import IntegrityError
from .config import settings
from .db import (
    api_keys,
    attempts,
    audit,
    connectors,
    engine,
    jobs,
    login_attempts,
    orders,
    organisations,
    payments,
    sessions,
    users,
)
from .schemas import ConnectorInput, KeyInput, Login, MatchInput, MemberInput, OrderInput
from .security import admin, current_user, digest, hash_password, verify_password, webhook_org, writer
from .services import accept_order, record_audit, uid

app = FastAPI(title="BridgeSync", version="1.0.0")


def schema():
    if app.openapi_schema:
        return app.openapi_schema
    result = get_openapi(title=app.title, version=app.version, routes=app.routes)
    for path, operations in result["paths"].items():
        for method, operation in operations.items():
            if method not in ("post", "put", "patch", "delete"):
                continue
            if path == "/api/webhooks/orders":
                operation.setdefault("parameters", []).append(
                    {
                        "name": "Authorization",
                        "in": "header",
                        "required": True,
                        "schema": {"type": "string"},
                        "description": "Bearer bs_YOUR_INTEGRATION_KEY",
                    }
                )
            else:
                operation.setdefault("parameters", []).append(
                    {
                        "name": "X-BridgeSync-Request",
                        "in": "header",
                        "required": True,
                        "schema": {"type": "string", "default": "browser"},
                    }
                )
    app.openapi_schema = result
    return result


app.openapi = schema


@app.middleware("http")
async def guard(request: Request, call_next):
    request_id = str(uuid4())
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        if (
            request.url.path != "/api/webhooks/orders"
            and request.headers.get("x-bridgesync-request") != "browser"
        ):
            return JSONResponse({"detail": "The required request header is missing."}, status_code=403)
        length = request.headers.get("content-length")
        if length is None and request.headers.get("transfer-encoding"):
            return JSONResponse({"detail": "Content-Length is required."}, status_code=411)
        if length is not None and (not length.isdigit() or int(length) > 2_000_000):
            return JSONResponse({"detail": "Request exceeds the 2 MB limit."}, status_code=413)
    response = await call_next(request)
    response.headers.update(
        {
            "X-Request-ID": request_id,
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "same-origin",
            "X-Frame-Options": "DENY",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'",
        }
    )
    if request.url.path in ("/docs", "/redoc"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; connect-src 'self'; frame-ancestors 'none'"
        )
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health")
def health():
    with engine.connect() as conn:
        conn.execute(select(1))
    return {"status": "ok", "version": "1.0.0"}


@app.post("/api/auth/login")
def login(data: Login, request: Request, response: Response):
    email = data.email.strip().lower()
    now = time.time()
    key = digest((request.client.host if request.client else "unknown") + ":" + email)
    with engine.begin() as conn:
        # Atomic upsert prevents parallel attempts from bypassing the counter.
        if engine.dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import insert
        else:
            from sqlalchemy.dialects.sqlite import insert
        stmt = insert(login_attempts).values(key=key, count=1, window_start=now)
        stmt = stmt.on_conflict_do_update(
            index_elements=["key"],
            set_={
                "count": case(
                    (login_attempts.c.window_start < now - 900, 1), else_=login_attempts.c.count + 1
                ),
                "window_start": case(
                    (login_attempts.c.window_start < now - 900, now), else_=login_attempts.c.window_start
                ),
            },
        )
        conn.execute(stmt)
        count = conn.execute(select(login_attempts.c.count).where(login_attempts.c.key == key)).scalar_one()
        row = (
            conn.execute(select(users).where(users.c.email == email, users.c.active.is_(True)))
            .mappings()
            .first()
        )
    if count > 10:
        raise HTTPException(429, "Too many sign-in attempts. Try again in 15 minutes.")
    # Perform a comparable password operation for unknown accounts.
    valid = (
        verify_password(data.password, row["password_hash"])
        if row
        else verify_password(data.password, "00" * 16 + ":" + "00" * 64)
    )
    if not row or not valid:
        raise HTTPException(401, "Email or password is incorrect.")
    token = secrets.token_urlsafe(32)
    with engine.begin() as conn:
        conn.execute(delete(login_attempts).where(login_attempts.c.key == key))
        conn.execute(delete(sessions).where(sessions.c.expires_at < now))
        conn.execute(
            sessions.insert().values(
                token_hash=digest(token), user_id=row["id"], expires_at=now + settings.session_hours * 3600
            )
        )
    response.set_cookie(
        "bridgesync_session",
        token,
        httponly=True,
        secure=settings.secure_cookie,
        samesite="strict",
        max_age=settings.session_hours * 3600,
        path="/",
    )
    return {"name": row["name"], "role": row["role"]}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response, user=Depends(current_user)):
    with engine.begin() as conn:
        conn.execute(
            delete(sessions).where(
                sessions.c.token_hash == digest(request.cookies.get("bridgesync_session", ""))
            )
        )
    response.delete_cookie("bridgesync_session", path="/")
    return {"ok": True}


@app.get("/api/me")
def me(user=Depends(current_user)):
    with engine.connect() as conn:
        name = conn.execute(
            select(organisations.c.name).where(organisations.c.id == user["org_id"])
        ).scalar_one()
    return {k: user[k] for k in ("id", "name", "email", "role")} | {"organisation": name}


@app.get("/api/overview")
def overview(user=Depends(current_user)):
    org = user["org_id"]
    with engine.connect() as conn:
        states = dict(
            conn.execute(
                select(jobs.c.status, func.count()).where(jobs.c.org_id == org).group_by(jobs.c.status)
            ).all()
        )
        payment_states = dict(
            conn.execute(
                select(payments.c.status, func.count())
                .where(payments.c.org_id == org)
                .group_by(payments.c.status)
            ).all()
        )
        currencies = conn.execute(
            select(orders.c.currency, func.sum(orders.c.amount_cents))
            .where(orders.c.org_id == org)
            .group_by(orders.c.currency)
        ).all()
    return {
        "orders": sum(states.values()),
        "synced": states.get("succeeded", 0),
        "pending": sum(states.get(s, 0) for s in ("pending", "running", "retrying")),
        "failed": states.get("failed", 0),
        "payment_exceptions": sum(payment_states.get(s, 0) for s in ("mismatch", "unmatched")),
        "totals": [{"currency": c, "amount_cents": v} for c, v in currencies],
    }


@app.post("/api/orders", status_code=201)
def create_order(data: OrderInput, user=Depends(writer)):
    return accept_order(user["org_id"], data, user["email"])


@app.post("/api/webhooks/orders", status_code=202)
def webhook(data: OrderInput, org=Depends(webhook_org)):
    return accept_order(org, data, "integration")


@app.get("/api/orders")
def list_orders(
    q: str = Query("", max_length=120),
    status: str = "",
    page: int = Query(1, ge=1),
    user=Depends(current_user),
):
    condition = [orders.c.org_id == user["org_id"]]
    if q:
        condition.append(or_search(q))
    if status:
        condition.append(jobs.c.status == status)
    joined = orders.join(jobs, orders.c.id == jobs.c.order_id)
    with engine.connect() as conn:
        total = conn.execute(select(func.count()).select_from(joined).where(*condition)).scalar_one()
        rows = (
            conn.execute(
                select(
                    orders.c.id,
                    orders.c.reference,
                    orders.c.customer,
                    orders.c.amount_cents,
                    orders.c.currency,
                    orders.c.created_at,
                    jobs.c.id.label("job_id"),
                    jobs.c.status,
                    jobs.c.attempts,
                    jobs.c.last_error,
                )
                .select_from(joined)
                .where(*condition)
                .order_by(orders.c.created_at.desc())
                .offset((page - 1) * 20)
                .limit(20)
            )
            .mappings()
            .all()
        )
    return {"items": [dict(r) for r in rows], "total": total, "page": page, "page_size": 20}


def or_search(q):
    from sqlalchemy import or_

    # Treat SQL wildcard characters literally.
    return or_(
        orders.c.reference.contains(q, autoescape=True), orders.c.customer.contains(q, autoescape=True)
    )


@app.get("/api/jobs/{job_id}")
def job_detail(job_id: str, user=Depends(current_user)):
    with engine.connect() as conn:
        job = (
            conn.execute(select(jobs).where(jobs.c.id == job_id, jobs.c.org_id == user["org_id"]))
            .mappings()
            .first()
        )
        if not job:
            raise HTTPException(404, "Job not found.")
        history = (
            conn.execute(
                select(attempts)
                .where(
                    attempts.c.job_id == job_id,
                    attempts.c.org_id == user["org_id"],
                )
                .order_by(attempts.c.created_at.desc())
            )
            .mappings()
            .all()
        )
    return {"job": dict(job), "attempts": [dict(r) for r in history]}


@app.post("/api/jobs/{job_id}/retry")
def retry_job(job_id: str, user=Depends(writer)):
    with engine.begin() as conn:
        changed = conn.execute(
            update(jobs)
            .where(
                jobs.c.id == job_id,
                jobs.c.org_id == user["org_id"],
                jobs.c.status == "failed",
            )
            .values(
                status="pending",
                next_attempt_at=time.time(),
                max_attempts=jobs.c.attempts + 3,
                last_error=None,
                updated_at=time.time(),
            )
        )
        if changed.rowcount != 1:
            raise HTTPException(409, "Only a failed job in your organisation can be retried.")
        record_audit(conn, user["org_id"], user["email"], "job.manual_retry", job_id)
    return {"ok": True}


@app.get("/api/connector")
def connector(user=Depends(current_user)):
    with engine.connect() as conn:
        mode = conn.execute(
            select(connectors.c.mode).where(connectors.c.org_id == user["org_id"])
        ).scalar_one()
    return {"name": "Test business system", "kind": "simulation", "mode": mode}


@app.put("/api/connector")
def set_connector(data: ConnectorInput, user=Depends(admin)):
    with engine.begin() as conn:
        conn.execute(update(connectors).where(connectors.c.org_id == user["org_id"]).values(mode=data.mode))
        record_audit(conn, user["org_id"], user["email"], "connector.mode_changed", data.mode)
    return {"mode": data.mode}


@app.get("/api/payments")
def list_payments(page: int = Query(1, ge=1), user=Depends(current_user)):
    with engine.connect() as conn:
        where = payments.c.org_id == user["org_id"]
        total = conn.execute(select(func.count()).select_from(payments).where(where)).scalar_one()
        rows = (
            conn.execute(
                select(payments)
                .where(where)
                .order_by(payments.c.created_at.desc())
                .offset((page - 1) * 20)
                .limit(20)
            )
            .mappings()
            .all()
        )
    return {"items": [dict(r) for r in rows], "total": total, "page": page, "page_size": 20}


def classify(conn, org, reference, amount, currency):
    order = (
        conn.execute(select(orders).where(orders.c.org_id == org, orders.c.reference == reference))
        .mappings()
        .first()
    )
    if not order:
        return None, "unmatched"
    if order["amount_cents"] != amount or order["currency"] != currency:
        return order["id"], "mismatch"
    return order["id"], "matched"


@app.post("/api/payments/import")
async def import_payments(file: UploadFile = File(...), user=Depends(writer)):
    raw = await file.read(1_000_001)
    if len(raw) > 1_000_000:
        raise HTTPException(413, "CSV files must be smaller than 1 MB.")
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        required = ["reference", "order_reference", "amount", "currency"]
        if reader.fieldnames != required:
            raise HTTPException(422, "Required CSV header: reference,order_reference,amount,currency")
        parsed, errors, seen = [], [], set()
        for number, row in enumerate(reader, 2):
            if number > 1001:
                raise HTTPException(422, "Import at most 1000 payments at a time.")
            try:
                data = OrderInput(
                    event_id=row["reference"],
                    reference=row["order_reference"],
                    customer="payment",
                    amount=Decimal(row["amount"]),
                    currency=row["currency"],
                )
                ref = row["reference"].strip()
                if len(ref) > 80 or ref in seen or None in row:
                    raise ValueError("Duplicate reference, extra column or reference too long")
                seen.add(ref)
                parsed.append((ref, data.reference, int(data.amount * 100), data.currency))
            except (ValueError, InvalidOperation, TypeError):
                errors.append(
                    {"row": number, "message": "Invalid reference, amount, currency or duplicate row."}
                )
        if not parsed and not errors:
            raise HTTPException(422, "The CSV contains no payments.")
        if errors:
            return JSONResponse(
                {"detail": "Nothing imported. Correct these rows and try again.", "errors": errors},
                status_code=422,
            )
    except UnicodeDecodeError:
        raise HTTPException(422, "Upload a UTF-8 CSV file.")
    counts = {"imported": 0, "duplicates": 0, "matched": 0, "mismatch": 0, "unmatched": 0}
    with engine.begin() as conn:
        for ref, order_ref, amount, currency in parsed:
            order_id, status = classify(conn, user["org_id"], order_ref, amount, currency)
            # A savepoint handles a duplicate from a concurrent import.
            try:
                with conn.begin_nested():
                    conn.execute(
                        payments.insert().values(
                            id=uid(),
                            org_id=user["org_id"],
                            reference=ref,
                            order_reference=order_ref,
                            order_id=order_id,
                            amount_cents=amount,
                            currency=currency,
                            status=status,
                            note="",
                            created_at=time.time(),
                        )
                    )
                counts["imported"] += 1
                counts[status] += 1
            except IntegrityError:
                old = (
                    conn.execute(
                        select(payments).where(
                            payments.c.org_id == user["org_id"],
                            payments.c.reference == ref,
                        )
                    )
                    .mappings()
                    .one()
                )
                if (old["order_reference"], old["amount_cents"], old["currency"]) != (
                    order_ref,
                    amount,
                    currency,
                ):
                    raise HTTPException(
                        409, "A payment reference already exists with different data. Nothing imported."
                    )
                counts["duplicates"] += 1
        record_audit(
            conn,
            user["org_id"],
            user["email"],
            "payments.imported",
            f"{counts['imported']} imported; {counts['duplicates']} duplicates skipped",
        )
    return counts


@app.post("/api/payments/{payment_id}/match")
def match_payment(payment_id: str, data: MatchInput, user=Depends(writer)):
    with engine.begin() as conn:
        payment = (
            conn.execute(
                select(payments).where(payments.c.id == payment_id, payments.c.org_id == user["org_id"])
            )
            .mappings()
            .first()
        )
        if not payment:
            raise HTTPException(404, "Payment not found.")
        order_id, status = classify(
            conn, user["org_id"], data.order_reference, payment["amount_cents"], payment["currency"]
        )
        if status != "matched":
            raise HTTPException(422, "Choose an order with the same amount and currency.")
        conn.execute(
            update(payments)
            .where(payments.c.id == payment_id)
            .values(
                order_id=order_id,
                order_reference=data.order_reference,
                status="matched",
                note="Matched by " + user["email"],
            )
        )
        record_audit(conn, user["org_id"], user["email"], "payment.matched", payment["reference"])
    return {"ok": True}


@app.get("/api/audit")
def audit_log(page: int = Query(1, ge=1), user=Depends(current_user)):
    with engine.connect() as conn:
        where = audit.c.org_id == user["org_id"]
        total = conn.execute(select(func.count()).select_from(audit).where(where)).scalar_one()
        rows = (
            conn.execute(
                select(audit)
                .where(where)
                .order_by(audit.c.created_at.desc())
                .offset((page - 1) * 30)
                .limit(30)
            )
            .mappings()
            .all()
        )
    return {"items": [dict(r) for r in rows], "total": total, "page": page, "page_size": 30}


@app.get("/api/keys")
def keys(user=Depends(admin)):
    with engine.connect() as conn:
        rows = (
            conn.execute(
                select(api_keys.c.id, api_keys.c.name, api_keys.c.created_at, api_keys.c.revoked).where(
                    api_keys.c.org_id == user["org_id"]
                )
            )
            .mappings()
            .all()
        )
    return [dict(r) for r in rows]


@app.post("/api/keys", status_code=201)
def create_key(data: KeyInput, user=Depends(admin)):
    token, key_id = "bs_" + secrets.token_urlsafe(32), uid()
    with engine.begin() as conn:
        conn.execute(
            api_keys.insert().values(
                id=key_id,
                org_id=user["org_id"],
                name=data.name,
                token_hash=digest(token),
                revoked=False,
                created_at=time.time(),
            )
        )
        record_audit(conn, user["org_id"], user["email"], "key.created", data.name)
    return {"id": key_id, "token": token}


@app.delete("/api/keys/{key_id}")
def revoke_key(key_id: str, user=Depends(admin)):
    with engine.begin() as conn:
        result = conn.execute(
            update(api_keys)
            .where(api_keys.c.id == key_id, api_keys.c.org_id == user["org_id"])
            .values(revoked=True)
        )
        if result.rowcount != 1:
            raise HTTPException(404, "Key not found.")
        record_audit(conn, user["org_id"], user["email"], "key.revoked", key_id)
    return {"ok": True}


@app.get("/api/members")
def members(user=Depends(admin)):
    with engine.connect() as conn:
        rows = (
            conn.execute(
                select(users.c.id, users.c.name, users.c.email, users.c.role, users.c.active).where(
                    users.c.org_id == user["org_id"]
                )
            )
            .mappings()
            .all()
        )
    return [dict(r) for r in rows]


@app.post("/api/members", status_code=201)
def create_member(data: MemberInput, user=Depends(admin)):
    try:
        with engine.begin() as conn:
            conn.execute(
                users.insert().values(
                    id=uid(),
                    org_id=user["org_id"],
                    name=data.name.strip(),
                    email=data.email.strip().lower(),
                    password_hash=hash_password(data.password),
                    role=data.role,
                    active=True,
                )
            )
            record_audit(conn, user["org_id"], user["email"], "member.created", data.email)
    except IntegrityError:
        raise HTTPException(409, "That email is already registered.")
    return {"ok": True}


@app.delete("/api/members/{member_id}")
def disable_member(member_id: str, user=Depends(admin)):
    if member_id == user["id"]:
        raise HTTPException(422, "You cannot disable your own account.")
    with engine.begin() as conn:
        result = conn.execute(
            update(users)
            .where(users.c.id == member_id, users.c.org_id == user["org_id"])
            .values(active=False)
        )
        if result.rowcount != 1:
            raise HTTPException(404, "Member not found.")
        conn.execute(delete(sessions).where(sessions.c.user_id == member_id))
        record_audit(conn, user["org_id"], user["email"], "member.disabled", member_id)
    return {"ok": True}


frontend = Path(__file__).resolve().parents[1] / "static"
if frontend.exists():
    app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
