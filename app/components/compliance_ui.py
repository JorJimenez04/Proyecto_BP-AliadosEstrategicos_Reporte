"""
app/components/compliance_ui.py
Centro Documental de Cumplimiento -- AdamoServices Partner Manager.
Gestor de documentos regulatorios: Politicas, Manuales, Onboarding,
Etica, Riesgos, Empresariales y Capacitacion.
"""

from __future__ import annotations
import html as _html
import logging
import re as _re
from typing import Optional
from urllib.parse import urlparse as _urlparse
import streamlit as st
import streamlit.components.v1 as _components

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
# Entidades corporativas
# ─────────────────────────────────────────────────────────────
_EMPRESAS = ["Todas", "Holdings BPO", "PayCOP", "Adamo Services"]
_EMPRESA_COLOR: dict[str, str] = {
    "Holdings BPO":    _C_VIOLET,
    "PayCOP":          _C_CYAN,
    "Adamo Services":  _C_AMBER,
}

# ─────────────────────────────────────────────────────────────
# Utilidades Google Drive
# ─────────────────────────────────────────────────────────────
_DRIVE_ID_RE     = _re.compile(r'/d/([a-zA-Z0-9_-]{20,})')
_DRIVE_ID_ALT_RE = _re.compile(r'[?&]id=([a-zA-Z0-9_-]{20,})')
_ALLOWED_DRIVE   = frozenset({"drive.google.com", "docs.google.com"})
_MAX_DL_BYTES    = 25 * 1024 * 1024   # 25 MB


def _extract_drive_id(url: str) -> Optional[str]:
    """Extrae el file-ID de cualquier URL de Google Drive."""
    m = _DRIVE_ID_RE.search(url)
    if m:
        return m.group(1)
    m = _DRIVE_ID_ALT_RE.search(url)
    return m.group(1) if m else None


def _is_drive_url(url: str) -> bool:
    """True si la URL pertenece a drive.google.com o docs.google.com."""
    if not url:
        return False
    try:
        return _urlparse(url).netloc in _ALLOWED_DRIVE
    except Exception:
        return False


def _to_drive_preview(url: str) -> Optional[str]:
    """Convierte cualquier URL de Drive al endpoint /preview del archivo."""
    fid = _extract_drive_id(url)
    return f"https://drive.google.com/file/d/{fid}/preview" if fid else None


def _download_drive_file(url: str) -> tuple[bytes, str]:
    """
    Descarga un archivo de Google Drive.
    Protección SSRF: extrae el ID y reconstruye la URL desde cero.
    Límite 25 MB · timeout 20 s.
    """
    import requests  # lazy import — disponible via streamlit/transitive dep

    fid = _extract_drive_id(url)
    if not fid:
        raise ValueError("No se encontró un ID válido de Google Drive en la URL.")

    # Reconstruir URL desde ID extraído (protección SSRF)
    dl_url  = f"https://drive.google.com/uc?export=download&id={fid}"
    headers = {"User-Agent": "Mozilla/5.0"}
    sess    = requests.Session()

    resp = sess.get(dl_url, timeout=20, stream=True,
                    allow_redirects=True, headers=headers)
    resp.raise_for_status()

    # Manejar página de confirmación antivirus de Google (archivos grandes)
    if "text/html" in resp.headers.get("Content-Type", ""):
        token_m = _re.search(r'confirm=([0-9A-Za-z_-]+)', resp.text)
        if token_m:
            resp = sess.get(
                dl_url + f"&confirm={token_m.group(1)}",
                timeout=20, stream=True, allow_redirects=True, headers=headers,
            )
            resp.raise_for_status()

    # Leer con límite de tamaño
    content = b""
    for chunk in resp.iter_content(chunk_size=65536):
        content += chunk
        if len(content) > _MAX_DL_BYTES:
            raise ValueError("El archivo supera el límite de 25 MB para descarga directa.")

    # Nombre de archivo desde Content-Disposition
    cd      = resp.headers.get("content-disposition", "")
    fname_m = _re.search(r'filename[^;=\n]*=([\'"]?)([^\'"\n;]+)\1', cd)
    filename = fname_m.group(2).strip() if fname_m else f"documento_{fid[:8]}.pdf"
    return content, filename


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
    """Renderiza un documento como tarjeta oscura con badges de estado, formato y empresa."""
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
        badge_empresa = " &nbsp;" + _badge(empresa, emp_c, emp_c + "22")

    url      = doc.get("url_documento")
    url_safe = _html.escape(str(url)) if url else ""
    link_html = (
        f'<a href="{url_safe}" target="_blank" rel="noopener noreferrer" '
        f'style="color:{_C_CYAN};text-decoration:none;font-size:0.78rem;">&#128279; Abrir</a>'
        if url else
        '<span style="color:#4b5563;font-size:0.78rem;">Sin enlace</span>'
    )

    fecha_raw = doc.get("fecha_emision")
    fecha  = str(fecha_raw) if fecha_raw else "-"
    ver    = _html.escape(str(doc.get("version",  "-")))
    codigo = _html.escape(str(doc.get("codigo",   "")))
    nombre = _html.escape(str(doc.get("nombre",   "Sin nombre")))
    desc_raw  = doc.get("descripcion") or ""
    desc      = _html.escape(desc_raw)
    desc_html = (
        f'<div style="color:{_C_GRAY};font-size:0.78rem;margin-bottom:6px;">{desc}</div>'
        if desc else ""
    )

    st.markdown(
        f'<div style="background:{_C_CARD};border:1px solid {_C_BORDER};border-radius:8px;padding:16px;margin-bottom:6px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:6px;margin-bottom:8px;">'
        f'<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">{badge_formato}{badge_estado}{badge_empresa}</div>'
        f'<div style="color:{_C_GRAY};font-size:0.72rem;">{codigo}</div>'
        f'</div>'
        f'<div style="color:{_C_TEXT};font-weight:600;font-size:0.92rem;margin-bottom:2px;">{nombre}</div>'
        + (f'<div style="color:{_C_GRAY};font-size:0.78rem;margin-bottom:6px;">{desc}</div>' if desc else '')
        + f'<div style="color:{_C_GRAY};font-size:0.75rem;margin-top:8px;">v{ver} &nbsp;|&nbsp; {fecha} &nbsp;|&nbsp; {link_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Previsualizar + Descargar (solo si URL es de Drive) ────────────────────────
    is_drive      = bool(url and _is_drive_url(url))
    prev_open_key = f"_prev_{key_prefix}{doc_id}"   # tab-local preview toggle
    dl_data_key   = f"_dldata_{doc_id}"               # global download cache

    if is_drive:
        ca, cb = st.columns(2)
        with ca:
            prev_lbl = "⬆️ Ocultar" if st.session_state.get(prev_open_key) else "👁️ Previsualizar"
            if st.button(prev_lbl, key=f"{key_prefix}prev_{doc_id}",
                         use_container_width=True):
                st.session_state[prev_open_key] = not st.session_state.get(
                    prev_open_key, False
                )
        with cb:
            if st.session_state.get(dl_data_key):
                dl_bytes, dl_name = st.session_state[dl_data_key]
                st.download_button(
                    "💾 Guardar archivo",
                    data=dl_bytes,
                    file_name=dl_name,
                    key=f"{key_prefix}dlsave_{doc_id}",
                    use_container_width=True,
                )
            else:
                if st.button("⬇️ Descargar", key=f"{key_prefix}dl_{doc_id}",
                             use_container_width=True):
                    with st.spinner("Preparando descarga…"):
                        try:
                            data, fname = _download_drive_file(url)
                            st.session_state[dl_data_key] = (data, fname)
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))

        if st.session_state.get(prev_open_key):
            preview_url = _to_drive_preview(url)
            if preview_url:
                _components.iframe(preview_url, height=520, scrolling=True)
            else:
                st.warning("No se puede generar vista previa para este enlace.")

    # ── Nueva Versión (solo editores) ────────────────────────────────────────
    if puede_editar:
        nv_open_key = f"_nv_open_{key_prefix}{doc_id}"
        if st.button("✏️ Nueva Versión", key=f"{key_prefix}nv_btn_{doc_id}",
                     use_container_width=False):
            st.session_state[nv_open_key] = True
        if st.session_state.get(nv_open_key):
            _form_nueva_version(doc, key_prefix=key_prefix)

    st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)


def _form_nueva_version(doc: dict, key_prefix: str = "") -> None:
    form_key    = f"{key_prefix}form_nv_{doc['id']}"
    nv_open_key = f"_nv_open_{key_prefix}{doc['id']}"
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
            "URL de Google Drive",
            value=doc.get("url_documento") or "",
            placeholder="https://drive.google.com/file/d/.../view",
        )
        st.caption(
            "ℹ️ Asegúrate de que el enlace sea público: "
            "Google Drive → Compartir → *Cualquier persona con el enlace puede ver*."
        )
        descripcion_cambio = st.text_area(
            "Descripción del cambio", placeholder="Breve descripción…", height=80
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
            st.session_state[nv_open_key] = False
            st.rerun()
        except Exception as exc:
            logger.exception("[Compliance] Error actualizando version")
            st.error(f"Error al guardar: {exc}")


def _form_nuevo_documento(
    user: dict,
    carpeta_default: str | None = None,
    empresa_default: str | None = None,
) -> None:
    """Formulario para agregar un nuevo documento (admin/compliance)."""
    with st.expander("➕ Agregar nuevo documento a esta sección", expanded=False):
        # Clave única por carpeta + empresa para evitar DuplicateWidgetID entre tabs/empresas
        form_key = f"form_nuevo_doc_{carpeta_default or 'X'}_{empresa_default or 'X'}"
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
                    "URL de Google Drive",
                    placeholder="https://drive.google.com/file/d/.../view",
                )
                fecha_emision     = st.date_input("Fecha emisión",    value=None)
                fecha_vencimiento = st.date_input("Fecha vencimiento", value=None)
            descripcion = st.text_area("Descripción", height=70)
            st.caption(
                "ℹ️ Para habilitar Previsualizar y Descargar, usa un enlace de Google Drive "
                "(/file/d/) con permiso *Cualquier persona con el enlace puede ver*."
            )
            guardar = st.form_submit_button("💾 Crear documento")

        if guardar:
            if not nombre.strip():
                st.error("El nombre del documento es obligatorio.")
                return
            empresa_val = None if empresa == "(Compartido)" else empresa
            url_clean   = url_doc.strip() or None
            if url_clean and not _is_drive_url(url_clean):
                st.warning(
                    "⚠️ La URL no parece ser de Google Drive. "
                    "Previsualizar y Descargar no estarán disponibles."
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
                carpeta_filtro: Optional[str] = None
            else:
                carpeta_filtro = _CARPETAS_ORDEN[tab_idx - 1]

            # Documentos de esta carpeta (sin filtro de estado aún)
            docs_carpeta = (
                [d for d in todos if d["carpeta"] == carpeta_filtro]
                if carpeta_filtro
                else todos
            )

            # ── Barra de progreso (solo en tabs de carpeta específica) ────────
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
                col_a, col_b = st.columns(2)
                for idx, doc in enumerate(docs_tab):
                    col = col_a if idx % 2 == 0 else col_b
                    with col:
                        _doc_card(doc, puede_editar, key_prefix=f"t{tab_idx}_")
            else:
                st.info(
                    "No hay documentos en esta carpeta."
                    if not docs_carpeta
                    else "No hay documentos con los filtros seleccionados."
                )

            # ── Formulario agregar (SIEMPRE al final, sin depender de docs) ───
            # Condiciones: carpeta específica + empresa seleccionada + rol editor
            if carpeta_filtro and puede_editar and filtro_empresa is not None:
                _form_nuevo_documento(
                    user,
                    carpeta_default=carpeta_filtro,
                    empresa_default=filtro_empresa,
                )
