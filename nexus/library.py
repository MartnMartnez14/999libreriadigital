"""Biblioteca personal + favoritos."""
import sqlite3
from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for

from nexus.auth import login_required
from nexus.database import get_connection

bp = Blueprint("library", __name__)

STATUSES = ("pendiente", "leyendo", "terminado")


def _db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = get_connection(current_app.config["DATABASE_PATH"])
    return g.db


@bp.teardown_request
def _close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _adquirido(db, user_id: int, book_id: int) -> bool:
    row = db.execute(
        "SELECT 1 FROM demo_order_items doi JOIN demo_orders o ON o.id = doi.order_id"
        " WHERE o.user_id = ? AND doi.book_id = ? LIMIT 1", (user_id, book_id)
    ).fetchone()
    return row is not None


@bp.get("/biblioteca")
@login_required
def library():
    db = _db()
    uid = session["user_id"]
    entradas = db.execute(
        "SELECT b.*, le.status, le.progress_percent, le.started_at, le.finished_at, le.added_at"
        " FROM library_entries le JOIN books b ON b.id = le.book_id"
        " WHERE le.user_id = ? ORDER BY le.added_at DESC", (uid,)
    ).fetchall()
    contadores = db.execute(
        "SELECT COUNT(*) AS total,"
        " SUM(CASE WHEN status='pendiente' THEN 1 ELSE 0 END) AS pendientes,"
        " SUM(CASE WHEN status='leyendo' THEN 1 ELSE 0 END) AS leyendo,"
        " SUM(CASE WHEN status='terminado' THEN 1 ELSE 0 END) AS terminados"
        " FROM library_entries WHERE user_id = ?", (uid,)
    ).fetchone()
    return render_template("library.html", entradas=entradas, contadores=contadores)


@bp.post("/biblioteca/anadir/<int:book_id>")
@login_required
def add_book(book_id: int):
    db = _db()
    uid = session["user_id"]
    libro = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if libro is None:
        abort(404)
    # Solo si disponible y (gratis o adquirido vía demo_order) o es demo (precio 0).
    if not libro["is_available"]:
        flash("Libro no disponible.", "error")
        return redirect(url_for("catalog.detalle", book_id=book_id))
    es_demo = libro["price_minor_units"] == 0
    if not (libro["is_free"] or es_demo or _adquirido(db, uid, book_id)):
        flash("Adquiere el libro antes de añadirlo a tu biblioteca.", "error")
        return redirect(url_for("catalog.detalle", book_id=book_id))
    try:
        db.execute("INSERT INTO library_entries(user_id, book_id) VALUES (?, ?)", (uid, book_id))
        db.commit()
        flash("Añadido a tu biblioteca.", "ok")
    except Exception:
        db.rollback()
        flash("Ya está en tu biblioteca.", "error")
    return redirect(url_for("library.library"))


@bp.post("/biblioteca/quitar/<int:book_id>")
@login_required
def remove_book(book_id: int):
    db = _db()
    # Quitar visual: solo borra la entrada, nunca el libro.
    db.execute("DELETE FROM library_entries WHERE user_id = ? AND book_id = ?",
               (session["user_id"], book_id))
    db.commit()
    flash("Eliminado de tu biblioteca.", "ok")
    return redirect(url_for("library.library"))


@bp.post("/biblioteca/estado/<int:book_id>")
@login_required
def update_status(book_id: int):
    db = _db()
    status = (request.form.get("status") or "").strip()
    try:
        progress = max(0, min(100, int(request.form.get("progress_percent") or 0)))
    except ValueError:
        flash("Progreso no válido (0-100).", "error")
        return redirect(url_for("library.library"))
    if status not in STATUSES:
        flash("Estado no válido.", "error")
        return redirect(url_for("library.library"))
    cur = db.execute(
        "UPDATE library_entries SET status = ?, progress_percent = ?,"
        " started_at = CASE WHEN ? = 'leyendo' THEN COALESCE(started_at, strftime('%Y-%m-%dT%H:%M:%fZ','now')) ELSE started_at END,"
        " finished_at = CASE WHEN ? = 'terminado' THEN strftime('%Y-%m-%dT%H:%M:%fZ','now') ELSE NULL END"
        " WHERE user_id = ? AND book_id = ?",
        (status, progress, status, status, session["user_id"], book_id),
    )
    db.commit()
    if cur.rowcount == 0:
        abort(404)
    flash("Progreso actualizado.", "ok")
    return redirect(url_for("library.library"))


@bp.get("/favoritos")
@login_required
def favorites():
    db = _db()
    favs = db.execute(
        "SELECT b.*, GROUP_CONCAT(DISTINCT a.name) AS author_names"
        " FROM favorites f JOIN books b ON b.id = f.book_id"
        " LEFT JOIN book_authors ba ON ba.book_id = b.id"
        " LEFT JOIN authors a ON a.id = ba.author_id"
        " WHERE f.user_id = ? AND b.is_available = 1 GROUP BY b.id ORDER BY b.title COLLATE NOCASE ASC", (session["user_id"],)
    ).fetchall()
    return render_template("favorites.html", favs=favs)


@bp.post("/favoritos/toggle/<int:book_id>")
@login_required
def toggle_favorite(book_id: int):
    db = _db()
    uid = session["user_id"]
    if db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone() is None:
        abort(404)
    row = db.execute("SELECT id FROM favorites WHERE user_id = ? AND book_id = ?", (uid, book_id)).fetchone()
    if row:
        db.execute("DELETE FROM favorites WHERE user_id = ? AND book_id = ?", (uid, book_id))
        flash("Quitado de favoritos.", "ok")
    else:
        db.execute("INSERT INTO favorites(user_id, book_id) VALUES (?, ?)", (uid, book_id))
        flash("Añadido a favoritos.", "ok")
    db.commit()
    return redirect(request.referrer or url_for("library.favorites"))
