"""Auth: registro, login/logout con sesiones Flask, CSRF propio y rate-limit."""
import secrets
import time
from collections import defaultdict
from functools import wraps

from flask import (
    Blueprint, abort, current_app, flash, g, redirect, render_template,
    request, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from nexus.database import get_connection

bp = Blueprint("auth", __name__)

# Rate-limit login en memoria: máx 5 intentos / 5 min por IP.
_LOGIN_ATTEMPTS: dict[str, list[float]] = defaultdict(list)
MAX_ATTEMPTS = 5
WINDOW_SECS = 5 * 60


def _db():
    if "db" not in g:
        g.db = get_connection(current_app.config["DATABASE_PATH"])
    return g.db


@bp.teardown_request
def _close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _csrf_token() -> str:
    tok = session.get("csrf_token")
    if not tok:
        tok = secrets.token_hex(32)
        session["csrf_token"] = tok
    return tok


@bp.app_context_processor
def _inject_csrf():
    return {"csrf_token": _csrf_token}


def _check_csrf() -> bool:
    return session.get("csrf_token") and request.form.get("csrf_token") == session["csrf_token"]


def _rate_limited(ip: str) -> bool:
    now = time.time()
    hits = [t for t in _LOGIN_ATTEMPTS[ip] if now - t < WINDOW_SECS]
    _LOGIN_ATTEMPTS[ip] = hits
    return len(hits) >= MAX_ATTEMPTS


def _register_attempt(ip: str) -> None:
    _LOGIN_ATTEMPTS[ip].append(time.time())


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Inicia sesión para continuar.", "error")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("user_id") or session.get("role") != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapper


@bp.route("/registro", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not _check_csrf():
            abort(400)
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip() or None
        password = request.form.get("password") or ""
        if not username or len(password) < 6:
            flash("Usuario obligatorio y contraseña mínima de 6 caracteres.", "error")
            return render_template("auth/register.html")
        db = _db()
        try:
            db.execute(
                "INSERT INTO users(username, email, password_hash, role) VALUES (?, ?, ?, 'user')",
                (username, email, generate_password_hash(password)),
            )
            db.commit()
        except Exception:
            db.rollback()
            flash("Nombre de usuario o email ya en uso.", "error")
            return render_template("auth/register.html")
        flash("Cuenta creada. Inicia sesión.", "ok")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if not _check_csrf():
            abort(400)
        ip = request.remote_addr or "unknown"
        if _rate_limited(ip):
            flash("Demasiados intentos. Espera 5 minutos.", "error")
            return render_template("auth/login.html"), 429
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        db = _db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user is None or not user["is_active"] or not check_password_hash(user["password_hash"], password):
            _register_attempt(ip)
            flash("Credenciales no válidas.", "error")
            return render_template("auth/login.html")
        _LOGIN_ATTEMPTS.pop(ip, None)
        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        session["csrf_token"] = secrets.token_hex(32)
        flash("Sesión iniciada.", "ok")
        nxt = request.args.get("next") or request.form.get("next") or "/"
        return redirect(nxt)
    return render_template("auth/login.html")


@bp.route("/logout", methods=["GET", "POST"])
def logout():
    if request.method == "POST" and not _check_csrf():
        abort(400)
    session.clear()
    flash("Sesión cerrada.", "ok")
    return redirect(url_for("catalog.home"))


@bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    db = _db()
    if request.method == "POST":
        if not _check_csrf():
            abort(400)
        actual = request.form.get("actual") or ""
        nueva = request.form.get("nueva") or ""
        user = db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        if user is None or not check_password_hash(user["password_hash"], actual):
            flash("La contraseña actual no es correcta.", "error")
        elif len(nueva) < 6:
            flash("La nueva contraseña debe tener al menos 6 caracteres.", "error")
        else:
            db.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                       (generate_password_hash(nueva), session["user_id"]))
            db.commit()
            flash("Contraseña actualizada.", "ok")
            return redirect(url_for("auth.perfil"))
    user = db.execute("SELECT id, username, email, role, created_at FROM users WHERE id = ?",
                      (session["user_id"],)).fetchone()
    counts = db.execute(
        "SELECT (SELECT COUNT(*) FROM library_entries WHERE user_id = ?) AS en_biblio,"
        " (SELECT COUNT(*) FROM favorites WHERE user_id = ?) AS en_favs",
        (session["user_id"], session["user_id"]),
    ).fetchone()
    return render_template("auth/perfil.html", user=user, counts=counts)
