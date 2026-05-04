-- ============================================================
-- AdamoServices Partner Manager -- Migracion 015
-- Descripcion : Renombra la carpeta "Riesgos" a
--               "Governanza" en la tabla compliance_documentos.
--               1) Actualiza filas existentes.
--               2) Reemplaza el CHECK constraint de carpeta.
-- Idempotente : Usa DO $$ ... $$ para ejecutar solo si aplica.
-- ============================================================

-- 1. Actualizar datos existentes
UPDATE compliance_documentos
SET    carpeta = 'Governanza'
WHERE  carpeta = 'Riesgos';

-- 2. Reemplazar el CHECK constraint
DO $$
BEGIN
    ALTER TABLE compliance_documentos
        DROP CONSTRAINT IF EXISTS compliance_documentos_carpeta_check;

    ALTER TABLE compliance_documentos
        ADD CONSTRAINT compliance_documentos_carpeta_check
        CHECK (carpeta IN (
            'Politicas','Manuales','Onboarding',
            'Procesos y Procedimientos','Governanza','Empresariales','Capacitacion'
        ));
END $$;
