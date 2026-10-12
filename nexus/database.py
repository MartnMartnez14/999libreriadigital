"""Conexión SQLite + init con foreign_keys ON."""
import os
import sqlite3

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")
MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "migrations")


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    return any(r["name"] == column for r in conn.execute(f"PRAGMA table_info({table})").fetchall())


def init_db(db_path: str) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = f.read()
    conn = get_connection(db_path)
    try:
        conn.executescript(schema)
        cur = conn.execute("SELECT COUNT(*) FROM schema_version")
        if cur.fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO schema_version(version, description) VALUES (1, 'init nexus v1.0')"
            )
        conn.commit()
        # Migración 02: affiliate_source si la columna no existe (idempotente).
        if not _has_column(conn, "books", "affiliate_source"):
            mig = os.path.join(MIGRATIONS_DIR, "02_affiliate_source.sql")
            with open(mig, encoding="utf-8") as f:
                conn.executescript(f.read())
        # Migración 03: géneros base (idempotente por INSERT OR IGNORE).
        mig3 = os.path.join(MIGRATIONS_DIR, "03_generos_base.sql")
        with open(mig3, encoding="utf-8") as f:
            conn.executescript(f.read())
        # Migración 04: editoriales + books.publisher_id (idempotente).
        mig4 = os.path.join(MIGRATIONS_DIR, "04_publishers.sql")
        with open(mig4, encoding="utf-8") as f:
            conn.executescript(f.read())
        if not _has_column(conn, "books", "publisher_id"):
            conn.execute(
                "ALTER TABLE books ADD COLUMN publisher_id INTEGER REFERENCES publishers(id)"
            )
        conn.commit()
    finally:
        conn.close()
