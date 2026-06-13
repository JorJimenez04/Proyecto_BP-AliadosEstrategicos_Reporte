-- 033_optional_nit.sql
-- Hace el campo NIT opcional en la tabla aliados.
-- PostgreSQL permite múltiples NULL en columnas UNIQUE (NULL != NULL).

ALTER TABLE aliados ALTER COLUMN nit DROP NOT NULL;
