"""Two-client integration checks for the StudySpot observation feed."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

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


def test_home_statuses_after_simultaneous_reports_and_at_staleness_boundary(app, monkeypatch):
    now = datetime(2026, 11, 11, 18, tzinfo=timezone.utc)
    monkeypatch.setattr(studyspot, "utc_now", lambda: now)
    viewer = app.test_client()
    assert b'data-space-statuses="/spaces/statuses"' in viewer.get("/").data
    initial = app.test_client().get("/spaces/statuses")
    assert initial.json == {}
    assert initial.headers["Cache-Control"] == "no-store"
    assert "Set-Cookie" not in initial.headers

    ready = Barrier(2, timeout=5)

    def publish(crowd, address):
        client = app.test_client()
        fields = {"csrf_token": token(client), "crowd": crowd, "noise": "quiet"}
        ready.wait()
        return client.post("/spaces/1/reports", data=fields, environ_overrides={"REMOTE_ADDR": address}).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        writes = [pool.submit(publish, "low", "192.0.2.1"), pool.submit(publish, "high", "192.0.2.2")]
        assert [result.result() for result in writes] == [303, 303]

    statuses = viewer.get("/spaces/statuses").json
    assert list(statuses) == ["1"]
    latest = statuses["1"]
    assert latest["crowd"] in ("Not busy", "Very busy")
    assert latest["crowd"].encode() in viewer.get("/spaces/1/live").data.split(b"Recent observations", 1)[0]
    assert (latest["noise"], latest["age"], latest["stale"]) == ("Quiet", "Just now", False)
    now += timedelta(minutes=60)
    assert viewer.get("/spaces/statuses").json["1"]["stale"] is True
