-- Géneros base Librería Bluffer (idempotente).
INSERT OR IGNORE INTO genres(name, slug) VALUES
  ('Autoayuda', 'autoayuda'),
  ('Biografía', 'biografia'),
  ('Ciencia ficción y fantasía', 'ciencia-ficcion-y-fantasia'),
  ('Literatura', 'literatura'),
  ('Historia', 'historia'),
  ('Misterio y thriller', 'misterio-y-thriller'),
  ('Familia', 'familia'),
  ('No ficción', 'no-ficcion'),
  ('Ciencias', 'ciencias'),
  ('Cocina', 'cocina'),
  ('Filosofía', 'filosofia'),
  ('Relaciones', 'relaciones'),
  ('Romance', 'romance'),
  ('Terror', 'terror');
INSERT OR IGNORE INTO schema_version(version, description) VALUES (3, 'generos base bluffer');
