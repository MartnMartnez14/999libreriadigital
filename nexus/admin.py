"""Admin Fase B: decorador real de auth + CRUD minimo parametrizado."""
import os
import re
import unicodedata

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.utils import secure_filename

from nexus.auth import admin_required
from nexus.database import get_connection

bp = Blueprint("admin", __name__, url_prefix="/admin")

PORTADA_EXTS = {"png", "jpg", "jpeg", "webp"}
PORTADA_MAX_BYTES = 2 * 1024 * 1024


def _db():
    if "db" not in g:
        g.db = get_connection(current_app.config["DATABASE_PATH"])
    return g.db


@bp.teardown_request
def _close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _validar_external_url(raw: str, errores: list) -> str | None:
    url = (raw or "").strip() or None
    if url is None:
        return None
    if len(url) > 2048:
        errores.append("La URL externa supera 2048 caracteres.")
        return None
    if not (url.startswith("http://") or url.startswith("https://")):
        errores.append("La URL externa debe empezar por http:// o https://.")
        return None
    return url


def _guardar_portada(archivo, book_id: int) -> str | None:
    """Valida y guarda la portada. Devuelve ruta relativa a static/ o None."""
    if archivo is None or not (archivo.filename or "").strip():
        return None
    nombre = secure_filename(archivo.filename.strip())
    ext = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
    if ext not in PORTADA_EXTS:
        raise ValueError("Portada: solo PNG, JPG o WEBP.")
    data = archivo.read()
    if len(data) > PORTADA_MAX_BYTES:
        raise ValueError("Portada: máximo 2 MB.")
    if len(data) == 0:
        raise ValueError("Portada: archivo vacío.")
    destino_dir = os.path.join(current_app.static_folder, "covers")
    os.makedirs(destino_dir, exist_ok=True)
    final = f"{book_id}_{secure_filename(nombre)}"
    with open(os.path.join(destino_dir, final), "wb") as f:
        f.write(data)
    return f"covers/{final}"


def _borrar_portada(rel: str | None) -> None:
    if not rel or not rel.startswith("covers/"):
        return
    nombre = rel[len("covers/"):]
    if not nombre or "/" in nombre or nombre.startswith("."):
        return
    ruta = os.path.join(current_app.static_folder, "covers", nombre)
    try:
        if os.path.isfile(ruta):
            os.remove(ruta)
    except OSError:
        pass


def _slugify(texto: str) -> str:
    base = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-") or "genero"


def _validar_libro(form) -> tuple[dict, list]:
    errores = []
    titulo = (form.get("title") or "").strip()
    if not titulo:
        errores.append("El titulo es obligatorio.")
    try:
        year = int(form.get("publication_year") or 0) if form.get("publication_year") else None
        if year is not None and not 1000 <= year <= 2100:
            errores.append("Ano fuera de rango (1000-2100).")
    except ValueError:
        year = None
        errores.append("Ano no valido.")
    idioma = (form.get("language") or "es").strip()
    if idioma not in ("es", "en"):
        idioma = "es"
    publisher_id = form.get("publisher_id") or ""
    publisher_id = int(publisher_id) if publisher_id.isdigit() else None
    datos = {
        "title": titulo,
        "synopsis": (form.get("synopsis") or "").strip() or None,
        "publisher_id": publisher_id,
        "publication_year": year,
        "isbn": (form.get("isbn") or "").strip() or None,
        "language": idioma,
        "external_url": _validar_external_url(form.get("external_url") or "", errores),
    }
    return datos, errores


def _guardar_m2m(db, book_id: int, author_ids: list, genre_ids: list) -> None:
    db.execute("DELETE FROM book_authors WHERE book_id = ?", (book_id,))
    for aid in author_ids:
        db.execute(
            "INSERT OR IGNORE INTO book_authors(book_id, author_id) VALUES (?, ?)",
            (book_id, aid),
        )
    db.execute("DELETE FROM book_genres WHERE book_id = ?", (book_id,))
    for gid in genre_ids:
        db.execute(
            "INSERT OR IGNORE INTO book_genres(book_id, genre_id) VALUES (?, ?)",
            (book_id, gid),
        )


@bp.get("/libros")
@admin_required
def listar_libros():
    db = _db()
    libros = db.execute(
        "SELECT b.*, GROUP_CONCAT(DISTINCT a.name) AS author_names "
        "FROM books b LEFT JOIN book_authors ba ON ba.book_id = b.id "
        "LEFT JOIN authors a ON a.id = ba.author_id "
        "GROUP BY b.id ORDER BY b.title COLLATE NOCASE ASC LIMIT 200"
    ).fetchall()
    return render_template("admin/books.html", libros=libros)


@bp.route("/libros/nuevo", methods=["GET", "POST"])
@admin_required
def crear_libro():
    db = _db()
    autores = db.execute("SELECT id, name FROM authors ORDER BY name").fetchall()
    generos = db.execute("SELECT id, name FROM genres ORDER BY name").fetchall()
    editoriales = db.execute("SELECT id, name FROM publishers ORDER BY name").fetchall()
    if request.method == "POST":
        datos, errores = _validar_libro(request.form)
        if errores:
            for e in errores:
                flash(e, "error")
        else:
            try:
                cur = db.execute(
                    "INSERT INTO books(title, synopsis, publisher_id, publication_year,"
                    " isbn, language, external_url)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    tuple(datos.values()),
                )
                book_id = cur.lastrowid
                try:
                    rel = _guardar_portada(request.files.get("cover"), book_id)
                except ValueError as exc:
                    db.rollback()
                    flash(str(exc), "error")
                    return render_template("admin/book_form.html", libro=None, autores=autores, generos=generos, editoriales=editoriales)
                if rel:
                    db.execute("UPDATE books SET cover_path = ? WHERE id = ?", (rel, book_id))
                aids = [int(x) for x in request.form.getlist("author_ids") if x.isdigit()]
                gids = [int(x) for x in request.form.getlist("genre_ids") if x.isdigit()]
                _guardar_m2m(db, book_id, aids, gids)
                db.commit()
                flash("Libro creado.", "ok")
                return redirect(url_for("admin.listar_libros"))
            except Exception as exc:  # ISBN duplicado, etc.
                db.rollback()
                flash(f"No se pudo crear: {exc}", "error")
    return render_template("admin/book_form.html", libro=None, autores=autores, generos=generos, editoriales=editoriales)


@bp.route("/libros/<int:book_id>/editar", methods=["GET", "POST"])
@admin_required
def editar_libro(book_id: int):
    db = _db()
    libro = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if libro is None:
        abort(404)
    autores = db.execute("SELECT id, name FROM authors ORDER BY name").fetchall()
    generos = db.execute("SELECT id, name FROM genres ORDER BY name").fetchall()
    editoriales = db.execute("SELECT id, name FROM publishers ORDER BY name").fetchall()
    sel_a = {r["author_id"] for r in db.execute("SELECT author_id FROM book_authors WHERE book_id = ?", (book_id,))}
    sel_g = {r["genre_id"] for r in db.execute("SELECT genre_id FROM book_genres WHERE book_id = ?", (book_id,))}
    if request.method == "POST":
        datos, errores = _validar_libro(request.form)
        if errores:
            for e in errores:
                flash(e, "error")
        else:
            try:
                try:
                    rel = _guardar_portada(request.files.get("cover"), book_id)
                except ValueError as exc:
                    db.rollback()
                    flash(str(exc), "error")
                    return render_template(
                        "admin/book_form.html", libro=libro, autores=autores, generos=generos,
                        editoriales=editoriales, sel_a=sel_a, sel_g=sel_g,
                    )
                if rel:
                    _borrar_portada(libro["cover_path"])
                    db.execute("UPDATE books SET cover_path = ? WHERE id = ?", (rel, book_id))
                db.execute(
                    "UPDATE books SET title=?, synopsis=?, publisher_id=?,"
                    " publication_year=?, isbn=?, language=?,"
                    " external_url=?, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')"
                    " WHERE id=?",
                    (*tuple(datos.values()), book_id),
                )
                aids = [int(x) for x in request.form.getlist("author_ids") if x.isdigit()]
                gids = [int(x) for x in request.form.getlist("genre_ids") if x.isdigit()]
                _guardar_m2m(db, book_id, aids, gids)
                db.commit()
                flash("Libro actualizado.", "ok")
                return redirect(url_for("admin.listar_libros"))
            except Exception as exc:
                db.rollback()
                flash(f"No se pudo actualizar: {exc}", "error")
    return render_template(
        "admin/book_form.html", libro=libro, autores=autores, generos=generos,
        editoriales=editoriales, sel_a=sel_a, sel_g=sel_g,
    )


@bp.post("/libros/<int:book_id>/estado")
@admin_required
def cambiar_estado(book_id: int):
    db = _db()
    cur = db.execute("UPDATE books SET is_available = 1 - is_available WHERE id = ?", (book_id,))
    db.commit()
    if cur.rowcount == 0:
        abort(404)
    row = db.execute("SELECT is_available FROM books WHERE id = ?", (book_id,)).fetchone()
    flash("Libro activado." if row["is_available"] else "Libro desactivado.", "ok")
    return redirect(url_for("admin.listar_libros"))


@bp.route("/autores", methods=["GET", "POST"])
@admin_required
def gestionar_autores():
    db = _db()
    if request.method == "POST":
        nombre = (request.form.get("name") or "").strip()
        if not nombre:
            flash("El nombre del autor es obligatorio.", "error")
        else:
            try:
                db.execute("INSERT INTO authors(name) VALUES (?)", (nombre,))
                db.commit()
                flash("Autor guardado.", "ok")
            except Exception as exc:
                db.rollback()
                flash(f"No se pudo guardar: {exc}", "error")
        return redirect(url_for("admin.gestionar_autores"))
    autores = db.execute("SELECT * FROM authors ORDER BY name").fetchall()
    return render_template("admin/authors.html", autores=autores)


@bp.route("/editoriales", methods=["GET", "POST"])
@admin_required
def gestionar_editoriales():
    db = _db()
    if request.method == "POST":
        nombre = (request.form.get("name") or "").strip()
        if not nombre:
            flash("El nombre de la editorial es obligatorio.", "error")
        else:
            try:
                db.execute("INSERT INTO publishers(name) VALUES (?)", (nombre,))
                db.commit()
                flash("Editorial guardada.", "ok")
            except Exception as exc:
                db.rollback()
                flash(f"No se pudo guardar: {exc}", "error")
        return redirect(url_for("admin.gestionar_editoriales"))
    editoriales = db.execute("SELECT * FROM publishers ORDER BY name").fetchall()
    return render_template("admin/publishers.html", editoriales=editoriales)


@bp.route("/generos", methods=["GET", "POST"])
@admin_required
def gestionar_generos():
    db = _db()
    if request.method == "POST":
        nombre = (request.form.get("name") or "").strip()
        if not nombre:
            flash("El nombre del género es obligatorio.", "error")
        else:
            try:
                db.execute("INSERT INTO genres(name, slug) VALUES (?, ?)", (nombre, _slugify(nombre)))
                db.commit()
                flash("Genero guardado.", "ok")
            except Exception as exc:
                db.rollback()
                flash(f"No se pudo guardar: {exc}", "error")
        return redirect(url_for("admin.gestionar_generos"))
    generos = db.execute("SELECT * FROM genres ORDER BY name").fetchall()
    return render_template("admin/genres.html", generos=generos)
