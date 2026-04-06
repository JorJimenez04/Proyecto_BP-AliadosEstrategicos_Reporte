"""
app/components/dashboard_ui.py
Dashboard principal — AdamoServices Partner Manager.
Incluye métricas globales, comparativa de salud corporativa por empresa
del grupo (HoldingsBPO / Adamo / Paycop) y alertas SARLAFT.
"""

import streamlit as st
from db.database import get_session
from db.repositories.partner_repo import PartnerRepository
from app.components.alerts import render_centro_notificaciones


def _badge(text: str, color: str) -> str:
    return f"<span class='badge' style='background:{color}20; color:{color};'>{text}</span>"


def _kpi(label: str, value, delta: str | None = None, color: str = "#5fe9d0"):
    st.markdown(
        f"""
        <div style='background:#1f2937;border-radius:10px;padding:16px 20px;border-left:3px solid {color};'>
            <div style='color:#9ca3af;font-size:0.78rem;text-transform:uppercase;letter-spacing:1px;'>{label}</div>
            <div style='color:#f9fafb;font-size:2rem;font-weight:800;margin:4px 0;'>{value}</div>
            {f"<div style='color:{color};font-size:0.8rem;'>{delta}</div>" if delta else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _empresa_card(nombre: str, datos: dict, color: str):
    activos    = datos["activos"]
    inactivos  = datos["inactivos"]
    sin_rel    = datos["sin_relacion"]
    pct        = datos["pct_activos"]
    total_rel  = activos + inactivos

    st.markdown(
        f"""
        <div style='background:#1f2937;border-radius:10px;padding:18px;border-top:3px solid {color};'>
            <div style='color:{color};font-weight:700;font-size:0.9rem;text-transform:uppercase;
                        letter-spacing:1px;margin-bottom:12px;'>{nombre}</div>
            <div style='display:flex;gap:16px;flex-wrap:wrap;'>
                <div style='text-align:center;'>
                    <div style='color:#5fe9d0;font-size:1.5rem;font-weight:800;'>{activos}</div>
                    <div style='color:#9ca3af;font-size:0.7rem;'>Activos</div>
                </div>
                <div style='text-align:center;'>
                    <div style='color:#f59e0b;font-size:1.5rem;font-weight:800;'>{inactivos}</div>
                    <div style='color:#9ca3af;font-size:0.7rem;'>Inactivos</div>
                </div>
                <div style='text-align:center;'>
                    <div style='color:#6b7280;font-size:1.5rem;font-weight:800;'>{sin_rel}</div>
                    <div style='color:#9ca3af;font-size:0.7rem;'>Sin relación</div>
                </div>
            </div>
            <div style='margin-top:12px;background:#111827;border-radius:6px;height:8px;overflow:hidden;'>
                <div style='width:{pct}%;height:100%;background:{color};border-radius:6px;'></div>
            </div>
            <div style='color:#9ca3af;font-size:0.72rem;margin-top:4px;'>
                {pct}% activos de {total_rel} con relación
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_dashboard(user: dict):
    st.markdown("<h1>📊 Dashboard Ejecutivo — AdamoPay</h1>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#293056;'>", unsafe_allow_html=True)

    with next(get_session()) as session:
        repo   = PartnerRepository(session)

        stats_pipeline = repo.get_stats_pipeline()
        stats_riesgo   = repo.get_stats_riesgo()
        salud_grupo    = repo.get_salud_grupo()

        total          = sum(stats_pipeline.values())
        activos        = stats_pipeline.get("Activo", 0)
        alto_riesgo    = stats_riesgo.get("Alto", 0) + stats_riesgo.get("Muy Alto", 0)
        onboarding     = stats_pipeline.get("Onboarding", 0)

        # ── KPIs Globales ─────────────────────────────────────────────────────
        st.markdown('<p class="section-title">Portafolio Global</p>', unsafe_allow_html=True)
        k1, k2, k3, k4 = st.columns(4)
        with k1: _kpi("Total Partners", total, color="#5fe9d0")
        with k2: _kpi("Partners Activos", activos,
                       f"{round(activos/total*100)}% del portafolio" if total else None,
                       color="#5fe9d0")
        with k3: _kpi("Alto / Muy Alto Riesgo", alto_riesgo,
                       "⚠ Requieren atención" if alto_riesgo else "✓ Bajo control",
                       color="#ef4444" if alto_riesgo else "#5fe9d0")
        with k4: _kpi("En Onboarding", onboarding, color="#7839ee")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Salud de Relación por Empresa del Grupo ───────────────────────────
        st.markdown('<p class="section-title">🏢 Salud de Relación Corporativa</p>', unsafe_allow_html=True)
        eg1, eg2, eg3 = st.columns(3)
        with eg1: _empresa_card("HoldingsBPO", salud_grupo["hbpocorp"], "#5fe9d0")
        with eg2: _empresa_card("Adamo",        salud_grupo["adamo"],    "#7839ee")
        with eg3: _empresa_card("Paycop",       salud_grupo["paycop"],   "#f59e0b")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Mix de Riesgo ─────────────────────────────────────────────────────
        st.markdown('<p class="section-title">⚖ Distribución de Riesgo SARLAFT</p>', unsafe_allow_html=True)
        _COLORES_RIESGO = {"Bajo": "#5fe9d0", "Medio": "#f59e0b",
                           "Alto": "#fb923c", "Muy Alto": "#ef4444"}
        cols_r = st.columns(4)
        for i, (nivel, color) in enumerate(_COLORES_RIESGO.items()):
            with cols_r[i]:
                _kpi(nivel, stats_riesgo.get(nivel, 0), color=color)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Alertas SARLAFT ───────────────────────────────────────────────────
        st.markdown('<p class="section-title">🔔 Centro de Alertas de Compliance</p>', unsafe_allow_html=True)
        render_centro_notificaciones(repo, session, user)
