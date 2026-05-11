-- ============================================================
-- Migración 021: Campos SoF / UoF (Metodología Excel AdamoServices)
-- Tabla: crypto_monitoreo
-- Descripción: Agrega los campos de análisis Source of Funds y
--              Use of Funds alineados con la hoja "Wallets Monitoring
--              Clients" del Excel de monitoreo AdamoServices.
-- ============================================================

-- ── Source of Funds (SoF) ────────────────────────────────────
ALTER TABLE crypto_monitoreo
    ADD COLUMN IF NOT EXISTS sof_tipo_riesgo       TEXT,
    ADD COLUMN IF NOT EXISTS sof_indicador         TEXT,
    ADD COLUMN IF NOT EXISTS sof_naturaleza        TEXT,
    ADD COLUMN IF NOT EXISTS sof_profundidad       INTEGER,
    ADD COLUMN IF NOT EXISTS sof_cont_directa      NUMERIC(8,4),
    ADD COLUMN IF NOT EXISTS sof_cont_indirecta    NUMERIC(8,4),
    ADD COLUMN IF NOT EXISTS sof_cont_total        NUMERIC(8,4),
    ADD COLUMN IF NOT EXISTS sof_score             INTEGER,
    ADD COLUMN IF NOT EXISTS sof_nivel             TEXT,
    ADD COLUMN IF NOT EXISTS sof_monto             NUMERIC(20,2);

-- ── Use of Funds (UoF) ───────────────────────────────────────
ALTER TABLE crypto_monitoreo
    ADD COLUMN IF NOT EXISTS uof_indicador         TEXT,
    ADD COLUMN IF NOT EXISTS uof_naturaleza        TEXT,
    ADD COLUMN IF NOT EXISTS uof_profundidad       INTEGER,
    ADD COLUMN IF NOT EXISTS uof_cont_directa      NUMERIC(8,4),
    ADD COLUMN IF NOT EXISTS uof_cont_indirecta    NUMERIC(8,4),
    ADD COLUMN IF NOT EXISTS uof_cont_total        NUMERIC(8,4),
    ADD COLUMN IF NOT EXISTS uof_score             INTEGER,
    ADD COLUMN IF NOT EXISTS uof_nivel             TEXT,
    ADD COLUMN IF NOT EXISTS uof_monto             NUMERIC(20,2);

-- ── Conclusión / Resumen de Monitoreo ────────────────────────
ALTER TABLE crypto_monitoreo
    ADD COLUMN IF NOT EXISTS analyst_observations  TEXT,
    ADD COLUMN IF NOT EXISTS monitoring_analyst    TEXT,
    ADD COLUMN IF NOT EXISTS final_risk_score      NUMERIC(6,2),
    ADD COLUMN IF NOT EXISTS final_risk_level      TEXT,
    ADD COLUMN IF NOT EXISTS wallet_status         TEXT DEFAULT 'Active';

-- ── Índices de búsqueda ──────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_crypto_mon_sof_nivel
    ON crypto_monitoreo (sof_nivel);
CREATE INDEX IF NOT EXISTS idx_crypto_mon_uof_nivel
    ON crypto_monitoreo (uof_nivel);
CREATE INDEX IF NOT EXISTS idx_crypto_mon_final_level
    ON crypto_monitoreo (final_risk_level);
CREATE INDEX IF NOT EXISTS idx_crypto_mon_monitoring_analyst
    ON crypto_monitoreo (monitoring_analyst);
