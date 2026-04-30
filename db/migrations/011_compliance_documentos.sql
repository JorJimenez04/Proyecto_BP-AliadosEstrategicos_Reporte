-- ============================================================
-- AdamoServices Partner Manager -- Migracion 011
-- Descripcion : Tabla compliance_documentos para el modulo
--               "Centro Documental de Cumplimiento".
-- Idempotente : CREATE TABLE IF NOT EXISTS
-- ============================================================

CREATE TABLE IF NOT EXISTS compliance_documentos (
    id              SERIAL      PRIMARY KEY,
    carpeta         TEXT        NOT NULL
                    CHECK (carpeta IN (
                        'Politicas','Manuales','Onboarding',
                        'Procesos y Procedimientos','Riesgos','Empresariales','Capacitacion'
                    )),
    codigo          TEXT        NOT NULL,
    nombre          TEXT        NOT NULL,
    descripcion     TEXT,
    version         TEXT        NOT NULL DEFAULT '1.0',
    estado          TEXT        NOT NULL DEFAULT 'Vigente'
                    CHECK (estado IN ('Vigente','Pendiente','Vencido','Archivado')),
    formato         TEXT        NOT NULL DEFAULT 'PDF'
                    CHECK (formato IN ('PDF','DOCX','XLSX','PPTX','OTRO')),
    url_documento   TEXT,
    fecha_emision   DATE        NOT NULL DEFAULT CURRENT_DATE,
    fecha_vencimiento DATE,
    creado_por      TEXT        NOT NULL DEFAULT 'sistema',
    actualizado_por TEXT,
    created_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_compliance_docs_carpeta ON compliance_documentos (carpeta);
CREATE INDEX IF NOT EXISTS idx_compliance_docs_estado  ON compliance_documentos (estado);
CREATE INDEX IF NOT EXISTS idx_compliance_docs_codigo  ON compliance_documentos (codigo);

CREATE OR REPLACE FUNCTION fn_compliance_docs_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_compliance_docs_updated_at ON compliance_documentos;
CREATE TRIGGER trg_compliance_docs_updated_at
    BEFORE UPDATE ON compliance_documentos
    FOR EACH ROW EXECUTE FUNCTION fn_compliance_docs_updated_at();

-- Seed removido: los INSERTs se movieron fuera de la migración para evitar
-- duplicados en cada re-ejecución de sync_db.py (que no tiene tracking).
-- La carga de documentos se realiza de forma manual desde la UI del Centro Documental.
