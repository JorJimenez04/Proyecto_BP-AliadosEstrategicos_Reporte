-- ============================================================
-- Migración 005 — AdamoServices Partner Manager
-- Descripción : Tabla dedicada para el catálogo de agentes
--               operativos (independiente de la tabla usuarios).
--               Agrega FK agente_id en aliados para asignaciones.
-- Idempotente  : Seguro para ejecutar múltiples veces.
-- ============================================================

-- ─────────────────────────────────────────────────────────────
-- TABLA: agentes
-- Catálogo informativo de colaboradores por equipo.
-- No contiene credenciales — los agentes NO acceden al sistema.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agentes (
    id                      SERIAL          PRIMARY KEY,
    username                TEXT            NOT NULL UNIQUE,     -- identificador único (ej: samuel_mora)
    nombre_completo         TEXT            NOT NULL,
    equipo                  TEXT            NOT NULL
                                CHECK (equipo IN ('Cumplimiento', 'Pagos', 'Soporte')),
    cargo                   TEXT,
    email                   TEXT,
    telefono                TEXT,
    foto_url                TEXT,                                -- URL externa (Supabase Storage)
    meta_mensual_gestiones  INTEGER         NOT NULL DEFAULT 50,
    notas                   TEXT,                                -- Observaciones internas de RRHH
    activo                  BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Trigger para updated_at automático
CREATE OR REPLACE FUNCTION fn_agentes_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_agentes_updated_at ON agentes;
CREATE TRIGGER trg_agentes_updated_at
    BEFORE UPDATE ON agentes
    FOR EACH ROW EXECUTE FUNCTION fn_agentes_updated_at();

-- ─────────────────────────────────────────────────────────────
-- Columna agente_id en aliados (asignación partner → agente)
-- ─────────────────────────────────────────────────────────────
ALTER TABLE aliados
    ADD COLUMN IF NOT EXISTS agente_id INTEGER REFERENCES agentes(id) ON DELETE SET NULL;

-- Índices
CREATE INDEX IF NOT EXISTS idx_agentes_equipo    ON agentes (equipo);
CREATE INDEX IF NOT EXISTS idx_agentes_activo    ON agentes (activo) WHERE activo = TRUE;
CREATE INDEX IF NOT EXISTS idx_aliados_agente_id ON aliados (agente_id);
