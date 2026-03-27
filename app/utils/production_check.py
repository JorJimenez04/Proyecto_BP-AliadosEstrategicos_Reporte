"""
app/utils/production_check.py
Validación de seguridad pre-arranque para entornos de producción.

Dos modos de uso:
  1. CLI / entrypoint.sh  → run_checks()         imprime errores y llama sys.exit(1)
  2. Código Python        → raise_if_insecure()  lanza RuntimeError (testeable)

Controles aplicados (GAFI R.1 / CSBF Circular 027):
  - SECRET_KEY: mínimo 43 chars (≈ 32 bytes URL-safe, 256 bits de entropía)
  - ADMIN_PASSWORD: mínimo 16 chars + complejidad (4 clases de caracteres)
  - DATABASE_URL: debe apuntar a PostgreSQL, no a SQLite
  - Variables obligatorias presentes: ADMIN_USERNAME, ADMIN_EMAIL
"""

import os
import re
import sys
import logging

logger = logging.getLogger(__name__)

# ── Umbrales de seguridad ─────────────────────────────────────────
_MIN_SECRET_KEY_LEN  = 43   # token_urlsafe(32) → exactamente 43 chars
_MIN_PASSWORD_LEN    = 16   # CSBF Circular 027 / GAFI R.1

# ── Valores inseguros conocidos (jamás en producción) ─────────────
_INSECURE_SECRETS: set[str] = {
    "dev-secret-key-change-in-production",
    "REEMPLAZAR_CON_SALIDA_DE_token_urlsafe_32",
    "secret",
    "changeme",
    "admin",
    "password",
    "123456",
}

_INSECURE_PASSWORDS: set[str] = {
    "Admin@AdamoServices2025!",          # valor por defecto de desarrollo
    "Compliance2026",                    # valor por defecto del .env.example
    "REEMPLAZAR_CON_PASSWORD_DE_ALTA_ENTROPIA",
    "admin",
    "password",
    "123456",
    "changeme",
}

# ── Reglas de complejidad de contraseña ──────────────────────────
_PASSWORD_RULES: list[tuple[str, str]] = [
    (r"[A-Z]",                              "al menos una letra MAYÚSCULA"),
    (r"[a-z]",                              "al menos una letra minúscula"),
    (r"\d",                                 "al menos un dígito (0-9)"),
    (r"[!@#$%^&*()\-_=+\[\]{};:'\",.<>?/`~\\|]", "al menos un símbolo especial"),
]


# ── Helpers de validación ────────────────────────────────────────

def _check_secret_key() -> list[str]:
    """Valida entropía mínima de SECRET_KEY (256 bits / 43 chars URL-safe)."""
    errors: list[str] = []
    key = os.getenv("SECRET_KEY", "")

    if not key:
        return ["  ✗ SECRET_KEY no está definida."]

    if key in _INSECURE_SECRETS:
        errors.append(
            "  ✗ SECRET_KEY usa un valor de plantilla inseguro. "
            "Genera una nueva con:\n"
            "      python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )

    if len(key) < _MIN_SECRET_KEY_LEN:
        errors.append(
            f"  ✗ SECRET_KEY demasiado corta ({len(key)} chars). "
            f"Mínimo requerido: {_MIN_SECRET_KEY_LEN} chars (token_urlsafe(32))."
        )

    return errors


def _check_admin_password() -> list[str]:
    """Valida longitud + complejidad de ADMIN_PASSWORD (CSBF / GAFI R.1)."""
    errors: list[str] = []
    pwd = os.getenv("ADMIN_PASSWORD", "")

    if not pwd:
        return ["  ✗ ADMIN_PASSWORD no está definida."]

    if pwd in _INSECURE_PASSWORDS:
        errors.append(
            "  ✗ ADMIN_PASSWORD usa un valor por defecto inseguro. "
            "Establece una contraseña única para este entorno."
        )

    if len(pwd) < _MIN_PASSWORD_LEN:
        errors.append(
            f"  ✗ ADMIN_PASSWORD demasiado corta ({len(pwd)} chars). "
            f"Mínimo requerido: {_MIN_PASSWORD_LEN} caracteres (Circular 027)."
        )

    for pattern, description in _PASSWORD_RULES:
        if not re.search(pattern, pwd):
            errors.append(f"  ✗ ADMIN_PASSWORD requiere {description}.")

    return errors


def _check_database_url() -> list[str]:
    """Verifica que DATABASE_URL apunte a PostgreSQL, no a SQLite."""
    errors: list[str] = []
    db_url = os.getenv("DATABASE_URL", "")

    if not db_url:
        return ["  ✗ DATABASE_URL no está definida."]

    if db_url.startswith("sqlite"):
        errors.append(
            "  ✗ DATABASE_URL apunta a SQLite en producción. "
            "Provisiona un PostgreSQL en Railway y actualiza la variable."
        )

    return errors


def _check_required_vars() -> list[str]:
    """Verifica presencia de variables obligatorias sin validar su valor."""
    errors: list[str] = []
    for var in ("ADMIN_USERNAME", "ADMIN_EMAIL"):
        if not os.getenv(var):
            errors.append(f"  ✗ {var} no está definida.")
    return errors


def _collect_errors() -> list[str]:
    """Ejecuta todos los controles y retorna la lista consolidada de errores."""
    errors: list[str] = []
    errors += _check_secret_key()
    errors += _check_admin_password()
    errors += _check_database_url()
    errors += _check_required_vars()
    return errors


# ── API pública ──────────────────────────────────────────────────

def raise_if_insecure() -> None:
    """
    Valida la configuración de producción y lanza RuntimeError si hay fallos.

    Uso recomendado al inicio de app/main.py en entornos de producción:

        from app.utils.production_check import raise_if_insecure
        if os.getenv("APP_ENV") == "production":
            raise_if_insecure()
    """
    errors = _collect_errors()
    if errors:
        detail = "\n".join(errors)
        raise RuntimeError(
            f"\n{'═' * 60}\n"
            f"🚨  ADAMOSERVICES — CONFIGURACIÓN DE PRODUCCIÓN INSEGURA\n"
            f"{'═' * 60}\n"
            f"{detail}\n"
            f"{'═' * 60}\n"
            f"Corrige las variables en Railway → Service → Variables.\n"
        )


def run_checks() -> None:
    """
    Ejecuta todas las validaciones de seguridad.
    Imprime errores en stderr y llama sys.exit(1) si alguna falla.
    Invocada desde entrypoint.sh antes de arrancar Streamlit.
    """
    logging.basicConfig(level=logging.WARNING)
    try:
        raise_if_insecure()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    print("✅ [AdamoServices] Validación de seguridad OK — iniciando servidor.")


if __name__ == "__main__":
    run_checks()
