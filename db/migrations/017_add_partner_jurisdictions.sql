-- =============================================================
-- Migración 017: Añadir columna jurisdicciones a aliados
-- Idempotente: ADD COLUMN IF NOT EXISTS — seguro en re-deploy.
-- Almacena como TEXT[] los países donde opera el partner.
-- =============================================================

ALTER TABLE aliados
    ADD COLUMN IF NOT EXISTS jurisdicciones TEXT[] NOT NULL DEFAULT '{}';

-- Índice GIN para consultas eficientes sobre el array
-- (ej. WHERE 'Brasil' = ANY(jurisdicciones))
CREATE INDEX IF NOT EXISTS idx_aliados_jurisdicciones
    ON aliados USING GIN (jurisdicciones);

COMMENT ON COLUMN aliados.jurisdicciones IS
    'Países de operación del partner. Array TEXT[]. '
    'Impacta puntaje_riesgo si incluye jurisdicciones GAFI de alto riesgo.';
