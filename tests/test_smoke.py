"""
tests/test_smoke.py
Pruebas de humo — no tocan la base de datos.

Objetivo: detectar rupturas de importación, símbolos borrados por error y
regresiones en la matriz de permisos. Es la red de seguridad mínima tras la
limpieza de código muerto.

Uso:
    pytest tests/ -v
"""

from __future__ import annotations

import importlib
import os
import pkgutil

import pytest

# La app exige DATABASE_URL al importar config.settings
os.environ.setdefault("DATABASE_URL", "postgresql://smoke:smoke@localhost:5432/smoke")
os.environ.setdefault("APP_ENV", "development")


# ── 1. Todos los módulos importan ────────────────────────────
# app/webhook.py es un entrypoint aparte que entrypoint.sh arranca en segundo
# plano. Importa Flask, que NO está en requirements.txt — el proceso muere al
# arrancar sin que nadie se entere (se lanza con '&' y no se comprueba).
# Se excluye aquí para que el smoke test no falle por un problema ajeno a la
# limpieza, pero conviene resolverlo: añadir flask a requirements o retirar
# el webhook de entrypoint.sh.
_EXCLUIDOS = {"app.webhook"}


def _modulos() -> list[str]:
    encontrados: list[str] = []
    for paquete in ("app", "db", "config"):
        for mod in pkgutil.walk_packages([paquete], prefix=f"{paquete}."):
            if "__pycache__" in mod.name or mod.name in _EXCLUIDOS:
                continue
            encontrados.append(mod.name)
    return sorted(encontrados)


@pytest.mark.parametrize("nombre", _modulos())
def test_modulo_importa(nombre: str) -> None:
    """Cada módulo debe importarse sin error."""
    importlib.import_module(nombre)


# ── 2. Símbolos que la app necesita en tiempo de ejecución ───
def test_simbolos_criticos_existen() -> None:
    from app.auth.login import require_auth, logout
    from db.repositories.user_repo import UserRepository
    from db.repositories.partner_repo import PartnerRepository

    assert callable(require_auth)
    assert callable(logout)
    # login solo necesita estas dos del repositorio de usuarios
    assert hasattr(UserRepository, "get_by_username")
    assert hasattr(UserRepository, "get_by_id")
    assert hasattr(PartnerRepository, "create")


def test_paginas_del_router_existen() -> None:
    """
    Cada símbolo que main() importa dinámicamente debe existir.

    main() hace los imports dentro de las ramas del router, así que un símbolo
    borrado por error no se detecta hasta que el usuario abre esa página.
    """
    from app.components.partners_ui import page_alianzas                  # noqa: F401
    from app.components.audit_ui import page_auditoria                    # noqa: F401
    from app.components.screening_ui import render_screening_workspace    # noqa: F401
    from app.components.agentes_ui import (                               # noqa: F401
        get_agentes_sidebar, render_gestion_agentes, render_perfil_agente,
    )
    from app.components.compliance_ui import page_compliance              # noqa: F401
    from app.components.crypto_ui import page_crypto_compliance           # noqa: F401
    from app.components.email_ui import page_bandeja_cumplimiento         # noqa: F401
    from app.components.clientes_ui import page_clientes                  # noqa: F401


# ── 3. Matriz de permisos ────────────────────────────────────
def test_rol_cic_replica_a_comercial() -> None:
    """'cic' debe pertenecer exactamente a los mismos conjuntos que 'comercial'."""
    from config.settings import Roles

    excluir = {"CARPETAS_COMERCIAL", "CARPETAS_LEGAL", "CARPETAS_OPS"}
    conjuntos = {
        n: v for n, v in vars(Roles).items()
        if isinstance(v, frozenset) and n not in excluir
    }
    assert conjuntos, "No se encontraron conjuntos de permiso en Roles"

    divergencias = [n for n, c in conjuntos.items() if ("cic" in c) != ("comercial" in c)]
    assert not divergencias, f"cic y comercial divergen en: {divergencias}"


def test_roles_canonicos_declarados() -> None:
    from config.settings import Roles

    for rol in ("super_admin", "compliance", "manager_ops", "manager_comercial",
                "manager_legal", "agente", "cic"):
        assert rol in Roles.ALL, f"Falta '{rol}' en Roles.ALL"


def test_permisos_criticos_restringidos() -> None:
    """Ningún rol operativo debe colarse en los permisos sensibles."""
    from config.settings import Roles

    assert Roles.CAN_MANAGE_USERS == frozenset({"super_admin", "admin"})
    assert Roles.CAN_DELETE_PARTNERS == frozenset({"super_admin", "admin"})
    assert "cic" not in Roles.CAN_EDIT_SARLAFT
    assert "cic" not in Roles.CAN_VIEW_AUDIT
    assert "cic" not in Roles.CAN_VIEW_CRYPTO
    assert "agente" not in Roles.CAN_VIEW_ALIANZAS


def test_validador_de_rol_acepta_todos_los_roles() -> None:
    """El validador Pydantic debe aceptar cualquier rol declarado y rechazar el resto."""
    from config.settings import Roles
    from db.models import UsuarioBase

    for rol in Roles.ALL:
        UsuarioBase(
            username="smoke_user",
            nombre_completo="Smoke Test",
            email="smoke@example.com",
            rol=rol,
        )

    with pytest.raises(Exception):
        UsuarioBase(
            username="smoke_user",
            nombre_completo="Smoke Test",
            email="smoke@example.com",
            rol="rol_que_no_existe",
        )
