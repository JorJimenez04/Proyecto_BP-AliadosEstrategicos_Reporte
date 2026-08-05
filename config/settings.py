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
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    raise EnvironmentError(
        "DATABASE_URL no está configurada. "
        "Define la URL de PostgreSQL en el archivo .env (desarrollo) "
        "o en las Variables de Railway (producción)."
    )

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
            "(APP_ENV=production):\n"
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
    # ── Roles canónicos nuevos ────────────────────────────
    SUPER_ADMIN       = "super_admin"      # Acceso total
    COMPLIANCE        = "compliance"       # Compliance 360
    MANAGER_OPS       = "manager_ops"      # Pagos / Gestión Humana / Chief Operating Officer / Gerente de Operaciones / COO 
    MANAGER_COMERCIAL = "manager_comercial"
    MANAGER_LEGAL     = "manager_legal"
    AGENTE            = "agente"           # Senior y Junior (mismo rol)
    CIC               = "cic"              # Comercial Inteligencia Comercial — mismos permisos que 'comercial'

    # ── Aliases legacy — mantener para no romper código existente ──
    ADMIN             = "admin"
    COMERCIAL         = "comercial"
    AGENTE_KYC        = "agente_kyc"
    AGENTE_OPERATIVO  = "agente_operativo"
    CONSULTA          = "consulta"

    # ── Lista completa para selectores de UI ─────────────
    ALL = [
        SUPER_ADMIN, COMPLIANCE, MANAGER_OPS,
        MANAGER_COMERCIAL, MANAGER_LEGAL, AGENTE, CIC,
        # legacy
        ADMIN, COMERCIAL, AGENTE_KYC, AGENTE_OPERATIVO, CONSULTA,
    ]

    # ── Conjuntos de permiso ──────────────────────────────

    # Acceso total al sistema
    CAN_ACCESS_ALL = frozenset({
        "super_admin", "admin",
    })

    # Vista completa (compliance 360)
    CAN_VIEW_ALL = frozenset({
        "super_admin", "admin", "compliance",
    })

    # Auditoría
    CAN_VIEW_AUDIT = frozenset({
        "super_admin", "admin", "compliance",
    })

    # Cripto Compliance
    CAN_VIEW_CRYPTO = frozenset({
        "super_admin", "admin", "compliance",
    })

    # Gestión de Alianzas — ver
    CAN_VIEW_ALIANZAS = frozenset({
        "super_admin", "admin", "compliance",
        "manager_ops", "manager_comercial", "manager_legal",
        "cic",
        "comercial",  # legacy
    })

    # Gestión de Alianzas — editar (sin eliminar)
    CAN_EDIT_PARTNERS = frozenset({
        "super_admin", "admin", "compliance", "manager_ops",
        "cic",
        "comercial", "agente_kyc", "agente_operativo",  # legacy
    })

    # Gestión de Alianzas — alta de partner
    CAN_CREATE_PARTNERS = frozenset({
        "super_admin", "admin", "compliance", "manager_ops",
        "cic",
        "comercial",  # legacy
    })

    # Gestión de Alianzas — eliminar (solo super_admin)
    CAN_DELETE = frozenset({
        "super_admin", "admin",
    })
    CAN_DELETE_PARTNERS = frozenset({
        "super_admin", "admin",
    })

    # Campos SARLAFT / riesgo
    CAN_EDIT_SARLAFT = frozenset({
        "super_admin", "admin", "agente_kyc",
    })
    CAN_EDIT_COMPLIANCE = frozenset({
        "super_admin", "admin", "compliance",
    })
    CAN_EDIT_JURISDICTIONS = frozenset({
        "super_admin", "admin", "compliance",
    })

    # KPIs de gestión
    CAN_REGISTER_KPIS = frozenset({
        "super_admin", "admin", "compliance", "manager_ops",
        "cic",
        "comercial",  # legacy
    })

    # Gestión de Agentes — ver equipos completos
    # 'cic' entra en solo lectura: necesita conocer la operación, pero no
    # edita colaboradores (no está en CAN_EDIT_AGENTES).
    # Es una divergencia deliberada respecto al rol legacy 'comercial'.
    CAN_VIEW_AGENTES = frozenset({
        "super_admin", "admin", "compliance", "manager_ops",
        "cic",
    })

    # Gestión de Agentes — editar/crear colaboradores
    CAN_EDIT_AGENTES = frozenset({
        "super_admin", "admin", "compliance", "manager_ops",
    })

    # Centro Documental — cualquier acceso
    CAN_VIEW_DOCS = frozenset({
        "super_admin", "admin", "compliance",
        "manager_ops", "manager_comercial", "manager_legal",
        "cic",
        "comercial", "consulta",  # legacy
    })

    # Centro Documental — crear/editar documentos
    CAN_EDIT_DOCS = frozenset({
        "super_admin", "admin", "compliance",
    })

    # Centro Documental — carpetas por rol restringido
    CARPETAS_COMERCIAL = frozenset({
        "Empresariales",
    })
    CARPETAS_LEGAL = frozenset({
        "Empresariales", "Contratos", "Actas y Formatos", "Governanza",
    })
    CARPETAS_OPS = frozenset({
        "Empresariales", "Contratos", "Actas y Formatos",
        "Capacitacion", "Onboarding",
    })
    # Carpetas operativas para 'cic'. Excluye deliberadamente:
    #   Politicas, Governanza, Matrices  → documentación de compliance y junta
    # Para ampliar o recortar el acceso, editar solo este conjunto.
    CARPETAS_CIC = frozenset({
        "Empresariales", "Contratos", "Actas y Formatos",
        "Onboarding", "Capacitacion",
        "Procesos y Procedimientos", "Manuales", "Tecnologia",
    })

    # Gestión de usuarios del sistema
    CAN_MANAGE_USERS = frozenset({
        "super_admin", "admin",
    })

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

# ── Jurisdicciones de Operación ──────────────────────────────────
class Jurisdicciones:
    """
    Catálogo de países relevantes para Banking Partners latinoamericanos.
    Incluye países de alto riesgo GAFI / SAGRILAFT para cálculo automático
    del puntaje_riesgo.
    """

    ALL: list[str] = [
        # ─ Latinoamérica ────────────────────────────────
        "🇨🇴 Colombia",
        "🇧🇷 Brasil",
        "🇲🇽 México",
        "🇦🇷 Argentina",
        "🇨🇱 Chile",
        "🇵🇪 Perú",
        "🇪🇨 Ecuador",
        "🇧🇴 Bolivia",
        "🇵🇾 Paraguay",
        "🇺🇾 Uruguay",
        "🇻🇪 Venezuela",
        "🇨🇷 Costa Rica",
        "🇬🇹 Guatemala",
        "🇭🇳 Honduras",
        "🇸🇻 El Salvador",
        "🇳🇮 Nicaragua",
        "🇨🇺 Cuba",
        "🇩🇴 República Dominicana",
        "🇭🇹 Haití",
        # ─ Centros financieros / Offshore ───────────────────
        "🇵🇦 Panamá",
        "🇰🇾 Islas Caimán",
        "🇧🇸 Bahamas",
        "🇧🇲 Bermuda",
        "🇻🇬 Islas Vírgenes (UK)",
        "🇦🇼 Aruba",
        "🇵🇦 Panamá (ZLC)",
        # ─ Norteamérica y Europa ────────────────────────
        "🇺🇸 Estados Unidos",
        "🇨🇦 Canadá",
        "🇪🇸 España",
        "🇬🇧 Reino Unido",
        "🇵🇹 Portugal",
        "🇩🇪 Alemania",
        "🇳🇱 Países Bajos",
        "🇨🇭 Suiza",
        # ─ Alto riesgo GAFI / black list ───────────────────
        "🇮🇷 Irán",
        "🇰🇵 Corea del Norte",
        "🇲🇲 Myanmar",
    ]

    # ── Capas de riesgo por jurisdicción ─────────────────────
    #
    # Antes existía un único conjunto ALTO_RIESGO que fundía tres cosas
    # distintas bajo la etiqueta "GAFI": listados del GAFI, sanciones OFAC y
    # una política interna sobre centros offshore. Afirmar que el GAFI señala
    # a Islas Caimán es falso desde octubre de 2023, y ante una auditoría
    # SARLAFT eso es un hallazgo. Cada capa va ahora por separado, con su
    # fuente, y pesa distinto en el scoring.
    #
    # Última verificación contra fatf-gafi.org: plenaria del 19/06/2026.

    FUENTE_GAFI_VERIFICADA: str = "2026-06-19"

    # Llamado a la acción — contramedidas obligatorias.
    LISTA_NEGRA_GAFI: frozenset[str] = frozenset({
        "🇮🇷 Irán",
        "🇰🇵 Corea del Norte",
        "🇲🇲 Myanmar",
    })

    # Monitoreo intensificado. De las 22 jurisdicciones de la lista gris,
    # estas son las que figuran en el catálogo. Bolivia faltaba: se penalizaba
    # a Haití pero no a Bolivia, estando ambas en la misma lista.
    LISTA_GRIS_GAFI: frozenset[str] = frozenset({
        "🇭🇹 Haití",
        "🇧🇴 Bolivia",
    })

    # Sanciones de OFAC y la UE. Motivo geopolítico, no deficiencia antilavado:
    # ninguno de los dos está en los listados del GAFI.
    SANCIONES_INTERNACIONALES: frozenset[str] = frozenset({
        "🇨🇺 Cuba",
        "🇻🇪 Venezuela",
    })

    # Decisión propia de AdamoServices sobre centros offshore por opacidad
    # societaria. Ninguno está hoy en listas del GAFI — Islas Caimán salió en
    # octubre de 2023 y Bahamas en 2020. Se mantiene la cautela, pero
    # declarada como lo que es y con menos peso que un listado oficial.
    OFFSHORE_POLITICA_INTERNA: frozenset[str] = frozenset({
        "🇰🇾 Islas Caimán",
        "🇧🇸 Bahamas",
        "🇧🇲 Bermuda",
        "🇻🇬 Islas Vírgenes (UK)",
    })

    # Unión de todo lo que penaliza. Se mantiene por compatibilidad con el
    # código existente; para lógica nueva usar la capa concreta.
    ALTO_RIESGO: frozenset[str] = (
        LISTA_NEGRA_GAFI
        | LISTA_GRIS_GAFI
        | SANCIONES_INTERNACIONALES
        | OFFSHORE_POLITICA_INTERNA
    )

    # Etiqueta legible de cada capa, para explicar en la interfaz por qué
    # una jurisdicción penaliza.
    ETIQUETA_CAPA: dict[str, str] = {
        "negra":    "Lista negra GAFI · llamado a la acción",
        "gris":     "Lista gris GAFI · monitoreo intensificado",
        "sancion":  "Sanciones OFAC o UE",
        "offshore": "Restringida por política interna",
    }

    @classmethod
    def capa_de(cls, jurisdiccion: str) -> str | None:
        """Capa a la que pertenece una jurisdicción, o None si no penaliza."""
        if jurisdiccion in cls.LISTA_NEGRA_GAFI:
            return "negra"
        if jurisdiccion in cls.LISTA_GRIS_GAFI:
            return "gris"
        if jurisdiccion in cls.SANCIONES_INTERNACIONALES:
            return "sancion"
        if jurisdiccion in cls.OFFSHORE_POLITICA_INTERNA:
            return "offshore"
        return None


# ── Tipos de Riel de Pago ─────────────────────────────────────
class TiposRiel:
    DISPERSION = "Dispersión"
    RECAUDO    = "Recaudo"
    CRYPTO     = "Crypto"
    MIXTO      = "Mixto"
    NA         = "N/A"

    ALL = [DISPERSION, RECAUDO, CRYPTO, MIXTO, NA]