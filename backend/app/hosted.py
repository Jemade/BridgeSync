"""Supervise the API and demo workers as one hosted service."""

import os
import signal
import subprocess
import sys
import threading

from . import config


def supervise(commands):
    """Stop every child on shutdown or when any component exits."""
    stop = threading.Event()
    children = []

    def shutdown(signum, frame):
        stop.set()

    previous = {sig: signal.signal(sig, shutdown) for sig in (signal.SIGTERM, signal.SIGINT)}
    result = 0
    try:
        for command in commands:
            if stop.is_set():
                break
            children.append(subprocess.Popen(command))
        while not stop.wait(0.25):
            for child in children:
                status = child.poll()
                if status is not None:
                    print("Hosted component exited; stopping service.", flush=True)
                    result = status or 1
                    stop.set()
                    break
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    return result


def api_command():
    port = int(os.getenv("PORT", "10000"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535")
    return [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(port)]


def main():
    from sqlalchemy import select
    from .db import engine, users
    from .seed import seed

    if not config.settings.connector_token:
        raise ValueError("CONNECTOR_TOKEN is required for the hosted test connector")
    if config.settings.connector_url != "http://127.0.0.1:8001/orders":
        raise ValueError("Hosted demo requires the loopback test connector URL")
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    if not email:
        raise ValueError("ADMIN_EMAIL is required for initial account setup")
    with engine.connect() as connection:
        exists = connection.execute(select(users.c.id).where(users.c.email == email)).first()
    if not exists:
        seed(email, os.getenv("ADMIN_PASSWORD", ""), demo=True)
    commands = [
        [sys.executable, "-m", "uvicorn", "app.mock_connector:app", "--host", "127.0.0.1", "--port", "8001"],
        [sys.executable, "-m", "app.worker"],
        api_command(),
    ]
    return supervise(commands)


if __name__ == "__main__":
    raise SystemExit(main())

