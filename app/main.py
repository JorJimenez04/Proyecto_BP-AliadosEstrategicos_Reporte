"""
app/main.py
Entry point principal de AdamoServices Partner Manager.
Actualizado con métricas de gestión corporativa y operativa.
"""

from __future__ import annotations

import streamlit as st
from datetime import datetime
import sys
from pathlib import Path
import os

# Asegurar que la raíz del proyecto esté en el path ANTES de cualquier import local
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import (
    APP_NAME, APP_ENV, Roles, SECRET_KEY_IS_DEFAULT
)
from db.database import get_session

# ── Rutas de assets ──────────────────────────────────────────
_STATIC_DIR   = Path(__file__).resolve().parent / "static"
_LOGOS_DIR    = _STATIC_DIR / "img" / "logos"
_IMG_FORMATS  = (".png", ".jpg", ".jpeg", ".webp", ".svg")

def _get_logos() -> tuple[Path | None, Path | None]:
    logo_sidebar = logo_icono = None
    for ext in _IMG_FORMATS:
        if not logo_sidebar and (_LOGOS_DIR / f"logo_adamo_blanco{ext}").exists():
            logo_sidebar = _LOGOS_DIR / f"logo_adamo_blanco{ext}"
        if not logo_icono and (_LOGOS_DIR / f"logo_adamo_color{ext}").exists():
            logo_icono = _LOGOS_DIR / f"logo_adamo_color{ext}"
    if not logo_sidebar and _LOGOS_DIR.exists():
        all_imgs: list[Path] = sorted(p for ext in _IMG_FORMATS for p in _LOGOS_DIR.glob(f"*{ext}"))
        if all_imgs: logo_sidebar = all_imgs[0]
        if len(all_imgs) >= 2: logo_icono = all_imgs[1]
    return logo_sidebar, logo_icono

# ── Configuración de página ───────────────────────────────────
st.set_page_config(
    page_title="Adamo Services | Intelligence Hub",
    page_icon="🔹",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS corporativo AdamoServices (Tu diseño original) ───────
st.markdown("""
<style>
    .stApp { color: #111827; }
    .stApp p, .stApp span, .stApp div { color: #d1d5db; }
    .stApp label { color: #d1d5db !important; font-size: 0.85rem !important; }
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: #f9fafb !important; }
    [data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #293056; }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #5fe9d0 0%, #7839ee 100%);
        color: #101323 !important; font-weight: 700; border: none; border-radius: 8px;
    }
    .section-title {
        font-size: 0.75rem; font-weight: 700; color: #5fe9d0;
        text-transform: uppercase; letter-spacing: 1.2px;
        border-bottom: 1px solid #293056; padding-bottom: 6px; margin-bottom: 14px;
    }
    .badge { display:inline-block; padding:3px 12px; border-radius:20px; font-size:0.75rem; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ── Callback del radio: al cambiar de sección borra el agente activo ─────────
def _on_nav_radio_change() -> None:
    st.session_state.pop("nav_agente", None)


# ── Sidebar Navegación ────────────────────────────────────────
def sidebar(user: dict) -> tuple[str, str | None]:
    """
    Retorna (page, agente_username | None).

    page puede ser:
      "� Core Operations" | "🤝 Partners" | "➕ Nuevo Partner" |
      "📋 Log de Auditoría" | "👤 Perfil Agente"
    agente_username solo está definido cuando page == "👤 Perfil Agente".
    """
    from app.components.agentes_ui import get_agentes_sidebar

    _logo_sidebar, _logo_icono = _get_logos()
    if _logo_icono:
        try:
            _icon_bytes = _logo_icono.read_bytes()
            st.logo(
                _logo_sidebar.read_bytes() if _logo_sidebar else _icon_bytes,
                icon_image=_icon_bytes,
                size="large",
            )
        except:
            pass

    agente_seleccionado: str | None = None

    with st.sidebar:
        if _logo_sidebar:
            try:
                st.image(_logo_sidebar.read_bytes(), width=220)
            except:
                pass

        st.markdown(
            f"<span style='color:#9ca3af; font-size:0.82rem;'>👤 {user['nombre_completo']}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='border-bottom:1px solid #293056;margin:10px 0 14px;'></div>",
            unsafe_allow_html=True,
        )

        # ── Navegación principal ──────────────────────────────
        # Clave interna _radio_nav — nunca se escribe desde fuera del widget.
        # on_change limpia nav_agente cuando el usuario vuelve al radio.
        _nav_opts = ["🤝 Gestión de Alianzas"]
        if user.get("rol") in {"admin", "compliance"}:
            _nav_opts.append("📋 Log de Auditoría")
        if user.get("rol") in Roles.CAN_VIEW_AGENTES:
            _nav_opts.append("👥 Gestión de Agentes")
        if user.get("rol") in {"admin", "compliance", "comercial", "consulta"}:
            _nav_opts.append("📚 Centro Documental")
        nav_choice = st.radio(
            "Navegación",
            options=_nav_opts,
            label_visibility="collapsed",
            key="_radio_nav",
            on_change=_on_nav_radio_change,
        )

        # ── Equipos Operativos (expander) ─────────────────────
        _equipos_data = get_agentes_sidebar()
        st.markdown(
            "<div style='border-top:1px solid #293056;margin:14px 0 10px;'></div>",
            unsafe_allow_html=True,
        )
        with st.expander("🏢 Equipos Operativos", expanded=False):
            for equipo_nombre, equipo_data in _equipos_data.items():
                equipo_color = equipo_data["color"]
                st.markdown(
                    f"<p style='color:{equipo_color};font-size:0.72rem;font-weight:700;"
                    f"text-transform:uppercase;letter-spacing:1px;"
                    f"margin:10px 0 6px;'>{equipo_nombre}</p>",
                    unsafe_allow_html=True,
                )
                for agente in equipo_data["agentes"]:
                    if st.button(
                        f"  {agente['nombre']}",
                        key=f"btn_agente_{agente['username']}",
                        use_container_width=True,
                    ):
                        # Solo escribimos en nav_agente, nunca en _radio_nav
                        st.session_state["nav_agente"] = agente["username"]

        # Derivar página activa: agente tiene precedencia sobre el radio
        if st.session_state.get("nav_agente"):
            agente_seleccionado = st.session_state["nav_agente"]
            page = "👤 Perfil Agente"
        else:
            page = nav_choice

        st.markdown(
            "<div style='border-top:1px solid #293056;margin:14px 0 10px;'></div>",
            unsafe_allow_html=True,
        )
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            from app.auth.login import logout as _auth_logout
            _auth_logout()

    return page, agente_seleccionado


# ── Router Principal ──────────────────────────────────────────
def main():
    from app.auth.login import require_auth
    user = require_auth()

    page, agente_username = sidebar(user)

    if page == "🤝 Gestión de Alianzas":
        from app.components.partners_ui import page_alianzas
        page_alianzas(user)
    elif page == "📋 Log de Auditoría":
        if user.get("rol") not in {"admin", "compliance"}:
            st.error("🚫 Acceso Denegado. No tienes permisos para ver el Log de Auditoría.")
            st.stop()
        from app.components.audit_ui import page_auditoria
        page_auditoria(user)
    elif page == "👥 Gestión de Agentes":
        if user.get("rol") not in Roles.CAN_VIEW_AGENTES:
            st.error("🚫 Acceso Denegado. No tienes permisos para acceder a Gestión de Agentes.")
            st.stop()
        from app.components.agentes_ui import render_gestion_agentes
        render_gestion_agentes(user)
    elif page == "\U0001f4da Centro Documental":
        from app.components.compliance_ui import page_compliance
        page_compliance(user)
    elif page == "�👤 Perfil Agente" and agente_username:
        from app.components.agentes_ui import render_perfil_agente
        render_perfil_agente(agente_username, user=user)


if __name__ == "__main__":
    main()