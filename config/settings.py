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
import logging as _logging
_log = _logging.getLogger(__name__)

# Valor de desarrollo por defecto — jamás usar en producción
_DEV_FALLBACK_KEY: str = "dev-secret-key-change-in-production"

# Conjunto de claves inseguras/plantilla conocidas
_INSECURE_KEYS: frozenset[str] = frozenset({
    _DEV_FALLBACK_KEY,
    "REEMPLAZAR_CON_SALIDA_DE_token_urlsafe_32",
    "secret", "changeme", "admin", "password", "123456",
})

_MIN_KEY_LEN: int = 43          # token_urlsafe(32) → exactamente 43 chars URL-safe
_raw_secret:  str = os.getenv("SECRET_KEY", "")

if APP_ENV == "production":
    # ── Validación bloqueante: el proceso no puede arrancar sin una clave segura ──
    _sec_errors: list[str] = []
    if not _raw_secret:
        _sec_errors.append(
            "SECRET_KEY no está definida. "
            "Agrégala en las Variables de Entorno del proyecto en Railway."
        )
    elif _raw_secret in _INSECURE_KEYS:
        _sec_errors.append(
            "SECRET_KEY usa un valor de plantilla inseguro. "
            "Genera una nueva con: "
            'python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )
    elif len(_raw_secret) < _MIN_KEY_LEN:
        _sec_errors.append(
            f"SECRET_KEY demasiado corta ({len(_raw_secret)} chars). "
            f"Mínimo requerido: {_MIN_KEY_LEN} chars (token_urlsafe(32))."
        )
    if _sec_errors:
        raise RuntimeError(
            "[AdamoServices] INICIO BLOQUEADO — Configuración de seguridad inválida "
            f"(APP_ENV=production):\n"
            + "\n".join(f"  ✗ {e}" for e in _sec_errors)
        )
    SECRET_KEY: str       = _raw_secret
    SECRET_KEY_IS_DEFAULT: bool = False
else:
    # ── Modo desarrollo: permite el fallback, pero lo registra en logs ──
    SECRET_KEY = _raw_secret if _raw_secret else _DEV_FALLBACK_KEY
    SECRET_KEY_IS_DEFAULT: bool = (not _raw_secret) or (_raw_secret in _INSECURE_KEYS)
    if SECRET_KEY_IS_DEFAULT:
        _log.warning(
            "[AdamoServices] SECRET_KEY usa el valor de desarrollo. "
            "Configure una clave segura antes de desplegar en producción."
        )

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
