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
                        'Etica','Riesgos','Empresariales','Capacitacion'
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

-- Seed: 39 documentos reales de ADAMO
INSERT INTO compliance_documentos (carpeta,codigo,nombre,formato,version,estado,fecha_emision,descripcion) VALUES
('Politicas','POL-001','Politica AML-SARO v1.0','DOCX','1.0','Vigente','2024-06-01','Version editable vigente'),
('Politicas','POL-001','Politica AML-SARO Firmada','PDF','1.0','Vigente','2024-06-01','Documento firmado'),
('Politicas','POL-002','Politica Manejo de Informacion v1.0','DOCX','1.0','Vigente','2024-06-01','Version editable'),
('Politicas','POL-002','Politica Manejo Informacion Firmada','PDF','1.0','Vigente','2024-06-01','Firmada'),
('Politicas','POL-003','Politica PEPs v1.0','DOCX','1.0','Vigente','2024-06-01','Version editable'),
('Politicas','POL-003','Politica PEPs Firmada','PDF','1.0','Vigente','2024-06-01','Firmada'),
('Manuales','MAN-001','Manual SAGRILAFT Borrador','DOCX','1.0','Vigente','2024-06-01','Borrador editable'),
('Manuales','MAN-001','Manual SAGRILAFT Firmado','PDF','1.0','Vigente','2024-06-01','Version firmada'),
('Manuales','MAN-002','Manual PTEE Cumplimiento Borrador','DOCX','1.0','Vigente','2024-06-01','Borrador editable'),
('Manuales','MAN-002','Manual PTEE Firmado','PDF','1.0','Vigente','2024-06-01','Firmado'),
('Manuales','MAN-003','Manual Procedimientos de Pagos','DOCX','1.0','Pendiente','2024-03-01','Requiere revision'),
('Manuales','MAN-004','Proceso Compliance v1.0','DOCX','1.0','Vigente','2024-06-01',NULL),
('Manuales','MAN-005','ROS Interno','DOCX','1.0','Vigente','2024-06-01',NULL),
('Manuales','MAN-006','Flujo Compliance Firmado','PDF','1.0','Vigente','2024-06-01',NULL),
('Onboarding','ONB-001','Onboarding Procedure EN','PDF','1.07','Vigente','2024-06-01','Version en ingles'),
('Onboarding','ONB-002','Proceso Vinculacion ES','PDF','1.07','Vigente','2024-06-01','Version en espanol'),
('Onboarding','ONB-003','Flujo Nuevos Clientes Firmado','PDF','1.0','Vigente','2024-06-01',NULL),
('Onboarding','ONB-004','Alertas Monitoreo Transacciones','DOCX','1.0','Vigente','2024-06-01',NULL),
('Onboarding','ONB-005','Documentos Soporte Compliance Request','DOCX','1.0','Vigente','2024-06-01','Checklist'),
('Etica','ETI-001','Codigo de Etica y Conducta Borrador','DOCX','1.0','Vigente','2024-06-01',NULL),
('Etica','ETI-001','Codigo de Etica y Conducta Firmado','PDF','1.0','Vigente','2024-06-01','Firmado'),
('Etica','ETI-002','Programa Transparencia Etica Publica 2024','DOCX','2024','Vigente','2024-01-01','PTEE anual'),
('Etica','ETI-003','PTEE Firmado','PDF','2024','Vigente','2024-01-01','Firmado'),
('Riesgos','RIE-001','Matriz de Riesgos 2022','XLSX','2022','Vencido','2022-06-01','Actualizar a version 2025'),
('Riesgos','RIE-002','ADAMO RISK Documento','DOCX','1.0','Vigente','2025-01-01',NULL),
('Riesgos','RIE-003','Politica AML-SARO v1.6 (Adamo Risk)','DOCX','1.6','Pendiente','2024-06-01','Version anotada'),
('Riesgos','RIE-004','Preguntas Kick Off Adamo Risk','DOCX','1.0','Vigente','2025-01-01',NULL),
('Riesgos','RIE-005','CERL ADAMO Enero 2025','PDF','2025','Vigente','2025-01-01',NULL),
('Empresariales','EMP-001','Certificado Existencia y Rep. Legal Ene 2026','PDF','2026','Vigente','2026-01-01','Vigente'),
('Empresariales','EMP-002','Certificacion Composicion Accionaria Ene 2026','PDF','2026','Vigente','2026-01-01','Vigente'),
('Empresariales','EMP-003','Estados Financieros 2024-2023','PDF','2024','Vigente','2024-12-01',NULL),
('Empresariales','EMP-004','Certificacion EEFF 2024','PDF','2024','Vigente','2024-12-01',NULL),
('Empresariales','EMP-005','RUT ADAMO','PDF','2024','Vigente','2024-06-01',NULL),
('Empresariales','EMP-006','Contrato Confidencialidad Paxum','DOCX','1.0','Pendiente','2023-06-01','Revisar vencimiento'),
('Capacitacion','CAP-001','Training Schedule','DOCX','2024','Vigente','2024-01-01',NULL),
('Capacitacion','CAP-002','Ejemplo Certificado Entrenamiento','PDF','1.0','Vigente','2024-06-01','Plantilla'),
('Capacitacion','CAP-003','Estructura Depto Cumplimiento','DOCX','1.0','Vigente','2024-06-01',NULL),
('Capacitacion','CAP-003','Estructura Depto Cumplimiento Publicada','PDF','1.0','Vigente','2024-06-01','Publicada'),
('Capacitacion','CAP-004','Template Corporativo ADAMO','DOCX','1.0','Vigente','2024-06-01','Plantilla base')
ON CONFLICT DO NOTHING;
