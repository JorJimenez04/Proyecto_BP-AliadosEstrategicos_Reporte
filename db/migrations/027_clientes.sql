-- ============================================================
-- AdamoServices Partner Manager -- Migración 027
-- Descripción : Tabla maestra de clientes con ficha KYC/SARLAFT.
-- Idempotente : CREATE TABLE IF NOT EXISTS
-- ============================================================

CREATE TABLE IF NOT EXISTS clientes (
    id                        SERIAL      PRIMARY KEY,
    razon_social              TEXT        NOT NULL,
    nit                       TEXT        NOT NULL UNIQUE,
    tipo_sociedad             TEXT,
    fecha_constitucion        DATE,
    pais_constitucion         TEXT        NOT NULL DEFAULT 'Colombia',
    sector_ciiu               TEXT,
    sitio_web                 TEXT,
    direccion                 TEXT,
    nivel_riesgo              TEXT        NOT NULL DEFAULT 'Sin calificar'
                                  CHECK (nivel_riesgo IN (
                                      'Sin calificar','Bajo','Medio','Alto','Muy Alto'
                                  )),
    puntaje_riesgo            INTEGER     CHECK (puntaje_riesgo >= 0 AND puntaje_riesgo <= 100),
    fecha_ultima_calificacion DATE,
    proxima_revision          DATE,
    es_pep                    INTEGER     NOT NULL DEFAULT 0 CHECK (es_pep IN (0,1)),
    exposicion_cripto         INTEGER     NOT NULL DEFAULT 0 CHECK (exposicion_cripto IN (0,1)),
    crypto_friendly           INTEGER     NOT NULL DEFAULT 0 CHECK (crypto_friendly IN (0,1)),
    listas_verificadas        INTEGER     NOT NULL DEFAULT 0 CHECK (listas_verificadas IN (0,1)),
    fecha_verificacion_listas DATE,
    en_listas_restriccion     INTEGER     NOT NULL DEFAULT 0 CHECK (en_listas_restriccion IN (0,1)),
    jurisdicciones            TEXT[]      NOT NULL DEFAULT '{}',
    estado                    TEXT        NOT NULL DEFAULT 'Prospecto'
                                  CHECK (estado IN (
                                      'Prospecto','Activo','Suspendido','Terminado'
                                  )),
    notas                     TEXT,
    creado_por                TEXT        NOT NULL DEFAULT 'sistema',
    created_at                TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_clientes_estado
    ON clientes (estado);
CREATE INDEX IF NOT EXISTS idx_clientes_nivel_riesgo
    ON clientes (nivel_riesgo);
CREATE INDEX IF NOT EXISTS idx_clientes_nit
    ON clientes (nit);
CREATE INDEX IF NOT EXISTS idx_clientes_proxima_revision
    ON clientes (proxima_revision);
CREATE INDEX IF NOT EXISTS idx_clientes_en_listas
    ON clientes (en_listas_restriccion);

CREATE OR REPLACE FUNCTION fn_clientes_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_clientes_updated_at ON clientes;
CREATE TRIGGER trg_clientes_updated_at
    BEFORE UPDATE ON clientes
    FOR EACH ROW EXECUTE FUNCTION fn_clientes_updated_at();
