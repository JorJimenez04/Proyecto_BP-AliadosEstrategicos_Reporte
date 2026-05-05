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
    "Bajo":     "#5fe9d0",
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
        EstadosAliado, NivelesRiesgo, TiposAliado, EstadosSARLAFT, Roles, Jurisdicciones,
    )

    st.markdown(
        '<div style="border:2px solid #5fe9d0;border-radius:12px;'
        'padding:20px 24px 16px;margin-bottom:20px;background:#1a2744">',
        unsafe_allow_html=True,
    )

    try:
        with next(get_session()) as session:
            repo = PartnerRepository(session)
            aliado = repo.get_by_id(aliado_id)
    except Exception as _db_exc:
        st.error(f"Error al conectar con la base de datos: {_db_exc}")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if not aliado:
        st.error("Aliado no encontrado.")
        if st.button("Cerrar", key="edit_close_notfound"):
            st.session_state.pop("edit_id", None)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    es_comercial     = user.get("rol") == Roles.COMERCIAL
    rol_activo       = user.get("rol", "")
    # Solo ADMIN_PRO y AGENTE_KYC pueden editar campos SARLAFT / riesgo / PEP
    puede_sarlaft    = rol_activo in Roles.CAN_EDIT_SARLAFT
    # Comercial y agentes operativos no editan información básica
    solo_operativo   = rol_activo in (Roles.COMERCIAL, Roles.AGENTE_OPERATIVO)

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
                disabled=solo_operativo,
            )
            tipo = st.selectbox(
                "Tipo de Aliado",
                TiposAliado.ALL,
                index=TiposAliado.ALL.index(aliado.get("tipo_aliado", TiposAliado.ALL[0]))
                if aliado.get("tipo_aliado") in TiposAliado.ALL else 0,
                key=prefix + "tipo",
                disabled=solo_operativo,
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
                disabled=not puede_sarlaft,
            )

    # ── Sección 2: Relación Corporativa ──────────────────────────────────────
    _ESTADOS_EMPRESA = ["Activo", "Inactivo", "Sin relación"]
    with st.expander("Relación Corporativa"):
        col1, col2, col3 = st.columns(3)
        _val = lambda field, opts: opts.index(aliado.get(field, opts[-1])) if aliado.get(field) in opts else len(opts) - 1
        with col1:
            est_hbpo = st.selectbox("HoldingsBPO Corp", _ESTADOS_EMPRESA,
                                    index=_val("estado_hbpocorp", _ESTADOS_EMPRESA),
                                    key=prefix + "hbpo", disabled=solo_operativo)
        with col2:
            est_adamo = st.selectbox("Adamo", _ESTADOS_EMPRESA,
                                     index=_val("estado_adamo", _ESTADOS_EMPRESA),
                                     key=prefix + "adamo", disabled=solo_operativo)
        with col3:
            est_paycop = st.selectbox("Paycop", _ESTADOS_EMPRESA,
                                      index=_val("estado_paycop", _ESTADOS_EMPRESA),
                                      key=prefix + "paycop", disabled=solo_operativo)

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

        jur_actual = list(aliado.get("jurisdicciones") or [])
        jur_validas = [j for j in jur_actual if j in Jurisdicciones.ALL]
        jur_sel = st.multiselect(
            "🌍 Jurisdicciones de Operación",
            options=Jurisdicciones.ALL,
            default=jur_validas,
            key=prefix + "jurisdicciones",
            disabled=rol_activo not in Roles.CAN_EDIT_JURISDICTIONS,
            help="Solo Admin y Compliance pueden editar este campo (afecta el scoring SARLAFT).",
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
                disabled=not puede_sarlaft,
                help="Solo Admin Pro y Agente KYC pueden modificar el estado SARLAFT.",
            )
            es_pep = st.checkbox(
                "Es PEP",
                value=bool(aliado.get("es_pep", False)),
                key=prefix + "pep",
                disabled=not puede_sarlaft,
                help="Solo Admin Pro y Agente KYC pueden modificar el flag PEP.",
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
                disabled=not puede_sarlaft,
                help="Solo Admin Pro y Agente KYC pueden modificar este campo.",
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
                jurisdicciones=jur_sel,
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
                        valores_anteriores={k: aliado.get(k) for k in cambios.model_fields_set},
                        valores_nuevos=cambios.model_dump(exclude_none=True),
                        resultado="exitoso",
                        rol_usuario=user.get("rol"),
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
    """Panel de confirmación de eliminación con borde rojo. Solo ADMIN_PRO."""
    import streamlit as st
    from db.database import get_session
    from db.repositories.partner_repo import PartnerRepository
    from db.repositories.audit_repo import AuditRepository
    from config.settings import Roles as _R

    # Gatekeeper server-side — aunque el botón esté oculto en la UI
    if user.get("rol", "") not in _R.CAN_DELETE:
        st.error("🔒 Solo el Administrador Pro puede eliminar partners.")
        if st.button("Cerrar", key="del_perm_denied"):
            st.session_state.pop("delete_id", None)
            st.rerun()
        return

    try:
        with next(get_session()) as session:
            repo = PartnerRepository(session)
            aliado = repo.get_by_id(aliado_id)
    except Exception as _db_exc:
        st.error(f"Error al conectar con la base de datos: {_db_exc}")
        return

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
                        valores_anteriores=dict(aliado),
                        valores_nuevos=None,
                        resultado="exitoso",
                        rol_usuario=user.get("rol"),
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
                            rol_usuario=user.get("rol"),
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
    from config.settings import EstadosAliado, NivelesRiesgo, Roles, Jurisdicciones

    # ── Permisos ──────────────────────────────────────────────────────────────
    rol = user.get("rol", "")
    puede_editar   = rol in Roles.CAN_EDIT_PARTNERS
    puede_eliminar = rol in Roles.CAN_DELETE

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
        col5, _ = st.columns([2, 2])
        with col5:
            f_jur = st.multiselect(
                "🌍 Jurisdicción de Operación",
                options=Jurisdicciones.ALL,
                default=[],
                key="f_jur",
                help="Filtra por países donde opera el partner.",
            )

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
    if f_jur:
        filas = [
            r for r in filas
            if any(j in (_idx(r, "jurisdicciones") or []) for j in f_jur)
        ]

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

        # Jurisdicciones (badges con indicador de alto riesgo GAFI)
        jur_list = _idx(fila, "jurisdicciones") or []
        jur_html_block = ""
        if jur_list:
            badges_jur = []
            for j in jur_list[:6]:
                is_risky = j in Jurisdicciones.ALTO_RIESGO
                bg      = "#450a0a" if is_risky else "#1f2937"
                color   = "#fca5a5" if is_risky else "#9ca3af"
                border  = "#ef444455" if is_risky else "#374151"
                badges_jur.append(
                    f'<span style="background:{bg};color:{color};border:1px solid '
                    f'{border};border-radius:4px;'
                    f'padding:1px 5px;font-size:10px;white-space:nowrap">{j}</span>'
                )
            if len(jur_list) > 6:
                badges_jur.append(
                    '<span style="color:#6b7280;font-size:10px">'
                    f'+{len(jur_list)-6} más</span>'
                )
            jur_html_block = (
                '<div style="display:flex;gap:3px;flex-wrap:wrap;align-items:center;margin-top:5px">'
                '<span style="color:#9ca3af;font-size:11px;margin-right:2px">🌍</span>'
                + " ".join(badges_jur)
                + '</div>'
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
            + jur_html_block
            + f'</div>'
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


# ── Tab: Alta de Partner ──────────────────────────────────────────────────────

def _tab_alta_partner(user: dict) -> None:
    """Formulario de registro de nuevo partner (pestaña interna)."""
    import streamlit as st
    from datetime import date as _date
    from db.database import get_session
    from db.repositories.partner_repo import PartnerRepository
    from db.repositories.audit_repo import AuditRepository
    from db.models import AliadoCreate
    from config.settings import TiposAliado, NivelesRiesgo, Roles, Jurisdicciones

    st.markdown(
        '<p style="color:#9ca3af;margin-bottom:18px">'
        'Completa los datos del nuevo Banking Partner. Los campos marcados con * son obligatorios.</p>',
        unsafe_allow_html=True,
    )

    with st.form("form_nuevo_partner_alianzas", clear_on_submit=True):
        # ── SECCIÓN 1: IDENTIFICACIÓN ─────────────────────────────────────────
        st.markdown('<p class="section-title">Información Básica e Identificación</p>',
                    unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            nombre   = st.text_input("Razón Social *", placeholder="Ej: Cobre / Davivienda")
            nit      = st.text_input("NIT * (900123456-1)", placeholder="900123456-1")
        with c2:
            tipo     = st.selectbox("Tipo de Aliado *", TiposAliado.ALL)
            fecha_vinc = st.date_input("Fecha Vinculación *", value=_date.today())
        with c3:
            ciudad   = st.text_input("Ciudad")
            depto    = st.text_input("Departamento")

        # ── SECCIÓN 2: RELACIÓN CORPORATIVA ──────────────────────────────────
        st.markdown('<p class="section-title">🏢 Relación con el Grupo Corporativo</p>',
                    unsafe_allow_html=True)
        cg1, cg2, cg3 = st.columns(3)
        with cg1:
            est_hbpo   = st.selectbox("Estado en HoldingsBPO",
                                      ["Activo", "Inactivo", "Sin relación"], index=2)
        with cg2:
            est_adamo  = st.selectbox("Estado en Adamo",
                                      ["Activo", "Inactivo", "Sin relación"], index=2)
        with cg3:
            est_paycop = st.selectbox("Estado en Paycop",
                                      ["Activo", "Inactivo", "Sin relación"], index=2)

        jur_sel = st.multiselect(
            "🌍 Jurisdicciones de Operación",
            options=Jurisdicciones.ALL,
            default=[],
            key="alta_jur",
            help="Países donde opera o tiene exposición el partner. "
                 "Las jurisdicciones GAFI de alto riesgo incrementan el puntaje SARLAFT.",
        )

        # ── SECCIÓN 3: PERFIL OPERATIVO ───────────────────────────────────────
        st.markdown('<p class="section-title">💳 Perfil Operativo y Capacidades</p>',
                    unsafe_allow_html=True)
        co1, co2 = st.columns(2)
        with co1:
            crypto      = st.checkbox("¿Es Crypto Friendly?")
            adult       = st.checkbox("¿Es Adult Friendly?")
            monetizacion = st.checkbox("Permite Monetización")
            dispersion  = st.checkbox("Permite Dispersión")
        with co2:
            monedas  = st.text_input("Monedas Soportadas", placeholder="COP-USD-MXN-BRL")
            volumen  = st.text_input("Volumen Real Estimado", placeholder="Ej: 10-11M mensuales")

        clientes = st.text_area("Clientes Vinculados",
                                placeholder="Ej: Paxum, Scientia, CM Group...")
        cf1, cf2 = st.columns(2)
        with cf1:
            fecha_ini_rel = st.date_input("Fecha Inicio Relación Grupo", value=None)
        with cf2:
            fecha_fin_rel = st.date_input("Fecha Fin Relación (si aplica)", value=None)

        # ── SECCIÓN 4: COMPLIANCE ─────────────────────────────────────────────
        st.markdown('<p class="section-title">⚖️ Cumplimiento y Riesgo</p>',
                    unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        with cc1:
            riesgo = st.selectbox("Nivel de Riesgo Inicial", NivelesRiesgo.ALL, index=1)
            pep    = st.checkbox("¿Es Persona Expuesta Políticamente (PEP)?")
        with cc2:
            freq        = st.selectbox("Frecuencia Revisión",
                                       ["Anual", "Semestral", "Trimestral", "Mensual"])
            motivo_inact = st.text_area("Si está Inactivo, ¿por qué?")

        obs = st.text_area("Observaciones Adicionales de Compliance")

        submitted = st.form_submit_button("💾 Registrar Partner", type="primary")

    if submitted:
        if not nombre or not nit:
            st.error("Razón Social y NIT son obligatorios.")
            return
        try:
            nuevo = AliadoCreate(
                nombre_razon_social=nombre, nit=nit, tipo_aliado=tipo,
                fecha_vinculacion=fecha_vinc, ciudad=ciudad, departamento_geo=depto,
                nivel_riesgo=riesgo, es_pep=pep, frecuencia_revision=freq,
                observaciones_compliance=obs,
                estado_hbpocorp=est_hbpo, estado_adamo=est_adamo,
                estado_paycop=est_paycop, crypto_friendly=crypto,
                adult_friendly=adult, permite_monetizacion=monetizacion,
                permite_dispersion=dispersion, monedas_soportadas=monedas,
                clientes_vinculados=clientes, volumen_real_mensual=volumen,
                fecha_inicio_relacion=fecha_ini_rel,
                fecha_fin_relacion=fecha_fin_rel,
                motivo_inactividad=motivo_inact,
                jurisdicciones=jur_sel,
            )
            with next(get_session()) as session:
                repo  = PartnerRepository(session)
                audit = AuditRepository(session)
                nuevo_id = repo.create(nuevo, creado_por=user["id"])
                audit.registrar(
                    username=user["username"], usuario_id=user["id"],
                    accion="CREATE", entidad="aliados", entidad_id=nuevo_id,
                    descripcion=f"Nuevo partner registrado: {nombre} (NIT: {nit})",
                    valores_nuevos=nuevo.model_dump(mode="json"),
                    rol_usuario=user.get("rol"),
                )
            # Señal para mostrar éxito en el banner del módulo y en el Portafolio
            st.session_state["_alianzas_nuevo_partner"] = (
                f"✅ **{nombre}** registrado con ID #{nuevo_id}. "
                "Consulta la pestaña 📋 Portafolio."
            )
            st.session_state["_alianzas_portafolio_notify"] = (
                f"✅ **{nombre}** (ID #{nuevo_id}) registrado. El registro aparece a continuación."
            )
            st.toast(f"✅ {nombre} registrado exitosamente", icon="✅")
        except Exception as exc:
            st.error(f"Error al registrar: {exc}")


# ── Tab: Análisis de Riesgo ───────────────────────────────────────────────────

def _tab_analisis_riesgo(user: dict) -> None:
    """Vista de análisis SARLAFT, Due Diligence y riesgo operativo."""
    import streamlit as st
    from db.database import get_session
    from db.repositories.partner_repo import PartnerRepository
    from config.settings import Roles

    es_comercial = user.get("rol") == Roles.COMERCIAL

    if es_comercial:
        st.info(
            "🔒 Vista de solo lectura. El rol Comercial puede consultar el análisis "
            "pero no puede modificar niveles de riesgo ni estado SARLAFT.",
        )

    try:
        with next(get_session()) as session:
            repo               = PartnerRepository(session)
            termometro         = repo.get_termometro_sarlaft()
            stats_riesgo       = repo.get_stats_riesgo()
            stats_pipeline     = repo.get_stats_pipeline()
            sarlaft_vencidas   = repo.get_sarlaft_vencidas()
            revisiones_proximas = repo.get_revisiones_proximas(dias=30)
            volumenes          = repo.get_resumen_volumen()
    except Exception as exc:
        st.error(f"Error al cargar análisis de riesgo: {exc}")
        return

    # ── Fila superior: termómetro SARLAFT + distribución de riesgo ───────────
    col_sarlaft, col_riesgo = st.columns(2)

    _BG     = "#1f2937"
    _BORDER = "#293056"
    _GRAY   = "#9ca3af"

    with col_sarlaft:
        st.markdown(
            f'<div style="background:{_BG};border:1px solid {_BORDER};border-radius:12px;'
            f'padding:20px 24px;margin-bottom:16px">'
            f'<div style="color:{_GRAY};font-size:0.72rem;font-weight:600;'
            f'text-transform:uppercase;letter-spacing:1px;margin-bottom:14px">'
            f'🌡️ Termómetro SARLAFT</div>',
            unsafe_allow_html=True,
        )
        t_total = max(sum(termometro.values()), 1)
        for label, key, color in [
            ("Vencidos",     "vencidos",  "#ef4444"),
            ("Próximos 15d", "proximos",  "#f59e0b"),
            ("Al Día",       "al_dia",    "#5fe9d0"),
            ("Sin fecha",    "sin_fecha", "#4b5563"),
        ]:
            val = termometro.get(key, 0)
            pct = round(val / t_total * 100)
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">'
                f'<div style="width:100px;color:{_GRAY};font-size:0.78rem;text-align:right">{label}</div>'
                f'<div style="flex:1;background:#111827;border-radius:6px;height:10px;overflow:hidden">'
                f'<div style="width:{pct}%;height:100%;background:{color};border-radius:6px"></div></div>'
                f'<div style="width:50px;text-align:right">'
                f'<span style="color:{color};font-weight:700">{val}</span>'
                f'<span style="color:#4b5563;font-size:0.72rem"> ({pct}%)</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_riesgo:
        st.markdown(
            f'<div style="background:{_BG};border:1px solid {_BORDER};border-radius:12px;'
            f'padding:20px 24px;margin-bottom:16px">'
            f'<div style="color:{_GRAY};font-size:0.72rem;font-weight:600;'
            f'text-transform:uppercase;letter-spacing:1px;margin-bottom:14px">'
            f'⚠️ Distribución de Riesgo SARLAFT</div>',
            unsafe_allow_html=True,
        )
        r_total = max(sum(stats_riesgo.values()), 1)
        for nivel, color in [
            ("Muy Alto", "#ef4444"),
            ("Alto",     "#f97316"),
            ("Medio",    "#f59e0b"),
            ("Bajo",     "#5fe9d0"),
        ]:
            val = stats_riesgo.get(nivel, 0)
            pct = round(val / r_total * 100)
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">'
                f'<div style="width:65px;color:{_GRAY};font-size:0.78rem;text-align:right">{nivel}</div>'
                f'<div style="flex:1;background:#111827;border-radius:6px;height:10px;overflow:hidden">'
                f'<div style="width:{pct}%;height:100%;background:{color};border-radius:6px"></div></div>'
                f'<div style="width:50px;text-align:right">'
                f'<span style="color:{color};font-weight:700">{val}</span>'
                f'<span style="color:#4b5563;font-size:0.72rem"> ({pct}%)</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Pipeline de estados ───────────────────────────────────────────────────
    st.markdown(
        f'<div style="background:{_BG};border:1px solid {_BORDER};border-radius:12px;'
        f'padding:20px 24px;margin-bottom:16px">'
        f'<div style="color:{_GRAY};font-size:0.72rem;font-weight:600;'
        f'text-transform:uppercase;letter-spacing:1px;margin-bottom:14px">'
        f'📊 Pipeline de Estados</div>',
        unsafe_allow_html=True,
    )
    p_total = max(sum(stats_pipeline.values()), 1)
    pip_cols = st.columns(len(stats_pipeline) or 1)
    for idx, (estado, cnt) in enumerate(stats_pipeline.items()):
        color = _COLORES_PIPELINE.get(estado, "#6b7280")
        pct   = round(cnt / p_total * 100)
        pip_cols[idx].markdown(
            f'<div style="text-align:center;background:#111827;border:1px solid {color}33;'
            f'border-radius:10px;padding:14px 8px">'
            f'<div style="color:{color};font-size:1.6rem;font-weight:800">{cnt}</div>'
            f'<div style="color:{_GRAY};font-size:0.68rem;margin-top:4px">{estado}</div>'
            f'<div style="color:{color};font-size:0.65rem;margin-top:2px">{pct}%</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Partners con SARLAFT vencido ──────────────────────────────────────────
    if sarlaft_vencidas:
        st.markdown(
            f'<div style="background:#2a0f0f;border:1px solid #ef444466;border-radius:12px;'
            f'padding:20px 24px;margin-bottom:16px">'
            f'<div style="color:#ef4444;font-size:0.72rem;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:1px;margin-bottom:12px">'
            f'🚨 SARLAFT Vencidos ({len(sarlaft_vencidas)})</div>',
            unsafe_allow_html=True,
        )
        for p in sarlaft_vencidas:
            nombre_p = p.get("nombre_razon_social", "—")
            nit_p    = p.get("nit", "—")
            fecha_p  = p.get("proxima_revision_sarlaft", "—")
            riesgo_p = p.get("nivel_riesgo", "—")
            r_color  = _COLORES_RIESGO.get(riesgo_p, "#6b7280")
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:8px 0;border-bottom:1px solid #293056">'
                f'<div><span style="color:#f1f5f9;font-weight:600">{nombre_p}</span>'
                f'<span style="color:#6b7280;font-size:0.78rem;margin-left:8px">{nit_p}</span></div>'
                f'<div style="display:flex;gap:8px;align-items:center">'
                f'<span style="color:{r_color};font-size:0.75rem;font-weight:600">{riesgo_p}</span>'
                f'<span style="color:#ef4444;font-size:0.75rem">{fecha_p}</span>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Revisiones próximas 30 días ───────────────────────────────────────────
    if revisiones_proximas:
        st.markdown(
            f'<div style="background:#1a1f0f;border:1px solid #f59e0b66;border-radius:12px;'
            f'padding:20px 24px;margin-bottom:16px">'
            f'<div style="color:#f59e0b;font-size:0.72rem;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:1px;margin-bottom:12px">'
            f'⏰ Revisiones Próximas — 30 días ({len(revisiones_proximas)})</div>',
            unsafe_allow_html=True,
        )
        for p in revisiones_proximas:
            nombre_p = p.get("nombre_razon_social", "—")
            fecha_p  = p.get("proxima_revision_sarlaft", "—")
            riesgo_p = p.get("nivel_riesgo", "—")
            r_color  = _COLORES_RIESGO.get(riesgo_p, "#6b7280")
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;'
                f'padding:8px 0;border-bottom:1px solid #293056">'
                f'<span style="color:#f1f5f9">{nombre_p}</span>'
                f'<div style="display:flex;gap:8px">'
                f'<span style="color:{r_color};font-size:0.75rem">{riesgo_p}</span>'
                f'<span style="color:#f59e0b;font-size:0.75rem">{fecha_p}</span>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)


# ── Módulo maestro: Gestión de Alianzas ──────────────────────────────────────

def page_alianzas(user: dict) -> None:
    """
    🤝 Gestión de Alianzas Estratégicas — Banking Partners Hub.

    Consolida en 3 pestañas:
      📊 Monitor    — KPIs de gestión: Total, Activos, Riesgo Alto, PEPs
      📋 Portafolio — Grilla de tarjetas con filtros de búsqueda y edición
      ➕ Alta        — Formulario de registro (solo CAN_CREATE_PARTNERS)

    RBAC:
      - Pestaña Alta visible solo para admin / compliance / comercial.
    """
    import streamlit as st
    from config.settings import Roles

    # Cabecera del módulo
    st.markdown(
        '<h2 style="color:#5fe9d0;margin-bottom:2px">🤝 Gestión de Alianzas Estratégicas</h2>'
        '<p style="color:#9ca3af;margin-top:0;margin-bottom:18px">'
        'Banking Partners Hub — Monitor · Portafolio · Alta</p>',
        unsafe_allow_html=True,
    )

    # Banner de éxito post-creación (persiste un rerun)
    _success_msg = st.session_state.pop("_alianzas_nuevo_partner", None)
    if _success_msg:
        st.success(_success_msg)

    rol = user.get("rol", "")
    puede_crear = rol in Roles.CAN_CREATE_PARTNERS

    # Construcción dinámica: pestaña Alta solo si tiene permiso
    _tab_labels = ["📊 Monitor", "📋 Portafolio"]
    if puede_crear:
        _tab_labels.append("➕ Alta de Partner")

    tabs = st.tabs(_tab_labels)

    with tabs[0]:
        # KPIs rápidos de gestión: Total, Activos, Riesgo Alto, PEPs
        from app.components.dashboard_ui import page_dashboard
        page_dashboard(user)

    with tabs[1]:
        # Notificación de partner recién registrado dentro del Portafolio
        _portafolio_msg = st.session_state.pop("_alianzas_portafolio_notify", None)
        if _portafolio_msg:
            st.success(_portafolio_msg)
        page_partners(user)

    if puede_crear:
        with tabs[2]:
            _tab_alta_partner(user)
