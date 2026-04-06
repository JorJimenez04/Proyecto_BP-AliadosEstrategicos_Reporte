-- ============================================================
-- Migración 003 — AdamoServices Partner Manager
-- Descripción : Columnas de métricas corporativas +
--               recreación de CHECK constraints en UTF-8.
-- Idempotente  : Seguro para ejecutar múltiples veces.
-- ============================================================

-- ─────────────────────────────────────────────────────────────
-- BLOQUE 1: Columnas corporativas (ADD IF NOT EXISTS)
-- ─────────────────────────────────────────────────────────────
ALTER TABLE aliados
    ADD COLUMN IF NOT EXISTS estado_hbpocorp      TEXT NOT NULL DEFAULT 'Sin relación',
    ADD COLUMN IF NOT EXISTS estado_adamo         TEXT NOT NULL DEFAULT 'Sin relación',
    ADD COLUMN IF NOT EXISTS estado_paycop        TEXT NOT NULL DEFAULT 'Sin relación',
    ADD COLUMN IF NOT EXISTS crypto_friendly      BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS adult_friendly       BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS permite_monetizacion BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS permite_dispersion   BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS monedas_soportadas   TEXT,
    ADD COLUMN IF NOT EXISTS clientes_vinculados  TEXT,
    ADD COLUMN IF NOT EXISTS volumen_real_mensual TEXT,
    ADD COLUMN IF NOT EXISTS motivo_inactividad   TEXT,
    ADD COLUMN IF NOT EXISTS fecha_inicio_relacion DATE,
    ADD COLUMN IF NOT EXISTS fecha_fin_relacion    DATE;

-- ─────────────────────────────────────────────────────────────
-- BLOQUE 2: Eliminar constraints previos (pueden tener
--           encoding corrupto si se aplicaron con PowerShell)
-- ─────────────────────────────────────────────────────────────
ALTER TABLE aliados
    DROP CONSTRAINT IF EXISTS aliados_estado_hbpocorp_check,
    DROP CONSTRAINT IF EXISTS aliados_estado_adamo_check,
    DROP CONSTRAINT IF EXISTS aliados_estado_paycop_check;

-- ─────────────────────────────────────────────────────────────
-- BLOQUE 3: Recrear constraints con texto limpio UTF-8
-- ─────────────────────────────────────────────────────────────
ALTER TABLE aliados
    ADD CONSTRAINT aliados_estado_hbpocorp_check
        CHECK (estado_hbpocorp IN ('Activo', 'Inactivo', 'Sin relación')),
    ADD CONSTRAINT aliados_estado_adamo_check
        CHECK (estado_adamo    IN ('Activo', 'Inactivo', 'Sin relación')),
    ADD CONSTRAINT aliados_estado_paycop_check
        CHECK (estado_paycop   IN ('Activo', 'Inactivo', 'Sin relación'));

-- ─────────────────────────────────────────────────────────────
-- BLOQUE 4: Índices de optimización (idempotentes)
-- ─────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_aliados_estado_hbpocorp ON aliados(estado_hbpocorp);
CREATE INDEX IF NOT EXISTS idx_aliados_estado_adamo    ON aliados(estado_adamo);
CREATE INDEX IF NOT EXISTS idx_aliados_estado_paycop   ON aliados(estado_paycop);
CREATE INDEX IF NOT EXISTS idx_aliados_crypto
    ON aliados(crypto_friendly) WHERE crypto_friendly = TRUE;
CREATE INDEX IF NOT EXISTS idx_aliados_adult
    ON aliados(adult_friendly)  WHERE adult_friendly  = TRUE;
