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
    if partner.get("sla_garantizado"):      capacidades.append("⚡ SLA Garantizado")
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
    sla       = aliado.get("sla_garantizado") or "—"
    respaldo  = aliado.get("partner_respaldo") or None
    vinculos  = [respaldo] if respaldo else []
    fid       = aliado.get("id") or aliado_id

    # Capacidades derivadas de flags
    capacidades: list[tuple[str, bool]] = [
        ("📤 Dispersión",     bool(aliado.get("permite_dispersion"))),
        ("💱 Monetización",   bool(aliado.get("permite_monetizacion"))),
        ("🔷 Crypto",         bool(aliado.get("crypto_friendly"))),
        ("🔞 Adult",          bool(aliado.get("adult_friendly"))),
        ("⚡ SLA Garantizado", bool(aliado.get("sla_garantizado"))),
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
        _param_row("Tiempo de Liquidación",    sla)
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
        TiposRiel, CertificacionesISO,
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
    # Solo ADMIN y COMPLIANCE pueden editar campos de Criticidad y Cumplimiento ISO
    puede_compliance = rol_activo in Roles.CAN_EDIT_COMPLIANCE
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
            sla_garantizado = st.text_input(
                "SLA Garantizado",
                value=aliado.get("sla_garantizado") or "",
                key=prefix + "sla",
                placeholder="Ej: 99.9% uptime / resolución < 4h",
            )

    # ── Sección 5: Cumplimiento ISO & Gobernanza ──────────────────────────────
    with st.expander("🛡️ Cumplimiento ISO & Gobernanza"):
        if not puede_compliance:
            st.warning(
                "🔒 Solo Admin y Compliance pueden editar los campos de "
                "Criticidad y Cumplimiento ISO."
            )
        fiso1, fiso2 = st.columns(2)
        with fiso1:
            es_regulada = st.checkbox(
                "🏛️ Entidad Regulada (licencia financiera)",
                value=bool(aliado.get("es_entidad_regulada", False)),
                key=prefix + "regulada",
                disabled=not puede_compliance,
                help="Marcar si el partner posee resolución de la SFC u otro ente regulador.",
            )
            numero_licencia = st.text_input(
                "Número de Licencia",
                value=aliado.get("numero_licencia") or "",
                key=prefix + "licencia",
                disabled=not puede_compliance,
                placeholder="Ej: Res. SFC 0001-2023",
            )
            fecha_auditoria = st.date_input(
                "Fecha Última Auditoría",
                value=aliado.get("fecha_ultima_auditoria"),
                key=prefix + "auditoria",
                disabled=not puede_compliance,
            )
        with fiso2:
            _certs_actual  = list(aliado.get("certificaciones") or [])
            _certs_validas = [c for c in _certs_actual if c in CertificacionesISO.ALL]
            certificaciones = st.multiselect(
                "Certificaciones (ISO / PCI-DSS)",
                options=CertificacionesISO.ALL,
                default=_certs_validas,
                key=prefix + "certificaciones",
                disabled=not puede_compliance,
                help="ISO 27001, PCI-DSS, SOC 2, ISO 9001, ISO 20000",
            )
            partner_respaldo = st.text_input(
                "Partner de Respaldo (Plan de Continuidad)",
                value=aliado.get("partner_respaldo") or "",
                key=prefix + "respaldo",
                disabled=not puede_compliance,
                placeholder="Ej: Davivienda / Nequi",
            )
            pct_val = aliado.get("pct_concentracion")
            pct_concentracion = st.number_input(
                "% Concentración Operativa",
                min_value=0.0, max_value=100.0, step=0.5,
                value=float(pct_val) if pct_val is not None else 0.0,
                key=prefix + "pct_conc",
                disabled=not puede_compliance,
                help="Porcentaje de la operación total que depende de este partner.",
            )
    col_g, col_c, _ = st.columns([1, 1, 4])
    with col_g:
        if st.button("💾 Guardar", key=prefix + "guardar", type="primary"):
            # Detectar cambios en campos de criticidad/compliance para auditoría enriquecida
            _campos_compliance = {
                "es_entidad_regulada", "numero_licencia", "fecha_ultima_auditoria",
                "certificaciones", "partner_respaldo", "pct_concentracion",
            }
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
                sla_garantizado=sla_garantizado or None,
                # Cumplimiento ISO & Gobernanza
                es_entidad_regulada=es_regulada,
                numero_licencia=numero_licencia or None,
                fecha_ultima_auditoria=fecha_auditoria if fecha_auditoria else None,
                certificaciones=certificaciones,
                partner_respaldo=partner_respaldo or None,
                pct_concentracion=pct_concentracion if pct_concentracion > 0 else None,
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
    from config.settings import EstadosAliado, NivelesRiesgo, Roles, Jurisdicciones, NivelesCriticidad

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

        score_color = _SCORE_COLOR.get(riesgo, "#6b7280")
        score_pct   = min(100, int(puntaje))
        fecha_str   = str(fecha_rev) if fecha_rev else "—"

        # ── Pills / badges ────────────────────────────────────────────────────
        c_color          = _COLORES_CRITICIDAD.get(criticidad, "#6b7280")
        pip_pill         = _pill(estado_pip,  _COLORES_PIPELINE.get(estado_pip, "#6b7280"))
        criticidad_pill  = _pill(criticidad,  c_color)
        sarlaft_pill     = _pill(sarlaft,     _COLORES_SARLAFT.get(sarlaft, "#6b7280"))
        pep_badge        = _pill("⚠ PEP", "#f59e0b") if es_pep_fila else ""
        regulada_badge   = (
            _pill("🏛️ Entidad Regulada", "#5fe9d0") if es_regulada else ""
        )

        # Tipo de riel badge
        riel_icons = {"Dispersión": "📤", "Recaudo": "📥", "Crypto": "🔷", "Mixto": "🔄"}
        riel_badge = ""
        if tipo_riel and tipo_riel != "N/A":
            riel_icon = riel_icons.get(tipo_riel, "⚙️")
            riel_badge = (
                f'<span style="background:#1e274022;color:#93c5fd;border:1px solid #3b4f7a;'
                f'border-radius:9999px;padding:2px 9px;font-size:11px;font-weight:600;'
                f'margin-right:3px">{riel_icon} {tipo_riel}</span>'
            )

        # ── Capacidades ───────────────────────────────────────────────────────
        caps_html = (
            _capacidad_badge("🔷 Crypto",    bool(_idx(fila, "crypto_friendly")))
            + _capacidad_badge("🔞 Adult",   bool(_idx(fila, "adult_friendly")))
            + _capacidad_badge("💱 Monet.",  bool(_idx(fila, "permite_monetizacion")))
            + _capacidad_badge("📤 Dispers.", bool(_idx(fila, "permite_dispersion")))
        )
        jur_list       = _idx(fila, "jurisdicciones") or []
        jur_block_html = ""
        if jur_list:
            badges_jur = []
            for j in jur_list[:6]:
                is_risky = j in Jurisdicciones.ALTO_RIESGO
                jbg      = "#450a0a" if is_risky else "#1e2740"
                jcolor   = "#fca5a5" if is_risky else "#93c5fd"
                jborder  = "#ef444466" if is_risky else "#3b4f7a"
                badges_jur.append(
                    f'<span style="background:{jbg};color:{jcolor};border:1px solid '
                    f'{jborder};border-radius:5px;padding:2px 7px;font-size:10px;'
                    f'font-weight:500;white-space:nowrap">{j}</span>'
                )
            if len(jur_list) > 6:
                extra = len(jur_list) - 6
                badges_jur.append(
                    f'<span style="color:#6b7280;font-size:10px;padding:2px 4px">'
                    f'+{extra} más</span>'
                )
            jur_block_html = (
                '<div style="display:flex;gap:4px;flex-wrap:wrap;align-items:center">'
                + " ".join(badges_jur)
                + '</div>'
            )

        jur_section = (
            '<div style="margin-bottom:10px">'
            '<span style="color:#64748b;font-size:10px;text-transform:uppercase;'
            'letter-spacing:.5px;margin-right:6px">🌍 Jurisdicciones</span>'
            + jur_block_html
            + '</div>'
        ) if jur_list else ""

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
    from config.settings import TiposAliado, NivelesRiesgo, Roles, Jurisdicciones, TiposRiel, CertificacionesISO

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
            sla_garantizado = st.text_input(
                "SLA Garantizado",
                placeholder="Ej: 99.9% uptime / resolución < 4h",
            )

        # ── SECCIÓN 5: CUMPLIMIENTO ISO & GOBERNANZA ──────────────────────────
        st.markdown('<p class="section-title">🛡️ Cumplimiento ISO & Gobernanza</p>',
                    unsafe_allow_html=True)
        fi1, fi2 = st.columns(2)
        with fi1:
            es_regulada = st.checkbox(
                "🏛️ Entidad Regulada (posee licencia financiera)",
                help="Activa la etiqueta 'DDI - Entidad Regulada' en lugar de un riesgo connotativo.",
            )
            numero_licencia = st.text_input(
                "Número de Licencia",
                placeholder="Ej: Res. SFC 0001-2023",
            )
            fecha_auditoria = st.date_input(
                "Fecha Última Auditoría",
                value=None,
            )
        with fi2:
            certificaciones = st.multiselect(
                "Certificaciones",
                options=CertificacionesISO.ALL,
                help="ISO 27001, PCI-DSS, SOC 2, ISO 9001, ISO 20000",
            )
            partner_respaldo = st.text_input(
                "Partner de Respaldo",
                placeholder="Ej: Davivienda",
                help="Partner que asume la operación en caso de contingencia.",
            )
            pct_concentracion = st.number_input(
                "% Concentración Operativa",
                min_value=0.0, max_value=100.0, step=0.5, value=0.0,
                help="% de la operación total que depende de este partner.",
            )
        st.markdown('<p class="section-title">⚖️ Cumplimiento SARLAFT</p>',
                    unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        with cc1:
            riesgo = st.selectbox(
                "Nivel de Riesgo SARLAFT",
                NivelesRiesgo.ALL, index=1,
                help="El Nivel de Criticidad se calculará automáticamente al registrar.",
            )
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
                # Ficha Técnica del Riel
                tipo_riel=tipo_riel or None,
                sla_garantizado=sla_garantizado or None,
                # Cumplimiento ISO & Gobernanza
                es_entidad_regulada=es_regulada,
                numero_licencia=numero_licencia or None,
                fecha_ultima_auditoria=fecha_auditoria if fecha_auditoria else None,
                certificaciones=certificaciones,
                partner_respaldo=partner_respaldo or None,
                pct_concentracion=pct_concentracion if pct_concentracion > 0 else None,
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


# ── Monitor Operativo de Rieles ───────────────────────────────────────────────

def _tab_monitor_operativo(user: dict) -> None:
    """Tablero de control operativo: salud, capacidad y volumen de los rieles de pago."""
    import streamlit as st
    from db.database import get_session
    from db.repositories.partner_repo import PartnerRepository

    st.markdown(
        '<h3 style="color:#5fe9d0;margin-bottom:4px">📊 Monitor Operativo de Rieles</h3>'
        '<p style="color:#9ca3af;margin-top:0;margin-bottom:18px">'
        'Salud técnica · Capacidad financiera · Continuidad de negocio</p>',
        unsafe_allow_html=True,
    )

    # ── Carga de datos ────────────────────────────────────────────────────────
    with next(get_session()) as _s:
        _repo = PartnerRepository(_s)
        _filas = _repo.get_lista_enriquecida()

    total    = len(_filas)
    activos  = sum(1 for r in _filas if _idx(r, "estado_pipeline") == "Activo")
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
    # Volumen: derivado de pct_concentracion como proxy cuando no hay campo real
    _vol_refs = [_idx(r, "pct_concentracion") for r in _filas if _idx(r, "pct_concentracion")]
    _vol_display = f"{sum(float(v) for v in _vol_refs):.0f}%" if _vol_refs else "N/D"
    k2.markdown(
        f'<div style="{_KPI}">'
        f'<div style="font-size:1.9rem;font-weight:700;color:#3b82f6">{_vol_display}</div>'
        f'<div style="font-size:.78rem;color:#9ca3af;margin-top:4px">Concentración de Carga (acum.)</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    # Tasa de éxito proxy: 100% si ningún suspendido, decrementa 5% por cada uno
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

    # ── Alertas operativas ────────────────────────────────────────────────────
    _alertas = False
    for _r in suspendidos:
        st.error(
            f"🔴 Riel **{_idx(_r,'nombre_razon_social','—')}** en estado **Suspendido** — "
            "verificar continuidad operativa y activar riel de respaldo."
        )
        _alertas = True

    # Documento próximo a vencer (fecha_proxima_revision)
    import datetime as _dt
    _hoy = _dt.date.today()
    for _r in _filas:
        _fecha = _idx(_r, "fecha_proxima_revision")
        if _fecha:
            try:
                _d = _fecha.date() if hasattr(_fecha, "date") else _dt.date.fromisoformat(str(_fecha))
                _dias = (_d - _hoy).days
                if 0 <= _dias <= 30:
                    st.warning(
                        f"⚠️ **{_idx(_r,'nombre_razon_social','—')}** — Documentación KYB vence "
                        f"en **{_dias} días** ({_d.strftime('%d/%m/%Y')}). Renovar Contrato/DD."
                    )
                    _alertas = True
            except (ValueError, TypeError):
                pass

    if not _alertas:
        st.success("✅ Todos los rieles operativos dentro de parámetros normales.")

    st.markdown("<hr style='border-color:#293056;margin:20px 0'>", unsafe_allow_html=True)

    # ── Matriz de monitoreo de rieles ─────────────────────────────────────────
    st.markdown(
        '<p style="font-weight:600;color:#e2e8f0;margin-bottom:10px">'
        '🖥️ Matriz de Estado — Rieles en Tiempo Real</p>',
        unsafe_allow_html=True,
    )

    # Mapeo salud del canal: Suspendido→Degradado, Onboarding→Mantenimiento, resto→Online
    def _salud_canal(estado: str) -> tuple[str, str]:
        if estado == "Suspendido":
            return "🔴 Degradado", "#ef4444"
        if estado in ("Onboarding", "En Calificación"):
            return "🟡 Mantenimiento", "#f59e0b"
        if estado == "Activo":
            return "🟢 Online", "#22c55e"
        return "⚪ Inactivo", "#6b7280"

    # Latencia proxy desde tipo_riel / sla_garantizado
    def _latencia_display(r: dict) -> str:
        sla = _idx(r, "sla_garantizado") or ""
        tipo = (_idx(r, "tipo_riel") or "").lower()
        if "t+0" in sla.lower() or "inmediato" in sla.lower():
            return "T+0 (~150ms)"
        if "t+1" in sla.lower():
            return "T+1 (24h)"
        if "instant" in tipo or "real" in tipo:
            return "T+0 (~200ms)"
        return sla if sla else "—"

    # Volumen proxy desde pct_concentracion
    def _vol_canal(r: dict) -> str:
        pct = _idx(r, "pct_concentracion")
        if pct:
            try:
                return f"{float(pct):.1f}% del total"
            except (ValueError, TypeError):
                pass
        return "—"

    # Construir tabla HTML
    _COL_HDR = "background:#111827;color:#9ca3af;font-size:.72rem;padding:8px 12px;text-align:left;"
    _COL_CEL = "padding:10px 12px;font-size:.82rem;border-bottom:1px solid #1f2937;"
    _ROW_BG_ODD  = "background:#0f172a;"
    _ROW_BG_EVEN = "background:#111827;"

    _html_rows = ""
    for _i, _r in enumerate(_filas):
        _nombre   = _idx(_r, "nombre_razon_social") or "—"
        _tipo     = _idx(_r, "tipo_aliado") or _idx(_r, "tipo_riel") or "—"
        _estado   = _idx(_r, "estado_pipeline") or "—"
        _salud_t, _salud_c = _salud_canal(_estado)
        _lat      = _latencia_display(_r)
        _vol      = _vol_canal(_r)
        _row_bg   = _ROW_BG_ODD if _i % 2 == 0 else _ROW_BG_EVEN
        _estado_color = _ESTADO_COLORES_B2B.get(_estado, "#9ca3af")
        _html_rows += (
            f'<tr style="{_row_bg}">'
            f'<td style="{_COL_CEL}color:#e2e8f0;font-weight:600">{_nombre}</td>'
            f'<td style="{_COL_CEL}color:#9ca3af">{_tipo}</td>'
            f'<td style="{_COL_CEL}"><span style="background:{_estado_color}22;color:{_estado_color};'
            f'border-radius:4px;padding:2px 8px;font-size:.75rem;font-weight:600">{_estado}</span></td>'
            f'<td style="{_COL_CEL}color:{_salud_c};font-weight:600">{_salud_t}</td>'
            f'<td style="{_COL_CEL}color:#9ca3af">{_lat}</td>'
            f'<td style="{_COL_CEL}color:#60a5fa">{_vol}</td>'
            f'</tr>'
        )

    if not _html_rows:
        _html_rows = (
            '<tr><td colspan="6" style="padding:20px;text-align:center;color:#6b7280">'
            'Sin partners registrados.</td></tr>'
        )

    st.markdown(
        f'<div style="overflow-x:auto;border-radius:10px;border:1px solid #293056">'
        f'<table style="width:100%;border-collapse:collapse">'
        f'<thead><tr>'
        f'<th style="{_COL_HDR}">Aliado</th>'
        f'<th style="{_COL_HDR}">Tipo de Riel</th>'
        f'<th style="{_COL_HDR}">Estado Operativo</th>'
        f'<th style="{_COL_HDR}">Salud del Canal</th>'
        f'<th style="{_COL_HDR}">Latencia / SLA</th>'
        f'<th style="{_COL_HDR}">Volumen Canalizado</th>'
        f'</tr></thead>'
        f'<tbody>{_html_rows}</tbody>'
        f'</table></div>',
        unsafe_allow_html=True,
    )

    st.markdown("<div style='margin-bottom:24px'></div>", unsafe_allow_html=True)

    # ── Gráfico: Distribución de carga por riel ───────────────────────────────
    st.markdown(
        '<p style="font-weight:600;color:#e2e8f0;margin-bottom:10px">'
        '📈 Distribución de Carga por Riel</p>',
        unsafe_allow_html=True,
    )

    # Construir datos para el gráfico
    _chart_data: dict[str, float] = {}
    for _r in _filas:
        _nombre = _idx(_r, "nombre_razon_social") or "Sin nombre"
        _pct = _idx(_r, "pct_concentracion")
        try:
            _chart_data[_nombre] = float(_pct) if _pct else 0.0
        except (ValueError, TypeError):
            _chart_data[_nombre] = 0.0

    _nombres_activos = [_idx(r, "nombre_razon_social") or "—" for r in _filas
                        if _idx(r, "estado_pipeline") == "Activo"]

    _has_real_data = any(v > 0 for v in _chart_data.values())

    if _has_real_data:
        try:
            import pandas as _pd
            _df_chart = _pd.DataFrame(
                {"Aliado": list(_chart_data.keys()), "% Carga": list(_chart_data.values())}
            ).set_index("Aliado")
            st.bar_chart(_df_chart, color="#3b82f6")
        except Exception:
            for _nombre, _pct_v in _chart_data.items():
                if _pct_v > 0:
                    st.markdown(
                        f'<div style="margin:4px 0;display:flex;align-items:center;gap:8px">'
                        f'<span style="color:#e2e8f0;min-width:180px;font-size:.82rem">{_nombre}</span>'
                        f'<div style="flex:1;background:#1f2937;border-radius:4px;height:16px">'
                        f'<div style="width:{min(_pct_v,100):.0f}%;background:#3b82f6;'
                        f'border-radius:4px;height:16px"></div></div>'
                        f'<span style="color:#60a5fa;font-size:.78rem;min-width:44px">'
                        f'{_pct_v:.1f}%</span></div>',
                        unsafe_allow_html=True,
                    )
    else:
        # Sin pct_concentracion: distribución equitativa entre activos
        if _nombres_activos:
            _eq_pct = round(100.0 / len(_nombres_activos), 1)
            for _n in _nombres_activos:
                st.markdown(
                    f'<div style="margin:4px 0;display:flex;align-items:center;gap:8px">'
                    f'<span style="color:#e2e8f0;min-width:180px;font-size:.82rem">{_n}</span>'
                    f'<div style="flex:1;background:#1f2937;border-radius:4px;height:16px">'
                    f'<div style="width:{_eq_pct:.0f}%;background:#3b82f6;'
                    f'border-radius:4px;height:16px"></div></div>'
                    f'<span style="color:#60a5fa;font-size:.78rem;min-width:44px">'
                    f'{_eq_pct}%</span></div>',
                    unsafe_allow_html=True,
                )
            st.caption("⚠️ Sin datos de concentración reales — distribución equitativa estimada entre rieles activos.")
        else:
            st.info("Sin rieles activos para graficar.")


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
