-- 025_rbac_roles_v2.sql
-- Amplía el CHECK constraint de usuarios.rol con los nuevos perfiles RBAC
-- Idempotente: usa DROP CONSTRAINT IF EXISTS + ADD CONSTRAINT

ALTER TABLE usuarios
  DROP CONSTRAINT IF EXISTS usuarios_rol_check;

ALTER TABLE usuarios
  ADD CONSTRAINT usuarios_rol_check
  CHECK (rol IN (
    'super_admin',
    'compliance',
    'manager_ops',
    'manager_comercial',
    'manager_legal',
    'agente',
    -- legacy (mantener compatibilidad)
    'admin',
    'comercial',
    'consulta'
  ));

-- Backfill: mapear roles legacy a nuevos
UPDATE usuarios SET rol = 'super_admin'  WHERE rol = 'admin';
UPDATE usuarios SET rol = 'manager_ops'  WHERE rol = 'comercial';
UPDATE usuarios SET rol = 'agente'       WHERE rol = 'consulta';
