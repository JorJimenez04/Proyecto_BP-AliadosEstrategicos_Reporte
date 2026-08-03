"""
scripts/create_cic_sergio.py
Seed script para crear el perfil de Sergio García con rol CIC.

El rol 'cic' replica los permisos del rol comercial (legacy):
ver/crear/editar partners, registrar KPIs, Centro Documental y Gestión de Clientes.

Uso:
    python scripts/create_cic_sergio.py
    python scripts/create_cic_sergio.py --database-url postgresql://usuario:clave@host:puerto/base

Base de datos destino (orden de precedencia):
    1. --database-url <url>
    2. Variable de entorno DATABASE_PUBLIC_URL
    3. DATABASE_URL del .env

Requisito: aplicar antes la migración db/migrations/034_rol_cic.sql
(amplía el CHECK constraint de usuarios.rol con 'cic').

El script es idempotente: si el usuario ya existe, informa y sale limpiamente.
"""

from __future__ import annotations

import sys
from pathlib import Path

# ── Asegurar que la raíz del proyecto esté en el path ────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt
from sqlalchemy import text
from scripts._db_target import crear_engine

# ── Datos del usuario ────────────────────────────────────────
_USERNAME        = "sergio.garcia"
_PASSWORD_PLAIN  = "AdamoCIC2026*"
_NOMBRE_COMPLETO = "Sergio García"
_EMAIL           = "sergio.garcia@holdingsbpo.com"
_ROL             = "cic"


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
│  ⚠️  Comparte la contraseña por canal seguro y pide    │
│     que la cambie en el primer inicio de sesión.       │
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


def create_cic_sergio() -> None:
    # ── Conectar ──────────────────────────────────────────────
    engine, destino = crear_engine()
    print(f"🎯 Destino : {destino}")

    try:
        with engine.begin() as conn:
            # ── Verificar existencia previa (username o email) ────
            existing = conn.execute(
                text("SELECT id FROM usuarios WHERE username = :u OR email = :e"),
                {"u": _USERNAME, "e": _EMAIL},
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
            conn.execute(
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
        _print_banner(created=True)

    except Exception as exc:
        print(f"❌ Error durante la inserción: {exc}")
        print("   Si el error menciona 'usuarios_rol_check', aplica primero:")
        print("   python scripts/apply_034_rol_cic.py --database-url <misma-url>")
        sys.exit(1)


if __name__ == "__main__":
    create_cic_sergio()
