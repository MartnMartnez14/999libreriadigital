# Roadmap — Librería Bluffer

> Librería digital de afiliados: el usuario explora una grilla de libros y al
> hacer clic en la portada va al link de afiliado (compra externa).
> Estado actual: **v1 offline funcional** (catálogo, favoritos, admin, rediseño visual).

Última actualización: 2026-10-11

---

## 1. Afiliados (inmediato)

- [ ] Investigar y elegir programas de afiliados:
  - Amazon Afiliados (ES), Awin, Casa del Libro, Fnac, etc.
  - Revisar requisitos de alta, % de comisión y si admiten libros digitales.
- [ ] Definir el formato del link con tag propio.
- [ ] Poblar por libro: `external_url` (link con tag) y `affiliate_source` (red).
- [ ] (Opcional futuro) Registrar clics salientes para medir rendimiento, sin datos personales.

> Nota legal: marcar los enlaces como afiliado (`rel="sponsored nofollow noopener"`).
> El aviso ya se muestra en el footer.

## 2. Base de datos real (inmediato)

- [ ] Cargar catálogo real: título, autor, editorial, año, género, portada y link de afiliado.
- [ ] Revisar duplicados (ISBN) al cargar.
- [ ] Definir rutina de backup de `instance/libreria.db` (ver `roadmap/DEPLOY.md`).

## 3. Publicación online gratis (corto plazo)

- [ ] **Aviso clave:** GitHub Pages **no ejecuta Flask** (solo estático).
      Para esta app (Flask + SQLite) usar **PythonAnywhere** (ideal), Render o Railway free.
- [ ] Repositorio GitHub **privado** de momento.
- [ ] Deploy en PythonAnywhere (paso a paso en `roadmap/DEPLOY.md`).
- [ ] Endurecer seguridad antes de publicar:
  - [ ] CSRF en formularios de Admin (pendiente).
  - [ ] `SECRET_KEY` real vía variable de entorno.
  - [ ] `debug=False`, cookies `Secure` bajo HTTPS.

## 4. Dominio propio (medio plazo)

- [ ] Comprar dominio + HTTPS.
- [ ] Evaluar concurrencia de SQLite; migrar a Postgres si hace falta.

## 5. Visibilidad (medio plazo)

- [ ] Difusión en redes sociales propias.
- [ ] Publicidad barata (Meta / Google) para atraer clientes.

## 6. Pendientes técnicos v1

- [ ] CSRF en Admin.
- [ ] README + procedimiento de respaldo.
- [ ] Tests finales (`tests/`, unittest).

---

## Estado funcional hoy

- Catálogo con búsqueda (LIKE), filtros (género, idioma), orden (novedad, título, año) y paginación.
- Géneros como chips de colores, hero con buscador.
- Ficha de libro a dos columnas, relacionados por género/autor.
- Usuarios locales (registro/login), favoritos con corazón y estado visual.
- Admin: CRUD de libros (portada, link de afiliado, autor, género, editorial),
  autores, editoriales, géneros, activar/desactivar.
- Temas claro/oscuro/sistema, responsive, accesibilidad básica.
- **Fuera de alcance v1:** carrito, pagos, lector, EPUB (descartados por el modelo de afiliados).
