-- ============================================================
-- Migración 006 — AdamoServices Partner Manager
-- Descripción : Añade columnas de métricas manuales (KPIs) a la
--               tabla agentes para soporte de edición inline y
--               carga masiva por parte del equipo de Compliance.
-- Idempotente  : Usa ADD COLUMN IF NOT EXISTS — seguro para
--               ejecutar múltiples veces.
-- ============================================================

ALTER TABLE agentes
    ADD COLUMN IF NOT EXISTS kpi_docs_personales      INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS kpi_docs_comerciales     INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS kpi_cuentas_pers_activas INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS kpi_cuentas_com_activas  INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS kpi_sanciones_revisadas  INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS kpi_alertas_hardstop     INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS kpi_tx_ongoing           INTEGER NOT NULL DEFAULT 0;

COMMENT ON COLUMN agentes.kpi_docs_personales      IS 'KPI: contratos firmados — tipo personal';
COMMENT ON COLUMN agentes.kpi_docs_comerciales     IS 'KPI: contratos firmados — tipo comercial';
COMMENT ON COLUMN agentes.kpi_cuentas_pers_activas IS 'KPI: partners personales en estado Activo';
COMMENT ON COLUMN agentes.kpi_cuentas_com_activas  IS 'KPI: partners comerciales en estado Activo';
COMMENT ON COLUMN agentes.kpi_sanciones_revisadas  IS 'KPI: registros con listas de sanciones verificadas';
COMMENT ON COLUMN agentes.kpi_alertas_hardstop     IS 'KPI: alertas SARLAFT resueltas (hardstop)';
COMMENT ON COLUMN agentes.kpi_tx_ongoing           IS 'KPI: transacciones ongoing con due-diligence completado';
