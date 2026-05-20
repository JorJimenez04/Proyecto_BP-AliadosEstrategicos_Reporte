"""
scripts/create_comercial_manager.py
Seed script para crear el perfil genérico provisional del rol manager_comercial.

Uso:
    python scripts/create_comercial_manager.py

El script es idempotente: si el usuario ya existe, informa y sale limpiamente.
"""

from __future__ import annotations

import sys
from pathlib import Path

# ── Asegurar que la raíz del proyecto esté en el path ────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt
from sqlalchemy import text
from db.database import get_session

# ── Datos del usuario provisional ────────────────────────────
_USERNAME        = "comercial.manager"
_PASSWORD_PLAIN  = "AdamoComercial2026*"
_NOMBRE_COMPLETO = "Equipo Comercial (Provisional)"
_EMAIL           = "comercial-test@adamopay.com"
_ROL             = "manager_comercial"


def _print_banner(created: bool) -> None:
    sep = "─" * 56
    if created:
        print(f"""
┌{sep}┐
│  ✅  USUARIO CREADO EXITOSAMENTE                       │
├{sep}┤
│  Username   : {_USERNAME:<40}│
│  Contraseña : {_PASSWORD_PLAIN:<40}│
│  Nombre     : {_NOMBRE_COMPLETO:<40}│
│  Email      : {_EMAIL:<40}│
│  Rol        : {_ROL:<40}│
│  Estado     : Activo                                   │
├{sep}┤
│  ⚠️  Solo para pruebas. Cambia la contraseña           │
│     antes de usar en entornos compartidos.             │
└{sep}┘
""")
    else:
        print(f"""
┌{sep}┐
│  ℹ️  USUARIO YA EXISTE — operación cancelada           │
├{sep}┤
│  Username : {_USERNAME:<44}│
│  No se realizaron cambios en la base de datos.         │
└{sep}┘
""")


def create_comercial_manager() -> None:
    # ── Conectar ──────────────────────────────────────────────
    try:
        session = next(get_session())
    except Exception as exc:
        print(f"❌ No se pudo conectar a la base de datos: {exc}")
        sys.exit(1)

    try:
        # ── Verificar existencia previa ───────────────────────
        existing = session.execute(
            text("SELECT id FROM usuarios WHERE username = :u"),
            {"u": _USERNAME},
        ).fetchone()

        if existing:
            _print_banner(created=False)
            return

        # ── Hash bcrypt ───────────────────────────────────────
        password_hash = bcrypt.hashpw(
            _PASSWORD_PLAIN.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")

        # ── Insertar ──────────────────────────────────────────
        session.execute(
            text("""
                INSERT INTO usuarios
                    (username, nombre_completo, email, password_hash, rol, activo)
                VALUES
                    (:username, :nombre_completo, :email, :password_hash, :rol, 1)
            """),
            {
                "username":        _USERNAME,
                "nombre_completo": _NOMBRE_COMPLETO,
                "email":           _EMAIL,
                "password_hash":   password_hash,
                "rol":             _ROL,
            },
        )
        session.commit()
        _print_banner(created=True)

    except Exception as exc:
        session.rollback()
        print(f"❌ Error durante la inserción: {exc}")
        sys.exit(1)

    finally:
        session.close()


if __name__ == "__main__":
    create_comercial_manager()
