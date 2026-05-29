-- ============================================================
-- AdamoServices Partner Manager -- Migración 032
-- Descripción : Historial de calificaciones de riesgo SARLAFT
--               por cliente. Append-only: nunca UPDATE ni DELETE.
-- Idempotente : CREATE TABLE IF NOT EXISTS
-- ============================================================

CREATE TABLE IF NOT EXISTS cliente_historial_riesgo (
    id                   SERIAL      PRIMARY KEY,
    cliente_id           INTEGER     NOT NULL
                             REFERENCES clientes(id) ON DELETE CASCADE,
    puntaje_anterior     INTEGER     CHECK (puntaje_anterior >= 0 AND puntaje_anterior <= 100),
    puntaje_nuevo        INTEGER     NOT NULL CHECK (puntaje_nuevo >= 0 AND puntaje_nuevo <= 100),
    nivel_anterior       TEXT,
    nivel_nuevo          TEXT        NOT NULL
                             CHECK (nivel_nuevo IN (
                                 'Sin calificar','Bajo','Medio','Alto','Muy Alto'
                             )),
    motivo               TEXT,
    observaciones        TEXT,
    era_pep              INTEGER     NOT NULL DEFAULT 0 CHECK (era_pep IN (0,1)),
    tenia_cripto         INTEGER     NOT NULL DEFAULT 0 CHECK (tenia_cripto IN (0,1)),
    jurisdicciones_snap  TEXT[]      NOT NULL DEFAULT '{}',
    registrado_por       TEXT        NOT NULL DEFAULT 'sistema',
    registrado_en        TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_historial_riesgo_cliente_id
    ON cliente_historial_riesgo (cliente_id);
CREATE INDEX IF NOT EXISTS idx_historial_riesgo_registrado_en
    ON cliente_historial_riesgo (registrado_en DESC);
