"""StudySpot Sprint 2: a local Flask/SQLite prototype with sample locations."""
from datetime import datetime, timezone
from pathlib import Path
import os
import secrets
import sqlite3

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for

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
CROWD = {"low": "Not busy", "medium": "Somewhat busy", "high": "Very busy"}
NOISE = {"quiet": "Quiet", "moderate": "Some conversation", "loud": "Loud"}


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

    def report_view(row):
        if not row:
            return None
        posted = datetime.fromisoformat(row["created_at"])
        minutes = max(0, int((utc_now() - posted).total_seconds() // 60))
        age = "Just now" if minutes == 0 else (f"{minutes} min ago" if minutes < 60 else (f"{minutes // 60} hours ago" if minutes < 1440 else f"{minutes // 1440} days ago"))
        return dict(row) | {"age": age, "stale": minutes >= 60, "crowd_label": CROWD[row["crowd"]], "noise_label": NOISE[row["noise"]], "display_time": posted.strftime("%Y-%m-%d %H:%M UTC")}

    @app.context_processor
    def shared():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(24)
        return {"csrf_token": session["csrf_token"], "crowd_options": CROWD, "noise_options": NOISE}

    @app.get("/")
    def explore():
        q = request.args.get("q", "").strip()[:120]
        study = request.args.get("study", "")
        outlets = request.args.get("outlets", "")
        atmosphere = request.args.get("atmosphere", "")
        if study not in ("", "individual", "group") or outlets not in ("", "yes") or atmosphere not in ("", "quiet"):
            abort(400, description="Choose one of the available filters.")
        conditions, args = [], []
        if q:
            escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            conditions.append("name LIKE ? ESCAPE '\\'")
            args.append("%" + escaped + "%")
        if study:
            conditions.append("study_type IN (?, 'both')")
            args.append(study)
        if outlets:
            conditions.append("outlets = 1")
        if atmosphere:
            conditions.append("atmosphere = 'quiet'")
        sql = "SELECT * FROM study_spaces" + (" WHERE " + " AND ".join(conditions) if conditions else "") + " ORDER BY name"
        rows = get_db().execute(sql, args).fetchall()
        return render_template("explore.html", spaces=rows, filters=dict(q=q, study=study, outlets=outlets, atmosphere=atmosphere))

    @app.get("/spaces/<int:space_id>")
    def detail(space_id):
        db = get_db()
        space = db.execute("SELECT * FROM study_spaces WHERE id=?", (space_id,)).fetchone()
        if space is None:
            abort(404)
        rows = db.execute("SELECT * FROM status_reports WHERE space_id=? ORDER BY created_at DESC, id DESC LIMIT 5", (space_id,)).fetchall()
        reports = [report_view(r) for r in rows]
        return render_template("detail.html", space=space, reports=reports, latest=reports[0] if reports else None)

    @app.post("/spaces/<int:space_id>/reports")
    def submit_report(space_id):
        db = get_db()
        if not db.execute("SELECT 1 FROM study_spaces WHERE id=?", (space_id,)).fetchone():
            abort(404)
        if not secrets.compare_digest(request.form.get("csrf_token", ""), session.get("csrf_token", "INVALID")):
            abort(400, description="The form expired. Return to the place page and try again.")
        crowd, noise = request.form.get("crowd"), request.form.get("noise")
        if crowd not in CROWD or noise not in NOISE:
            abort(400, description="Select a crowd level and a noise level.")
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
