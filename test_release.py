"""Regression coverage for health and staging-only release fixtures."""
from pathlib import Path

import pytest

from app import create_app

pytestmark = pytest.mark.integration


def test_release_health_identity_and_safe_logs(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("STUDYSPOT_INSTANCE", str(tmp_path / "data"))
    monkeypatch.setenv("STUDYSPOT_COMMIT", "test-commit")
    monkeypatch.setenv("STUDYSPOT_JSON_LOGS", "1")
    app = create_app({"TESTING": True})
    client = app.test_client()
    response = client.get("/health")
    assert response.json["database"] == "reachable"
    assert response.json["commit"] == "test-commit"
    assert response.json["version"] == Path("VERSION").read_text().strip()
    missing = client.get("/does-not-exist?credential=redacted-example")
    logs = capsys.readouterr().out
    assert missing.headers["X-Request-ID"] in logs and '"level": "INFO"' in logs
    assert "redacted-example" not in logs
    Path(app.config["DATABASE"]).unlink()
    response = client.get("/health")
    assert response.status_code == 503 and response.json["database"] == "unavailable"


def test_staging_fixture_is_absent_from_production(monkeypatch, tmp_path):
    monkeypatch.setenv("STUDYSPOT_ENV", "staging")
    monkeypatch.setenv("STUDYSPOT_SECURE_COOKIE", "1")
    monkeypatch.setenv("STUDYSPOT_INSTANCE", str(tmp_path / "stage"))
    monkeypatch.delenv("STUDYSPOT_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="strong signing key"):
        create_app()
    monkeypatch.setenv("STUDYSPOT_SECRET", "x" * 32)
    assert create_app().test_client().get("/spaces/999").status_code == 200
    monkeypatch.setenv("STUDYSPOT_ENV", "production")
    monkeypatch.setenv("STUDYSPOT_INSTANCE", str(tmp_path / "production"))
    assert create_app().test_client().get("/spaces/999").status_code == 404


def test_proxy_mode_keeps_shared_gateway_users_separate(monkeypatch, tmp_path):
    from test_security import submit

    monkeypatch.setenv("STUDYSPOT_TRUST_PROXY", "1")
    monkeypatch.setenv("STUDYSPOT_INSTANCE", str(tmp_path / "data"))
    app = create_app({"TESTING": True})
    assert submit(app.test_client(), address="192.0.2.1").status_code == 303
    client = app.test_client()
    with client.session_transaction() as session:
        session["csrf_token"] = "test-csrf"
    response = client.post(
        "/spaces/1/reports",
        headers={"X-Forwarded-For": "192.0.2.6", "X-Forwarded-Proto": "https"},
        data={"csrf_token": "test-csrf", "crowd": "low", "noise": "quiet"},
    )
    assert response.status_code == 303


def test_json_error_log_uses_route_template(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("STUDYSPOT_JSON_LOGS", "1")
    monkeypatch.setenv("STUDYSPOT_INSTANCE", str(tmp_path / "data"))
    app = create_app({"TESTING": False})

    @app.get("/_test_error/<value>")
    def internal_error(value):
        raise RuntimeError(value)

    response = app.test_client().get("/_test_error/credential-example")
    assert response.status_code == 500
    logs = capsys.readouterr().out
    assert '"level": "ERROR"' in logs and '"route": "/_test_error/<value>"' in logs
    assert response.headers["X-Request-ID"] in logs
    assert "credential-example" not in logs
