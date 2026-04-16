-- ============================================================
-- Migración 004 — AdamoServices Partner Manager
-- Descripción : Columnas de perfil operativo en la tabla usuarios
--               para el módulo de Equipos y KPIs de Desempeño.
-- Idempotente  : Seguro para ejecutar múltiples veces.
-- ============================================================

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS equipo                 TEXT,
    ADD COLUMN IF NOT EXISTS cargo                  TEXT,
    ADD COLUMN IF NOT EXISTS foto_url               TEXT,
    ADD COLUMN IF NOT EXISTS meta_mensual_gestiones INTEGER NOT NULL DEFAULT 50;

-- Índice para filtrar agentes por equipo en el sidebar
CREATE INDEX IF NOT EXISTS idx_usuarios_equipo
    ON usuarios (equipo)
    WHERE equipo IS NOT NULL;

-- Comentario de documentación
COMMENT ON COLUMN usuarios.equipo                 IS 'Equipo operativo: Cumplimiento | Pagos | Soporte';
COMMENT ON COLUMN usuarios.cargo                  IS 'Cargo o título del agente (ej: Analista SARLAFT)';
COMMENT ON COLUMN usuarios.foto_url               IS 'URL de foto en Supabase Storage (reservado para uso futuro)';
COMMENT ON COLUMN usuarios.meta_mensual_gestiones IS 'Meta mensual de gestiones para el KPI de productividad';
