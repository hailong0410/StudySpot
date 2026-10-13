"""ICA10: deterministic EP/BVA and real route/database integration checks."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3

import pytest
import app as studyspot
from test_app import token

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('seconds,expected_age,stale', [
    (-60, 'Just now', False),
    (0, 'Just now', False),
    (59, 'Just now', False),
    (60, '1 min ago', False),
    (59 * 60, '59 min ago', False),
    (60 * 60 - 1, '59 min ago', False),
    (60 * 60, '1 hours ago', True),
    (61 * 60, '1 hours ago', True),
    (1439 * 60, '23 hours ago', True),
    (1440 * 60, '1 days ago', True),
    (1441 * 60, '1 days ago', True),
])
def test_report_age_boundaries(client, app, monkeypatch, seconds, expected_age, stale):
    # Stub only the clock; run the real route, database query and template.
    now = datetime(2026, 10, 13, 17, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(studyspot, 'utc_now', lambda: now)
    posted = now - timedelta(seconds=seconds)
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute(
            'INSERT INTO status_reports(space_id,crowd,noise,created_at) VALUES (1,?,?,?)',
            ('low', 'quiet', posted.isoformat()),
        )
    response = client.get('/spaces/1')
    assert response.status_code == 200
    latest = response.data.split(b'id="latest"')[1].split(b'class="history"')[0]
    assert expected_age.encode() in latest
    assert (b'class="stale"' in latest) is stale
    assert (b'class="fresh"' in latest) is (not stale)


@pytest.mark.parametrize('count', [4, 5, 6])
def test_report_history_five_item_boundary(client, app, count):
    now = datetime(2026, 10, 13, 17, 0, tzinfo=timezone.utc)
    with sqlite3.connect(app.config['DATABASE']) as db:
        for i in range(count):
            db.execute(
                'INSERT INTO status_reports(space_id,crowd,noise,created_at) VALUES (1,?,?,?)',
                ('low', 'quiet', (now - timedelta(minutes=i)).isoformat()),
            )
    response = client.get('/spaces/1')
    assert response.status_code == 200
    assert response.data.count(b'class="history-row"') == min(count, 5)
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM status_reports').fetchone()[0] == count


@pytest.mark.parametrize('crowd,noise', [('low', 'invalid'), ('', 'quiet'), ('low', '')])
def test_invalid_report_fields_never_write(client, app, crowd, noise):
    csrf = token(client)
    response = client.post('/spaces/1/reports', data={
        'csrf_token': csrf, 'crowd': crowd, 'noise': noise,
    })
    assert response.status_code == 400
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM status_reports').fetchone()[0] == 0


def test_report_for_missing_space_returns_404_without_writing(client, app):
    csrf = token(client)
    response = client.post('/spaces/99999/reports', data={
        'csrf_token': csrf, 'crowd': 'low', 'noise': 'quiet',
    })
    assert response.status_code == 404
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM status_reports').fetchone()[0] == 0


def test_wrong_csrf_token_never_writes(client, app):
    token(client)
    response = client.post('/spaces/1/reports', data={
        'csrf_token': 'wrong-token', 'crowd': 'low', 'noise': 'quiet',
    })
    assert response.status_code == 400
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM status_reports').fetchone()[0] == 0


@pytest.mark.parametrize('field,value', [('outlets', 'no'), ('atmosphere', 'loud')])
def test_invalid_filters_return_400(client, field, value):
    assert client.get('/', query_string={field: value}).status_code == 400


def test_health_returns_status_with_real_database(client, app):
    # Public requests in one context exercise reuse of the SQLite connection.
    with app.app_context():
        assert client.get('/').status_code == 200
        response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json() == {'status': 'ok', 'dataset': 'sample'}


def test_default_startup_keeps_session_key_and_sample_data(tmp_path, monkeypatch):
    # Place all startup files in a temporary directory, never the demo instance.
    schema = Path(studyspot.__file__).with_name('schema.sql').read_text()
    (tmp_path / 'schema.sql').write_text(schema)
    monkeypatch.setattr(studyspot, 'BASE', tmp_path)
    monkeypatch.delenv('STUDYSPOT_SECRET', raising=False)
    first = studyspot.create_app()
    assert first.test_client().get('/health').status_code == 200
    first_key = first.config['SECRET_KEY']
    assert first_key
    assert (tmp_path / 'instance' / 'session.key').read_text().strip() == first_key
    second = studyspot.create_app()
    assert second.config['SECRET_KEY'] == first_key
    with sqlite3.connect(second.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM study_spaces').fetchone()[0] == 8


def test_oversized_report_returns_413_without_writing(client, app):
    csrf = token(client)
    response = client.post('/spaces/1/reports', data={
        'csrf_token': csrf, 'crowd': 'low', 'noise': 'quiet',
        'extra': 'x' * (16 * 1024 + 1),
    })
    assert response.status_code == 413
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM status_reports').fetchone()[0] == 0


@pytest.mark.parametrize('query,expected_count', [
    ({'study': 'individual'}, 5),
    ({'study': 'group'}, 5),
    ({'outlets': 'yes'}, 6),
])
def test_each_study_and_outlet_filter_crosses_real_database(client, query, expected_count):
    response = client.get('/', query_string=query)
    assert response.status_code == 200
    assert response.data.count(b'class="space"') == expected_count


def test_valid_report_route_writes_exact_database_row(client, app, monkeypatch):
    now = datetime(2026, 10, 13, 18, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(studyspot, 'utc_now', lambda: now)
    csrf = token(client)
    response = client.post('/spaces/1/reports', data={
        'csrf_token': csrf, 'crowd': 'low', 'noise': 'quiet',
    })
    assert response.status_code == 303
    with sqlite3.connect(app.config['DATABASE']) as db:
        rows = db.execute('SELECT space_id,crowd,noise,created_at FROM status_reports').fetchall()
    assert rows == [(1, 'low', 'quiet', '2026-10-13T18:00:00+00:00')]
