"""
config/settings.py
# AdamoServices Partner Manager — Configuración centralizada de la aplicación.
# Lee variables desde el archivo .env usando python-dotenv.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Directorio raíz del proyecto (un nivel arriba de /config)
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar .env desde la raíz del proyecto
load_dotenv(BASE_DIR / ".env")


# ── Aplicación ────────────────────────────────────────────
APP_NAME: str = os.getenv("APP_NAME", "AdamoServices Partner Manager")
APP_ENV: str = os.getenv("APP_ENV", "development")
DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

# ── Base de Datos ─────────────────────────────────────────
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'data' / 'adamoservices.db'}"
)

# Directorio donde se almacena la BD SQLite local
DATA_DIR: Path = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# ── Seguridad ─────────────────────────────────────────────
SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
SESSION_TIMEOUT_MINUTES: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "60"))

# ── Roles del sistema ─────────────────────────────────────
class Roles:
    ADMIN      = "admin"
    COMPLIANCE = "compliance"
    COMERCIAL  = "comercial"
    CONSULTA   = "consulta"

    ALL = [ADMIN, COMPLIANCE, COMERCIAL, CONSULTA]

# ── Pipeline de estados de aliados ───────────────────────
class EstadosAliado:
    PROSPECTO     = "Prospecto"
    CALIFICACION  = "En Calificación"
    ONBOARDING    = "Onboarding"
    ACTIVO        = "Activo"
    SUSPENDIDO    = "Suspendido"
    TERMINADO     = "Terminado"

    ALL = [PROSPECTO, CALIFICACION, ONBOARDING, ACTIVO, SUSPENDIDO, TERMINADO]

    # Transiciones permitidas entre estados
    TRANSICIONES: dict[str, list[str]] = {
        PROSPECTO:    [CALIFICACION, TERMINADO],
        CALIFICACION: [ONBOARDING, TERMINADO],
        ONBOARDING:   [ACTIVO, SUSPENDIDO, TERMINADO],
        ACTIVO:       [SUSPENDIDO, TERMINADO],
        SUSPENDIDO:   [ACTIVO, TERMINADO],
        TERMINADO:    [],
    }

# ── Tipos de Aliado ───────────────────────────────────────
class TiposAliado:
    BANKING_PARTNER   = "Banking Partner"
    ALIADO_ESTRATEGICO = "Aliado Estratégico"
    CORRESPONSAL      = "Corresponsal Bancario"
    PROVEEDOR         = "Proveedor de Servicios"

    ALL = [BANKING_PARTNER, ALIADO_ESTRATEGICO, CORRESPONSAL, PROVEEDOR]

# ── Niveles de Riesgo SARLAFT ─────────────────────────────
class NivelesRiesgo:
    BAJO     = "Bajo"
    MEDIO    = "Medio"
    ALTO     = "Alto"
    MUY_ALTO = "Muy Alto"

    ALL = [BAJO, MEDIO, ALTO, MUY_ALTO]

# ── Estados SARLAFT ───────────────────────────────────────
class EstadosSARLAFT:
    AL_DIA     = "Al Día"
    PENDIENTE  = "Pendiente"
    EN_REVISION = "En Revisión"
    VENCIDO    = "Vencido"

    ALL = [AL_DIA, PENDIENTE, EN_REVISION, VENCIDO]
