"""Verify campus links, honest initial state and separation from sample observations."""
from pathlib import Path

import pytest

import app as studyspot
from test_app import token

pytestmark = pytest.mark.integration


def test_campus_app_starts_with_verified_spaces_and_no_sample_observations(tmp_path, monkeypatch):
    for name in ("schema.sql", "campus-spaces.json"):
        (tmp_path / name).write_bytes((Path(studyspot.__file__).parent / name).read_bytes())
    monkeypatch.setattr(studyspot, "BASE", tmp_path)
    monkeypatch.delenv("STUDYSPOT_DATABASE", raising=False)
    sample = studyspot.create_app({"DATASET": "sample", "SECRET_KEY": "fixture-key"}).test_client()
    assert sample.post("/spaces/1/reports", data={
        "csrf_token": token(sample), "crowd": "high", "noise": "loud",
    }).status_code == 303

    campus_app = studyspot.create_app({"DATASET": "campus", "SECRET_KEY": "fixture-key"})
    campus = campus_app.test_client()
    explore = campus.get("/")
    assert explore.data.count(b'class="space"') == 6
    assert b"Vanderbilt study space" in explore.data
    assert b"Library Quiet Zone" not in explore.data
    assert b"Sample campus dataset" not in explore.data
    room = campus.get("/spaces/1")
    assert b"https://www.library.vanderbilt.edu/central/hours/" in room.data
    assert b"https://www.google.com/maps/search/" in room.data
    assert b"No updates yet" in campus.get("/spaces/1/live").data
    assert campus.post("/spaces/1/reports", data={
        "csrf_token": token(campus), "crowd": "low", "noise": "quiet",
    }).status_code == 303
    assert b"Not busy" in campus_app.test_client().get("/spaces/1/live").data
    assert b"Very busy" in sample.get("/spaces/1/live").data

    with pytest.raises(ValueError, match="different StudySpot catalog"):
        studyspot.create_app({
            "DATASET": "campus",
            "DATABASE": str(tmp_path / "instance" / "studyspot.sqlite3"),
            "SECRET_KEY": "fixture-key",
        })
