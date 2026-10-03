"""Environment configuration shared by the API, worker and migrations."""

import os
from dataclasses import dataclass


def database_url(value):
    """Accept hosted PostgreSQL URLs with the installed psycopg driver."""
    for prefix in ("postgres://", "postgresql://"):
        if value.startswith(prefix):
            return "postgresql+psycopg://" + value[len(prefix):]
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str = database_url(os.getenv("DATABASE_URL", "sqlite:///./bridgesync.db"))
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    connector_url: str = os.getenv("CONNECTOR_URL", "http://localhost:8001/orders")
    connector_token: str = os.getenv("CONNECTOR_TOKEN", "")
    secure_cookie: bool = os.getenv("SECURE_COOKIE", "false").lower() == "true"
    session_hours: int = 12


settings = Settings()
