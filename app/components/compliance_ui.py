"""
app/components/compliance_ui.py
Centro Documental de Cumplimiento -- AdamoServices Partner Manager.
Gestor de documentos regulatorios (11 carpetas): Politicas, Manuales,
Onboarding, Procesos y Procedimientos, Governanza, Empresariales,
Capacitacion, Contratos, Actas y Formatos, Matrices y Tecnologia.
"""

from __future__ import annotations
import html as _html
import logging
import re as _re
from typing import Optional
from urllib.parse import urlparse as _urlparse
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


def _hex_fill(h: str, alpha: float = 0.13) -> str:
    """Convierte '#rrggbb' a 'rgba(r,g,b,a)' para Plotly fillcolor."""
    r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
    return f"rgba({r},{g},{b},{alpha})"

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
    "Procesos y Procedimientos": "⚙️",
    "Governanza":  "🛡️",
    "Empresariales":"🏢",
    "Capacitacion":"🎓",
    "Contratos":   "📝",
    "Actas y Formatos": "📑",
    "Matrices":    "📊",
    "Tecnologia":  "💻",
}

_CARPETAS_ORDEN = [
    "Politicas", "Manuales", "Onboarding",
    "Procesos y Procedimientos", "Governanza", "Empresariales", "Capacitacion",
    "Contratos", "Actas y Formatos", "Matrices", "Tecnologia",
]

_ROLES_EDITOR = {Roles.ADMIN, Roles.COMPLIANCE}

# ─────────────────────────────────────────────────────────────
# Entidades corporativas
# ─────────────────────────────────────────────────────────────
_EMPRESAS = ["Todas", "Holdings BPO", "PayCOP", "Adamo Services"]
_EMPRESA_COLOR: dict[str, str] = {
    "Holdings BPO":    _C_VIOLET,
    "PayCOP":          _C_CYAN,
    "Adamo Services":  _C_AMBER,
}

# ─────────────────────────────────────────────────────────────
# Utilidades OneDrive / SharePoint
# ─────────────────────────────────────────────────────────────
_ALLOWED_ONEDRIVE = frozenset({"onedrive.live.com", "1drv.ms"})
_SHAREPOINT_RE    = _re.compile(r'^[a-zA-Z0-9-]+\.sharepoint\.com$', _re.IGNORECASE)


def _is_onedrive_url(url: str) -> bool:
    """True si la URL es de OneDrive personal o SharePoint corporativo."""
    if not url:
        return False
    try:
        netloc = _urlparse(url).netloc
        return netloc in _ALLOWED_ONEDRIVE or bool(_SHAREPOINT_RE.match(netloc))
    except Exception:
        return False


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


def _doc_card(doc: dict, puede_editar: bool, key_prefix: str = "") -> None:
    """Tarjeta de documento — borde dinámico por estado, layout moderno."""
    estado  = doc.get("estado",  "Vigente")
    fmt     = doc.get("formato", "OTRO")
    empresa = doc.get("empresa")
    doc_id  = doc["id"]

    e_fg, e_bg = _ESTADO_COLOR.get(estado, (_C_GRAY, "#00000000"))
    f_fg, f_bg = _FORMATO_COLOR.get(fmt,   (_C_GRAY, "#00000000"))

    badge_estado  = _badge(estado, e_fg, e_bg)
    badge_formato = _badge(fmt,    f_fg, f_bg)
    badge_empresa = ""
    if empresa:
        emp_c = _EMPRESA_COLOR.get(empresa, _C_GRAY)
        badge_empresa = _badge(empresa, emp_c, emp_c + "22")

    url      = doc.get("url_documento")
    fecha_raw = doc.get("fecha_emision")
    fecha    = str(fecha_raw) if fecha_raw else "—"
    ver      = _html.escape(str(doc.get("version", "—")))
    codigo   = _html.escape(str(doc.get("codigo",  "")))
    nombre   = _html.escape(str(doc.get("nombre",  "Sin nombre")))
    desc_raw = doc.get("descripcion") or ""
    desc     = _html.escape(desc_raw)
    carpeta  = doc.get("carpeta", "")

    # Badge ISO: carpetas críticas para norma ISO 27001 / 37001
    _ISO_CRITICAS = frozenset({"Politicas", "Matrices"})
    iso_badge = (
        '&nbsp;<span style="background:#312e81;color:#a5b4fc;'
        'font-size:0.62rem;padding:1px 5px;border-radius:4px;'
        'font-weight:700">ISO ✓</span>'
        if carpeta in _ISO_CRITICAS else ""
    )

    # Pre-computar borde/glow según estado (sin backslash en f-strings)
    card_border_top  = e_fg
    card_border_side = e_fg + "44"
    has_url_icon     = "🔗" if url else "🔒"

    st.markdown(
        # Contenedor — borde superior de color por estado
        f'<div style="background:{_C_CARD};'
        f'border:1px solid {card_border_side};'
        f'border-top:3px solid {card_border_top};'
        f'border-radius:10px;padding:14px 16px 12px;margin-bottom:4px;">'

        # Fila 1: badges (formato · estado · empresa) + código
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:flex-start;flex-wrap:wrap;gap:4px;margin-bottom:10px;">'
        f'<div style="display:flex;gap:5px;flex-wrap:wrap;align-items:center">'
        f'{badge_formato}&nbsp;{badge_estado}'
        + (f'&nbsp;{badge_empresa}' if badge_empresa else '')
        + f'</div>'
        + (
            f'<div style="color:#94a3b8;font-size:0.68rem;background:#0f172a;'
            f'padding:2px 8px;border-radius:4px;font-family:monospace;'
            f'white-space:nowrap">{codigo}</div>'
            if codigo else ''
        )
        + f'</div>'

        # Fila 2: título + badge ISO
        f'<div style="color:{_C_TEXT};font-weight:700;font-size:0.9rem;'
        f'line-height:1.35;margin-bottom:6px;">{nombre}{iso_badge}</div>'

        # Fila 3: descripción truncada — evidencia de control de cambios
        + (
            f'<div style="color:{_C_GRAY};font-size:0.74rem;line-height:1.45;'
            f'margin-bottom:8px;display:-webkit-box;-webkit-line-clamp:2;'
            f'-webkit-box-orient:vertical;overflow:hidden;'
            f'font-style:italic">"{desc}"</div>'
            if desc else ''
        )

        # Footer: versión + fecha + icono URL
        + f'<div style="display:flex;align-items:center;gap:6px;'
        f'margin-top:8px;padding-top:8px;border-top:1px solid #1e2740;">'
        f'<span style="background:#0f172a;color:{_C_GRAY};font-size:0.68rem;'
        f'padding:2px 7px;border-radius:4px;font-family:monospace;">v{ver}</span>'
        f'<span style="color:#475569;font-size:0.7rem;flex:1">{fecha}</span>'
        f'<span style="font-size:0.75rem;color:{"#22c55e" if url else "#475569"}">'
        f'{has_url_icon}</span>'
        f'</div>'

        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Botones de acción ──────────────────────────────────────────────────────
    nv_open_key = f"_nv_open_{key_prefix}{doc_id}"

    if url:
        if puede_editar:
            c_edit, c_open = st.columns(2)
        else:
            c_open = st.columns(1)[0]

        if puede_editar:
            is_open = st.session_state.get(nv_open_key, False)
            btn_lbl = "🔼 Cerrar" if is_open else "✏️ Editar"
            with c_edit:
                if st.button(btn_lbl, key=f"{key_prefix}nv_btn_{doc_id}",
                             use_container_width=True):
                    st.session_state[nv_open_key] = not is_open

        with c_open:
            st.link_button("🔗 Abrir", url=url, use_container_width=True)

    else:
        if puede_editar:
            is_open = st.session_state.get(nv_open_key, False)
            btn_lbl = "🔼 Cerrar" if is_open else "✏️ Editar"
            if st.button(btn_lbl, key=f"{key_prefix}nv_btn_{doc_id}",
                         use_container_width=True):
                st.session_state[nv_open_key] = not is_open
        no_url_msg = "añade la URL en ✏️ Editar" if puede_editar else "requiere URL para habilitar acceso"
        st.markdown(
            f'<div style="color:#475569;font-size:0.7rem;margin-top:2px;">'
            f'🔒 Sin enlace — {no_url_msg}</div>',
            unsafe_allow_html=True,
        )

    # Formulario de edición (inline)
    if puede_editar and st.session_state.get(nv_open_key):
        _form_editar(doc, key_prefix=key_prefix)

    st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)


def _form_editar(doc: dict, key_prefix: str = "") -> None:
    """Editor integral de metadatos: título, carpeta, empresa, estado, url, versión."""
    form_key    = f"{key_prefix}form_edit_{doc['id']}"
    nv_open_key = f"_nv_open_{key_prefix}{doc['id']}"

    _emp_opts    = ["", "Holdings BPO", "PayCOP", "Adamo Services"]
    _estado_opts = ["Vigente", "Pendiente", "Vencido"]

    emp_actual  = doc.get("empresa") or ""
    emp_idx     = _emp_opts.index(emp_actual) if emp_actual in _emp_opts else 0
    est_actual  = doc.get("estado", "Vigente")
    est_idx     = _estado_opts.index(est_actual) if est_actual in _estado_opts else 0
    carp_actual = doc.get("carpeta", _CARPETAS_ORDEN[0])
    carp_idx    = _CARPETAS_ORDEN.index(carp_actual) if carp_actual in _CARPETAS_ORDEN else 0

    with st.form(form_key, clear_on_submit=False):
        st.markdown(f"**Editar:** `{doc.get('nombre', '')}`", unsafe_allow_html=False)
        c1, c2 = st.columns(2)
        with c1:
            nuevo_nombre  = st.text_input("Título *",  value=(doc.get("nombre") or "").replace("}", "").strip())
            nuevo_codigo  = st.text_input("Código", value=doc.get("codigo") or "", placeholder="ej. POL-001")
            nueva_carpeta = st.selectbox("Carpeta",    options=_CARPETAS_ORDEN, index=carp_idx)
            nuevo_estado  = st.selectbox("Estado",     options=_estado_opts,    index=est_idx)
        with c2:
            nueva_empresa = st.selectbox(
                "Empresa",
                options=_emp_opts,
                index=emp_idx,
                format_func=lambda x: x if x else "Compartido",
            )
            nueva_version = st.text_input("Versión", value=doc.get("version", "1.0"))
        nueva_url = st.text_input(
            "URL del documento",
            value=doc.get("url_documento") or "",
            placeholder="https://empresa.sharepoint.com/…",
        )
        descripcion_cambio = st.text_area(
            "Descripción del cambio (auditoría)", placeholder="Breve descripción…", height=68
        )
        guardar = st.form_submit_button("💾 Guardar cambios")

    if guardar:
        if not nuevo_nombre.strip():
            st.error("El título es obligatorio.")
            return
        try:
            from streamlit import session_state as ss
            user     = ss.get("user", {})
            username = user.get("username") or user.get("usuario") or "sistema"
            data = {
                "carpeta":           nueva_carpeta,
                "codigo":            nuevo_codigo.strip().upper(),
                "nombre":            nuevo_nombre.replace("}", "").strip(),
                "descripcion":       descripcion_cambio.strip() or doc.get("descripcion"),
                "version":           nueva_version.strip() or doc.get("version", "1.0"),
                "estado":            nuevo_estado,
                "formato":           doc.get("formato", "PDF"),
                "url_documento":     nueva_url.strip() or None,
                "fecha_emision":     doc.get("fecha_emision"),
                "fecha_vencimiento": doc.get("fecha_vencimiento"),
                "empresa":           nueva_empresa or None,
            }
            with next(get_session()) as session:
                from db.repositories.audit_repo import AuditRepository
                repo  = ComplianceRepository(session)
                audit = AuditRepository(session)
                repo.actualizar(doc["id"], data, actualizado_por=username)
                audit.registrar(
                    username=username,
                    accion="UPDATE",
                    entidad="compliance_documentos",
                    descripcion=descripcion_cambio.strip() or f"Edición metadatos doc id={doc['id']}",
                    entidad_id=doc["id"],
                    valores_anteriores={
                        "codigo":        doc.get("codigo"),
                        "nombre":        doc.get("nombre"),
                        "carpeta":       doc.get("carpeta"),
                        "empresa":       doc.get("empresa"),
                        "estado":        doc.get("estado"),
                        "version":       doc.get("version"),
                        "url_documento": doc.get("url_documento"),
                    },
                    valores_nuevos=data,
                    resultado="exitoso",
                )
            st.success("Documento actualizado correctamente.")
            doc_id_str = str(doc["id"])
            for k in list(st.session_state.keys()):
                if doc_id_str in k and (
                    k.startswith("_prev_") or k.startswith("_dldata_") or k.startswith("_nv_open_")
                ):
                    del st.session_state[k]
            st.rerun()
        except Exception as exc:
            logger.exception("[Compliance] Error actualizando documento")
            st.error(f"Error al guardar: {exc}")


def _form_nuevo_documento(
    user: dict,
    carpeta_default: str | None = None,
    empresa_default: str | None = None,
) -> None:
    """Formulario para agregar un nuevo documento (admin/compliance)."""
    with st.expander(
        "➕ Cargar nuevo documento en esta carpeta" if carpeta_default else "➕ Cargar nuevo documento",
        expanded=(carpeta_default is None),   # abierto por defecto cuando es el form global
    ):
        # Clave única por empresa para evitar DuplicateWidgetID
        form_key = f"form_upload_{empresa_default or 'X'}"
        with st.form(form_key, clear_on_submit=True):
            fa, fb = st.columns(2)
            with fa:
                # Empresa: pre-seleccionada y bloqueada cuando viene del filtro
                _emp_opts = ["(Compartido)"] + _EMPRESAS[1:]
                emp_idx = _emp_opts.index(empresa_default) if empresa_default in _emp_opts else 0
                empresa = st.selectbox(
                    "Empresa",
                    _emp_opts,
                    index=emp_idx,
                    disabled=empresa_default is not None,
                    help="Entidad propietaria. '(Compartido)' es visible para todas.",
                )
                # Carpeta: pre-seleccionada y bloqueada cuando viene de la tab
                carpeta_idx = _CARPETAS_ORDEN.index(carpeta_default) if carpeta_default in _CARPETAS_ORDEN else 0
                carpeta = st.selectbox(
                    "Carpeta *",
                    _CARPETAS_ORDEN,
                    index=carpeta_idx,
                    disabled=carpeta_default is not None,
                )
                codigo  = st.text_input("Código", placeholder="ej. POL-004")
                nombre  = st.text_input("Nombre del documento *")
                version = st.text_input("Versión", value="1.0")
            with fb:
                estado  = st.selectbox("Estado", ["Vigente", "Pendiente", "Vencido"])
                formato = st.selectbox("Formato", ["PDF", "DOCX", "XLSX", "PPTX", "OTRO"])
                url_doc = st.text_input(
                    "URL del documento",
                    placeholder="https://empresa.sharepoint.com/sites/.../documento.pdf",
                )
                fecha_emision     = st.date_input("Fecha emisión",    value=None)
                fecha_vencimiento = st.date_input("Fecha vencimiento", value=None)
            descripcion = st.text_area("Descripción", height=70)
            guardar = st.form_submit_button("💾 Crear documento")

        if guardar:
            if not nombre.strip():
                st.error("El nombre del documento es obligatorio.")
                return
            empresa_val = None if empresa == "(Compartido)" else empresa
            url_clean   = url_doc.strip() or None
            if url_clean and not _is_onedrive_url(url_clean):
                st.warning(
                    "⚠️ La URL no parece ser de OneDrive o SharePoint. "
                    "El botón 🔗 Abrir abrirá el enlace en una nueva pestaña de todas formas."
                )
            try:
                username = user.get("username") or user.get("usuario") or "sistema"
                with next(get_session()) as session:
                    repo = ComplianceRepository(session)
                    new_id = repo.crear(
                        data={
                            "empresa":          empresa_val,
                            "carpeta":          carpeta,
                            "codigo":           codigo.strip(),
                            "nombre":           nombre.strip(),
                            "descripcion":      descripcion.strip() or None,
                            "version":          version.strip() or "1.0",
                            "estado":           estado,
                            "formato":          formato,
                            "url_documento":    url_clean,
                            "fecha_emision":    str(fecha_emision)     if fecha_emision     else None,
                            "fecha_vencimiento":str(fecha_vencimiento) if fecha_vencimiento else None,
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

    # Limpiar cualquier caché residual de Streamlit (defensivo)
    st.cache_data.clear()

    puede_editar = user.get("rol") in _ROLES_EDITOR

    st.markdown(
        "<h1 style='margin-bottom:4px;'>📚 Centro Documental de Cumplimiento</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#9ca3af;margin-top:0;'>Repositorio centralizado de "
        "políticas, manuales y documentos regulatorios de ADAMO Services.</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr style='border-color:#293056;margin:0 0 16px;'>", unsafe_allow_html=True)

    # ── Filtro por empresa (control segmentado) ───────────────────────────
    filtro_empresa_raw: str = st.radio(
        "Filtrar por empresa",
        options=_EMPRESAS,
        horizontal=True,
        key="filtro_empresa_cd",
    )
    filtro_empresa: Optional[str] = (
        None if filtro_empresa_raw == "Todas" else filtro_empresa_raw
    )
    st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

    # ── Cargar datos (filtrados por empresa) ──────────────────────────────
    try:
        with next(get_session()) as session:
            repo  = ComplianceRepository(session)
            stats = repo.get_stats(empresa=filtro_empresa)
            todos = repo.get_documentos(empresa=filtro_empresa)
    except Exception as exc:
        logger.exception("[Compliance] Error cargando documentos")
        st.error(f"Error al conectar con la base de datos: {exc}")
        return
    logger.info("[Compliance] empresa=%s docs=%d", filtro_empresa or "todas", len(todos))

    # ── KPI cards (siempre visibles) ─────────────────────────────────────────
    _kpi_cards(stats)
    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

    # ── Estado vacío: mensaje amigable (no hace return — las tabs siguen) ────
    if stats["total"] == 0 and len(todos) == 0:
        st.markdown(
            f'<div style="background:{_C_CARD};border:1px solid {_C_BORDER};'
            f'border-radius:10px;padding:28px 24px;text-align:center;">'
            f'<div style="font-size:2.4rem;margin-bottom:12px;">📂</div>'
            f'<div style="color:{_C_TEXT};font-size:1.05rem;font-weight:600;margin-bottom:8px;">El Centro Documental está listo.</div>'
            + (f'<div style="color:{_C_GRAY};font-size:0.88rem;">Selecciona una empresa y una carpeta para agregar el primer documento.</div>' if filtro_empresa else f'<div style="color:{_C_GRAY};font-size:0.88rem;">Selecciona una empresa en el filtro para comenzar a cargar documentos.</div>')
            + '</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

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

    # ── Tabs por carpeta ──────────────────────────────────────────────────────
    tab_labels = ["📄 Todos"] + [
        f"{_CARPETA_ICON.get(c,'📁')} {c}" for c in _CARPETAS_ORDEN
    ]
    tabs = st.tabs(tab_labels)

    for tab_idx, tab in enumerate(tabs):
        with tab:
            if tab_idx == 0:
                # ════════════════════════════════════════════════════════════
                # TAB "TODOS" — Modo Gobernanza ISO (vista global) o
                #               Portafolio por empresa (vista filtrada)
                # ════════════════════════════════════════════════════════════

                if filtro_empresa is None:
                    # ════════════════════════════════════════════════════════
                    # MODO GOBERNANZA: filtro = "Todas las empresas"
                    # ════════════════════════════════════════════════════════
                    import plotly.graph_objects as go

                    # Cargar métricas del grupo
                    try:
                        with next(get_session()) as session:
                            grupo = ComplianceRepository(session).get_stats_grupo()
                    except Exception as exc:
                        st.error(f"Error cargando métricas del grupo: {exc}")
                        grupo = {"por_empresa": [], "por_empresa_carpeta": [],
                                 "gap_total": 0, "vigencia_pct": 0.0}

                    vigencia_pct = grupo["vigencia_pct"]
                    gap_total    = grupo["gap_total"]

                    # ── Encabezado especial ───────────────────────────────
                    st.markdown(
                        f'<div style="background:linear-gradient(135deg,#0f172a,#1e2740);'
                        f'border:1px solid #3b4f7a;border-left:4px solid {_C_VIOLET};'
                        f'border-radius:10px;padding:16px 20px;margin-bottom:18px;">'
                        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">'
                        f'<span style="font-size:1.4rem">🏛️</span>'
                        f'<div>'
                        f'<div style="color:{_C_TEXT};font-size:1.05rem;font-weight:700">'
                        f'Gobernanza del Grupo Corporativo</div>'
                        f'<div style="color:#64748b;font-size:0.76rem">'
                        f'Estándar ISO 27001 / ISO 37001 — Control de Información Documentada</div>'
                        f'</div>'
                        f'</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                    # ── KPIs ISO de Preparación ───────────────────────────
                    vig_color  = _C_GREEN  if vigencia_pct >= 80 else (_C_AMBER if vigencia_pct >= 60 else _C_RED)
                    gap_color  = _C_GREEN  if gap_total == 0    else (_C_AMBER if gap_total <= 5   else _C_RED)
                    gap_label  = "Sin brechas" if gap_total == 0 else f"{gap_total} docs requieren acción"
                    total_corp = stats["total"]

                    k1, k2, k3, k4 = st.columns(4)
                    _iso_kpis = [
                        (k1, "📊 Índice de Vigencia", f"{vigencia_pct}%", vig_color,
                         "Documentos vigentes sobre total activo"),
                        (k2, "🚨 Gap de Cumplimiento", str(gap_total), gap_color,
                         gap_label),
                        (k3, "📋 Total Documentado", str(total_corp), _C_CYAN,
                         "Documentos activos (no archivados)"),
                        (k4, "🏢 Empresas Cubiertas", "3 / 3", _C_GREEN,
                         "Holdings BPO · PayCOP · Adamo Services"),
                    ]
                    for col, titulo, valor, color, subtitulo in _iso_kpis:
                        col.markdown(
                            f'<div style="background:#0f172a;border:1px solid #1e2740;'
                            f'border-top:3px solid {color};border-radius:8px;'
                            f'padding:14px 16px;text-align:center;">'
                            f'<div style="color:#64748b;font-size:0.72rem;margin-bottom:4px">{titulo}</div>'
                            f'<div style="color:{color};font-size:1.8rem;font-weight:700;line-height:1">{valor}</div>'
                            f'<div style="color:#475569;font-size:0.68rem;margin-top:5px">{subtitulo}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                    st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)

                    # ── Gráficos Plotly ───────────────────────────────────
                    _EMPRESAS_GRAF = ["Holdings BPO", "PayCOP", "Adamo Services"]
                    _COLORES_EMP   = [_C_VIOLET, _C_CYAN, _C_AMBER]
                    _ISO_CARPETAS  = [
                        "Politicas", "Manuales",
                        "Procesos y Procedimientos", "Governanza", "Matrices",
                    ]

                    # Pre-procesar datos por empresa y carpeta
                    pec = grupo["por_empresa_carpeta"]

                    def _get_vigentes(empresa: str, carpeta: str) -> int:
                        r = next(
                            (x for x in pec
                             if x["empresa"] == empresa and x["carpeta"] == carpeta),
                            None,
                        )
                        return int(r["vigentes"]) if r else 0

                    def _get_total(empresa: str, carpeta: str) -> int:
                        r = next(
                            (x for x in pec
                             if x["empresa"] == empresa and x["carpeta"] == carpeta),
                            None,
                        )
                        return int(r["total"]) if r else 0

                    col_radar, col_barra = st.columns(2)

                    # ── Radar ISO: completitud por carpeta crítica ────────
                    with col_radar:
                        st.markdown(
                            f'<p style="color:{_C_GRAY};font-size:0.75rem;'
                            f'text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">'
                            f'🕸️ Radar ISO — Completitud Carpetas Críticas</p>',
                            unsafe_allow_html=True,
                        )
                        radar_fig = go.Figure()
                        for emp, col_emp in zip(_EMPRESAS_GRAF, _COLORES_EMP):
                            vals = []
                            for carp in _ISO_CARPETAS:
                                total_v = _get_total(emp, carp)
                                vigent_v = _get_vigentes(emp, carp)
                                vals.append(round(vigent_v / total_v * 100, 1) if total_v else 0)
                            # Cerrar el polígono
                            vals_closed = vals + [vals[0]]
                            cats_closed = _ISO_CARPETAS + [_ISO_CARPETAS[0]]
                            radar_fig.add_trace(go.Scatterpolar(
                                r=vals_closed,
                                theta=cats_closed,
                                fill="toself",
                                name=emp,
                                line=dict(color=col_emp, width=2),
                                fillcolor=_hex_fill(col_emp),
                            ))
                        radar_fig.update_layout(
                            polar=dict(
                                bgcolor="#0f172a",
                                radialaxis=dict(
                                    visible=True, range=[0, 100],
                                    tickfont=dict(size=9, color="#64748b"),
                                    gridcolor="#1e2740",
                                    linecolor="#1e2740",
                                ),
                                angularaxis=dict(
                                    tickfont=dict(size=9, color="#94a3b8"),
                                    gridcolor="#1e2740",
                                    linecolor="#293056",
                                ),
                            ),
                            paper_bgcolor="#0f172a",
                            plot_bgcolor="#0f172a",
                            font=dict(color="#94a3b8", size=10),
                            legend=dict(
                                orientation="h", x=0.5, xanchor="center", y=-0.1,
                                font=dict(size=10),
                            ),
                            margin=dict(l=30, r=30, t=20, b=40),
                            height=320,
                        )
                        st.plotly_chart(radar_fig, use_container_width=True,
                                        config={"displayModeBar": False})

                    # ── Barras apiladas: salud documental por empresa ─────
                    with col_barra:
                        st.markdown(
                            f'<p style="color:{_C_GRAY};font-size:0.75rem;'
                            f'text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">'
                            f'📊 Salud Documental — Comparativa Inter-Empresas</p>',
                            unsafe_allow_html=True,
                        )
                        pe = grupo["por_empresa"]

                        def _emp_val(empresa: str, campo: str) -> int:
                            r = next((x for x in pe if x["empresa"] == empresa), None)
                            return int(r[campo]) if r else 0

                        bar_fig = go.Figure()
                        estados_bar = [
                            ("vigentes",   "Vigente",   _C_GREEN),
                            ("pendientes", "Pendiente", _C_AMBER),
                            ("vencidos",   "Vencido",   _C_RED),
                        ]
                        for campo, label, color in estados_bar:
                            bar_fig.add_trace(go.Bar(
                                name=label,
                                x=_EMPRESAS_GRAF,
                                y=[_emp_val(e, campo) for e in _EMPRESAS_GRAF],
                                marker_color=color,
                            ))
                        bar_fig.update_layout(
                            barmode="stack",
                            paper_bgcolor="#0f172a",
                            plot_bgcolor="#0f172a",
                            font=dict(color="#94a3b8", size=10),
                            legend=dict(
                                orientation="h", x=0.5, xanchor="center", y=-0.12,
                                font=dict(size=10),
                            ),
                            xaxis=dict(
                                tickfont=dict(size=10),
                                gridcolor="#1e2740",
                                linecolor="#293056",
                            ),
                            yaxis=dict(
                                tickfont=dict(size=10),
                                gridcolor="#1e2740",
                                linecolor="#293056",
                                title=dict(text="Documentos", font=dict(size=10)),
                            ),
                            margin=dict(l=40, r=10, t=20, b=50),
                            height=320,
                        )
                        st.plotly_chart(bar_fig, use_container_width=True,
                                        config={"displayModeBar": False})

                    # ── Resumen por carpeta ───────────────────────────────
                    st.markdown(
                        f'<p style="color:{_C_GRAY};font-size:0.75rem;font-weight:700;'
                        f'text-transform:uppercase;letter-spacing:1px;margin:16px 0 8px">'
                        f'Estado por Carpeta — Grupo Corporativo</p>',
                        unsafe_allow_html=True,
                    )
                    for carp in _CARPETAS_ORDEN:
                        cs = next(
                            (c for c in stats["por_carpeta"] if c["carpeta"] == carp), None
                        )
                        total_c  = cs.get("total",      0) if cs else 0
                        vigent_c = cs.get("vigentes",   0) if cs else 0
                        vencid_c = cs.get("vencidos",   0) if cs else 0
                        pend_c   = cs.get("pendientes", 0) if cs else 0
                        pct_c    = vigent_c / total_c if total_c else 0
                        icono    = _CARPETA_ICON.get(carp, "📁")
                        # Marcar carpetas críticas ISO
                        iso_tag  = ("&nbsp;<span style='background:#312e81;color:#a5b4fc;"
                                    "font-size:0.65rem;padding:1px 6px;border-radius:4px;"
                                    "font-weight:600'>ISO ✓</span>"
                                    if carp in ("Politicas", "Manuales",
                                                "Procesos y Procedimientos",
                                                "Governanza", "Matrices")
                                    else "")

                        alert_html = ""
                        if vencid_c:
                            alert_html += (
                                f"&nbsp;<span style='background:#7f1d1d;color:#fca5a5;"
                                f"font-size:0.68rem;padding:1px 7px;border-radius:10px;'>"
                                f"⚠ {vencid_c} vencido{'s' if vencid_c>1 else ''}</span>"
                            )
                        if pend_c:
                            alert_html += (
                                f"&nbsp;<span style='background:#78350f;color:#fcd34d;"
                                f"font-size:0.68rem;padding:1px 7px;border-radius:10px;'>"
                                f"⏳ {pend_c} pendiente{'s' if pend_c>1 else ''}</span>"
                            )

                        bar_color = _C_CYAN if pct_c >= 0.8 else (_C_AMBER if pct_c >= 0.5 else _C_RED)
                        bar_pct   = int(pct_c * 100)
                        st.markdown(
                            f'<div style="background:{_C_CARD};border:1px solid {_C_BORDER};'
                            f'border-radius:8px;padding:10px 14px;margin-bottom:5px;'
                            f'display:flex;align-items:center;gap:12px;">'
                            f'<span style="font-size:1.1rem">{icono}</span>'
                            f'<div style="flex:1">'
                            f'<div style="display:flex;justify-content:space-between;align-items:center">'
                            f'<span style="color:{_C_TEXT};font-size:0.84rem;font-weight:600">'
                            f'{carp}{iso_tag}</span>'
                            f'<span style="color:{_C_GRAY};font-size:0.73rem">'
                            f'{vigent_c}/{total_c} vigentes{alert_html}</span>'
                            f'</div>'
                            f'<div style="background:#1e2740;border-radius:4px;height:5px;margin-top:6px">'
                            f'<div style="background:{bar_color};width:{bar_pct}%;'
                            f'max-width:100%;height:5px;border-radius:4px"></div>'
                            f'</div>'
                            f'</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                    # ── Gap Analysis: documentos que requieren acción ─────
                    prioritarios = [
                        d for d in todos if d.get("estado") in ("Vencido", "Pendiente")
                    ]
                    if prioritarios:
                        st.markdown(
                            f'<p style="color:{_C_GRAY};font-size:0.75rem;font-weight:700;'
                            f'text-transform:uppercase;letter-spacing:1px;margin:18px 0 8px">'
                            f'🚨 Gap Analysis — Requieren Acción para Auditoría '
                            f'({len(prioritarios)})</p>',
                            unsafe_allow_html=True,
                        )
                        for d in sorted(
                            prioritarios,
                            key=lambda x: (x.get("estado", "") == "Vencido", x.get("updated_at", "")),
                            reverse=True,
                        ):
                            est      = d.get("estado", "")
                            est_fg   = _ESTADO_COLOR.get(est, (_C_GRAY, "#0"))[0]
                            emp      = d.get("empresa") or "Compartido"
                            emp_c    = _EMPRESA_COLOR.get(emp, _C_GRAY)
                            ver      = d.get("version", "—")
                            updated  = str(d.get("updated_at", ""))[:10] or "—"
                            desc_raw = (d.get("descripcion") or "")[:80]
                            desc_esc = _html.escape(desc_raw)
                            nombre_e = _html.escape(d.get("nombre", ""))
                            carpeta_e = d.get("carpeta", "")
                            st.markdown(
                                f'<div style="background:{_C_CARD};border-left:3px solid {est_fg};'
                                f'border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:5px">'
                                f'<div style="display:flex;justify-content:space-between;'
                                f'align-items:flex-start;flex-wrap:wrap;gap:4px">'
                                f'<div>'
                                f'<span style="color:{est_fg};font-size:0.7rem;font-weight:700;'
                                f'margin-right:8px">{est.upper()}</span>'
                                f'<span style="color:{_C_TEXT};font-size:0.84rem;'
                                f'font-weight:600">{nombre_e}</span>'
                                f'</div>'
                                f'<div style="display:flex;gap:5px;align-items:center">'
                                f'<span style="background:{emp_c}22;color:{emp_c};font-size:0.68rem;'
                                f'padding:1px 7px;border-radius:4px;border:1px solid {emp_c}44">'
                                f'{emp}</span>'
                                f'</div>'
                                f'</div>'
                                f'<div style="display:flex;gap:12px;margin-top:5px;flex-wrap:wrap">'
                                f'<span style="color:#475569;font-size:0.7rem">'
                                f'{_CARPETA_ICON.get(carpeta_e,"📁")} {carpeta_e}</span>'
                                f'<span style="color:#475569;font-size:0.7rem">'
                                f'v{ver}</span>'
                                f'<span style="color:#475569;font-size:0.7rem">'
                                f'📅 Última mod. {updated}</span>'
                                + (
                                    f'<span style="color:#64748b;font-size:0.7rem;'
                                    f'font-style:italic">'
                                    f'"{desc_esc}"</span>'
                                    if desc_esc else ''
                                )
                                + f'</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                else:
                    # ════════════════════════════════════════════════════════
                    # MODO EMPRESA: vista filtrada — búsqueda + tarjetas
                    # ════════════════════════════════════════════════════════

                    # ── Búsqueda de texto ─────────────────────────────────
                    busqueda = st.text_input(
                        "🔍 Buscar documento",
                        placeholder="Nombre, código o descripción…",
                        key="busqueda_todos",
                        label_visibility="collapsed",
                    )
                    docs_busqueda = todos
                    if busqueda.strip():
                        q = busqueda.strip().lower()
                        docs_busqueda = [
                            d for d in todos
                            if q in (d.get("nombre") or "").lower()
                            or q in (d.get("codigo") or "").lower()
                            or q in (d.get("descripcion") or "").lower()
                        ]

                    # ── Resumen por carpeta ───────────────────────────────
                    if not busqueda.strip():
                        st.markdown(
                            f"<p style='color:{_C_GRAY};font-size:0.78rem;font-weight:700;"
                            f"text-transform:uppercase;letter-spacing:1px;margin:8px 0 10px;'>"
                            f"Resumen por carpeta</p>",
                            unsafe_allow_html=True,
                        )
                        for carp in _CARPETAS_ORDEN:
                            cs = next(
                                (c for c in stats["por_carpeta"] if c["carpeta"] == carp), None
                            )
                            total_c  = cs.get("total",      0) if cs else 0
                            vigent_c = cs.get("vigentes",   0) if cs else 0
                            vencid_c = cs.get("vencidos",   0) if cs else 0
                            pend_c   = cs.get("pendientes", 0) if cs else 0
                            pct_c    = vigent_c / total_c if total_c else 0
                            icono    = _CARPETA_ICON.get(carp, "📁")

                            alert_html = ""
                            if vencid_c:
                                alert_html += (
                                    f"&nbsp;<span style='background:#7f1d1d;color:#fca5a5;"
                                    f"font-size:0.68rem;padding:1px 7px;border-radius:10px;'>"
                                    f"⚠ {vencid_c} vencido{'s' if vencid_c>1 else ''}</span>"
                                )
                            if pend_c:
                                alert_html += (
                                    f"&nbsp;<span style='background:#78350f;color:#fcd34d;"
                                    f"font-size:0.68rem;padding:1px 7px;border-radius:10px;'>"
                                    f"⏳ {pend_c} pendiente{'s' if pend_c>1 else ''}</span>"
                                )

                            bar_color = _C_CYAN if pct_c >= 0.8 else (_C_AMBER if pct_c >= 0.5 else _C_RED)
                            bar_pct   = int(pct_c * 100)
                            st.markdown(
                                f'<div style="background:{_C_CARD};border:1px solid {_C_BORDER};'
                                f'border-radius:8px;padding:10px 14px;margin-bottom:6px;'
                                f'display:flex;align-items:center;gap:12px;">'
                                f'<span style="font-size:1.1rem;">{icono}</span>'
                                f'<div style="flex:1;">'
                                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                                f'<span style="color:{_C_TEXT};font-size:0.85rem;font-weight:600;">{carp}</span>'
                                f'<span style="color:{_C_GRAY};font-size:0.75rem;">{vigent_c}/{total_c} vigentes{alert_html}</span>'
                                f'</div>'
                                f'<div style="background:#1f2937;border-radius:4px;height:5px;margin-top:5px;">'
                                f'<div style="background:{bar_color};width:{bar_pct}%;max-width:100%;height:5px;border-radius:4px;"></div>'
                                f'</div>'
                                f'</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                        # ── Atención prioritaria ──────────────────────────
                        prioritarios = [
                            d for d in todos if d.get("estado") in ("Vencido", "Pendiente")
                        ]
                        if prioritarios:
                            st.markdown(
                                f"<p style='color:{_C_GRAY};font-size:0.78rem;font-weight:700;"
                                f"text-transform:uppercase;letter-spacing:1px;margin:18px 0 8px;'>"
                                f"Requieren atención ({len(prioritarios)})</p>",
                                unsafe_allow_html=True,
                            )
                            for d in sorted(prioritarios, key=lambda x: x.get("estado", "") == "Vencido", reverse=True):
                                est = d.get("estado", "")
                                est_color = _ESTADO_COLOR.get(est, (_C_GRAY, "#00000000"))
                                emp = d.get("empresa") or "Compartido"
                                st.markdown(
                                    f'<div style="background:{_C_CARD};border-left:3px solid {est_color[0]};'
                                    f'border-radius:0 6px 6px 0;padding:8px 12px;margin-bottom:4px;">'
                                    f'<span style="color:{est_color[0]};font-size:0.72rem;font-weight:700;">{est.upper()}</span>'
                                    f'&nbsp;&nbsp;<span style="color:{_C_TEXT};font-size:0.83rem;">{_html.escape(d.get("nombre",""))}</span>'
                                    f'&nbsp;&nbsp;<span style="color:{_C_GRAY};font-size:0.72rem;">'
                                    f'{_CARPETA_ICON.get(d.get("carpeta",""),"📁")} {d.get("carpeta","")} · {emp}'
                                    f'</span></div>',
                                    unsafe_allow_html=True,
                                )

                    else:
                        # ── Resultados de búsqueda ────────────────────────
                        if docs_busqueda:
                            st.markdown(
                                f"<p style='color:{_C_GRAY};font-size:0.78rem;margin-bottom:10px;'>"
                                f"{len(docs_busqueda)} resultado(s)</p>",
                                unsafe_allow_html=True,
                            )
                            col_a, col_b, col_c = st.columns(3)
                            _cols = [col_a, col_b, col_c]
                            for idx, doc in enumerate(docs_busqueda):
                                with _cols[idx % 3]:
                                    _doc_card(doc, puede_editar, key_prefix="busq_")
                        else:
                            st.info("No se encontraron documentos con ese término.")

                continue   # el resto del bucle es solo para tabs de carpeta

            # ── Tabs de carpeta específica (tab_idx > 0) ─────────────────
            carpeta_filtro: Optional[str] = _CARPETAS_ORDEN[tab_idx - 1]

            # Documentos de esta carpeta
            docs_carpeta = [d for d in todos if d["carpeta"] == carpeta_filtro]

            # ── Barra de progreso ─────────────────────────────────────────────
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

            # ── Filtro de estado (inline) ─────────────────────────────────────
            filtro_estado = st.selectbox(
                "Estado",
                ["Todos", "Vigente", "Pendiente", "Vencido"],
                key=f"fe_{tab_idx}",
                label_visibility="collapsed",
            )
            docs_tab = (
                [d for d in docs_carpeta if d["estado"] == filtro_estado]
                if filtro_estado != "Todos"
                else docs_carpeta
            )

            # ── Tarjetas de documentos ────────────────────────────────────────
            if docs_tab:
                col_a, col_b, col_c = st.columns(3)
                _cols = [col_a, col_b, col_c]
                for idx, doc in enumerate(docs_tab):
                    with _cols[idx % 3]:
                        _doc_card(doc, puede_editar, key_prefix=f"t{tab_idx}_")
            else:
                st.info(
                    "No hay documentos en esta carpeta."
                    if not docs_carpeta
                    else "No hay documentos con los filtros seleccionados."
                )

    # ── Formulario de carga (fijo, fuera de los tabs) ─────────────────────────
    # Visible siempre que: rol editor + empresa seleccionada (no "Todas")
    if puede_editar and filtro_empresa is not None:
        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='color:{_C_GRAY};font-size:0.78rem;border-top:1px solid {_C_BORDER};"
            f"padding-top:12px;margin-bottom:4px;'>Carga de documentos para "
            f"<strong style=\"color:{_C_TEXT};\">{filtro_empresa}</strong></div>",
            unsafe_allow_html=True,
        )
        _form_nuevo_documento(
            user,
            carpeta_default=None,       # usuario elige la carpeta en el form
            empresa_default=filtro_empresa,
        )
