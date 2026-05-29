-- ============================================================
-- AdamoServices Partner Manager -- Migración 030
-- Descripción : Servicios activos por contrato.
--               UNIQUE (contrato_id, servicio): un registro
--               por servicio por contrato.
-- Idempotente : CREATE TABLE IF NOT EXISTS
-- ============================================================

CREATE TABLE IF NOT EXISTS contrato_servicios (
    id                SERIAL      PRIMARY KEY,
    contrato_id       INTEGER     NOT NULL
                          REFERENCES cliente_contratos(id) ON DELETE CASCADE,
    servicio          TEXT        NOT NULL
                          CHECK (servicio IN (
                              'Dispersión','Monetización',
                              'Monitoreo de Transacciones','Compliance 360'
                          )),
    estado            TEXT        NOT NULL DEFAULT 'Activo'
                          CHECK (estado IN ('Activo','Suspendido','Terminado')),
    fecha_activacion  DATE,
    fecha_terminacion DATE,
    notas             TEXT,
    creado_por        TEXT        NOT NULL DEFAULT 'sistema',
    created_at        TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (contrato_id, servicio)
);

CREATE INDEX IF NOT EXISTS idx_contrato_servicios_contrato_id
    ON contrato_servicios (contrato_id);
CREATE INDEX IF NOT EXISTS idx_contrato_servicios_estado
    ON contrato_servicios (estado);

CREATE OR REPLACE FUNCTION fn_contrato_servicios_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_contrato_servicios_updated_at ON contrato_servicios;
CREATE TRIGGER trg_contrato_servicios_updated_at
    BEFORE UPDATE ON contrato_servicios
    FOR EACH ROW EXECUTE FUNCTION fn_contrato_servicios_updated_at();
