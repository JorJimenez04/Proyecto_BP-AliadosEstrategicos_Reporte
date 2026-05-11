-- =============================================================
-- Migracion 019: Modulo Cripto Compliance (VASP Monitor)
-- Idempotente: CREATE TABLE IF NOT EXISTS
-- NOTA: CHECK constraint en riesgo_nivel omitido para evitar
--       problemas de encoding UTF-8. Validacion en Pydantic.
-- =============================================================

CREATE TABLE IF NOT EXISTS crypto_monitoreo (
    id                  SERIAL          PRIMARY KEY,
    wallet_address      TEXT            NOT NULL UNIQUE,
    blockchain          TEXT            NOT NULL DEFAULT 'ETH',
    client_id           INTEGER         REFERENCES aliados(id) ON DELETE SET NULL,
    client_nombre       TEXT,
    gl_score            INTEGER         CHECK (gl_score BETWEEN 0 AND 100),
    riesgo_nivel        TEXT            NOT NULL DEFAULT 'Sin Datos',
    risk_labels         JSONB           NOT NULL DEFAULT '[]',
    total_exposure      NUMERIC(20,2)   DEFAULT 0.00,
    exposure_currency   TEXT            DEFAULT 'USD',
    pdf_report_url      TEXT,
    last_report_date    TIMESTAMP WITH TIME ZONE,
    registrado_por      TEXT,
    notas               TEXT,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crypto_client_id ON crypto_monitoreo (client_id);
CREATE INDEX IF NOT EXISTS idx_crypto_riesgo_nivel ON crypto_monitoreo (riesgo_nivel);
CREATE INDEX IF NOT EXISTS idx_crypto_gl_score ON crypto_monitoreo (gl_score);
CREATE INDEX IF NOT EXISTS idx_crypto_risk_labels ON crypto_monitoreo USING GIN (risk_labels);

CREATE OR REPLACE FUNCTION fn_update_crypto_updated_at()
RETURNS TRIGGER AS main
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
main LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_crypto_updated_at ON crypto_monitoreo;
CREATE TRIGGER trg_crypto_updated_at
    BEFORE UPDATE ON crypto_monitoreo
    FOR EACH ROW EXECUTE FUNCTION fn_update_crypto_updated_at();
