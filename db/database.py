"""
db/database.py
Gestor de conexión a la base de datos — AdamoServices Partner Manager.
Motor: PostgreSQL vía SQLAlchemy.
Ejecutar directamente para inicializar el esquema: python -m db.database
"""

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from config.settings import DATABASE_URL, BASE_DIR, DEBUG

logger = logging.getLogger(__name__)

# ── Motor SQLAlchemy (PostgreSQL) ─────────────────────────────
# Normalizar esquema postgres:// → postgresql:// (Railway usa postgres://)
_db_url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
engine = create_engine(
    _db_url,
    poolclass=QueuePool,
    pool_size=5,          # Conexiones simultáneas mantenidas
    max_overflow=10,      # Conexiones adicionales bajo carga
    pool_timeout=30,      # Tiempo máximo de espera por conexión (s)
    pool_recycle=1800,    # Reciclar conexiones cada 30 min (evita timeout Railway)
    pool_pre_ping=True,   # Verifica conexiones antes de usarlas
    echo=DEBUG,
)


# ── Fábrica de sesiones ───────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


def get_session() -> Session:
    """
    Generador de sesiones para usar como context manager.

    Uso:
        with get_session() as session:
            result = session.execute(text("SELECT 1"))
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database() -> None:
    """
    Inicializa la base de datos ejecutando el script SQL de migración inicial.
    """
    migration_file = BASE_DIR / "db" / "migrations" / "001_initial_schema_pg.sql"

    if not migration_file.exists():
        raise FileNotFoundError(f"Script de migración no encontrado: {migration_file}")

    logger.info("[AdamoServices] Inicializando base de datos (PostgreSQL)...")

    sql_script = migration_file.read_text(encoding="utf-8")

    # Ejecutar el script completo en un único cursor para soportar
    # bloques plpgsql ($$...END;...$$) que contienen ";" internos.
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cur:
            cur.execute(sql_script)
        raw_conn.commit()
    finally:
        raw_conn.close()

    # Actualizar el hash de la password del admin seed
    _seed_admin_user()

    logger.info("[AdamoServices] Base de datos inicializada correctamente.")


def _seed_admin_user() -> None:
    """
    Crea o actualiza el usuario administrador seed usando las variables de entorno.

    Estrategia (para evitar conflictos de UNIQUE en username y email):
    1. UPDATE la fila con PLACEHOLDER_HASH → la convierte en el usuario final
       (maneja el caso de renombrar 'admin' → ADMIN_USERNAME).
    2. Si ninguna fila tenía PLACEHOLDER_HASH (la BD ya estaba inicializada),
       intenta INSERT del usuario final. Si el username ya existe, actualiza
       el hash solo si aún era PLACEHOLDER_HASH.
    """
    import bcrypt
    import os

    admin_password = os.getenv("ADMIN_PASSWORD", "Admin@AdamoServices2025!")
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_email    = os.getenv("ADMIN_EMAIL", "compliance@adamoservices.co")
    admin_name     = os.getenv("ADMIN_NAME", "Administrador del Sistema")

    password_hash = bcrypt.hashpw(
        admin_password.encode("utf-8"),
        bcrypt.gensalt(rounds=12)
    ).decode("utf-8")

    params = {
        "username": admin_username,
        "nombre":   admin_name,
        "email":    admin_email,
        "hash":     password_hash,
    }

    with engine.connect() as conn:
        # Paso 1: actualizar cualquier fila con PLACEHOLDER_HASH.
        # Esto convierte el seed SQL ('admin') en el usuario real configurado
        # sin generar conflictos de email duplicado.
        result = conn.execute(
            text("""
                UPDATE usuarios
                SET username        = :username,
                    nombre_completo = :nombre,
                    email           = :email,
                    password_hash   = :hash,
                    rol             = 'admin'
                WHERE password_hash = 'PLACEHOLDER_HASH'
            """),
            params,
        )
        updated = result.rowcount

        # Paso 2: si no había PLACEHOLDER_HASH, el usuario ya existía previamente.
        # Asegurarse de que existe con el username correcto.
        if updated == 0:
            conn.execute(
                text("""
                    INSERT INTO usuarios (username, nombre_completo, email, password_hash, rol)
                    VALUES (:username, :nombre, :email, :hash, 'admin')
                    ON CONFLICT (username) DO UPDATE
                        SET password_hash   = CASE
                                                  WHEN usuarios.password_hash = 'PLACEHOLDER_HASH'
                                                  THEN EXCLUDED.password_hash
                                                  ELSE usuarios.password_hash
                                              END,
                            nombre_completo = EXCLUDED.nombre_completo
                """),
                params,
            )

        conn.commit()


def health_check() -> bool:
    """Verifica que la conexión a la BD esté disponible."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Error de conexión a la BD: {e}")
        return False


# ── Punto de entrada: inicialización directa ─────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_database()
    safe_url = DATABASE_URL.split("@")[-1]  # ocultar credenciales
    print(f"✅ [AdamoServices] Base de datos (PostgreSQL) inicializada. Host: {safe_url}")
