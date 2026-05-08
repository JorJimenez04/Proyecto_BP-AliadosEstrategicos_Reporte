-- =============================================================
-- Migración 018: Ficha Técnica del Riel y Criticidad Operativa
-- Transforma la ficha del partner en herramienta de Debida Diligencia
-- avanzada conforme a estándar ISO/SARLAFT/GAFI.
-- Idempotente: ADD COLUMN IF NOT EXISTS — seguro en re-deploy.
-- =============================================================

-- ── Información Técnica del Riel ──────────────────────────────
ALTER TABLE aliados
    ADD COLUMN IF NOT EXISTS tipo_riel              TEXT,
    ADD COLUMN IF NOT EXISTS sla_garantizado        TEXT;

COMMENT ON COLUMN aliados.tipo_riel IS
    'Tipo de riel de pago operado: Dispersión, Recaudo, Crypto, Mixto, N/A';
COMMENT ON COLUMN aliados.sla_garantizado IS
    'Nivel de servicio garantizado por el partner (ej: 99.9%, 4h resolución)';

-- ── Información de Cumplimiento ISO ───────────────────────────
ALTER TABLE aliados
    ADD COLUMN IF NOT EXISTS numero_licencia           TEXT,
    ADD COLUMN IF NOT EXISTS fecha_ultima_auditoria    DATE,
    ADD COLUMN IF NOT EXISTS certificaciones           TEXT[]  NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS es_entidad_regulada       BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN aliados.numero_licencia IS
    'Número de licencia o resolución regulatoria emitida por la SFC u otro ente';
COMMENT ON COLUMN aliados.fecha_ultima_auditoria IS
    'Fecha de la última auditoría externa o visita de inspección';
COMMENT ON COLUMN aliados.certificaciones IS
    'Certificaciones vigentes: ISO 27001, PCI-DSS, SOC 2, ISO 9001, ISO 20000';
COMMENT ON COLUMN aliados.es_entidad_regulada IS
    'TRUE si el partner posee licencia financiera emitida por un ente regulador';

-- ── Gobernanza y Plan de Continuidad ─────────────────────────
ALTER TABLE aliados
    ADD COLUMN IF NOT EXISTS partner_respaldo       TEXT,
    ADD COLUMN IF NOT EXISTS pct_concentracion      NUMERIC(5,2);

COMMENT ON COLUMN aliados.partner_respaldo IS
    'Nombre del partner de respaldo para el plan de continuidad operativa';
COMMENT ON COLUMN aliados.pct_concentracion IS
    'Porcentaje de la operación total concentrada en este partner (0.00 - 100.00)';

-- ── Nivel de Criticidad Operativa (derivado de SARLAFT + regulación) ──
ALTER TABLE aliados
    ADD COLUMN IF NOT EXISTS nivel_criticidad       TEXT NOT NULL DEFAULT 'Estándar';

COMMENT ON COLUMN aliados.nivel_criticidad IS
    'DDI (Debida Diligencia Intensificada) | DDS-Alto | DDS-Simplificado | Estándar. '
    'DDI - Entidad Regulada para entidades reguladas con score técnico alto. '
    'Campo derivado de nivel_riesgo + es_entidad_regulada.';

-- ── Índice para consultas por criticidad ─────────────────────
CREATE INDEX IF NOT EXISTS idx_aliados_nivel_criticidad
    ON aliados (nivel_criticidad);

CREATE INDEX IF NOT EXISTS idx_aliados_entidad_regulada
    ON aliados (es_entidad_regulada)
    WHERE es_entidad_regulada = TRUE;

-- ── Índice GIN para certificaciones ──────────────────────────
CREATE INDEX IF NOT EXISTS idx_aliados_certificaciones
    ON aliados USING GIN (certificaciones);

-- ── Actualizar nivel_criticidad en registros existentes ───────
-- Lógica: Muy Alto sin licencia → DDI
--          Alto/Medio sin licencia → DDS-Alto / DDS-Simplificado
--          Bajo → Estándar
--          Regulada con score alto → DDI - Entidad Regulada
UPDATE aliados
SET nivel_criticidad = CASE
    WHEN es_entidad_regulada = TRUE AND nivel_riesgo IN ('Alto', 'Muy Alto')
        THEN 'DDI - Entidad Regulada'
    WHEN nivel_riesgo = 'Muy Alto'
        THEN 'DDI'
    WHEN nivel_riesgo = 'Alto'
        THEN 'DDS-Alto'
    WHEN nivel_riesgo = 'Medio'
        THEN 'DDS-Simplificado'
    ELSE 'Estándar'
END
WHERE nivel_criticidad = 'Estándar';
