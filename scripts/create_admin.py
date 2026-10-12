"""Crea el primer administrador (uso local). Uso: python scripts/create_admin.py USUARIO CONTRASEÑA [EMAIL]"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash

from config import Config
from nexus.database import get_connection, init_db


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(2)
    username, password = sys.argv[1], sys.argv[2]
    email = sys.argv[3] if len(sys.argv) > 3 else None
    if len(password) < 6:
        print("La contraseña debe tener al menos 6 caracteres.")
        raise SystemExit(1)
    init_db(Config.DATABASE_PATH)
    db = get_connection(Config.DATABASE_PATH)
    try:
        db.execute(
            "INSERT INTO users(username, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
            (username, email, generate_password_hash(password)),
        )
        db.commit()
        print(f"Admin '{username}' creado.")
    except Exception:
        print("No se pudo crear: usuario o email ya en uso.")
        raise SystemExit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
