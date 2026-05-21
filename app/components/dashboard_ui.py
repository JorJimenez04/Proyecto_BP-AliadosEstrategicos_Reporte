"""
app/components/dashboard_ui.py
Dashboard Ejecutivo — Core Operations Hub · Adamo Services Partner Manager.

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


def _empresa_card(nombre: str, datos: dict, color: str, partners: list) -> None:
    activos   = datos.get("activos", 0)
    inactivos = datos.get("inactivos", 0)
    sin_rel   = datos.get("sin_relacion", 0)
    pct       = datos.get("pct_activos", 0.0)
    total_rel = activos + inactivos + sin_rel

    # ── Salud badge ──────────────────────────────────────────────────
    if pct >= 70:
        salud_color, salud_label, salud_icon = _C_CYAN,  "Saludable", "●"
    elif pct >= 40:
        salud_color, salud_label, salud_icon = _C_AMBER, "En Alerta", "▲"
    else:
        salud_color, salud_label, salud_icon = _C_RED,   "Crítico",   "■"

    # ── Anillo SVG ───────────────────────────────────────────────────
    # Circunferencia r=28 → 2π×28 ≈ 175.9
    _circ     = 175.9
    _filled_a = round((activos   / total_rel * _circ), 1) if total_rel else 0
    _filled_i = round((inactivos / total_rel * _circ), 1) if total_rel else 0
    _offset_a = round(_circ * 0.25, 1)
    _offset_i = round(_circ * 0.25 - _filled_a, 1)

    _ring_svg = (
        f"<svg width='80' height='80' viewBox='0 0 80 80'"
        f" xmlns='http://www.w3.org/2000/svg'>"
        f"<circle cx='40' cy='40' r='28' fill='none'"
        f" stroke='#1e2130' stroke-width='9'/>"
        f"<circle cx='40' cy='40' r='28' fill='none'"
        f" stroke='{_C_CYAN}' stroke-width='9'"
        f" stroke-dasharray='{_filled_a} {_circ - _filled_a}'"
        f" stroke-dashoffset='{_offset_a}'"
        f" transform='rotate(-90 40 40)'"
        f" stroke-linecap='round'/>"
        f"<circle cx='40' cy='40' r='28' fill='none'"
        f" stroke='{_C_RED}' stroke-width='9' opacity='0.7'"
        f" stroke-dasharray='{_filled_i} {_circ - _filled_i}'"
        f" stroke-dashoffset='{_offset_i}'"
        f" transform='rotate(-90 40 40)'"
        f" stroke-linecap='round'/>"
        f"<text x='40' y='36' text-anchor='middle'"
        f" fill='#f9fafb' font-size='13' font-weight='800'"
        f" font-family='Inter,sans-serif'>{pct}%</text>"
        f"<text x='40' y='50' text-anchor='middle'"
        f" fill='#6b7280' font-size='7' font-weight='600'"
        f" font-family='Inter,sans-serif' letter-spacing='0.5'>ACTIVOS</text>"
        f"</svg>"
    )

    # ── Partners por estado (función anidada) ────────────────────────
    def _partner_rows(estado_filtro: str, e_color: str, icon: str) -> str:
        filtrados = [p for p in partners if p.get("estado", "") == estado_filtro]
        if not filtrados:
            return (
                f"<div style='color:#4b5563;font-size:0.75rem;"
                f"font-style:italic;padding:6px 0;'>"
                f"Sin partners en este estado</div>"
            )
        rows = ""
        for p in filtrados:
            nombre_p = p.get("nombre_razon_social", "—")
            riesgo   = p.get("nivel_riesgo", "")
            r_color  = _COLORES_RIESGO.get(riesgo, "#4b5563")
            riesgo_badge = (
                f"<span style='background:{r_color}18;color:{r_color};"
                f"font-size:0.62rem;font-weight:700;padding:1px 7px;"
                f"border-radius:10px;border:1px solid {r_color}33;"
                f"white-space:nowrap;margin-left:6px;'>{riesgo}</span>"
            ) if riesgo else ""
            rows += (
                f"<div style='display:flex;justify-content:space-between;"
                f"align-items:center;padding:6px 8px;border-radius:8px;"
                f"margin-bottom:3px;background:#0d1117;'>"
                f"<div style='display:flex;align-items:center;gap:6px;'>"
                f"<span style='color:{e_color};font-size:0.65rem;'>{icon}</span>"
                f"<span style='color:#e5e7eb;font-size:0.80rem;"
                f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                f"max-width:140px;'>{nombre_p}</span>"
                f"{riesgo_badge}"
                f"</div>"
                f"</div>"
            )
        return rows

    def _partner_rows_multi(estados: list, e_color: str, icon: str) -> str:
        filtrados = [
            p for p in partners
            if p.get("estado", "") in estados
        ]
        if not filtrados:
            return (
                f"<div style='color:#4b5563;font-size:0.75rem;"
                f"font-style:italic;padding:6px 0;'>"
                f"Sin partners en este estado</div>"
            )
        rows = ""
        for p in filtrados:
            nombre_p = p.get("nombre_razon_social", "—")
            riesgo   = p.get("nivel_riesgo", "")
            r_color  = _COLORES_RIESGO.get(riesgo, "#4b5563")
            riesgo_badge = (
                f"<span style='background:{r_color}18;color:{r_color};"
                f"font-size:0.62rem;font-weight:700;padding:1px 7px;"
                f"border-radius:10px;border:1px solid {r_color}33;"
                f"white-space:nowrap;margin-left:6px;'>{riesgo}</span>"
            ) if riesgo else ""
            estado_p = p.get("estado", "")
            rows += (
                f"<div style='display:flex;justify-content:space-between;"
                f"align-items:center;padding:6px 8px;border-radius:8px;"
                f"margin-bottom:3px;background:#0d1117;'>"
                f"<div style='display:flex;align-items:center;gap:6px;'>"
                f"<span style='color:{e_color};font-size:0.65rem;'>{icon}</span>"
                f"<span style='color:#e5e7eb;font-size:0.80rem;"
                f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                f"max-width:140px;'>{nombre_p}</span>"
                f"{riesgo_badge}"
                f"</div>"
                f"<span style='color:{e_color};font-size:0.62rem;"
                f"font-weight:600;opacity:0.8;'>{estado_p}</span>"
                f"</div>"
            )
        return rows

    _rows_activos   = _partner_rows("Activo", _C_CYAN, "●")
    _rows_inactivos = _partner_rows_multi(
        ["Inactivo", "Suspendido", "Terminado"], _C_RED, "■"
    )
    _rows_sin_rel   = _partner_rows_multi(
        ["Sin relación", "Sin Relacion", ""], "#4b5563", "○"
    )

    # ── Barra proporcional mini (3 colores) ──────────────────────────
    _pct_a = round(activos   / total_rel * 100) if total_rel else 0
    _pct_i = round(inactivos / total_rel * 100) if total_rel else 0
    _pct_s = 100 - _pct_a - _pct_i

    _mini_bar = (
        f"<div style='display:flex;height:4px;border-radius:99px;"
        f"overflow:hidden;gap:1px;margin-bottom:14px;'>"
        f"<div style='flex:{_pct_a};background:{_C_CYAN};"
        f"border-radius:99px;'></div>"
        f"<div style='flex:{_pct_i};background:{_C_RED};"
        f"border-radius:99px;opacity:0.7;'></div>"
        f"<div style='flex:{_pct_s};background:#1e2130;"
        f"border-radius:99px;'></div>"
        f"</div>"
    ) if total_rel else ""

    # ── Render final ─────────────────────────────────────────────────
    st.markdown(
        f"<div style='background:#0d1117;border-radius:16px;padding:20px;"
        f"border:1px solid #1e2130;border-top:3px solid {color};"
        f"box-shadow:0 2px 8px rgba(0,0,0,0.3);'>"

        # Header: nombre + anillo + badge salud
        f"<div style='display:flex;justify-content:space-between;"
        f"align-items:flex-start;margin-bottom:14px;'>"
        f"<div>"
        f"<div style='color:{color};font-weight:800;font-size:0.88rem;"
        f"text-transform:uppercase;letter-spacing:1.2px;"
        f"margin-bottom:6px;'>{nombre}</div>"
        f"<span style='background:{salud_color}18;color:{salud_color};"
        f"font-size:0.65rem;font-weight:700;padding:3px 10px;"
        f"border-radius:20px;border:1px solid {salud_color}33;'>"
        f"{salud_icon} {salud_label}</span>"
        f"</div>"
        f"<div>{_ring_svg}</div>"
        f"</div>"

        # Contadores 3 columnas
        f"<div style='display:grid;grid-template-columns:1fr 1fr 1fr;"
        f"gap:8px;margin-bottom:12px;'>"
        f"<div style='background:#0a0f1a;border-radius:10px;padding:10px;"
        f"border:1px solid #1e2130;text-align:center;'>"
        f"<div style='color:{_C_CYAN};font-size:1.5rem;font-weight:800;"
        f"line-height:1;'>{activos}</div>"
        f"<div style='color:#6b7280;font-size:0.60rem;margin-top:3px;"
        f"letter-spacing:0.8px;font-weight:600;'>ACTIVOS</div>"
        f"</div>"
        f"<div style='background:#0a0f1a;border-radius:10px;padding:10px;"
        f"border:1px solid #1e2130;text-align:center;'>"
        f"<div style='color:{_C_RED};font-size:1.5rem;font-weight:800;"
        f"line-height:1;'>{inactivos}</div>"
        f"<div style='color:#6b7280;font-size:0.60rem;margin-top:3px;"
        f"letter-spacing:0.8px;font-weight:600;'>INACTIVOS</div>"
        f"</div>"
        f"<div style='background:#0a0f1a;border-radius:10px;padding:10px;"
        f"border:1px solid #1e2130;text-align:center;'>"
        f"<div style='color:#4b5563;font-size:1.5rem;font-weight:800;"
        f"line-height:1;'>{sin_rel}</div>"
        f"<div style='color:#6b7280;font-size:0.60rem;margin-top:3px;"
        f"letter-spacing:0.8px;font-weight:600;'>SIN REL.</div>"
        f"</div>"
        f"</div>"

        # Barra proporcional
        f"{_mini_bar}"

        # Leyenda
        f"<div style='display:flex;gap:12px;margin-bottom:14px;'>"
        f"<span style='display:flex;align-items:center;gap:4px;"
        f"color:#6b7280;font-size:0.65rem;'>"
        f"<span style='width:8px;height:8px;border-radius:50%;"
        f"background:{_C_CYAN};display:inline-block;'></span>Activos</span>"
        f"<span style='display:flex;align-items:center;gap:4px;"
        f"color:#6b7280;font-size:0.65rem;'>"
        f"<span style='width:8px;height:8px;border-radius:50%;"
        f"background:{_C_RED};display:inline-block;opacity:0.7;'></span>Inactivos</span>"
        f"<span style='display:flex;align-items:center;gap:4px;"
        f"color:#6b7280;font-size:0.65rem;'>"
        f"<span style='width:8px;height:8px;border-radius:50%;"
        f"background:#1e2130;display:inline-block;'></span>Sin rel.</span>"
        f"</div>"

        # Sección partners por estado
        f"<div style='border-top:1px solid #1e2130;padding-top:12px;'>"

        f"<div style='margin-bottom:10px;'>"
        f"<div style='display:flex;align-items:center;gap:6px;margin-bottom:6px;'>"
        f"<span style='width:6px;height:6px;border-radius:50%;"
        f"background:{_C_CYAN};display:inline-block;'></span>"
        f"<span style='color:{_C_CYAN};font-size:0.65rem;font-weight:700;"
        f"letter-spacing:0.8px;text-transform:uppercase;'>Activos ({activos})</span></div>"
        f"{_rows_activos}</div>"

        f"<div style='margin-bottom:10px;'>"
        f"<div style='display:flex;align-items:center;gap:6px;margin-bottom:6px;'>"
        f"<span style='width:6px;height:6px;border-radius:50%;"
        f"background:{_C_RED};display:inline-block;opacity:0.7;'></span>"
        f"<span style='color:{_C_RED};font-size:0.65rem;font-weight:700;"
        f"letter-spacing:0.8px;text-transform:uppercase;'>"
        f"Inactivos / Suspendidos ({inactivos})</span></div>"
        f"{_rows_inactivos}</div>"

        f"<div>"
        f"<div style='display:flex;align-items:center;gap:6px;margin-bottom:6px;'>"
        f"<span style='width:6px;height:6px;border-radius:50%;"
        f"background:#4b5563;display:inline-block;'></span>"
        f"<span style='color:#4b5563;font-size:0.65rem;font-weight:700;"
        f"letter-spacing:0.8px;text-transform:uppercase;'>Sin Relación ({sin_rel})</span></div>"
        f"{_rows_sin_rel}</div>"

        f"</div>"   # cierre sección partners
        f"</div>",  # cierre contenedor principal
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
    Dashboard ejecutivo de Adamo Services — Core Operations Hub.

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
        f"""
        <div style='margin-bottom:6px;'>
            <h1 style='margin-bottom:4px;letter-spacing:4px;font-size:1.95rem;
                       background:linear-gradient(135deg,#ffffff 30%,{_C_CYAN} 70%);
                       -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                       background-clip:text;display:inline-block;'>
                CORE OPERATIONS HUB
            </h1>
            <div style='color:#9ca3af;font-size:0.88rem;margin-top:2px;letter-spacing:0.3px;'>
                Gestión de Ecosistema Bancario y Gobierno de Datos
            </div>
            <div style='display:inline-flex;align-items:center;gap:6px;
                        background:rgba(95,233,208,0.1);border:1px solid rgba(95,233,208,0.28);
                        border-radius:20px;padding:3px 12px;margin-top:8px;font-size:0.72rem;
                        color:{_C_CYAN};font-weight:600;letter-spacing:0.5px;'>
                <span style='width:7px;height:7px;background:{_C_CYAN};border-radius:50%;
                             display:inline-block;box-shadow:0 0 6px {_C_CYAN};'></span>
                Monitoreo Activo: Online
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    try:
        with next(get_session()) as session:
            repo = PartnerRepository(session)

            stats_pipeline  = repo.get_stats_pipeline()
            stats_riesgo    = repo.get_stats_riesgo()
            salud_grupo     = repo.get_salud_grupo()
            stats_cap       = repo.get_stats_capacidades()
            termometro      = repo.get_termometro_sarlaft()
            volumenes       = repo.get_resumen_volumen()
            partners_hbpo   = repo.get_partners_por_empresa("hbpocorp")
            partners_adamo  = repo.get_partners_por_empresa("adamo")
            partners_paycop = repo.get_partners_por_empresa("paycop")

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

        import pandas as pd

        df_vol = pd.DataFrame(volumenes).rename(columns={
            "nombre_razon_social":  "Partner",
            "volumen_real_mensual": "Volumen",
            "crypto_friendly":      "Crypto 🔥",
            "adult_friendly":       "Adult 🔞",
            "permite_monetizacion": "Monet. 📥",
            "permite_dispersion":   "Disp. 📤",
        })

        # Ordenar descendente por volumen (texto → intentar numérico)
        df_vol["_sort"] = pd.to_numeric(
            df_vol["Volumen"].astype(str)
                .str.replace(r"[^\d.]", "", regex=True),
            errors="coerce",
        ).fillna(0)
        df_vol = df_vol.sort_values("_sort", ascending=False).drop(columns=["_sort"])

        # Asegurar booleanos
        for col in ("Crypto 🔥", "Adult 🔞", "Monet. 📥", "Disp. 📤"):
            if col in df_vol.columns:
                df_vol[col] = df_vol[col].astype(bool)

        st.dataframe(
            df_vol,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Partner":     st.column_config.TextColumn("Partner", width="large"),
                "Volumen":     st.column_config.TextColumn("Volumen Estimado", width="medium"),
                "Crypto 🔥":  st.column_config.CheckboxColumn("Crypto 🔥",  width="small"),
                "Adult 🔞":   st.column_config.CheckboxColumn("Adult 🔞",   width="small"),
                "Monet. 📥":  st.column_config.CheckboxColumn("Monet. 📥",  width="small"),
                "Disp. 📤":   st.column_config.CheckboxColumn("Disp. 📤",   width="small"),
            },
        )

    _spacer()

    # ==================================================================
    # SECCION 5 — Centro de Alertas de Compliance
    # ==================================================================
    _section("Centro de Alertas de Compliance")
    with next(get_session()) as session2:
        repo2 = PartnerRepository(session2)
        render_centro_notificaciones(repo2, session2, user)
