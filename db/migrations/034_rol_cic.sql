-- 034_rol_cic.sql
-- Añade el rol 'cic' (Comercial Inteligencia Comercial) al CHECK constraint de usuarios.rol.
-- El rol replica los permisos del rol legacy 'comercial'.
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
    'cic',
    'admin',
    'comercial',
    'agente_kyc',
    'agente_operativo',
    'consulta'
  ));
