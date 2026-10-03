"""Hosted startup preserves process lifecycle and hosted database compatibility."""

import os
import subprocess
import sys
import time

import pytest

from app import config
from app.hosted import api_command


@pytest.mark.parametrize("prefix", ["postgres://", "postgresql://"])
def test_hosted_postgres_url_uses_installed_driver(prefix):
    assert config.database_url(prefix + "user:password@db/app") == (
        "postgresql+psycopg://user:password@db/app"
    )
    assert config.database_url("sqlite:///demo.db") == "sqlite:///demo.db"


def test_api_binds_provider_port(monkeypatch):
    monkeypatch.setenv("PORT", "10987")
    assert api_command()[-3:] == ["0.0.0.0", "--port", "10987"]
    monkeypatch.setenv("PORT", "0")
    with pytest.raises(ValueError):
        api_command()


def assert_stopped(pid):
    for _ in range(50):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.02)
    pytest.fail("Supervisor left a child process running")


def test_component_failure_stops_other_component():
    child = "import os,time; print(os.getpid(),flush=True); time.sleep(120)"
    failing = "import time; time.sleep(.2); raise SystemExit(7)"
    script = (
        "import sys; from app.hosted import supervise; "
        f"raise SystemExit(supervise([[sys.executable,'-c',{child!r}],"
        f"[sys.executable,'-c',{failing!r}]]))"
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=12)
    assert result.returncode == 7
    assert_stopped(int(result.stdout.splitlines()[0]))


def test_platform_shutdown_stops_child():
    child = "import os,time; print(os.getpid(),flush=True); time.sleep(120)"
    script = (
        "import sys; from app.hosted import supervise; "
        f"raise SystemExit(supervise([[sys.executable,'-c',{child!r}]]))"
    )
    parent = subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.PIPE, text=True)
    try:
        pid = int(parent.stdout.readline())
        parent.terminate()
        assert parent.wait(timeout=12) == 0
        assert_stopped(pid)
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait()
