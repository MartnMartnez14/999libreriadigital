# Despliegue online (gratis) — Librería Bluffer

> Guía prevista para publicar la app Flask + SQLite.
> **GitHub Pages no sirve** para ejecutar Flask (solo hosting estático).
> Opción recomendada gratis: **PythonAnywhere**. Alternativas: Render, Railway.

Última actualización: 2026-10-11

---

## 0. Requisitos previos
- Cuenta GitHub (repo **privado**).
- Cuenta gratuita en PythonAnywhere.

## 1. Repositorio
- Crear repo privado y subir el proyecto.
- Asegurar que **no** se suben: `.env`, `instance/*.db`, `protected_books/`, `.venv/`
  (ya están en `.gitignore`).

## 2. PythonAnywhere
- Subir código (git clone o ZIP) al home.
- Crear virtualenv e instalar `requirements.txt`.
- Crear Web App tipo **Manual configuration (Python 3.12)** apuntando a `app.py`.
- Configurar WSGI para importar `create_app()`.
- Definir variables de entorno: `SECRET_KEY`, `DATABASE_PATH`, `BOOKS_DIR`.

## 3. Base de datos en producción
- Inicializar: `python -c "from nexus.database import init_db; from config import Config; init_db(Config.DATABASE_PATH)"`.
- Crear el primer admin: `python scripts/create_admin.py USUARIO CONTRASEÑA`.
- Cargar catálogo real desde el panel de Admin.

## 4. Seguridad antes de publicar
- [ ] CSRF en formularios de Admin.
- [ ] `SECRET_KEY` robusta por entorno (nunca en el repo).
- [ ] `debug=False`.
- [ ] Cookies `Secure` + HTTPS (PythonAnywhere da HTTPS por defecto).

## 5. Backups
- Copiar periódicamente `instance/libreria.db`.
- En local: `cp instance/libreria.db backups/libreria-$(date +%F).db`.

## 6. Dominio propio (fase posterior)
- Comprar dominio y enlazarlo al host (o usar un proxy/CDN con HTTPS).
