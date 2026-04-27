-- ============================================================
-- Migración 010 — AdamoServices Partner Manager
-- Descripción : Añade columna de texto `observaciones` a la
--               tabla agente_kpi_diario para registrar notas
--               de jornada y alimentar el análisis de IA.
-- Idempotente  : Uso de ADD COLUMN IF NOT EXISTS.
-- ============================================================

ALTER TABLE agente_kpi_diario
    ADD COLUMN IF NOT EXISTS observaciones TEXT;
