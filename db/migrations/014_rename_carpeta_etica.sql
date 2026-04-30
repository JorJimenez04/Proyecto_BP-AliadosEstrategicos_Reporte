-- ============================================================
-- AdamoServices Partner Manager -- Migracion 014
-- Descripcion : Renombra la carpeta "Etica" a
--               "Procesos y Procedimientos" en la tabla
--               compliance_documentos.
--               1) Actualiza filas existentes.
--               2) Reemplaza el CHECK constraint de carpeta.
-- Idempotente : Usa DO $$ ... $$ para ejecutar solo si aplica.
-- ============================================================

-- 1. Actualizar datos existentes
UPDATE compliance_documentos
SET    carpeta = 'Procesos y Procedimientos'
WHERE  carpeta = 'Etica';

-- 2. Reemplazar el CHECK constraint
DO $$
BEGIN
    -- Eliminar el constraint antiguo (nombre generado por Postgres)
    ALTER TABLE compliance_documentos
        DROP CONSTRAINT IF EXISTS compliance_documentos_carpeta_check;

    -- Agregar el constraint actualizado
    ALTER TABLE compliance_documentos
        ADD CONSTRAINT compliance_documentos_carpeta_check
        CHECK (carpeta IN (
            'Politicas','Manuales','Onboarding',
            'Procesos y Procedimientos','Riesgos','Empresariales','Capacitacion'
        ));
END $$;
