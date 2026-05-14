-- 025_rbac_roles_v2.sql
-- Amplía CHECK constraint de usuarios.rol con los nuevos perfiles RBAC v2.
-- Idempotente: DROP CONSTRAINT IF EXISTS + ADD CONSTRAINT

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
    'admin',
    'comercial',
    'agente_kyc',
    'agente_operativo',
    'consulta'
  ));
