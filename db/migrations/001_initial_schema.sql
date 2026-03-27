-- ============================================================
-- AdamoServices Partner Manager — Esquema de Base de Datos v1.0
-- Motor: SQLite (desarrollo) | PostgreSQL (producción)
-- Autor: Compliance & Technology — AdamoServices
-- ============================================================
-- Ejecutar con: python -m db.database  (inicializa la BD)
-- ============================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;


-- ─────────────────────────────────────────────────────────────
-- TABLA: usuarios
-- Gestión de acceso basado en roles (RBAC)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS usuarios (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    username            TEXT    NOT NULL UNIQUE,
    nombre_completo     TEXT    NOT NULL,
    email               TEXT    NOT NULL UNIQUE,
    password_hash       TEXT    NOT NULL,                      -- bcrypt hash
    rol                 TEXT    NOT NULL DEFAULT 'consulta'
                            CHECK(rol IN ('admin', 'compliance', 'comercial', 'consulta')),
    departamento        TEXT,                                  -- Área o ciudad de la oficina
    activo              INTEGER NOT NULL DEFAULT 1,            -- 0 = desactivado
    ultimo_acceso       TIMESTAMP,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ─────────────────────────────────────────────────────────────
-- TABLA: aliados
-- Registro maestro de Banking Partners y Aliados Estratégicos
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS aliados (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,

    -- ── Información Básica ───────────────────────────────
    nombre_razon_social TEXT    NOT NULL,
    nit                 TEXT    NOT NULL UNIQUE,               -- Con dígito verificador: 900123456-1
    tipo_aliado         TEXT    NOT NULL
                            CHECK(tipo_aliado IN (
                                'Banking Partner',
                                'Aliado Estratégico',
                                'Corresponsal Bancario',
                                'Proveedor de Servicios'
                            )),
    fecha_vinculacion   DATE    NOT NULL,
    estado_pipeline     TEXT    NOT NULL DEFAULT 'Prospecto'
                            CHECK(estado_pipeline IN (
                                'Prospecto',
                                'En Calificación',
                                'Onboarding',
                                'Activo',
                                'Suspendido',
                                'Terminado'
                            )),

    -- ── Información de Contacto ──────────────────────────
    representante_legal TEXT,
    cargo_representante TEXT,
    email_contacto      TEXT,
    telefono_contacto   TEXT,
    ciudad              TEXT,
    departamento_geo    TEXT,                                  -- Departamento/Estado geográfico
    direccion           TEXT,

    -- ── Información Comercial ────────────────────────────
    ejecutivo_cuenta_id INTEGER REFERENCES usuarios(id),      -- Responsable comercial asignado
    segmento_negocio    TEXT,                                  -- Ej: Retail, Fintech, Salud
    volumen_estimado_mensual REAL DEFAULT 0.0,                 -- COP estimado de transacciones

    -- ────────────────────────────────────────────────────
    -- CAMPOS DE CUMPLIMIENTO — SARLAFT
    -- (Sistema de Administración del Riesgo de Lavado de
    --  Activos y de la Financiación del Terrorismo)
    -- ────────────────────────────────────────────────────

    -- Clasificación de Riesgo
    nivel_riesgo        TEXT    NOT NULL DEFAULT 'Medio'
                            CHECK(nivel_riesgo IN ('Bajo', 'Medio', 'Alto', 'Muy Alto')),
    puntaje_riesgo      REAL    DEFAULT 0.0,                   -- Score numérico 0-100
    metodologia_riesgo  TEXT,                                  -- Descripción metodología aplicada

    -- PEP — Persona Expuesta Políticamente
    es_pep              INTEGER NOT NULL DEFAULT 0,            -- 0=No, 1=Sí
    descripcion_pep     TEXT,                                  -- Cargo/relación PEP si aplica
    vinculo_pep         TEXT,                                  -- Familiar/socio PEP si aplica

    -- Revisiones SARLAFT periódicas
    estado_sarlaft          TEXT    NOT NULL DEFAULT 'Pendiente'
                                CHECK(estado_sarlaft IN ('Al Día', 'Pendiente', 'En Revisión', 'Vencido')),
    fecha_ultima_revision   DATE,                              -- Última revisión SARLAFT completada
    fecha_proxima_revision  DATE,                              -- Próxima revisión programada
    frecuencia_revision     TEXT    DEFAULT 'Anual'
                                CHECK(frecuencia_revision IN ('Mensual', 'Trimestral', 'Semestral', 'Anual')),
    oficial_compliance_id   INTEGER REFERENCES usuarios(id),  -- Quién realizó la última revisión

    -- Verificación de Listas Restrictivas
    listas_verificadas          INTEGER NOT NULL DEFAULT 0,    -- 0=No, 1=Sí
    fecha_verificacion_listas   DATE,
    resultado_listas            TEXT    DEFAULT 'Sin coincidencias'
                                    CHECK(resultado_listas IN (
                                        'Sin coincidencias',
                                        'Coincidencia leve — revisar',
                                        'Coincidencia — bloqueado'
                                    )),
    -- Listas verificadas (OFAC, ONU, UE, LAFT local)
    lista_ofac_ok       INTEGER DEFAULT 0,
    lista_onu_ok        INTEGER DEFAULT 0,
    lista_ue_ok         INTEGER DEFAULT 0,
    lista_local_ok      INTEGER DEFAULT 0,                     -- Lista local Superfinanciera

    -- Due Diligence
    estado_due_diligence    TEXT    NOT NULL DEFAULT 'Pendiente'
                                CHECK(estado_due_diligence IN (
                                    'Pendiente',
                                    'En Proceso',
                                    'Completado',
                                    'Rechazado'
                                )),
    fecha_due_diligence     DATE,
    nivel_due_diligence     TEXT    DEFAULT 'Básico'
                                CHECK(nivel_due_diligence IN ('Básico', 'Reforzado', 'Simplificado')),

    -- ── Documentación ────────────────────────────────────
    rut_recibido                    INTEGER DEFAULT 0,
    camara_comercio_recibida        INTEGER DEFAULT 0,
    fecha_vencimiento_camara        DATE,
    estados_financieros_recibidos   INTEGER DEFAULT 0,
    formulario_vinculacion_recibido INTEGER DEFAULT 0,
    contrato_firmado                INTEGER DEFAULT 0,
    fecha_firma_contrato            DATE,
    fecha_vencimiento_contrato      DATE,
    poliza_recibida                 INTEGER DEFAULT 0,
    fecha_vencimiento_poliza        DATE,

    -- ── Observaciones y Señales de Alerta ────────────────
    observaciones_compliance    TEXT,                          -- Notas internas del área
    alertas_activas             INTEGER DEFAULT 0,             -- Número de alertas pendientes
    motivo_suspension           TEXT,                          -- Si estado es Suspendido

    -- ── Metadata de registro ─────────────────────────────
    creado_por          INTEGER REFERENCES usuarios(id),
    actualizado_por     INTEGER REFERENCES usuarios(id),
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ─────────────────────────────────────────────────────────────
-- TABLA: historial_estados
-- Trazabilidad completa del Pipeline de estados
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS historial_estados (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    aliado_id       INTEGER NOT NULL REFERENCES aliados(id) ON DELETE CASCADE,
    estado_anterior TEXT,
    estado_nuevo    TEXT    NOT NULL,
    motivo          TEXT,                                      -- Justificación del cambio
    cambiado_por    INTEGER NOT NULL REFERENCES usuarios(id),
    changed_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ─────────────────────────────────────────────────────────────
-- TABLA: revisiones_sarlaft
-- Registro detallado de cada revisión SARLAFT realizada
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS revisiones_sarlaft (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    aliado_id           INTEGER NOT NULL REFERENCES aliados(id) ON DELETE CASCADE,
    fecha_revision      DATE    NOT NULL,
    oficial_id          INTEGER NOT NULL REFERENCES usuarios(id),
    nivel_riesgo_previo TEXT,
    nivel_riesgo_nuevo  TEXT    NOT NULL,
    puntaje_previo      REAL,
    puntaje_nuevo       REAL,
    hallazgos           TEXT,                                  -- Observaciones de la revisión
    acciones_requeridas TEXT,                                  -- Plan de acción si aplica
    proxima_revision    DATE,
    aprobado            INTEGER DEFAULT 0,                     -- 0=En revisión, 1=Aprobado
    aprobado_por        INTEGER REFERENCES usuarios(id),
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ─────────────────────────────────────────────────────────────
-- TABLA: log_auditoria
-- Registro inmutable de todas las acciones del sistema
-- Requerido por Superfinanciera para cumplimiento
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS log_auditoria (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id      INTEGER REFERENCES usuarios(id),
    username        TEXT    NOT NULL,                          -- Denormalizado por inmutabilidad
    accion          TEXT    NOT NULL,                          -- CREATE | UPDATE | DELETE | LOGIN | EXPORT
    entidad         TEXT    NOT NULL,                          -- Tabla afectada: 'aliados', 'usuarios', etc.
    entidad_id      INTEGER,                                   -- ID del registro afectado
    descripcion     TEXT    NOT NULL,                          -- Descripción legible del cambio
    valores_anteriores TEXT,                                   -- JSON con los valores antes del cambio
    valores_nuevos     TEXT,                                   -- JSON con los valores después del cambio
    ip_address      TEXT,                                      -- IP del cliente (si disponible)
    user_agent      TEXT,
    resultado       TEXT    NOT NULL DEFAULT 'exitoso'
                        CHECK(resultado IN ('exitoso', 'fallido', 'rechazado')),
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ─────────────────────────────────────────────────────────────
-- ÍNDICES — Optimización de consultas frecuentes
-- ─────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_aliados_nit              ON aliados(nit);
CREATE INDEX IF NOT EXISTS idx_aliados_estado_pipeline  ON aliados(estado_pipeline);
CREATE INDEX IF NOT EXISTS idx_aliados_nivel_riesgo     ON aliados(nivel_riesgo);
CREATE INDEX IF NOT EXISTS idx_aliados_estado_sarlaft   ON aliados(estado_sarlaft);
CREATE INDEX IF NOT EXISTS idx_aliados_proxima_revision ON aliados(fecha_proxima_revision);
CREATE INDEX IF NOT EXISTS idx_historial_aliado         ON historial_estados(aliado_id);
CREATE INDEX IF NOT EXISTS idx_revisiones_aliado        ON revisiones_sarlaft(aliado_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_usuario        ON log_auditoria(usuario_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_entidad        ON log_auditoria(entidad, entidad_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_fecha          ON log_auditoria(created_at);


-- ─────────────────────────────────────────────────────────────
-- TRIGGERS — Automatización de updated_at
-- ─────────────────────────────────────────────────────────────
CREATE TRIGGER IF NOT EXISTS trg_aliados_updated_at
    AFTER UPDATE ON aliados
    FOR EACH ROW
BEGIN
    UPDATE aliados SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_usuarios_updated_at
    AFTER UPDATE ON usuarios
    FOR EACH ROW
BEGIN
    UPDATE usuarios SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;


-- ─────────────────────────────────────────────────────────────
-- DATOS INICIALES — Usuario administrador seed
-- La password debe ser reemplazada al inicializar vía Python
-- ─────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO usuarios (username, nombre_completo, email, password_hash, rol)
VALUES (
    'admin',
    'Administrador del Sistema',
    'compliance@adamoservices.co',
    'PLACEHOLDER_HASH',           -- Reemplazado por database.py con bcrypt
    'admin'
);
