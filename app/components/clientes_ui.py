"""
app/components/clientes_ui.py
Módulo 👥 Gestión de Clientes — AdamoServices Partner Manager.
Vista unificada KYC + contratos + personas + documentos + riesgo SARLAFT.
"""

from __future__ import annotations
import logging
from datetime import date, timedelta
from typing import Optional
import streamlit as st

from config.settings import Roles, Jurisdicciones

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Constantes de UI
# ─────────────────────────────────────────────────────────────
_ESTADO_COLOR = {
    "Prospecto":  "#6b7280",
    "Activo":     "#22c55e",
    "Suspendido": "#f59e0b",
    "Terminado":  "#ef4444",
}
_NIVEL_COLOR = {
    "Sin calificar": "#6b7280",
    "Bajo":          "#22c55e",
    "Medio":         "#f59e0b",
    "Alto":          "#f97316",
    "Muy Alto":      "#ef4444",
}
_EMPRESA_COLOR = {
    "Holdings BPO":   "#7839ee",
    "Adamo Services": "#f59e0b",
    "Paycop":         "#5fe9d0",
}
_SERVICIOS_COLOR = {
    "Dispersión":               "#3b82f6",
    "Monetización":             "#8b5cf6",
    "Monitoreo de Transacciones": "#f59e0b",
    "Compliance 360":           "#22c55e",
}
_CARPETA_ICON = {
    "Politicas": "📋", "Manuales": "📖", "Onboarding": "🔗",
    "Procesos y Procedimientos": "⚙️", "Governanza": "🛡️",
    "Empresariales": "🏢", "Capacitacion": "🎓", "Contratos": "📝",
    "Actas y Formatos": "📑", "Matrices": "📊", "Tecnologia": "💻",
}
_CARPETAS_ORDEN = [
    "Politicas", "Manuales", "Onboarding", "Procesos y Procedimientos",
    "Governanza", "Empresariales", "Capacitacion", "Contratos",
    "Actas y Formatos", "Matrices", "Tecnologia",
]
_ESTADOS_CLIENTE    = ["Prospecto", "Activo", "Suspendido", "Terminado"]
_NIVELES_RIESGO     = ["Sin calificar", "Bajo", "Medio", "Alto", "Muy Alto"]
_EMPRESAS_GRUPO     = ["Holdings BPO", "Adamo Services", "Paycop"]
_SERVICIOS          = ["Dispersión", "Monetización", "Monitoreo de Transacciones", "Compliance 360"]
_ROLES_PERSONA      = [
    "Representante Legal", "Director", "Accionista",
    "Beneficiario Final (UBO)", "Apoderado", "Otro",
]
_FORMATOS_DOC       = ["PDF", "DOCX", "XLSX", "PPTX", "OTRO"]
_TIPOS_SOCIEDAD     = [
    "S.A.S", "S.A.", "S de R.L.", "Ltda.", "E.A.T.",
    "Fundación", "Cooperativa", "Otro",
]


def _badge(texto: str, color: str) -> str:
    return (
        f"<span style='display:inline-block;padding:2px 10px;border-radius:99px;"
        f"background:{color}22;color:{color};border:1px solid {color}55;"
        f"font-size:0.65rem;font-weight:700;font-family:JetBrains Mono,monospace;"
        f"letter-spacing:0.05em;'>{texto}</span>"
    )


def _pill(texto: str, color: str = "#6b7280") -> str:
    return (
        f"<span style='display:inline-flex;align-items:center;padding:3px 10px;"
        f"border-radius:99px;background:{color}18;border:1px solid {color}40;"
        f"color:{color};font-size:0.70rem;font-weight:600;margin:2px;'>{texto}</span>"
    )


def _fmt_cop(valor: Optional[int]) -> str:
    if not valor:
        return "—"
    return f"${valor:,.0f}"


# ─────────────────────────────────────────────────────────────
# Punto de entrada principal
# ─────────────────────────────────────────────────────────────

def page_clientes(user: dict) -> None:
    rol = user.get("rol", "")
    st.markdown("## 👥 Gestión de Clientes")

    # Navegación interna: portafolio → ficha detalle
    if "cliente_detalle_id" in st.session_state:
        _ficha_cliente(st.session_state["cliente_detalle_id"], user)
        if st.button("← Volver al portafolio", key="btn_volver_portafolio"):
            del st.session_state["cliente_detalle_id"]
            st.rerun()
        return

    tabs_labels = ["📋 Portafolio"]
    if rol in {"admin", "compliance", "super_admin"}:
        tabs_labels.append("➕ Nuevo Cliente")

    tabs = st.tabs(tabs_labels)

    with tabs[0]:
        _tab_portafolio(user)

    if len(tabs) > 1:
        with tabs[1]:
            _tab_alta_cliente(user)


# ─────────────────────────────────────────────────────────────
# Tab: Portafolio
# ─────────────────────────────────────────────────────────────

def _tab_portafolio(user: dict) -> None:
    from db.database import get_session
    from db.repositories.cliente_repo import ClienteRepository

    with next(get_session()) as session:
        repo = ClienteRepository(session)
        stats = repo.get_stats()

    # ── KPI cards ──────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total clientes", stats["total"])
    c2.metric("Activos", stats["activos"])
    alto_muy_alto = stats["riesgo_alto"] + stats["riesgo_muy_alto"]
    c3.metric("Alto / Muy Alto riesgo", alto_muy_alto,
              delta=None if alto_muy_alto == 0 else f"{alto_muy_alto}",
              delta_color="inverse")
    c4.metric("PEPs activos", stats["peps_activos"])
    c5.metric("Revisiones próx. 30d", stats["proximas_revisiones_30d"])

    st.markdown("<hr style='border-color:#1e2130;margin:16px 0;'>", unsafe_allow_html=True)

    # ── Filtros ────────────────────────────────────────────────
    col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 3])
    with col_f1:
        filtro_estado = st.selectbox(
            "Estado", ["Todos"] + _ESTADOS_CLIENTE, key="cli_f_estado"
        )
    with col_f2:
        filtro_nivel = st.selectbox(
            "Nivel riesgo", ["Todos"] + _NIVELES_RIESGO, key="cli_f_nivel"
        )
    with col_f3:
        filtro_empresa = st.selectbox(
            "Empresa grupo", ["Todos"] + _EMPRESAS_GRUPO, key="cli_f_empresa"
        )
    with col_f4:
        filtro_search = st.text_input("🔍 Buscar por nombre o NIT", key="cli_f_search")

    with next(get_session()) as session:
        repo = ClienteRepository(session)
        clientes = repo.get_lista(
            estado=filtro_estado if filtro_estado != "Todos" else None,
            nivel_riesgo=filtro_nivel if filtro_nivel != "Todos" else None,
            empresa_grupo=filtro_empresa if filtro_empresa != "Todos" else None,
            search=filtro_search or None,
        )

    if not clientes:
        st.info("No se encontraron clientes con los filtros seleccionados.")
        return

    # ── Lista de tarjetas ──────────────────────────────────────
    for c in clientes:
        _tarjeta_cliente(c, user)


def _tarjeta_cliente(c: dict, user: dict) -> None:
    from db.database import get_session
    from db.repositories.cliente_repo import ClienteRepository

    estado_color = _ESTADO_COLOR.get(c.get("estado", ""), "#6b7280")
    nivel_color  = _NIVEL_COLOR.get(c.get("nivel_riesgo", ""), "#6b7280")
    puntaje      = c.get("puntaje_riesgo") or 0
    score_color  = "#22c55e" if puntaje <= 40 else "#f59e0b" if puntaje <= 60 else "#f97316" if puntaje <= 80 else "#ef4444"

    # Obtener contratos para pills
    with next(get_session()) as session:
        repo = ClienteRepository(session)
        contratos = repo.get_contratos(c["id"])

    empresas_activas  = [ct["empresa_grupo"] for ct in contratos if ct.get("estado") == "Activo"]
    servicios_activos = []
    for ct in contratos:
        if ct.get("estado") == "Activo":
            for sv in ct.get("servicios", []):
                if sv.get("estado") == "Activo" and sv["servicio"] not in servicios_activos:
                    servicios_activos.append(sv["servicio"])

    volumen_total = sum(
        ct.get("volumen_mensual_cop") or 0
        for ct in contratos if ct.get("estado") == "Activo"
    )

    hoy = date.today()
    proxima = c.get("proxima_revision")
    alerta_revision = proxima and (proxima - hoy).days <= 30 if proxima else False
    alerta_listas   = c.get("en_listas_restriccion") == 1

    pills_empresas  = " ".join(_pill(e, _EMPRESA_COLOR.get(e, "#6b7280")) for e in empresas_activas)
    pills_servicios = " ".join(_pill(s, _SERVICIOS_COLOR.get(s, "#6b7280")) for s in servicios_activos)
    alerta_html = ""
    if alerta_listas:
        alerta_html += (
            "<div style='background:#ef444418;border-left:3px solid #ef4444;"
            "border-radius:0 6px 6px 0;padding:6px 12px;font-size:0.78rem;"
            "color:#f87171;margin-top:8px;'>⚠️ En listas de restricción</div>"
        )
    if alerta_revision:
        dias_rest = (proxima - hoy).days if proxima else 0
        alerta_html += (
            f"<div style='background:#f59e0b18;border-left:3px solid #f59e0b;"
            f"border-radius:0 6px 6px 0;padding:6px 12px;font-size:0.78rem;"
            f"color:#fbbf24;margin-top:4px;'>🔔 Revisión en {dias_rest}d</div>"
        )

    vol_str = _fmt_cop(volumen_total) if volumen_total else "—"

    st.markdown(f"""
<div style='background:#12141c;border:1px solid #1e2130;border-radius:12px;
padding:18px 22px;margin-bottom:12px;transition:all 0.2s;'>
  <div style='display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;'>
    <div>
      <span style='font-size:1.05rem;font-weight:700;color:#f0f1f5;'>{c.get('razon_social','')}</span>
      <span style='color:#6b7280;font-size:0.78rem;margin-left:10px;'>NIT: {c.get('nit','')}</span>
    </div>
    <div style='display:flex;gap:8px;flex-wrap:wrap;align-items:center;'>
      {_badge(c.get('estado',''), estado_color)}
      {_badge(c.get('nivel_riesgo',''), nivel_color)}
    </div>
  </div>
  <div style='margin:10px 0 6px;display:flex;flex-wrap:wrap;gap:6px;align-items:center;'>
    {pills_empresas}
    {pills_servicios}
  </div>
  <div style='background:{score_color};width:{puntaje}%;height:6px;border-radius:4px;margin:8px 0;'></div>
  <div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:4px;'>
    <span style='font-size:0.72rem;color:#9ca3af;'>Puntaje: {puntaje}/100 · Vol. mensual: {vol_str}</span>
    <span style='font-size:0.72rem;color:#6b7280;'>{c.get('sector_ciiu','') or ''}</span>
  </div>
  {alerta_html}
</div>
""", unsafe_allow_html=True)

    if st.button(f"Ver ficha → {c['razon_social']}", key=f"btn_ficha_{c['id']}",
                 use_container_width=True):
        st.session_state["cliente_detalle_id"] = c["id"]
        st.rerun()


# ─────────────────────────────────────────────────────────────
# Tab: Alta de cliente
# ─────────────────────────────────────────────────────────────

def _tab_alta_cliente(user: dict) -> None:
    rol = user.get("rol", "")
    if rol not in {"admin", "compliance", "super_admin"}:
        st.warning("No tienes permisos para crear clientes.")
        return

    st.markdown("### Nuevo Cliente")
    with st.form("form_nuevo_cliente", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            razon_social   = st.text_input("Razón social *")
            nit            = st.text_input("NIT *")
            tipo_sociedad  = st.selectbox("Tipo de sociedad", [""] + _TIPOS_SOCIEDAD)
            sector_ciiu    = st.text_input("Sector / CIIU")
            fecha_const    = st.date_input("Fecha de constitución", value=None)
        with col2:
            pais           = st.text_input("País de constitución", value="Colombia")
            sitio_web      = st.text_input("Sitio web")
            direccion      = st.text_area("Dirección", height=72)
            estado_ini     = st.selectbox("Estado inicial", _ESTADOS_CLIENTE)

        st.markdown("**Perfil de riesgo**")
        col3, col4, col5 = st.columns(3)
        with col3:
            es_pep_v         = st.checkbox("Es PEP")
        with col4:
            exp_cripto_v     = st.checkbox("Exposición cripto")
        with col5:
            crypto_fr_v      = st.checkbox("Crypto friendly")

        jurisdicciones_v = st.multiselect("Jurisdicciones", Jurisdicciones.ALL)
        notas_v          = st.text_area("Notas", height=72)

        submitted = st.form_submit_button("Crear cliente", type="primary")

    if submitted:
        if not razon_social or not nit:
            st.error("Razón social y NIT son obligatorios.")
            return
        from db.database import get_session
        from db.repositories.cliente_repo import ClienteRepository
        from db.models import ClienteCreate
        data = ClienteCreate(
            razon_social=razon_social.strip(),
            nit=nit.strip(),
            tipo_sociedad=tipo_sociedad or None,
            fecha_constitucion=fecha_const if fecha_const else None,
            pais_constitucion=pais or "Colombia",
            sector_ciiu=sector_ciiu or None,
            sitio_web=sitio_web or None,
            direccion=direccion or None,
            es_pep=1 if es_pep_v else 0,
            exposicion_cripto=1 if exp_cripto_v else 0,
            crypto_friendly=1 if crypto_fr_v else 0,
            jurisdicciones=jurisdicciones_v,
            estado=estado_ini,
            notas=notas_v or None,
            creado_por=user.get("username", "sistema"),
        )
        try:
            with next(get_session()) as session:
                repo = ClienteRepository(session)
                cliente = repo.crear(data)
            st.success(f"Cliente '{cliente['razon_social']}' creado con ID {cliente['id']}.")
            st.rerun()
        except Exception as exc:
            st.error(f"Error al crear cliente: {exc}")


# ─────────────────────────────────────────────────────────────
# Ficha de cliente — vista detalle
# ─────────────────────────────────────────────────────────────

def _ficha_cliente(cliente_id: int, user: dict) -> None:
    from db.database import get_session
    from db.repositories.cliente_repo import ClienteRepository

    with next(get_session()) as session:
        repo = ClienteRepository(session)
        ficha = repo.get_ficha_completa(cliente_id)

    if not ficha:
        st.error("Cliente no encontrado.")
        return

    estado_color = _ESTADO_COLOR.get(ficha.get("estado", ""), "#6b7280")
    nivel_color  = _NIVEL_COLOR.get(ficha.get("nivel_riesgo", ""), "#6b7280")

    st.markdown(f"""
<div style='background:#12141c;border:1px solid #1e2130;border-radius:12px;
padding:20px 24px;margin-bottom:20px;'>
  <div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;'>
    <div>
      <span style='font-size:1.4rem;font-weight:800;color:#f0f1f5;'>
        {ficha.get('razon_social','')}
      </span>
      <span style='color:#6b7280;font-size:0.82rem;margin-left:12px;'>
        NIT: {ficha.get('nit','')}
      </span>
    </div>
    <div style='display:flex;gap:8px;'>
      {_badge(ficha.get('estado',''), estado_color)}
      {_badge(ficha.get('nivel_riesgo',''), nivel_color)}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    tab_info, tab_personas, tab_contratos, tab_docs, tab_historial = st.tabs([
        "🏢 Información general",
        "👥 Personas vinculadas",
        "📄 Contratos",
        "📁 Documentos",
        "📊 Historial de riesgo",
    ])

    with tab_info:
        _tab_info_general(ficha, user)
    with tab_personas:
        _tab_personas(ficha, user)
    with tab_contratos:
        _tab_contratos(ficha, user)
    with tab_docs:
        _tab_documentos(ficha, user)
    with tab_historial:
        _tab_historial_riesgo(ficha, user)


# ──── Tab: Información general ────────────────────────────────

def _tab_info_general(ficha: dict, user: dict) -> None:
    rol      = user.get("rol", "")
    puntaje  = ficha.get("puntaje_riesgo") or 0
    score_color = (
        "#22c55e" if puntaje <= 40
        else "#f59e0b" if puntaje <= 60
        else "#f97316" if puntaje <= 80
        else "#ef4444"
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Datos de identificación**")
        st.markdown(f"- **Tipo sociedad:** {ficha.get('tipo_sociedad') or '—'}")
        st.markdown(f"- **CIIU:** {ficha.get('sector_ciiu') or '—'}")
        st.markdown(f"- **País constitución:** {ficha.get('pais_constitucion') or '—'}")
        fecha_c = ficha.get("fecha_constitucion")
        st.markdown(f"- **Fecha constitución:** {fecha_c or '—'}")
        st.markdown(f"- **Dirección:** {ficha.get('direccion') or '—'}")
        st.markdown(f"- **Sitio web:** {ficha.get('sitio_web') or '—'}")
    with col2:
        st.markdown("**Perfil de riesgo SARLAFT**")
        st.markdown(f"- **PEP:** {'Sí' if ficha.get('es_pep') else 'No'}")
        st.markdown(f"- **Exposición cripto:** {'Sí' if ficha.get('exposicion_cripto') else 'No'}")
        st.markdown(f"- **Crypto friendly:** {'Sí' if ficha.get('crypto_friendly') else 'No'}")
        st.markdown(f"- **En listas restricción:** {'Sí' if ficha.get('en_listas_restriccion') else 'No'}")
        st.markdown(f"- **Última calificación:** {ficha.get('fecha_ultima_calificacion') or '—'}")
        st.markdown(f"- **Próxima revisión:** {ficha.get('proxima_revision') or '—'}")
        juris = ficha.get("jurisdicciones") or []
        if juris:
            st.markdown("- **Jurisdicciones:** " + ", ".join(juris))

    st.markdown("**Score de riesgo**")
    st.markdown(f"""
<div style='display:flex;align-items:center;gap:12px;'>
  <div style='flex:1;background:#1a1d28;border-radius:4px;height:8px;'>
    <div style='background:{score_color};width:{puntaje}%;height:8px;border-radius:4px;'></div>
  </div>
  <span style='font-weight:700;color:{score_color};font-size:0.9rem;'>{puntaje}/100</span>
</div>
""", unsafe_allow_html=True)

    if ficha.get("notas"):
        st.markdown(f"**Notas:** {ficha['notas']}")

    # ── Formulario de edición ──────────────────────────────────
    if rol in {"admin", "compliance", "super_admin"}:
        with st.expander("✏️ Editar información", expanded=False):
            with st.form("form_editar_cliente"):
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    e_razon   = st.text_input("Razón social", value=ficha.get("razon_social",""))
                    e_tipo    = st.selectbox("Tipo sociedad", [""] + _TIPOS_SOCIEDAD,
                                             index=([""] + _TIPOS_SOCIEDAD).index(ficha.get("tipo_sociedad","")) if ficha.get("tipo_sociedad") in _TIPOS_SOCIEDAD else 0)
                    e_ciiu    = st.text_input("CIIU", value=ficha.get("sector_ciiu","") or "")
                    e_pais    = st.text_input("País", value=ficha.get("pais_constitucion","Colombia"))
                    e_dir     = st.text_area("Dirección", value=ficha.get("direccion","") or "", height=72)
                    e_web     = st.text_input("Sitio web", value=ficha.get("sitio_web","") or "")
                with e_col2:
                    e_estado  = st.selectbox("Estado", _ESTADOS_CLIENTE,
                                             index=_ESTADOS_CLIENTE.index(ficha.get("estado","Prospecto")) if ficha.get("estado") in _ESTADOS_CLIENTE else 0)
                    e_pep     = st.checkbox("Es PEP", value=bool(ficha.get("es_pep")))
                    e_cripto  = st.checkbox("Exposición cripto", value=bool(ficha.get("exposicion_cripto")))
                    e_cf      = st.checkbox("Crypto friendly", value=bool(ficha.get("crypto_friendly")))
                    e_listas  = st.checkbox("En listas restricción", value=bool(ficha.get("en_listas_restriccion")))
                    e_juris   = st.multiselect("Jurisdicciones", Jurisdicciones.ALL,
                                               default=list(ficha.get("jurisdicciones") or []))
                e_notas = st.text_area("Notas", value=ficha.get("notas","") or "", height=72)
                guardar = st.form_submit_button("Guardar cambios", type="primary")

            if guardar:
                from db.database import get_session
                from db.repositories.cliente_repo import ClienteRepository
                from db.models import ClienteUpdate
                upd = ClienteUpdate(
                    razon_social=e_razon or None,
                    tipo_sociedad=e_tipo or None,
                    sector_ciiu=e_ciiu or None,
                    pais_constitucion=e_pais or None,
                    direccion=e_dir or None,
                    sitio_web=e_web or None,
                    estado=e_estado,
                    es_pep=1 if e_pep else 0,
                    exposicion_cripto=1 if e_cripto else 0,
                    crypto_friendly=1 if e_cf else 0,
                    listas_verificadas=None,
                    en_listas_restriccion=1 if e_listas else 0,
                    jurisdicciones=e_juris,
                    notas=e_notas or None,
                )
                try:
                    with next(get_session()) as session:
                        repo = ClienteRepository(session)
                        repo.actualizar(ficha["id"], upd, user.get("username","sistema"))
                    st.success("Cliente actualizado.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error: {exc}")


# ──── Tab: Personas vinculadas ─────────────────────────────────

def _tab_personas(ficha: dict, user: dict) -> None:
    rol     = user.get("rol", "")
    personas = ficha.get("personas", [])

    if not personas:
        st.info("No hay personas vinculadas.")
    else:
        for p in personas:
            activo_badge = _badge("Activo", "#22c55e") if p.get("activo") else _badge("Inactivo", "#6b7280")
            pep_badge    = _badge("PEP", "#ef4444") if p.get("es_pep") else ""
            lista_badge  = _badge("En listas", "#f97316") if p.get("en_listas_restriccion") else ""
            pct_str      = f"{p.get('pct_participacion')}%" if p.get("pct_participacion") is not None else "—"

            st.markdown(f"""
<div style='background:#12141c;border:1px solid #1e2130;border-radius:10px;
padding:14px 18px;margin-bottom:8px;'>
  <div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;'>
    <div>
      <span style='font-weight:700;color:#f0f1f5;font-size:0.95rem;'>{p.get('nombre_completo','')}</span>
      <span style='color:#6b7280;font-size:0.78rem;margin-left:8px;'>{p.get('rol','')}</span>
    </div>
    <div style='display:flex;gap:6px;'>
      {activo_badge} {pep_badge} {lista_badge}
    </div>
  </div>
  <div style='margin-top:6px;font-size:0.78rem;color:#9ca3af;'>
    Doc: {p.get('tipo_documento') or '—'} {p.get('numero_documento') or ''} ·
    Nac.: {p.get('nacionalidad') or '—'} · Participación: {pct_str}
  </div>
</div>
""", unsafe_allow_html=True)

            if rol in {"admin", "compliance", "super_admin"} and p.get("activo"):
                if st.button(f"Desactivar {p['nombre_completo']}", key=f"des_pers_{p['id']}"):
                    from db.database import get_session
                    from db.repositories.cliente_repo import ClienteRepository
                    with next(get_session()) as session:
                        repo = ClienteRepository(session)
                        repo.desactivar_persona(p["id"], user.get("username","sistema"))
                    st.success("Persona desactivada.")
                    st.rerun()

    # ── Agregar persona ────────────────────────────────────────
    if rol in {"admin", "compliance", "super_admin"}:
        with st.expander("➕ Agregar persona vinculada", expanded=False):
            with st.form("form_agregar_persona"):
                p_col1, p_col2 = st.columns(2)
                with p_col1:
                    p_nombre    = st.text_input("Nombre completo *")
                    p_tipo_doc  = st.selectbox("Tipo doc.", ["CC", "CE", "PAS", "NIT", "Otro"])
                    p_num_doc   = st.text_input("Número doc.")
                    p_nac       = st.text_input("Nacionalidad", value="Colombia")
                with p_col2:
                    p_rol       = st.selectbox("Rol *", _ROLES_PERSONA)
                    p_pct       = st.number_input("% Participación", 0.0, 100.0, 0.0, step=0.1)
                    p_pep       = st.checkbox("Es PEP")
                    p_en_listas = st.checkbox("En listas restricción")
                    p_fecha_ver = st.date_input("Fecha verificación", value=None)
                p_notas = st.text_area("Notas", height=60)
                p_submit = st.form_submit_button("Agregar persona", type="primary")

            if p_submit:
                if not p_nombre:
                    st.error("El nombre es obligatorio.")
                else:
                    from db.database import get_session
                    from db.repositories.cliente_repo import ClienteRepository
                    from db.models import PersonaCreate
                    pdata = PersonaCreate(
                        cliente_id=ficha["id"],
                        nombre_completo=p_nombre.strip(),
                        tipo_documento=p_tipo_doc,
                        numero_documento=p_num_doc or None,
                        nacionalidad=p_nac or "Colombia",
                        rol=p_rol,
                        pct_participacion=p_pct if p_pct > 0 else None,
                        es_pep=1 if p_pep else 0,
                        en_listas_restriccion=1 if p_en_listas else 0,
                        fecha_verificacion=p_fecha_ver if p_fecha_ver else None,
                        notas=p_notas or None,
                        creado_por=user.get("username","sistema"),
                    )
                    try:
                        with next(get_session()) as session:
                            repo = ClienteRepository(session)
                            repo.agregar_persona(pdata)
                        st.success("Persona agregada.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Error: {exc}")


# ──── Tab: Contratos ───────────────────────────────────────────

def _tab_contratos(ficha: dict, user: dict) -> None:
    rol      = user.get("rol", "")
    contratos = ficha.get("contratos", [])
    empresas_con_contrato = {c["empresa_grupo"] for c in contratos}

    for empresa in _EMPRESAS_GRUPO:
        contrato = next((c for c in contratos if c["empresa_grupo"] == empresa), None)
        emp_color = _EMPRESA_COLOR.get(empresa, "#6b7280")

        with st.expander(f"**{empresa}**", expanded=bool(contrato)):
            if not contrato:
                st.markdown(f"*Sin contrato registrado para {empresa}*")
            else:
                est_color = _ESTADO_COLOR.get(contrato.get("estado",""), "#6b7280")
                servicios = contrato.get("servicios", [])
                servicios_activos = [s for s in servicios if s.get("estado") == "Activo"]
                pills_sv = " ".join(
                    _pill(s["servicio"], _SERVICIOS_COLOR.get(s["servicio"], "#6b7280"))
                    for s in servicios_activos
                )
                firmado_badge = _badge("Firmado", "#22c55e") if contrato.get("contrato_firmado") else _badge("Sin firma", "#f59e0b")

                st.markdown(f"""
<div style='background:#12141c;border:1px solid #1e2130;border-radius:10px;padding:16px 20px;'>
  <div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;'>
    <div>
      {_badge(contrato.get('estado',''), est_color)}
      {firmado_badge}
      {f"<span style='color:#6b7280;font-size:0.78rem;margin-left:8px;'>No. {contrato.get('numero_contrato','')}</span>" if contrato.get('numero_contrato') else ""}
    </div>
    <span style='color:#9ca3af;font-size:0.78rem;'>
      Vol. mensual: {_fmt_cop(contrato.get('volumen_mensual_cop'))} ·
      Txns/mes: {contrato.get('num_transacciones_mes') or '—'}
    </span>
  </div>
  <div style='margin-top:8px;'>{pills_sv or "<span style='color:#6b7280;font-size:0.78rem;'>Sin servicios activos</span>"}</div>
  <div style='margin-top:8px;font-size:0.78rem;color:#9ca3af;'>
    Inicio: {contrato.get('fecha_inicio') or '—'} · Vence: {contrato.get('fecha_vencimiento') or '—'}
  </div>
  <div style='margin-top:4px;font-size:0.78rem;color:#9ca3af;'>
    Contacto op.: {contrato.get('contacto_operativo') or '—'} ({contrato.get('email_operativo') or '—'})
  </div>
</div>
""", unsafe_allow_html=True)

                # Editar volumen
                if rol in {"admin", "compliance", "super_admin", "comercial", "cic", "manager_comercial"}:
                    with st.form(f"form_vol_{contrato['id']}"):
                        v_col1, v_col2 = st.columns(2)
                        with v_col1:
                            nuevo_vol   = st.number_input(
                                "Volumen mensual COP", value=contrato.get("volumen_mensual_cop") or 0,
                                min_value=0, step=1_000_000,
                            )
                        with v_col2:
                            nuevo_txns  = st.number_input(
                                "Transacciones/mes", value=contrato.get("num_transacciones_mes") or 0,
                                min_value=0, step=1,
                            )
                        if st.form_submit_button("Actualizar volumen"):
                            from db.database import get_session
                            from db.repositories.cliente_repo import ClienteRepository
                            with next(get_session()) as session:
                                repo = ClienteRepository(session)
                                repo.actualizar_volumen(
                                    contrato["id"], int(nuevo_vol), int(nuevo_txns),
                                    user.get("username","sistema")
                                )
                            st.success("Volumen actualizado.")
                            st.rerun()

                # Servicios
                if rol in {"admin", "compliance", "super_admin"}:
                    with st.expander("Gestionar servicios", expanded=False):
                        servicios_todos = contrato.get("servicios", [])
                        servicios_existentes = {s["servicio"] for s in servicios_todos}
                        servicios_disponibles = [s for s in _SERVICIOS if s not in servicios_existentes]

                        for sv in servicios_todos:
                            sv_color = _SERVICIOS_COLOR.get(sv["servicio"], "#6b7280")
                            sv_badge = _badge(sv.get("estado",""), _ESTADO_COLOR.get(sv.get("estado",""), "#6b7280"))
                            st.markdown(f"{sv['servicio']} {sv_badge}", unsafe_allow_html=True)
                            if sv.get("estado") == "Activo":
                                if st.button(f"Suspender {sv['servicio']}", key=f"sus_sv_{sv['id']}"):
                                    from db.database import get_session
                                    from db.repositories.cliente_repo import ClienteRepository
                                    with next(get_session()) as session:
                                        repo = ClienteRepository(session)
                                        repo.actualizar_servicio(sv["id"], "Suspendido", user.get("username","sistema"))
                                    st.rerun()

                        if servicios_disponibles:
                            with st.form(f"form_sv_{contrato['id']}"):
                                nuevo_sv = st.selectbox("Agregar servicio", servicios_disponibles)
                                sv_fecha = st.date_input("Fecha activación", value=date.today())
                                sv_notas = st.text_input("Notas del servicio")
                                if st.form_submit_button("Agregar servicio"):
                                    from db.database import get_session
                                    from db.repositories.cliente_repo import ClienteRepository
                                    from db.models import ServicioCreate
                                    svdata = ServicioCreate(
                                        contrato_id=contrato["id"],
                                        servicio=nuevo_sv,
                                        estado="Activo",
                                        fecha_activacion=sv_fecha,
                                        notas=sv_notas or None,
                                        creado_por=user.get("username","sistema"),
                                    )
                                    try:
                                        with next(get_session()) as session:
                                            repo = ClienteRepository(session)
                                            repo.agregar_servicio(svdata)
                                        st.success(f"Servicio '{nuevo_sv}' agregado.")
                                        st.rerun()
                                    except Exception as exc:
                                        st.error(f"{exc}")

            # Crear contrato si no existe
            if not contrato and rol in {"admin", "compliance", "super_admin"}:
                with st.form(f"form_nuevo_contrato_{empresa}"):
                    st.markdown(f"**Nuevo contrato — {empresa}**")
                    nc1, nc2 = st.columns(2)
                    with nc1:
                        nc_estado  = st.selectbox("Estado", _ESTADOS_CLIENTE, key=f"nc_est_{empresa}")
                        nc_inicio  = st.date_input("Fecha inicio", value=None, key=f"nc_ini_{empresa}")
                        nc_vence   = st.date_input("Fecha vencimiento", value=None, key=f"nc_ven_{empresa}")
                        nc_firmado = st.checkbox("Contrato firmado", key=f"nc_firma_{empresa}")
                        nc_num     = st.text_input("Número contrato", key=f"nc_num_{empresa}")
                    with nc2:
                        nc_cop_op  = st.text_input("Contacto operativo", key=f"nc_cop_{empresa}")
                        nc_eop     = st.text_input("Email operativo", key=f"nc_eop_{empresa}")
                        nc_cop_co  = st.text_input("Contacto compliance", key=f"nc_cco_{empresa}")
                        nc_eco     = st.text_input("Email compliance", key=f"nc_eco_{empresa}")
                        nc_sla     = st.text_input("SLA contratado", key=f"nc_sla_{empresa}")
                    nc_notas = st.text_area("Notas", key=f"nc_notas_{empresa}", height=60)
                    if st.form_submit_button(f"Crear contrato {empresa}"):
                        from db.database import get_session
                        from db.repositories.cliente_repo import ClienteRepository
                        from db.models import ContratoCreate
                        cdata = ContratoCreate(
                            cliente_id=ficha["id"],
                            empresa_grupo=empresa,
                            estado=nc_estado,
                            fecha_inicio=nc_inicio if nc_inicio else None,
                            fecha_vencimiento=nc_vence if nc_vence else None,
                            contrato_firmado=1 if nc_firmado else 0,
                            numero_contrato=nc_num or None,
                            contacto_operativo=nc_cop_op or None,
                            email_operativo=nc_eop or None,
                            contacto_compliance=nc_cop_co or None,
                            email_compliance=nc_eco or None,
                            sla_contratado=nc_sla or None,
                            notas=nc_notas or None,
                            creado_por=user.get("username","sistema"),
                        )
                        try:
                            with next(get_session()) as session:
                                repo = ClienteRepository(session)
                                repo.crear_contrato(cdata)
                            st.success(f"Contrato {empresa} creado.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"{exc}")


# ──── Tab: Documentos ─────────────────────────────────────────

def _tab_documentos(ficha: dict, user: dict) -> None:
    from db.database import get_session
    from db.repositories.cliente_repo import ClienteRepository

    rol = user.get("rol", "")

    with next(get_session()) as session:
        repo = ClienteRepository(session)
        stats_docs = repo.get_stats_documentos(ficha["id"])
        docs_todos = repo.get_documentos(ficha["id"])

    # KPIs
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Total docs", stats_docs["total"])
    d2.metric("Vigentes", stats_docs["vigentes"])
    d3.metric("Pendientes", stats_docs["pendientes"])
    d4.metric("Vencidos", stats_docs["vencidos"])

    # Tabs por carpeta
    carpetas_con_docs = sorted(set(d["carpeta"] for d in docs_todos))
    if not carpetas_con_docs:
        st.info("Sin documentos registrados.")
    else:
        tabs_carpetas = st.tabs([f"{_CARPETA_ICON.get(c,'📄')} {c}" for c in carpetas_con_docs])
        for i, carpeta in enumerate(carpetas_con_docs):
            with tabs_carpetas[i]:
                docs_carpeta = [d for d in docs_todos if d["carpeta"] == carpeta]
                for doc in docs_carpeta:
                    est_color = {
                        "Vigente": "#22c55e", "Pendiente": "#f59e0b",
                        "Vencido": "#ef4444", "Archivado": "#6b7280",
                    }.get(doc.get("estado",""), "#6b7280")
                    url_html = (
                        f"<a href='{doc['url']}' target='_blank' "
                        f"style='color:#5fe9d0;font-size:0.75rem;'>Abrir ↗</a>"
                        if doc.get("url") else ""
                    )
                    st.markdown(f"""
<div style='background:#12141c;border:1px solid #1e2130;border-radius:8px;
padding:12px 16px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;'>
  <div>
    <span style='font-weight:600;color:#f0f1f5;font-size:0.88rem;'>{doc.get('titulo','')}</span>
    <span style='color:#6b7280;font-size:0.72rem;margin-left:8px;'>v{doc.get('version','1.0')} · {doc.get('formato','')}</span>
  </div>
  <div style='display:flex;gap:8px;align-items:center;'>
    {_badge(doc.get('estado',''), est_color)}
    {url_html}
  </div>
</div>
""", unsafe_allow_html=True)

                    # Historial de versiones
                    if rol in {"admin", "compliance", "super_admin"}:
                        with st.expander(f"Historial versiones: {doc['titulo']}", expanded=False):
                            with next(get_session()) as session:
                                repo2 = ClienteRepository(session)
                                hist = repo2.get_historial_documento(doc["id"])
                            if not hist:
                                st.caption("Sin historial previo.")
                            else:
                                for h in hist:
                                    st.markdown(
                                        f"- `{h.get('snapshot_at','')[:16]}` — "
                                        f"v{h.get('version','?')} · {h.get('estado','?')} · "
                                        f"por {h.get('snapshot_por','?')} · "
                                        f"{h.get('descripcion_cambio','') or ''}"
                                    )

    # Nuevo documento
    if rol in {"admin", "compliance", "super_admin"}:
        with st.expander("➕ Agregar documento", expanded=False):
            with st.form("form_nuevo_doc_cliente"):
                fd1, fd2 = st.columns(2)
                with fd1:
                    doc_titulo  = st.text_input("Título del documento *")
                    doc_carpeta = st.selectbox("Carpeta", _CARPETAS_ORDEN)
                    doc_estado  = st.selectbox("Estado", ["Vigente","Pendiente","Vencido"])
                    doc_formato = st.selectbox("Formato", _FORMATOS_DOC)
                with fd2:
                    doc_version = st.text_input("Versión", value="1.0")
                    doc_url     = st.text_input("URL (OneDrive/SharePoint)")
                    doc_fecha   = st.date_input("Fecha emisión", value=None)
                    doc_cambio  = st.text_input("Descripción del cambio")
                if st.form_submit_button("Agregar documento", type="primary"):
                    if not doc_titulo:
                        st.error("El título es obligatorio.")
                    else:
                        from db.models import ClienteDocumentoCreate
                        ddata = ClienteDocumentoCreate(
                            cliente_id=ficha["id"],
                            titulo=doc_titulo.strip(),
                            carpeta=doc_carpeta,
                            estado=doc_estado,
                            formato=doc_formato,
                            url=doc_url or None,
                            version=doc_version or "1.0",
                            fecha_emision=doc_fecha if doc_fecha else None,
                            descripcion_cambio=doc_cambio or None,
                            creado_por=user.get("username","sistema"),
                        )
                        try:
                            with next(get_session()) as session:
                                repo3 = ClienteRepository(session)
                                repo3.crear_documento(ddata)
                            st.success("Documento agregado.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Error: {exc}")


# ──── Tab: Historial de riesgo ────────────────────────────────

def _tab_historial_riesgo(ficha: dict, user: dict) -> None:
    from db.database import get_session
    from db.repositories.cliente_repo import ClienteRepository

    rol = user.get("rol", "")

    with next(get_session()) as session:
        repo = ClienteRepository(session)
        historial = repo.get_historial_riesgo(ficha["id"])

    if not historial:
        st.info("Sin historial de calificaciones.")
    else:
        # Gráfico Plotly
        try:
            import plotly.graph_objects as go
            fechas   = [str(h.get("registrado_en",""))[:10] for h in reversed(historial)]
            puntajes = [h.get("puntaje_nuevo", 0) for h in reversed(historial)]
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=fechas, y=puntajes,
                mode="lines+markers",
                line=dict(color="#7857ff", width=2),
                marker=dict(size=8, color="#7857ff"),
                name="Puntaje riesgo",
            ))
            fig.update_layout(
                paper_bgcolor="#0d0e14",
                plot_bgcolor="#12141c",
                font_color="#9ca3af",
                margin=dict(l=20, r=20, t=30, b=20),
                yaxis=dict(range=[0, 100], gridcolor="#1e2130"),
                xaxis=dict(gridcolor="#1e2130"),
                height=240,
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass

        # Timeline
        for h in historial:
            nivel_color = _NIVEL_COLOR.get(h.get("nivel_nuevo",""), "#6b7280")
            fecha_str   = str(h.get("registrado_en",""))[:16]
            cambio_str  = (
                f"{h.get('puntaje_anterior','?')} → {h.get('puntaje_nuevo','?')}"
                if h.get("puntaje_anterior") is not None
                else f"→ {h.get('puntaje_nuevo','?')}"
            )
            st.markdown(f"""
<div style='background:#12141c;border-left:3px solid {nivel_color};
border-radius:0 8px 8px 0;padding:10px 16px;margin-bottom:6px;'>
  <div style='display:flex;justify-content:space-between;align-items:center;'>
    <span style='font-weight:700;color:{nivel_color};'>{h.get('nivel_nuevo','')}</span>
    <span style='font-size:0.72rem;color:#6b7280;'>{fecha_str} · {h.get('registrado_por','')}</span>
  </div>
  <div style='font-size:0.78rem;color:#9ca3af;margin-top:4px;'>
    Puntaje: {cambio_str} · {h.get('motivo','') or ''}
  </div>
  {f"<div style='font-size:0.75rem;color:#6b7280;'>{h.get('observaciones','')}</div>" if h.get('observaciones') else ""}
</div>
""", unsafe_allow_html=True)

    # Nueva calificación
    if rol in {"admin", "compliance", "super_admin"}:
        with st.expander("📊 Nueva calificación", expanded=False):
            with st.form("form_nueva_calificacion"):
                cal1, cal2 = st.columns(2)
                with cal1:
                    cal_puntaje   = st.number_input("Puntaje nuevo (0-100)",
                                                     value=ficha.get("puntaje_riesgo") or 0,
                                                     min_value=0, max_value=100)
                    cal_nivel     = st.selectbox("Nivel nuevo", _NIVELES_RIESGO,
                                                  index=_NIVELES_RIESGO.index(ficha.get("nivel_riesgo","Sin calificar"))
                                                  if ficha.get("nivel_riesgo") in _NIVELES_RIESGO else 0)
                with cal2:
                    cal_motivo    = st.text_input("Motivo de la calificación")
                cal_obs = st.text_area("Observaciones", height=72)
                if st.form_submit_button("Registrar calificación", type="primary"):
                    from db.database import get_session
                    from db.repositories.cliente_repo import ClienteRepository
                    from db.models import CalificacionRiesgoCreate
                    cdata = CalificacionRiesgoCreate(
                        cliente_id=ficha["id"],
                        puntaje_anterior=ficha.get("puntaje_riesgo"),
                        puntaje_nuevo=int(cal_puntaje),
                        nivel_anterior=ficha.get("nivel_riesgo"),
                        nivel_nuevo=cal_nivel,
                        motivo=cal_motivo or None,
                        observaciones=cal_obs or None,
                        registrado_por=user.get("username","sistema"),
                    )
                    try:
                        with next(get_session()) as session:
                            repo = ClienteRepository(session)
                            repo.calificar(cdata)
                        st.success("Calificación registrada.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Error: {exc}")
