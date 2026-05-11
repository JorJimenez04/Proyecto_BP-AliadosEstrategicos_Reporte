-- =============================================================
-- Migración 019: Módulo Cripto Compliance (VASP Monitor)
-- Registro de wallets, scores Global Ledger y alertas FATF.
-- Idempotente: CREATE TABLE IF NOT EXISTS / ADD COLUMN IF NOT EXISTS
-- =============================================================

-- ── Tabla principal de monitoreo ─────────────────────────────
CREATE TABLE IF NOT EXISTS crypto_monitoreo (
    -- Identificadores
    id                  SERIAL          PRIMARY KEY,
    wallet_address      TEXT            NOT NULL UNIQUE,
    blockchain          TEXT            NOT NULL DEFAULT 'ETH',

    -- Relación con cliente / aliado
    client_id           INTEGER         REFERENCES aliados(id) ON DELETE SET NULL,
    client_nombre       TEXT,                       -- desnormalizado para reportes offline

    -- Score Global Ledger (0–100; mayor = más limpio)
    gl_score            INTEGER         CHECK (gl_score BETWEEN 0 AND 100),
    riesgo_nivel        TEXT            NOT NULL DEFAULT 'Sin Datos'
                        CHECK (riesgo_nivel IN ('Crítico','Alto','Medio','Bajo','Sin Datos')),

    -- Alertas / Labels de Global Ledger (array de objetos JSON)
    -- Ej: [{"label": "Sanctioned Exchange", "exposure_pct": 12.5, "source": "OFAC"}]
    risk_labels         JSONB           NOT NULL DEFAULT '[]',

    -- Exposición financiera
    total_exposure      NUMERIC(20,2)   DEFAULT 0.00,   -- USD
    exposure_currency   TEXT            DEFAULT 'USD',

    -- Reporte adjunto
    pdf_report_url      TEXT,                           -- URL o ruta al PDF de Global Ledger

    -- Metadatos de auditoría
    last_report_date    TIMESTAMP WITH TIME ZONE,
    registrado_por      TEXT,
    notas               TEXT,

    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ── Índices ───────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_crypto_client_id
    ON crypto_monitoreo (client_id);

CREATE INDEX IF NOT EXISTS idx_crypto_riesgo_nivel
    ON crypto_monitoreo (riesgo_nivel);

CREATE INDEX IF NOT EXISTS idx_crypto_gl_score
    ON crypto_monitoreo (gl_score);

-- Índice GIN para búsquedas dentro de risk_labels JSONB
CREATE INDEX IF NOT EXISTS idx_crypto_risk_labels
    ON crypto_monitoreo USING GIN (risk_labels);

-- ── Función + Trigger para updated_at automático ──────────────
CREATE OR REPLACE FUNCTION fn_update_crypto_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_crypto_updated_at ON crypto_monitoreo;
CREATE TRIGGER trg_crypto_updated_at
    BEFORE UPDATE ON crypto_monitoreo
    FOR EACH ROW EXECUTE FUNCTION fn_update_crypto_updated_at();

-- ── Comentarios de columnas ───────────────────────────────────
COMMENT ON TABLE  crypto_monitoreo IS
    'Registro de wallets monitoreadas por Global Ledger. Cumplimiento VASP/FATF.';
COMMENT ON COLUMN crypto_monitoreo.gl_score IS
    'Score de riesgo Global Ledger 0-100. >70=Bajo, 40-70=Medio, 20-40=Alto, <20=Crítico';
COMMENT ON COLUMN crypto_monitoreo.risk_labels IS
    'Array JSON de alertas GL: [{label, exposure_pct, source}]';
COMMENT ON COLUMN crypto_monitoreo.total_exposure IS
    'Exposición total en USD calculada por Global Ledger';
COMMENT ON COLUMN crypto_monitoreo.pdf_report_url IS
    'URL del reporte PDF generado por Global Ledger para esta wallet';
