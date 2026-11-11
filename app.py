"""StudySpot: a local Flask/SQLite prototype with community observations."""
from datetime import datetime, timezone
from math import ceil
from pathlib import Path
import hmac
import json
import os
import secrets
import sqlite3
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode

from flask import Flask, Response, abort, flash, g, redirect, render_template, request, session, url_for

from werkzeug.exceptions import TooManyRequests

from domain import CROWD, NOISE, build_space_query, parse_filters, report_view, validate_report_fields

REPORT_COOLDOWN_SECONDS = 60
BASE = Path(__file__).resolve().parent
SAMPLE_SPACES = [
    ("Library Quiet Zone", "Sample campus library, level 2", "A sample space for focused individual study.", "individual", 1, "quiet"),
    ("Engineering Study Lounge", "Sample engineering building, level 1", "A sample lounge with tables for small groups.", "group", 1, "moderate"),
    ("Graduate Reading Room", "Sample graduate center, level 3", "A sample reading room for individual work.", "individual", 1, "quiet"),
    ("Student Center Commons", "Sample student center, ground floor", "A sample shared area suitable for group discussions.", "group", 0, "lively"),
    ("Courtyard Study Tables", "Sample campus courtyard", "A sample outdoor space for individual or group work.", "both", 0, "moderate"),
    ("Science Reading Corner", "Sample science building, level 2", "A sample quiet corner with power outlets.", "individual", 1, "quiet"),
    ("Collaboration Room", "Sample learning center, level 1", "A sample indoor area for project discussions.", "group", 1, "moderate"),
    ("Campus Cafe Tables", "Sample campus cafe", "A sample informal space that may be noisy.", "both", 1, "lively"),
]


def utc_now():
    return datetime.now(timezone.utc)


def local_session_key(instance):
    key_path = instance / "session.key"
    if not key_path.exists():
        # Publish a complete, privately created key, even if two workers start together.
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=instance, delete=False) as staged:
            staged.write(secrets.token_hex(32))
        try:
            os.link(staged.name, key_path)
        except FileExistsError:
            pass  # Another worker published the key first.
        finally:
            Path(staged.name).unlink()
    if os.name == "posix":
        key_path.chmod(0o600)
    return key_path.read_text(encoding="utf-8").strip()


def create_app(test_config=None):
    dataset = (test_config or {}).get("DATASET", os.environ.get("STUDYSPOT_DATASET", "campus"))
    if dataset not in ("campus", "sample"):
        raise ValueError("STUDYSPOT_DATASET must be campus or sample.")
    campus = dataset == "campus"
    catalog = {
        entry["id"]: entry for entry in json.loads((BASE / "campus-spaces.json").read_text(encoding="utf-8"))
    } if campus else {}
    app = Flask(__name__)
    instance = BASE / "instance"
    instance.mkdir(mode=0o700, exist_ok=True)
    if os.name == "posix":
        instance.chmod(0o700)
    database = "studyspot-campus.sqlite3" if campus else "studyspot.sqlite3"
    app.config.update(DATABASE=os.environ.get("STUDYSPOT_DATABASE", str(instance / database)),
                      MAX_CONTENT_LENGTH=16 * 1024,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                      SESSION_COOKIE_SECURE=os.environ.get("STUDYSPOT_SECURE_COOKIE") == "1")
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = os.environ.get("STUDYSPOT_SECRET") or local_session_key(instance)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"], timeout=10)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    @app.teardown_appcontext
    def close_db(error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        db = get_db()
        db.executescript((BASE / "schema.sql").read_text(encoding="utf-8"))
        with db:
            db.execute("BEGIN IMMEDIATE")
            identity = db.execute("SELECT dataset FROM catalog_identity WHERE id=1").fetchone()
            if identity and identity["dataset"] != dataset:
                raise ValueError("The database belongs to a different StudySpot catalog.")
            if not identity:
                if db.execute("SELECT 1 FROM study_spaces LIMIT 1").fetchone() and campus:
                    raise ValueError("Use a new campus database. Existing unlabelled data may be from the sample catalog.")
                db.execute("INSERT INTO catalog_identity VALUES (1,?)", (dataset,))
            if campus:
                db.executemany(
                    """INSERT INTO study_spaces(id,name,location,description,study_type,outlets,atmosphere)
                       VALUES (:id,:name,:location,:description,:study_type,0,:atmosphere)
                       ON CONFLICT(id) DO UPDATE SET name=excluded.name, location=excluded.location,
                           description=excluded.description, study_type=excluded.study_type,
                           atmosphere=excluded.atmosphere
                       WHERE name!=excluded.name OR location!=excluded.location OR
                           description!=excluded.description OR study_type!=excluded.study_type OR
                           atmosphere!=excluded.atmosphere""",
                    catalog.values(),
                )
            elif db.execute("SELECT COUNT(*) FROM study_spaces").fetchone()[0] == 0:
                db.executemany(
                    "INSERT INTO study_spaces(name, location, description, study_type, outlets, atmosphere) VALUES (?,?,?,?,?,?)",
                    SAMPLE_SPACES,
                )

    @app.after_request
    def set_browser_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        return response

    @app.context_processor
    def shared():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(24)
        return {"csrf_token": session["csrf_token"], "crowd_options": CROWD, "noise_options": NOISE, "campus": campus}

    @app.get("/")
    def explore():
        try:
            filters = parse_filters(
                request.args.get("q", ""), request.args.get("study", ""),
                "" if campus else request.args.get("outlets", ""), request.args.get("atmosphere", ""),
            )
        except ValueError as error:
            abort(400, description=str(error))
        sql, args = build_space_query(filters)
        rows = get_db().execute(sql, args).fetchall()
        return render_template("explore.html", spaces=rows, filters=filters)

    @app.get("/spaces/<int:space_id>")
    def detail(space_id):
        db = get_db()
        space = db.execute("SELECT * FROM study_spaces WHERE id=?", (space_id,)).fetchone()
        if space is None:
            abort(404)
        info = catalog.get(space_id)
        directions = None
        if info:
            query = urlencode({"api": 1, "query": info["map_query"]})
            directions = f"https://www.google.com/maps/search/?{query}"
        return render_template(
            "detail.html", space=space, reports=recent_reports(space_id),
            info=info, directions=directions,
        )

    def recent_reports(space_id):
        rows = get_db().execute(
            "SELECT * FROM status_reports WHERE space_id=? ORDER BY created_at DESC, id DESC LIMIT 5",
            (space_id,),
        ).fetchall()
        now = utc_now()
        return [report_view(row, now) for row in rows]

    @app.get("/spaces/<int:space_id>/live")
    def live_reports(space_id):
        if not get_db().execute("SELECT 1 FROM study_spaces WHERE id=?", (space_id,)).fetchone():
            abort(404)
        # This public fragment has no form or session-specific data.
        fragment = app.jinja_env.get_template("observations.html").render(reports=recent_reports(space_id))
        return Response(fragment, headers={"Cache-Control": "no-store"})

    @app.post("/spaces/<int:space_id>/reports")
    def submit_report(space_id):
        db = get_db()
        if not db.execute("SELECT 1 FROM study_spaces WHERE id=?", (space_id,)).fetchone():
            abort(404)
        submitted_token = request.form.get("csrf_token", "").encode("utf-8")
        expected_token = session.get("csrf_token")
        if expected_token is None or not secrets.compare_digest(submitted_token, expected_token.encode("utf-8")):
            abort(400, description="The form expired. Return to the place page and try again.")
        try:
            crowd, noise = validate_report_fields(request.form.get("crowd"), request.form.get("noise"))
        except ValueError as error:
            abort(400, description=str(error))
        # Use the direct peer, not client-supplied forwarding headers. Store no raw IP.
        signing_key = app.config["SECRET_KEY"]
        if isinstance(signing_key, str):
            signing_key = signing_key.encode("utf-8")
        source = hmac.digest(signing_key, (request.remote_addr or "").encode("utf-8"), "sha256").hex()
        with db:
            db.execute("BEGIN IMMEDIATE")
            now = utc_now()
            timestamp = now.timestamp()
            allowed = db.execute(
                """INSERT INTO report_cooldowns(space_id, source, expires_at) VALUES (?,?,?)
                   ON CONFLICT(space_id, source) DO UPDATE SET expires_at = excluded.expires_at
                   WHERE report_cooldowns.expires_at <= ?""",
                (space_id, source, timestamp + REPORT_COOLDOWN_SECONDS, timestamp),
            ).rowcount
            if not allowed:
                row = db.execute(
                    "SELECT expires_at FROM report_cooldowns WHERE space_id=? AND source=?",
                    (space_id, source),
                ).fetchone()
                raise TooManyRequests(
                    "Please wait before sending another report for this space.",
                    retry_after=ceil(row["expires_at"] - timestamp),
                )
            db.execute("DELETE FROM report_cooldowns WHERE expires_at <= ?", (timestamp,))
            db.execute(
                "INSERT INTO status_reports(space_id,crowd,noise,created_at) VALUES (?,?,?,?)",
                (space_id, crowd, noise, now.isoformat()),
            )
        flash("Your update was saved.")
        return redirect(url_for("detail", space_id=space_id) + "#latest", code=303)

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(413)
    @app.errorhandler(429)
    def error_page(error):
        response = error.get_response()
        response.set_data(render_template("error.html", error=error))
        return response

    @app.get("/health")
    def health():
        get_db().execute("SELECT 1").fetchone()
        return {"status": "ok", "dataset": dataset}

    return app


if __name__ == "__main__":
    create_app().run(
        host=os.environ.get("STUDYSPOT_HOST", "127.0.0.1"),
        port=int(os.environ.get("STUDYSPOT_PORT", "5000")),
        debug=False,
    )
