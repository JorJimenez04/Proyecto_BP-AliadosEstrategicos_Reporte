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

## ── CSS corporativo AdamoServices (Tu diseño original) ───────
#st.markdown("""
#<style>
#    .stApp { color: #111827; }
#    .stApp p, .stApp span, .stApp div { color: #d1d5db; }
#    .stApp label { color: #d1d5db !important; font-size: 0.85rem !important; }
#    .stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: #f9fafb !important; }
#    [data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #293056; }
#    .stButton > button[kind="primary"] {
#        background: linear-gradient(135deg, #5fe9d0 0%, #7839ee 100%);
#        color: #101323 !important; font-weight: 700; border: none; border-radius: 8px;
#    }
#    .section-title {
#        font-size: 0.75rem; font-weight: 700; color: #5fe9d0;
#        text-transform: uppercase; letter-spacing: 1.2px;
#        border-bottom: 1px solid #293056; padding-bottom: 6px; margin-bottom: 14px;
#    }
#    .badge { display:inline-block; padding:3px 12px; border-radius:20px; font-size:0.75rem; font-weight:700; }
#</style>
#""", unsafe_allow_html=True)
st.markdown("""
<style>
/* ═══════════════════════════════════════════════════════════════
   ADAMO RISK — Design System v2
   Extraído de Lovable · Inter + JetBrains Mono · Dark theme
═══════════════════════════════════════════════════════════════ */

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── Tokens de color ──────────────────────────────────────── */
:root {
  --bg:              #0d0e14;
  --bg-card:         #12141c;
  --bg-card-raised:  #151720;
  --bg-overlay:      #1a1d28;
  --bg-sidebar:      #0a0b11;

  --border:          #1e2130;
  --border-hover:    rgba(120,87,255,0.25);

  --fg:              #f0f1f5;
  --fg-muted:        #6b7280;
  --fg-subtle:       #9ca3af;

  --primary:         #7857ff;
  --primary-soft:    rgba(120,87,255,0.12);
  --primary-glow:    rgba(120,87,255,0.20);

  --risk-critical:   #ef4444;
  --risk-high:       #f97316;
  --risk-medium:     #f59e0b;
  --risk-low:        #22c55e;
  --risk-none:       #6b7280;

  --ai:              #a78bfa;
  --ai-soft:         rgba(167,139,250,0.12);

  --radius-sm:       8px;
  --radius-md:       12px;
  --radius-lg:       16px;
  --radius-xl:       20px;

  --ease-expo:       cubic-bezier(0.16, 1, 0.3, 1);
  --shadow-card:     0 1px 2px rgba(0,0,0,0.25), 0 1px 4px rgba(0,0,0,0.15);
  --shadow-hover:    0 8px 24px -8px rgba(120,87,255,0.22), 0 2px 8px rgba(0,0,0,0.2);
}

/* ── Reset y base ─────────────────────────────────────────── */
* { box-sizing: border-box; }

.stApp {
  background-color: var(--bg) !important;
  font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
  font-feature-settings: 'cv11','ss01','ss03';
  letter-spacing: -0.005em;
  color: var(--fg) !important;
}

.stApp p, .stApp span, .stApp div,
.stApp li, .stApp td, .stApp th {
  color: var(--fg) !important;
}

.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5 {
  color: #ffffff !important;
  letter-spacing: -0.02em;
  font-weight: 700;
}

.stApp label {
  color: var(--fg-subtle) !important;
  font-size: 0.78rem !important;
  font-weight: 500 !important;
  letter-spacing: 0.01em !important;
  text-transform: uppercase !important;
}

code, .stApp code, pre {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.82rem !important;
}

/* ── Sidebar ──────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background-color: var(--bg-sidebar) !important;
  border-right: 1px solid var(--border) !important;
}

[data-testid="stSidebar"] * {
  color: #94a3b8 !important;
}

[data-testid="stSidebar"] .stRadio label {
  font-size: 0.82rem !important;
  font-weight: 500 !important;
  text-transform: none !important;
  letter-spacing: 0 !important;
  padding: 6px 10px;
  border-radius: var(--radius-md);
  transition: all 0.2s var(--ease-expo);
}

[data-testid="stSidebar"] .stRadio label:hover {
  background: rgba(120,87,255,0.10) !important;
  color: #c4b5fd !important;
}

/* ── Botones ──────────────────────────────────────────────── */
.stButton > button {
  background: var(--bg-overlay) !important;
  color: var(--fg) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 0.82rem !important;
  font-weight: 500 !important;
  padding: 8px 16px !important;
  transition: all 0.2s var(--ease-expo) !important;
  box-shadow: var(--shadow-card) !important;
}

.stButton > button:hover {
  background: var(--primary-soft) !important;
  border-color: var(--border-hover) !important;
  color: #c4b5fd !important;
  transform: translateY(-1px) !important;
  box-shadow: var(--shadow-hover) !important;
}

.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #7857ff 0%, #5fe9d0 100%) !important;
  color: #ffffff !important;
  border: none !important;
  font-weight: 600 !important;
  box-shadow: 0 4px 16px -4px rgba(120,87,255,0.5) !important;
}

.stButton > button[kind="primary"]:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 24px -6px rgba(120,87,255,0.6) !important;
  color: #ffffff !important;
}

/* ── Inputs y formularios ─────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input,
.stSelectbox > div > div,
.stMultiSelect > div > div {
  background-color: var(--bg-overlay) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
  color: var(--fg) !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 0.85rem !important;
  transition: border-color 0.2s ease !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus,
.stNumberInput > div > div > input:focus {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 3px var(--primary-soft) !important;
}

.stTextInput > div > div > input:disabled,
.stTextArea > div > div > textarea:disabled,
.stNumberInput > div > div > input:disabled {
  background-color: #0f1118 !important;
  color: var(--fg-muted) !important;
  opacity: 0.7 !important;
}

/* ── Tabs ─────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  background: transparent !important;
  border-bottom: 1px solid var(--border) !important;
  gap: 2px !important;
}

.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  color: var(--fg-muted) !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 0.82rem !important;
  font-weight: 500 !important;
  padding: 8px 16px !important;
  border-radius: var(--radius-md) var(--radius-md) 0 0 !important;
  border: none !important;
  transition: all 0.2s var(--ease-expo) !important;
}

.stTabs [data-baseweb="tab"]:hover {
  color: var(--fg) !important;
  background: var(--primary-soft) !important;
}

.stTabs [aria-selected="true"] {
  color: #c4b5fd !important;
  background: var(--primary-soft) !important;
  border-bottom: 2px solid var(--primary) !important;
  font-weight: 600 !important;
}

/* ── Métricas ─────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  padding: 16px 20px !important;
  box-shadow: var(--shadow-card) !important;
  transition: all 0.3s var(--ease-expo) !important;
}

[data-testid="stMetric"]:hover {
  border-color: var(--border-hover) !important;
  box-shadow: var(--shadow-hover) !important;
  transform: translateY(-1px) !important;
}

[data-testid="stMetricLabel"] {
  color: var(--fg-muted) !important;
  font-size: 0.72rem !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.08em !important;
}

[data-testid="stMetricValue"] {
  color: #ffffff !important;
  font-size: 1.75rem !important;
  font-weight: 700 !important;
  letter-spacing: -0.02em !important;
  font-variant-numeric: tabular-nums !important;
}

[data-testid="stMetricDelta"] {
  font-size: 0.75rem !important;
  font-weight: 600 !important;
}

/* ── Expanders ────────────────────────────────────────────── */
.stExpander {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  box-shadow: var(--shadow-card) !important;
  overflow: hidden !important;
}

.stExpander summary {
  padding: 12px 16px !important;
  font-weight: 500 !important;
  font-size: 0.85rem !important;
  color: var(--fg) !important;
  transition: background 0.2s ease !important;
}

.stExpander summary:hover {
  background: var(--primary-soft) !important;
}

/* ── Dataframes / tablas ──────────────────────────────────── */
.stDataFrame {
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  overflow: hidden !important;
}

[data-testid="stDataFrameResizable"] th {
  background: var(--bg-overlay) !important;
  color: var(--fg-muted) !important;
  font-size: 0.72rem !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.08em !important;
  border-bottom: 1px solid var(--border) !important;
}

[data-testid="stDataFrameResizable"] td {
  background: var(--bg-card) !important;
  color: var(--fg) !important;
  font-size: 0.82rem !important;
  border-bottom: 1px solid var(--border) !important;
}

/* ── Progress bars ────────────────────────────────────────── */
.stProgress > div > div > div {
  background: linear-gradient(90deg, var(--primary) 0%, #5fe9d0 100%) !important;
  border-radius: 99px !important;
}

.stProgress > div > div {
  background: var(--bg-overlay) !important;
  border-radius: 99px !important;
}

/* ── Alerts / info boxes ──────────────────────────────────── */
.stAlert {
  border-radius: var(--radius-lg) !important;
  border: 1px solid var(--border) !important;
  font-size: 0.83rem !important;
}

[data-baseweb="notification"] {
  background: var(--bg-card) !important;
  border-radius: var(--radius-lg) !important;
}

/* ── File uploader ────────────────────────────────────────── */
[data-testid="stFileUploader"] {
  background: var(--bg-overlay) !important;
  border: 2px dashed var(--border) !important;
  border-radius: var(--radius-lg) !important;
  transition: all 0.2s ease !important;
}

[data-testid="stFileUploader"]:hover {
  border-color: var(--primary) !important;
  background: var(--primary-soft) !important;
}

/* ── Selectbox dropdown ───────────────────────────────────── */
[data-baseweb="select"] {
  background: var(--bg-overlay) !important;
}

[data-baseweb="popover"] {
  background: var(--bg-card-raised) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4) !important;
}

[data-baseweb="menu"] li {
  background: transparent !important;
  color: var(--fg) !important;
  font-size: 0.83rem !important;
  border-radius: var(--radius-sm) !important;
  transition: background 0.15s ease !important;
}

[data-baseweb="menu"] li:hover {
  background: var(--primary-soft) !important;
  color: #c4b5fd !important;
}

/* ── Checkboxes y radio ───────────────────────────────────── */
.stCheckbox label, .stRadio label {
  color: var(--fg) !important;
  font-size: 0.83rem !important;
  font-weight: 400 !important;
  text-transform: none !important;
}

/* ── Spinner ──────────────────────────────────────────────── */
.stSpinner > div {
  border-top-color: var(--primary) !important;
}

/* ── Toast / notifications ────────────────────────────────── */
[data-testid="stToast"] {
  background: var(--bg-card-raised) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  color: var(--fg) !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4) !important;
}

/* ── Scrollbar personalizada ──────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 99px;
}
::-webkit-scrollbar-thumb:hover { background: #374151; }

/* ══════════════════════════════════════════════════════════
   COMPONENTES REUTILIZABLES — usar en st.markdown()
══════════════════════════════════════════════════════════ */

/* Tarjeta glass */
.ar-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px 24px;
  box-shadow: var(--shadow-card);
  transition: all 0.3s var(--ease-expo);
}
.ar-card:hover {
  border-color: var(--border-hover);
  box-shadow: var(--shadow-hover);
  transform: translateY(-1px);
}

/* Section title */
.ar-section-title {
  font-size: 0.67rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin-bottom: 12px;
}

/* Risk badges */
.ar-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 99px;
  font-size: 0.65rem;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.05em;
  border: 1px solid;
}
.ar-badge-critical {
  background: rgba(239,68,68,0.12);
  color: #f87171;
  border-color: rgba(239,68,68,0.30);
}
.ar-badge-high {
  background: rgba(249,115,22,0.12);
  color: #fb923c;
  border-color: rgba(249,115,22,0.30);
}
.ar-badge-medium {
  background: rgba(245,158,11,0.12);
  color: #fbbf24;
  border-color: rgba(245,158,11,0.30);
}
.ar-badge-low {
  background: rgba(34,197,94,0.10);
  color: #4ade80;
  border-color: rgba(34,197,94,0.25);
}
.ar-badge-neutral {
  background: rgba(107,114,128,0.12);
  color: #9ca3af;
  border-color: rgba(107,114,128,0.25);
}
.ar-badge-primary {
  background: rgba(120,87,255,0.12);
  color: #a78bfa;
  border-color: rgba(120,87,255,0.30);
}

/* Metric mini card */
.ar-metric {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px 18px;
  transition: all 0.25s var(--ease-expo);
}
.ar-metric:hover {
  border-color: var(--border-hover);
  box-shadow: var(--shadow-hover);
}
.ar-metric-label {
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin-bottom: 6px;
}
.ar-metric-value {
  font-size: 1.6rem;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

/* Divider */
.ar-divider {
  border: none;
  border-top: 1px solid var(--border);
  margin: 16px 0;
}

/* Alert strip */
.ar-alert-strip {
  background: var(--bg-overlay);
  border-left: 3px solid var(--primary);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  padding: 10px 16px;
  font-size: 0.82rem;
  color: var(--fg);
}
.ar-alert-strip-critical { border-left-color: var(--risk-critical); }
.ar-alert-strip-warning  { border-left-color: var(--risk-medium); }
.ar-alert-strip-success  { border-left-color: var(--risk-low); }

/* Pill tag */
.ar-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 99px;
  font-size: 0.70rem;
  font-weight: 600;
  background: var(--bg-overlay);
  border: 1px solid var(--border);
  color: var(--fg-subtle);
}

/* Wallet address */
.ar-wallet {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.78rem;
  color: #5fe9d0;
  letter-spacing: 0.02em;
}

/* AI glow effect */
.ar-ai-glow {
  box-shadow: 0 0 32px -8px rgba(167,139,250,0.30);
  border-color: rgba(167,139,250,0.20) !important;
}
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
      "🏛️ Gestión de Infraestructura Financiera" | "📋 Log de Auditoría" |
      "👥 Gestión de Agentes"  | "📚 Centro Documental" | "👤 Perfil Agente"
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
        _rol = user.get("rol", "")
        _nav_opts = []

        # Gestión de Infraestructura Financiera — visible para roles con acceso
        if _rol in Roles.CAN_VIEW_ALIANZAS:
            _nav_opts.append("🏛️ Gestión de Infraestructura Financiera")

        # Auditoría
        if _rol in Roles.CAN_VIEW_AUDIT:
            _nav_opts.append("📋 Log de Auditoría")

        # Gestión de Agentes — equipos completos
        # Agentes ven su propio perfil (acceso directo, no por menú)
        if _rol in Roles.CAN_VIEW_AGENTES:
            _nav_opts.append("👥 Gestión de Agentes")

        # Centro Documental
        if _rol in Roles.CAN_VIEW_DOCS:
            _nav_opts.append("📚 Centro Documental")

        # Cripto Compliance
        if _rol in Roles.CAN_VIEW_CRYPTO:
            _nav_opts.append("🛡️ Cripto Compliance")

        # Agente: solo ve su propio perfil
        if _rol == Roles.AGENTE:
            _nav_opts.append("👤 Mi Perfil")

        # Fallback: si no hay ninguna opción (rol sin permisos)
        if not _nav_opts:
            _nav_opts = ["🚫 Sin acceso"]

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
        if _rol in Roles.CAN_VIEW_AGENTES:
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

    if page == "🏛️ Gestión de Infraestructura Financiera":
        if user.get("rol") not in Roles.CAN_VIEW_ALIANZAS:
            st.error("🚫 Acceso Denegado.")
            st.stop()
        from app.components.partners_ui import page_alianzas
        page_alianzas(user)
    elif page == "📋 Log de Auditoría":
        if user.get("rol") not in Roles.CAN_VIEW_AUDIT:
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
    elif page == "📚 Centro Documental":
        if user.get("rol") not in Roles.CAN_VIEW_DOCS:
            st.error("🚫 Acceso Denegado al Centro Documental.")
            st.stop()
        from app.components.compliance_ui import page_compliance
        page_compliance(user)
    elif page == "🛡️ Cripto Compliance":
        if user.get("rol") not in Roles.CAN_VIEW_CRYPTO:
            st.error("🚫 Acceso Denegado. Este módulo requiere rol admin o compliance.")
            st.stop()
        from app.components.crypto_ui import page_crypto_compliance
        page_crypto_compliance(user)
    elif page == "👤 Perfil Agente" and agente_username:
        from app.components.agentes_ui import render_perfil_agente
        render_perfil_agente(agente_username, user=user)
    elif page == "👤 Mi Perfil":
        _username = user.get("username", "")
        from app.components.agentes_ui import render_perfil_agente
        render_perfil_agente(_username, user=user)


if __name__ == "__main__":
    main()