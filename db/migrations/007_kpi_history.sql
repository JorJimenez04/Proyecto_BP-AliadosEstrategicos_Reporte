-- ============================================================
-- Migración 007 — AdamoServices Partner Manager
-- Descripción : Tabla de historial diario de KPIs por agente.
--               Permite registrar una entrada por colaborador
--               por día y consultar totales acumulados históricos.
-- Idempotente  : Uso de CREATE TABLE IF NOT EXISTS.
-- ============================================================

-- ─────────────────────────────────────────────────────────────
-- TABLA: agente_kpi_diario
-- Una fila por (agente_id, fecha). El índice UNIQUE garantiza
-- que un colaborador no tenga más de un registro por día.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agente_kpi_diario (
    id              SERIAL      PRIMARY KEY,
    agente_id       INTEGER     NOT NULL
                    REFERENCES agentes(id) ON DELETE CASCADE,
    fecha           DATE        NOT NULL DEFAULT CURRENT_DATE,
    docs_personales  INTEGER    NOT NULL DEFAULT 0 CHECK (docs_personales  >= 0),
    docs_comerciales INTEGER    NOT NULL DEFAULT 0 CHECK (docs_comerciales >= 0),
    sanciones        INTEGER    NOT NULL DEFAULT 0 CHECK (sanciones        >= 0),
    hardstop         INTEGER    NOT NULL DEFAULT 0 CHECK (hardstop         >= 0),
    tx_ongoing       INTEGER    NOT NULL DEFAULT 0 CHECK (tx_ongoing       >= 0),
    created_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Garantiza una sola entrada por agente por día
CREATE UNIQUE INDEX IF NOT EXISTS uix_agente_kpi_diario_agente_fecha
    ON agente_kpi_diario (agente_id, fecha);

-- Índice de ordenamiento para consultas por agente
CREATE INDEX IF NOT EXISTS idx_agente_kpi_diario_agente_id
    ON agente_kpi_diario (agente_id, fecha DESC);

-- Trigger para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION fn_agente_kpi_diario_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_agente_kpi_diario_updated_at ON agente_kpi_diario;
CREATE TRIGGER trg_agente_kpi_diario_updated_at
    BEFORE UPDATE ON agente_kpi_diario
    FOR EACH ROW EXECUTE FUNCTION fn_agente_kpi_diario_updated_at();
