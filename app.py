"""StudySpot Sprint 2: a local Flask/SQLite prototype with sample locations."""
from datetime import datetime, timezone
from pathlib import Path
import os
import secrets
import sqlite3

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for

from domain import CROWD, NOISE, build_space_query, parse_filters, report_view, validate_report_fields

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


def create_app(test_config=None):
    app = Flask(__name__)
    instance = BASE / "instance"
    instance.mkdir(exist_ok=True)
    app.config.update(DATABASE=str(instance / "studyspot.sqlite3"), MAX_CONTENT_LENGTH=16 * 1024,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        secret_path = instance / "session.key"
        if not secret_path.exists():
            secret_path.write_text(secrets.token_hex(32), encoding="utf-8")
        app.config["SECRET_KEY"] = os.environ.get("STUDYSPOT_SECRET", secret_path.read_text().strip())

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
        if db.execute("SELECT COUNT(*) FROM study_spaces").fetchone()[0] == 0:
            db.executemany("INSERT INTO study_spaces(name, location, description, study_type, outlets, atmosphere) VALUES (?,?,?,?,?,?)", SAMPLE_SPACES)
            db.commit()

    @app.context_processor
    def shared():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(24)
        return {"csrf_token": session["csrf_token"], "crowd_options": CROWD, "noise_options": NOISE}

    @app.get("/")
    def explore():
        try:
            filters = parse_filters(
                request.args.get("q", ""), request.args.get("study", ""),
                request.args.get("outlets", ""), request.args.get("atmosphere", ""),
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
        rows = db.execute("SELECT * FROM status_reports WHERE space_id=? ORDER BY created_at DESC, id DESC LIMIT 5", (space_id,)).fetchall()
        reports = [report_view(r, utc_now()) for r in rows]
        return render_template("detail.html", space=space, reports=reports, latest=reports[0] if reports else None)

    @app.post("/spaces/<int:space_id>/reports")
    def submit_report(space_id):
        db = get_db()
        if not db.execute("SELECT 1 FROM study_spaces WHERE id=?", (space_id,)).fetchone():
            abort(404)
        if not secrets.compare_digest(request.form.get("csrf_token", ""), session.get("csrf_token", "INVALID")):
            abort(400, description="The form expired. Return to the place page and try again.")
        try:
            crowd, noise = validate_report_fields(request.form.get("crowd"), request.form.get("noise"))
        except ValueError as error:
            abort(400, description=str(error))
        with db:
            db.execute("INSERT INTO status_reports(space_id,crowd,noise,created_at) VALUES (?,?,?,?)", (space_id, crowd, noise, utc_now().isoformat()))
        flash("Your update was saved.")
        return redirect(url_for("detail", space_id=space_id) + "#latest", code=303)

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(413)
    def error_page(error):
        return render_template("error.html", error=error), error.code

    @app.get("/health")
    def health():
        get_db().execute("SELECT 1").fetchone()
        return {"status": "ok", "dataset": "sample"}

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("STUDYSPOT_PORT", "5000")), debug=False)
