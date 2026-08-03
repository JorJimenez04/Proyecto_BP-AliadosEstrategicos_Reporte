"""
app/components/partners_ui.py
Portafolio de Banking Partners — Ficha Técnica del Riel con estándar
de Debida Diligencia avanzada (ISO / SARLAFT / GAFI).
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

# ── Criticidad Operativa (ISO/GAFI) ──────────────────────────────────────────
_COLORES_CRITICIDAD: dict[str, str] = {
    "DDI":                   "#ef4444",   # Rojo — Debida Diligencia Intensificada
    "DDI - Entidad Regulada": "#5fe9d0",  # Teal — Regulada; complejidad esperada
    "DDS-Alto":              "#f97316",   # Naranja
    "DDS-Simplificado":      "#f59e0b",   # Amarillo
    "Estándar":              "#22c55e",   # Verde
}

# Mantener mapa legacy para compatibilidad con análisis de riesgo SARLAFT
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

# Borde de tarjeta según nivel de criticidad
_BORDER_CRITICIDAD: dict[str, str] = {
    "DDI":                   "#ef4444",
    "DDI - Entidad Regulada": "#5fe9d0",
    "DDS-Alto":              "#f97316",
    "DDS-Simplificado":      "#f59e0b",
    "Estándar":              "#22c55e",
}

_SCORE_COLOR: dict[str, str] = {
    "Bajo":     "#22c55e",
    "Medio":    "#f59e0b",
    "Alto":     "#f97316",
    "Muy Alto": "#ef4444",
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


# ── Tarjeta B2B — Portafolio de Banking Partners ─────────────────────────────

_ESTADO_COLORES_B2B: dict[str, str] = {
    "Activo":          "#10b981",
    "En Calificación": "#f59e0b",
    "Onboarding":      "#3b82f6",
    "Suspendido":      "#ef4444",
    "Prospecto":       "#9ca3af",
    "Terminado":       "#4b5563",
}


def _card_banking_partner(
    partner: dict,
    edit_id=None,
    delete_id=None,
    detail_id=None,
) -> str:
    """
    Tarjeta HTML B2B para el Portafolio de Banking Partners.
    Muestra perspectiva institucional/infraestructura, desacoplada de SARLAFT.
    """
    from config.settings import Jurisdicciones

    fid    = partner.get("id")
    nombre = partner.get("nombre_razon_social") or "—"
    tipo   = partner.get("tipo_aliado") or "—"
    estado = partner.get("estado_pipeline") or "Prospecto"
    nit    = partner.get("nit") or ""

    # Jurisdicciones
    jur_list: list = partner.get("jurisdicciones") or []

    # Vinculos — usar partner_respaldo como corresponsalía de respaldo
    respaldo = partner.get("partner_respaldo")
    vinculos: list[str] = [respaldo] if respaldo else []

    # Capacidades derivadas de flags booleanos
    capacidades: list[str] = []
    if partner.get("permite_dispersion"):   capacidades.append("📤 Dispersión")
    if partner.get("permite_monetizacion"): capacidades.append("💱 Monetización")
    if partner.get("crypto_friendly"):      capacidades.append("🔷 Crypto")
    if partner.get("adult_friendly"):       capacidades.append("🔞 Adult")
    tipo_riel = partner.get("tipo_riel") or ""
    if tipo_riel and tipo_riel != "N/A":
        capacidades.append(f"⚙️ {tipo_riel}")

    # Colores de borde según estado de edición
    if fid == detail_id or fid == edit_id:
        card_border = "#5fe9d0"
        card_bg     = "rgba(6, 26, 26, 0.95)"
        card_glow   = "0 0 14px #5fe9d033"
    elif fid == delete_id:
        card_border = "#ef4444"
        card_bg     = "rgba(26, 6, 6, 0.95)"
        card_glow   = "0 0 14px #ef444433"
    else:
        estado_color = _ESTADO_COLORES_B2B.get(estado, "#293056")
        card_border  = estado_color
        card_bg      = "rgba(31, 41, 55, 0.4)"
        card_glow    = "none"

    estado_color = _ESTADO_COLORES_B2B.get(estado, "#9ca3af")
    estado_badge = (
        f'<span style="background:{estado_color}22;color:{estado_color};'
        f'border:1px solid {estado_color}44;border-radius:9999px;'
        f'padding:2px 10px;font-size:11px;font-weight:600">'
        f'{estado}</span>'
    )
    tipo_badge = (
        f'<span style="background:#1e274022;color:#93c5fd;border:1px solid #3b4f7a;'
        f'border-radius:9999px;padding:2px 9px;font-size:11px;font-weight:500">'
        f'🏦 {tipo}</span>'
    )

    # ── Jurisdicciones ────────────────────────────────────────────────────────
    jur_html = ""
    if jur_list:
        badges = []
        for j in jur_list[:6]:
            is_risky = j in Jurisdicciones.ALTO_RIESGO
            jbg      = "#450a0a" if is_risky else "#1e2740"
            jcolor   = "#fca5a5" if is_risky else "#93c5fd"
            jborder  = "#ef444466" if is_risky else "#3b4f7a"
            badges.append(
                f'<span style="background:{jbg};color:{jcolor};'
                f'border:1px solid {jborder};border-radius:5px;'
                f'padding:2px 7px;font-size:10px;font-weight:500">'
                f'{j}</span>'
            )
        if len(jur_list) > 6:
            badges.append(
                f'<span style="color:#6b7280;font-size:10px">+{len(jur_list)-6} más</span>'
            )
        jur_html = (
            '<div style="margin-bottom:10px">'  
            '<div style="color:#64748b;font-size:10px;text-transform:uppercase;'
            'letter-spacing:.5px;margin-bottom:5px">🌍 Alcance Geográfico</div>'
            '<div style="display:flex;gap:4px;flex-wrap:wrap">'
            + " ".join(badges)
            + '</div></div>'
        )

    # ── Capacidades ───────────────────────────────────────────────────────────
    caps_html = ""
    if capacidades:
        cap_badges = " ".join(
            f'<span style="background:#1e3a5f;color:#93c5fd;border:1px solid #3b4f7a;'
            f'border-radius:6px;padding:2px 8px;font-size:11px;font-weight:600">'
            f'{c}</span>'
            for c in capacidades
        )
        caps_html = (
            '<div style="margin-bottom:10px">'  
            '<div style="color:#64748b;font-size:10px;text-transform:uppercase;'
            'letter-spacing:.5px;margin-bottom:5px">⚡ Capacidades Operativas</div>'
            '<div style="display:flex;gap:4px;flex-wrap:wrap">'
            + cap_badges
            + '</div></div>'
        )
    else:
        caps_html = (
            '<div style="margin-bottom:10px">'  
            '<div style="color:#64748b;font-size:10px;text-transform:uppercase;'
            'letter-spacing:.5px;margin-bottom:5px">⚡ Capacidades Operativas</div>'
            '<span style="color:#4b5563;font-size:11px">Sin capacidades registradas</span>'
            '</div>'
        )

    # ── Red de corresponsalías ────────────────────────────────────────────────
    vinculos_html = ""
    if vinculos:
        vin_badges = " ".join(
            f'<span style="background:#1c2a1e;color:#86efac;border:1px solid #16a34a55;'
            f'border-radius:6px;padding:2px 8px;font-size:11px;font-weight:500">'
            f'🔗 {v}</span>'
            for v in vinculos
        )
        vinculos_html = (
            '<div style="margin-bottom:10px">'  
            '<div style="color:#64748b;font-size:10px;text-transform:uppercase;'
            'letter-spacing:.5px;margin-bottom:5px">🔗 Red de Corresponsalías</div>'
            '<div style="display:flex;gap:4px;flex-wrap:wrap">'
            + vin_badges
            + '</div></div>'
        )

    nit_str = f'<span style="color:#64748b;font-size:12px;margin-left:6px">{nit}</span>' if nit else ""

    return (
        f'<div style="background:{card_bg};border:1.5px solid {card_border};'
        f'border-radius:12px;padding:16px 20px 14px;margin-bottom:2px;'
        f'box-shadow:{card_glow}">'

        # Encabezado
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;'
        f'margin-bottom:10px;flex-wrap:wrap;gap:6px">'
        f'<div>'
        f'<span style="font-weight:700;color:#f1f5f9;font-size:16px">{nombre}</span>'
        + nit_str +
        f'</div>'
        f'<div style="display:flex;gap:5px;flex-wrap:wrap;align-items:center">'
        f'{tipo_badge}{estado_badge}'
        f'</div>'
        f'</div>'

        # Cuerpo
        + jur_html
        + caps_html
        + vinculos_html

        + '</div>'  # end card
    )


# ── Ficha Técnica del Riel (Vista Detalle) ────────────────────────────────────

def _panel_detalle_ficha(aliado_id: int, user: dict) -> None:
    """
    Ficha Técnica Institucional B2B del Banking Partner.
    Vista KYB orientada a infraestructura, desacoplada de SARLAFT/cripto.
    """
    import streamlit as st
    from db.database import get_session
    from db.repositories.partner_repo import PartnerRepository
    from config.settings import Jurisdicciones

    st.markdown(
        '<div style="border:2px solid #3b82f6;border-radius:14px;'
        'padding:22px 26px 18px;margin-bottom:20px;background:#0d1525">',
        unsafe_allow_html=True,
    )

    try:
        with next(get_session()) as session:
            repo   = PartnerRepository(session)
            aliado = repo.get_by_id(aliado_id)
    except Exception as _db_exc:
        st.error(f"Error al conectar con la base de datos: {_db_exc}")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if not aliado:
        st.error("Aliado no encontrado.")
        if st.button("Cerrar", key="detail_close_notfound"):
            st.session_state.pop("detail_id", None)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # ── Campos del aliado ─────────────────────────────────────────────────────
    nombre    = aliado.get("nombre_razon_social") or "—"
    nit       = aliado.get("nit") or "—"
    estado    = aliado.get("estado_pipeline") or "Prospecto"
    tipo      = aliado.get("tipo_aliado") or "—"
    jur_list  = aliado.get("jurisdicciones") or []
    respaldo  = aliado.get("partner_respaldo") or None
    vinculos  = [respaldo] if respaldo else []
    fid       = aliado.get("id") or aliado_id

    # Capacidades derivadas de flags
    capacidades: list[tuple[str, bool]] = [
        ("📤 Dispersión",     bool(aliado.get("permite_dispersion"))),
        ("💱 Monetización",   bool(aliado.get("permite_monetizacion"))),
        ("🔷 Crypto",         bool(aliado.get("crypto_friendly"))),
        ("🔞 Adult",          bool(aliado.get("adult_friendly"))),
    ]
    tipo_riel = aliado.get("tipo_riel") or ""
    if tipo_riel and tipo_riel != "N/A":
        capacidades.append((f"⚙️ {tipo_riel}", True))

    # ── Encabezado ────────────────────────────────────────────────────────────
    e_color = _ESTADO_COLORES_B2B.get(estado, "#9ca3af")
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:flex-start;flex-wrap:wrap;gap:10px;margin-bottom:18px">'
        f'<div>'
        f'<div style="font-size:20px;font-weight:800;color:#f1f5f9;margin-bottom:3px">'
        f'{nombre}</div>'
        f'<div style="color:#64748b;font-size:13px">NIT: {nit}</div>'
        f'</div>'
        f'<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">'
        f'<span style="background:#1e274022;color:#93c5fd;border:1px solid #3b4f7a;'
        f'border-radius:9999px;padding:3px 12px;font-size:12px;font-weight:500">'
        f'🏦 {tipo}</span>'
        f'<span style="background:{e_color}22;color:{e_color};'
        f'border:1px solid {e_color}44;border-radius:9999px;'
        f'padding:3px 14px;font-size:12px;font-weight:700">'
        f'{estado}</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Sección: Parámetros de negocio + Corresponsalías ─────────────────────
    col_neg, col_vin = st.columns(2)

    with col_neg:
        st.markdown(
            '<div style="background:#ffffff08;border-radius:10px;padding:14px 16px">'
            '<div style="color:#5fe9d0;font-size:11px;text-transform:uppercase;'
            'letter-spacing:.7px;font-weight:700;margin-bottom:12px">'
            '📊 Parámetros de Negocio</div>',
            unsafe_allow_html=True,
        )

        def _param_row(label: str, value: str) -> None:
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;'
                f'align-items:baseline;padding:5px 0;'
                f'border-bottom:1px solid #1e2740">'
                f'<span style="color:#64748b;font-size:12px">{label}</span>'
                f'<span style="color:#e2e8f0;font-size:13px;font-weight:600">{value}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Jurisdicción operativa — primera de la lista o "—"
        jur_display = jur_list[0] if jur_list else "—"
        if len(jur_list) > 1:
            jur_display += f" +{len(jur_list)-1}"

        _param_row("Tipo de Alianza",         tipo)
        _param_row("Jurisdicción Operativa",   jur_display)
        _param_row("Tiempo de Liquidación",    aliado.get("sla_garantizado") or "—")
        _param_row("Esquema de Comisiones",    aliado.get("fee_structure") or "—")
        _param_row("Límite Operativo Diario",  aliado.get("daily_limit") or "—")
        _param_row("Volumen Mensual",          aliado.get("volumen_real_mensual") or "—")

        # Jurisdicciones completas si hay más de 1
        if len(jur_list) > 1:
            badges = []
            for j in jur_list:
                is_risky = j in Jurisdicciones.ALTO_RIESGO
                jbg      = "#450a0a" if is_risky else "#1e2740"
                jcol     = "#fca5a5" if is_risky else "#93c5fd"
                jbor     = "#ef444466" if is_risky else "#3b4f7a"
                badges.append(
                    f'<span style="background:{jbg};color:{jcol};'
                    f'border:1px solid {jbor};border-radius:5px;'
                    f'padding:2px 7px;font-size:10px">{j}</span>'
                )
            st.markdown(
                '<div style="margin-top:10px;display:flex;gap:4px;flex-wrap:wrap">'
                + " ".join(badges) + '</div>',
                unsafe_allow_html=True,
            )

        st.markdown('</div>', unsafe_allow_html=True)

    with col_vin:
        st.markdown(
            '<div style="background:#ffffff08;border-radius:10px;padding:14px 16px">'
            '<div style="color:#5fe9d0;font-size:11px;text-transform:uppercase;'
            'letter-spacing:.7px;font-weight:700;margin-bottom:12px">'
            '🔗 Red de Corresponsalías</div>',
            unsafe_allow_html=True,
        )
        if vinculos:
            for v in vinculos:
                st.markdown(
                    f'<div style="border-left:3px solid #3b82f6;'
                    f'background:#1e2740;border-radius:0 8px 8px 0;'
                    f'padding:10px 14px;margin-bottom:8px">'
                    f'<span style="color:#93c5fd;font-size:13px;font-weight:600">'
                    f'🏦 {v}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div style="color:#4b5563;font-size:12px;padding:8px 0">'
                'Sin corresponsalías registradas</div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            '<div style="margin-top:10px;color:#64748b;font-size:11px">'
            'Registra el Partner de Respaldo en el formulario de edición '
            'para ampliar esta sección.</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-top:18px'></div>", unsafe_allow_html=True)

    # ── Tabs: Capacidades + KYB Compliance ───────────────────────────────────
    tab_caps, tab_kyb = st.tabs(["⚡ Capacidades Técnicas", "📚 Estado de Documentación"])

    with tab_caps:
        st.markdown(
            '<p style="color:#9ca3af;font-size:12px;margin-bottom:14px">'
            'Capacidades operativas activas del riel de infraestructura.</p>',
            unsafe_allow_html=True,
        )
        cap_cols = st.columns(min(len(capacidades), 3))
        for idx, (label, activo) in enumerate(capacidades):
            bg    = "#0d2d1e" if activo else "#1a1f2e"
            color = "#10b981" if activo else "#4b5563"
            bord  = "#10b98133" if activo else "#293056"
            icono = "✅" if activo else "✗"
            cap_cols[idx % 3].markdown(
                f'<div style="background:{bg};border:1px solid {bord};'
                f'border-radius:10px;padding:12px 14px;text-align:center;'
                f'margin-bottom:8px">'
                f'<div style="font-size:12px;color:{color};font-weight:600;'
                f'margin-bottom:4px">{label}</div>'
                f'<div style="font-size:20px">{icono}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    with tab_kyb:
        st.markdown(
            '<p style="color:#9ca3af;font-size:12px;margin-bottom:14px">'
            'Checklist KYB — estado de documentación institucional del partner.</p>',
            unsafe_allow_html=True,
        )

        # Estado SARLAFT → estado Due Diligence
        sarlaft_val   = aliado.get("estado_sarlaft") or "Pendiente"
        sarlaft_map   = {"Al Día": "Aprobado", "En Revisión": "En Revisión",
                         "Pendiente": "Pendiente", "Vencido": "Pendiente"}
        dd_estado     = sarlaft_map.get(sarlaft_val, "Pendiente")

        # Licencia activa
        licencia_ok   = bool(aliado.get("numero_licencia"))
        regulada_ok   = bool(aliado.get("es_entidad_regulada"))

        # Pipeline avanzado → contrato firmado
        pipeline_avz  = aliado.get("estado_pipeline") in ("Onboarding", "Activo")

        # Certificaciones ISO
        certs         = aliado.get("certificaciones") or []

        kyb_items = [
            ("Contrato de Alianza",          "Aprobado"     if pipeline_avz  else "Pendiente"),
            ("Formulario Due Diligence",      dd_estado),
            ("Certificación Bancaria",        "Aprobado"     if regulada_ok   else "Pendiente"),
            ("Licencia Operativa / SFC",      "Aprobado"     if licencia_ok   else "Pendiente"),
            ("Ficha SARLAFT",                 dd_estado),
            ("Certificaciones ISO/Técnicas",
             "Aprobado" if certs else "Pendiente"),
        ]

        _EST_ICON  = {"Aprobado": "✅", "En Revisión": "⏳", "Pendiente": "❌"}
        _EST_COLOR = {"Aprobado": "#10b981", "En Revisión": "#f59e0b", "Pendiente": "#6b7280"}

        for doc_nombre, doc_estado in kyb_items:
            icono  = _EST_ICON.get(doc_estado, "❌")
            dcolor = _EST_COLOR.get(doc_estado, "#6b7280")
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;'
                f'align-items:center;padding:9px 14px;margin-bottom:6px;'
                f'background:#ffffff07;border-radius:8px;'
                f'border-left:3px solid {dcolor}">'
                f'<span style="color:#e2e8f0;font-size:13px">{doc_nombre}</span>'
                f'<span style="background:{dcolor}22;color:{dcolor};'
                f'border:1px solid {dcolor}44;border-radius:9999px;'
                f'padding:2px 10px;font-size:11px;font-weight:700">'
                f'{icono} {doc_estado}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        if certs:
            st.markdown(
                '<div style="margin-top:10px;color:#64748b;font-size:11px">'
                f'Certificaciones activas: {", ".join(certs)}</div>',
                unsafe_allow_html=True,
            )

    # ── Pie de página ─────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="margin-top:16px;padding-top:12px;'
        f'border-top:1px solid #1e2740;display:flex;'
        f'justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">'
        f'<span style="color:#4b5563;font-size:11px">ID de registro: #{fid}</span>'
        f'<span style="color:#4b5563;font-size:11px">'
        f'Account Manager: {aliado.get("account_manager") or "—"}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Botón Cerrar ─────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("✖ Cerrar ficha", key=f"detail_close_{aliado_id}"):
        st.session_state.pop("detail_id", None)
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


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
        TiposRiel,
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

    es_comercial     = user.get("rol") in (Roles.COMERCIAL, Roles.CIC)
    rol_activo       = user.get("rol", "")
    # Solo ADMIN_PRO y AGENTE_KYC pueden editar campos SARLAFT / riesgo / PEP
    puede_sarlaft    = rol_activo in Roles.CAN_EDIT_SARLAFT
    # Solo ADMIN y COMPLIANCE pueden editar campos de Criticidad y Cumplimiento ISO
    puede_compliance = rol_activo in Roles.CAN_EDIT_COMPLIANCE
    # Comercial y agentes operativos no editan información básica
    solo_operativo   = rol_activo in (Roles.COMERCIAL, Roles.CIC, Roles.AGENTE_OPERATIVO)

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
                "Nivel de Riesgo SARLAFT",
                NivelesRiesgo.ALL,
                index=NivelesRiesgo.ALL.index(aliado.get("nivel_riesgo", NivelesRiesgo.MEDIO))
                if aliado.get("nivel_riesgo") in NivelesRiesgo.ALL else 1,
                key=prefix + "riesgo",
                disabled=not puede_sarlaft,
                help="El Nivel de Criticidad Operativa se recalculará automáticamente al guardar.",
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

    # ── Sección 4: Ficha Técnica del Riel ────────────────────────────────────
    with st.expander("⚙️ Ficha Técnica del Riel"):
        if es_comercial:
            st.info("📋 Rol Comercial: puede editar datos operativos del riel.")
        ftr1, ftr2 = st.columns(2)
        with ftr1:
            _tipo_riel_actual = aliado.get("tipo_riel") or TiposRiel.ALL[0]
            _tipo_riel_idx    = TiposRiel.ALL.index(_tipo_riel_actual) if _tipo_riel_actual in TiposRiel.ALL else 0
            tipo_riel = st.selectbox(
                "Tipo de Riel",
                TiposRiel.ALL,
                index=_tipo_riel_idx,
                key=prefix + "tipo_riel",
                help="Dispersión: envío de fondos · Recaudo: cobro · Crypto: activos digitales",
            )
        with ftr2:
            es_regulada = st.checkbox(
                "🏛️ Entidad Regulada (licencia financiera)",
                value=bool(aliado.get("es_entidad_regulada", False)),
                key=prefix + "regulada",
                disabled=not puede_compliance,
                help="Marcar si el partner posee resolución de la SFC u otro ente regulador.",
            )
    col_g, col_c, _ = st.columns([1, 1, 4])
    with col_g:
        if st.button("💾 Guardar", key=prefix + "guardar", type="primary"):
            # Detectar cambios en campos de criticidad/compliance para auditoría enriquecida
            _campos_compliance = {"es_entidad_regulada"}
            _campos_criticidad = {"nivel_riesgo", "es_entidad_regulada"}
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
                # Ficha Técnica del Riel
                tipo_riel=tipo_riel or None,
                es_entidad_regulada=es_regulada,
                actualizado_por=user.get("id"),
            )
            try:
                with next(get_session()) as session:
                    repo  = PartnerRepository(session)
                    audit = AuditRepository(session)
                    repo.update(aliado_id, cambios, actualizado_por=user.get("id") or 0)

                    # Auditoría estándar
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

                    # Auditoría ISO enriquecida para cambios de criticidad
                    _set_changed = cambios.model_fields_set
                    if _campos_criticidad & _set_changed:
                        audit.registrar(
                            username=user.get("username", ""),
                            accion="ESTADO_CHANGE",
                            entidad="aliados",
                            descripcion=(
                                f"Cambio de Criticidad/Riesgo: {aliado['nombre_razon_social']} — "
                                f"nivel_riesgo: {aliado.get('nivel_riesgo')} → {nivel_riesgo} | "
                                f"es_entidad_regulada: {aliado.get('es_entidad_regulada')} → {es_regulada}"
                            ),
                            usuario_id=user.get("id"),
                            entidad_id=aliado_id,
                            valores_anteriores={k: aliado.get(k) for k in _campos_criticidad},
                            valores_nuevos={
                                "nivel_riesgo": nivel_riesgo,
                                "es_entidad_regulada": es_regulada,
                            },
                            resultado="exitoso",
                            rol_usuario=user.get("rol"),
                        )
                    if _campos_compliance & _set_changed:
                        audit.registrar(
                            username=user.get("username", ""),
                            accion="UPDATE",
                            entidad="aliados_compliance",
                            descripcion=(
                                f"Actualización ISO/Compliance: "
                                f"{aliado['nombre_razon_social']}"
                            ),
                            usuario_id=user.get("id"),
                            entidad_id=aliado_id,
                            valores_anteriores={
                                k: aliado.get(k)
                                for k in _campos_compliance & _set_changed
                            },
                            valores_nuevos={
                                k: cambios.model_dump(exclude_none=True).get(k)
                                for k in _campos_compliance & _set_changed
                            },
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
    """Página 'Portafolio de Banking Partners — Ficha del Riel'."""
    import streamlit as st
    from db.database import get_session
    from db.repositories.partner_repo import PartnerRepository
    from config.settings import EstadosAliado, NivelesRiesgo, Roles, Jurisdicciones

    # ── Permisos ──────────────────────────────────────────────────────────────
    rol = user.get("rol", "")
    puede_editar   = rol in Roles.CAN_EDIT_PARTNERS
    puede_eliminar = rol in Roles.CAN_DELETE

    # ── Session state ─────────────────────────────────────────────────────────
    for _key in ("edit_id", "delete_id", "detail_id"):
        if _key not in st.session_state:
            st.session_state[_key] = None

    # ── Cabecera ──────────────────────────────────────────────────────────────
    st.markdown(
        '<h2 style="color:#5fe9d0;margin-bottom:4px">🤝 Portafolio de Banking Partners</h2>'
        '<p style="color:#9ca3af;margin-top:0">Ficha del Riel — Debida Diligencia · ISO · SARLAFT</p>',
        unsafe_allow_html=True,
    )

    # ── Paneles activos ───────────────────────────────────────────────────────
    if st.session_state["detail_id"]:
        _panel_detalle_ficha(st.session_state["detail_id"], user)

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
    alto_riesgo = sum(
        1 for r in filas
        if _idx(r, "nivel_criticidad", "Estándar") in ("DDI", "DDI - Entidad Regulada", "DDS-Alto")
    )
    peps = sum(1 for r in filas if _idx(r, "es_pep"))

    m1, m2, m3, m4 = st.columns(4)
    _KPI_STYLE = (
        'background:#1f2937;border:1px solid #293056;border-radius:10px;'
        'padding:14px 18px;text-align:center'
    )
    for col, valor, etiqueta, color in [
        (m1, total,      "Total Partners",  "#5fe9d0"),
        (m2, activos,    "Activos",          "#22c55e"),
        (m3, alto_riesgo,"DDI / Alta Criti.", "#ef4444"),
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

    edit_activo = st.session_state.get("edit_id")
    del_activo  = st.session_state.get("delete_id")

    for fila in filas:
        fid          = _idx(fila, "id")
        nombre       = _idx(fila, "nombre_razon_social", "—")
        nit          = _idx(fila, "nit", "—")
        tipo         = _idx(fila, "tipo_aliado", "—")
        estado_pip   = _idx(fila, "estado_pipeline", "—")
        criticidad   = _idx(fila, "nivel_criticidad", "Estándar")
        riesgo       = _idx(fila, "nivel_riesgo", "—")
        sarlaft      = _idx(fila, "estado_sarlaft", "—")
        es_pep_fila  = bool(_idx(fila, "es_pep", False))
        es_regulada  = bool(_idx(fila, "es_entidad_regulada", False))
        puntaje      = _idx(fila, "puntaje_riesgo", 0) or 0
        tipo_riel    = _idx(fila, "tipo_riel") or ""
        fecha_rev    = _idx(fila, "fecha_proxima_revision")

        # ── Colores de tarjeta ────────────────────────────────────────────────
        if fid == edit_activo or fid == st.session_state.get("detail_id"):
            card_border = "#5fe9d0"
            card_bg     = "#061a1a"
            card_glow   = "0 0 14px #5fe9d033"
        elif fid == del_activo:
            card_border = "#ef4444"
            card_bg     = "#1a0606"
            card_glow   = "0 0 14px #ef444433"
        else:
            card_border = _BORDER_CRITICIDAD.get(criticidad, "#293056")
            card_bg     = "#1a1f2e"
            card_glow   = "none"

        # ── Capacidades ───────────────────────────────────────────────────────
        caps_html = (
            _capacidad_badge("🔷 Crypto",    bool(_idx(fila, "crypto_friendly")))
            + _capacidad_badge("🔞 Adult",   bool(_idx(fila, "adult_friendly")))
            + _capacidad_badge("💱 Monet.",  bool(_idx(fila, "permite_monetizacion")))
            + _capacidad_badge("📤 Dispers.", bool(_idx(fila, "permite_dispersion")))
        )
        # ── HTML de la tarjeta B2B ────────────────────────────────────────────
        card_html = _card_banking_partner(
            fila,
            edit_id=edit_activo,
            delete_id=del_activo,
            detail_id=st.session_state.get("detail_id"),
        )

        with st.container():
            st.markdown(card_html, unsafe_allow_html=True)

            # ── Pie de tarjeta: botones de acción ─────────────────────────────
            btn_c1, btn_c2, btn_c3, _ = st.columns([2, 2, 2, 6])

            with btn_c1:
                if st.button("📋 Ver Ficha", key=f"view_btn_{fid}",
                             use_container_width=True):
                    st.session_state["detail_id"] = fid
                    st.session_state["edit_id"]   = None
                    st.session_state["delete_id"] = None
                    st.rerun()

            with btn_c2:
                if puede_editar:
                    if st.button("✏️ Editar", key=f"edit_btn_{fid}",
                                 use_container_width=True):
                        st.session_state["edit_id"]   = fid
                        st.session_state["detail_id"] = None
                        st.session_state["delete_id"] = None
                        st.rerun()

            with btn_c3:
                if puede_eliminar:
                    if st.button("🗑️ Eliminar", key=f"del_btn_{fid}",
                                 use_container_width=True):
                        st.session_state["delete_id"] = fid
                        st.session_state["edit_id"]   = None
                        st.session_state["detail_id"] = None
                        st.rerun()

        st.markdown(
            '<hr style="border:0;border-top:1px solid #1e2740;margin:4px 0 14px 0">',
            unsafe_allow_html=True,
        )


# ── Tab: Alta de Partner ──────────────────────────────────────────────────────

def _tab_alta_partner(user: dict) -> None:
    """Formulario de registro de nuevo partner (pestaña interna)."""
    import streamlit as st
    from datetime import date as _date
    from db.database import get_session
    from db.repositories.partner_repo import PartnerRepository
    from db.repositories.audit_repo import AuditRepository
    from db.models import AliadoCreate
    from config.settings import TiposAliado, Roles, Jurisdicciones, TiposRiel

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
            nit      = st.text_input("NIT (900123456-1 — opcional)", placeholder="Ej: 900123456-1")
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

        # ── SECCIÓN 4: FICHA TÉCNICA DEL RIEL ────────────────────────────────
        st.markdown('<p class="section-title">⚙️ Ficha Técnica del Riel</p>',
                    unsafe_allow_html=True)
        fr1, fr2 = st.columns(2)
        with fr1:
            tipo_riel = st.selectbox(
                "Tipo de Riel",
                TiposRiel.ALL,
                help="Dispersión: salida · Recaudo: cobro · Crypto: activos digitales",
            )
        with fr2:
            es_regulada = st.checkbox(
                "🏛️ Entidad Regulada (posee licencia financiera)",
                help="Activa la etiqueta 'DDI - Entidad Regulada' en el scoring SARLAFT.",
            )

        submitted = st.form_submit_button("💾 Registrar Partner", type="primary")

    if submitted:
        if not nombre:
            st.error("La Razón Social es obligatoria.")
            return
        try:
            nuevo = AliadoCreate(
                nombre_razon_social=nombre, nit=nit.strip() or None, tipo_aliado=tipo,
                fecha_vinculacion=fecha_vinc, ciudad=ciudad, departamento_geo=depto,
                # Safe infrastructure defaults — not collected from UI
                nivel_riesgo="Medio",
                es_pep=False,
                frecuencia_revision="Anual",
                estado_sarlaft="Al Día",
                contrato_firmado=True,
                lista_ofac_ok=True,
                listas_verificadas=True,
                estado_hbpocorp=est_hbpo, estado_adamo=est_adamo,
                estado_paycop=est_paycop, crypto_friendly=crypto,
                adult_friendly=adult, permite_monetizacion=monetizacion,
                permite_dispersion=dispersion, monedas_soportadas=monedas,
                clientes_vinculados=clientes, volumen_real_mensual=volumen,
                fecha_inicio_relacion=fecha_ini_rel,
                fecha_fin_relacion=fecha_fin_rel,
                jurisdicciones=jur_sel if jur_sel else [],
                # Ficha Técnica del Riel
                tipo_riel=tipo_riel or None,
                es_entidad_regulada=es_regulada,
                # Gobernanza defaults (no longer collected from UI)
                certificaciones=[],
                numero_licencia=None,
                partner_respaldo=None,
                pct_concentracion=None,
                nivel_criticidad="Estándar",
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


# ── Monitor Operativo de Rieles ───────────────────────────────────────────────

def _tab_monitor_operativo(user: dict) -> None:
    """Tablero de control operativo: capacidad comercial por unidad de negocio y volumen financiero."""
    import streamlit as st
    import datetime as _dt
    import pandas as _pd
    import altair as _alt
    from db.database import get_session
    from db.repositories.partner_repo import PartnerRepository

    st.markdown(
        '<h3 style="color:#5fe9d0;margin-bottom:4px">📊 Monitor Operativo de Rieles</h3>'
        '<p style="color:#9ca3af;margin-top:0;margin-bottom:18px">'
        'Capacidad comercial · Volumen financiero · Unidades de negocio</p>',
        unsafe_allow_html=True,
    )

    # ── Carga única de datos (fuente compartida para todos los componentes) ───
    with next(get_session()) as _s:
        _repo = PartnerRepository(_s)
        _filas = _repo.get_lista_enriquecida()

    # ── KPIs Globales del Portafolio ─────────────────────────────────────────
    _total_p    = len(_filas)
    _activos_p  = sum(1 for r in _filas if _idx(r, "estado_pipeline") == "Activo")
    _alto_r_p   = sum(
        1 for r in _filas
        if _idx(r, "nivel_riesgo") in ("Alto", "Muy Alto")
    )
    _onboard_p  = sum(1 for r in _filas if _idx(r, "estado_pipeline") == "Onboarding")
    _pct_act_p  = f"{round(_activos_p / _total_p * 100)}% del portafolio" if _total_p else ""

    import plotly.graph_objects as _go

    _KPI_S = (
        "background:#0d1117;border:1px solid #1e2130;border-radius:12px;"
        "padding:16px 20px;text-align:center;"
    )

    # Activos por empresa del grupo corporativo
    _campos_empresas = [
        ("estado_hbpocorp", "Holdings BPO",        "#3b82f6"),
        ("estado_adamo",    "Adamo Services",       "#10b981"),
        ("estado_paycop",   "PayCop International", "#f59e0b"),
    ]
    _labels_donut = []
    _values_donut = []
    _colors_donut = []
    for _campo_e, _nombre_e, _color_e in _campos_empresas:
        _n = sum(
            1 for r in _filas
            if (_idx(r, _campo_e) or "").strip() == "Activo"
        )
        _labels_donut.append(_nombre_e)
        _values_donut.append(_n)
        _colors_donut.append(_color_e)

    # 2 cols: izquierda = ambas KPI cards apiladas; derecha = donut
    _kp_left, _kp_chart = st.columns([1, 2])

    with _kp_left:
        st.markdown(
            f'<div style="display:flex;flex-direction:column;gap:8px;">'
            f'<div style="{_KPI_S}">'
            f'<div style="color:#6b7280;font-size:0.62rem;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;">'
            f'Total Partners</div>'
            f'<div style="color:#5fe9d0;font-size:2rem;font-weight:800;line-height:1;">'
            f'{_total_p}</div>'
            f'</div>'
            f'<div style="{_KPI_S}">'
            f'<div style="color:#6b7280;font-size:0.62rem;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;">'
            f'Partners Activos</div>'
            f'<div style="color:#22c55e;font-size:2rem;font-weight:800;line-height:1;">'
            f'{_activos_p}</div>'
            f'<div style="color:#6b7280;font-size:0.72rem;margin-top:4px;">'
            f'{_pct_act_p}</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with _kp_chart:
        _total_donut = sum(_values_donut)
        if _total_donut > 0:
            _fig_corp = _go.Figure(_go.Pie(
                labels=_labels_donut,
                values=_values_donut,
                hole=0.62,
                domain=dict(x=[0.0, 0.55], y=[0.0, 1.0]),
                marker=dict(
                    colors=_colors_donut,
                    line=dict(color="#0d1117", width=3),
                ),
                textinfo="none",
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "%{value} partners activos<br>"
                    "%{percent}<extra></extra>"
                ),
                direction="clockwise",
                sort=False,
            ))
            _fig_corp.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=True,
                legend=dict(
                    font=dict(color="#9ca3af", size=11),
                    bgcolor="rgba(0,0,0,0)",
                    orientation="v",
                    x=0.60, y=0.5,
                    xanchor="left",
                    yanchor="middle",
                    itemclick=False,
                    itemdoubleclick=False,
                ),
                margin=dict(t=12, b=12, l=12, r=12),
                height=175,
                annotations=[
                    dict(
                        text=f"<b>{_total_donut}</b>",
                        font=dict(color="#f9fafb", size=26, family="Inter, sans-serif"),
                        x=0.275, y=0.56,
                        showarrow=False,
                    ),
                    dict(
                        text="activos",
                        font=dict(color="#6b7280", size=11, family="Inter, sans-serif"),
                        x=0.275, y=0.38,
                        showarrow=False,
                    ),
                ],
            )
            st.plotly_chart(
                _fig_corp,
                use_container_width=True,
                config={"displayModeBar": False},
            )
        else:
            st.markdown(
                f'<div style="{_KPI_S};display:flex;align-items:center;'
                f'justify-content:center;min-height:175px;">'
                f'<div>'
                f'<div style="color:#6b7280;font-size:0.72rem;text-align:center;">'
                f'Participaci\u00f3n por Empresa</div>'
                f'<div style="color:#4b5563;font-size:0.82rem;text-align:center;'
                f'margin-top:6px;">Sin partners activos</div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<div style='margin-bottom:20px'></div>", unsafe_allow_html=True)

    # ── Bloque: Relación con el Grupo Corporativo ─────────────────────────────
    st.markdown(
        '<p style="font-weight:600;color:#e2e8f0;margin-bottom:10px">'
        '🏢 Relación con el Grupo Corporativo</p>',
        unsafe_allow_html=True,
    )

    # Definición de entidades reales del Holding y su campo de estado en DB
    _HOLDING_ENTITIES = [
        {
            "nombre":    "Holdings BPO",
            "icono":     "💼",
            "campo_db":  "estado_hbpocorp",
            "badge":     "COMPLIANCE CORPORATIVO",
            "badge_bg":  "#1d4ed8",
            "badge_fg":  "#93c5fd",
        },
        {
            "nombre":    "Adamo Services",
            "icono":     "🏦",
            "campo_db":  "estado_adamo",
            "badge":     "SERVICIOS TECNOLOGICOS",
            "badge_bg":  "#065f46",
            "badge_fg":  "#6ee7b7",
        },
        {
            "nombre":    "PayCop International",
            "icono":     "💳",
            "campo_db":  "estado_paycop",
            "badge":     "PAGOS Y SOLUCIONES FINANCIERAS",
            "badge_bg":  "#78350f",
            "badge_fg":  "#fcd34d",
        },
    ]

    # Badges micro-píldora por estado de relación (opacidad 10%)
    _BADGE_REL = {
        "Activo":       "background:rgba(16,185,129,.12);color:#34d399;",
        "Inactivo":     "background:rgba(245,158,11,.12);color:#fbbf24;",
        "Sin relación": "background:rgba(156,163,175,.12);color:#9ca3af;",
    }
    _BADGE_BASE = "padding:3px 10px;border-radius:6px;font-size:.72rem;font-weight:700;text-transform:uppercase;white-space:nowrap;"

    # Color de acento superior por entidad (glow sutil)
    _GLOW_COLOR = ["#3b82f6", "#10b981", "#f59e0b"]

    _corp_cols = st.columns(len(_HOLDING_ENTITIES))

    for _col, _ent, _color in zip(_corp_cols, _HOLDING_ENTITIES, _GLOW_COLOR):
        _campo = _ent["campo_db"]

        _bbg       = _ent["badge_bg"]
        _bfg       = _ent["badge_fg"]
        _badge_txt = _ent["badge"]
        _icono     = _ent["icono"]
        _nombre    = _ent["nombre"]

        _activos   = [r for r in _filas if (_idx(r, _campo) or "").strip() == "Activo"]
        _inactivos = [r for r in _filas if (_idx(r, _campo) or "").strip() in ("Inactivo", "Suspendido", "Terminado")]
        _sin_rel   = [r for r in _filas if (_idx(r, _campo) or "").strip() not in ("Activo", "Inactivo", "Suspendido", "Terminado")]

        _n_act  = len(_activos)
        _n_inac = len(_inactivos)
        _n_sin  = len(_sin_rel)
        _total  = _n_act + _n_inac + _n_sin
        _pct    = round(_n_act / _total * 100) if _total else 0

        if _pct >= 70:
            _salud_color, _salud_label = "#22c55e", "Saludable"
        elif _pct >= 40:
            _salud_color, _salud_label = "#f59e0b", "En Alerta"
        else:
            _salud_color, _salud_label = "#ef4444", "Cr\u00edtico"

        _circ  = 163.4
        _f_a   = round((_n_act  / _total * _circ), 1) if _total else 0
        _f_i   = round((_n_inac / _total * _circ), 1) if _total else 0
        _off_a = round(_circ * 0.25, 1)
        _off_i = round(_circ * 0.25 - _f_a, 1)

        _svg = (
            f"<svg width='72' height='72' viewBox='0 0 72 72' xmlns='http://www.w3.org/2000/svg'>"
            f"<circle cx='36' cy='36' r='26' fill='none' stroke='#1e2130' stroke-width='8'/>"
            f"<circle cx='36' cy='36' r='26' fill='none' stroke='#22c55e' stroke-width='8'"
            f" stroke-dasharray='{_f_a} {_circ - _f_a}' stroke-dashoffset='{_off_a}'"
            f" transform='rotate(-90 36 36)' stroke-linecap='round'/>"
            f"<circle cx='36' cy='36' r='26' fill='none' stroke='#ef4444' stroke-width='8' opacity='0.7'"
            f" stroke-dasharray='{_f_i} {_circ - _f_i}' stroke-dashoffset='{_off_i}'"
            f" transform='rotate(-90 36 36)' stroke-linecap='round'/>"
            f"<text x='36' y='32' text-anchor='middle' fill='#f9fafb' font-size='12' font-weight='800'"
            f" font-family='Inter,sans-serif'>{_pct}%</text>"
            f"<text x='36' y='44' text-anchor='middle' fill='#6b7280' font-size='6' font-weight='600'"
            f" font-family='Inter,sans-serif' letter-spacing='0.5'>ACTIVOS</text>"
            f"</svg>"
        )

        def _build_rows(partners: list, e_color: str, icon: str) -> str:
            if not partners:
                return (
                    f"<div style='color:#4b5563;font-size:0.72rem;"
                    f"font-style:italic;padding:4px 0;'>Sin partners</div>"
                )
            html = ""
            for _p in partners:
                _nom = _idx(_p, "nombre_razon_social") or "\u2014"
                _nom_short = (_nom[:18] + "\u2026") if len(_nom) > 18 else _nom
                html += (
                    f"<div style='display:flex;align-items:center;gap:5px;"
                    f"padding:5px 6px;border-radius:6px;margin-bottom:2px;background:#0a0d14;'>"
                    f"<span style='color:{e_color};font-size:0.6rem;'>{icon}</span>"
                    f"<span style='color:#d1d5db;font-size:0.76rem;'>{_nom_short}</span>"
                    f"</div>"
                )
            return html

        _rows_act  = _build_rows(_activos,   "#22c55e", "\u25cf")
        _rows_inac = _build_rows(_inactivos, "#ef4444", "\u25a0")
        _rows_sin  = _build_rows(_sin_rel,   "#4b5563", "\u25cb")

        _pa = round(_n_act  / _total * 100) if _total else 0
        _pi = round(_n_inac / _total * 100) if _total else 0
        _ps = 100 - _pa - _pi
        _mini_bar = (
            f"<div style='display:flex;height:3px;border-radius:99px;"
            f"overflow:hidden;gap:1px;margin-bottom:12px;'>"
            f"<div style='flex:{_pa};background:#22c55e;border-radius:99px;'></div>"
            f"<div style='flex:{_pi};background:#ef4444;opacity:0.7;border-radius:99px;'></div>"
            f"<div style='flex:{_ps};background:#1e2130;border-radius:99px;'></div>"
            f"</div>"
        ) if _total else ""

        _label_badge = (
            f"<span style='background:{_bbg}22;color:{_bfg};border:1px solid {_bfg}33;"
            f"font-size:0.62rem;font-weight:700;letter-spacing:0.7px;border-radius:20px;"
            f"padding:3px 10px;text-transform:uppercase;'>{_badge_txt}</span>"
        )

        _col.markdown(
            f"<div style='background:#0d1117;border:1px solid #1e2130;"
            f"border-top:2px solid {_color};border-radius:12px;padding:16px 14px;"
            f"box-shadow:0 4px 12px rgba(0,0,0,0.3);'>"
            f"<div style='display:flex;justify-content:space-between;"
            f"align-items:flex-start;margin-bottom:10px;'>"
            f"<div style='font-size:0.88rem;font-weight:700;color:#f1f5f9;"
            f"margin-bottom:5px;'>{_icono} {_nombre}</div>"
            f"<div>{_svg}</div></div>"
            f"<div style='display:grid;grid-template-columns:1fr 1fr 1fr;"
            f"gap:6px;margin-bottom:10px;'>"
            f"<div style='background:#0a0d14;border-radius:8px;padding:8px;"
            f"border:1px solid #1e2130;text-align:center;'>"
            f"<div style='color:#22c55e;font-size:1.3rem;font-weight:800;"
            f"line-height:1;'>{_n_act}</div>"
            f"<div style='color:#6b7280;font-size:0.55rem;margin-top:2px;"
            f"letter-spacing:0.8px;font-weight:600;'>ACTIVOS</div></div>"
            f"<div style='background:#0a0d14;border-radius:8px;padding:8px;"
            f"border:1px solid #1e2130;text-align:center;'>"
            f"<div style='color:#ef4444;font-size:1.3rem;font-weight:800;"
            f"line-height:1;'>{_n_inac}</div>"
            f"<div style='color:#6b7280;font-size:0.55rem;margin-top:2px;"
            f"letter-spacing:0.8px;font-weight:600;'>INACTIVOS</div></div>"
            f"<div style='background:#0a0d14;border-radius:8px;padding:8px;"
            f"border:1px solid #1e2130;text-align:center;'>"
            f"<div style='color:#4b5563;font-size:1.3rem;font-weight:800;"
            f"line-height:1;'>{_n_sin}</div>"
            f"<div style='color:#6b7280;font-size:0.55rem;margin-top:2px;"
            f"letter-spacing:0.8px;font-weight:600;'>SIN REL.</div></div>"
            f"</div>"
            f"{_mini_bar}"
            f"<div style='display:flex;gap:10px;margin-bottom:12px;'>"
            f"<span style='display:flex;align-items:center;gap:4px;"
            f"color:#6b7280;font-size:0.62rem;'>"
            f"<span style='width:6px;height:6px;border-radius:50%;"
            f"background:#22c55e;display:inline-block;'></span>Activos</span>"
            f"<span style='display:flex;align-items:center;gap:4px;"
            f"color:#6b7280;font-size:0.62rem;'>"
            f"<span style='width:6px;height:6px;border-radius:50%;"
            f"background:#ef4444;display:inline-block;opacity:0.7;'></span>Inactivos</span>"
            f"<span style='display:flex;align-items:center;gap:4px;"
            f"color:#6b7280;font-size:0.62rem;'>"
            f"<span style='width:6px;height:6px;border-radius:50%;"
            f"background:#1e2130;display:inline-block;'></span>Sin rel.</span>"
            f"</div>"
            f"<div style='border-top:1px solid #1e2130;padding-top:10px;'>"
            f"<div style='margin-bottom:8px;'>"
            f"<div style='display:flex;align-items:center;gap:5px;margin-bottom:5px;'>"
            f"<span style='width:5px;height:5px;border-radius:50%;"
            f"background:#22c55e;display:inline-block;'></span>"
            f"<span style='color:#22c55e;font-size:0.60rem;font-weight:700;"
            f"letter-spacing:0.8px;text-transform:uppercase;'>"
            f"Activos ({_n_act})</span></div>{_rows_act}</div>"
            f"<div style='margin-bottom:8px;'>"
            f"<div style='display:flex;align-items:center;gap:5px;margin-bottom:5px;'>"
            f"<span style='width:5px;height:5px;border-radius:50%;"
            f"background:#ef4444;display:inline-block;opacity:0.7;'></span>"
            f"<span style='color:#ef4444;font-size:0.60rem;font-weight:700;"
            f"letter-spacing:0.8px;text-transform:uppercase;'>"
            f"Inactivos ({_n_inac})</span></div>{_rows_inac}</div>"
            f"<div>"
            f"<div style='display:flex;align-items:center;gap:5px;margin-bottom:5px;'>"
            f"<span style='width:5px;height:5px;border-radius:50%;"
            f"background:#4b5563;display:inline-block;'></span>"
            f"<span style='color:#4b5563;font-size:0.60rem;font-weight:700;"
            f"letter-spacing:0.8px;text-transform:uppercase;'>"
            f"Sin Relaci\u00f3n ({_n_sin})</span></div>{_rows_sin}</div>"
            f"</div>"
            f"<div style='margin-top:12px;border-top:1px solid #1e2130;"
            f"padding-top:10px;'>{_label_badge}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-bottom:20px'></div>", unsafe_allow_html=True)

    total       = len(_filas)
    activos     = sum(1 for r in _filas if _idx(r, "estado_pipeline") == "Activo")
    suspendidos = [r for r in _filas if _idx(r, "estado_pipeline") == "Suspendido"]

    # ── KPIs principales ──────────────────────────────────────────────────────
    _KPI = (
        "background:#1f2937;border:1px solid #293056;border-radius:10px;"
        "padding:16px 20px;text-align:center;"
    )
    k1, k2, k3 = st.columns(3)

    k1.markdown(
        f'<div style="{_KPI}">'
        f'<div style="font-size:1.9rem;font-weight:700;color:#22c55e">{activos} / {total}</div>'
        f'<div style="font-size:.78rem;color:#9ca3af;margin-top:4px">Rieles Activos / Total</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    _vol_vals = []
    for _r in _filas:
        _v = _idx(_r, "pct_concentracion")
        try:
            _vol_vals.append(float(_v))
        except (TypeError, ValueError):
            pass
    _vol_total = sum(_vol_vals)
    _vol_display = f"{_vol_total:.1f}%" if _vol_vals else "N/D"
    k2.markdown(
        f'<div style="{_KPI}">'
        f'<div style="font-size:1.9rem;font-weight:700;color:#3b82f6">{_vol_display}</div>'
        f'<div style="font-size:.78rem;color:#9ca3af;margin-top:4px">Concentración de Carga (acum.)</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    _tasa = max(0.0, 100.0 - len(suspendidos) * 5.0)
    _tasa_color = "#22c55e" if _tasa >= 95 else "#f59e0b" if _tasa >= 80 else "#ef4444"
    k3.markdown(
        f'<div style="{_KPI}">'
        f'<div style="font-size:1.9rem;font-weight:700;color:{_tasa_color}">{_tasa:.1f}%</div>'
        f'<div style="font-size:.78rem;color:#9ca3af;margin-top:4px">Tasa de Éxito de la Red</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<div style='margin-bottom:20px'></div>", unsafe_allow_html=True)

    # ── Alertas operativas (cuellos de botella) ───────────────────────────────
    _alertas = False
    for _r in suspendidos:
        st.error(
            f"🔴 Riel **{_idx(_r, 'nombre_razon_social', '—')}** en estado **Suspendido** — "
            "verificar continuidad operativa y activar riel de respaldo."
        )
        _alertas = True

    _hoy = _dt.date.today()
    for _r in _filas:
        _fecha = _idx(_r, "fecha_proxima_revision")
        if _fecha:
            try:
                _d = _fecha.date() if hasattr(_fecha, "date") else _dt.date.fromisoformat(str(_fecha))
                _dias = (_d - _hoy).days
                if 0 <= _dias <= 30:
                    st.warning(
                        f"⚠️ **{_idx(_r, 'nombre_razon_social', '—')}** — Documentación KYB vence "
                        f"en **{_dias} días** ({_d.strftime('%d/%m/%Y')}). Renovar Contrato/DD."
                    )
                    _alertas = True
            except (ValueError, TypeError):
                pass

    if not _alertas:
        st.success("✅ Todos los rieles operativos dentro de parámetros normales.")

    st.markdown("<hr style='border-color:#293056;margin:20px 0'>", unsafe_allow_html=True)

    # ── Matriz de Unidades de Negocio ─────────────────────────────────────────
    st.markdown(
        '<p style="font-weight:600;color:#e2e8f0;margin-bottom:10px">'
        '🖥️ Matriz de Estado — Rieles en Tiempo Real</p>',
        unsafe_allow_html=True,
    )

    if not _filas:
        st.caption("No hay rieles de infraestructura registrados para mostrar en el monitor operativo.")
        return

    # Construir filas del dataframe
    _rows = []
    for _r in _filas:
        _nombre  = _idx(_r, "nombre_razon_social") or "—"
        _tipo    = _idx(_r, "tipo_aliado") or _idx(_r, "tipo_riel") or "—"
        _estado  = (_idx(_r, "estado_pipeline") or "—").upper()

        _pct = _idx(_r, "pct_concentracion")
        try:
            _vol_num = float(_pct) if _pct is not None else 0.0
        except (TypeError, ValueError):
            _vol_num = 0.0
        _vol_str = f"${_vol_num:.2f} USD"

        _crypto  = bool(_idx(_r, "crypto_friendly"))
        _adult   = bool(_idx(_r, "adult_friendly"))
        _disp    = bool(_idx(_r, "permite_dispersion"))
        _monet   = bool(_idx(_r, "permite_monetizacion"))

        _rows.append({
            "🏢 Aliado":            _nombre,
            "🤝 Tipo de Riel":       _tipo,
            "📋 Estado Operativo":   _estado,
            "💰 Volumen Canalizado": _vol_str,
            "🔵 CriptoFriendly":     "✅ SÍ" if _crypto else "❌ NO",
            "🔞 AdultFriendly":      "✅ SÍ" if _adult  else "❌ NO",
            "📥 Dispersa":           "📥 SÍ" if _disp   else "❌ NO",
            "📤 Monetiza":           "📤 SÍ" if _monet  else "❌ NO",
        })

    _df_matriz = _pd.DataFrame(_rows)
    st.dataframe(_df_matriz, use_container_width=True, hide_index=True)

    st.markdown("<div style='margin-bottom:24px'></div>", unsafe_allow_html=True)

    # ── Gráficas de Control Gerencial ─────────────────────────────────────────
    _gcol1, _gcol2 = st.columns(2)

    # Gráfica 1: Volumen Total Canalizado por Riel
    with _gcol1:
        st.markdown(
            '<p style="font-weight:600;color:#e2e8f0;margin-bottom:8px">'
            '💰 Volumen Canalizado por Riel</p>',
            unsafe_allow_html=True,
        )
        _vol_data: dict[str, float] = {}
        for _r in _filas:
            _n = _idx(_r, "nombre_razon_social") or "—"
            _p = _idx(_r, "pct_concentracion")
            try:
                _vol_data[_n] = float(_p) if _p is not None else 0.0
            except (TypeError, ValueError):
                _vol_data[_n] = 0.0

        _df_vol = _pd.DataFrame(
            {"Aliado": list(_vol_data.keys()), "Volumen (USD)": list(_vol_data.values())}
        ).set_index("Aliado")

        if _df_vol["Volumen (USD)"].sum() > 0:
            st.bar_chart(_df_vol, color="#3b82f6")
        else:
            st.caption("Sin datos de volumen registrados — campo `pct_concentracion` vacío.")

    # Gráfica 2: Capacidad de la Red por Unidades de Negocio (barras apiladas por estado)
    with _gcol2:
        st.markdown(
            '<p style="font-weight:600;color:#e2e8f0;margin-bottom:8px">'
            '⚡ Capacidad de la Red por Unidad de Negocio</p>',
            unsafe_allow_html=True,
        )
        # Construir filas long-form: una entrada por (partner, vertical habilitada)
        _cap_rows = []
        for _r in _filas:
            _estado_r = (_idx(_r, "estado_pipeline") or "Otro").upper()
            if bool(_idx(_r, "permite_dispersion")):
                _cap_rows.append({"Vertical": "📥 Dispersión", "Estado": _estado_r})
            if bool(_idx(_r, "permite_monetizacion")):
                _cap_rows.append({"Vertical": "📤 Monetización", "Estado": _estado_r})
            if bool(_idx(_r, "crypto_friendly")):
                _cap_rows.append({"Vertical": "🔵 Cripto", "Estado": _estado_r})
            if bool(_idx(_r, "adult_friendly")):
                _cap_rows.append({"Vertical": "🔞 Adult", "Estado": _estado_r})

        if _cap_rows:
            _df_cap = (
                _pd.DataFrame(_cap_rows)
                .groupby(["Vertical", "Estado"])
                .size()
                .reset_index(name="Rieles")
            )
            _estado_order = ["ACTIVO", "ONBOARDING", "EN CALIFICACIÓN", "SUSPENDIDO", "PROSPECTO", "OTRO"]
            _color_domain = ["ACTIVO", "ONBOARDING", "EN CALIFICACIÓN", "SUSPENDIDO", "PROSPECTO", "OTRO"]
            _color_range  = ["#22c55e", "#3b82f6", "#f59e0b", "#ef4444", "#9ca3af", "#6b7280"]
            # Columna numérica para orden de apilado (alt.Order solo acepta 'ascending'/'descending')
            _rank_map = {s: i for i, s in enumerate(_estado_order)}
            _df_cap["_orden"] = _df_cap["Estado"].map(lambda e: _rank_map.get(e, 99))
            _chart_cap = (
                _alt.Chart(_df_cap)
                .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
                .encode(
                    x=_alt.X("Vertical:N", title="Vertical de Negocio",
                              axis=_alt.Axis(labelColor="#9ca3af", titleColor="#9ca3af")),
                    y=_alt.Y("Rieles:Q", title="Rieles disponibles",
                              axis=_alt.Axis(labelColor="#9ca3af", titleColor="#9ca3af",
                                             tickMinStep=1)),
                    color=_alt.Color(
                        "Estado:N",
                        scale=_alt.Scale(domain=_color_domain, range=_color_range),
                        legend=_alt.Legend(
                            title="Estado Operativo",
                            labelColor="#9ca3af",
                            titleColor="#9ca3af",
                        ),
                    ),
                    order=_alt.Order("_orden:Q", sort="ascending"),
                    tooltip=["Vertical:N", "Estado:N", "Rieles:Q"],
                )
                .properties(height=260, background="transparent")
                .configure_view(strokeWidth=0)
            )
            st.altair_chart(_chart_cap, use_container_width=True)
        else:
            st.caption("Sin datos de capacidades registrados.")


# ── Módulo maestro: Gestión de Alianzas ──────────────────────────────────────

def page_alianzas(user: dict) -> None:
    """
    🤝 Gestión de Alianzas Estratégicas — Banking Partners Hub.

    Consolida en 3 pestañas:
      📊 Monitor    — Tablero operativo: salud de rieles, KPIs de red, distribución de carga
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
        _tab_monitor_operativo(user)

    with tabs[1]:
        # Notificación de partner recién registrado dentro del Portafolio
        _portafolio_msg = st.session_state.pop("_alianzas_portafolio_notify", None)
        if _portafolio_msg:
            st.success(_portafolio_msg)
        page_partners(user)

    if puede_crear:
        with tabs[2]:
            _tab_alta_partner(user)
