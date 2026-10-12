"""Catalogo publico: home, explorar y ficha (Fase B)."""
import sqlite3
from functools import wraps  # noqa: F401  (reservado extension Fase C)

from flask import Blueprint, abort, current_app, g, render_template, request, session

from nexus.database import get_connection

bp = Blueprint("catalog", __name__)


def _db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = get_connection(current_app.config["DATABASE_PATH"])
    return g.db


def _fav_ids(db) -> set:
    uid = session.get("user_id")
    if not uid:
        return set()
    return {r["book_id"] for r in db.execute("SELECT book_id FROM favorites WHERE user_id = ?", (uid,))}


@bp.teardown_request
def _close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


BOOK_SELECT = (
    "SELECT b.*, "
    "(SELECT name FROM publishers p WHERE p.id = b.publisher_id) AS publisher_name, "
    "GROUP_CONCAT(DISTINCT a.name) AS author_names, "
    "GROUP_CONCAT(DISTINCT gn.name) AS genre_names, "
    "((SELECT COUNT(*) FROM library_entries le WHERE le.book_id = b.id) "
    " + (SELECT COUNT(*) FROM favorites f WHERE f.book_id = b.id) "
    " + (SELECT COUNT(*) FROM demo_order_items doi WHERE doi.book_id = b.id)) AS popularity "
    "FROM books b "
    "LEFT JOIN book_authors ba ON ba.book_id = b.id "
    "LEFT JOIN authors a ON a.id = ba.author_id "
    "LEFT JOIN book_genres bg ON bg.book_id = b.id "
    "LEFT JOIN genres gn ON gn.id = bg.genre_id"
)

ORDER_MAP = {
    "titulo_az": "b.title COLLATE NOCASE ASC",
    "novedad": "b.created_at DESC",
    "anio": "b.publication_year DESC",
}

# Idiomas con contenido: fijo y mínimo (afiliados ES/EN).
IDIOMAS = (("es", "Español"), ("en", "English"))


@bp.get("/")
def home():
    db = _db()
    populares = db.execute(
        BOOK_SELECT + " WHERE b.is_available = 1"
        " GROUP BY b.id ORDER BY popularity DESC, b.created_at DESC LIMIT 10"
    ).fetchall()
    hay_favs = db.execute("SELECT 1 FROM favorites LIMIT 1").fetchone() is not None
    if not hay_favs:
        # Sin favoritos todavía: muestra 10 al azar para no dejar la sección vacía.
        populares = db.execute(
            BOOK_SELECT + " WHERE b.is_available = 1 GROUP BY b.id ORDER BY RANDOM() LIMIT 10"
        ).fetchall()
    total = db.execute("SELECT COUNT(*) FROM books WHERE is_available = 1").fetchone()[0]
    vacio = total == 0
    generos = db.execute("SELECT name, slug FROM genres ORDER BY name").fetchall()
    q = (request.args.get("q") or "").strip()
    return render_template(
        "index.html", populares=populares, vacio=vacio, fav_ids=_fav_ids(db),
        generos=generos, q=q,
    )


@bp.get("/explorar")
def explorar():
    db = _db()
    q = (request.args.get("q") or "").strip()
    genero = (request.args.get("genero") or "").strip()
    idioma = (request.args.get("idioma") or "").strip()
    if idioma not in (c for c, _ in IDIOMAS):
        idioma = ""
    orden = request.args.get("orden", "novedad").strip()
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1
    per_page = int(current_app.config.get("BOOKS_PER_PAGE", 24))

    conds = ["b.is_available = 1"]
    params: list = []
    if q:
        like = f"%{q}%"
        conds.append(
            "(b.title LIKE ? OR b.synopsis LIKE ? OR b.isbn LIKE ?"
            " OR EXISTS (SELECT 1 FROM book_authors ba2 JOIN authors a2 ON a2.id = ba2.author_id"
            " WHERE ba2.book_id = b.id AND a2.name LIKE ?))"
        )
        params.extend([like, like, like, like])
    if genero:
        conds.append(
            "EXISTS (SELECT 1 FROM book_genres bg2 JOIN genres g2 ON g2.id = bg2.genre_id"
            " WHERE bg2.book_id = b.id AND g2.slug = ?)"
        )
        params.append(genero)
    if idioma:
        conds.append("b.language = ?")
        params.append(idioma)

    where = (" WHERE " + " AND ".join(conds)) if conds else ""
    order_sql = ORDER_MAP.get(orden, ORDER_MAP["novedad"])
    if orden not in ORDER_MAP:
        orden = "novedad"

    total = db.execute(
        f"SELECT COUNT(DISTINCT b.id) FROM books b{where}", params
    ).fetchone()[0]
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages)
    offset = (page - 1) * per_page

    libros = db.execute(
        f"{BOOK_SELECT}{where} GROUP BY b.id ORDER BY {order_sql} LIMIT ? OFFSET ?",
        [*params, per_page, offset],
    ).fetchall()
    generos = db.execute("SELECT name, slug FROM genres ORDER BY name").fetchall()
    return render_template(
        "catalog.html",
        libros=libros,
        total=total,
        page=page,
        pages=pages,
        per_page=per_page,
        q=q,
        genero=genero,
        idioma=idioma,
        orden=orden,
        generos=generos,
        idiomas=IDIOMAS,
        fav_ids=_fav_ids(db),
    )


@bp.get("/libro/<int:book_id>")
def detalle(book_id: int):
    db = _db()
    libro = db.execute(
        BOOK_SELECT + " WHERE b.id = ? GROUP BY b.id", (book_id,)
    ).fetchone()
    if libro is None:
        abort(404)
    relacionados = db.execute(
        "SELECT DISTINCT b.*, GROUP_CONCAT(DISTINCT a.name) AS author_names "
        "FROM books b "
        "LEFT JOIN book_authors ba ON ba.book_id = b.id "
        "LEFT JOIN authors a ON a.id = ba.author_id "
        "WHERE b.id != ? AND b.is_available = 1 AND ("
        " EXISTS (SELECT 1 FROM book_genres g1 JOIN book_genres g2 ON g1.genre_id = g2.genre_id"
        "  WHERE g1.book_id = b.id AND g2.book_id = ?)"
        " OR EXISTS (SELECT 1 FROM book_authors t1 JOIN book_authors t2 ON t1.author_id = t2.author_id"
        "  WHERE t1.book_id = b.id AND t2.book_id = ?)"
        ") GROUP BY b.id LIMIT 4",
        (book_id, book_id, book_id),
    ).fetchall()
    return render_template("book_detail.html", libro=libro, relacionados=relacionados, fav_ids=_fav_ids(db))
