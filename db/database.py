"""
db/database.py
Gestor de conexión a la base de datos — AdamoServices Partner Manager.
Soporta SQLite (desarrollo) y PostgreSQL (producción - Railway) vía SQLAlchemy.
Ejecutar directamente para inicializar el esquema: python -m db.database
"""

import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool, QueuePool

from config.settings import DATABASE_URL, BASE_DIR, DEBUG

logger = logging.getLogger(__name__)

_IS_POSTGRES = DATABASE_URL.startswith(("postgresql", "postgres"))

# ── Motor SQLAlchemy ──────────────────────────────────────────
# Railway / PostgreSQL: pool de conexiones eficiente.
# SQLite local: NullPool (no requiere pool, evita problemas de threading).
if _IS_POSTGRES:
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
else:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
        echo=DEBUG,
    )

# ── Activar WAL y claves foráneas en SQLite ───────────────────
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if not _IS_POSTGRES:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


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
    Crea las tablas, índices y triggers si no existen.
    Compatible con SQLite (desarrollo) y PostgreSQL (producción/Railway).
    """
    migration_file = BASE_DIR / "db" / "migrations" / "001_initial_schema.sql"

    if not migration_file.exists():
        raise FileNotFoundError(f"Script de migración no encontrado: {migration_file}")

    backend = "PostgreSQL" if _IS_POSTGRES else "SQLite"
    logger.info(f"[AdamoServices] Inicializando base de datos ({backend})...")

    sql_script = migration_file.read_text(encoding="utf-8")

    # PostgreSQL soporta IF NOT EXISTS en DDL — ejecutar en bloque único
    # SQLite también lo acepta, pero lo dividimos por sentencia para robustez
    with engine.connect() as conn:
        statements = [s.strip() for s in sql_script.split(";") if s.strip()]
        for statement in statements:
            try:
                conn.execute(text(statement))
            except Exception as e:
                logger.warning(f"Sentencia omitida (probablemente ya existe): {e}")
        conn.commit()

    # Actualizar el hash de la password del admin seed
    _seed_admin_user()

    logger.info("[AdamoServices] Base de datos inicializada correctamente.")


def _seed_admin_user() -> None:
    """
    Reemplaza el placeholder del admin con un hash bcrypt real
    tomando la password de las variables de entorno.
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

    with engine.connect() as conn:
        conn.execute(
            text("""
                UPDATE usuarios
                SET password_hash = :hash,
                    email         = :email,
                    nombre_completo = :nombre
                WHERE username = :username
                  AND password_hash = 'PLACEHOLDER_HASH'
            """),
            {
                "hash":     password_hash,
                "email":    admin_email,
                "nombre":   admin_name,
                "username": admin_username,
            }
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
    backend = "PostgreSQL" if _IS_POSTGRES else "SQLite"
    safe_url = DATABASE_URL if not _IS_POSTGRES else DATABASE_URL.split("@")[-1]  # ocultar credenciales
    print(f"✅ [AdamoServices] Base de datos ({backend}) inicializada. Host: {safe_url}")
