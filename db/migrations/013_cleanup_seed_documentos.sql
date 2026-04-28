-- ============================================================
-- AdamoServices Partner Manager -- Migracion 013
-- Descripcion : Elimina todos los documentos generados por el
--               seed automatico (creado_por = 'sistema').
--
-- Idempotente : DELETE ... WHERE creado_por = 'sistema'
--               Despues de la primera ejecucion no existen filas
--               con creado_por = 'sistema', por lo que sucesivas
--               ejecuciones eliminan 0 filas sin efectos adversos.
--
-- Razon       : sync_db.py no tiene seguimiento de migraciones
--               aplicadas, por lo que re-ejecuta 011 en cada
--               despliegue y el seed sin restriccion UNIQUE
--               generaba duplicados (39 docs * N deploys).
--               Esta migracion limpia esos duplicados una sola vez.
-- ============================================================

DELETE FROM compliance_documentos WHERE creado_por = 'sistema';

-- Reiniciar la secuencia de IDs para que los proximos documentos
-- reales comiencen desde 1.
-- Se usa RESTART IDENTITY si la tabla queda vacia; si el usuario ya
-- cargó documentos reales (creado_por != 'sistema'), la secuencia
-- NO se reinicia para no romper las FK existentes.
DO $$
BEGIN
    IF (SELECT COUNT(*) FROM compliance_documentos) = 0 THEN
        ALTER SEQUENCE compliance_documentos_id_seq RESTART WITH 1;
    END IF;
END $$;
