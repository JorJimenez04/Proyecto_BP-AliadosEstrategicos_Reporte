-- ============================================================
-- AdamoServices Partner Manager — Migración v2.0
-- Descripción: Añade métricas de relación corporativa (Grupo HoldingsBPO)
--              y capacidades operativas de Banking Partners.
-- Aplicar sobre: Railway PostgreSQL (producción)
-- Autor: Compliance & Technology — AdamoServices
-- ============================================================

-- ─────────────────────────────────────────────────────────────
-- BLOQUE 1: Estados por empresa del Grupo Corporativo
-- Permite registrar el "Relationship Status" de cada partner
-- con cada entidad del holding de forma independiente.
-- ─────────────────────────────────────────────────────────────
ALTER TABLE aliados
    ADD COLUMN IF NOT EXISTS estado_hbpocorp TEXT NOT NULL DEFAULT 'Sin relación'
        CHECK(estado_hbpocorp IN ('Activo', 'Inactivo', 'Sin relación')),
    ADD COLUMN IF NOT EXISTS estado_adamo    TEXT NOT NULL DEFAULT 'Sin relación'
        CHECK(estado_adamo    IN ('Activo', 'Inactivo', 'Sin relación')),
    ADD COLUMN IF NOT EXISTS estado_paycop   TEXT NOT NULL DEFAULT 'Sin relación'
        CHECK(estado_paycop   IN ('Activo', 'Inactivo', 'Sin relación'));


-- ─────────────────────────────────────────────────────────────
-- BLOQUE 2: Perfil Operativo — Banking Capabilities
-- Capacidades del partner relevantes para el scoring SARLAFT
-- y la asignación preventiva del nivel de riesgo.
-- ─────────────────────────────────────────────────────────────
ALTER TABLE aliados
    ADD COLUMN IF NOT EXISTS crypto_friendly      BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS adult_friendly       BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS permite_monetizacion BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS permite_dispersion   BOOLEAN NOT NULL DEFAULT FALSE;


-- ─────────────────────────────────────────────────────────────
-- BLOQUE 3: Detalle Operacional Enriquecido
-- Campos de texto libre para describir el perfil financiero real.
-- ─────────────────────────────────────────────────────────────
ALTER TABLE aliados
    ADD COLUMN IF NOT EXISTS monedas_soportadas   TEXT,   -- Ej: COP-USD-MXN
    ADD COLUMN IF NOT EXISTS clientes_vinculados  TEXT,   -- Ej: Paxum, CM Group
    ADD COLUMN IF NOT EXISTS volumen_real_mensual TEXT;   -- Ej: 10-11M mensuales


-- ─────────────────────────────────────────────────────────────
-- BLOQUE 4: Trazabilidad del Ciclo de Vida de la Relación
-- ─────────────────────────────────────────────────────────────
ALTER TABLE aliados
    ADD COLUMN IF NOT EXISTS motivo_inactividad    TEXT,
    ADD COLUMN IF NOT EXISTS fecha_inicio_relacion DATE,
    ADD COLUMN IF NOT EXISTS fecha_fin_relacion    DATE;


-- ─────────────────────────────────────────────────────────────
-- ÍNDICES — Acelerar filtros del dashboard corporativo
-- ─────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_aliados_estado_hbpocorp ON aliados(estado_hbpocorp);
CREATE INDEX IF NOT EXISTS idx_aliados_estado_adamo    ON aliados(estado_adamo);
CREATE INDEX IF NOT EXISTS idx_aliados_estado_paycop   ON aliados(estado_paycop);
CREATE INDEX IF NOT EXISTS idx_aliados_crypto          ON aliados(crypto_friendly) WHERE crypto_friendly = TRUE;
CREATE INDEX IF NOT EXISTS idx_aliados_adult           ON aliados(adult_friendly)  WHERE adult_friendly  = TRUE;
