import os
import tempfile
from pathlib import Path

os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "sqlite:///" + str(Path(tempfile.mkdtemp()) / "tests.db")
)
os.environ["CONNECTOR_TOKEN"] = "test-only-connector-token"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.db import engine, metadata, users
from app.main import app
from app.seed import seed

HEADER = {"X-BridgeSync-Request": "browser"}
PASSWORD = "A-test-password-123"


@pytest.fixture(autouse=True)
def database():
    metadata.drop_all(engine)
    metadata.create_all(engine)
    seed("admin@example.com", PASSWORD)
    seed("other@example.com", PASSWORD, name="Other organisation")
    yield


@pytest.fixture
def client():
    with TestClient(app, headers=HEADER) as client:
        response = client.post("/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
        assert response.status_code == 200
        yield client


@pytest.fixture
def org():
    with engine.connect() as conn:
        return conn.execute(select(users.c.org_id).where(users.c.email == "admin@example.com")).scalar_one()
