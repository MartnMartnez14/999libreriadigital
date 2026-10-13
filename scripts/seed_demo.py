"""Carga datos de demo FICTICIOS en la base indicada por DATABASE_PATH.

Uso (recomendado, base separada de la tuya):
    DATABASE_PATH=instance/demo.db python scripts/seed_demo.py

Datos ficticios: autores, editoriales y libros inventados, con enlaces de ejemplo.
Usuarios demo: demo / demo123456 (usuario) y admin_demo / admin123456 (admin).
No usar en una base con datos reales.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash

from config import Config
from nexus.database import get_connection, init_db

USUARIOS = [
    ("demo", "demo@example.com", "demo123456", "user"),
    ("admin_demo", "admin@example.com", "admin123456", "admin"),
]

EDITORIALES = ["Editorial Ejemplo", "Ediciones Demo", "Letras de Prueba"]

# (título, subtítulo, autor, editorial, año, género-slug, páginas, precio céntimos, destacado, sinopsis)
LIBROS = [
    ("El río de papel", None, "Ana Solís", "Editorial Ejemplo", 2019, "literatura", 312, 1290, 1,
     "Una novela ficticia sobre una familia que administra una imprenta en un pueblo costero."),
    ("Mapas de la memoria", None, "Lucas Varela", "Ediciones Demo", 2021, "historia", 240, 1550, 1,
     "Libro inventado que recorre la historia de un barrio a través de sus cartógrafos."),
    ("Cuatro estaciones de cocina", None, "Marta Bellido", "Letras de Prueba", 2020, "cocina", 180, 990, 0,
     "Recetario de ejemplo organizado por temporadas. Recetas inventadas."),
    ("La noche del faro", "Un caso sin resolver", "Julián Ortega", "Editorial Ejemplo", 2022, "misterio-y-thriller", 290, 1190, 1,
     "Thriller ficticio: un farero desaparece y la isla empieza a guardar secretos."),
    ("Hábitos pequeños", None, "Carla Mena", "Ediciones Demo", 2018, "autoayuda", 205, 1100, 0,
     "Guía de ejemplo sobre cambios graduales en la rutina diaria."),
    ("Viaje al centro del código", None, "Diego Ríos", "Letras de Prueba", 2023, "ciencias", 260, 1490, 0,
     "Divulgación inventada sobre cómo piensan los programas, sin fórmulas."),
    ("Crónicas de Ciudad Lenta", None, "Sofía Navarro", "Editorial Ejemplo", 2017, "ciencia-ficcion-y-fantasia", 378, 1350, 0,
     "Ciencia ficción ficticia en una ciudad donde el tiempo se detiene por barrios."),
    ("Diario de un cuarto propio", None, "Elena Duarte", "Ediciones Demo", 2016, "biografia", 224, 1200, 0,
     "Biografía ficticia de una escritora que nunca existió, con fines demostrativos."),
    ("Filosofía para la sobremesa", None, "Pablo Iriarte", "Letras de Prueba", 2021, "filosofia", 166, 890, 0,
     "Ensayos cortos e inventados para conversar después de comer."),
    ("Canciones para el invierno", None, "Rosa Bermúdez", "Editorial Ejemplo", 2024, "romance", 198, 1040, 1,
     "Novela romántica ficticia ambientada en una estación de montaña."),
    ("Manual de finanzas domésticas", None, "Tomás Quiroga", "Ediciones Demo", 2022, "no-ficcion", 150, 790, 0,
     "Guía de ejemplo para ordenar gastos del hogar. Sin consejos reales de inversión."),
    ("El jardín de las sombras", None, "Irene Castro", "Letras de Prueba", 2020, "terror", 232, 1120, 0,
     "Relato de terror ficticio sobre una casa con un jardín que crece de noche."),
]

GENERO_ID_CACHE = {}


def _id_genero(db, slug):
    if slug not in GENERO_ID_CACHE:
        row = db.execute("SELECT id FROM genres WHERE slug = ?", (slug,)).fetchone()
        GENERO_ID_CACHE[slug] = row["id"] if row else None
    return GENERO_ID_CACHE[slug]


def _obtener_o_crear(db, tabla, columna, valor):
    row = db.execute(f"SELECT id FROM {tabla} WHERE {columna} = ?", (valor,)).fetchone()
    if row:
        return row["id"]
    return db.execute(f"INSERT INTO {tabla}({columna}) VALUES (?)", (valor,)).lastrowid


def main() -> None:
    init_db(Config.DATABASE_PATH)
    db = get_connection(Config.DATABASE_PATH)
    try:
        if db.execute("SELECT 1 FROM users WHERE username = 'demo'").fetchone():
            print("La base ya tiene datos de demo. Nada que cargar.")
            return

        for username, email, password, role in USUARIOS:
            db.execute(
                "INSERT INTO users(username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (username, email, generate_password_hash(password), role),
            )

        for nombre in EDITORIALES:
            _obtener_o_crear(db, "publishers", "name", nombre)

        for titulo, subtitulo, autor, editorial, anio, genero, paginas, precio, destacado, sinopsis in LIBROS:
            publisher_id = db.execute("SELECT id FROM publishers WHERE name = ?", (editorial,)).fetchone()["id"]
            cur = db.execute(
                """INSERT INTO books(title, subtitle, synopsis, publisher, publisher_id, publication_year,
                   isbn, language, pages, price_minor_units, currency, is_featured, external_url,
                   external_label, affiliate_source)
                   VALUES (?, ?, ?, ?, ?, ?, NULL, 'es', ?, ?, 'EUR', ?, 'https://example.com/demo', 'Ver en tienda (demo)', NULL)""",
                (titulo, subtitulo, sinopsis, editorial, publisher_id, anio, paginas, precio, destacado),
            )
            book_id = cur.lastrowid
            author_id = _obtener_o_crear(db, "authors", "name", autor)
            db.execute("INSERT INTO book_authors(book_id, author_id) VALUES (?, ?)", (book_id, author_id))
            genre_id = _id_genero(db, genero)
            if genre_id:
                db.execute("INSERT INTO book_genres(book_id, genre_id) VALUES (?, ?)", (book_id, genre_id))

        db.commit()
        print(f"Demo cargada en {Config.DATABASE_PATH}: {len(LIBROS)} libros ficticios.")
        print("Usuario: demo / demo123456 · Admin: admin_demo / admin123456")
    finally:
        db.close()


if __name__ == "__main__":
    main()
