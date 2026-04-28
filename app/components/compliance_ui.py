"""
app/components/compliance_ui.py
Centro Documental de Cumplimiento -- AdamoServices Partner Manager.
Gestor de documentos regulatorios: Politicas, Manuales, Onboarding,
Etica, Riesgos, Empresariales y Capacitacion.
"""

from __future__ import annotations
import logging
from typing import Optional
import streamlit as st

from db.database import get_session
from db.repositories.compliance_repo import ComplianceRepository
from config.settings import Roles

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Paleta corporativa
# ─────────────────────────────────────────────────────────────
_C_BG     = "#111827"
_C_CARD   = "#1a2236"
_C_BORDER = "#293056"
_C_CYAN   = "#5fe9d0"
_C_VIOLET = "#7839ee"
_C_AMBER  = "#f59e0b"
_C_RED    = "#ef4444"
_C_GREEN  = "#22c55e"
_C_GRAY   = "#9ca3af"
_C_TEXT   = "#e2e8f0"

_ESTADO_COLOR: dict[str, tuple[str, str]] = {
    "Vigente":   (_C_GREEN,  "#14532d22"),
    "Pendiente": (_C_AMBER,  "#78350f22"),
    "Vencido":   (_C_RED,    "#7f1d1d22"),
    "Archivado": (_C_GRAY,   "#1f293700"),
}

_FORMATO_COLOR: dict[str, tuple[str, str]] = {
    "PDF":  (_C_RED,    "#450a0a22"),
    "DOCX": ("#3b82f6", "#1e3a5f22"),
    "XLSX": (_C_GREEN,  "#14532d22"),
    "PPTX": ("#f97316", "#431407aa"),
    "OTRO": (_C_GRAY,   "#1f2937aa"),
}

_CARPETA_ICON: dict[str, str] = {
    "Politicas":   "📋",
    "Manuales":    "📖",
    "Onboarding":  "🔗",
    "Etica":       "⚖️",
    "Riesgos":     "🔍",
    "Empresariales":"🏢",
    "Capacitacion":"🎓",
}

_CARPETAS_ORDEN = [
    "Politicas", "Manuales", "Onboarding",
    "Etica", "Riesgos", "Empresariales", "Capacitacion",
]

_ROLES_EDITOR = {Roles.ADMIN, Roles.COMPLIANCE}


# ─────────────────────────────────────────────────────────────
# Helpers de renderizado
# ─────────────────────────────────────────────────────────────

def _badge(label: str, fg: str, bg: str) -> str:
    return (
        f'<span style="background:{bg};color:{fg};border:1px solid {fg}44;'
        f'border-radius:4px;padding:2px 8px;font-size:0.72rem;'
        f'font-weight:600;letter-spacing:0.04em;">{label}</span>'
    )


def _kpi_cards(stats: dict) -> None:
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        (c1, "📄 Total",    stats["total"],      _C_CYAN),
        (c2, "✅ Vigentes", stats["vigentes"],    _C_GREEN),
        (c3, "⏳ Pendientes",stats["pendientes"], _C_AMBER),
        (c4, "⚠️ Vencidos", stats["vencidos"],   _C_RED),
    ]
    for col, titulo, valor, color in cards:
        col.markdown(
            f"""<div style="background:{_C_CARD};border:1px solid {_C_BORDER};
            border-left:4px solid {color};border-radius:8px;padding:16px 18px;
            text-align:center;">
            <div style="color:{_C_GRAY};font-size:0.78rem;margin-bottom:4px;">
                {titulo}
            </div>
            <div style="color:{color};font-size:2rem;font-weight:700;
                line-height:1;">{valor}</div>
            </div>""",
            unsafe_allow_html=True,
        )


def _doc_card(doc: dict, puede_editar: bool) -> None:
    """Renderiza un documento como tarjeta oscura con badges."""
    estado = doc.get("estado", "Vigente")
    fmt    = doc.get("formato", "OTRO")
    e_fg, e_bg = _ESTADO_COLOR.get(estado, (_C_GRAY, "#00000000"))
    f_fg, f_bg = _FORMATO_COLOR.get(fmt,   (_C_GRAY, "#00000000"))

    badge_estado  = _badge(estado, e_fg, e_bg)
    badge_formato = _badge(fmt,    f_fg, f_bg)

    url = doc.get("url_documento")
    link_html = (
        f'<a href="{url}" target="_blank" style="color:{_C_CYAN};'
        f'text-decoration:none;font-size:0.78rem;">🔗 Abrir documento</a>'
        if url else
        '<span style="color:#4b5563;font-size:0.78rem;">Sin enlace</span>'
    )

    fecha = doc.get("fecha_emision") or "-"
    ver   = doc.get("version", "-")
    codigo = doc.get("codigo", "")
    nombre = doc.get("nombre", "Sin nombre")
    desc   = doc.get("descripcion") or ""

    st.markdown(
        f"""<div style="background:{_C_CARD};border:1px solid {_C_BORDER};
        border-radius:8px;padding:16px;margin-bottom:10px;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;
            flex-wrap:wrap;gap:6px;margin-bottom:8px;">
            <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
                {badge_formato}{badge_estado}
            </div>
            <div style="color:{_C_GRAY};font-size:0.72rem;">{codigo}</div>
        </div>
        <div style="color:{_C_TEXT};font-weight:600;font-size:0.92rem;
            margin-bottom:2px;">{nombre}</div>
        {'<div style="color:'+_C_GRAY+';font-size:0.78rem;margin-bottom:6px;">'+desc+'</div>' if desc else ''}
        <div style="display:flex;gap:16px;align-items:center;margin-top:8px;
            flex-wrap:wrap;">
            <span style="color:{_C_GRAY};font-size:0.75rem;">v{ver} &nbsp;|&nbsp; {fecha}</span>
            {link_html}
        </div>
        </div>""",
        unsafe_allow_html=True,
    )

    if puede_editar:
        btn_key = f"nv_btn_{doc['id']}"
        if st.button("✏️ Nueva Versión", key=btn_key, use_container_width=False):
            st.session_state[f"_nv_open_{doc['id']}"] = True

        if st.session_state.get(f"_nv_open_{doc['id']}"):
            _form_nueva_version(doc)


def _form_nueva_version(doc: dict) -> None:
    form_key = f"form_nv_{doc['id']}"
    with st.form(form_key, clear_on_submit=True):
        st.markdown(
            f"**Nueva versión para:** `{doc['nombre']}`",
            unsafe_allow_html=False,
        )
        nueva_version = st.text_input(
            "Nueva versión", value=doc.get("version", "1.0"),
            placeholder="ej. 1.1"
        )
        nueva_url = st.text_input(
            "URL del documento",
            value=doc.get("url_documento") or "",
            placeholder="https://..."
        )
        descripcion_cambio = st.text_area(
            "Descripción del cambio", placeholder="Breve descripción...", height=80
        )
        guardar = st.form_submit_button("💾 Guardar versión")

    if guardar:
        if not nueva_version.strip():
            st.error("La versión es obligatoria.")
            return
        try:
            from streamlit import session_state as ss
            user = ss.get("user", {})
            username = user.get("username") or user.get("usuario") or "sistema"
            with next(get_session()) as session:
                repo = ComplianceRepository(session)
                repo.nueva_version(
                    doc_id=doc["id"],
                    nueva_version=nueva_version.strip(),
                    nueva_url=nueva_url.strip() or None,
                    descripcion_cambio=descripcion_cambio.strip() or None,
                    actualizado_por=username,
                )
            st.success(f"Versión {nueva_version} guardada correctamente.")
            st.session_state[f"_nv_open_{doc['id']}"] = False
            st.rerun()
        except Exception as exc:
            logger.exception("[Compliance] Error actualizando version")
            st.error(f"Error al guardar: {exc}")


def _form_nuevo_documento(user: dict) -> None:
    """Formulario para agregar un nuevo documento (admin/compliance)."""
    with st.expander("➕ Agregar nuevo documento", expanded=False):
        with st.form("form_nuevo_doc", clear_on_submit=True):
            fa, fb = st.columns(2)
            with fa:
                carpeta = st.selectbox("Carpeta *", _CARPETAS_ORDEN)
                codigo  = st.text_input("Código", placeholder="ej. POL-004")
                nombre  = st.text_input("Nombre del documento *")
                version = st.text_input("Versión", value="1.0")
            with fb:
                estado  = st.selectbox("Estado", ["Vigente","Pendiente","Vencido"])
                formato = st.selectbox("Formato", ["PDF","DOCX","XLSX","PPTX","OTRO"])
                url_doc = st.text_input("URL documento", placeholder="https://...")
                fecha_emision    = st.date_input("Fecha emisión", value=None)
                fecha_vencimiento= st.date_input("Fecha vencimiento", value=None)
            descripcion = st.text_area("Descripción", height=70)
            guardar = st.form_submit_button("💾 Crear documento")

        if guardar:
            if not nombre.strip():
                st.error("El nombre del documento es obligatorio.")
                return
            try:
                username = user.get("username") or user.get("usuario") or "sistema"
                with next(get_session()) as session:
                    repo = ComplianceRepository(session)
                    new_id = repo.crear(
                        data={
                            "carpeta": carpeta,
                            "codigo":  codigo.strip(),
                            "nombre":  nombre.strip(),
                            "descripcion": descripcion.strip() or None,
                            "version": version.strip() or "1.0",
                            "estado":  estado,
                            "formato": formato,
                            "url_documento": url_doc.strip() or None,
                            "fecha_emision":     str(fecha_emision) if fecha_emision else None,
                            "fecha_vencimiento": str(fecha_vencimiento) if fecha_vencimiento else None,
                        },
                        creado_por=username,
                    )
                st.success(f"Documento creado correctamente (id={new_id}).")
                st.rerun()
            except Exception as exc:
                logger.exception("[Compliance] Error creando documento")
                st.error(f"Error al crear: {exc}")


# ─────────────────────────────────────────────────────────────
# Pagina principal
# ─────────────────────────────────────────────────────────────

def page_compliance(user: dict) -> None:
    """Pagina principal del Centro Documental de Cumplimiento."""

    puede_editar = user.get("rol") in _ROLES_EDITOR

    st.markdown(
        "<h1 style='margin-bottom:4px;'>📚 Centro Documental de Cumplimiento</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#9ca3af;margin-top:0;'>Repositorio centralizado de "
        "politicas, manuales y documentos regulatorios de ADAMO Services.</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr style='border-color:#293056;margin:0 0 20px;'>", unsafe_allow_html=True)

    # ── Cargar datos ─────────────────────────────────────────────────────────
    try:
        with next(get_session()) as session:
            repo  = ComplianceRepository(session)
            stats = repo.get_stats()
            todos = repo.get_documentos()
    except Exception as exc:
        logger.exception("[Compliance] Error cargando documentos")
        st.error(f"Error al conectar con la base de datos: {exc}")
        return

    # ── KPI cards ────────────────────────────────────────────────────────────
    _kpi_cards(stats)
    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

    # ── Alertas de estado ────────────────────────────────────────────────────
    if stats["vencidos"] > 0:
        st.warning(
            f"⚠️ **{stats['vencidos']} documento(s) vencido(s)** requieren actualizacion urgente.",
            icon=None,
        )
    if stats["pendientes"] > 0:
        st.info(
            f"⏳ **{stats['pendientes']} documento(s) pendiente(s)** de revision.",
            icon=None,
        )

    # ── Formulario nuevo documento (admin/compliance) ─────────────────────────
    if puede_editar:
        _form_nuevo_documento(user)

    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

    # ── Tabs por carpeta ──────────────────────────────────────────────────────
    tab_labels = ["📄 Todos"] + [
        f"{_CARPETA_ICON.get(c,'📁')} {c}" for c in _CARPETAS_ORDEN
    ]
    tabs = st.tabs(tab_labels)

    for tab_idx, tab in enumerate(tabs):
        with tab:
            if tab_idx == 0:
                carpeta_filtro: Optional[str] = None
            else:
                carpeta_filtro = _CARPETAS_ORDEN[tab_idx - 1]

            docs_tab = (
                [d for d in todos if d["carpeta"] == carpeta_filtro]
                if carpeta_filtro
                else todos
            )

            # Filtro de estado (inline, dentro del tab)
            filtro_estado = st.selectbox(
                "Estado",
                ["Todos", "Vigente", "Pendiente", "Vencido"],
                key=f"fe_{tab_idx}",
                label_visibility="collapsed",
            )
            if filtro_estado != "Todos":
                docs_tab = [d for d in docs_tab if d["estado"] == filtro_estado]

            if not docs_tab:
                st.info("No hay documentos con los filtros seleccionados.")
                continue

            # Barra de progreso carpeta (solo en tabs de carpeta especifica)
            if carpeta_filtro:
                carpeta_stats = next(
                    (c for c in stats["por_carpeta"] if c["carpeta"] == carpeta_filtro),
                    None,
                )
                if carpeta_stats and carpeta_stats["total"] > 0:
                    pct = carpeta_stats["vigentes"] / carpeta_stats["total"]
                    st.markdown(
                        f"<div style='margin-bottom:6px;color:{_C_GRAY};"
                        f"font-size:0.78rem;'>Vigentes: "
                        f"{carpeta_stats['vigentes']}/{carpeta_stats['total']}</div>",
                        unsafe_allow_html=True,
                    )
                    st.progress(pct)

            # Grid de 2 columnas
            col_a, col_b = st.columns(2)
            for idx, doc in enumerate(docs_tab):
                col = col_a if idx % 2 == 0 else col_b
                with col:
                    _doc_card(doc, puede_editar)
