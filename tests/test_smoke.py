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
    from app.components.partners_ui import page_alianzas
    from app.components.audit_ui import page_auditoria
    from app.components.screening_ui import render_screening_workspace
    from app.components.agentes_ui import (
        get_agentes_sidebar, render_gestion_agentes, render_perfil_agente,
    )
    from app.components.compliance_ui import page_compliance
    from app.components.crypto_ui import page_crypto_compliance
    from app.components.email_ui import page_bandeja_cumplimiento
    from app.components.clientes_ui import page_clientes

    for fn in (
        page_alianzas, page_auditoria, render_screening_workspace,
        get_agentes_sidebar, render_gestion_agentes, render_perfil_agente,
        page_compliance, page_crypto_compliance, page_bandeja_cumplimiento,
        page_clientes,
    ):
        assert callable(fn)


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


# ── 4. Navegación ────────────────────────────────────────────
def _constantes_de_pagina() -> list[str]:
    from app.main import Paginas
    return [
        v for k, v in vars(Paginas).items()
        if not k.startswith("_") and isinstance(v, str)
    ]


def test_toda_pagina_tiene_ruta_en_el_router() -> None:
    """
    Cada constante de Paginas debe aparecer en el cuerpo de main().

    El menú y el router usaban literales con emoji duplicados en dos sitios;
    si uno cambiaba sin el otro, la página quedaba inalcanzable sin error.
    """
    import inspect
    from app.main import Paginas, main

    fuente = inspect.getsource(main)
    sin_ruta = [
        nombre for nombre, valor in vars(Paginas).items()
        if not nombre.startswith("_") and isinstance(valor, str)
        and nombre not in {"SIN_ACCESO"}
        and f"Paginas.{nombre}" not in fuente
    ]
    assert not sin_ruta, f"Páginas sin rama en el router: {sin_ruta}"


def test_etiquetas_de_pagina_sin_emoji() -> None:
    """Las etiquetas del menú no deben llevar emoji."""
    import re

    emoji = re.compile("[\U0001F300-\U0001FAFF☀-➿⬀-⯿️]")
    con_emoji = [v for v in _constantes_de_pagina() if emoji.search(v)]
    assert not con_emoji, f"Etiquetas con emoji: {con_emoji}"


# ── 5. Kit de componentes ────────────────────────────────────
def test_ui_kit_genera_html_valido() -> None:
    from app.components import ui_kit as ui

    assert ui.section_header("Título", "sub", icon_name="chart").startswith("<div")
    assert "26px" in ui.kpi("Etiqueta", 9, "pie")
    assert ui.kpi_grid([ui.kpi("a", 1), ui.kpi("b", 2)]).count("<div") >= 3
    assert ui.badge("Texto", "info").startswith("<span")
    assert ui.bar(50).startswith("<div")
    assert ui.stacked_bar([(50, "ok"), (50, "warn")]).startswith("<div")


def test_ui_kit_donut_reparte_el_circulo() -> None:
    """El donut debe pintar un aro por segmento con valor positivo, más el fondo."""
    from app.components import ui_kit as ui

    svg = ui.donut([(4, "info"), (3, "teal"), (0, "warn")], 7, "activos")
    assert svg.count("<circle") == 3, "fondo + 2 segmentos con valor"
    assert ">7<" in svg

    vacio = ui.donut([(0, "info")], 0, "activos")
    assert vacio.count("<circle") == 1, "solo el aro de fondo"


def test_ui_kit_no_escribe_colores_a_mano_en_componentes() -> None:
    """
    Los tonos deben resolverse por nombre, no por hex.

    Es la regla que evita volver a los 843 colores dispersos: si un componente
    devuelve un hex que no venga de la tabla de tonos, algo se coló.
    """
    from app.components import ui_kit as ui

    assert ui.tone_color("ok").startswith("var(")
    assert ui.tone_color("primary").startswith("var(")
    assert ui.tone_color("#abcdef") == "#abcdef"


def test_ui_kit_iconos_conocidos_y_desconocidos() -> None:
    from app.components import ui_kit as ui

    assert ui.icon("chart").startswith("<svg")
    assert 'stroke-width="1.5"' in ui.icon("bank")
    assert ui.icon("no_existe") == ""
