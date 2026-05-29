-- 026_email_casos.sql
-- Bandeja de Cumplimiento — tabla de casos de correo electrónico
-- Idempotente: CREATE TABLE IF NOT EXISTS

CREATE TABLE IF NOT EXISTS email_casos (
    id                  SERIAL PRIMARY KEY,
    empresa             TEXT NOT NULL
                            CHECK (empresa IN ('Holdings BPO', 'Adamo Services', 'Paycop')),
    "buzón"             TEXT NOT NULL
                            CHECK ("buzón" IN (
                                'compliance@holdingsbpo.com',
                                'compliance@adamoservices.co',
                                'compliance@paycop.co'
                            )),
    remitente           TEXT NOT NULL,
    asunto              TEXT NOT NULL,
    cuerpo              TEXT,
    fecha_recepcion     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    message_id_externo  TEXT UNIQUE,
    estado              TEXT NOT NULL DEFAULT 'Nuevo'
                            CHECK (estado IN ('Nuevo', 'En gestión', 'Resuelto', 'Escalado')),
    prioridad           TEXT NOT NULL DEFAULT 'Normal'
                            CHECK (prioridad IN ('Alta', 'Normal', 'Baja')),
    notas_internas      TEXT,
    atendido_por        TEXT,
    fecha_resolucion    TIMESTAMPTZ,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_casos_empresa
    ON email_casos (empresa);

CREATE INDEX IF NOT EXISTS idx_email_casos_estado
    ON email_casos (estado);

CREATE INDEX IF NOT EXISTS idx_email_casos_prioridad
    ON email_casos (prioridad);

CREATE INDEX IF NOT EXISTS idx_email_casos_fecha
    ON email_casos (fecha_recepcion DESC);

CREATE OR REPLACE FUNCTION _trg_email_casos_updated()
RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_en = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_email_casos_updated_at ON email_casos;
CREATE TRIGGER trg_email_casos_updated_at
    BEFORE UPDATE ON email_casos
    FOR EACH ROW EXECUTE FUNCTION _trg_email_casos_updated();
