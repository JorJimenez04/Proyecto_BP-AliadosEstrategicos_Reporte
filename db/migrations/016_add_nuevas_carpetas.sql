-- ============================================================
-- AdamoServices Partner Manager -- Migracion 016
-- Descripcion : Agrega las carpetas Contratos, Actas y Formatos,
--               Matrices y Tecnologia al CHECK constraint de
--               compliance_documentos.
-- Idempotente : DROP + ADD CONSTRAINT dentro de DO $$
-- ============================================================

DO $$
BEGIN
    ALTER TABLE compliance_documentos
        DROP CONSTRAINT IF EXISTS compliance_documentos_carpeta_check;

    ALTER TABLE compliance_documentos
        ADD CONSTRAINT compliance_documentos_carpeta_check
        CHECK (carpeta IN (
            'Politicas','Manuales','Onboarding',
            'Procesos y Procedimientos','Governanza','Empresariales','Capacitacion',
            'Contratos','Actas y Formatos','Matrices','Tecnologia'
        ));
END $$;
