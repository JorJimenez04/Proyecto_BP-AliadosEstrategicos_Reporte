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

    # Los conjuntos ya no se escriben aquí: se derivan de data/listas_riesgo.json
    # cruzando los códigos ISO con la tabla de equivalencias. Mantenerlos a mano
    # en formato con emoji impedía casarlos con las publicaciones del GAFI y de
    # OFAC, que usan nombres en inglés, y obligaba a actualizar dos sitios.

    @classmethod
    def _derivar(cls, clave_capa: str) -> frozenset[str]:
        """Valores del catálogo cuyo país figura en una capa del dataset."""
        from config.jurisdicciones_legacy import a_iso3
        from config.listas_riesgo import capas

        capa = capas().get(clave_capa)
        if not capa:
            return frozenset()
        return frozenset(
            v for v in cls.ALL
            if (iso := a_iso3(v)) and iso in capa.paises
        )

    @classmethod
    def capa_de(cls, jurisdiccion: str) -> str | None:
        """
        Clave de la capa más severa de una jurisdicción, o None si no penaliza.

        Un país puede figurar en varias: Venezuela está en la lista gris del
        GAFI y además tiene sanciones de OFAC. Para el cálculo manda la peor.
        """
        from config.jurisdicciones_legacy import a_iso3
        from config.listas_riesgo import capa_dominante

        iso = a_iso3(jurisdiccion)
        if not iso:
            return None
        capa = capa_dominante(iso)
        return capa.clave if capa else None

    @classmethod
    def peso_de(cls, jurisdiccion: str) -> int:
        """Puntos que aporta una jurisdicción al puntaje de riesgo."""
        from config.jurisdicciones_legacy import a_iso3
        from config.listas_riesgo import peso_de as _peso

        iso = a_iso3(jurisdiccion)
        return _peso(iso) if iso else 0

    @classmethod
    def capas_de(cls, jurisdiccion: str) -> list[str]:
        """
        Todas las capas en que figura una jurisdicción, de más a menos severa.

        Para explicar al usuario por qué penaliza: Siria aparece a la vez en
        la lista gris del GAFI y en el programa integral de OFAC.
        """
        from config.jurisdicciones_legacy import a_iso3
        from config.listas_riesgo import capas_de as _capas

        iso = a_iso3(jurisdiccion)
        return [c.clave for c in _capas(iso)] if iso else []

    @classmethod
    def etiqueta_capa(cls, clave: str) -> str:
        from config.listas_riesgo import capas
        capa = capas().get(clave)
        return capa.etiqueta if capa else clave

    @classmethod
    def fuente_verificada(cls) -> str:
        from config.listas_riesgo import verificado
        return verificado()


# ── Conjuntos derivados del dataset ───────────────────────────
# Se calculan una vez al importar, cruzando data/listas_riesgo.json con la
# tabla de equivalencias. Quedan como atributos normales para no romper el
# código que ya los consultaba.
Jurisdicciones.LISTA_NEGRA_GAFI = Jurisdicciones._derivar("gafi_negra")
Jurisdicciones.LISTA_GRIS_GAFI = Jurisdicciones._derivar("gafi_gris")
Jurisdicciones.SANCIONES_INTERNACIONALES = Jurisdicciones._derivar("ofac_integral")
Jurisdicciones.OFFSHORE_POLITICA_INTERNA = Jurisdicciones._derivar("politica_interna")

# Unión de todo lo que penaliza. Se mantiene por compatibilidad; para lógica
# nueva usar Jurisdicciones.capa_de(), que distingue la severidad.
Jurisdicciones.ALTO_RIESGO = (
    Jurisdicciones.LISTA_NEGRA_GAFI
    | Jurisdicciones.LISTA_GRIS_GAFI
    | Jurisdicciones.SANCIONES_INTERNACIONALES
    | Jurisdicciones.OFFSHORE_POLITICA_INTERNA
)


# ── Tipos de Riel de Pago ─────────────────────────────────────
class TiposRiel:
    DISPERSION = "Dispersión"
    RECAUDO    = "Recaudo"
    CRYPTO     = "Crypto"
    MIXTO      = "Mixto"
    NA         = "N/A"

    ALL = [DISPERSION, RECAUDO, CRYPTO, MIXTO, NA]