"""Two-client integration checks for the StudySpot observation feed."""
from datetime import datetime, timedelta, timezone

import pytest

import app as studyspot
from test_app import token

pytestmark = pytest.mark.integration


def test_live_feed_updates_after_another_client_posts(client, app):
    viewer = app.test_client()
    page = viewer.get("/spaces/1")
    assert b'data-live-observations="/spaces/1/live"' in page.data
    assert b"live-observations.js" in page.data

    initial = app.test_client().get("/spaces/1/live")
    assert b"No updates yet" in initial.data
    assert initial.headers["Cache-Control"] == "no-store"
    assert "Set-Cookie" not in initial.headers

    response = client.post("/spaces/1/reports", data={
        "csrf_token": token(client), "crowd": "high", "noise": "loud",
    })
    assert response.status_code == 303
    updated = viewer.get("/spaces/1/live")
    assert b"Very busy" in updated.data and b"Loud" in updated.data
    assert b"Recent observation" in updated.data
    assert b"No updates yet" in viewer.get("/spaces/2/live").data
    assert viewer.get("/spaces/99999/live").status_code == 404


def test_live_feed_becomes_stale_without_another_report(client, monkeypatch):
    now = datetime(2026, 11, 11, 18, tzinfo=timezone.utc)
    monkeypatch.setattr(studyspot, "utc_now", lambda: now)
    client.post("/spaces/1/reports", data={
        "csrf_token": token(client), "crowd": "low", "noise": "quiet",
    })
    now += timedelta(minutes=59, seconds=59)
    assert b'class="fresh"' in client.get("/spaces/1/live").data
    now += timedelta(seconds=1)
    feed = client.get("/spaces/1/live")
    assert b'class="stale"' in feed.data
    assert b"at least 60 minutes old" in feed.data
