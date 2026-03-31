"""
app/main.py
Entry point principal de AdamoServices Partner Manager.
Ejecutar con: python -m streamlit run app/main.py
"""

import streamlit as st
from datetime import date, datetime
import sys
from pathlib import Path
import os
import db.repositories.partner_repo as pr
print(f"📍 EL REPOSITORIO SE CARGA DESDE: {os.path.abspath(pr.__file__)}")

# Asegurar que la raíz del proyecto esté en el path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── Rutas de assets ──────────────────────────────────────────
_STATIC_DIR   = Path(__file__).resolve().parent / "static"
_LOGOS_DIR    = _STATIC_DIR / "img" / "logos"
_IMG_FORMATS  = (".png", ".jpg", ".jpeg", ".webp", ".svg")


def _get_logos() -> tuple[Path | None, Path | None]:
    """
    Retorna (logo_sidebar, logo_icono) con esta prioridad:
      1. Nombres estándar: logo_adamo_blanco.* y logo_adamo_color.*
      2. Fallback posicional: todos los archivos imagen en logos/ ordenados
         alfabéticamente — el 1º va al sidebar, el 2º al ícono de pestaña.
    Formatos aceptados: PNG, JPG, JPEG, WEBP, SVG.
    """
    # 1. Búsqueda por nombre estándar
    logo_sidebar = logo_icono = None
    for ext in _IMG_FORMATS:
        if not logo_sidebar and (_LOGOS_DIR / f"logo_adamo_blanco{ext}").exists():
            logo_sidebar = _LOGOS_DIR / f"logo_adamo_blanco{ext}"
        if not logo_icono and (_LOGOS_DIR / f"logo_adamo_color{ext}").exists():
            logo_icono = _LOGOS_DIR / f"logo_adamo_color{ext}"

    # 2. Fallback: archivos disponibles ordenados alfabéticamente
    if not logo_sidebar and _LOGOS_DIR.exists():
        all_imgs: list[Path] = sorted(
            p for ext in _IMG_FORMATS for p in _LOGOS_DIR.glob(f"*{ext}")
        )
        if all_imgs:
            logo_sidebar = all_imgs[0]
        if len(all_imgs) >= 2:
            logo_icono = all_imgs[1]

    return logo_sidebar, logo_icono

from config.settings import (
    APP_NAME, APP_ENV, EstadosAliado, TiposAliado, NivelesRiesgo,
    EstadosSARLAFT, Roles, SECRET_KEY_IS_DEFAULT
)
from db.database import get_session
from db.repositories.partner_repo import PartnerRepository
from db.repositories.audit_repo import AuditRepository

# ── Configuración de página ───────────────────────────────────
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🔹",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS corporativo AdamoServices ─────────────────────────────
st.markdown("""
<style>
    /* ══════════════════════════════════════════════════════════
       PALETA ADAMOSERVICES — Dark Theme completo
       Background:  #101323  | Card:    #111927  | Border: #293056
       Primary:     #5fe9d0  | Secondary: #7839ee
       Text hi:     #f9fafb  | Text mid:  #d1d5db | Text lo: #9ca3af
    ══════════════════════════════════════════════════════════ */

    /* ── Base ────────────────────────────────────────────── */
    /* Fondo controlado exclusivamente por config.toml → backgroundColor */
    .stApp { color: #111827; }
    .stApp p, .stApp span, .stApp div { color: #d1d5db; }
    .stApp label { color: #d1d5db !important; font-size: 0.85rem !important; }
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: #f9fafb !important; }

    /* ── Sidebar ─────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #293056;
    }
    [data-testid="stSidebar"] * { color: #e8eaed !important; }

    /* ── Botones ─────────────────────────────────────────── */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #5fe9d0 0%, #7839ee 100%);
        color: #101323 !important; font-weight: 700; border: none;
        border-radius: 8px; transition: all 0.2s;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 20px rgba(95,233,208,0.35);
    }
    .stButton > button:not([kind="primary"]) {
        background: transparent; border: 1px solid #293056;
        color: #d1d5db !important; border-radius: 8px;
    }
    .stButton > button:not([kind="primary"]):hover {
        border-color: #5fe9d0; color: #5fe9d0 !important;
    }

    /* ── Métricas ────────────────────────────────────────── */
    [data-testid="metric-container"] {
        background: #111927;
        border-radius: 12px; padding: 18px 20px;
        position: relative;
        /* Gradient border via box-shadow */
        box-shadow: inset 0 0 0 1px #293056;
        transition: box-shadow 0.25s;
    }
    [data-testid="metric-container"]:hover {
        box-shadow:
            inset 0 0 0 1.5px transparent,
            0 0 0 1.5px #5fe9d0,
            0 4px 18px rgba(95,233,208,0.15);
    }
    [data-testid="stMetricValue"] { color: #5fe9d0 !important; font-weight: 700; }
    [data-testid="stMetricLabel"] { color: #d1d5db !important; font-size: 0.82rem; }
    [data-testid="stMetricDelta"] { font-size: 0.76rem !important; }

    /* ── Tabs ────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        background: #111927; border-radius: 10px;
        border: 1px solid #293056; gap: 4px; padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px; color: #d1d5db !important;
        font-weight: 500; font-size: 0.88rem; padding: 8px 16px;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #5fe9d0, #7839ee) !important;
        color: #101323 !important; font-weight: 700 !important;
    }
    .stTabs [data-baseweb="tab-panel"] { padding-top: 20px; }

    /* ── Text inputs & Number inputs ─────────────────────── */
    .stTextInput input, .stNumberInput input {
        background-color: #111927 !important;
        border: 1px solid #293056 !important;
        color: #f9fafb !important;
        border-radius: 8px !important;
    }
    .stTextInput input::placeholder, .stNumberInput input::placeholder {
        color: #6b7280 !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #5fe9d0 !important;
        box-shadow: 0 0 0 2px rgba(95,233,208,0.15) !important;
    }

    /* ── Date input ─────────────────────────────────────── */
    [data-testid="stDateInput"] input,
    [data-testid="stDateInput"] > div > div,
    [data-baseweb="base-input"] {
        background-color: #111927 !important;
        color: #f9fafb !important;
        border-color: #293056 !important;
        border-radius: 8px !important;
    }
    [data-testid="stDateInput"] input { color: #f9fafb !important; }
    /* Calender popup */
    [data-baseweb="calendar"], [data-baseweb="datepicker"] {
        background-color: #111927 !important;
        border: 1px solid #293056 !important;
    }
    [data-baseweb="calendar"] * { color: #f9fafb !important; }
    [data-baseweb="calendar"] [aria-selected="true"] {
        background-color: #5fe9d0 !important; color: #101323 !important;
    }

    /* ── Selectbox ───────────────────────────────────────── */
    [data-baseweb="select"] > div {
        background-color: #111927 !important;
        border-color: #293056 !important;
    }
    [data-baseweb="select"] span,
    [data-baseweb="select"] [data-testid="stSelectbox"] { color: #f9fafb !important; }
    /* Dropdown list */
    [data-baseweb="popover"] ul, [data-baseweb="menu"] {
        background-color: #111927 !important;
        border: 1px solid #293056 !important;
    }
    [data-baseweb="menu"] li { color: #d1d5db !important; }
    [data-baseweb="menu"] li:hover,
    [data-baseweb="menu"] [aria-selected="true"] {
        background-color: rgba(95,233,208,0.1) !important;
        color: #5fe9d0 !important;
    }
    /* Texto dentro del select visible */
    [data-baseweb="select"] [data-testid="stMarkdownContainer"] p,
    [data-baseweb="select"] div[class*="valueContainer"] { color: #f9fafb !important; }
    div[class*="singleValue"] { color: #f9fafb !important; }
    div[class*="placeholder"] { color: #6b7280 !important; }

    /* ── Textarea ────────────────────────────────────────── */
    .stTextArea textarea {
        background-color: #111927 !important;
        border: 1px solid #293056 !important;
        color: #f9fafb !important;
        border-radius: 8px !important;
    }
    .stTextArea textarea::placeholder { color: #6b7280 !important; }
    .stTextArea textarea:focus {
        border-color: #5fe9d0 !important;
        box-shadow: 0 0 0 2px rgba(95,233,208,0.15) !important;
    }

    /* ── Checkbox ────────────────────────────────────────── */
    .stCheckbox label { color: #d1d5db !important; }
    .stCheckbox [data-baseweb="checkbox"] { border-color: #293056 !important; }
    .stCheckbox input:checked + div { background-color: #5fe9d0 !important; border-color: #5fe9d0 !important; }

    /* ── Radio ───────────────────────────────────────────── */
    .stRadio label { color: #d1d5db !important; }
    .stRadio [data-baseweb="radio"] div { border-color: #293056 !important; }

    /* ── Expander ────────────────────────────────────────── */
    .streamlit-expanderHeader {
        background-color: #111927 !important;
        border: 1px solid #293056 !important;
        border-radius: 10px !important;
        color: #f9fafb !important;
        font-weight: 600 !important;
    }
    .streamlit-expanderHeader:hover { border-color: #5fe9d0 !important; }
    .streamlit-expanderHeader p { color: #f9fafb !important; font-weight: 600 !important; }
    .streamlit-expanderContent {
        background-color: #0d1520 !important;
        border: 1px solid #293056 !important;
        border-top: none !important;
        border-radius: 0 0 10px 10px !important;
    }

    /* ── Dataframe ───────────────────────────────────────── */
    .stDataFrame { border: 1px solid #293056; border-radius: 10px; overflow: hidden; }
    .stDataFrame th { background-color: #0d1520 !important; color: #9ca3af !important;
                      font-size: 0.75rem !important; text-transform: uppercase;
                      letter-spacing: 0.5px; border-bottom: 1px solid #293056 !important; }
    .stDataFrame td { color: #d1d5db !important; border-color: #1e2a3a !important; }
    .stDataFrame tr:hover td { background-color: rgba(95,233,208,0.05) !important; }

    /* ── Form ────────────────────────────────────────────── */
    [data-testid="stForm"] {
        background: #111927; border: 1px solid #293056;
        border-radius: 14px; padding: 24px;
    }

    /* ── Info / Warning / Error / Success ────────────────── */
    [data-testid="stAlert"] { border-radius: 10px !important; }
    [data-testid="stInfo"]    { background: rgba(95,233,208,0.08) !important; color: #d1d5db !important;
                                border-color: #5fe9d0 !important; }
    [data-testid="stSuccess"] { background: rgba(34,197,94,0.08) !important; color: #d1d5db !important;
                                border-color: #22c55e !important; }
    [data-testid="stWarning"] { background: rgba(245,158,11,0.08) !important; color: #d1d5db !important;
                                border-color: #f59e0b !important; }
    [data-testid="stError"]   { background: rgba(239,68,68,0.1) !important; color: #fca5a5 !important;
                                border-color: #ef4444 !important; }

    /* ── Caption / Small text ────────────────────────────── */
    .stApp [data-testid="stCaptionContainer"] p { color: #9ca3af !important; }
    small, caption { color: #9ca3af !important; }

    /* ── Section titles (custom class) ──────────────────── */
    .section-title {
        font-size: 0.75rem; font-weight: 700; color: #5fe9d0;
        text-transform: uppercase; letter-spacing: 1.2px;
        border-bottom: 1px solid #293056;
        padding-bottom: 6px; margin-bottom: 14px;
    }

    /* ── Sidebar brand ───────────────────────────────────── */
    .sidebar-brand {
        font-size: 1.2rem; font-weight: 800;
        background: linear-gradient(90deg, #5fe9d0, #7839ee);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    /* ── Misc ────────────────────────────────────────────── */
    hr { border-color: #293056 !important; }
    h2 { border-bottom: 1px solid #293056; padding-bottom: 8px; }
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: #111927; }
    ::-webkit-scrollbar-thumb { background: #293056; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #5fe9d0; }

    /* ── Logo nativo — ocultar solo la versión del sidebar expandido ── */
    /* stSidebarLogo = logo pequeño en header del sidebar expandido (duplicado con st.image) */
    /* stHeaderLogo  = icono flotante cuando sidebar está colapsado   (queremos mantenerlo) */
    [data-testid="stSidebarLogo"] { display: none !important; }

    /* ── Holdings BPO — aumentar tamaño del icono flotante al colapsar ── */
    [data-testid="stHeaderLogo"] {
        height: 48px !important;
        max-height: 48px !important;
        width: auto !important;
    }

    /* ── Badges ──────────────────────────────────────────── */
    .badge { display:inline-block; padding:3px 12px; border-radius:20px;
             font-size:0.75rem; font-weight:700; letter-spacing:0.3px; }
    .badge-activo      { background:rgba(95,233,208,0.15);  color:#5fe9d0;  border:1px solid #5fe9d0; }
    .badge-prospecto   { background:rgba(120,57,238,0.15);  color:#c4b5fd;  border:1px solid #7839ee; }
    .badge-onboarding  { background:rgba(129,140,248,0.15); color:#a5b4fc;  border:1px solid #818cf8; }
    .badge-suspendido  { background:rgba(220,38,38,0.15);   color:#fca5a5;  border:1px solid #dc2626; }
    .badge-calificacion{ background:rgba(14,147,132,0.2);   color:#5fe9d0;  border:1px solid #0e9384; }
    .badge-terminado   { background:rgba(75,85,99,0.2);     color:#d1d5db;  border:1px solid #4d5761; }
</style>
""", unsafe_allow_html=True)


# ── Autenticación — delegada a app/auth/login.py ──────────────
# login_screen(), authenticate() y require_auth() viven allí.
# Este módulo solo invoca require_auth() desde main().


# ── Sidebar de navegación ─────────────────────────────────────
def sidebar(user: dict):
    # ── Logos: leídos como bytes para máxima compatibilidad con Windows ──────
    _logo_sidebar, _logo_icono = _get_logos()

    # st.logo() → icono flotante cuando el sidebar está colapsado
    if _logo_icono:
        try:
            _icon_bytes = _logo_icono.read_bytes()
            _main_bytes = _logo_sidebar.read_bytes() if _logo_sidebar else _icon_bytes
            st.logo(_main_bytes, icon_image=_icon_bytes, size="large")
        except Exception:
            pass

    with st.sidebar:
        if _logo_sidebar:
            try:
                st.image(_logo_sidebar.read_bytes(), width=220)
            except Exception:
                pass
        st.markdown("<hr style='border-color:#293056; margin:10px 0;'>", unsafe_allow_html=True)
        st.markdown(f"<span style='color:#9ca3af; font-size:0.82rem;'>👤 {user['nombre_completo']}</span>", unsafe_allow_html=True)
        st.markdown(f"<span style='color:#363f72; font-size:0.78rem;'>🔑 {user['rol']}</span>", unsafe_allow_html=True)
        st.markdown("<hr style='border-color:#293056; margin:10px 0;'>", unsafe_allow_html=True)

        page = st.radio(
            "Navegación",
            options=["📊 Dashboard", "🤝 Partners", "➕ Nuevo Partner", "📋 Log de Auditoría"],
            label_visibility="collapsed"
        )

        # ── Filtros de Monitoreo (Dashboard) ─────────────────────────────────
        st.markdown("<hr style='border-color:#293056; margin:10px 0;'>", unsafe_allow_html=True)
        st.markdown(
            "<div style='font-size:0.68rem; font-weight:700; color:#5fe9d0;"
            " text-transform:uppercase; letter-spacing:1.2px; margin-bottom:8px;'>"
            "Filtros de Monitoreo</div>",
            unsafe_allow_html=True,
        )
        st.checkbox(
            "Solo Exposición PEP (GAFI R.12)",
            key="filtro_pep",
            help="Muestra solo aliados con Exposición Política activa — DDI obligatoria (GAFI R.12 / Cap. VII SARLAFT)",
        )
        st.checkbox(
            "Solo Riesgo Alto / Muy Alto",
            key="filtro_alto",
            help="Monitoreo Intensificado — Debida Diligencia Intensificada requerida (GAFI R.1)",
        )
        # Oficiales de Cumplimiento disponibles en DB
        try:
            _s_gen = get_session()
            _s = next(_s_gen)
            from sqlalchemy import text as _text
            _rows = _s.execute(
                _text(
                    "SELECT nombre_completo FROM usuarios "
                    "WHERE rol IN ('admin','compliance') AND activo = 1 "
                    "ORDER BY nombre_completo"
                )
            ).fetchall()
            _s.close()
            _oficiales = ["Todos los Oficiales"] + [r[0] for r in _rows]
        except Exception:
            _oficiales = ["Todos los Oficiales"]
        st.selectbox(
            "Oficial de Cumplimiento",
            _oficiales,
            key="filtro_oficial",
            help="Filtrar vista por Oficial de Cumplimiento asignado al portafolio",
        )

        st.markdown("<hr style='border-color:#293056; margin:10px 0;'>", unsafe_allow_html=True)
        # Footer del sidebar
        st.markdown("""
        <div style='font-size:0.7rem; color:#363f72; text-align:center; padding-top:8px;'>
            © 2026 AdamoServices S.A.S.<br>
            <span style='color:#293056;'>Compliance & Technology</span>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            for _k in ("user", "authenticated", "login_fails", "login_locked_until",
                       "filtro_pep", "filtro_alto", "filtro_oficial"):
                st.session_state.pop(_k, None)
            st.rerun()

    return page


# ── Badge HTML ────────────────────────────────────────────────
def badge(estado: str) -> str:
    clases = {
        "Activo":         "badge-activo",
        "Prospecto":      "badge-prospecto",
        "Onboarding":     "badge-onboarding",
        "Suspendido":     "badge-suspendido",
        "En Calificación":"badge-calificacion",
        "Terminado":      "badge-terminado",
    }
    css = clases.get(estado, "badge-terminado")
    return f'<span class="badge {css}">{estado}</span>'


# ── Helpers EBR ───────────────────────────────────────────────
def _riesgo_color(nivel: str) -> str:
    """Semáforo de color por nivel de riesgo (EBR)."""
    return {"Bajo": "#5fe9d0", "Medio": "#f59e0b",
            "Alto": "#fb923c", "Muy Alto": "#ef4444"}.get(nivel, "#9ca3af")


# ── Mapas de etiquetas con emojis (compartidos en toda la UI) ──
_MAP_RIESGO  = {"Bajo": "🟢 Bajo", "Medio": "🟡 Medio", "Alto": "🔴 Alto", "Muy Alto": "🔴 Muy Alto"}
_MAP_SARLAFT = {"Al Día": "✅ Al Día", "Pendiente": "⏳ Pendiente",
                "En Revisión": "🔍 En Revisión", "Vencido": "❌ Vencido"}


def _build_table_df(partners: list) -> tuple:
    """Enriquece lista de aliados con emojis para la tabla `st.dataframe`."""
    import pandas as pd
    PIPELINE = {"Prospecto": "🔵 Prospecto", "En Calificación": "🟡 En Calificación",
                "Onboarding": "🟣 Onboarding", "Activo": "🟢 Activo",
                "Suspendido": "🔴 Suspendido", "Terminado": "⚫ Terminado"}
    DD       = {"Pendiente": "⏳ Pendiente", "En Proceso": "🔄 En Proceso",
                "Completado": "✅ Completado", "Rechazado": "❌ Rechazado"}
    df = pd.DataFrame(partners)
    df["nivel_riesgo"]         = df["nivel_riesgo"].map(lambda x: _MAP_RIESGO.get(x, x))
    df["estado_sarlaft"]       = df["estado_sarlaft"].map(lambda x: _MAP_SARLAFT.get(x, x))
    df["estado_pipeline"]      = df["estado_pipeline"].map(lambda x: PIPELINE.get(x, x))
    df["estado_due_diligence"] = df["estado_due_diligence"].map(lambda x: DD.get(x, x))
    df["es_pep"]               = df["es_pep"].astype(bool)
    df["listas_verificadas"]   = df["listas_verificadas"].astype(bool)
    df["puntaje_riesgo"]       = df["puntaje_riesgo"].fillna(0.0)
    col_cfg = {
        "nombre_razon_social":  st.column_config.TextColumn("Partner / Aliado", width="large"),
        "nit":                  st.column_config.TextColumn("NIT"),
        "tipo_aliado":          st.column_config.TextColumn("Tipo"),
        "estado_pipeline":      st.column_config.TextColumn("Pipeline"),
        "nivel_riesgo":         st.column_config.TextColumn("Nivel Riesgo"),
        "puntaje_riesgo":       st.column_config.ProgressColumn(
                                    "Score Riesgo", min_value=0, max_value=100, format="%.0f pts"),
        "estado_sarlaft":       st.column_config.TextColumn("SARLAFT"),
        "estado_due_diligence": st.column_config.TextColumn("Debida Diligencia"),
        "es_pep":               st.column_config.CheckboxColumn("PEP"),
        "listas_verificadas":   st.column_config.CheckboxColumn("Listas ✓"),
        "fecha_proxima_revision": st.column_config.DateColumn("Próx. Revisión", format="DD/MMM/YYYY"),
        "ciudad":               st.column_config.TextColumn("Ciudad"),
    }
    cols = ["nombre_razon_social", "nit", "tipo_aliado", "estado_pipeline", "nivel_riesgo",
            "puntaje_riesgo", "estado_sarlaft", "estado_due_diligence",
            "es_pep", "listas_verificadas", "fecha_proxima_revision", "ciudad"]
    return df, col_cfg, cols


def _kpi_bar(repo) -> tuple:
    """Renderiza el panel de KPIs de cumplimiento y retorna datos para los tabs."""
    stats_pipeline = repo.get_stats_pipeline()
    stats_riesgo   = repo.get_stats_riesgo()
    dd_stats       = repo.get_cobertura_due_diligence()
    sarlaft_stats  = repo.get_stats_estado_sarlaft()
    proximas       = repo.get_revisiones_proximas(dias=30)
    pep_list       = repo.get_pep_activos()
    total          = sum(stats_pipeline.values())
    activos        = stats_pipeline.get("Activo", 0) or 0
    dd_total       = int(dd_stats.get("total") or 0)
    dd_completados = int(dd_stats.get("completados") or 0)
    dd_pct         = round((dd_completados / dd_total) * 100) if dd_total else 0
    vencidas       = int(sarlaft_stats.get("Vencido") or 0)
    alto_riesgo    = (stats_riesgo.get("Alto") or 0) + (stats_riesgo.get("Muy Alto") or 0)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Partners", total, delta=f"{activos} activos")
    c2.metric("Cobertura Due Diligence", f"{dd_pct}%",
              delta=f"{dd_completados}/{dd_total} completados")
    c3.metric("Alertas SARLAFT Vencidas", vencidas,
              delta=f"−{vencidas} críticos" if vencidas else "Sin alertas",
              delta_color="inverse" if vencidas else "off")
    c4.metric("Riesgo Alto / Muy Alto", alto_riesgo,
              delta=f"{round(alto_riesgo/total*100) if total else 0}% del total",
              delta_color="inverse" if alto_riesgo else "off")
    c5.metric("Sujetos PEP Activos", len(pep_list),
              delta="DDI requerida (GAFI R.12)" if pep_list else "Sin PEP vigentes",
              delta_color="inverse" if pep_list else "off")
    return stats_pipeline, stats_riesgo, sarlaft_stats, proximas, pep_list


def _tab_pipeline(stats_pipeline: dict, all_partners: list) -> None:
    """Tab 1: Distribución del Pipeline + tabla interactiva EBR."""
    import plotly.express as px
    import pandas as pd
    c1, c2 = st.columns([1.5, 1])
    with c1:
        st.markdown("##### Distribución del Pipeline")
        if stats_pipeline:
            color_map = {
                "Prospecto": "#7839ee", "En Calificación": "#0e9384",
                "Onboarding": "#818cf8", "Activo": "#5fe9d0",
                "Suspendido": "#dc2626", "Terminado": "#4d5761",
            }
            df_bar = pd.DataFrame(
                [(e, stats_pipeline.get(e, 0)) for e in EstadosAliado.ALL],
                columns=["Estado", "Total"]
            )
            fig = px.bar(df_bar, x="Estado", y="Total", color="Estado",
                         color_discrete_map=color_map, template="plotly_dark", text="Total")
            fig.update_traces(textposition="outside")
            fig.update_layout(
                showlegend=False, height=320,
                margin=dict(t=10, b=10, l=0, r=0),
                paper_bgcolor="#111927", plot_bgcolor="#111927",
                font=dict(color="#9ca3af"),
                xaxis=dict(gridcolor="#293056", title=""),
                yaxis=dict(gridcolor="#293056", title=""),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin datos. Registra el primer Partner.")
    with c2:
        st.markdown("##### Kanban — Estado del Pipeline")
        kanban = {
            "Prospecto":       ("#7839ee", "rgba(120,57,238,0.1)"),
            "En Calificación": ("#0e9384", "rgba(14,147,132,0.1)"),
            "Onboarding":      ("#818cf8", "rgba(129,140,248,0.1)"),
            "Activo":          ("#5fe9d0", "rgba(95,233,208,0.1)"),
            "Suspendido":      ("#dc2626", "rgba(220,38,38,0.1)"),
            "Terminado":       ("#4d5761", "rgba(77,87,97,0.1)"),
        }
        for estado in EstadosAliado.ALL:
            count = stats_pipeline.get(estado, 0)
            color, bg = kanban.get(estado, ("#9ca3af", "rgba(156,163,175,0.1)"))
            st.markdown(f"""
            <div style='background:{bg}; border-left:3px solid {color};
                border-radius:6px; padding:8px 14px; margin-bottom:6px;
                display:flex; justify-content:space-between; align-items:center;'>
                <span style='color:{color}; font-size:0.85rem; font-weight:600;'>{estado}</span>
                <span style='color:#f9fafb; font-size:1.1rem; font-weight:800;'>{count}</span>
            </div>
            """, unsafe_allow_html=True)
    if all_partners:
        st.markdown("---")
        st.markdown("##### Tabla Interactiva — Ordenada por Riesgo (EBR · GAFI R.1)")
        df, col_cfg, cols = _build_table_df(all_partners)
        st.dataframe(df[cols], column_config=col_cfg, hide_index=True, use_container_width=True)


def _tab_mapa_riesgos(stats_riesgo: dict, sarlaft_stats: dict, all_partners: list) -> None:
    """Tab 2: Donut riesgo + barras SARLAFT + Matriz de Riesgo Inherente (Scatter 4x4)."""
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd
    COLOR_R = {"Bajo": "#5fe9d0", "Medio": "#f59e0b", "Alto": "#fb923c", "Muy Alto": "#ef4444"}
    COLOR_S = {"Al Día": "#5fe9d0", "Pendiente": "#f59e0b",
               "En Revisión": "#7839ee", "Vencido": "#ef4444"}

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Distribución por Nivel de Riesgo (EBR)")
        if stats_riesgo:
            df_r = pd.DataFrame(stats_riesgo.items(), columns=["Nivel", "Total"])
            fig  = px.pie(df_r, names="Nivel", values="Total", color="Nivel",
                          color_discrete_map=COLOR_R, template="plotly_dark", hole=0.52)
            fig.update_traces(textinfo="label+percent")
            fig.update_layout(height=300, margin=dict(t=10, b=10, l=0, r=0),
                              paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#9ca3af"),
                              legend=dict(bgcolor="rgba(0,0,0,0)"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin datos.")
    with c2:
        st.markdown("##### Estado de Revisiones SARLAFT")
        if sarlaft_stats:
            df_s = pd.DataFrame(sarlaft_stats.items(), columns=["Estado", "Total"])
            fig2 = px.bar(df_s, x="Total", y="Estado", orientation="h", color="Estado",
                          color_discrete_map=COLOR_S, template="plotly_dark", text="Total")
            fig2.update_traces(textposition="outside")
            fig2.update_layout(showlegend=False, height=300,
                               margin=dict(t=10, b=10, l=0, r=0),
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               font=dict(color="#9ca3af"),
                               xaxis=dict(gridcolor="#293056"),
                               yaxis=dict(gridcolor="#293056"))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Sin datos.")

    # ── Matriz de Riesgo Inherente 4×4 ──────────────────────────────────────
    st.markdown("---")
    st.markdown("##### 🎯 Matriz de Riesgo Inherente — Probabilidad × Impacto (EBR · GAFI R.1)")

    # Probabilidad basada en tipo_aliado (proxy regulatorio)
    PROB_MAP = {
        "Banco":              4, "Cooperativa":       4,
        "Fintech":            3, "Aseguradora":       3,
        "Distribuidor":       2, "Proveedor":         2,
        "Comercializador":    2, "Consultor":         1,
    }
    if all_partners:
        df_scatter = pd.DataFrame(all_partners)
        df_scatter["puntaje_riesgo"] = df_scatter["puntaje_riesgo"].fillna(0)
        df_scatter["probabilidad"] = df_scatter["tipo_aliado"].map(
            lambda t: PROB_MAP.get(t, 2)
        ).astype(float)
        # jitter para evitar superposición
        import numpy as np
        rng = np.random.default_rng(42)
        df_scatter["prob_j"] = df_scatter["probabilidad"] + rng.uniform(-0.15, 0.15, len(df_scatter))
        df_scatter["imp_j"]  = df_scatter["puntaje_riesgo"] + rng.uniform(-1.5, 1.5, len(df_scatter))
        df_scatter["imp_j"]  = df_scatter["imp_j"].clip(0, 100)

        color_map_scatter = {"Bajo": "#5fe9d0", "Medio": "#f59e0b",
                             "Alto": "#fb923c", "Muy Alto": "#ef4444"}

        fig3 = px.scatter(
            df_scatter,
            x="prob_j", y="imp_j",
            color="nivel_riesgo",
            color_discrete_map=color_map_scatter,
            hover_name="nombre_razon_social",
            hover_data={"nit": True, "tipo_aliado": True,
                        "nivel_riesgo": True, "puntaje_riesgo": True,
                        "prob_j": False, "imp_j": False},
            template="plotly_dark",
            size_max=14,
        )
        fig3.update_traces(marker=dict(size=10, opacity=0.85, line=dict(width=0.5, color="#293056")))

        # Cuadrantes de zona de riesgo
        shapes = [
            dict(type="rect", x0=0.5, x1=2.5, y0=0,  y1=50,  fillcolor="rgba(95,233,208,0.05)",  line_width=0),
            dict(type="rect", x0=0.5, x1=2.5, y0=50, y1=100, fillcolor="rgba(245,158,11,0.07)",  line_width=0),
            dict(type="rect", x0=2.5, x1=4.5, y0=0,  y1=50,  fillcolor="rgba(251,146,60,0.07)",  line_width=0),
            dict(type="rect", x0=2.5, x1=4.5, y0=50, y1=100, fillcolor="rgba(239,68,68,0.10)",   line_width=0),
        ]
        annotations = [
            dict(x=1.5, y=25,  text="BAJO", showarrow=False, font=dict(color="#5fe9d0", size=10), opacity=0.5),
            dict(x=1.5, y=75,  text="MEDIO", showarrow=False, font=dict(color="#f59e0b", size=10), opacity=0.5),
            dict(x=3.5, y=25,  text="ALTO", showarrow=False, font=dict(color="#fb923c", size=10), opacity=0.5),
            dict(x=3.5, y=75,  text="MUY ALTO", showarrow=False, font=dict(color="#ef4444", size=10), opacity=0.5),
        ]
        fig3.update_layout(
            height=380,
            shapes=shapes, annotations=annotations,
            margin=dict(t=20, b=30, l=40, r=20),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#9ca3af"),
            xaxis=dict(title="Probabilidad (Tipo de Aliado)", range=[0.5, 4.5],
                       tickvals=[1, 2, 3, 4], ticktext=["Baja", "Media-Baja", "Media-Alta", "Alta"],
                       gridcolor="#1e2a3a", zeroline=False),
            yaxis=dict(title="Impacto (Score EBR)", range=[0, 100],
                       gridcolor="#1e2a3a", zeroline=False),
            legend=dict(title="Nivel", bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Sin datos para la matriz de riesgo.")

    # ── Tabla alto riesgo ────────────────────────────────────────────────────
    alto_lista = [p for p in all_partners if p.get("nivel_riesgo") in ("Alto", "Muy Alto")]
    st.markdown("---")
    if alto_lista:
        st.markdown(f"""
        <div style='border-left:4px solid #ef4444; padding:8px 16px;
            background:rgba(239,68,68,0.08); border-radius:0 8px 8px 0; margin-bottom:12px;'>
            <span style='color:#ef4444; font-weight:700; font-size:0.9rem;'>
                ⚠️ EBR — {len(alto_lista)} aliado(s) con riesgo Alto / Muy Alto
                requieren Debida Diligencia Intensificada (GAFI R.1).
            </span>
        </div>
        """, unsafe_allow_html=True)
        df_alto, col_cfg, _ = _build_table_df(alto_lista)
        cols_alto = ["nombre_razon_social", "nit", "nivel_riesgo", "puntaje_riesgo",
                     "estado_sarlaft", "estado_due_diligence", "es_pep", "ciudad"]
        st.dataframe(df_alto[cols_alto], column_config=col_cfg,
                     hide_index=True, use_container_width=True)
    else:
        st.success("✅ Sin aliados en categoría de Riesgo Alto o Muy Alto.")


def _tab_tendencias(repo, all_partners: list, stats_riesgo: dict, total: int) -> None:
    """Tab 4: Análisis de Tendencias — geografía, SARLAFT donut, Salud del Portafolio."""
    import plotly.express as px
    import pandas as pd

    # ── KPI Salud del Portafolio ─────────────────────────────────────────────
    n_alto = sum(
        1 for p in all_partners if p.get("nivel_riesgo") in ("Alto", "Muy Alto")
    )
    salud = max(0.0, 100.0 - (n_alto / total * 100)) if total else 100.0
    delta_label = f"{n_alto} en riesgo alto/muy alto"

    m1, m2, m3 = st.columns(3)
    m1.metric("🩺 Salud del Portafolio", f"{salud:.1f}%",
              delta=f"−{total - int(salud / 100 * total)} aliados de riesgo",
              delta_color="inverse")
    m2.metric("📋 Total analizados", total)
    m3.metric("⚠️ Riesgo Alto / Muy Alto", n_alto, delta_color="inverse",
              delta=f"{n_alto/total*100:.1f}% del portafolio" if total else "—")

    c1, c2 = st.columns([2, 1])

    # ── Distribución Geográfica ──────────────────────────────────────────────
    with c1:
        st.markdown("##### 🌍 Distribución Geográfica de Aliados (Top 15 ciudades)")
        ciudad_data = repo.get_stats_ciudad()
        if ciudad_data:
            df_geo = pd.DataFrame(ciudad_data)
            df_geo = df_geo.sort_values("total", ascending=True)
            COLOR_SEQ = (["#5fe9d0"] * len(df_geo))
            fig = px.bar(
                df_geo, x="total", y="ciudad", orientation="h",
                text="total", template="plotly_dark",
                color_discrete_sequence=["#5fe9d0"],
            )
            fig.update_traces(textposition="outside", marker_color=[
                "#ef4444" if v > df_geo["total"].mean() * 1.5 else "#5fe9d0"
                for v in df_geo["total"]
            ])
            fig.update_layout(
                height=380, showlegend=False,
                margin=dict(t=10, b=10, l=0, r=30),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#9ca3af"),
                xaxis=dict(title="Aliados", gridcolor="#1e2a3a", zeroline=False),
                yaxis=dict(title="", gridcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin datos geográficos.")

    # ── Donut SARLAFT Compliance ─────────────────────────────────────────────
    with c2:
        st.markdown("##### 🔄 Compliance SARLAFT")
        sarlaft_stats = repo.get_stats_estado_sarlaft()
        if sarlaft_stats:
            COLOR_S = {"Al Día": "#5fe9d0", "Pendiente": "#f59e0b",
                       "En Revisión": "#7839ee", "Vencido": "#ef4444"}
            df_s = pd.DataFrame(sarlaft_stats.items(), columns=["Estado", "Total"])
            fig2 = px.pie(df_s, names="Estado", values="Total", color="Estado",
                          color_discrete_map=COLOR_S, template="plotly_dark", hole=0.6)
            fig2.update_traces(textinfo="label+value")
            fig2.update_layout(
                height=380, margin=dict(t=10, b=10, l=0, r=0),
                paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#9ca3af"),
                legend=dict(bgcolor="rgba(0,0,0,0)", orientation="v"),
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Sin datos SARLAFT.")

    # ── Distribución por Tipo de Aliado ──────────────────────────────────────
    if all_partners:
        st.markdown("---")
        st.markdown("##### 🏷️ Composición por Tipo de Aliado")
        from collections import Counter
        tipo_count = Counter(p.get("tipo_aliado", "Sin tipo") for p in all_partners)
        df_tipo = pd.DataFrame(tipo_count.items(), columns=["Tipo", "Total"])
        df_tipo = df_tipo.sort_values("Total", ascending=False)
        fig3 = px.bar(df_tipo, x="Tipo", y="Total", color="Tipo",
                      text="Total", template="plotly_dark",
                      color_discrete_sequence=px.colors.qualitative.Set2)
        fig3.update_traces(textposition="outside")
        fig3.update_layout(
            height=280, showlegend=False,
            margin=dict(t=10, b=10, l=0, r=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#9ca3af"),
            xaxis=dict(gridcolor="rgba(0,0,0,0)"),
            yaxis=dict(gridcolor="#1e2a3a", zeroline=False),
        )
        st.plotly_chart(fig3, use_container_width=True)


def _tab_reportes(repo, user: dict, session) -> None:
    """Tab 5: Centro de Reportes — descarga CSV / Excel con auditoría."""
    import io
    import pandas as pd

    st.markdown("##### 📥 Centro de Reportes — Exportación con Auditoría")
    st.markdown(
        "<p style='color:#9ca3af; font-size:0.85rem;'>"
        "Los reportes generados quedan registrados en el log de auditoría "
        "con fecha, hora y usuario generador."
        "</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # ── Filtros de exportación ────────────────────────────────────────────────
    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        solo_pep = st.checkbox("Solo Sujetos PEP (GAFI R.12)", value=False)
    with cf2:
        solo_alto = st.checkbox("Solo Riesgo Alto / Muy Alto", value=False)
    with cf3:
        oficial = st.selectbox("Oficial de Cumplimiento",
                               ["Todos"] + sorted({
                                   p.get("oficial_cumplimiento", "") or ""
                                   for p in repo.get_lista_export(False, False, None)
                                   if p.get("oficial_cumplimiento")
                               }))
    oficial_val = None if oficial == "Todos" else oficial

    if st.button("🔄 Previsualizar Reporte", type="secondary"):
        data_prev = repo.get_lista_export(solo_pep, solo_alto, oficial_val)
        if data_prev:
            df_prev = pd.DataFrame(data_prev).head(20)
            st.dataframe(df_prev, hide_index=True, use_container_width=True)
            st.caption(f"Mostrando primeras 20 de {len(data_prev)} filas.")
        else:
            st.info("Sin registros con los filtros seleccionados.")

    st.markdown("---")
    st.markdown("##### 📂 Descargar Reporte")

    bd1, bd2 = st.columns(2)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    with bd1:
        if st.button("⬇️ Descargar CSV", type="primary", use_container_width=True):
            data = repo.get_lista_export(solo_pep, solo_alto, oficial_val)
            if not data:
                st.warning("Sin datos para exportar.")
            else:
                df_exp = pd.DataFrame(data)
                df_exp.insert(0, "timestamp_generacion",
                              datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                df_exp.insert(1, "usuario_generador", user.get("username", ""))
                csv_bytes = df_exp.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label=f"✅ Listo — clic para guardar CSV ({len(data)} registros)",
                    data=csv_bytes,
                    file_name=f"reporte_partners_{ts}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
                # Registrar auditoría
                try:
                    AuditRepository(session).registrar(
                        username=user.get("username", ""),
                        accion="EXPORT",
                        entidad="aliados",
                        descripcion=(
                            f"Exportación CSV — {len(data)} registros"
                            + (" · Solo PEP" if solo_pep else "")
                            + (" · Solo Alto Riesgo" if solo_alto else "")
                            + (f" · Oficial: {oficial_val}" if oficial_val else "")
                        ),
                        usuario_id=user.get("id"),
                        valores_nuevos={
                            "formato": "csv",
                            "registros": len(data),
                            "filtros": {
                                "solo_pep": solo_pep,
                                "solo_alto_riesgo": solo_alto,
                                "oficial": oficial_val,
                            },
                        },
                    )
                    session.commit()
                except Exception:
                    pass

    with bd2:
        if st.button("⬇️ Descargar Excel", type="primary", use_container_width=True):
            data = repo.get_lista_export(solo_pep, solo_alto, oficial_val)
            if not data:
                st.warning("Sin datos para exportar.")
            else:
                df_exp = pd.DataFrame(data)
                df_exp.insert(0, "timestamp_generacion",
                              datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                df_exp.insert(1, "usuario_generador", user.get("username", ""))
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                    df_exp.to_excel(writer, index=False, sheet_name="Partners")
                    # Hoja de auditoría
                    audit_df = pd.DataFrame([{
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "generado_por": user.get("username", ""),
                        "filtros_aplicados": str({
                            "solo_pep": solo_pep,
                            "solo_alto_riesgo": solo_alto,
                            "oficial": oficial_val,
                        }),
                        "total_registros": len(data),
                    }])
                    audit_df.to_excel(writer, index=False, sheet_name="Auditoría")
                buf.seek(0)
                st.download_button(
                    label=f"✅ Listo — clic para guardar Excel ({len(data)} registros)",
                    data=buf.getvalue(),
                    file_name=f"reporte_partners_{ts}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
                # Registrar auditoría
                try:
                    AuditRepository(session).registrar(
                        username=user.get("username", ""),
                        accion="EXPORT",
                        entidad="aliados",
                        descripcion=(
                            f"Exportación Excel — {len(data)} registros"
                            + (" · Solo PEP" if solo_pep else "")
                            + (" · Solo Alto Riesgo" if solo_alto else "")
                            + (f" · Oficial: {oficial_val}" if oficial_val else "")
                        ),
                        usuario_id=user.get("id"),
                        valores_nuevos={
                            "formato": "xlsx",
                            "registros": len(data),
                            "filtros": {
                                "solo_pep": solo_pep,
                                "solo_alto_riesgo": solo_alto,
                                "oficial": oficial_val,
                            },
                        },
                    )
                    session.commit()
                except Exception:
                    pass


def _tab_alertas(proximas: list, pep_list: list, sarlaft_vencidas: list) -> None:
    """Tab 3: Alertas operativas — SARLAFT vencidas, próximas revisiones, sujetos PEP."""
    import pandas as pd
    n_vencidas = len(sarlaft_vencidas)
    if n_vencidas:
        st.markdown(f"""
        <div style='background:rgba(239,68,68,0.12); border:1px solid #ef4444;
            border-radius:10px; padding:14px 20px; margin-bottom:16px;'>
            <span style='color:#ef4444; font-size:1rem; font-weight:700;'>
                🚨 {n_vencidas} revisión(es) SARLAFT VENCIDA(S) — Acción inmediata requerida.
            </span>
        </div>
        """, unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### 🔴 Revisiones SARLAFT Vencidas")
        if sarlaft_vencidas:
            for v in sarlaft_vencidas:
                nc = _riesgo_color(v.get("nivel_riesgo", ""))
                st.markdown(f"""
                <div style='background:rgba(239,68,68,0.07); border:1px solid #293056;
                    border-left:3px solid {nc}; border-radius:8px;
                    padding:10px 14px; margin-bottom:8px;'>
                    <div style='font-weight:600; color:#f9fafb;'>{v["nombre_razon_social"]}</div>
                    <div style='color:#9ca3af; font-size:0.78rem;'>
                        NIT: {v["nit"]} · {v.get("ciudad","—")} ·
                        <span style='color:{nc};'>{v.get("nivel_riesgo","—")}</span>
                    </div>
                    <div style='color:#ef4444; font-size:0.75rem; margin-top:4px;'>
                        Vencida: {v.get("fecha_proxima_revision","N/D")}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ Sin revisiones SARLAFT vencidas.")
    with col2:
        st.markdown("##### 🟡 Próximas Revisiones (30 días)")
        if proximas:
            for p in proximas:
                nc = _riesgo_color(p.get("nivel_riesgo", ""))
                st.markdown(f"""
                <div style='background:rgba(245,158,11,0.07); border:1px solid #293056;
                    border-left:3px solid {nc}; border-radius:8px;
                    padding:10px 14px; margin-bottom:8px;'>
                    <div style='font-weight:600; color:#f9fafb;'>{p["nombre_razon_social"]}</div>
                    <div style='color:#9ca3af; font-size:0.78rem;'>
                        NIT: {p["nit"]} ·
                        <span style='color:{nc};'>{p.get("nivel_riesgo","—")}</span>
                    </div>
                    <div style='color:#f59e0b; font-size:0.75rem; margin-top:4px;'>
                        Fecha: {p.get("fecha_proxima_revision","N/D")}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Sin revisiones próximas en 30 días.")
    # Tabla PEP
    st.markdown("---")
    st.markdown(f"##### ⚠️ Sujetos con Exposición Política (PEP) — {len(pep_list)} activo(s)")
    if pep_list:
        st.caption(
            "Debida Diligencia Intensificada requerida conforme GAFI R.12 "
            "y Capítulo VII del SARLAFT Colombia."
        )
        df_pep = pd.DataFrame(pep_list)
        df_pep["nivel_riesgo"]  = df_pep["nivel_riesgo"].map(lambda x: _MAP_RIESGO.get(x, x))
        df_pep["estado_sarlaft"] = df_pep["estado_sarlaft"].map(lambda x: _MAP_SARLAFT.get(x, x))
        cols_pep = [c for c in ["nombre_razon_social", "nit", "nivel_riesgo",
                                 "descripcion_pep", "vinculo_pep",
                                 "estado_sarlaft", "estado_pipeline"]
                    if c in df_pep.columns]
        st.dataframe(
            df_pep[cols_pep],
            column_config={
                "nombre_razon_social": st.column_config.TextColumn("Partner", width="large"),
                "nit":                 st.column_config.TextColumn("NIT"),
                "nivel_riesgo":        st.column_config.TextColumn("Nivel Riesgo"),
                "descripcion_pep":     st.column_config.TextColumn("Descripción PEP", width="large"),
                "vinculo_pep":         st.column_config.TextColumn("Vínculo PEP"),
                "estado_sarlaft":      st.column_config.TextColumn("SARLAFT"),
                "estado_pipeline":     st.column_config.TextColumn("Pipeline"),
            },
            hide_index=True, use_container_width=True,
        )
    else:
        st.success("✅ Sin sujetos PEP registrados actualmente.")


# ── Página Dashboard ──────────────────────────────────────────
def page_dashboard(user: dict):
    from app.components.alerts import render_centro_notificaciones
    from datetime import date as _date

    st.markdown("""
    <h1 style='font-size:1.8rem; font-weight:800; margin-bottom:4px;'>
        📊 Centro de Control de Cumplimiento
    </h1>
    <p style='color:#9ca3af; font-size:0.9rem; margin-top:0;'>
        Visión consolidada · Enfoque Basado en Riesgos (EBR — GAFI Recomendación 1)
    </p>
    """, unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#293056;'>", unsafe_allow_html=True)

    session_gen = get_session()
    session = next(session_gen)
    try:
        repo = PartnerRepository(session)
        all_partners     = repo.get_lista_enriquecida()
        sarlaft_vencidas = repo.get_sarlaft_vencidas()

        # ── Centro de Notificaciones ──────────────────────────────────────────
        render_centro_notificaciones(repo, session, user)
        st.markdown("<hr style='border-color:#293056; margin:20px 0;'>", unsafe_allow_html=True)

        # ── KPI Strip ────────────────────────────────────────────────────────
        stats_pipeline, stats_riesgo, sarlaft_stats, proximas, pep_list = _kpi_bar(repo)

        # KPIs extendidos: Exposición PEP % + Promedio Onboarding (días)
        total = sum(stats_pipeline.values()) or 1
        pep_pct = round(len(pep_list) / total * 100, 1)

        onboarding_partners = [
            p for p in all_partners
            if p.get("estado_pipeline") == "Onboarding" and p.get("fecha_vinculacion")
        ]
        if onboarding_partners:
            today = _date.today()
            deltas = []
            for op in onboarding_partners:
                try:
                    fv = op["fecha_vinculacion"]
                    if isinstance(fv, str):
                        fv = _date.fromisoformat(fv[:10])
                    deltas.append((today - fv).days)
                except Exception:
                    pass
            avg_onboarding = round(sum(deltas) / len(deltas)) if deltas else 0
        else:
            avg_onboarding = 0

        c_ext1, c_ext2 = st.columns(2)
        c_ext1.metric(
            "Exposición PEP del Portafolio",
            f"{pep_pct}%",
            delta=f"{len(pep_list)} sujeto(s) PEP" if pep_list else "Sin PEP activos",
            delta_color="inverse" if pep_list else "off",
            help="% de aliados activos con Exposición Política — DDI obligatoria (GAFI R.12)",
        )
        c_ext2.metric(
            "Promedio Onboarding",
            f"{avg_onboarding} días" if avg_onboarding else "—",
            delta=f"{len(onboarding_partners)} en proceso" if onboarding_partners else "Sin registros",
            delta_color="off",
            help="Promedio de días transcurridos desde fecha de vinculación para aliados en Onboarding",
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Filtros de sidebar aplicados ──────────────────────────────────────
        filtro_pep   = st.session_state.get("filtro_pep", False)
        filtro_alto  = st.session_state.get("filtro_alto", False)
        vista_partners = list(all_partners)
        if filtro_pep:
            vista_partners = [p for p in vista_partners if p.get("es_pep")]
        if filtro_alto:
            vista_partners = [p for p in vista_partners
                              if p.get("nivel_riesgo") in ("Alto", "Muy Alto")]
        if filtro_pep or filtro_alto:
            etiquetas = []
            if filtro_pep:
                etiquetas.append("Solo PEP (GAFI R.12)")
            if filtro_alto:
                etiquetas.append("Solo Riesgo Alto / Muy Alto")
            st.info(
                f"🔍 Filtros activos: **{' · '.join(etiquetas)}** — "
                f"mostrando {len(vista_partners)} de {len(all_partners)} aliado(s)."
            )

        # ── Tabs EBR ─────────────────────────────────────────────────────────
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🔄 Vista de Pipeline",
            "🗺️ Mapa de Riesgos",
            "🚨 Alertas de Cumplimiento",
            "📈 Análisis de Tendencias",
            "📥 Centro de Reportes",
        ])
        with tab1:
            _tab_pipeline(stats_pipeline, vista_partners)
        with tab2:
            _tab_mapa_riesgos(stats_riesgo, sarlaft_stats, vista_partners)
        with tab3:
            _tab_alertas(proximas, pep_list, sarlaft_vencidas)
        with tab4:
            _tab_tendencias(repo, all_partners, stats_riesgo, total)
        with tab5:
            _tab_reportes(repo, user, session)
    finally:
        session.close()


# ── Página Listado de Partners ────────────────────────────────
def page_partners(user: dict):
    st.markdown("""
    <h1 style='font-size:1.8rem; font-weight:800; margin-bottom:4px;'>
        🤝 Partners y Aliados Estratégicos
    </h1>
    <p style='color:#9ca3af; font-size:0.9rem; margin-top:0;'>
        Gestión del ciclo de vida · Cambio de estado del Pipeline · Compliance SARLAFT
    </p>
    """, unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#293056;'>", unsafe_allow_html=True)

    # ── Filtros ──────────────────────────────────────────────────
    with st.expander("🔍 Filtros de Búsqueda y Auditoría", expanded=True):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            f_estado  = st.selectbox("Estado Pipeline", ["Todos"] + EstadosAliado.ALL)
            f_sarlaft = st.selectbox("Estado SARLAFT",  ["Todos"] + EstadosSARLAFT.ALL)
        with fc2:
            f_riesgo = st.selectbox("Nivel de Riesgo", ["Todos"] + NivelesRiesgo.ALL)
            f_tipo   = st.selectbox("Tipo de Aliado",  ["Todos"] + TiposAliado.ALL)
        with fc3:
            f_pep    = st.checkbox("Solo sujetos PEP (GAFI R.12)")
            f_search = st.text_input("Buscar por nombre o NIT", placeholder="🔍 Nombre o NIT...")

    session_gen = get_session()
    session = next(session_gen)
    try:
        repo = PartnerRepository(session)
        partners = repo.get_lista_enriquecida(
            estado_pipeline=None if f_estado  == "Todos" else f_estado,
            nivel_riesgo=   None if f_riesgo  == "Todos" else f_riesgo,
            estado_sarlaft= None if f_sarlaft == "Todos" else f_sarlaft,
            tipo_aliado=    None if f_tipo    == "Todos" else f_tipo,
            solo_pep=f_pep,
            search_text=f_search or None,
        )
        st.markdown(
            f"<div style='color:#9ca3af; font-size:0.85rem; margin-bottom:12px;'>"
            f"<strong style='color:#5fe9d0;'>{len(partners)}</strong> "
            f"registro(s) — ordenados por riesgo (EBR · GAFI R.1)</div>",
            unsafe_allow_html=True,
        )
        if not partners:
            st.info("Sin resultados con los filtros aplicados.")
            return

        vista = st.radio(
            "Vista de datos", ["📊 Tabla", "📋 Detalle por Partner"],
            horizontal=True, label_visibility="collapsed",
        )

        if vista == "📊 Tabla":
            df, col_cfg, cols = _build_table_df(partners)
            st.dataframe(df[cols], column_config=col_cfg,
                         hide_index=True, use_container_width=True)
        else:  # Detalle por Partner
            for p in partners:
                nc      = _riesgo_color(p.get("nivel_riesgo", ""))
                pep_tag = " ⚠️ PEP" if p.get("es_pep") else ""
                icon    = ("🔴" if p.get("nivel_riesgo") in ("Alto", "Muy Alto")
                           else "🟡" if p.get("nivel_riesgo") == "Medio" else "🟢")
                with st.expander(
                    f"{icon} **{p['nombre_razon_social']}** — {p['nit']}{pep_tag}"
                ):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown("**Datos Generales**")
                        st.write(f"Tipo: `{p['tipo_aliado']}`")
                        st.write(f"Vinculación: {p['fecha_vinculacion']}")
                        st.write(f"Ciudad: {p.get('ciudad', '—')}")
                        st.markdown(badge(p["estado_pipeline"]), unsafe_allow_html=True)
                    with c2:
                        st.markdown("**SARLAFT & Riesgo**")
                        st.markdown(
                            f"Nivel: <span style='color:{nc}; font-weight:700;'>"
                            f"{p['nivel_riesgo']}</span>",
                            unsafe_allow_html=True,
                        )
                        score = int(p.get("puntaje_riesgo") or 0)
                        st.progress(score / 100, text=f"Score: {score}/100")
                        st.write(f"SARLAFT: `{p['estado_sarlaft']}`")
                        st.write(f"PEP: {'⚠️ Sí' if p.get('es_pep') else '✅ No'}")
                        st.write(f"Listas: {'✅ Verificadas' if p.get('listas_verificadas') else '❌ Pendiente'}")
                    with c3:
                        st.markdown("**Debida Diligencia**")
                        st.write(f"Estado DD: `{p['estado_due_diligence']}`")
                        st.write(f"Nivel DD: `{p.get('nivel_due_diligence', '—')}`")
                        st.write(f"Contrato: {'✅ Firmado' if p.get('contrato_firmado') else '❌ Pendiente'}")
                        if p.get("fecha_proxima_revision"):
                            st.write(f"Próx. revisión: {p['fecha_proxima_revision']}")
                    # Cambio de estado
                    if user["rol"] in (Roles.ADMIN, Roles.COMPLIANCE, Roles.COMERCIAL):
                        transiciones = EstadosAliado.TRANSICIONES.get(p["estado_pipeline"], [])
                        if transiciones:
                            st.markdown("---")
                            ct1, ct2, ct3 = st.columns([1.5, 2.5, 1])
                            with ct1:
                                nuevo_estado = st.selectbox(
                                    "Cambiar estado →", transiciones,
                                    key=f"estado_{p['id']}"
                                )
                            with ct2:
                                motivo = st.text_input(
                                    "Motivo del cambio (obligatorio para auditoría)",
                                    key=f"motivo_{p['id']}",
                                    placeholder="Justificación..."
                                )
                            with ct3:
                                st.markdown("<br>", unsafe_allow_html=True)
                                if st.button("Aplicar", key=f"btn_{p['id']}", type="primary"):
                                    if not motivo.strip():
                                        st.warning("⚠️ El motivo es obligatorio para el log de auditoría.")
                                    else:
                                        try:
                                            repo.cambiar_estado(
                                                p["id"], nuevo_estado,
                                                cambiado_por=user["id"],
                                                motivo=motivo,
                                            )
                                            audit = AuditRepository(session)
                                            audit.registrar(
                                                username=user["username"],
                                                usuario_id=user["id"],
                                                accion="ESTADO_CHANGE",
                                                entidad="aliados",
                                                entidad_id=p["id"],
                                                descripcion=(
                                                    f"Pipeline: {p['estado_pipeline']} → "
                                                    f"{nuevo_estado}. Motivo: {motivo}"
                                                ),
                                            )
                                            st.success(f"✅ Estado → **{nuevo_estado}**")
                                            st.rerun()
                                        except ValueError as e:
                                            st.error(str(e))
    finally:
        session.close()


# ── Página Nuevo Partner ──────────────────────────────────────
def page_nuevo_partner(user: dict):
    if user["rol"] not in (Roles.ADMIN, Roles.COMPLIANCE, Roles.COMERCIAL):
        st.error("No tienes permisos para crear partners.")
        return

    st.markdown("""
    <h1 style='font-size:1.8rem; font-weight:800; margin-bottom:4px;'>
        ➕ Registrar Nuevo Partner
    </h1>
    <p style='color:#9ca3af; font-size:0.9rem; margin-top:0;'>Completa los datos del aliado</p>
    """, unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#293056;'>", unsafe_allow_html=True)

    with st.form("form_nuevo_partner", clear_on_submit=True):
        st.markdown('<p class="section-title">Información General</p>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Razón Social *", placeholder="Banco XYZ S.A.")
            nit    = st.text_input("NIT * (formato: 900123456-1)", placeholder="900123456-1")
            tipo   = st.selectbox("Tipo de Aliado *", TiposAliado.ALL)
        with col2:
            fecha_vinc = st.date_input("Fecha de Vinculación *", value=date.today())
            ciudad     = st.text_input("Ciudad", placeholder="Bogotá")
            departamento = st.text_input("Departamento", placeholder="Cundinamarca")

        st.markdown('<p class="section-title">Contacto</p>', unsafe_allow_html=True)
        col3, col4 = st.columns(2)
        with col3:
            rep_legal = st.text_input("Representante Legal")
            email     = st.text_input("Email de Contacto")
        with col4:
            cargo     = st.text_input("Cargo del Representante")
            telefono  = st.text_input("Teléfono")

        st.markdown('<p class="section-title">Compliance SARLAFT</p>', unsafe_allow_html=True)
        col5, col6 = st.columns(2)
        with col5:
            nivel_riesgo = st.selectbox("Nivel de Riesgo Inicial", NivelesRiesgo.ALL, index=1)
            es_pep       = st.checkbox("¿Es Persona Expuesta Políticamente (PEP)?")
        with col6:
            freq_revision = st.selectbox("Frecuencia de Revisión SARLAFT",
                                         ["Anual", "Semestral", "Trimestral", "Mensual"])
            observaciones = st.text_area("Observaciones de Compliance", height=80)

        submitted = st.form_submit_button("💾 Registrar Partner", type="primary")

    if submitted:
        import re
        if not nombre or not nit or not tipo:
            st.error("Los campos marcados con * son obligatorios.")
            return
        if not re.match(r"^\d{8,10}-\d$", nit):
            st.error("Formato de NIT inválido. Use: 900123456-1")
            return

        from db.models import AliadoCreate
        try:
            nuevo = AliadoCreate(
                nombre_razon_social=nombre,
                nit=nit,
                tipo_aliado=tipo,
                fecha_vinculacion=fecha_vinc,
                ciudad=ciudad or None,
                departamento_geo=departamento or None,
                representante_legal=rep_legal or None,
                cargo_representante=cargo or None,
                email_contacto=email or None,
                telefono_contacto=telefono or None,
                nivel_riesgo=nivel_riesgo,
                es_pep=es_pep,
                frecuencia_revision=freq_revision,
                observaciones_compliance=observaciones or None,
            )
            session_gen = get_session()
            session = next(session_gen)
            try:
                repo  = PartnerRepository(session)
                audit = AuditRepository(session)
                nuevo_id = repo.create(nuevo, creado_por=user["id"])
                audit.registrar(
                    username=user["username"],
                    usuario_id=user["id"],
                    accion="CREATE",
                    entidad="aliados",
                    entidad_id=nuevo_id,
                    descripcion=f"Nuevo partner registrado: {nombre} (NIT: {nit})",
                    valores_nuevos=nuevo.model_dump(mode="json"),
                )
                st.success(f"✅ **{nombre}** registrado exitosamente con ID #{nuevo_id}")
            finally:
                session.close()
        except Exception as e:
            st.error(f"Error al registrar: {e}")


# ── Página Log de Auditoría ───────────────────────────────────
def page_auditoria(user: dict):
    if user["rol"] not in (Roles.ADMIN, Roles.COMPLIANCE):
        st.error("Acceso restringido. Solo roles Admin y Compliance.")
        return

    st.markdown("""
    <h1 style='font-size:1.8rem; font-weight:800; margin-bottom:4px;'>
        📋 Log de Auditoría
    </h1>
    <p style='color:#9ca3af; font-size:0.9rem; margin-top:0;'>Registro inmutable de todas las acciones del sistema</p>
    """, unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#293056;'>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        f_entidad = st.selectbox("Entidad", ["Todas", "aliados", "usuarios"])
    with col2:
        f_accion = st.selectbox("Acción", ["Todas", "CREATE", "UPDATE", "DELETE",
                                            "LOGIN", "ESTADO_CHANGE", "EXPORT"])
    with col3:
        f_limit = st.number_input("Registros a mostrar", min_value=10, max_value=1000, value=100)

    session_gen = get_session()
    session = next(session_gen)
    try:
        audit = AuditRepository(session)
        logs = audit.list_log(
            entidad=None if f_entidad == "Todas" else f_entidad,
            accion=None if f_accion == "Todas" else f_accion,
            limit=int(f_limit),
        )
        st.markdown(f"**{len(logs)} evento(s)**")
        if logs:
            import pandas as pd
            df = pd.DataFrame(logs)[["created_at", "username", "accion",
                                      "entidad", "entidad_id", "descripcion", "resultado"]]
            df.columns = ["Fecha", "Usuario", "Acción", "Entidad", "ID", "Descripción", "Resultado"]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No hay eventos registrados aún.")
    finally:
        session.close()


# ── Router principal ──────────────────────────────────────────
def main():
    from app.auth.login import require_auth
    user = require_auth()   # detiene la ejecución y muestra login si no autenticado

    # ── Advertencia de seguridad visible solo en desarrollo con clave insegura ──
    if SECRET_KEY_IS_DEFAULT and APP_ENV != "production":
        st.warning(
            "🔓 **Modo Desarrollo** — `SECRET_KEY` no está configurada o usa el valor "
            "por defecto. Las cookies de sesión **no están firmadas de forma segura**. "
            "Configura `SECRET_KEY` en tus variables de entorno antes de desplegar.",
            icon="⚠️",
        )

    page = sidebar(user)

    if page == "📊 Dashboard":
        page_dashboard(user)
    elif page == "🤝 Partners":
        page_partners(user)
    elif page == "➕ Nuevo Partner":
        page_nuevo_partner(user)
    elif page == "📋 Log de Auditoría":
        page_auditoria(user)


if __name__ == "__main__":
    main()
