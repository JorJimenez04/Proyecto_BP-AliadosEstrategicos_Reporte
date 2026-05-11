"""
app/components/crypto_ui.py
Módulo Cripto Compliance — VASP Monitor (Global Ledger).
Acceso restringido a roles: admin, compliance.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

import streamlit as st

from config.settings import Roles
from db.database import get_session
from db.repositories.crypto_repo import CryptoRepository, score_a_nivel_riesgo
from db.models import WalletMonitorCreate, RiskLabel, CryptoClienteCreate

logger = logging.getLogger(__name__)

# ── Paleta de colores por nivel ──────────────────────────────
_COLOR_NIVEL: dict[str, str] = {
    "Crítico":   "#ef4444",
    "Alto":      "#f97316",
    "Medio":     "#f59e0b",
    "Bajo":      "#22c55e",
    "Sin Datos": "#6b7280",
}
_BORDER_NIVEL: dict[str, str] = {
    "Crítico":   "2px solid #ef4444",
    "Alto":      "2px solid #f97316",
    "Medio":     "2px solid #f59e0b",
    "Bajo":      "2px solid #22c55e",
    "Sin Datos": "1px solid #374151",
}

_BLOCKCHAIN_ICONS: dict[str, str] = {
    "ETH": "⟠",  "BTC": "₿",  "BNB": "🔶",
    "TRX": "🔴", "SOL": "◎",  "MATIC": "🟣",
}

_LABELS_CRITICOS = {
    "Sanctioned Exchange", "OFAC Sanctioned", "Darknet Market",
    "Ransomware", "Scam", "Terrorism Financing",
    "Child Abuse Material", "Mixer", "Blacklisted",
}


# ── Helpers de UI ────────────────────────────────────────────
def _pill(text: str, color: str, bg: str = "") -> str:
    bg_style = f"background:{bg};" if bg else "background:rgba(255,255,255,0.08);"
    return (
        f"<span style='{bg_style}color:{color};padding:2px 10px;"
        f"border-radius:20px;font-size:0.72rem;font-weight:700;"
        f"border:1px solid {color};'>{text}</span>"
    )


def _score_bar(score: Optional[int]) -> str:
    if score is None:
        return "<span style='color:#6b7280;font-size:0.75rem;'>Sin datos</span>"
    color = _COLOR_NIVEL[score_a_nivel_riesgo(score)]
    pct   = score
    return (
        f"<div style='display:flex;align-items:center;gap:8px;'>"
        f"<div style='flex:1;background:#1f2937;border-radius:4px;height:8px;'>"
        f"<div style='width:{pct}%;background:{color};height:100%;border-radius:4px;'></div>"
        f"</div>"
        f"<span style='color:{color};font-size:0.8rem;font-weight:700;min-width:32px;'>{score}</span>"
        f"</div>"
    )


def _parse_labels(raw) -> list[dict]:
    """Normaliza risk_labels desde DB (puede ser str JSON, list o None)."""
    if not raw:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    return raw if isinstance(raw, list) else []


@st.cache_data(ttl=600, show_spinner=False)
def _get_wallets_cached(
    riesgo_nivel: Optional[str],
    blockchain: Optional[str],
    solo_criticos: bool,
    search_text: Optional[str],
    crypto_cliente_id: Optional[int] = None,
) -> list[dict]:
    """Lista de wallets con caché de 10 min."""
    try:
        session = next(get_session())
        wallets = CryptoRepository(session).get_lista(
            riesgo_nivel=riesgo_nivel,
            blockchain=blockchain,
            solo_criticos=solo_criticos,
            search_text=search_text,
        )
        session.close()
        # Filtrar por cliente si se especificó
        if crypto_cliente_id:
            wallets = [w for w in wallets if w.get("crypto_cliente_id") == crypto_cliente_id]
        return wallets
    except Exception:
        return []


@st.cache_data(ttl=300, show_spinner=False)
def _get_clientes_cached() -> list[dict]:
    """Lista de clientes corporativos con caché de 5 min."""
    try:
        session = next(get_session())
        clientes = CryptoRepository(session).get_clientes()
        session.close()
        return clientes
    except Exception:
        return []


# ── Ficha individual de wallet ───────────────────────────────
def _ficha_wallet(wallet: dict, user: dict) -> None:
    """Panel de detalle con tabs para una wallet seleccionada."""
    nivel      = wallet.get("riesgo_nivel", "Sin Datos")
    color      = _COLOR_NIVEL.get(nivel, "#6b7280")
    score      = wallet.get("gl_score")
    labels     = _parse_labels(wallet.get("risk_labels"))
    chain      = wallet.get("blockchain", "ETH")
    chain_icon = _BLOCKCHAIN_ICONS.get(chain, "🔗")

    st.markdown(
        f"<h4 style='color:#f9fafb;margin-bottom:4px;'>"
        f"{chain_icon} <code style='color:#5fe9d0;font-size:0.85rem;'>"
        f"{wallet['wallet_address']}</code></h4>",
        unsafe_allow_html=True,
    )
    st.markdown(
        _pill(nivel, color) + "&nbsp;&nbsp;" +
        _pill(chain, "#5fe9d0") +
        ("&nbsp;&nbsp;" + _pill("⚠️ ATENCIÓN PRIORITARIA", "#ef4444")
         if (score is not None and score < 30) or nivel == "Crítico" else ""),
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    tab_resumen, tab_labels, tab_notas = st.tabs(
        ["📊 Resumen", "🚩 Risk Labels", "📝 Notas & Reporte"]
    )

    with tab_resumen:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**GL Score**")
            st.markdown(_score_bar(score), unsafe_allow_html=True)
        with c2:
            exp      = wallet.get("total_exposure", 0) or 0
            currency = wallet.get("exposure_currency", "USD")
            st.metric("Exposición Total", f"${exp:,.2f} {currency}")
        with c3:
            st.metric("Cliente", wallet.get("client_nombre") or "—")

        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            rd = wallet.get("last_report_date")
            st.markdown(f"**Último reporte:** {str(rd)[:16] if rd else '—'}")
            st.markdown(f"**Blockchain:** {chain_icon} {chain}")
        with col_b:
            st.markdown(f"**Registrado por:** {wallet.get('registrado_por') or '—'}")
            st.markdown(f"**Actualizado:** {str(wallet.get('updated_at',''))[:16]}")

    with tab_labels:
        if not labels:
            st.info("Sin alertas registradas para esta wallet.")
        else:
            for lbl in labels:
                label_text = lbl.get("label", "")
                is_red     = label_text in _LABELS_CRITICOS
                pct        = lbl.get("exposure_pct", 0)
                source     = lbl.get("source", "")
                flag_color = "#ef4444" if is_red else "#f59e0b"
                st.markdown(
                    f"<div style='background:#1f2937;border-left:3px solid {flag_color};"
                    f"padding:8px 14px;border-radius:6px;margin-bottom:8px;'>"
                    f"<span style='color:{flag_color};font-weight:700;'>{'🔴' if is_red else '🟡'} {label_text}</span>"
                    f"&nbsp;&nbsp;<span style='color:#9ca3af;font-size:0.8rem;'>"
                    f"Exposición: {pct:.1f}%{' · ' + source if source else ''}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    with tab_notas:
        notas = wallet.get("notas") or ""
        pdf   = wallet.get("pdf_report_url") or ""
        if pdf:
            st.markdown(f"**📄 Reporte PDF:** [{pdf}]({pdf})")
            st.link_button("⬇️ Descargar reporte PDF", pdf, use_container_width=False)
        else:
            st.caption("Sin PDF adjunto.")
        st.markdown("**Notas internas:**")
        st.markdown(notas if notas else "_Sin notas._")

    st.markdown("---")
    if st.button("✖ Cerrar ficha", key=f"close_ficha_{wallet['id']}"):
        st.session_state.pop("crypto_detail_id", None)
        st.rerun()


# ── Tarjeta de wallet en lista ───────────────────────────────
def _card_wallet(w: dict) -> None:
    nivel      = w.get("riesgo_nivel", "Sin Datos")
    color      = _COLOR_NIVEL.get(nivel, "#6b7280")
    border     = _BORDER_NIVEL.get(nivel, "1px solid #374151")
    score      = w.get("gl_score")
    chain      = w.get("blockchain", "ETH")
    chain_icon = _BLOCKCHAIN_ICONS.get(chain, "🔗")
    labels     = _parse_labels(w.get("risk_labels"))
    n_red      = sum(1 for lbl in labels if lbl.get("label") in _LABELS_CRITICOS)
    exp        = w.get("total_exposure", 0) or 0

    score_text   = str(score) if score is not None else "N/A"
    labels_badge = (
        f"<span style='color:#ef4444;font-size:0.72rem;font-weight:700;'>"
        f"🔴 {n_red} label{'s' if n_red != 1 else ''} crítica{'s' if n_red != 1 else ''}</span>"
        if n_red else ""
    )

    st.markdown(
        f"""<div style='border:{border};border-radius:10px;padding:14px 18px;
        background:#111827;margin-bottom:10px;'>
        <div style='display:flex;justify-content:space-between;align-items:center;'>
            <span style='color:#5fe9d0;font-size:0.8rem;font-family:monospace;'>
                {chain_icon} {w['wallet_address'][:20]}…{w['wallet_address'][-8:]}
            </span>
            {_pill(nivel, color)}
        </div>
        <div style='display:flex;gap:20px;margin-top:8px;align-items:center;'>
            <span style='color:#9ca3af;font-size:0.78rem;'>
                🎯 Score: <b style='color:{color};'>{score_text}</b>
            </span>
            <span style='color:#9ca3af;font-size:0.78rem;'>
                💰 ${exp:,.0f} USD
            </span>
            <span style='color:#9ca3af;font-size:0.78rem;'>
                👤 {w.get('client_nombre') or '—'}
            </span>
            {labels_badge}
        </div>
        </div>""",
        unsafe_allow_html=True,
    )
    if st.button("📋 Ver Ficha", key=f"ver_wallet_{w['id']}", use_container_width=False):
        st.session_state["crypto_detail_id"] = w["id"]
        st.rerun()


# ── Tab Gestión de Clientes ──────────────────────────────────
def _tab_clientes(user: dict) -> None:
    """CRUD de clientes corporativos del módulo Cripto Compliance."""
    st.markdown("### 👥 Clientes Corporativos")

    # Búsqueda
    buscar = st.text_input("🔍 Buscar por razón social o NIT", placeholder="Blue Gate SAS...")

    # Cargar clientes
    try:
        session = next(get_session())
        clientes = CryptoRepository(session).get_clientes(search=buscar)
        session.close()
    except Exception as exc:
        st.error(f"Error cargando clientes: {exc}")
        clientes = []

    if not clientes:
        st.info("✅ Sin clientes registrados. Registra el primero usando el formulario de abajo.")
    else:
        st.caption(f"{len(clientes)} cliente{'s' if len(clientes) != 1 else ''} registrado{'s' if len(clientes) != 1 else ''}")
        for cl in clientes:
            total_wallets = int(cl.get("total_wallets") or 0)
            exposure_total = float(cl.get("exposure_total") or 0)
            nivel_badge = ""
            if total_wallets > 0:
                nivel_badge = f"<span style='color:#5fe9d0;font-size:0.75rem;'>{total_wallets} wallet{'s' if total_wallets != 1 else ''}</span>"

            st.markdown(
                f"""<div style='border:1px solid #374151;border-radius:10px;
                padding:14px 18px;background:#111827;margin-bottom:10px;'>
                <div style='display:flex;justify-content:space-between;align-items:flex-start;'>
                    <div>
                        <div style='color:#f9fafb;font-weight:700;font-size:1rem;'>
                            🏢 {cl['razon_social']}
                        </div>
                        <div style='color:#9ca3af;font-size:0.8rem;margin-top:4px;'>
                            NIT: {cl.get('nit') or '—'} &nbsp;·&nbsp;
                            Rep: {cl.get('representante_legal') or '—'} &nbsp;·&nbsp;
                            {cl.get('correo_corporativo') or '—'}
                        </div>
                    </div>
                    <div style='text-align:right;'>
                        {nivel_badge}
                        <div style='color:#f59e0b;font-size:0.85rem;font-weight:700;margin-top:4px;'>
                            💰 ${exposure_total:,.0f} USD
                        </div>
                    </div>
                </div>
                </div>""",
                unsafe_allow_html=True,
            )
            col_ver, col_esp = st.columns([1, 5])
            with col_ver:
                if st.button("📋 Ver Wallets", key=f"ver_cl_{cl['id']}"):
                    st.session_state["crypto_cliente_filtro"] = cl["id"]
                    st.session_state["crypto_cliente_nombre"] = cl["razon_social"]
                    st.rerun()

    st.markdown("---")
    # Formulario de nuevo cliente
    with st.expander("➕ Registrar Nuevo Cliente", expanded=False):
        with st.form("form_nuevo_cliente", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                razon_social = st.text_input("Razón Social *", placeholder="Blue Gate SAS")
                representante = st.text_input("Representante Legal", placeholder="Juan Pérez")
                correo = st.text_input("Correo Corporativo", placeholder="contacto@empresa.com")
            with c2:
                nit = st.text_input("NIT", placeholder="900123456-1")
                telefono = st.text_input("Teléfono", placeholder="+57 300 000 0000")
                fecha_onb = st.date_input("Fecha de Onboarding", value=None)
            direccion = st.text_input("Dirección", placeholder="Calle 123 #45-67, Bogotá")
            notas_cl = st.text_area("Notas", height=60)
            submitted = st.form_submit_button("💾 Registrar Cliente", type="primary", use_container_width=True)

        if submitted:
            if not razon_social.strip():
                st.error("La razón social es obligatoria.")
            else:
                try:
                    payload = CryptoClienteCreate(
                        razon_social=razon_social.strip(),
                        nit=nit.strip() or None,
                        representante_legal=representante.strip() or None,
                        correo_corporativo=correo.strip() or None,
                        telefono=telefono.strip() or None,
                        direccion=direccion.strip() or None,
                        fecha_onboarding=fecha_onb if fecha_onb else None,
                        notas=notas_cl.strip() or None,
                        creado_por=user.get("username"),
                    )
                    session = next(get_session())
                    CryptoRepository(session).crear_cliente(payload)
                    session.close()
                    _get_clientes_cached.clear()
                    st.success(f"✅ Cliente **{razon_social}** registrado correctamente.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error al registrar cliente: {exc}")


# ── Tab Vincular Wallet ──────────────────────────────────────
def _tab_vincular_wallet(user: dict) -> None:
    """Formulario de registro de wallet vinculada a cliente corporativo."""
    st.markdown("### ➕ Vincular Wallet a Cliente")

    # Cargar lista de clientes para el selectbox
    clientes = _get_clientes_cached()
    if not clientes:
        st.warning("⚠️ No hay clientes registrados. Ve a la pestaña **👥 Clientes** para registrar primero la empresa.")
        return

    opciones_cl = {f"{cl['razon_social']} (NIT: {cl.get('nit') or '—'})": cl["id"] for cl in clientes}
    opciones_labels = list(opciones_cl.keys())

    with st.form("form_nueva_wallet", clear_on_submit=True):
        st.markdown("**Cliente Corporativo** *(obligatorio)*")
        cliente_seleccionado = st.selectbox("Seleccionar Cliente", opciones_labels)

        st.markdown("**Identificación de la Wallet**")
        col1, col2 = st.columns([3, 1])
        with col1:
            wallet_address = st.text_input("Dirección de Wallet *", placeholder="0x... o bc1q...")
        with col2:
            blockchain = st.selectbox("Blockchain", ["ETH", "BTC", "BNB", "TRX", "SOL", "MATIC", "Otro"])

        st.markdown("**Datos Global Ledger**")
        st.caption("💡 Pega los datos del reporte Global Ledger (GL Score, Exposición, Risk Labels)")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            gl_score_val = st.number_input(
                "GL Score (0-100)", min_value=0, max_value=100,
                value=None, placeholder="Ej: 47",
            )
        with col_b:
            niveles = ["Sin Datos", "Bajo", "Medio", "Alto", "Crítico"]
            riesgo_manual = st.selectbox("Nivel de Riesgo", niveles)
        with col_c:
            exposure = st.number_input("Exposición Total", min_value=0.0, value=0.0, step=1000.0,
                                       placeholder="Ej: 2340897.66")
            exposure_currency = st.selectbox("Moneda", ["USD", "EUR", "USDT", "USDC"])

        st.markdown("**Risk Labels** *(JSON de Global Ledger)*")
        st.caption('Ej: `[{"label": "Blacklisted", "exposure_pct": 45.2, "source": "OFAC"}, {"label": "Sanctioned Exchange", "exposure_pct": 12.5, "source": "EU"}]`')
        labels_raw = st.text_area("Risk Labels JSON", value="[]", height=100)

        st.markdown("**Reporte**")
        col_p, col_f = st.columns(2)
        with col_p:
            pdf_url = st.text_input("URL del reporte PDF", placeholder="https://...")
        with col_f:
            report_date = st.date_input("Fecha del reporte", value=None)

        notas = st.text_area("Notas internas", height=80)
        submitted = st.form_submit_button("💾 Vincular Wallet", type="primary", use_container_width=True)

    if submitted:
        if not wallet_address.strip():
            st.error("La dirección de wallet es obligatoria.")
            return

        crypto_cliente_id = opciones_cl[cliente_seleccionado]

        try:
            labels_parsed = json.loads(labels_raw) if labels_raw.strip() else []
            risk_labels   = [RiskLabel(**lbl) if isinstance(lbl, dict) else lbl for lbl in labels_parsed]
        except Exception as exc:
            st.error(f"JSON de Risk Labels inválido: {exc}")
            return

        nivel_final = riesgo_manual
        if nivel_final == "Sin Datos" and gl_score_val is not None:
            nivel_final = score_a_nivel_riesgo(int(gl_score_val))

        # Nombre del cliente para desnormalizar
        cliente_nombre = clientes[[cl["id"] for cl in clientes].index(crypto_cliente_id)]["razon_social"]

        payload = WalletMonitorCreate(
            wallet_address     = wallet_address.strip(),
            blockchain         = blockchain,
            crypto_cliente_id  = crypto_cliente_id,
            client_nombre      = cliente_nombre,
            gl_score           = int(gl_score_val) if gl_score_val is not None else None,
            riesgo_nivel       = nivel_final,
            risk_labels        = risk_labels,
            total_exposure     = float(exposure),
            exposure_currency  = exposure_currency,
            pdf_report_url     = pdf_url.strip() or None,
            last_report_date   = datetime.combine(report_date, datetime.min.time()) if report_date else None,
            registrado_por     = user.get("username"),
            notas              = notas.strip() or None,
        )

        try:
            with next(get_session()) as session:
                result = CryptoRepository(session).upsert_from_gl(payload)

            _get_wallets_cached.clear()
            _get_clientes_cached.clear()
            nivel_r = result.get("riesgo_nivel", "")
            color_r = _COLOR_NIVEL.get(nivel_r, "#6b7280")
            st.success(
                f"✅ Wallet vinculada a **{cliente_nombre}** — "
                f"Score: **{result.get('gl_score', 'N/A')}** · Nivel: **{nivel_r}**"
            )
            st.rerun()
        except Exception as exc:
            st.error(f"Error al registrar wallet: {exc}")


# ── Reporte Gerencial ────────────────────────────────────────
def render_gerencial_crypto(session) -> None:
    """Dashboard ejecutivo con filtro por cliente."""
    import plotly.graph_objects as go

    repo  = CryptoRepository(session)
    stats = repo.get_stats_gerencial()

    if stats.get("_tabla_no_existe"):
        st.warning("⚠️ Módulo no inicializado. Aplica la migración 019.", icon="🛠️")
        return

    # Filtro por cliente
    clientes = repo.get_clientes()
    opciones_cl = {"Todos los clientes": None}
    opciones_cl.update({cl["razon_social"]: cl["id"] for cl in clientes})
    filtro_cliente_label = st.selectbox("🏢 Filtrar por Cliente", list(opciones_cl.keys()))
    filtro_cliente_id    = opciones_cl[filtro_cliente_label]

    # Stats específicas por cliente o globales
    if filtro_cliente_id:
        stats_cl = repo.get_stats_by_cliente(filtro_cliente_id)
        total_wallets = int(stats_cl.get("total_wallets") or 0)
        total_exp     = float(stats_cl.get("exposure_total") or 0)
        nivel_critico = int(stats_cl.get("nivel_critico") or 0)
        nivel_alto    = int(stats_cl.get("nivel_alto") or 0)
        nivel_medio   = int(stats_cl.get("nivel_medio") or 0)
        nivel_bajo    = int(stats_cl.get("nivel_bajo") or 0)
        sin_datos     = int(stats_cl.get("sin_datos") or 0)
        atencion      = nivel_critico + nivel_alto
        criticos      = repo.get_wallets_by_cliente(filtro_cliente_id)
        criticos      = [w for w in criticos if (w.get("gl_score") or 100) < 30
                         or w.get("riesgo_nivel") in ("Crítico", "Alto")]
    else:
        total_wallets = int(stats.get("total_wallets") or 0)
        total_exp     = float(stats.get("total_exposure_usd") or 0)
        nivel_critico = int(stats.get("nivel_critico") or 0)
        nivel_alto    = int(stats.get("nivel_alto") or 0)
        nivel_medio   = int(stats.get("nivel_medio") or 0)
        nivel_bajo    = int(stats.get("nivel_bajo") or 0)
        sin_datos     = int(stats.get("sin_datos") or 0)
        atencion      = int(stats.get("atencion_prioritaria") or 0)
        criticos      = repo.get_atencion_prioritaria()

    # KPI cards
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Wallets", total_wallets)
    k2.metric("Exposición USD", f"${total_exp:,.0f}")
    k3.metric("Atención Prioritaria", atencion,
              delta=f"{atencion} wallets" if atencion else None,
              delta_color="inverse")
    k4.metric("Críticas", nivel_critico)

    if total_wallets == 0:
        st.markdown("---")
        st.info("✅ Sistema listo. Registre la primera wallet para generar el análisis de riesgo.")
        return

    st.markdown("---")
    col_chart, col_table = st.columns([1, 1])

    with col_chart:
        st.markdown("#### Distribución de Riesgo")
        niveles = ["Crítico", "Alto", "Medio", "Bajo", "Sin Datos"]
        counts  = [nivel_critico, nivel_alto, nivel_medio, nivel_bajo, sin_datos]
        if any(c > 0 for c in counts):
            colors_pie = [_COLOR_NIVEL[n] for n in niveles]
            fig = go.Figure(go.Pie(
                labels=niveles, values=counts,
                marker_colors=colors_pie, hole=0.5,
                textinfo="label+value", textfont_size=12,
            ))
            fig.update_layout(
                paper_bgcolor="#111827", plot_bgcolor="#111827",
                font_color="#d1d5db", showlegend=False,
                margin=dict(t=10, b=10, l=10, r=10), height=280,
            )
            st.plotly_chart(fig, use_container_width=True)

        if not filtro_cliente_id:
            por_bc = stats.get("por_blockchain", [])
            if por_bc:
                st.markdown("#### Por Blockchain")
                fig_bc = go.Figure(go.Bar(
                    x=[r["blockchain"] for r in por_bc],
                    y=[r["total"] for r in por_bc],
                    marker_color="#5fe9d0",
                    text=[r["total"] for r in por_bc],
                    textposition="outside",
                ))
                fig_bc.update_layout(
                    paper_bgcolor="#111827", plot_bgcolor="#1f2937",
                    font_color="#d1d5db", showlegend=False,
                    margin=dict(t=20, b=20, l=20, r=20), height=200,
                    xaxis=dict(color="#9ca3af"),
                    yaxis=dict(color="#9ca3af", showgrid=False),
                )
                st.plotly_chart(fig_bc, use_container_width=True)

    with col_table:
        titulo = f"⚠️ Atención Prioritaria{' — ' + filtro_cliente_label if filtro_cliente_id else ''}"
        st.markdown(f"#### {titulo}")
        if not criticos:
            st.success("Sin wallets en atención prioritaria.")
        else:
            for w in criticos[:10]:
                nivel  = w.get("riesgo_nivel", "Sin Datos")
                color  = _COLOR_NIVEL.get(nivel, "#6b7280")
                score  = w.get("gl_score")
                s_text = str(score) if score is not None else "N/A"
                exp    = float(w.get("total_exposure", 0) or 0)
                chain  = w.get("blockchain", "ETH")
                icon   = _BLOCKCHAIN_ICONS.get(chain, "🔗")
                st.markdown(
                    f"<div style='background:#1f2937;border-left:3px solid {color};"
                    f"padding:8px 12px;border-radius:6px;margin-bottom:6px;'>"
                    f"<div style='color:#5fe9d0;font-size:0.75rem;font-family:monospace;'>"
                    f"{icon} {w['wallet_address'][:20]}…</div>"
                    f"<div style='display:flex;gap:14px;margin-top:4px;'>"
                    f"<span style='color:{color};font-size:0.78rem;font-weight:700;'>{nivel}</span>"
                    f"<span style='color:#9ca3af;font-size:0.78rem;'>Score: {s_text}</span>"
                    f"<span style='color:#9ca3af;font-size:0.78rem;'>${exp:,.0f} USD</span>"
                    f"<span style='color:#9ca3af;font-size:0.78rem;'>"
                    f"{w.get('client_nombre') or '—'}</span>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
            if len(criticos) > 10:
                st.caption(f"+ {len(criticos) - 10} wallets adicionales en atención prioritaria.")


# ── Página principal del módulo ──────────────────────────────
def page_crypto_compliance(user: dict) -> None:
    """Punto de entrada del módulo Cripto Compliance."""
    try:
        _page_crypto_compliance_inner(user)
    except Exception as exc:
        logger.exception("Error crítico en Cripto Compliance: %s", exc)
        st.error(f"❌ Error cargando el módulo Cripto: **{exc}**")
        st.caption("Revisa los logs del servidor para más detalles.")


def _page_crypto_compliance_inner(user: dict) -> None:
    """Implementación interna del módulo Cripto Compliance."""
    rol = user.get("rol", "")
    if rol not in {"admin", "compliance"}:
        st.error("🚫 Acceso Denegado. Este módulo requiere rol **admin** o **compliance**.")
        st.stop()

    st.markdown(
        "<h2 style='color:#f9fafb;'>🛡️ Cripto Compliance</h2>"
        "<p style='color:#9ca3af;font-size:0.88rem;margin-top:-8px;'>"
        "VASP Monitor · Global Ledger · FATF / GAFI</p>",
        unsafe_allow_html=True,
    )

    if "crypto_detail_id" not in st.session_state:
        st.session_state["crypto_detail_id"] = None

    tab_clientes, tab_monitor, tab_gerencial, tab_wallet = st.tabs([
        "👥 Clientes",
        "📋 Monitor de Wallets",
        "📊 Reporte Gerencial",
        "➕ Vincular Wallet",
    ])

    # ── Tab 1: Gestión de Clientes ────────────────────────────
    with tab_clientes:
        _tab_clientes(user)

    # ── Tab 2: Monitor de Wallets ─────────────────────────────
    with tab_monitor:
        # Banner si viene del filtro de cliente
        filtro_cl_id     = st.session_state.get("crypto_cliente_filtro")
        filtro_cl_nombre = st.session_state.get("crypto_cliente_nombre")
        if filtro_cl_id:
            col_b, col_x = st.columns([6, 1])
            with col_b:
                st.info(f"🏢 Mostrando wallets de **{filtro_cl_nombre}**")
            with col_x:
                if st.button("✖ Quitar filtro", key="quitar_filtro_cl"):
                    st.session_state.pop("crypto_cliente_filtro", None)
                    st.session_state.pop("crypto_cliente_nombre", None)
                    st.rerun()

        with st.expander("🔍 Filtros", expanded=False):
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                f_nivel = st.selectbox("Nivel de Riesgo",
                                       ["Todos", "Crítico", "Alto", "Medio", "Bajo", "Sin Datos"])
            with f2:
                f_chain = st.selectbox("Blockchain",
                                       ["Todos", "ETH", "BTC", "BNB", "TRX", "SOL", "MATIC"])
            with f3:
                f_criticos = st.checkbox("Solo Atención Prioritaria")
            with f4:
                f_search = st.text_input("Buscar wallet / cliente", placeholder="0x... o nombre")

        detail_id = st.session_state.get("crypto_detail_id")
        if detail_id:
            try:
                session = next(get_session())
                wallet = CryptoRepository(session).get_by_id(detail_id)
                session.close()
            except Exception as exc:
                st.error(f"Error cargando ficha: {exc}")
                wallet = None
            if wallet:
                _ficha_wallet(wallet, user)
                st.markdown("---")
            else:
                st.session_state.pop("crypto_detail_id", None)

        _tabla_ok = True
        try:
            session = next(get_session())
            _stats_check = CryptoRepository(session).get_stats_gerencial()
            session.close()
            _tabla_ok = not _stats_check.get("_tabla_no_existe", False)
            if _tabla_ok:
                wallets = _get_wallets_cached(
                    riesgo_nivel       = f_nivel if f_nivel != "Todos" else None,
                    blockchain         = f_chain if f_chain != "Todos" else None,
                    solo_criticos      = f_criticos,
                    search_text        = f_search or None,
                    crypto_cliente_id  = filtro_cl_id,
                )
            else:
                wallets = []
        except Exception as exc:
            st.error(f"Error consultando wallets: {exc}")
            wallets = []
            _tabla_ok = False

        if not _tabla_ok:
            st.warning("⚠️ Módulo no inicializado. Aplica la migración 019.", icon="🛠️")
        elif not wallets:
            st.info("✅ Sistema listo. Registre la primera wallet para generar el análisis de riesgo.")
        else:
            st.caption(f"{len(wallets)} wallet{'s' if len(wallets) != 1 else ''} encontrada{'s' if len(wallets) != 1 else ''}")
            for w in wallets:
                _card_wallet(w)

    # ── Tab 3: Reporte Gerencial ──────────────────────────────
    with tab_gerencial:
        try:
            session = next(get_session())
            render_gerencial_crypto(session)
            session.close()
        except Exception as exc:
            st.error(f"Error cargando reporte gerencial: {exc}")

    # ── Tab 4: Vincular Wallet ────────────────────────────────
    with tab_wallet:
        _tab_vincular_wallet(user)
