-- ============================================================
-- AdamoServices Partner Manager -- Migración 023
-- Descripción : Tabla de historial inmutable de versiones de
--               documentos del Centro Documental de Cumplimiento.
--               Cada fila es una versión "congelada" del documento
--               en el momento previo a una actualización.
-- Idempotente : CREATE TABLE IF NOT EXISTS
-- ============================================================

CREATE TABLE IF NOT EXISTS compliance_documentos_historial (
    id                  SERIAL      PRIMARY KEY,
    documento_raiz_id   INTEGER     NOT NULL
                        REFERENCES compliance_documentos(id) ON DELETE CASCADE,
    carpeta             TEXT        NOT NULL,
    codigo              TEXT        NOT NULL,
    nombre              TEXT        NOT NULL,
    descripcion         TEXT,
    version             TEXT        NOT NULL DEFAULT '1.0',
    estado              TEXT        NOT NULL DEFAULT 'Vigente',
    formato             TEXT        NOT NULL DEFAULT 'PDF',
    url_documento       TEXT,
    fecha_emision       DATE,
    fecha_vencimiento   DATE,
    empresa             TEXT,
    creado_por          TEXT,
    actualizado_por     TEXT,
    -- Metadatos del snapshot
    descripcion_cambio  TEXT,               -- razón registrada al guardar
    snapshot_por        TEXT    NOT NULL DEFAULT 'sistema',
    snapshot_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_doc_hist_raiz
    ON compliance_documentos_historial (documento_raiz_id);

CREATE INDEX IF NOT EXISTS idx_doc_hist_snapshot_at
    ON compliance_documentos_historial (snapshot_at DESC);
