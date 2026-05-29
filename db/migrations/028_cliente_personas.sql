-- ============================================================
-- AdamoServices Partner Manager -- Migración 028
-- Descripción : Personas vinculadas a clientes (directores,
--               representantes legales y UBOs).
-- Idempotente : CREATE TABLE IF NOT EXISTS
-- ============================================================

CREATE TABLE IF NOT EXISTS cliente_personas (
    id                    SERIAL      PRIMARY KEY,
    cliente_id            INTEGER     NOT NULL
                              REFERENCES clientes(id) ON DELETE CASCADE,
    nombre_completo       TEXT        NOT NULL,
    tipo_documento        TEXT,
    numero_documento      TEXT,
    nacionalidad          TEXT        NOT NULL DEFAULT 'Colombia',
    rol                   TEXT        NOT NULL
                              CHECK (rol IN (
                                  'Representante Legal','Director','Accionista',
                                  'Beneficiario Final (UBO)','Apoderado','Otro'
                              )),
    pct_participacion     NUMERIC(5,2)
                              CHECK (pct_participacion >= 0 AND pct_participacion <= 100),
    es_pep                INTEGER     NOT NULL DEFAULT 0 CHECK (es_pep IN (0,1)),
    en_listas_restriccion INTEGER     NOT NULL DEFAULT 0 CHECK (en_listas_restriccion IN (0,1)),
    fecha_verificacion    DATE,
    activo                INTEGER     NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    notas                 TEXT,
    creado_por            TEXT        NOT NULL DEFAULT 'sistema',
    created_at            TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cliente_personas_cliente_id
    ON cliente_personas (cliente_id);
CREATE INDEX IF NOT EXISTS idx_cliente_personas_activo
    ON cliente_personas (activo);
CREATE INDEX IF NOT EXISTS idx_cliente_personas_es_pep
    ON cliente_personas (es_pep);

CREATE OR REPLACE FUNCTION fn_cliente_personas_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_cliente_personas_updated_at ON cliente_personas;
CREATE TRIGGER trg_cliente_personas_updated_at
    BEFORE UPDATE ON cliente_personas
    FOR EACH ROW EXECUTE FUNCTION fn_cliente_personas_updated_at();
