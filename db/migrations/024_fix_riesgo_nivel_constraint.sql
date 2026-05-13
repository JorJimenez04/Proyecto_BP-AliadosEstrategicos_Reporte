-- =============================================================
-- Migración 023: Corregir CHECK constraint en crypto_monitoreo.riesgo_nivel
-- Añade 'Crítico' y 'Sin Datos' a los valores permitidos.
-- Idempotente vía DROP CONSTRAINT IF EXISTS.
-- =============================================================

ALTER TABLE crypto_monitoreo
    DROP CONSTRAINT IF EXISTS crypto_monitoreo_riesgo_nivel_check;

ALTER TABLE crypto_monitoreo
    ADD CONSTRAINT crypto_monitoreo_riesgo_nivel_check
    CHECK (riesgo_nivel IN ('Bajo', 'Medio', 'Alto', 'Crítico', 'Sin Datos'));
