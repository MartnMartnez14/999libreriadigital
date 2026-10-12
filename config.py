"""Configuración Librería Nexus (offline-first)."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _abs(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(BASE_DIR, path)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    DATABASE_PATH = _abs(os.environ.get("DATABASE_PATH", "instance/libreria.db"))
    BOOKS_DIR = _abs(os.environ.get("BOOKS_DIR", "protected_books"))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Secure solo con HTTPS (futuro online); en local queda False.
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    BOOKS_PER_PAGE = 24
