"""Regression checks for the Sprint 4 audit."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import re
import sqlite3
from threading import Barrier

from flask import session
import pytest

import app as studyspot
from test_app import token

pytestmark = pytest.mark.integration


def submit(client, space=1, address="127.0.0.1"):
    return client.post(
        f"/spaces/{space}/reports",
        data={"csrf_token": token(client), "crowd": "low", "noise": "quiet"},
        environ_overrides={"REMOTE_ADDR": address},
        headers={"X-Forwarded-For": "192.0.2.5"},
    )


def test_cooldown_boundary_and_scope(client, app, monkeypatch):
    now = datetime(2026, 11, 11, 18, tzinfo=timezone.utc)
    monkeypatch.setattr(studyspot, "utc_now", lambda: now)
    assert submit(client).status_code == 303
    now += timedelta(seconds=59)
    blocked = submit(app.test_client())
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "1"
    assert submit(client, space=2).status_code == 303
    assert submit(client, address="127.0.0.2").status_code == 303
    now += timedelta(seconds=1)
    assert submit(client).status_code == 303
    with sqlite3.connect(app.config["DATABASE"]) as db:
        assert db.execute("SELECT COUNT(*) FROM status_reports").fetchone()[0] == 4
        assert db.execute("SELECT COUNT(*) FROM report_cooldowns").fetchone()[0] == 3


def test_concurrent_report_writes_cannot_bypass_cooldown(app):
    ready = Barrier(2, timeout=5)

    def attempt():
        client = app.test_client()
        csrf = token(client)
        ready.wait()
        return client.post("/spaces/1/reports", data={
            "csrf_token": csrf, "crowd": "low", "noise": "quiet",
        }).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = sorted(pool.map(lambda _: attempt(), range(2)))
    assert codes == [303, 429]
    with sqlite3.connect(app.config["DATABASE"]) as db:
        assert db.execute("SELECT COUNT(*) FROM status_reports").fetchone()[0] == 1


def test_non_ascii_csrf_token_returns_400(client, app):
    token(client)
    response = client.post("/spaces/1/reports", data={
        "csrf_token": "ấ", "crowd": "low", "noise": "quiet",
    })
    assert response.status_code == 400
    with sqlite3.connect(app.config["DATABASE"]) as db:
        assert db.execute("SELECT COUNT(*) FROM status_reports").fetchone()[0] == 0


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode bits do not describe Windows ACLs")
def test_existing_instance_storage_is_private(tmp_path, monkeypatch):
    schema = Path(studyspot.__file__).with_name("schema.sql").read_text()
    (tmp_path / "schema.sql").write_text(schema)
    monkeypatch.setattr(studyspot, "BASE", tmp_path)
    monkeypatch.setenv("STUDYSPOT_DATASET", "sample")
    monkeypatch.delenv("STUDYSPOT_SECRET", raising=False)
    instance = tmp_path / "instance"
    instance.mkdir(mode=0o755)
    key = instance / "session.key"
    key.write_text("existing-test-key")
    key.chmod(0o644)

    assert studyspot.create_app().config["SECRET_KEY"] == "existing-test-key"
    assert instance.stat().st_mode & 0o077 == 0
    assert key.stat().st_mode & 0o077 == 0


def test_environment_key_skips_local_key_creation(tmp_path, monkeypatch):
    schema = Path(studyspot.__file__).with_name("schema.sql").read_text()
    (tmp_path / "schema.sql").write_text(schema)
    monkeypatch.setattr(studyspot, "BASE", tmp_path)
    monkeypatch.setenv("STUDYSPOT_DATASET", "sample")
    monkeypatch.setenv("STUDYSPOT_SECRET", "injected-test-key")
    assert studyspot.create_app().config["SECRET_KEY"] == "injected-test-key"
    assert not (tmp_path / "instance" / "session.key").exists()


def test_workflow_action_references_are_immutable():
    workflow = Path(studyspot.__file__).parent / ".github" / "workflows" / "ci.yml"
    uses = re.findall(r"^\s*-\s+uses:\s+(\S+)", workflow.read_text(), re.MULTILINE)
    assert uses and all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", action) for action in uses)


def test_flask_session_membership_response_varies_on_cookie(app):
    # Exercise the Flask session-access pattern underlying CVE-2026-27205.
    @app.get("/_test_session_membership")
    def session_membership():
        return str("marker" in session)

    with app.test_client() as client:
        with client.session_transaction() as state:
            state["marker"] = "value"
        response = client.get("/_test_session_membership")
        assert response.data == b"True"
        assert "Cookie" in response.vary


def test_app_and_live_feed_send_browser_security_headers(client):
    for route in ("/spaces/1", "/spaces/1/live"):
        response = client.get(route)
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
