-- ============================================================
-- 022_weekly_monitoring_historial.sql
-- Monitoreo semanal: columna weekly_delta + tabla historial
-- ============================================================

-- 1. Columna para el resumen de cambios semanales
ALTER TABLE crypto_monitoreo
    ADD COLUMN IF NOT EXISTS weekly_delta TEXT;

-- 2. Tabla de snapshots históricos (una fila por ciclo de monitoreo)
CREATE TABLE IF NOT EXISTS crypto_monitoreo_historial (
    id                   SERIAL PRIMARY KEY,
    original_id          INTEGER NOT NULL,
    snapshot_date        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    wallet_address       TEXT NOT NULL,
    -- GL
    gl_score             INTEGER,
    riesgo_nivel         TEXT,
    -- SoF
    sof_indicador        TEXT,
    sof_cont_total       NUMERIC(10,4),
    sof_score            INTEGER,
    sof_nivel            TEXT,
    sof_monto            NUMERIC(18,2),
    -- UoF
    uof_indicador        TEXT,
    uof_cont_total       NUMERIC(10,4),
    uof_score            INTEGER,
    uof_nivel            TEXT,
    uof_monto            NUMERIC(18,2),
    -- Conclusión
    final_risk_score     NUMERIC(6,2),
    final_risk_level     TEXT,
    weekly_delta         TEXT,
    analyst_observations TEXT,
    monitoring_analyst   TEXT,
    registrado_por       TEXT,
    pdf_report_url       TEXT,
    total_exposure       NUMERIC(18,2),
    exposure_currency    TEXT
);

-- Índices para búsquedas frecuentes
CREATE INDEX IF NOT EXISTS idx_crypto_hist_wallet
    ON crypto_monitoreo_historial(wallet_address);

CREATE INDEX IF NOT EXISTS idx_crypto_hist_original
    ON crypto_monitoreo_historial(original_id);

CREATE INDEX IF NOT EXISTS idx_crypto_hist_date
    ON crypto_monitoreo_historial(snapshot_date DESC);
