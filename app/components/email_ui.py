"""
app/components/email_ui.py
Módulo 📧 Bandeja de Cumplimiento — AdamoServices Partner Manager.

Centraliza los correos de los 3 buzones corporativos como casos
gestionables con estado, prioridad, notas y trazabilidad completa.

Acceso: admin · compliance
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)

# ── Paleta ────────────────────────────────────────────────────
_COLOR_EMPRESA: dict[str, str] = {
    "Holdings BPO":   "#7c3aed",
    "Adamo Services": "#0ea5e9",
    "Paycop":         "#10b981",
}

# (bg, color, border)
_ESTADO_STYLE: dict[str, tuple[str, str, str]] = {
    "Nuevo":      ("rgba(59,130,246,0.12)",  "#60a5fa", "rgba(59,130,246,0.30)"),
    "En gestión": ("rgba(245,158,11,0.12)",  "#fbbf24", "rgba(245,158,11,0.30)"),
    "Resuelto":   ("rgba(34,197,94,0.10)",   "#4ade80", "rgba(34,197,94,0.25)"),
    "Escalado":   ("rgba(239,68,68,0.12)",   "#f87171", "rgba(239,68,68,0.30)"),
}

_PRIORIDAD_STYLE: dict[str, tuple[str, str, str]] = {
    "Alta":   ("rgba(239,68,68,0.12)",   "#f87171", "rgba(239,68,68,0.30)"),
    "Normal": ("rgba(107,114,128,0.12)", "#9ca3af", "rgba(107,114,128,0.25)"),
    "Baja":   ("rgba(34,197,94,0.10)",   "#4ade80", "rgba(34,197,94,0.25)"),
}

_EMPRESAS    = ["Holdings BPO", "Adamo Services", "Paycop"]
_ESTADOS     = ["Nuevo", "En gestión", "Resuelto", "Escalado"]
_PRIORIDADES = ["Alta", "Normal", "Baja"]


# ── Helpers ───────────────────────────────────────────────────

def _tiempo_relativo(dt: Optional[datetime]) -> str:
    if dt is None:
        return ""
    ahora = datetime.now(tz=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    seg = max(0, int((ahora - dt).total_seconds()))
    if seg < 60:
        return "hace un momento"
    min_ = seg // 60
    if min_ < 60:
        return f"hace {min_} min"
    h = min_ // 60
    if h < 24:
        return f"hace {h}h"
    return f"hace {h // 24}d"


def _badge(text: str, bg: str, color: str, border: str) -> str:
    return (
        f"<span style='background:{bg};color:{color};border:1px solid {border};"
        f"border-radius:99px;font-size:0.62rem;font-weight:700;"
        f"padding:2px 9px;font-family:JetBrains Mono,monospace;'>{text}</span>"
    )


def _caso_card_html(caso: dict) -> str:
    """HTML completo de una tarjeta de caso (sin botón de acción)."""
    estado    = caso.get("estado", "Nuevo")
    prioridad = caso.get("prioridad", "Normal")
    empresa   = caso.get("empresa", "")
    asunto    = caso.get("asunto", "") or ""
    remitente = caso.get("remitente", "") or ""
    buzon     = caso.get("buzon", "") or ""
    fecha     = caso.get("fecha_recepcion")

    e_bg, e_color, e_border = _ESTADO_STYLE.get(estado, _ESTADO_STYLE["Nuevo"])
    p_bg, p_color, p_border = _PRIORIDAD_STYLE.get(prioridad, _PRIORIDAD_STYLE["Normal"])
    ec = _COLOR_EMPRESA.get(empresa, "#6b7280")
    tiempo = _tiempo_relativo(fecha)

    # Pre-compute badges (sin lógica dentro del f-string)
    b_empresa   = _badge(empresa,   f"{ec}26",   ec,      f"{ec}60")
    b_estado    = _badge(estado,    e_bg,        e_color, e_border)
    b_prioridad = _badge(prioridad, p_bg,        p_color, p_border)

    # Escape caracteres HTML en texto del usuario
    asunto_h    = asunto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    remitente_h = remitente.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    return (
        f"<div style='background:#12141c;border:1px solid #1e2130;"
        f"border-radius:12px;padding:14px 18px;margin-bottom:4px;'>"
        f"<div style='display:flex;align-items:center;gap:6px;"
        f"flex-wrap:wrap;margin-bottom:8px;'>"
        f"{b_empresa} {b_estado} {b_prioridad}"
        f"<span style='color:#6b7280;font-size:0.70rem;margin-left:auto;'>{tiempo}</span>"
        f"</div>"
        f"<div style='font-weight:600;color:#f0f1f5;font-size:0.88rem;"
        f"margin-bottom:4px;'>{asunto_h}</div>"
        f"<div style='color:#9ca3af;font-size:0.75rem;'>"
        f"{remitente_h}"
        f"<span style='color:#6b7280;'> · {buzon}</span>"
        f"</div>"
        f"</div>"
    )


def _kpi_card_html(label: str, value: int, color: str) -> str:
    return (
        f"<div style='background:#12141c;border:1px solid #1e2130;"
        f"border-radius:12px;padding:14px 18px;text-align:center;'>"
        f"<div style='font-size:0.60rem;font-weight:700;letter-spacing:0.10em;"
        f"text-transform:uppercase;color:#6b7280;margin-bottom:6px;'>{label}</div>"
        f"<div style='font-size:1.8rem;font-weight:700;color:{color};"
        f"font-variant-numeric:tabular-nums;line-height:1;'>{value}</div>"
        f"</div>"
    )


# ── Panel inline de gestión ───────────────────────────────────

def _panel_caso(caso: dict, user: dict) -> None:
    """Panel de detalle y gestión de un caso — se renderiza debajo de la tarjeta."""
    caso_id  = caso["id"]
    empresa  = caso.get("empresa", "")
    asunto   = caso.get("asunto", "") or ""
    remitente = caso.get("remitente", "") or ""
    buzon    = caso.get("buzon", "") or ""
    cuerpo   = caso.get("cuerpo") or "(Sin cuerpo)"
    fecha    = caso.get("fecha_recepcion")

    estado_actual    = caso.get("estado", "Nuevo")
    prioridad_actual = caso.get("prioridad", "Normal")
    notas_actuales   = caso.get("notas_internas") or ""
    atendido_actual  = caso.get("atendido_por") or ""

    ec = _COLOR_EMPRESA.get(empresa, "#6b7280")
    fecha_str = fecha.strftime("%d %b %Y %H:%M") if fecha else "—"
    asunto_h    = asunto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    remitente_h = remitente.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    st.markdown(
        f"<div style='background:#0d0e14;border:1px solid #293056;"
        f"border-radius:12px;padding:14px 18px;margin-bottom:10px;'>"
        f"<div style='font-size:0.60rem;font-weight:700;text-transform:uppercase;"
        f"letter-spacing:0.10em;color:#6b7280;margin-bottom:4px;'>Caso #{caso_id}</div>"
        f"<div style='color:{ec};font-size:0.75rem;font-weight:600;"
        f"margin-bottom:4px;'>{empresa} · {buzon}</div>"
        f"<div style='color:#f0f1f5;font-size:0.88rem;font-weight:600;"
        f"margin-bottom:4px;'>{asunto_h}</div>"
        f"<div style='color:#9ca3af;font-size:0.75rem;'>{remitente_h} · {fecha_str}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    with st.expander("📄 Ver cuerpo del correo"):
        st.text(cuerpo)

    with st.form(key=f"form_ec_{caso_id}"):
        col1, col2 = st.columns(2)
        with col1:
            idx_e = _ESTADOS.index(estado_actual) if estado_actual in _ESTADOS else 0
            nuevo_estado = st.selectbox("Estado", options=_ESTADOS, index=idx_e)
        with col2:
            idx_p = _PRIORIDADES.index(prioridad_actual) if prioridad_actual in _PRIORIDADES else 1
            nueva_prioridad = st.selectbox("Prioridad", options=_PRIORIDADES, index=idx_p)

        nuevas_notas = st.text_area(
            "Notas internas",
            value=notas_actuales,
            height=100,
        )
        atendido_default = atendido_actual or user.get("username", "")
        nuevo_atendido = st.text_input("Atendido por", value=atendido_default)

        if st.form_submit_button("💾 Guardar cambios", type="primary", use_container_width=True):
            from db.database import get_session
            from db.repositories.email_repo import EmailRepository
            from db.models import EmailCasoUpdate

            upd = EmailCasoUpdate(
                estado          = nuevo_estado,
                prioridad       = nueva_prioridad,
                notas_internas  = nuevas_notas or None,
                atendido_por    = nuevo_atendido or None,
            )
            try:
                with next(get_session()) as session:
                    EmailRepository(session).actualizar(
                        caso_id, upd, user.get("username", "sistema")
                    )
                st.success(f"✅ Caso #{caso_id} actualizado.")
                st.session_state.pop(f"_ec_panel_{caso_id}", None)
                st.rerun()
            except Exception as exc:
                st.error(f"Error al guardar: {exc}")


# ── Tab Bandeja ───────────────────────────────────────────────

def _tab_bandeja(user: dict) -> None:
    from db.database import get_session
    from db.repositories.email_repo import EmailRepository

    # Cargar stats
    try:
        with next(get_session()) as session:
            stats = EmailRepository(session).get_stats()
    except Exception as exc:
        st.warning(f"No se puede acceder a la tabla email_casos: {exc}")
        st.info("Aplica la migración 026_email_casos.sql con: `python db/sync_db.py --only 026`")
        return

    # KPI cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            _kpi_card_html("Total", stats.get("total", 0), "#f0f1f5"),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            _kpi_card_html("Nuevos", stats.get("nuevos", 0), "#60a5fa"),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            _kpi_card_html("En Gestión", stats.get("en_gestion", 0), "#fbbf24"),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            _kpi_card_html("Escalados", stats.get("escalados", 0), "#f87171"),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin:14px 0;'></div>", unsafe_allow_html=True)

    # Filtros
    fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 3])
    with fc1:
        f_empresa = st.selectbox("Empresa", ["Todas"] + _EMPRESAS, key="ec_f_empresa")
    with fc2:
        f_estado = st.selectbox("Estado", ["Todos"] + _ESTADOS, key="ec_f_estado")
    with fc3:
        f_prio = st.selectbox("Prioridad", ["Todas"] + _PRIORIDADES, key="ec_f_prio")
    with fc4:
        f_search = st.text_input(
            "🔍 Buscar", placeholder="Asunto o remitente...", key="ec_f_search"
        )

    empresa_q   = f_empresa if f_empresa != "Todas" else None
    estado_q    = f_estado  if f_estado  != "Todos"  else None
    prioridad_q = f_prio    if f_prio    != "Todas"  else None
    search_q    = f_search  if f_search  else None

    # Cargar casos
    try:
        with next(get_session()) as session:
            casos = EmailRepository(session).get_lista(
                empresa=empresa_q,
                estado=estado_q,
                prioridad=prioridad_q,
                search=search_q,
            )
    except Exception as exc:
        st.error(f"Error al cargar casos: {exc}")
        return

    if not casos:
        st.info("No hay casos que coincidan con los filtros.")
        return

    st.markdown(
        f"<p style='color:#9ca3af;font-size:0.78rem;margin-bottom:8px;'>"
        f"{len(casos)} caso(s)</p>",
        unsafe_allow_html=True,
    )

    for caso in casos:
        caso_id   = caso["id"]
        panel_key = f"_ec_panel_{caso_id}"

        st.markdown(_caso_card_html(caso), unsafe_allow_html=True)

        btn_lbl = "🔼 Cerrar" if st.session_state.get(panel_key) else "📋 Gestionar"
        if st.button(btn_lbl, key=f"ec_btn_{caso_id}"):
            st.session_state[panel_key] = not st.session_state.get(panel_key, False)
            st.rerun()

        if st.session_state.get(panel_key):
            _panel_caso(caso, user)
            st.markdown(
                "<hr style='border:none;border-top:1px solid #1e2130;margin:16px 0 20px;'>",
                unsafe_allow_html=True,
            )


# ── Tab Estadísticas ─────────────────────────────────────────

def _tab_estadisticas(user: dict) -> None:
    import plotly.graph_objects as go
    from db.database import get_session
    from db.repositories.email_repo import EmailRepository

    try:
        with next(get_session()) as session:
            repo        = EmailRepository(session)
            stats       = repo.get_stats()
            por_empresa = repo.get_casos_por_empresa()
    except Exception as exc:
        st.warning(f"Sin datos de estadísticas: {exc}")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Distribución por empresa**")
        empresas = list(por_empresa.keys())
        totales  = list(por_empresa.values())
        colores  = [_COLOR_EMPRESA.get(e, "#6b7280") for e in empresas]

        fig_empresa = go.Figure(go.Pie(
            labels=empresas,
            values=totales,
            hole=0.5,
            marker_colors=colores,
            textinfo="label+percent",
            textfont_size=11,
        ))
        fig_empresa.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#9ca3af",
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
            height=280,
        )
        st.plotly_chart(fig_empresa, use_container_width=True)

    with col2:
        st.markdown("**Distribución por estado**")
        estado_vals = {
            "Nuevo":      stats.get("nuevos", 0),
            "En gestión": stats.get("en_gestion", 0),
            "Resuelto":   stats.get("resueltos", 0),
            "Escalado":   stats.get("escalados", 0),
        }
        e_labels = list(estado_vals.keys())
        e_values = list(estado_vals.values())
        e_colors = [_ESTADO_STYLE.get(lbl, ("", "#6b7280", ""))[1] for lbl in e_labels]

        fig_estado = go.Figure(go.Bar(
            x=e_labels,
            y=e_values,
            marker_color=e_colors,
            text=e_values,
            textposition="outside",
        ))
        fig_estado.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#9ca3af",
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
            height=280,
            yaxis=dict(gridcolor="#1e2130"),
        )
        st.plotly_chart(fig_estado, use_container_width=True)

    # Tabla resumen por empresa
    st.markdown("**Resumen por empresa**")
    try:
        with next(get_session()) as session:
            repo = EmailRepository(session)
            for empresa in _EMPRESAS:
                casos_e = repo.get_lista(empresa=empresa)
                if not casos_e:
                    continue
                total_e     = len(casos_e)
                nuevos_e    = sum(1 for c in casos_e if c["estado"] == "Nuevo")
                gestion_e   = sum(1 for c in casos_e if c["estado"] == "En gestión")
                resueltos_e = sum(1 for c in casos_e if c["estado"] == "Resuelto")
                escalados_e = sum(1 for c in casos_e if c["estado"] == "Escalado")
                ec          = _COLOR_EMPRESA.get(empresa, "#6b7280")

                st.markdown(
                    f"<div style='background:#12141c;border:1px solid #1e2130;"
                    f"border-left:3px solid {ec};border-radius:8px;"
                    f"padding:10px 14px;margin-bottom:6px;display:flex;"
                    f"gap:20px;align-items:center;flex-wrap:wrap;'>"
                    f"<span style='color:{ec};font-weight:700;font-size:0.82rem;"
                    f"min-width:130px;'>{empresa}</span>"
                    f"<span style='color:#9ca3af;font-size:0.78rem;'>"
                    f"Total <b style='color:#f0f1f5;'>{total_e}</b></span>"
                    f"<span style='color:#9ca3af;font-size:0.78rem;'>"
                    f"Nuevos <b style='color:#60a5fa;'>{nuevos_e}</b></span>"
                    f"<span style='color:#9ca3af;font-size:0.78rem;'>"
                    f"En gestión <b style='color:#fbbf24;'>{gestion_e}</b></span>"
                    f"<span style='color:#9ca3af;font-size:0.78rem;'>"
                    f"Resueltos <b style='color:#4ade80;'>{resueltos_e}</b></span>"
                    f"<span style='color:#9ca3af;font-size:0.78rem;'>"
                    f"Escalados <b style='color:#f87171;'>{escalados_e}</b></span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
    except Exception as exc:
        st.error(f"Error al cargar resumen: {exc}")


# ── Entrada principal ─────────────────────────────────────────

def page_bandeja_cumplimiento(user: dict) -> None:
    st.markdown("## 📧 Bandeja de Cumplimiento")
    st.markdown(
        "<p style='color:#9ca3af;font-size:0.85rem;margin-top:-8px;'>"
        "Gestión centralizada de correos compliance · "
        "Holdings BPO · Adamo Services · Paycop"
        "</p>",
        unsafe_allow_html=True,
    )

    tab_bandeja, tab_stats = st.tabs(["📧 Bandeja", "📊 Estadísticas"])

    with tab_bandeja:
        _tab_bandeja(user)

    with tab_stats:
        _tab_estadisticas(user)
