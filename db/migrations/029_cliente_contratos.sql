-- ============================================================
-- AdamoServices Partner Manager -- Migración 029
-- Descripción : Contratos entre clientes y las 3 empresas del
--               grupo (Holdings BPO, Adamo Services, Paycop).
--               UNIQUE (cliente_id, empresa_grupo): un contrato
--               por empresa — actualizar si cambia de estado.
-- Idempotente : CREATE TABLE IF NOT EXISTS
-- ============================================================

CREATE TABLE IF NOT EXISTS cliente_contratos (
    id                      SERIAL      PRIMARY KEY,
    cliente_id              INTEGER     NOT NULL
                                REFERENCES clientes(id) ON DELETE CASCADE,
    empresa_grupo           TEXT        NOT NULL
                                CHECK (empresa_grupo IN (
                                    'Holdings BPO','Adamo Services','Paycop'
                                )),
    estado                  TEXT        NOT NULL DEFAULT 'Prospecto'
                                CHECK (estado IN (
                                    'Prospecto','Activo','Suspendido','Terminado'
                                )),
    fecha_inicio            DATE,
    fecha_vencimiento       DATE,
    contrato_firmado        INTEGER     NOT NULL DEFAULT 0 CHECK (contrato_firmado IN (0,1)),
    fecha_firma             DATE,
    numero_contrato         TEXT,
    contacto_operativo      TEXT,
    email_operativo         TEXT,
    telefono_operativo      TEXT,
    contacto_compliance     TEXT,
    email_compliance        TEXT,
    sla_contratado          TEXT,
    volumen_mensual_cop     BIGINT,
    num_transacciones_mes   INTEGER,
    fuente_volumen          TEXT        NOT NULL DEFAULT 'manual'
                                CHECK (fuente_volumen IN ('manual','adamo_pay')),
    fecha_ultimo_volumen    DATE,
    notas                   TEXT,
    creado_por              TEXT        NOT NULL DEFAULT 'sistema',
    created_at              TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (cliente_id, empresa_grupo)
);

CREATE INDEX IF NOT EXISTS idx_cliente_contratos_cliente_id
    ON cliente_contratos (cliente_id);
CREATE INDEX IF NOT EXISTS idx_cliente_contratos_empresa_grupo
    ON cliente_contratos (empresa_grupo);
CREATE INDEX IF NOT EXISTS idx_cliente_contratos_estado
    ON cliente_contratos (estado);
CREATE INDEX IF NOT EXISTS idx_cliente_contratos_vencimiento
    ON cliente_contratos (fecha_vencimiento);

CREATE OR REPLACE FUNCTION fn_cliente_contratos_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_cliente_contratos_updated_at ON cliente_contratos;
CREATE TRIGGER trg_cliente_contratos_updated_at
    BEFORE UPDATE ON cliente_contratos
    FOR EACH ROW EXECUTE FUNCTION fn_cliente_contratos_updated_at();
