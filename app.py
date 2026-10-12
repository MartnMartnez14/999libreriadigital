"""Punto de entrada Librería Nexus (solo local)."""
from nexus import create_app
from nexus.database import init_db
from config import Config

app = create_app()

if __name__ == "__main__":
    init_db(Config.DATABASE_PATH)
    app.run(host="127.0.0.1", port=5000, debug=False)
