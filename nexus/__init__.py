"""Librería Nexus — factory Flask."""
from flask import Flask

from config import Config


def create_app(config_class=Config):
    app = Flask(__name__, template_folder="templates", static_folder="../static")
    app.config.from_object(config_class)

    from nexus.auth import bp as auth_bp
    from nexus.catalog import bp as catalog_bp
    from nexus.library import bp as library_bp
    from nexus.store import bp as store_bp
    from nexus.reader import bp as reader_bp
    from nexus.admin import bp as admin_bp

    for bp in (auth_bp, catalog_bp, library_bp, store_bp, reader_bp, admin_bp):
        app.register_blueprint(bp)

    @app.get("/salud")
    def salud():
        return {"app": "libreria-nexus", "estado": "ok"}

    return app
