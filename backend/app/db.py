"""Portable schema. Integer cents avoid floating point money errors."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    event,
)
from .config import settings

metadata = MetaData()
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False, "timeout": 30}
    if settings.database_url.startswith("sqlite")
    else {},
)
if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def sqlite_setup(connection, _):
        # Disable the driver's legacy transaction mode so savepoints remain
        # inside the outer transaction (including atomic CSV imports).
        connection.isolation_level = None
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")

    @event.listens_for(engine, "begin")
    def sqlite_begin(connection):
        connection.exec_driver_sql("BEGIN")


organisations = Table(
    "organisations",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("name", String(120), nullable=False),
)
users = Table(
    "users",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("org_id", ForeignKey("organisations.id"), nullable=False),
    Column("name", String(120), nullable=False),
    Column("email", String(254), nullable=False, unique=True),
    Column("password_hash", Text, nullable=False),
    Column("role", String(20), nullable=False),
    Column("active", Boolean, nullable=False, default=True),
)
sessions = Table(
    "sessions",
    metadata,
    Column("token_hash", String(64), primary_key=True),
    Column("user_id", ForeignKey("users.id"), nullable=False),
    Column("expires_at", Float, nullable=False),
)
login_attempts = Table(
    "login_attempts",
    metadata,
    Column("key", String(64), primary_key=True),
    Column("count", Integer, nullable=False),
    Column("window_start", Float, nullable=False),
)
api_keys = Table(
    "api_keys",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("org_id", ForeignKey("organisations.id"), nullable=False),
    Column("name", String(80), nullable=False),
    Column("token_hash", String(64), nullable=False, unique=True),
    Column("created_at", Float, nullable=False),
    Column("revoked", Boolean, nullable=False, default=False),
)
connectors = Table(
    "connectors",
    metadata,
    Column("org_id", ForeignKey("organisations.id"), primary_key=True),
    Column("mode", String(20), nullable=False, default="available"),
)
orders = Table(
    "orders",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("org_id", ForeignKey("organisations.id"), nullable=False),
    Column("event_id", String(120), nullable=False),
    Column("reference", String(80), nullable=False),
    Column("customer", String(120), nullable=False),
    Column("amount_cents", BigInteger, nullable=False),
    Column("currency", String(3), nullable=False),
    Column("payload_hash", String(64), nullable=False),
    Column("created_at", Float, nullable=False),
    UniqueConstraint("org_id", "event_id"),
    UniqueConstraint("org_id", "reference"),
)
jobs = Table(
    "jobs",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("org_id", ForeignKey("organisations.id"), nullable=False),
    Column("order_id", ForeignKey("orders.id"), nullable=False, unique=True),
    Column("status", String(20), nullable=False, default="pending"),
    Column("attempts", Integer, nullable=False, default=0),
    Column("max_attempts", Integer, nullable=False, default=3),
    Column("next_attempt_at", Float, nullable=False),
    Column("lease_until", Float, nullable=True),
    Column("lease_token", String(36), nullable=True),
    Column("last_error", String(240), nullable=True),
    Column("updated_at", Float, nullable=False),
)
Index("ix_jobs_due", jobs.c.status, jobs.c.next_attempt_at)
Index("ix_orders_org_created", orders.c.org_id, orders.c.created_at)
attempts = Table(
    "attempts",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("job_id", ForeignKey("jobs.id"), nullable=False),
    Column("org_id", ForeignKey("organisations.id"), nullable=False),
    Column("number", Integer, nullable=False),
    Column("outcome", String(20), nullable=False),
    Column("detail", String(240), nullable=False),
    Column("duration_ms", Integer, nullable=False),
    Column("created_at", Float, nullable=False),
)
payments = Table(
    "payments",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("org_id", ForeignKey("organisations.id"), nullable=False),
    Column("reference", String(80), nullable=False),
    Column("order_reference", String(80), nullable=False),
    Column("order_id", ForeignKey("orders.id"), nullable=True),
    Column("amount_cents", BigInteger, nullable=False),
    Column("currency", String(3), nullable=False),
    Column("status", String(20), nullable=False),
    Column("note", String(240), nullable=False, default=""),
    Column("created_at", Float, nullable=False),
    UniqueConstraint("org_id", "reference"),
)
audit = Table(
    "audit",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("org_id", ForeignKey("organisations.id"), nullable=False),
    Column("actor", String(120), nullable=False),
    Column("action", String(80), nullable=False),
    Column("detail", String(240), nullable=False),
    Column("created_at", Float, nullable=False),
)
