-- =============================================================
-- Migracion 020: Tabla de Clientes Corporativos Cripto
-- Crea crypto_clientes y vincula crypto_monitoreo via FK.
-- Idempotente: CREATE TABLE IF NOT EXISTS / ADD COLUMN IF NOT EXISTS
-- =============================================================

CREATE TABLE IF NOT EXISTS crypto_clientes (
    id                   SERIAL          PRIMARY KEY,
    razon_social         TEXT            NOT NULL,
    nit                  TEXT            UNIQUE,
    representante_legal  TEXT,
    correo_corporativo   TEXT,
    telefono             TEXT,
    direccion            TEXT,
    fecha_onboarding     DATE,
    notas                TEXT,
    creado_por           TEXT,
    created_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crypto_clientes_nit
    ON crypto_clientes (nit);

CREATE INDEX IF NOT EXISTS idx_crypto_clientes_razon_social
    ON crypto_clientes (razon_social);

-- Vincular crypto_monitoreo a crypto_clientes (nueva FK, ademas de la FK a aliados)
ALTER TABLE crypto_monitoreo
    ADD COLUMN IF NOT EXISTS crypto_cliente_id INTEGER
        REFERENCES crypto_clientes(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_crypto_monitoreo_crypto_cliente_id
    ON crypto_monitoreo (crypto_cliente_id);

-- Trigger updated_at para crypto_clientes
CREATE OR REPLACE FUNCTION fn_update_crypto_clientes_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_crypto_clientes_updated_at ON crypto_clientes;
CREATE TRIGGER trg_crypto_clientes_updated_at
    BEFORE UPDATE ON crypto_clientes
    FOR EACH ROW EXECUTE FUNCTION fn_update_crypto_clientes_updated_at();
