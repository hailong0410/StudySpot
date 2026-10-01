"""Acceptance checks use a temporary database, never the demo database."""
from datetime import timedelta
import sqlite3
import pytest
from app import create_app, utc_now


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "SECRET_KEY": "testing-only-key", "DATABASE": str(tmp_path / "test.sqlite3")})


@pytest.fixture
def client(app):
    return app.test_client()


def token(client):
    client.get("/spaces/1")
    with client.session_transaction() as s:
        return s["csrf_token"]


def test_browse_eight_sample_spaces(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.data.count(b'class="space"') == 8
    assert b"fictional examples" in r.data


def test_search_case_insensitive(client):
    r = client.get("/?q=LIBRARY")
    assert r.data.count(b'class="space"') == 1
    assert b"Library Quiet Zone" in r.data


def test_empty_result(client):
    r = client.get("/?q=not-a-real-place")
    assert b"No matching spaces" in r.data
    assert b"Show all spaces" in r.data


def test_combined_group_outlets_filters(client):
    r = client.get("/?study=group&outlets=yes")
    assert r.data.count(b'class="space"') == 3
    assert b"Engineering Study Lounge" in r.data
    assert b"Collaboration Room" in r.data
    assert b"Campus Cafe Tables" in r.data
    assert b"Student Center Commons" not in r.data


def test_quiet_filter(client):
    r = client.get("/?atmosphere=quiet")
    assert r.data.count(b'class="space"') == 3


def test_unknown_and_invalid_parameters(client):
    assert client.get("/spaces/99999").status_code == 404
    assert client.get("/?study=invalid").status_code == 400
    assert client.get("/spaces/99999/reports").status_code == 405


def test_report_saved_and_survives_new_app(client, app):
    csrf = token(client)
    r = client.post("/spaces/1/reports", data={"csrf_token": csrf, "crowd": "medium", "noise": "quiet"})
    assert r.status_code == 303
    reopened = create_app({"TESTING": True, "SECRET_KEY": "other-key", "DATABASE": app.config["DATABASE"]}).test_client()
    page = reopened.get("/spaces/1")
    assert b"Somewhat busy" in page.data
    assert b"Recent observation" in page.data


def test_invalid_report_does_not_write(client, app):
    csrf = token(client)
    assert client.post("/spaces/1/reports", data={"csrf_token": csrf, "crowd": "invalid", "noise": "quiet"}).status_code == 400
    with sqlite3.connect(app.config["DATABASE"]) as db:
        assert db.execute("SELECT count(*) FROM status_reports").fetchone()[0] == 0


def test_missing_csrf_does_not_write(client, app):
    assert client.post("/spaces/1/reports", data={"crowd": "low", "noise": "quiet"}).status_code == 400
    with sqlite3.connect(app.config["DATABASE"]) as db:
        assert db.execute("SELECT count(*) FROM status_reports").fetchone()[0] == 0


def test_stale_report_warning(client, app):
    with sqlite3.connect(app.config["DATABASE"]) as db:
        db.execute("INSERT INTO status_reports(space_id,crowd,noise,created_at) VALUES (1,'high','loud',?)", ((utc_now() - timedelta(minutes=61)).isoformat(),))
    assert b"over 60 minutes old" in client.get("/spaces/1").data


def test_latest_report_and_space_isolation(client, app):
    now = utc_now()
    with sqlite3.connect(app.config["DATABASE"]) as db:
        db.execute("INSERT INTO status_reports(space_id,crowd,noise,created_at) VALUES (1,'high','loud',?)", ((now - timedelta(minutes=90)).isoformat(),))
        db.execute("INSERT INTO status_reports(space_id,crowd,noise,created_at) VALUES (1,'low','quiet',?)", (now.isoformat(),))
    page = client.get("/spaces/1").data
    latest_section = page.split(b'id="latest"')[1].split(b'class="history"')[0]
    assert b"Not busy" in latest_section and b"Recent observation" in latest_section
    assert b"No updates yet" in client.get("/spaces/2").data


def test_literal_search_and_escaped_output(client):
    assert client.get("/?q=%25").data.count(b'class="space"') == 0
    r = client.get("/?q=%3Cscript%3Ealert(1)%3C/script%3E")
    assert b"<script>alert(1)</script>" not in r.data
    assert b"&lt;script&gt;" in r.data
