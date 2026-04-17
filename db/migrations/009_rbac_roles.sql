-- ============================================================
-- AdamoServices Partner Manager — Migración 009
-- Descripción : Jerarquía RBAC extendida
--               · Expande el CHECK constraint de usuarios.rol con
--                 nuevos roles: agente_kyc, agente_operativo.
--               · Añade la columna rol_usuario a log_auditoria para
--                 trazabilidad de cumplimiento.
-- Modo        : Idempotente (IF NOT EXISTS / DO NOTHING)
-- ============================================================

-- ── 1. Ampliar el CHECK constraint de usuarios.rol ────────────
--    (DROP + re-CREATE es la única forma portátil en PG sin
--    conocer el nombre interno del constraint)
ALTER TABLE usuarios
    DROP CONSTRAINT IF EXISTS usuarios_rol_check;

ALTER TABLE usuarios
    ADD CONSTRAINT usuarios_rol_check
    CHECK(rol IN (
        'admin',              -- Admin Pro: acceso total
        'compliance',         -- Manager Compliance: gestión equipo + KPIs
        'comercial',          -- Manager Pagos: gestión cartera
        'agente_kyc',         -- Agente KYC: validación documental + SARLAFT
        'agente_operativo',   -- Agente Operativo: ejecución técnica
        'consulta'            -- Consulta: solo lectura
    ));

-- ── 2. Añadir columna rol_usuario a log_auditoria ─────────────
ALTER TABLE log_auditoria
    ADD COLUMN IF NOT EXISTS rol_usuario TEXT;

-- ── 3. Índice para búsquedas por rol en auditoría ─────────────
CREATE INDEX IF NOT EXISTS idx_auditoria_rol ON log_auditoria(rol_usuario);

-- ── 4. Backfill: completar rol_usuario en registros históricos ─
--    usando el rol actual del usuario que ejecutó la acción.
UPDATE log_auditoria la
SET    rol_usuario = u.rol
FROM   usuarios u
WHERE  la.usuario_id = u.id
  AND  la.rol_usuario IS NULL;
