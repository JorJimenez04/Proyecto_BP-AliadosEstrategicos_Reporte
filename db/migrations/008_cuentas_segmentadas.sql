-- ============================================================
-- Migración 008 — AdamoServices Partner Manager
-- Descripción : Segmentación de cuentas por estado:
--               aprobadas, rechazadas y bajo investigación,
--               separadas entre tipo personal y comercial.
-- Reemplaza   : kpi_cuentas_pers_activas / kpi_cuentas_com_activas
--               (se conservan por retrocompatibilidad).
-- Idempotente : Uso de ADD COLUMN IF NOT EXISTS.
-- ============================================================

ALTER TABLE agentes
    ADD COLUMN IF NOT EXISTS kpi_cuentas_pers_aprobadas     INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS kpi_cuentas_pers_rechazadas    INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS kpi_cuentas_pers_investigacion INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS kpi_cuentas_com_aprobadas      INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS kpi_cuentas_com_rechazadas     INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS kpi_cuentas_com_investigacion  INTEGER NOT NULL DEFAULT 0;
