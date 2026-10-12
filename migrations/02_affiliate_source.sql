-- Migración 02: columna NULLABLE affiliate_source en books + versión 2
ALTER TABLE books ADD COLUMN affiliate_source TEXT;
INSERT OR REPLACE INTO schema_version(version, description) VALUES (2, 'affiliate_source nullable');
