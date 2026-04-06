"""
app/components/dashboard_ui.py
Dashboard Ejecutivo — AdamoPay / AdamoServices Partner Manager.

Disenado para Compliance Officers: herramienta de decision de primera mano
con vision corporativa, monitor de riesgo operativo y analisis de volumen.

ARQUITECTURA: Todos los imports de DB estan DENTRO de page_dashboard()
(patron lazy) para evitar AttributeError si la DB no esta disponible al
iniciar el modulo.
"""

import streamlit as st

# ------------------------------------------------------------------
# Paleta corporativa AdamoServices
# ------------------------------------------------------------------
_C_CYAN   = "#5fe9d0"
_C_VIOLET = "#7839ee"
_C_RED    = "#ef4444"
_C_ORANGE = "#fb923c"
_C_AMBER  = "#f59e0b"
_C_GRAY   = "#9ca3af"
_C_BG     = "#1f2937"
_C_BG2    = "#111827"
_C_BORDER = "#293056"

_COLORES_RIESGO: dict[str, str] = {
    "Bajo":     _C_CYAN,
    "Medio":    _C_AMBER,
    "Alto":     _C_ORANGE,
    "Muy Alto": _C_RED,
}

# ------------------------------------------------------------------
# Helpers de UI puros (sin imports de DB)
# ------------------------------------------------------------------

def _section(title: str) -> None:
    st.markdown(
        f"<p class='section-title'>{title}</p>",
        unsafe_allow_html=True,
    )


def _spacer() -> None:
    st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)


def _kpi(label: str, value: object, delta: str = "", color: str = _C_CYAN) -> None:
    delta_html = (
        f"<div style='color:{color};font-size:0.78rem;margin-top:3px;'>{delta}</div>"
        if delta else ""
    )
    st.markdown(
        f"""
        <div style='background:{_C_BG};border-radius:10px;padding:16px 20px;
                    border-left:3px solid {color};margin-bottom:4px;'>
            <div style='color:{_C_GRAY};font-size:0.72rem;text-transform:uppercase;
                        letter-spacing:1.1px;font-weight:600;'>{label}</div>
            <div style='color:#f9fafb;font-size:2rem;font-weight:800;margin:5px 0 2px;'>
                {value}
            </div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _empresa_card(nombre: str, datos: dict, color: str) -> None:
    activos   = datos.get("activos", 0)
    inactivos = datos.get("inactivos", 0)
    sin_rel   = datos.get("sin_relacion", 0)
    pct       = datos.get("pct_activos", 0.0)
    total_rel = activos + inactivos

    if pct >= 70:
        badge_color, badge_label = _C_CYAN, "Saludable"
    elif pct >= 40:
        badge_color, badge_label = _C_AMBER, "Alerta"
    else:
        badge_color, badge_label = _C_RED, "Critico"

    st.markdown(
        f"<div style='background:{_C_BG};border-radius:12px;padding:20px;"
        f"border:1px solid {_C_BORDER};border-top:3px solid {color};'>"
        f"<div style='display:flex;justify-content:space-between;"
        f"align-items:flex-start;margin-bottom:16px;'>"
        f"<span style='color:{color};font-weight:700;font-size:0.95rem;"
        f"text-transform:uppercase;letter-spacing:1px;'>{nombre}</span>"
        f"<span style='background:{badge_color}22;color:{badge_color};"
        f"font-size:0.68rem;font-weight:700;padding:3px 10px;"
        f"border-radius:20px;border:1px solid {badge_color}44;"
        f"white-space:nowrap;'>{pct}% &middot; {badge_label}</span>"
        f"</div>"
        f"<div style='display:flex;gap:24px;margin-bottom:14px;'>"
        f"<div><div style='color:{_C_CYAN};font-size:2rem;font-weight:800;"
        f"line-height:1;'>{activos}</div>"
        f"<div style='color:{_C_GRAY};font-size:0.68rem;margin-top:2px;'>ACTIVOS</div></div>"
        f"<div><div style='color:{_C_RED};font-size:2rem;font-weight:800;"
        f"line-height:1;'>{inactivos}</div>"
        f"<div style='color:{_C_GRAY};font-size:0.68rem;margin-top:2px;'>INACTIVOS</div></div>"
        f"<div><div style='color:#4b5563;font-size:2rem;font-weight:800;"
        f"line-height:1;'>{sin_rel}</div>"
        f"<div style='color:{_C_GRAY};font-size:0.68rem;margin-top:2px;'>SIN RELACION</div></div>"
        f"</div>"
        f"<div style='background:{_C_BG2};border-radius:6px;height:6px;overflow:hidden;'>"
        f"<div style='width:{pct}%;height:100%;background:{color};border-radius:6px;'></div>"
        f"</div>"
        f"<div style='color:#4b5563;font-size:0.7rem;margin-top:5px;'>"
        f"{total_rel} partner(s) con relacion activa o inactiva</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _termometro_row(label: str, valor: int, total: int, color: str) -> None:
    pct = round(valor / total * 100) if total else 0
    st.markdown(
        f"""
        <div style='display:flex;align-items:center;gap:12px;margin-bottom:10px;'>
            <div style='width:110px;color:{_C_GRAY};font-size:0.78rem;
                        text-align:right;flex-shrink:0;'>{label}</div>
            <div style='flex:1;background:{_C_BG2};border-radius:6px;
                        height:10px;overflow:hidden;'>
                <div style='width:{pct}%;height:100%;background:{color};
                            border-radius:6px;'></div>
            </div>
            <div style='width:52px;text-align:right;flex-shrink:0;'>
                <span style='color:{color};font-weight:700;font-size:0.9rem;'>
                    {valor}</span>
                <span style='color:#4b5563;font-size:0.72rem;'> ({pct}%)</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def page_dashboard(user: dict) -> None:
    """
    Dashboard ejecutivo de AdamoPay para Compliance Officers.

    Secciones:
      1. KPIs globales
      2. Salud de Relacion Corporativa (HoldingsBPO / Adamo / Paycop)
      3. Monitor de Riesgo Operativo
         3a. Capacidades de alto riesgo (Plotly donut)
         3b. Termometro SARLAFT
      4. Analisis de Volumen y Concentracion
      5. Centro de Alertas de Compliance
    """
    # -- Lazy imports --------------------------------------------------
    from db.database import get_session
    from db.repositories.partner_repo import PartnerRepository
    from app.components.alerts import render_centro_notificaciones
    import plotly.graph_objects as go

    st.markdown(
        "<h1 style='margin-bottom:4px;'>Dashboard Ejecutivo &mdash; AdamoPay</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<hr style='border-color:{_C_BORDER};margin-bottom:24px;'>",
        unsafe_allow_html=True,
    )

    try:
        with next(get_session()) as session:
            repo = PartnerRepository(session)

            stats_pipeline  = repo.get_stats_pipeline()
            stats_riesgo    = repo.get_stats_riesgo()
            salud_grupo     = repo.get_salud_grupo()
            stats_cap       = repo.get_stats_capacidades()
            termometro      = repo.get_termometro_sarlaft()
            volumenes       = repo.get_resumen_volumen()

    except Exception as exc:
        st.error(f"Error al cargar el Dashboard: {exc}")
        st.caption(
            "Verifica que la base de datos este disponible "
            "y que la migracion 003 se haya aplicado."
        )
        return

    total      = sum(stats_pipeline.values())
    activos    = stats_pipeline.get("Activo", 0)
    alto_r     = stats_riesgo.get("Alto", 0) + stats_riesgo.get("Muy Alto", 0)
    onboarding = stats_pipeline.get("Onboarding", 0)

    # ==================================================================
    # SECCION 1 — KPIs Globales
    # ==================================================================
    _section("Portafolio Global")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        _kpi("Total Partners", total)
    with k2:
        pct_act = f"{round(activos / total * 100)}% del portafolio" if total else ""
        _kpi("Partners Activos", activos, pct_act)
    with k3:
        delta_r = "Requieren atencion" if alto_r else "Bajo control"
        _kpi("Alto / Muy Alto Riesgo", alto_r, delta_r,
             color=_C_RED if alto_r else _C_CYAN)
    with k4:
        _kpi("En Onboarding", onboarding, color=_C_VIOLET)

    _spacer()

    # ==================================================================
    # SECCION 2 — Salud de Relacion Corporativa
    # ==================================================================
    _section("Salud de Relacion Corporativa")
    eg1, eg2, eg3 = st.columns(3)
    with eg1:
        _empresa_card("HoldingsBPO", salud_grupo.get("hbpocorp", {}), _C_CYAN)
    with eg2:
        _empresa_card("Adamo",       salud_grupo.get("adamo",    {}), _C_VIOLET)
    with eg3:
        _empresa_card("Paycop",      salud_grupo.get("paycop",   {}), _C_AMBER)

    _spacer()

    # ==================================================================
    # SECCION 3 — Monitor de Riesgo Operativo
    # ==================================================================
    _section("Monitor de Riesgo Operativo")
    col_donut, col_term = st.columns([1, 1])

    # -- 3a. Capacidades de alto riesgo (grafico donut) ----------------
    with col_donut:
        st.markdown(
            f"<div style='background:{_C_BG};border-radius:10px;padding:16px;"
            f"border:1px solid {_C_BORDER};'>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='color:{_C_GRAY};font-size:0.72rem;font-weight:600;"
            f"text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;'>"
            f"Capacidades de Alto Riesgo</div>",
            unsafe_allow_html=True,
        )

        cap_total   = stats_cap.get("total", 0)
        solo_crypto = stats_cap.get("crypto_friendly", 0) - stats_cap.get("ambos", 0)
        solo_adult  = stats_cap.get("adult_friendly",  0) - stats_cap.get("ambos", 0)
        ambos       = stats_cap.get("ambos", 0)
        ninguno     = stats_cap.get("ninguno", 0)

        if cap_total > 0:
            fig_donut = go.Figure(go.Pie(
                labels=["Solo Crypto", "Solo Adult", "Crypto + Adult", "Sin exposicion"],
                values=[solo_crypto, solo_adult, ambos, ninguno],
                hole=0.62,
                marker=dict(colors=[_C_AMBER, _C_ORANGE, _C_RED, "#374151"]),
                textinfo="percent",
                textfont=dict(color="#f9fafb", size=11),
                hovertemplate="<b>%{label}</b><br>%{value} partners (%{percent})<extra></extra>",
            ))
            fig_donut.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=True,
                legend=dict(
                    font=dict(color=_C_GRAY, size=11),
                    bgcolor="rgba(0,0,0,0)",
                    orientation="v",
                    x=0.75, y=0.5,
                ),
                margin=dict(t=10, b=10, l=10, r=10),
                height=220,
                annotations=[dict(
                    text=f"<b>{cap_total}</b>",
                    font=dict(color="#f9fafb", size=14),
                    x=0.35, y=0.5, showarrow=False,
                )],
            )
            st.plotly_chart(
                fig_donut, use_container_width=True,
                config={"displayModeBar": False},
            )
        else:
            st.info("Sin partners registrados aun.")

        st.markdown("</div>", unsafe_allow_html=True)

    # -- 3b. Termometro SARLAFT ----------------------------------------
    with col_term:
        st.markdown(
            f"<div style='background:{_C_BG};border-radius:10px;padding:20px;"
            f"border:1px solid {_C_BORDER};height:100%;'>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='color:{_C_GRAY};font-size:0.72rem;font-weight:600;"
            f"text-transform:uppercase;letter-spacing:1px;margin-bottom:16px;'>"
            f"Termometro SARLAFT</div>",
            unsafe_allow_html=True,
        )

        t_total = sum(termometro.values())
        _termometro_row("Vencidos",      termometro.get("vencidos",  0), t_total, _C_RED)
        _termometro_row("Proximos 15d",  termometro.get("proximos",  0), t_total, _C_AMBER)
        _termometro_row("Al Dia",        termometro.get("al_dia",    0), t_total, _C_CYAN)
        _termometro_row("Sin fecha",     termometro.get("sin_fecha", 0), t_total, "#4b5563")

        # Mini KPIs de riesgo por nivel
        st.markdown(
            f"<div style='margin-top:14px;border-top:1px solid {_C_BORDER};"
            f"padding-top:12px;display:flex;gap:8px;'>",
            unsafe_allow_html=True,
        )
        for nivel, color in _COLORES_RIESGO.items():
            cnt = stats_riesgo.get(nivel, 0)
            st.markdown(
                f"<div style='text-align:center;flex:1;'>"
                f"  <div style='color:{color};font-size:1.2rem;font-weight:800;'>{cnt}</div>"
                f"  <div style='color:{_C_GRAY};font-size:0.65rem;'>{nivel}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div></div>", unsafe_allow_html=True)

    _spacer()

    # ==================================================================
    # SECCION 4 — Analisis de Volumen y Concentracion
    # ==================================================================
    _section("Analisis de Volumen y Concentracion")

    if not volumenes:
        st.info("Ningun partner tiene volumen real registrado aun.")
    else:
        if len(volumenes) == 1:
            st.warning(
                f"Concentracion critica: solo **{volumenes[0]['nombre_razon_social']}** "
                "tiene volumen registrado. Riesgo de dependencia de contraparte unica."
            )

        st.markdown(
            f"<div style='background:{_C_BG};border-radius:10px;padding:16px;"
            f"border:1px solid {_C_BORDER};'>",
            unsafe_allow_html=True,
        )
        hdr = st.columns([4, 3, 2, 2])
        for col, lbl in zip(hdr, ["Partner", "Volumen Estimado", "Riesgo", "Pipeline"]):
            col.markdown(
                f"<span style='color:{_C_CYAN};font-size:0.72rem;font-weight:700;"
                f"text-transform:uppercase;'>{lbl}</span>",
                unsafe_allow_html=True,
            )
        st.markdown(
            f"<hr style='border-color:{_C_BORDER};margin:6px 0 10px;'>",
            unsafe_allow_html=True,
        )
        for v in volumenes:
            nivel  = v.get("nivel_riesgo", "Medio")
            color  = _COLORES_RIESGO.get(nivel, _C_GRAY)
            c1, c2, c3, c4 = st.columns([4, 3, 2, 2])
            c1.markdown(
                f"<span style='color:#f9fafb;font-size:0.88rem;font-weight:600;'>"
                f"{v['nombre_razon_social']}</span>",
                unsafe_allow_html=True,
            )
            c2.markdown(
                f"<span style='color:{_C_CYAN};font-size:0.88rem;font-weight:700;'>"
                f"{v['volumen_real_mensual']}</span>",
                unsafe_allow_html=True,
            )
            c3.markdown(
                f"<span style='background:{color}22;color:{color};padding:2px 8px;"
                f"border-radius:20px;font-size:0.72rem;font-weight:700;'>{nivel}</span>",
                unsafe_allow_html=True,
            )
            c4.markdown(
                f"<span style='color:{_C_GRAY};font-size:0.82rem;'>"
                f"{v.get('estado_pipeline', '')}</span>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    _spacer()

    # ==================================================================
    # SECCION 5 — Centro de Alertas de Compliance
    # ==================================================================
    _section("Centro de Alertas de Compliance")
    with next(get_session()) as session2:
        repo2 = PartnerRepository(session2)
        render_centro_notificaciones(repo2, session2, user)
