"""Account routes; SQLite identity is always derived from the signed session."""
from datetime import timedelta
from hashlib import sha256
import re
import secrets
import sqlite3

from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


def register_accounts(app, get_db, clock):
    """Install account routes without changing public discovery or legacy reports."""
    routes = Blueprint("accounts", __name__)
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
    app.config["SESSION_REFRESH_EACH_REQUEST"] = False
    # Equal-cost verification also applies when the submitted account is unknown.
    dummy_hash = generate_password_hash(secrets.token_urlsafe(32))

    def session_digest():
        return sha256(session.get("auth_token", "").encode()).hexdigest()

    def revoke():
        with get_db() as db:
            db.execute("DELETE FROM auth_sessions WHERE token_hash=?", (session_digest(),))
        session.clear()

    def check_csrf():
        expected = session.get("csrf_token")
        supplied = request.form.get("csrf_token", "")
        if not expected or not secrets.compare_digest(supplied.encode(), expected.encode()):
            abort(400, description="The form expired. Reload and try again.")

    @app.before_request
    def load_user():
        g.user = None
        user_id = session.get("user_id")
        if user_id is None:
            return
        expires = session.get("auth_expires", 0)
        if clock().timestamp() >= expires:
            revoke()
            return
        g.user = get_db().execute(
            "SELECT u.id,u.email FROM users u JOIN auth_sessions s ON s.user_id=u.id "
            "WHERE u.id=? AND s.token_hash=? AND s.expires_at>?",
            (user_id, session_digest(), clock().timestamp()),
        ).fetchone()
        if g.user is None:
            revoke()

    def form(mode, message=None, status=200):
        return render_template("account.html", mode=mode, message=message), status

    @routes.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "GET":
            return form("register")
        check_csrf()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not re.fullmatch(r"[^\s@]{1,64}@[^\s@]+\.[^\s@]+", email) or len(email) > 254:
            return form("register", "Enter a valid email address.", 400)
        if not 8 <= len(password) <= 128:
            return form("register", "Use a password of 8 to 128 characters.", 400)
        password_hash = generate_password_hash(password)
        try:
            with get_db() as db:
                db.execute("INSERT INTO users(email,password_hash) VALUES (?,?)", (email, password_hash))
        except sqlite3.IntegrityError:
            # Do not expose whether an email already has an account.
            pass
        flash("If registration was available, your account is ready. Please log in.")
        return redirect(url_for("accounts.login"), code=303)

    @routes.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return form("login")
        check_csrf()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if len(email) > 254 or not 8 <= len(password) <= 128:
            return form("login", "Invalid email or password.", 400)
        user = get_db().execute("SELECT id,password_hash FROM users WHERE email=?", (email,)).fetchone()
        valid = check_password_hash(user["password_hash"] if user else dummy_hash, password)
        if not valid or user is None:
            return form("login", "Invalid email or password.", 400)
        revoke()
        session.permanent = True
        session["user_id"] = user["id"]
        session["auth_expires"] = (clock() + app.permanent_session_lifetime).timestamp()
        session["auth_token"] = secrets.token_urlsafe(32)
        with get_db() as db:
            db.execute("DELETE FROM auth_sessions WHERE expires_at<=?", (clock().timestamp(),))
            db.execute("INSERT INTO auth_sessions(token_hash,user_id,expires_at) VALUES (?,?,?)",
                       (session_digest(), user["id"], session["auth_expires"]))
        session["csrf_token"] = secrets.token_urlsafe(24)
        return redirect(url_for("accounts.account"), code=303)

    @routes.get("/account")
    def account():
        if g.user is None:
            return redirect(url_for("accounts.login"), code=303)
        return form("account")

    @routes.post("/logout")
    def logout():
        check_csrf()
        revoke()
        return redirect(url_for("explore"), code=303)

    app.register_blueprint(routes)
