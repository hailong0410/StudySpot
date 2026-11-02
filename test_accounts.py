"""Real Flask/session/SQLite checks for account success and failure paths."""
from datetime import datetime, timedelta, timezone
import sqlite3

import pytest
from werkzeug.security import check_password_hash

import app as studyspot
from test_app import token

pytestmark = pytest.mark.integration
PASSWORD = "studyspot-test-password"


def submit(client, route, **fields):
    return client.post(route, data={"csrf_token": token(client), **fields})


def register(client, email="long@example.edu", password=PASSWORD):
    return submit(client, "/register", email=email, password=password)


def login(client, email="long@example.edu", password=PASSWORD):
    return submit(client, "/login", email=email, password=password)


def users(app):
    with sqlite3.connect(app.config["DATABASE"]) as db:
        return db.execute("SELECT email,password_hash FROM users").fetchall()


def test_registration_normalizes_and_hashes(client, app):
    assert register(client, "  LONG@Example.edu ").status_code == 303
    email, stored = users(app)[0]
    assert email == "long@example.edu"
    assert stored != PASSWORD and check_password_hash(stored, PASSWORD)
    with client.session_transaction() as state:
        assert "user_id" not in state


def test_duplicate_has_same_response_and_preserves_password(client, app):
    first = register(client)
    original = users(app)
    duplicate = register(client, "LONG@example.edu", "a-different-password")
    assert (first.status_code, first.location) == (duplicate.status_code, duplicate.location)
    assert users(app) == original


@pytest.mark.parametrize("email,password", [
    ("", PASSWORD), ("no-at-sign", PASSWORD), ("a@b", PASSWORD),
    ("a b@example.edu", PASSWORD), ("a" * 65 + "@example.edu", PASSWORD),
    ("a@" + "b" * 250 + ".edu", PASSWORD),
    ("long@example.edu", ""), ("long@example.edu", "x" * 7),
    ("long@example.edu", "x" * 129),
])
def test_registration_rejects_invalid_input(client, app, email, password):
    assert register(client, email, password).status_code == 400
    assert users(app) == []


@pytest.mark.parametrize("length", [8, 128])
def test_password_inclusive_boundaries(client, length):
    assert register(client, password="x" * length).status_code == 303
    assert login(client, password="x" * length).status_code == 303


@pytest.mark.parametrize("path", ["/register", "/login", "/logout"])
@pytest.mark.parametrize("csrf", ["", "wrong", "\u2603"])
def test_csrf_required_for_every_account_mutation(client, app, path, csrf):
    token(client)
    response = client.post(path, data={"csrf_token": csrf, "email": "a@example.edu", "password": PASSWORD})
    assert response.status_code == 400
    assert users(app) == []


def test_login_rotates_session_and_logout_clears_it(client):
    register(client)
    old_token = token(client)
    with client.session_transaction() as state:
        state["untrusted_old_value"] = "discard"
    assert login(client).location.endswith("/account")
    with client.session_transaction() as state:
        assert state["user_id"] == 1 and state["_permanent"]
        assert state["csrf_token"] != old_token
        assert "untrusted_old_value" not in state
    page = client.get("/account")
    assert page.status_code == 200 and b"long@example.edu" in page.data
    assert client.post("/logout", data={"csrf_token": old_token}).status_code == 400
    assert submit(client, "/logout").status_code == 303
    assert client.get("/account").location.endswith("/login")
    assert client.get("/logout").status_code == 405


@pytest.mark.parametrize("email,password", [
    ("long@example.edu", "wrong-password"), ("missing@example.edu", PASSWORD),
    ("long@example.edu", "short"), ("a" * 255, PASSWORD),
])
def test_invalid_login_is_generic_and_anonymous(client, email, password):
    register(client)
    response = login(client, email, password)
    assert response.status_code == 400 and b"Invalid email or password." in response.data
    assert client.get("/account").location.endswith("/login")


@pytest.mark.parametrize("seconds,allowed", [(1799, True), (1800, False), (1801, False)])
def test_fixed_session_expiry(tmp_path, monkeypatch, seconds, allowed):
    now = datetime(2026, 11, 2, 18, 0, tzinfo=timezone.utc)
    current = [now]
    monkeypatch.setattr(studyspot, "utc_now", lambda: current[0])
    application = studyspot.create_app({"TESTING": True, "SECRET_KEY": "test-key", "DATABASE": str(tmp_path / "expiry.db")})
    browser = application.test_client()
    register(browser)
    login(browser)
    current[0] = now + timedelta(seconds=seconds)
    assert (browser.get("/account").status_code == 200) is allowed
    if not allowed:
        with browser.session_transaction() as state:
            assert "user_id" not in state


def test_deleted_account_loses_access(client, app):
    register(client)
    login(client)
    with sqlite3.connect(app.config["DATABASE"]) as db:
        db.execute("DELETE FROM users")
    assert client.get("/account").location.endswith("/login")


def test_logged_out_cookie_cannot_be_replayed(client, app):
    register(client)
    login(client)
    cookie = client.get_cookie("session").value
    assert submit(client, "/logout").status_code == 303
    replay = app.test_client()
    replay.set_cookie("session", cookie)
    assert replay.get("/account").location.endswith("/login")


def test_session_contains_no_plaintext_password_and_cookie_flags(client):
    register(client)
    response = login(client)
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie
    with client.session_transaction() as state:
        assert "password" not in state and PASSWORD not in str(dict(state))


def test_account_isolation_and_client_user_id_ignored(client, app):
    register(client)
    other = app.test_client()
    register(other, "other@example.edu")
    login(client)
    login(other, "other@example.edu")
    assert b"long@example.edu" in client.get("/account?user_id=2").data
    assert b"other@example.edu" not in client.get("/account?user_id=2").data
    assert b"other@example.edu" in other.get("/account").data
    assert b"long@example.edu" not in other.get("/account").data


def test_existing_reports_survive_schema_initialization(client, app):
    assert submit(client, "/spaces/1/reports", crowd="low", noise="quiet").status_code == 303
    register(client)
    reopened = studyspot.create_app(dict(app.config)).test_client()
    assert b"Not busy" in reopened.get("/spaces/1").data
    assert login(reopened).status_code == 303


def test_forms_never_echo_password_and_access_is_public(client):
    for path in ("/register", "/login", "/", "/spaces/1"):
        assert client.get(path).status_code == 200
    response = register(client, password="secret")
    assert b'value="secret"' not in response.data


def test_untrusted_email_is_escaped(client):
    register(client, "<script>@example.edu")
    login(client, "<script>@example.edu")
    assert b"<script>" not in client.get("/account").data
    assert b"&lt;script&gt;" in client.get("/account").data
