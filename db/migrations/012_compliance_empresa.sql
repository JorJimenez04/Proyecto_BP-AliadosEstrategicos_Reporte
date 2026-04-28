-- ============================================================
-- AdamoServices Partner Manager -- Migracion 012
-- Descripcion : Agrega columna empresa a compliance_documentos
--               para soporte multi-entidad (Holdings BPO /
--               PayCOP / Adamo Services).
-- Idempotente : ADD COLUMN IF NOT EXISTS
-- ============================================================

ALTER TABLE compliance_documentos
    ADD COLUMN IF NOT EXISTS empresa TEXT
    CHECK (empresa IN ('Holdings BPO', 'PayCOP', 'Adamo Services'));

-- NULL = documento compartido (visible en todas las empresas cuando filtro = Todas)

CREATE INDEX IF NOT EXISTS idx_compliance_docs_empresa
    ON compliance_documentos (empresa);

COMMENT ON COLUMN compliance_documentos.empresa IS
    'Entidad propietaria del documento. NULL = compartido entre todas las empresas.';
