-- ============================================================
-- AdamoServices Partner Manager -- Migración 031
-- Descripción : Gestión documental de clientes.
--               cliente_documentos       — tabla viva (actualizable)
--               cliente_documentos_historial — append-only (snapshots)
-- Idempotente : CREATE TABLE IF NOT EXISTS
-- ============================================================

CREATE TABLE IF NOT EXISTS cliente_documentos (
    id              SERIAL      PRIMARY KEY,
    cliente_id      INTEGER     NOT NULL
                        REFERENCES clientes(id) ON DELETE CASCADE,
    contrato_id     INTEGER
                        REFERENCES cliente_contratos(id) ON DELETE SET NULL,
    titulo          TEXT        NOT NULL,
    carpeta         TEXT        NOT NULL
                        CHECK (carpeta IN (
                            'Politicas','Manuales','Onboarding',
                            'Procesos y Procedimientos','Governanza','Empresariales',
                            'Capacitacion','Contratos','Actas y Formatos',
                            'Matrices','Tecnologia'
                        )),
    estado          TEXT        NOT NULL DEFAULT 'Pendiente'
                        CHECK (estado IN ('Vigente','Pendiente','Vencido','Archivado')),
    formato         TEXT        NOT NULL DEFAULT 'OTRO'
                        CHECK (formato IN ('PDF','DOCX','XLSX','PPTX','OTRO')),
    url             TEXT,
    version         TEXT        NOT NULL DEFAULT '1.0',
    fecha_emision   DATE,
    descripcion_cambio TEXT,
    creado_por      TEXT        NOT NULL DEFAULT 'sistema',
    actualizado_por TEXT,
    created_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cliente_docs_cliente_id
    ON cliente_documentos (cliente_id);
CREATE INDEX IF NOT EXISTS idx_cliente_docs_carpeta
    ON cliente_documentos (carpeta);
CREATE INDEX IF NOT EXISTS idx_cliente_docs_estado
    ON cliente_documentos (estado);
CREATE INDEX IF NOT EXISTS idx_cliente_docs_contrato_id
    ON cliente_documentos (contrato_id);

CREATE OR REPLACE FUNCTION fn_cliente_docs_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_cliente_docs_updated_at ON cliente_documentos;
CREATE TRIGGER trg_cliente_docs_updated_at
    BEFORE UPDATE ON cliente_documentos
    FOR EACH ROW EXECUTE FUNCTION fn_cliente_docs_updated_at();

-- ── Historial append-only ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS cliente_documentos_historial (
    id                  SERIAL      PRIMARY KEY,
    documento_raiz_id   INTEGER     NOT NULL
                            REFERENCES cliente_documentos(id) ON DELETE CASCADE,
    cliente_id          INTEGER     NOT NULL,
    contrato_id         INTEGER,
    titulo              TEXT        NOT NULL,
    carpeta             TEXT        NOT NULL,
    estado              TEXT        NOT NULL,
    formato             TEXT        NOT NULL,
    url                 TEXT,
    version             TEXT        NOT NULL DEFAULT '1.0',
    fecha_emision       DATE,
    descripcion_cambio  TEXT,
    snapshot_por        TEXT        NOT NULL DEFAULT 'sistema',
    snapshot_at         TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cliente_docs_hist_raiz
    ON cliente_documentos_historial (documento_raiz_id);
CREATE INDEX IF NOT EXISTS idx_cliente_docs_hist_cliente
    ON cliente_documentos_historial (cliente_id);
CREATE INDEX IF NOT EXISTS idx_cliente_docs_hist_at
    ON cliente_documentos_historial (snapshot_at DESC);
