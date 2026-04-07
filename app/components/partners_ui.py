"""
app/components/partners_ui.py
Portafolio de Banking Partners — tabla enriquecida con filtros y acciones
de edición (ADMIN / COMPLIANCE / COMERCIAL) y eliminación (ADMIN únicamente).
"""

from __future__ import annotations

# ── Color maps ────────────────────────────────────────────────────────────────
_COLORES_PIPELINE: dict[str, str] = {
    "Prospecto":       "#6b7280",
    "En Calificación": "#f59e0b",
    "Onboarding":      "#3b82f6",
    "Activo":          "#5fe9d0",
    "Suspendido":      "#f97316",
    "Terminado":       "#ef4444",
}

_COLORES_RIESGO: dict[str, str] = {
    "Bajo":     "#22c55e",
    "Medio":    "#f59e0b",
    "Alto":     "#f97316",
    "Muy Alto": "#ef4444",
}

_COLORES_SARLAFT: dict[str, str] = {
    "Al Día":      "#5fe9d0",
    "En Revisión": "#f59e0b",
    "Pendiente":   "#6b7280",
    "Vencido":     "#ef4444",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _pill(texto: str, color: str) -> str:
    """Badge HTML de una línea; sin comentarios ni posicionamiento absoluto."""
    return (
        f'<span style="background:{color}22;color:{color};border:1px solid {color}44;'
        f'border-radius:9999px;padding:2px 10px;font-size:11px;font-weight:600;'
        f'white-space:nowrap">{texto}</span>'
    )


def _capacidad_badge(label: str, activo: bool) -> str:
    color = "#5fe9d0" if activo else "#374151"
    texto_color = "#1f2937" if activo else "#6b7280"
    return (
        f'<span style="background:{color};color:{texto_color};border-radius:4px;'
        f'padding:1px 7px;font-size:10px;font-weight:600;margin-right:3px">{label}</span>'
    )


def _idx(row: dict, key: str, default=None):
    """Acceso seguro por clave a un dict de fila."""
    return row.get(key, default)


# ── Panel de Edición ──────────────────────────────────────────────────────────

def _panel_editar(aliado_id: int, user: dict) -> None:
    """Formulario de edición en línea para un aliado."""
    import streamlit as st
    from db.database import get_session
    from db.repositories.partner_repo import PartnerRepository
    from db.repositories.audit_repo import AuditRepository
    from db.models import AliadoUpdate
    from config.settings import (
        EstadosAliado, NivelesRiesgo, TiposAliado, EstadosSARLAFT, Roles,
    )

    st.markdown(
        '<div style="border:2px solid #5fe9d0;border-radius:12px;'
        'padding:20px 24px 16px;margin-bottom:20px;background:#1a2744">',
        unsafe_allow_html=True,
    )

    with next(get_session()) as session:
        repo = PartnerRepository(session)
        aliado = repo.get_by_id(aliado_id)

    if not aliado:
        st.error("Aliado no encontrado.")
        if st.button("Cerrar", key="edit_close_notfound"):
            st.session_state.pop("edit_id", None)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    es_comercial = user.get("rol") == Roles.COMERCIAL

    st.markdown(
        f'<h4 style="color:#5fe9d0;margin:0 0 16px 0">✏️ Editar: {aliado["nombre_razon_social"]}</h4>',
        unsafe_allow_html=True,
    )

    prefix = f"edit_{aliado_id}_"

    # ── Sección 1: Información Básica ─────────────────────────────────────────
    with st.expander("Información Básica", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input(
                "Razón Social",
                value=aliado.get("nombre_razon_social", ""),
                key=prefix + "nombre",
                disabled=es_comercial,
            )
            tipo = st.selectbox(
                "Tipo de Aliado",
                TiposAliado.ALL,
                index=TiposAliado.ALL.index(aliado.get("tipo_aliado", TiposAliado.ALL[0]))
                if aliado.get("tipo_aliado") in TiposAliado.ALL else 0,
                key=prefix + "tipo",
                disabled=es_comercial,
            )
        with col2:
            estado_pipeline = st.selectbox(
                "Estado Pipeline",
                EstadosAliado.ALL,
                index=EstadosAliado.ALL.index(aliado.get("estado_pipeline", EstadosAliado.PROSPECTO))
                if aliado.get("estado_pipeline") in EstadosAliado.ALL else 0,
                key=prefix + "pipeline",
            )
            nivel_riesgo = st.selectbox(
                "Nivel de Riesgo",
                NivelesRiesgo.ALL,
                index=NivelesRiesgo.ALL.index(aliado.get("nivel_riesgo", NivelesRiesgo.MEDIO))
                if aliado.get("nivel_riesgo") in NivelesRiesgo.ALL else 1,
                key=prefix + "riesgo",
                disabled=es_comercial,
            )

    # ── Sección 2: Relación Corporativa ──────────────────────────────────────
    _ESTADOS_EMPRESA = ["Activo", "Inactivo", "Sin relación"]
    with st.expander("Relación Corporativa"):
        col1, col2, col3 = st.columns(3)
        _val = lambda field, opts: opts.index(aliado.get(field, opts[-1])) if aliado.get(field) in opts else len(opts) - 1
        with col1:
            est_hbpo = st.selectbox("HoldingsBPO Corp", _ESTADOS_EMPRESA,
                                    index=_val("estado_hbpocorp", _ESTADOS_EMPRESA),
                                    key=prefix + "hbpo", disabled=es_comercial)
        with col2:
            est_adamo = st.selectbox("Adamo", _ESTADOS_EMPRESA,
                                     index=_val("estado_adamo", _ESTADOS_EMPRESA),
                                     key=prefix + "adamo", disabled=es_comercial)
        with col3:
            est_paycop = st.selectbox("Paycop", _ESTADOS_EMPRESA,
                                      index=_val("estado_paycop", _ESTADOS_EMPRESA),
                                      key=prefix + "paycop", disabled=es_comercial)

        col4, col5 = st.columns(2)
        with col4:
            fecha_inicio = st.date_input(
                "Fecha Inicio Relación",
                value=aliado.get("fecha_inicio_relacion"),
                key=prefix + "fecha_inicio",
            )
        with col5:
            fecha_fin = st.date_input(
                "Fecha Fin Relación",
                value=aliado.get("fecha_fin_relacion"),
                key=prefix + "fecha_fin",
            )

        motivo_inact = st.text_input(
            "Motivo Inactividad",
            value=aliado.get("motivo_inactividad") or "",
            key=prefix + "motivo_inact",
        )

    # ── Sección 3: Perfil Operativo ───────────────────────────────────────────
    with st.expander("Perfil Operativo"):
        col1, col2 = st.columns(2)
        with col1:
            estado_sarlaft = st.selectbox(
                "Estado SARLAFT",
                EstadosSARLAFT.ALL,
                index=EstadosSARLAFT.ALL.index(aliado.get("estado_sarlaft", EstadosSARLAFT.PENDIENTE))
                if aliado.get("estado_sarlaft") in EstadosSARLAFT.ALL else 0,
                key=prefix + "sarlaft",
                disabled=es_comercial,
            )
            es_pep = st.checkbox(
                "Es PEP",
                value=bool(aliado.get("es_pep", False)),
                key=prefix + "pep",
                disabled=es_comercial,
            )
        with col2:
            monedas = st.text_input(
                "Monedas Soportadas",
                value=aliado.get("monedas_soportadas") or "",
                key=prefix + "monedas",
            )
            volumen = st.text_input(
                "Volumen Real Mensual",
                value=aliado.get("volumen_real_mensual") or "",
                key=prefix + "volumen",
            )

        col3, col4 = st.columns(2)
        with col3:
            crypto = st.checkbox(
                "Crypto Friendly",
                value=bool(aliado.get("crypto_friendly", False)),
                key=prefix + "crypto",
            )
            adult = st.checkbox(
                "Adult Friendly",
                value=bool(aliado.get("adult_friendly", False)),
                key=prefix + "adult",
                disabled=es_comercial,
            )
        with col4:
            monetizacion = st.checkbox(
                "Permite Monetización",
                value=bool(aliado.get("permite_monetizacion", False)),
                key=prefix + "monetizacion",
            )
            dispersion = st.checkbox(
                "Permite Dispersión",
                value=bool(aliado.get("permite_dispersion", False)),
                key=prefix + "dispersion",
            )

        clientes = st.text_area(
            "Clientes Vinculados",
            value=aliado.get("clientes_vinculados") or "",
            key=prefix + "clientes",
            height=80,
        )

    # ── Botones Guardar / Cancelar ────────────────────────────────────────────
    col_g, col_c, _ = st.columns([1, 1, 4])
    with col_g:
        if st.button("💾 Guardar", key=prefix + "guardar", type="primary"):
            cambios = AliadoUpdate(
                nombre_razon_social=nombre,
                tipo_aliado=tipo,
                estado_pipeline=estado_pipeline,
                nivel_riesgo=nivel_riesgo,
                es_pep=es_pep,
                estado_sarlaft=estado_sarlaft,
                estado_hbpocorp=est_hbpo,
                estado_adamo=est_adamo,
                estado_paycop=est_paycop,
                crypto_friendly=crypto,
                adult_friendly=adult,
                permite_monetizacion=monetizacion,
                permite_dispersion=dispersion,
                monedas_soportadas=monedas or None,
                clientes_vinculados=clientes or None,
                volumen_real_mensual=volumen or None,
                motivo_inactividad=motivo_inact or None,
                fecha_inicio_relacion=fecha_inicio if fecha_inicio else None,
                fecha_fin_relacion=fecha_fin if fecha_fin else None,
                actualizado_por=user.get("id"),
            )
            try:
                with next(get_session()) as session:
                    repo = PartnerRepository(session)
                    audit = AuditRepository(session)
                    repo.update(aliado_id, cambios, actualizado_por=user.get("id") or 0)
                    audit.registrar(
                        username=user.get("username", ""),
                        accion="UPDATE",
                        entidad="aliados",
                        descripcion=f"Edición de aliado: {aliado['nombre_razon_social']}",
                        usuario_id=user.get("id"),
                        entidad_id=aliado_id,
                        valores_anteriores=str({k: aliado.get(k) for k in cambios.model_fields_set}),
                        valores_nuevos=str(cambios.model_dump(exclude_none=True)),
                        resultado="exitoso",
                    )
                st.success("Aliado actualizado.")
            except Exception as exc:
                try:
                    with next(get_session()) as session:
                        AuditRepository(session).registrar(
                            username=user.get("username", ""),
                            accion="UPDATE",
                            entidad="aliados",
                            descripcion=f"Error al editar aliado: {aliado['nombre_razon_social']} — {exc}",
                            usuario_id=user.get("id"),
                            entidad_id=aliado_id,
                            resultado="fallido",
                        )
                except Exception:
                    pass
                st.error(f"Error al guardar: {exc}")
            finally:
                st.session_state.pop("edit_id", None)
                st.rerun()
    with col_c:
        if st.button("✖ Cancelar", key=prefix + "cancelar"):
            st.session_state.pop("edit_id", None)
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ── Panel de Eliminación ──────────────────────────────────────────────────────

def _panel_eliminar(aliado_id: int, user: dict) -> None:
    """Panel de confirmación de eliminación con borde rojo."""
    import streamlit as st
    from db.database import get_session
    from db.repositories.partner_repo import PartnerRepository
    from db.repositories.audit_repo import AuditRepository

    with next(get_session()) as session:
        repo = PartnerRepository(session)
        aliado = repo.get_by_id(aliado_id)

    if not aliado:
        st.error("Aliado no encontrado.")
        if st.button("Cerrar", key="del_close_notfound"):
            st.session_state.pop("delete_id", None)
            st.rerun()
        return

    nombre = aliado["nombre_razon_social"]

    st.markdown(
        '<div style="border:2px solid #ef4444;border-radius:12px;'
        'padding:20px 24px 16px;margin-bottom:20px;background:#2a1a1a">',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<h4 style="color:#ef4444;margin:0 0 8px 0">🗑️ Eliminar aliado</h4>'
        f'<p style="color:#f1f5f9;margin:0 0 16px 0">'
        f'Esta acción es <strong>irreversible</strong>. Se eliminará permanentemente:<br>'
        f'<span style="color:#fbbf24;font-weight:600">{nombre}</span></p>',
        unsafe_allow_html=True,
    )

    col_conf, col_can, _ = st.columns([1, 1, 4])
    with col_conf:
        st.markdown("""
        <style>
        div[data-testid="stButton"] button[kind="primary"] {
            background: #EF4444 !important;
            border-color: #EF4444 !important;
            color: #ffffff !important;
            box-shadow: 0 2px 10px rgba(239,68,68,0.4) !important;
        }
        div[data-testid="stButton"] button[kind="primary"]:hover {
            background: #dc2626 !important;
            border-color: #dc2626 !important;
            box-shadow: 0 4px 16px rgba(239,68,68,0.55) !important;
        }
        </style>
        """, unsafe_allow_html=True)
        if st.button("🗑️ Confirmar eliminación", key=f"del_confirm_{aliado_id}", type="primary"):
            try:
                with next(get_session()) as session:
                    repo = PartnerRepository(session)
                    audit = AuditRepository(session)
                    repo.delete(aliado_id)
                    audit.registrar(
                        username=user.get("username", ""),
                        accion="DELETE",
                        entidad="aliados",
                        descripcion=f"Aliado eliminado: {nombre}",
                        usuario_id=user.get("id"),
                        entidad_id=aliado_id,
                        valores_anteriores=str(aliado),
                        valores_nuevos=None,
                        resultado="exitoso",
                    )
                st.warning(f"Aliado '{nombre}' eliminado.")
            except Exception as exc:
                try:
                    with next(get_session()) as session:
                        AuditRepository(session).registrar(
                            username=user.get("username", ""),
                            accion="DELETE",
                            entidad="aliados",
                            descripcion=f"Error al eliminar aliado: {nombre} — {exc}",
                            usuario_id=user.get("id"),
                            entidad_id=aliado_id,
                            resultado="fallido",
                        )
                except Exception:
                    pass
                st.error(f"Error al eliminar: {exc}")
            finally:
                st.session_state.pop("delete_id", None)
                st.rerun()
    with col_can:
        if st.button("✖ Cancelar", key=f"del_cancel_{aliado_id}"):
            st.session_state.pop("delete_id", None)
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ── Página principal ──────────────────────────────────────────────────────────

def page_partners(user: dict) -> None:
    """Página 'Portafolio de Banking Partners'."""
    import streamlit as st
    from db.database import get_session
    from db.repositories.partner_repo import PartnerRepository
    from config.settings import EstadosAliado, NivelesRiesgo, Roles

    # ── Permisos ──────────────────────────────────────────────────────────────
    rol = user.get("rol", "")
    puede_editar = rol in (Roles.ADMIN, Roles.COMPLIANCE, Roles.COMERCIAL)
    puede_eliminar = rol == Roles.ADMIN

    # ── Session state ─────────────────────────────────────────────────────────
    if "edit_id" not in st.session_state:
        st.session_state["edit_id"] = None
    if "delete_id" not in st.session_state:
        st.session_state["delete_id"] = None

    # ── Cabecera ──────────────────────────────────────────────────────────────
    st.markdown(
        '<h2 style="color:#5fe9d0;margin-bottom:4px">🤝 Portafolio de Banking Partners</h2>'
        '<p style="color:#9ca3af;margin-top:0">Gestión integral de aliados, riesgo y capacidades operativas</p>',
        unsafe_allow_html=True,
    )

    # ── Panel activo (editar o eliminar) ──────────────────────────────────────
    if st.session_state["edit_id"]:
        _panel_editar(st.session_state["edit_id"], user)

    if st.session_state["delete_id"]:
        _panel_eliminar(st.session_state["delete_id"], user)

    # ── Filtros ───────────────────────────────────────────────────────────────
    with st.expander("🔍 Filtros", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            f_estado = st.multiselect(
                "Estado Pipeline",
                EstadosAliado.ALL,
                default=[],
                key="f_estado",
            )
        with col2:
            f_riesgo = st.multiselect(
                "Nivel de Riesgo",
                NivelesRiesgo.ALL,
                default=[],
                key="f_riesgo",
            )
        with col3:
            f_buscar = st.text_input("Buscar por nombre / NIT", key="f_buscar")
        with col4:
            f_pep = st.selectbox("PEP", ["Todos", "Solo PEP", "Sin PEP"], key="f_pep")

    # ── Carga de datos ────────────────────────────────────────────────────────
    with next(get_session()) as session:
        repo = PartnerRepository(session)
        filas = repo.get_lista_enriquecida()

    # ── Aplicar filtros ───────────────────────────────────────────────────────
    if f_estado:
        filas = [r for r in filas if _idx(r, "estado_pipeline") in f_estado]
    if f_riesgo:
        filas = [r for r in filas if _idx(r, "nivel_riesgo") in f_riesgo]
    if f_buscar:
        buscar = f_buscar.lower()
        filas = [
            r for r in filas
            if buscar in (_idx(r, "nombre_razon_social") or "").lower()
            or buscar in (_idx(r, "nit") or "").lower()
        ]
    if f_pep == "Solo PEP":
        filas = [r for r in filas if _idx(r, "es_pep")]
    elif f_pep == "Sin PEP":
        filas = [r for r in filas if not _idx(r, "es_pep")]

    # ── Métricas rápidas ──────────────────────────────────────────────────────
    total = len(filas)
    activos = sum(1 for r in filas if _idx(r, "estado_pipeline") == "Activo")
    alto_riesgo = sum(1 for r in filas if _idx(r, "nivel_riesgo") in ("Alto", "Muy Alto"))
    peps = sum(1 for r in filas if _idx(r, "es_pep"))

    m1, m2, m3, m4 = st.columns(4)
    _KPI_STYLE = (
        'background:#1f2937;border:1px solid #293056;border-radius:10px;'
        'padding:14px 18px;text-align:center'
    )
    for col, valor, etiqueta, color in [
        (m1, total,      "Total Partners",  "#5fe9d0"),
        (m2, activos,    "Activos",          "#22c55e"),
        (m3, alto_riesgo,"Alto Riesgo",      "#ef4444"),
        (m4, peps,       "PEPs",             "#f59e0b"),
    ]:
        col.markdown(
            f'<div style="{_KPI_STYLE}">'
            f'<div style="font-size:28px;font-weight:700;color:{color}">{valor}</div>'
            f'<div style="font-size:12px;color:#9ca3af;margin-top:4px">{etiqueta}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabla ─────────────────────────────────────────────────────────────────
    if not filas:
        st.info("No se encontraron partners con los filtros aplicados.")
        return

    hay_acciones = puede_editar or puede_eliminar
    edit_activo = st.session_state.get("edit_id")
    del_activo = st.session_state.get("delete_id")

    for fila in filas:
        fid = _idx(fila, "id")
        nombre = _idx(fila, "nombre_razon_social", "—")
        nit = _idx(fila, "nit", "—")
        estado_pip = _idx(fila, "estado_pipeline", "—")
        riesgo = _idx(fila, "nivel_riesgo", "—")
        sarlaft = _idx(fila, "estado_sarlaft", "—")
        es_pep_fila = bool(_idx(fila, "es_pep", False))
        puntaje = _idx(fila, "puntaje_riesgo", 0) or 0

        # Resaltado de fila activa
        if fid == edit_activo:
            borde = "#5fe9d0"
            fondo = "#0f2a2a"
        elif fid == del_activo:
            borde = "#ef4444"
            fondo = "#2a0f0f"
        else:
            borde = "#293056"
            fondo = "#1f2937"

        # Capacidades operativas
        caps_html = (
            _capacidad_badge("Crypto", bool(_idx(fila, "crypto_friendly")))
            + _capacidad_badge("Adult", bool(_idx(fila, "adult_friendly")))
            + _capacidad_badge("Monet.", bool(_idx(fila, "permite_monetizacion")))
            + _capacidad_badge("Dispers.", bool(_idx(fila, "permite_dispersion")))
        )

        # Badges principales
        pip_pill   = _pill(estado_pip, _COLORES_PIPELINE.get(estado_pip, "#6b7280"))
        riesgo_pill = _pill(riesgo, _COLORES_RIESGO.get(riesgo, "#6b7280"))
        sarlaft_pill = _pill(sarlaft, _COLORES_SARLAFT.get(sarlaft, "#6b7280"))
        pep_badge  = _pill("PEP", "#f59e0b") if es_pep_fila else ""

        row_html = (
            f'<div style="background:{fondo};border:1px solid {borde};border-radius:10px;'
            f'padding:14px 18px;margin-bottom:8px">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
            f'<div style="flex:1;min-width:0">'
            f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px">'
            f'<span style="font-weight:700;color:#f1f5f9;font-size:15px">{nombre}</span>'
            f'<span style="color:#6b7280;font-size:12px">{nit}</span>'
            f'{pep_badge}'
            f'</div>'
            f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">'
            f'{pip_pill}{riesgo_pill}{sarlaft_pill}'
            f'</div>'
            f'<div style="display:flex;gap:4px;flex-wrap:wrap;align-items:center">'
            f'<span style="color:#9ca3af;font-size:11px;margin-right:4px">Capacidades:</span>'
            f'{caps_html}'
            f'</div>'
            f'</div>'
            f'<div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;min-width:80px">'
            f'<span style="color:#9ca3af;font-size:11px">Puntaje</span>'
            f'<span style="color:#5fe9d0;font-weight:700;font-size:18px">{int(puntaje)}</span>'
            f'</div>'
            f'</div>'
            f'</div>'
        )
        st.markdown(row_html, unsafe_allow_html=True)

        # Botones de acciones (fuera del HTML — Streamlit no soporta botones en markdown)
        if hay_acciones:
            btn_cols = st.columns([1, 1, 10])
            if puede_editar:
                with btn_cols[0]:
                    if st.button("✏️", key=f"edit_btn_{fid}", help=f"Editar {nombre}"):
                        st.session_state["edit_id"] = fid
                        st.session_state["delete_id"] = None
                        st.rerun()
            if puede_eliminar:
                with btn_cols[1]:
                    if st.button("🗑️", key=f"del_btn_{fid}", help=f"Eliminar {nombre}"):
                        st.session_state["delete_id"] = fid
                        st.session_state["edit_id"] = None
                        st.rerun()
