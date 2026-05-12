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

from db.database import get_session
from db.repositories.crypto_repo import CryptoRepository, score_a_nivel_riesgo
from db.models import WalletMonitorCreate, RiskLabel, CryptoClienteCreate
from app.utils.crypto_logic import (
    calificar_labels, lookup_label, nivel_dominante,
    GL_ALL_LABELS_SORTED, GL_SCORES, calcular_score_sof_uof, score_gl_to_nivel,
)
from app.utils.crypto_parser import parse_gl_pdf, generate_weekly_delta

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

# ── Opciones de selectbox GL (228 indicadores, orden score desc) ─
_GL_OPTS_NONE   = "— Sin indicador —"
_GL_SELECTBOX   = [_GL_OPTS_NONE] + [
    f"{lbl}  (GL: {sc})" for lbl, sc in GL_ALL_LABELS_SORTED
]

def _parse_gl_opt(opt: str) -> Optional[str]:
    """Extrae el nombre del indicador de la opción formateada del selectbox."""
    if not opt or opt == _GL_OPTS_NONE:
        return None
    return opt.split("  (GL:")[0].strip()


def _find_gl_opt(entity: str) -> str:
    """Busca la opción del selectbox que corresponde a un nombre de entidad GL.

    Hace primero match exacto (case-insensitive) y luego match parcial.
    Devuelve _GL_OPTS_NONE si no hay coincidencia.
    """
    if not entity:
        return _GL_OPTS_NONE
    entity_lower = entity.lower().strip()
    # Exacto
    for opt in _GL_SELECTBOX:
        if opt == _GL_OPTS_NONE:
            continue
        if opt.split("  (GL:")[0].strip().lower() == entity_lower:
            return opt
    # Parcial
    for opt in _GL_SELECTBOX:
        if opt == _GL_OPTS_NONE:
            continue
        lbl = opt.split("  (GL:")[0].strip().lower()
        if entity_lower in lbl or lbl in entity_lower:
            return opt
    return _GL_OPTS_NONE


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


def _contam_bar(label: str, pct: float, color: str) -> str:
    """HTML progress bar para mostrar % de contaminación."""
    safe = min(max(float(pct or 0), 0.0), 100.0)
    return (
        f"<div style='margin-bottom:7px;'>"
        f"<div style='display:flex;justify-content:space-between;margin-bottom:2px;'>"
        f"<span style='color:#9ca3af;font-size:0.74rem;'>{label}</span>"
        f"<span style='color:{color};font-size:0.75rem;font-weight:700;'>{safe:.1f}%</span>"
        f"</div>"
        f"<div style='background:#1f2937;border-radius:3px;height:5px;'>"
        f"<div style='width:{safe}%;background:{color};height:100%;border-radius:3px;'></div>"
        f"</div>"
        f"</div>"
    )


def _render_flujo_block(wallet: dict, prefix: str, title: str) -> None:
    """Renderiza el bloque SoF o UoF dentro del tab de análisis."""
    indicador   = wallet.get(f"{prefix}_indicador")
    tipo_riesgo = wallet.get(f"{prefix}_tipo_riesgo") if prefix == "sof" else None
    naturaleza  = wallet.get(f"{prefix}_naturaleza") or "—"
    profundidad = wallet.get(f"{prefix}_profundidad")
    cont_dir    = float(wallet.get(f"{prefix}_cont_directa")   or 0)
    cont_ind    = float(wallet.get(f"{prefix}_cont_indirecta") or 0)
    cont_tot    = float(wallet.get(f"{prefix}_cont_total")     or 0)
    score_val   = wallet.get(f"{prefix}_score")
    nivel       = wallet.get(f"{prefix}_nivel") or "Sin Datos"
    monto       = wallet.get(f"{prefix}_monto")
    color       = _COLOR_NIVEL.get(nivel, "#6b7280")

    if not indicador:
        st.markdown(
            f"<div style='border:1px dashed #374151;border-radius:8px;padding:16px;"
            f"background:#0a0f1a;text-align:center;'>"
            f"<span style='color:#6b7280;font-size:0.83rem;'>Sin indicador registrado</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        return

    # Pre-compute conditional fragments (no backslashes in f-expressions)
    gl_ref     = GL_SCORES.get(indicador)
    gl_ref_tag = (
        f"<span style='color:#6b7280;font-size:0.71rem;margin-top:2px;display:block;'>"
        f"Ref. GL: {gl_ref}</span>"
    ) if gl_ref is not None else ""

    tipo_row = (
        f"<div style='background:#111827;border-radius:6px;padding:8px 10px;'>"
        f"<span style='color:#6b7280;font-size:0.71rem;'>TIPO DE RIESGO</span><br>"
        f"<span style='color:#d1d5db;font-size:0.82rem;'>{tipo_riesgo}</span>"
        f"</div>"
    ) if tipo_riesgo else ""

    score_txt = str(score_val) if score_val is not None else "—"
    monto_txt = f"${float(monto):,.2f}" if monto else "—"
    prof_txt  = str(profundidad) if profundidad is not None else "—"

    bars_html = (
        _contam_bar("Contaminación Directa",   cont_dir, "#f97316") +
        _contam_bar("Contaminación Indirecta",  cont_ind, "#f59e0b") +
        _contam_bar("Total Contaminación",      cont_tot, color)
    )

    nivel_pill = _pill(nivel, color)

    st.markdown(
        f"<div style='border:1px solid {color};border-radius:8px;padding:14px 16px;"
        f"background:#0a0f1a;'>"
        # Título + nivel
        f"<div style='display:flex;justify-content:space-between;align-items:center;"
        f"margin-bottom:12px;'>"
        f"<span style='color:{color};font-weight:700;font-size:0.88rem;'>{title}</span>"
        f"{nivel_pill}"
        f"</div>"
        # Indicador
        f"<div style='background:#111827;border-radius:6px;padding:8px 10px;margin-bottom:10px;'>"
        f"<span style='color:#6b7280;font-size:0.71rem;'>INDICADOR</span><br>"
        f"<span style='color:#e5e7eb;font-size:0.85rem;font-weight:600;'>{indicador}</span>"
        f"{gl_ref_tag}"
        f"</div>"
        # Tipo de riesgo (SoF only) + Naturaleza + Profundidad
        f"<div style='display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap;'>"
        f"{tipo_row}"
        f"<div style='flex:1;min-width:90px;background:#111827;border-radius:6px;padding:8px 10px;'>"
        f"<span style='color:#6b7280;font-size:0.71rem;'>NATURALEZA</span><br>"
        f"<span style='color:#d1d5db;font-size:0.82rem;'>{naturaleza}</span>"
        f"</div>"
        f"<div style='min-width:60px;background:#111827;border-radius:6px;padding:8px 10px;'>"
        f"<span style='color:#6b7280;font-size:0.71rem;'>PROF.</span><br>"
        f"<span style='color:#d1d5db;font-size:0.82rem;'>{prof_txt}</span>"
        f"</div>"
        f"</div>"
        # Barras de contaminación
        f"<div style='margin-bottom:10px;'>{bars_html}</div>"
        # Score + Monto
        f"<div style='display:flex;gap:8px;'>"
        f"<div style='flex:1;background:#111827;border-radius:6px;padding:8px 10px;'>"
        f"<span style='color:#6b7280;font-size:0.71rem;'>SCORE ANALÍTICO</span><br>"
        f"<span style='color:{color};font-size:1.15rem;font-weight:700;'>{score_txt}</span>"
        f"</div>"
        f"<div style='flex:1;background:#111827;border-radius:6px;padding:8px 10px;'>"
        f"<span style='color:#6b7280;font-size:0.71rem;'>MONTO</span><br>"
        f"<span style='color:#9ca3af;font-size:0.85rem;'>{monto_txt}</span>"
        f"</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
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
    score      = wallet.get("gl_score")
    labels     = _parse_labels(wallet.get("risk_labels"))
    chain      = wallet.get("blockchain", "ETH")
    chain_icon = _BLOCKCHAIN_ICONS.get(chain, "🔗")

    # Datos del análisis SoF/UoF
    final_risk_score = wallet.get("final_risk_score")
    final_risk_level = wallet.get("final_risk_level")
    sof_indicador    = wallet.get("sof_indicador")
    uof_indicador    = wallet.get("uof_indicador")
    has_analysis     = bool(sof_indicador or uof_indicador)

    # Nivel efectivo: preferir el dictaminado por el analista
    display_nivel = final_risk_level or nivel
    display_color = _COLOR_NIVEL.get(display_nivel, "#6b7280")

    # ── Cabecera: dirección + pills ───────────────────────────
    st.markdown(
        f"<h4 style='color:#f9fafb;margin-bottom:4px;'>"
        f"{chain_icon} <code style='color:#5fe9d0;font-size:0.85rem;'>"
        f"{wallet['wallet_address']}</code></h4>",
        unsafe_allow_html=True,
    )
    attn_pill = (
        "&nbsp;&nbsp;" + _pill("⚠️ ATENCIÓN PRIORITARIA", "#ef4444")
        if (score is not None and score < 30) or display_nivel == "Crítico" else ""
    )
    st.markdown(
        _pill(display_nivel, display_color) + "&nbsp;&nbsp;" +
        _pill(chain, "#5fe9d0") + attn_pill,
        unsafe_allow_html=True,
    )

    # ── Métricas de cabecera ──────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    if final_risk_score is not None and score is not None:
        delta_val = round(float(final_risk_score) - float(score), 1)
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric(
                "Final Risk Score",
                f"{float(final_risk_score):.0f} / 100",
                delta=f"{delta_val:+.1f} vs GL",
                delta_color="inverse",
                help="Score calculado por el analista. Delta positivo = riesgo agravado respecto al GL.",
            )
        with m2:
            st.metric("GL Score Original", str(score) if score is not None else "—")
        with m3:
            st.metric("Nivel Final", display_nivel)
        with m4:
            st.metric("Analista", wallet.get("monitoring_analyst") or "—")
    else:
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown("**GL Score**")
            st.markdown(_score_bar(score), unsafe_allow_html=True)
        with m2:
            exp      = wallet.get("total_exposure", 0) or 0
            currency = wallet.get("exposure_currency", "USD")
            st.metric("Exposición Total", f"${exp:,.2f} {currency}")
        with m3:
            st.metric("Cliente", wallet.get("client_nombre") or "—")

    st.markdown(
        "<hr style='border:none;border-top:1px solid #374151;margin:10px 0 16px 0;'>",
        unsafe_allow_html=True,
    )

    # ── Tabs ──────────────────────────────────────────────────
    tab_resumen, tab_sof_uof, tab_labels_t, tab_notas = st.tabs(
        ["📊 Resumen", "🔬 Análisis SoF/UoF", "🚩 Risk Labels", "📝 Notas & Reporte"]
    )

    # ── Tab: Resumen ──────────────────────────────────────────
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

    # ── Tab: Análisis SoF/UoF ─────────────────────────────────
    with tab_sof_uof:
        if not has_analysis:
            st.info(
                "Esta wallet aún no tiene un análisis SoF/UoF completado. "
                "Ve a **➕ Vincular Wallet** para registrar el monitoreo.",
                icon="📋",
            )
        else:
            col_sof, col_uof = st.columns(2)
            with col_sof:
                _render_flujo_block(wallet, "sof", "📤 Source of Funds (SoF)")
            with col_uof:
                _render_flujo_block(wallet, "uof", "📥 Use of Funds (UoF)")

            # ── Bitácora del Analista ─────────────────────────
            observations = wallet.get("analyst_observations") or ""
            analyst      = wallet.get("monitoring_analyst") or "—"
            frs          = wallet.get("final_risk_score")
            frl          = wallet.get("final_risk_level") or "—"
            frl_color    = _COLOR_NIVEL.get(frl, "#6b7280")
            frs_txt      = f"{float(frs):.0f}" if frs is not None else "—"
            obs_content  = (
                observations if observations
                else "<i style='color:#6b7280;'>Sin observaciones registradas.</i>"
            )
            frs_span = (
                f"<span style='color:#9ca3af;font-size:0.76rem;'>"
                f"🎯 Score Final: <b style='color:{frl_color};'>{frs_txt}</b></span>"
            )
            frl_span = (
                f"<span style='color:#9ca3af;font-size:0.76rem;'>"
                f"🏁 Nivel: <b style='color:{frl_color};'>{frl}</b></span>"
            )
            analyst_span = (
                f"<span style='color:#9ca3af;font-size:0.76rem;'>"
                f"👤 Analista: <b style='color:#e5e7eb;'>{analyst}</b></span>"
            )

            st.markdown(
                f"<div style='margin-top:16px;background:#0d1a0d;border:1px solid {frl_color};"
                f"border-radius:8px;padding:16px 18px;'>"
                f"<div style='color:{frl_color};font-size:0.8rem;font-weight:700;"
                f"letter-spacing:0.05em;margin-bottom:10px;'>📋 CONCLUSIÓN DEL ANALISTA</div>"
                f"<div style='color:#d1d5db;font-size:0.86rem;line-height:1.6;"
                f"background:#111827;border-radius:6px;padding:10px 14px;'>"
                f"{obs_content}</div>"
                f"<div style='margin-top:12px;display:flex;gap:20px;flex-wrap:wrap;"
                f"border-top:1px solid #1f2937;padding-top:10px;'>"
                f"{analyst_span}{frs_span}{frl_span}"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ── Tab: Risk Labels ─────────────────────────────────────
    with tab_labels_t:
        if not labels:
            st.info("Sin alertas registradas para esta wallet.")
        else:
            calificacion = calificar_labels(labels)
            nivel_f      = calificacion["nivel_final"]
            color_f      = _COLOR_NIVEL.get(nivel_f, "#6b7280")
            sof          = calificacion["sof_max_nivel"]
            uof          = calificacion["uof_max_nivel"]
            sof_color    = _COLOR_NIVEL.get(sof, "#6b7280")
            uof_color    = _COLOR_NIVEL.get(uof, "#6b7280")
            st.markdown(
                f"<div style='background:#1f2937;border-radius:8px;padding:10px 14px;"
                f"margin-bottom:12px;display:flex;gap:20px;flex-wrap:wrap;'>"
                f"<span style='color:#9ca3af;font-size:0.82rem;'>Catálogo: "
                f"<b style='color:{color_f};'>{nivel_f}</b></span>"
                f"<span style='color:#9ca3af;font-size:0.82rem;'>SoF máx: "
                f"<b style='color:{sof_color};'>{sof}</b></span>"
                f"<span style='color:#9ca3af;font-size:0.82rem;'>UoF máx: "
                f"<b style='color:{uof_color};'>{uof}</b></span>"
                f"<span style='color:#9ca3af;font-size:0.82rem;'>"
                f"Críticos: <b style='color:#ef4444;'>{calificacion['criticos_encontrados']}</b>"
                f" · Altos: <b style='color:#f97316;'>{calificacion['altos_encontrados']}</b>"
                f"</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            for ind in calificacion["indicadores"]:
                label_text = ind.get("label", "")
                label_es   = ind.get("label_es") or label_text
                nivel_ind  = ind.get("nivel")
                flag_color = _COLOR_NIVEL.get(nivel_ind, "#6b7280") if nivel_ind else "#6b7280"
                nivel_badge = nivel_ind or "Sin clasificar"
                pct        = float(ind.get("exposure_pct") or 0)
                source     = ind.get("source") or ""
                flujo      = " · ".join(ind.get("flujo") or [])
                desc       = ind.get("descripcion") or ""
                flag_icon  = (
                    "🔴" if nivel_ind == "Crítico" else
                    "🟠" if nivel_ind == "Alto" else
                    "🟡" if nivel_ind == "Medio" else "🟢"
                )
                pct_html    = f"<span style='color:#9ca3af;font-size:0.78rem;'>📊 {round(pct, 1)}%</span>" if pct else ""
                flujo_html  = f"<span style='color:#9ca3af;font-size:0.78rem;'>🏷️ {flujo}</span>" if flujo else ""
                source_html = f"<span style='color:#9ca3af;font-size:0.78rem;'>📌 {source}</span>" if source else ""
                desc_html   = f"<div style='color:#6b7280;font-size:0.75rem;margin-top:4px;'>{desc}</div>" if desc else ""
                st.markdown(
                    f"<div style='background:#1f2937;border-left:3px solid {flag_color};"
                    f"padding:10px 14px;border-radius:6px;margin-bottom:8px;'>"
                    f"<div style='display:flex;justify-content:space-between;align-items:flex-start;"
                    f"flex-wrap:wrap;gap:6px;'>"
                    f"<span style='color:{flag_color};font-weight:700;font-size:0.9rem;'>"
                    f"{flag_icon} {label_es}</span>"
                    f"<span style='color:#6b7280;font-size:0.75rem;font-style:italic;'>{label_text}</span>"
                    f"</div>"
                    f"<div style='display:flex;gap:14px;margin-top:6px;flex-wrap:wrap;'>"
                    f"<span style='color:{flag_color};font-size:0.78rem;font-weight:700;"
                    f"background:rgba(255,255,255,0.06);padding:2px 8px;border-radius:10px;'>"
                    f"{nivel_badge}</span>"
                    f"{pct_html}{flujo_html}{source_html}"
                    f"</div>"
                    f"{desc_html}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            if calificacion["sin_catalogo"]:
                st.caption(f"⚠️ Sin clasificar: {', '.join(calificacion['sin_catalogo'])}")

    # ── Tab: Notas & Reporte ──────────────────────────────────
    with tab_notas:
        notas        = wallet.get("notas") or ""
        pdf          = wallet.get("pdf_report_url") or ""
        weekly_delta = wallet.get("weekly_delta") or ""

        # Resumen evolutivo del ciclo semanal
        if weekly_delta:
            st.markdown(
                "<span style='color:#9ca3af;font-size:0.78rem;letter-spacing:0.05em;'>"
                "📈 EVOLUCIÓN SEMANAL</span>",
                unsafe_allow_html=True,
            )
            with st.chat_message("assistant"):
                st.markdown(weekly_delta)
            st.markdown("")

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

    # ── Modo vincular wallet (activado desde un cliente) ──────
    if st.session_state.get("show_vinculador"):
        cl_id_v   = st.session_state.get("vincular_cliente_id")
        cl_nom_v  = st.session_state.get("vincular_cliente_nombre", "—")
        col_title_v, col_cancel_v = st.columns([6, 1])
        with col_title_v:
            st.markdown(
                f"<h4 style='color:#86efac;margin-bottom:4px;'>"
                f"➕ Vincular Wallet &rarr; {cl_nom_v}</h4>",
                unsafe_allow_html=True,
            )
        with col_cancel_v:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✖ Cancelar", key="cancelar_vinculador"):
                st.session_state.pop("show_vinculador", None)
                st.session_state.pop("vincular_cliente_id", None)
                st.session_state.pop("vincular_cliente_nombre", None)
                st.rerun()
        _form_nueva_wallet(user, cl_id_v, cl_nom_v)
        st.markdown("---")

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
            total_wallets  = int(cl.get("total_wallets") or 0)
            exposure_total = float(cl.get("exposure_total") or 0)
            wallets_badge  = f"🔗 {total_wallets} wallet{'s' if total_wallets != 1 else ''}" if total_wallets > 0 else "Sin wallets"
            # Determinar color de riesgo de exposición
            if exposure_total >= 1_000_000:
                exp_color = "#ef4444"
            elif exposure_total >= 100_000:
                exp_color = "#f97316"
            else:
                exp_color = "#f59e0b"

            razon_social   = cl["razon_social"]
            nit_val        = cl.get("nit") or "—"
            rep_val        = cl.get("representante_legal") or "—"
            correo_val     = cl.get("correo_corporativo") or "—"
            exp_fmt        = f"${exposure_total:,.0f} USD"

            expander_label = f"🏢 {razon_social}  ·  {wallets_badge}  ·  💰 {exp_fmt}"
            with st.expander(expander_label, expanded=False):
                # Cabecera con info corporativa
                st.markdown(
                    f"<div style='background:#111827;border-radius:8px;padding:12px 16px;"
                    f"border:1px solid #374151;margin-bottom:12px;'>"
                    f"<div style='color:#9ca3af;font-size:0.82rem;'>"
                    f"<b style='color:#d1d5db;'>NIT:</b> {nit_val} &nbsp;&nbsp;"
                    f"<b style='color:#d1d5db;'>Rep. Legal:</b> {rep_val} &nbsp;&nbsp;"
                    f"<b style='color:#d1d5db;'>Correo:</b> {correo_val}"
                    f"</div>"
                    f"<div style='margin-top:8px;color:{exp_color};font-weight:700;font-size:1rem;'>"
                    f"💰 Exposición Total: {exp_fmt}"
                    f"</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                # Wallets vinculadas
                if total_wallets == 0:
                    st.caption("Sin wallets vinculadas. Ve a ➕ Vincular Wallet para agregar la primera.")
                else:
                    try:
                        w_session = next(get_session())
                        wallets_cl = CryptoRepository(w_session).get_wallets_by_cliente(cl["id"])
                        w_session.close()
                    except Exception:
                        wallets_cl = []
                    for w in wallets_cl:
                        nivel   = w.get("riesgo_nivel", "Sin Datos")
                        color   = _COLOR_NIVEL.get(nivel, "#6b7280")
                        score   = w.get("gl_score")
                        chain   = w.get("blockchain", "ETH")
                        icon    = _BLOCKCHAIN_ICONS.get(chain, "🔗")
                        w_exp   = float(w.get("total_exposure") or 0)
                        s_txt   = str(score) if score is not None else "N/A"
                        addr    = w["wallet_address"]
                        addr_sh = f"{addr[:16]}…{addr[-8:]}"
                        st.markdown(
                            f"<div style='background:#1f2937;border-left:3px solid {color};"
                            f"padding:8px 14px;border-radius:6px;margin-bottom:6px;"
                            f"display:flex;justify-content:space-between;'>"
                            f"<span style='color:#5fe9d0;font-size:0.78rem;font-family:monospace;'>"
                            f"{icon} {addr_sh}</span>"
                            f"<span style='color:{color};font-size:0.78rem;font-weight:700;'>{nivel}</span>"
                            f"<span style='color:#9ca3af;font-size:0.78rem;'>Score: {s_txt}</span>"
                            f"<span style='color:#9ca3af;font-size:0.78rem;'>${w_exp:,.0f} USD</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                # Botones de acción
                col_mon_b, col_vinc_b = st.columns(2)
                with col_mon_b:
                    if st.button("📋 Ver en Monitor", key=f"ver_mon_{cl['id']}", use_container_width=True):
                        st.session_state["crypto_cliente_filtro"] = cl["id"]
                        st.session_state["crypto_cliente_nombre"] = razon_social
                        st.rerun()
                with col_vinc_b:
                    if st.button("➕ Vincular Wallet", key=f"vincular_{cl['id']}", use_container_width=True):
                        st.session_state["show_vinculador"]       = True
                        st.session_state["vincular_cliente_id"]   = cl["id"]
                        st.session_state["vincular_cliente_nombre"] = razon_social
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


# ── Panel comparativo semana anterior ───────────────────────
def _render_comparativo(prev: dict, new_gl_score: Optional[int] = None,
                        new_cont_total: Optional[float] = None) -> None:
    """
    Muestra métricas de comparación entre el ciclo anterior y el actual.
    `prev` puede ser un registro de crypto_monitoreo o crypto_monitoreo_historial.
    `new_*` son los valores del formulario actual (None = aún no calculados).
    """
    prev_score   = prev.get("gl_score")
    prev_cont    = float(prev.get("sof_cont_total") or 0) + float(prev.get("uof_cont_total") or 0)
    prev_frs     = prev.get("final_risk_score")
    prev_nivel   = prev.get("final_risk_level") or prev.get("riesgo_nivel") or "Sin Datos"
    prev_color   = _COLOR_NIVEL.get(prev_nivel, "#6b7280")
    prev_analyst = prev.get("monitoring_analyst") or prev.get("registrado_por") or "—"

    # Fecha de la última actualización
    snap_date = prev.get("snapshot_date") or prev.get("updated_at") or prev.get("created_at")
    snap_label = str(snap_date)[:10] if snap_date else "—"

    st.markdown(
        f"<div style='background:#111827;border:1px solid #374151;border-radius:8px;"
        f"padding:12px 16px;margin-bottom:12px;'>"
        f"<div style='color:#6b7280;font-size:0.73rem;font-weight:700;"
        f"letter-spacing:0.06em;margin-bottom:8px;'>📅 SNAPSHOT ANTERIOR — {snap_label} "
        f"· Analista: {prev_analyst}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    m1, m2, m3, m4 = st.columns(4)

    # GL Score
    score_delta  = (new_gl_score - prev_score) if (new_gl_score is not None and prev_score is not None) else None
    score_label  = f"{prev_score}" if prev_score is not None else "—"
    with m1:
        st.metric(
            "GL Score anterior",
            score_label,
            delta=f"{score_delta:+d} esta semana" if score_delta is not None else None,
            delta_color="inverse",
            help="Delta positivo = riesgo creciente.",
        )

    # Contaminación total SoF+UoF
    prev_cont_fmt = f"{prev_cont:.2f}%"
    cont_delta    = round(new_cont_total - prev_cont, 2) if new_cont_total is not None else None
    with m2:
        st.metric(
            "% Contam. Total anterior",
            prev_cont_fmt,
            delta=f"{cont_delta:+.2f}% esta semana" if cont_delta is not None else None,
            delta_color="inverse",
        )

    # Final Risk Score anterior
    frs_fmt = f"{float(prev_frs):.0f}" if prev_frs is not None else "—"
    with m3:
        st.metric("Final Risk Score ant.", frs_fmt)

    # Nivel anterior
    with m4:
        st.metric("Nivel anterior", prev_nivel)

    # ── Alerta de degradación ─────────────────────────────
    alerts: list[str] = []
    if score_delta is not None and score_delta > 0:
        pct_deg = round((score_delta / max(prev_score, 1)) * 100, 1)
        alerts.append(
            f"📈 El GL Score **aumentó {score_delta} puntos** ({pct_deg:+.1f}%) respecto al último reporte."
        )
    if cont_delta is not None and cont_delta > 0:
        alerts.append(
            f"☣️ La contaminación total **creció {cont_delta:+.2f} pp** — revisa nuevas señales."
        )
    _NIVEL_PESO = {"Sin Datos": 0, "Bajo": 1, "Medio": 2, "Alto": 3, "Crítico": 4}
    if new_gl_score is not None and prev_score is not None:
        prev_lv = _COLOR_NIVEL.get(prev_nivel)  # just to reference
        new_nivel_est = score_gl_to_nivel(new_gl_score) if new_gl_score is not None else "Sin Datos"
        if _NIVEL_PESO.get(new_nivel_est, 0) > _NIVEL_PESO.get(prev_nivel, 0):
            alerts.append(
                f"🚨 El nivel de riesgo **escaló de {prev_nivel} → {new_nivel_est}**."
            )
    for alert in alerts:
        st.warning(alert)


# ── Formulario de primera vinculación (desde Clientes) ─────
def _form_nueva_wallet(user: dict, cliente_id: int, cliente_nombre: str) -> None:
    """
    Formulario para vincular una nueva wallet.
    El PDF de Global Ledger es la fuente de verdad principal.
    Los campos clave se bloquean y se rellenan automáticamente desde el reporte.
    """
    fk = str(cliente_id)

    chain_opts       = ["ETH", "BTC", "BNB", "TRX", "SOL", "MATIC", "Otro"]
    niveles          = ["Sin Datos", "Bajo", "Medio", "Alto", "Crítico"]
    status_opts      = ["Active", "Inactive", "Suspended", "Under Review"]
    tipo_riesgo_opts = ["Low", "Medium", "High", "Critical"]
    naturaleza_opts  = ["Directa", "Indirecta"]
    currency_opts    = ["USD", "EUR", "USDT", "USDC"]
    analyst_opts     = list(dict.fromkeys([
        user.get("nombre_completo") or user.get("username") or "Analista",
        "Adrian Cardona", "Jorge Jiménez",
    ]))

    def _infer_chain(addr: str) -> str:
        if addr.startswith("0x") and len(addr) == 42:
            return "ETH"
        if addr.startswith("bc1"):
            return "BTC"
        if addr and addr[0] in ("1", "3") and 25 <= len(addr) <= 34:
            return "BTC"
        if addr.startswith("T") and len(addr) == 34:
            return "TRX"
        if len(addr) == 44:
            return "SOL"
        return "ETH"

    def _score_to_nivel_local(s: int) -> str:
        if s < 20: return "Crítico"
        if s < 40: return "Alto"
        if s < 70: return "Medio"
        return "Bajo"

    # ── Session-state keys ────────────────────────────────────────────────────
    _gl_key      = f"nw_gl_data_{fk}"
    _uploader_k  = f"pdf_nw_{fk}"
    _active_k    = f"_nw_pdf_active_{fk}"

    # ── PASO 0: Cargar PDF (fuente de verdad) ─────────────────────────────────
    st.markdown(
        "<div style='background:#0f172a;border-left:4px solid #22d3ee;"
        "padding:10px 16px;border-radius:6px;margin-bottom:12px;'>"
        "<b style='color:#67e8f9;'>📎 PASO 0 — Reporte Global Ledger PDF</b>"
        "<span style='color:#94a3b8;font-size:0.8rem;margin-left:8px;'>"
        "El PDF es la fuente de verdad. Los campos clave se extraen automáticamente.</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    pdf_nw = st.file_uploader(
        "Seleccionar PDF de Global Ledger",
        type=["pdf"],
        key=_uploader_k,
        help="Carga el reporte GL para autocompletar todos los campos.",
    )

    _gl: dict = {}
    _from_pdf = False

    if pdf_nw:
        _cache_key = f"_nw_pdf_c_{fk}_{pdf_nw.name}_{pdf_nw.size}"
        if _cache_key not in st.session_state:
            with st.spinner("🔍 Analizando reporte GL…"):
                st.session_state[_cache_key] = parse_gl_pdf(pdf_nw.getvalue())
            st.session_state[_gl_key]    = st.session_state[_cache_key]
            st.session_state[_active_k]  = _cache_key
        _gl       = st.session_state.get(_gl_key, {})
        _from_pdf = _gl.get("ok", False)

        if _gl.get("ok"):
            _w       = _gl.get("wallet_detected") or ""
            _sc      = _gl.get("gl_score_detected")
            _tot     = _gl.get("total_rows", 0)
            _hi      = _gl.get("high_risk_count", 0)
            _med     = _gl.get("medium_risk_count", 0)
            _pdf_sof_snap = _gl.get("sof_top")
            _dir_pct = float(_pdf_sof_snap["direct_pct"]) if _pdf_sof_snap else 0.0

            if not _w:
                st.warning(
                    "⚠️ **El reporte no coincide con los parámetros de seguridad.** "
                    "No se detectó ninguna dirección de wallet en el PDF. "
                    "Verifique que el documento corresponde a este cliente.",
                    icon="🔒",
                )
                _from_pdf = False
            else:
                st.success(f"✅ Reporte analizado · `{pdf_nw.name}` ({pdf_nw.size // 1024} KB)")
                # Foto Actual
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("📊 Total Txs", f"{_tot:,}")
                c2.metric("🔴 Alto Riesgo", f"{_hi:,}")
                c3.metric("🟡 Medio Riesgo", f"{_med:,}")
                c4.metric("🎯 GL Score", _sc if _sc is not None else "—")
                st.info(
                    f"📸 **Foto Actual de la Wallet:** Se detectaron **{_tot:,} transacciones** "
                    f"con una exposición directa inicial de **{_dir_pct:.4f}%** "
                    f"(SoF: `{_pdf_sof_snap['entity'] if _pdf_sof_snap else '—'}`)."
                )
        elif _gl.get("error"):
            st.warning(f"⚠️ Parser GL: {_gl['error']}", icon="📄")
    else:
        # Limpiar datos de parseo cuando se quita el PDF
        if _active_k in st.session_state:
            _stale = st.session_state.pop(_active_k)
            st.session_state.pop(_stale, None)
        st.session_state.pop(_gl_key, None)

    st.markdown("---")

    # ── JSON como alternativa (colapsado) ─────────────────────────────────────
    if not _from_pdf:
        with st.expander("{ } Pegar JSON GL (alternativa al PDF)", expanded=False):
            gl_raw_pre = st.text_area(
                "Reporte GL (JSON)",
                height=70,
                placeholder='{"address":"TAHQWz...","score":47}',
                key=f"gl_raw_nueva_{fk}",
            )
            if st.button("🔍 Extraer campos", key=f"parse_gl_nueva_{fk}"):
                if gl_raw_pre.strip():
                    st.session_state[f"gl_parsed_json_{fk}"] = _parse_gl_report(gl_raw_pre)
                    st.rerun()

    _parsed_json = (
        st.session_state.get(f"gl_parsed_json_{fk}", {}) if not _from_pdf else {}
    )
    _src = _gl if _from_pdf else _parsed_json

    # ── Valores derivados del parser ──────────────────────────────────────────
    _pdf_wallet = _gl.get("wallet_detected") or "" if _from_pdf else ""
    _pdf_score  = _gl.get("gl_score_detected")     if _from_pdf else None
    _pdf_sof    = _gl.get("sof_top")               if _from_pdf else None
    _pdf_uof    = _gl.get("uof_top")               if _from_pdf else None
    _pdf_tots   = _gl.get("total_rows", 0)          if _from_pdf else 0

    init_addr   = _pdf_wallet or _src.get("wallet_address") or ""
    init_chain  = (
        _infer_chain(_pdf_wallet) if (_from_pdf and _pdf_wallet)
        else _src.get("blockchain") or "ETH"
    )
    init_score  = _pdf_score if _pdf_score is not None else _src.get("gl_score")
    init_nivel  = (
        _score_to_nivel_local(_pdf_score) if _pdf_score is not None
        else _src.get("riesgo_nivel") or "Sin Datos"
    )
    init_labels = json.dumps(_src.get("risk_labels") or [], ensure_ascii=False)

    chain_idx = chain_opts.index(init_chain) if init_chain in chain_opts else 0
    nivel_idx = niveles.index(init_nivel) if init_nivel in niveles else 0

    # Pre-llenar session_state para SoF/UoF — guardados en _gl para la lógica de submit
    # (no se usan widgets de form para SoF/UoF; se calculan directamente desde risk_exposure_list)

    # Bloquear si PDF inválido (cargado pero sin wallet detectada)
    if _from_pdf is False and pdf_nw and _gl.get("ok"):
        # ok=True pero wallet not found → ya mostramos warning arriba, no renderizar form
        return

    # ── GL-Score Hero Component ───────────────────────────────────────────────
    if _from_pdf and _pdf_score is not None:
        _s = _pdf_score
        if _s <= 30:
            _bg, _border, _fg, _lbl = "#D1FAE5", "#10B981", "#065F46", "LOW RISK"
        elif _s <= 60:
            _bg, _border, _fg, _lbl = "#FFF3E0", "#FF9800", "#E65100", "MEDIUM RISK"
        else:
            _bg, _border, _fg, _lbl = "#FEE2E2", "#EF4444", "#7F1D1D", "HIGH RISK"
        st.markdown(
            f"<div style='background-color:{_bg};border-radius:15px;padding:20px;"
            f"text-align:center;border:2px solid {_border};margin-bottom:16px;'>"
            f"<h1 style='color:{_fg};margin:0;font-size:56px;font-weight:900;'>{_s}</h1>"
            f"<p style='color:{_fg};font-weight:bold;margin:4px 0 0;font-size:1.1rem;'>"
            f"{_lbl}</p>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Métricas globales SoF / UoF ───────────────────────────────────────────
    _risk_expo      = _gl.get("risk_exposure_list", []) if _from_pdf else []
    _residual_count = _gl.get("residual_count", 0)      if _from_pdf else 0
    _sof_pct        = _gl.get("sof_total_pct", 0.0)     if _from_pdf else 0.0
    _uof_pct        = _gl.get("uof_total_pct", 0.0)     if _from_pdf else 0.0
    _sof_amt        = _gl.get("sof_total_amount", 0.0)  if _from_pdf else 0.0
    _uof_amt        = _gl.get("uof_total_amount", 0.0)  if _from_pdf else 0.0

    # Separar listas por tipo antes de renderizar
    _sof_rows = [r for r in _risk_expo if r.get("type") == "SoF"]
    _uof_rows = [r for r in _risk_expo if r.get("type") == "UoF"]

    if _from_pdf and (_sof_pct > 0 or _uof_pct > 0):
        _mc1, _mc2 = st.columns(2)
        with _mc1:
            # Mostrar % como valor principal; monto como delta si existe
            _sof_main  = f"{_sof_pct:.4f}% exposición"
            _sof_delta = f"$ {_sof_amt:,.2f}" if _sof_amt > 0 else None
            st.metric(
                "📥 Total SoF Analizado",
                _sof_main,
                delta=_sof_delta,
                delta_color="off",
            )
        with _mc2:
            _uof_main  = f"{_uof_pct:.4f}% exposición"
            _uof_delta = f"$ {_uof_amt:,.2f}" if _uof_amt > 0 else None
            st.metric(
                "📤 Total UoF Analizado",
                _uof_main,
                delta=_uof_delta,
                delta_color="off",
            )

    def _render_exposure_table(rows: list[dict], title: str, color: str) -> None:
        """Renderiza una tabla de Risk Exposure para SoF o UoF."""
        import pandas as _pd  # noqa: PLC0415
        st.markdown(
            f"<div style='background:#0f172a;border-left:4px solid {color};"
            f"padding:10px 16px;border-radius:6px;margin-bottom:8px;'>"
            f"<b style='color:#fcd34d;'>{title}</b>"
            f"<span style='color:#94a3b8;font-size:0.78rem;margin-left:8px;'>"
            f"HIGH siempre visible · MEDIUM/LOW ≥ 5%</span></div>",
            unsafe_allow_html=True,
        )
        if not rows:
            st.caption("Sin indicadores para este tipo de flujo.")
            return
        _level_colors = {
            "CRITICAL": "🔴", "HIGH": "🔴", "MEDIUM": "🟡",
            "LOW": "🟢", "UNKNOWN": "⚪",
        }
        _df = _pd.DataFrame(rows)[["label", "level", "amount", "percentage"]]
        _df = _df.rename(columns={
            "label":      "Risk Label",
            "level":      "Risk Level",
            "amount":     "Monto (USD)",
            "percentage": "% Exposición",
        })
        _df["Risk Level"] = _df["Risk Level"].map(
            lambda v: f"{_level_colors.get(v, '⚪')} {v}"
        )
        # Monto: reemplazar 0.0 por None para que no muestre "$ 0.00"
        _df["Monto (USD)"] = _df["Monto (USD)"].apply(
            lambda v: v if v > 0 else None
        )
        st.dataframe(
            _df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Risk Label":   st.column_config.TextColumn(width="large"),
                "Risk Level":   st.column_config.TextColumn(width="medium"),
                "Monto (USD)":  st.column_config.NumberColumn(
                    format="$ %.2f", width="small",
                ),
                "% Exposición": st.column_config.NumberColumn(
                    format="%.4f%%", width="small",
                ),
            },
        )

    # ── Risk Exposure: dos tablas lado a lado ─────────────────────────────────
    if _risk_expo:
        _tc1, _tc2 = st.columns(2, gap="medium")
        with _tc1:
            _render_exposure_table(_sof_rows, "📥 Source of Funds (SoF)", "#93c5fd")
        with _tc2:
            _render_exposure_table(_uof_rows, "📤 Use of Funds (UoF)", "#86efac")

        # ── Nota de Cumplimiento ──────────────────────────────────────────────
        _high_shown = sum(
            1 for r in _risk_expo if r["level"] in ("CRITICAL", "HIGH")
        )
        _note_parts = []
        if _residual_count > 0:
            _note_parts.append(
                f"Se han detectado **{_residual_count}** indicador(es) adicional(es) "
                f"de riesgo Medio/Bajo con exposición < 5% (omitidos por política de "
                f"relevancia analítica)."
            )
        if _high_shown > 0:
            _note_parts.append(
                f"Todos los **{_high_shown}** indicador(es) de riesgo **ALTO / CRÍTICO** "
                f"han sido detallados independientemente de su porcentaje de exposición."
            )
        if _note_parts:
            st.info("📋 **Nota de Cumplimiento:** " + " ".join(_note_parts))
    else:
        st.info(
            "📄 Cargue un reporte PDF para visualizar la exposición.",
            icon="📊",
        )


    st.markdown("---")

    # ── Header del formulario ─────────────────────────────────────────────────
    _lbl_btn = "✅ Confirmar y Vincular Wallet" if _from_pdf else "💾 Vincular Wallet"
    st.markdown(
        "<div style='background:#0f172a;border-left:4px solid #6366f1;"
        "padding:10px 16px;border-radius:6px;margin-bottom:12px;'>"
        "<b style='color:#a5b4fc;'>📋 Datos de Vinculación</b>"
        f"<span style='color:#94a3b8;font-size:0.8rem;margin-left:8px;'>"
        f"{'Campos clave bloqueados — extraídos del PDF.' if _from_pdf else 'Ingreso manual.'}"
        "</span></div>",
        unsafe_allow_html=True,
    )

    with st.form(f"form_nueva_wallet_{fk}", clear_on_submit=True):
        col_wa, col_chain, col_status = st.columns([4, 1, 1])
        with col_wa:
            wallet_address = st.text_input(
                "💳 Dirección de Wallet *",
                value=init_addr,
                disabled=_from_pdf,
                placeholder="0x... · T... · bc1q...",
            )
        with col_chain:
            if _from_pdf:
                blockchain = st.text_input("Blockchain", value=init_chain, disabled=True)
            else:
                blockchain = st.selectbox("Blockchain", chain_opts, index=chain_idx)
        with col_status:
            wallet_status = st.selectbox("Estado", status_opts)

        col_sc, col_nv, col_an, col_fecha = st.columns(4)
        with col_sc:
            gl_score_val = st.number_input(
                "🎯 GL Score",
                min_value=0, max_value=100,
                value=init_score, placeholder="Ej: 47",
                disabled=(_from_pdf and _pdf_score is not None),
            )
        with col_nv:
            if _from_pdf and _pdf_score is not None:
                riesgo_manual = st.text_input("Nivel GL", value=init_nivel, disabled=True)
            else:
                riesgo_manual = st.selectbox("Nivel GL", niveles, index=nivel_idx)
        with col_an:
            monitoring_analyst = st.selectbox("👤 Analista", analyst_opts)
        with col_fecha:
            report_date = st.date_input("📅 Fecha Reporte", value=None)

        st.markdown("---")
        col_exp, col_cur, col_url = st.columns(3)
        with col_exp:
            exposure = st.number_input(
                "💰 Exposición Total", min_value=0.0, value=0.0, step=1000.0,
            )
        with col_cur:
            exposure_currency = st.selectbox("Moneda", currency_opts)
        with col_url:
            pdf_url = st.text_input("📄 URL Reporte PDF", placeholder="https://...")

        analyst_observations = st.text_area(
            "📝 Observaciones", height=80,
            placeholder="Ej: Wallet corporativa, bajo riesgo inicial.",
        )
        notas = st.text_area("Notas internas", height=60)

        submitted = st.form_submit_button(
            _lbl_btn, type="primary", use_container_width=True,
        )

    if submitted:
        if not wallet_address.strip():
            st.error("La dirección de wallet es obligatoria.")
            return

        # ── Calcular SoF / UoF desde risk_exposure_list (PDF) ──────────────
        risk_labels: list = []
        _sof_indicador = _uof_indicador = None
        _sof_direct = _sof_indirect = _uof_direct = _uof_indirect = 0.0
        _sof_profundidad = _uof_profundidad = 1
        _sof_naturaleza = _uof_naturaleza = "Directa"
        _sof_tipo = "Medium"

        if _from_pdf and _risk_expo:
            _sof_rows = [r for r in _risk_expo if r["type"] == "SoF"]
            _uof_rows = [r for r in _risk_expo if r["type"] == "UoF"]
            if _sof_rows:
                _best_sof = max(_sof_rows, key=lambda r: r["percentage"])
                _sof_indicador  = _parse_gl_opt(_find_gl_opt(_best_sof["label"]))
                _sof_direct     = float(_best_sof["percentage"])
                _sof_indirect   = 0.0
                _sof_profundidad = int(_pdf_sof.get("depth", 1)) if _pdf_sof else 1
                _lvl_raw         = _best_sof.get("level", "")
                _sof_tipo = (
                    "Critical" if _lvl_raw == "CRITICAL" else
                    "High"     if _lvl_raw == "HIGH"     else
                    "Medium"   if _lvl_raw == "MEDIUM"   else "Low"
                )
            if _uof_rows:
                _best_uof = max(_uof_rows, key=lambda r: r["percentage"])
                _uof_indicador  = _parse_gl_opt(_find_gl_opt(_best_uof["label"]))
                _uof_direct     = float(_best_uof["percentage"])
                _uof_indirect   = 0.0
                _uof_profundidad = int(_pdf_uof.get("depth", 1)) if _pdf_uof else 1
        elif _pdf_sof:
            _sof_indicador  = _parse_gl_opt(_find_gl_opt(_pdf_sof["entity"]))
            _sof_direct     = float(_pdf_sof.get("direct_pct", 0))
            _sof_indirect   = float(_pdf_sof.get("indirect_pct", 0))
            _sof_profundidad = int(_pdf_sof.get("depth", 1))
            if _pdf_uof:
                _uof_indicador  = _parse_gl_opt(_find_gl_opt(_pdf_uof["entity"]))
                _uof_direct     = float(_pdf_uof.get("direct_pct", 0))
                _uof_indirect   = float(_pdf_uof.get("indirect_pct", 0))
                _uof_profundidad = int(_pdf_uof.get("depth", 1))

        sof_ind_score  = GL_SCORES.get(_sof_indicador, 50) if _sof_indicador else 50
        sof_total_pct  = _sof_direct + _sof_indirect
        sof_score_calc = round((sof_total_pct / 100.0) * sof_ind_score)
        sof_nivel_calc = score_gl_to_nivel(sof_score_calc)

        uof_ind_score  = GL_SCORES.get(_uof_indicador, 50) if _uof_indicador else 50
        uof_total_pct  = _uof_direct + _uof_indirect
        uof_score_calc = round((uof_total_pct / 100.0) * uof_ind_score)
        uof_nivel_calc = score_gl_to_nivel(uof_score_calc)

        is_critico_locked = (sof_ind_score == 100 or uof_ind_score == 100)
        if _sof_indicador and _uof_indicador:
            final_risk_score_calc = (sof_score_calc + uof_score_calc) / 2.0
        elif _sof_indicador:
            final_risk_score_calc = float(sof_score_calc)
        elif _uof_indicador:
            final_risk_score_calc = float(uof_score_calc)
        else:
            final_risk_score_calc = None

        if is_critico_locked:
            final_risk_level_calc = "Crítico"
        elif final_risk_score_calc is not None:
            final_risk_level_calc = score_gl_to_nivel(round(final_risk_score_calc))
        else:
            final_risk_level_calc = riesgo_manual

        gl_score_int   = int(gl_score_val) if gl_score_val is not None else None
        calificacion   = calificar_labels([])
        nivel_catalogo = calificacion["nivel_final"]
        nivel_base     = riesgo_manual
        if nivel_base == "Sin Datos" and gl_score_int is not None:
            nivel_base = score_a_nivel_riesgo(gl_score_int)
        nivel_gl = nivel_dominante(nivel_catalogo, nivel_base)
        if gl_score_int is not None and gl_score_int < 30:
            nivel_gl = "Crítico"
        riesgo_nivel_final = nivel_dominante(nivel_gl, final_risk_level_calc)

        if is_critico_locked:
            st.error(
                "🚨 Indicador de alto riesgo detectado. "
                "Calificación bloqueada en **CRÍTICO** según política AdamoServices."
            )

        payload = WalletMonitorCreate(
            wallet_address        = wallet_address.strip(),
            blockchain            = blockchain,
            crypto_cliente_id     = cliente_id,
            client_nombre         = cliente_nombre,
            gl_score              = gl_score_int,
            riesgo_nivel          = riesgo_nivel_final,
            risk_labels           = risk_labels,
            total_exposure        = float(exposure),
            exposure_currency     = exposure_currency,
            wallet_status         = wallet_status,
            sof_tipo_riesgo       = _sof_tipo,
            sof_indicador         = _sof_indicador,
            sof_naturaleza        = _sof_naturaleza,
            sof_profundidad       = _sof_profundidad,
            sof_cont_directa      = _sof_direct,
            sof_cont_indirecta    = _sof_indirect,
            sof_cont_total        = sof_total_pct,
            sof_score             = sof_score_calc,
            sof_nivel             = sof_nivel_calc,
            sof_monto             = None,
            uof_indicador         = _uof_indicador,
            uof_naturaleza        = _uof_naturaleza,
            uof_profundidad       = _uof_profundidad,
            uof_cont_directa      = _uof_direct,
            uof_cont_indirecta    = _uof_indirect,
            uof_cont_total        = uof_total_pct,
            uof_score             = uof_score_calc,
            uof_nivel             = uof_nivel_calc,
            uof_monto             = None,
            analyst_observations  = analyst_observations.strip() or None,
            monitoring_analyst    = monitoring_analyst,
            final_risk_score      = final_risk_score_calc,
            final_risk_level      = final_risk_level_calc,
            pdf_report_url        = pdf_url.strip() or None,
            last_report_date      = datetime.combine(report_date, datetime.min.time()) if report_date else None,
            registrado_por        = user.get("username"),
            notas                 = notas.strip() or None,
        )

        try:
            session = next(get_session())
            CryptoRepository(session).create_wallet(payload)
            session.close()
            _get_wallets_cached.clear()
            _get_clientes_cached.clear()
            # Limpiar TODOS los estados del vinculador para que el rerun
            # muestre al usuario la vista de clientes limpia y la wallet
            # nueva ya disponible en el Monitor.
            _keys_to_clear = (
                "show_vinculador", "vincular_cliente_id",
                "vincular_cliente_nombre",
                f"gl_parsed_nueva_{fk}", f"gl_parsed_json_{fk}",
                f"nw_gl_data_{fk}",
            )
            for _k in _keys_to_clear:
                st.session_state.pop(_k, None)
            # Limpiar cache activo del PDF
            _active_key_ref = f"_nw_pdf_active_{fk}"
            if _active_key_ref in st.session_state:
                _stale = st.session_state.pop(_active_key_ref)
                st.session_state.pop(_stale, None)
            short_addr = wallet_address.strip()[:16]
            st.toast(
                f"✅ Wallet {short_addr}… vinculada a {cliente_nombre}.",
                icon="🔗",
            )
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Error al crear wallet: {exc}")


# ── Parser de reporte Global Ledger ─────────────────────────
def _parse_gl_report(texto: str) -> dict:
    """
    Extrae campos clave de un texto/JSON pegado desde Global Ledger.
    Retorna dict con claves: wallet_address, blockchain, gl_score,
    riesgo_nivel, total_exposure, risk_labels (lista de dicts).
    Los campos no encontrados quedan en None o [].
    """
    import re

    result: dict = {
        "wallet_address": None,
        "blockchain":     None,
        "gl_score":       None,
        "riesgo_nivel":   None,
        "total_exposure": None,
        "risk_labels":    [],
    }

    # ── Intentar parseo JSON primero ──────────────────────────
    stripped = texto.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            result["wallet_address"] = (
                data.get("address") or data.get("wallet_address") or data.get("wallet")
            )
            result["blockchain"] = (
                data.get("blockchain") or data.get("chain") or data.get("network")
            )
            score_raw = data.get("score") or data.get("gl_score") or data.get("risk_score")
            if score_raw is not None:
                result["gl_score"] = int(float(score_raw))
            exp_raw = (
                data.get("total_exposure") or data.get("exposure") or
                data.get("totalExposure") or data.get("volume")
            )
            if exp_raw is not None:
                result["total_exposure"] = float(str(exp_raw).replace(",", ""))
            risk_raw = data.get("labels") or data.get("risk_labels") or data.get("riskLabels") or []
            if isinstance(risk_raw, list):
                for item in risk_raw:
                    if isinstance(item, dict):
                        result["risk_labels"].append({
                            "label":        item.get("name") or item.get("label") or "",
                            "exposure_pct": float(item.get("exposure_pct") or item.get("exposurePct") or 0),
                            "source":       item.get("source") or "",
                        })
                    elif isinstance(item, str):
                        result["risk_labels"].append({"label": item, "exposure_pct": 0.0, "source": ""})
        except Exception:
            pass  # Fallback a regex

    # ── Regex sobre texto plano (cubre PDFs copiados) ─────────
    # Wallet address — TRX (34 chars base58), ETH (0x...), BTC (bc1/1/3...)
    if not result["wallet_address"]:
        m = re.search(r'\b(T[A-HJ-NP-Za-km-z1-9]{33})\b', texto)  # TRX
        if not m:
            m = re.search(r'\b(0x[0-9a-fA-F]{40})\b', texto)       # ETH/BNB
        if not m:
            m = re.search(r'\b(bc1[a-zA-HJ-NP-Z0-9]{6,87})\b', texto)  # BTC bech32
        if m:
            result["wallet_address"] = m.group(1)

    # Blockchain
    if not result["blockchain"]:
        bc_map = {
            r'\bTRON\b|\bTRX\b': "TRX",
            r'\bEthereum\b|\bETH\b': "ETH",
            r'\bBitcoin\b|\bBTC\b': "BTC",
            r'\bBNB\b|\bBinance Smart Chain\b|\bBSC\b': "BNB",
            r'\bSolana\b|\bSOL\b': "SOL",
            r'\bPolygon\b|\bMATIC\b': "MATIC",
        }
        for pattern, chain in bc_map.items():
            if re.search(pattern, texto, re.IGNORECASE):
                result["blockchain"] = chain
                break

    # Score — busca "Score: 47", "GL Score 47", "Risk Score: 47"
    if result["gl_score"] is None:
        m = re.search(r'(?:gl[- ]?score|risk[- ]?score|score)[:\s]+(\d{1,3})', texto, re.IGNORECASE)
        if m:
            result["gl_score"] = int(m.group(1))

    # Nivel de riesgo — HIGH, MEDIUM, LOW, CRITICAL
    if not result["riesgo_nivel"]:
        nivel_map = {
            r'\bCRITICAL\b|\bCRITICO\b': "Crítico",
            r'\bHIGH\b|\bALTO\b': "Alto",
            r'\bMEDIUM\b|\bMODERATE\b|\bMEDIO\b': "Medio",
            r'\bLOW\b|\bBAJO\b': "Bajo",
        }
        for pattern, nivel in nivel_map.items():
            if re.search(pattern, texto, re.IGNORECASE):
                result["riesgo_nivel"] = nivel
                break

    # Exposure total — busca "2,340,897.66 USD" o "Total Exposure: 2340897.66"
    if result["total_exposure"] is None:
        m = re.search(
            r'(?:total[_ ]?exposure|exposure|volume)[:\s]+\$?([\d,]+\.?\d*)',
            texto, re.IGNORECASE,
        )
        if not m:
            # Formato numérico grande standalone con USD nearby
            m = re.search(r'\$?([\d]{1,3}(?:,\d{3})+(?:\.\d+)?)\s*USD', texto, re.IGNORECASE)
        if m:
            result["total_exposure"] = float(m.group(1).replace(",", ""))

    # Risk labels en texto libre — busca nombres conocidos
    if not result["risk_labels"]:
        known_labels = [
            "Sanctioned Exchange", "OFAC Sanctioned", "Blacklisted Wallet",
            "High-Risk Exchange", "Darknet Market", "Ransomware",
            "Scam", "Terrorism Financing", "Mixer", "Child Abuse Material",
        ]
        found = []
        for lbl in known_labels:
            if lbl.lower() in texto.lower():
                found.append({"label": lbl, "exposure_pct": 0.0, "source": ""})
        result["risk_labels"] = found

    # Política interna: score < 30 → CRÍTICO siempre
    if result["gl_score"] is not None and result["gl_score"] < 30:
        result["riesgo_nivel"] = "Crítico"

    return result


# ── Tab Monitoreo Semanal ─────────────────────────────────────
def _tab_monitoreo_semanal(user: dict) -> None:
    """
    Seguimiento semanal de wallets ya existentes.
    Selecciona una wallet, revisa el comparativo con el ciclo anterior
    y actualiza las métricas con archivado automático en historial.
    """
    st.markdown("### 📈 Monitoreo Semanal")

    all_wallets = _get_wallets_cached(
        riesgo_nivel=None, blockchain=None,
        solo_criticos=False, search_text=None,
    )

    if not all_wallets:
        st.info(
            "✅ No hay wallets registradas aún. "
            "Ve a **👥 Clientes** para vincular la primera wallet."
        )
        return

    # Selectbox de wallets activas
    _NONE_OPT = "— Seleccionar wallet —"
    wallet_opts = [_NONE_OPT]
    wallet_map: dict = {}
    for w in all_wallets:
        client = w.get("client_nombre") or "Sin cliente"
        addr   = w["wallet_address"]
        chain  = w.get("blockchain") or "?"
        nivel  = w.get("riesgo_nivel") or "Sin Datos"
        nivel_icon = (
            "🔴" if nivel == "Crítico" else
            "🟠" if nivel == "Alto" else
            "🟡" if nivel == "Medio" else
            "🟢" if nivel == "Bajo" else "⚫"
        )
        short = addr[:12] + "…" + addr[-6:]
        label = f"{client}  |  {short}  •  {chain}  {nivel_icon} {nivel}"
        wallet_opts.append(label)
        wallet_map[label] = w

    sel_label = st.selectbox(
        "🔍 Wallet a Monitorear",
        wallet_opts,
        key="mon_wallet_sel",
    )

    if sel_label == _NONE_OPT:
        st.info("Selecciona una wallet del listado para iniciar el ciclo de monitoreo.")
        return

    selected       = wallet_map[sel_label]
    wallet_addr    = selected["wallet_address"]
    cliente_nombre = selected.get("client_nombre") or "—"

    # Cargar registro completo fresco (sin caché)
    try:
        _s = next(get_session())
        current_record = CryptoRepository(_s).get_by_address(wallet_addr)
        _s.close()
    except Exception as exc:
        st.error(f"Error cargando wallet: {exc}")
        return

    if not current_record:
        st.error("Wallet no encontrada en la base de datos.")
        return

    # Cargar snapshot previo del historial (cacheado por sesión)
    _snap_key = f"_mon_prev_snap_{wallet_addr}"
    if _snap_key not in st.session_state:
        try:
            _ss = next(get_session())
            st.session_state[_snap_key] = CryptoRepository(_ss).get_previous_snapshot(wallet_addr)
            _ss.close()
        except Exception:
            st.session_state[_snap_key] = None
    _prev_snapshot = st.session_state.get(_snap_key)

    # Mostrar estado actual como "ciclo anterior a archivar"
    label_actual = "📊 Estado Actual (se archivará al guardar)"
    st.markdown(
        f"<div style='background:#0f172a;border-left:4px solid #f59e0b;"
        f"padding:10px 16px;border-radius:6px;margin-bottom:8px;'>"
        f"<b style='color:#fde68a;'>{label_actual}</b></div>",
        unsafe_allow_html=True,
    )
    _render_comparativo(current_record)
    st.markdown("---")

    # ═══════════════════════════════════════════════════════
    # PASO 1: PDF + Delta (fuera del form)
    # ═══════════════════════════════════════════════════════
    step1_label = "📂 Paso 1 — Evidencia del Ciclo"
    st.markdown(
        f"<div style='background:#0f172a;border-left:4px solid #3b82f6;"
        f"padding:10px 16px;border-radius:6px;margin-bottom:12px;'>"
        f"<b style='color:#93c5fd;'>{step1_label}</b></div>",
        unsafe_allow_html=True,
    )
    # Key dinámica por wallet — fuerza un uploader limpio al cambiar wallet
    _uploader_key = f"pdf_mon_{wallet_addr}"
    _active_key   = f"mon_pdf_active_{wallet_addr}"

    col_pdf_up, col_delta = st.columns([1, 2])
    with col_pdf_up:
        pdf_file = st.file_uploader(
            "📎 Cargar Reporte PDF", type=["pdf"],
            key=_uploader_key,
        )
        if pdf_file:
            kb = pdf_file.size // 1024
            st.caption(f"✅ `{pdf_file.name}`  ({kb} KB)")
            # ── Auto-parseo (cacheado por wallet+nombre+tamaño) ──
            _pdf_key = f"mon_pdf_parsed_{wallet_addr}_{pdf_file.name}_{pdf_file.size}"
            if _pdf_key not in st.session_state:
                with st.spinner("🔍 Analizando reporte…"):
                    st.session_state[_pdf_key] = parse_gl_pdf(pdf_file.getvalue())
            # Registrar la clave activa para usarla fuera del bloque
            st.session_state[_active_key] = _pdf_key
        else:
            # Reset: el usuario quitó el archivo — limpiar datos del parser
            if _active_key in st.session_state:
                _stale_key = st.session_state.pop(_active_key)
                st.session_state.pop(_stale_key, None)
    with col_delta:
        weekly_delta = st.text_area(
            "📝 Resumen de Cambios Semanales (Delta) *",
            height=100,
            placeholder=(
                "Ej: Score GL degradó 45→62. Aparecen 2 nuevas señales "
                "indirectas (+1.2%). Se identificó salto en profundidad 7."
            ),
            key="mon_weekly_delta",
        )

    # ── Resultados del parseo (ancho completo, bajo las columnas) ──
    _active_pdf_key = st.session_state.get(_active_key)
    if _active_pdf_key:
        _pr = st.session_state.get(_active_pdf_key, {})
        if _pr.get("ok"):
            _high  = _pr["high_risk_count"]
            _med   = _pr["medium_risk_count"]
            _total = _pr["total_rows"]
            _top   = _pr.get("top_entity") or "—"
            _sof   = _pr.get("sof_top")
            _uof   = _pr.get("uof_top")

            _badge_color = "#ef4444" if _high > 0 else "#f59e0b" if _med > 0 else "#22c55e"
            _summary = (
                f"Se detectaron **{_total}** filas de transacciones — "
                f"**{_high}** de riesgo Crítico/Alto, **{_med}** Medio. "
                f"Indicador principal: **{_top}**."
            )
            with st.expander("🔬 Transacciones GL detectadas — ver detalle", expanded=True):
                st.markdown(
                    f"<div style='background:#1a1a2e;border-left:3px solid {_badge_color};"
                    f"padding:10px 16px;border-radius:6px;margin-bottom:10px;'>"
                    f"<span style='color:#e5e7eb;font-size:0.88rem;'>{_summary}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                # Tabla de top indicadores
                _indicators = _pr.get("indicators", [])[:8]
                if _indicators:
                    _tbl_rows = ""
                    for _ind in _indicators:
                        _sc   = _ind.get("gl_score")
                        _rl   = _ind.get("risk_level", "—")
                        _rl_c = _COLOR_NIVEL.get(_rl, "#6b7280")
                        _dp   = _ind.get("direct_pct", 0.0)
                        _ip   = _ind.get("indirect_pct", 0.0)
                        _tp   = _ind.get("total_pct", 0.0)
                        _tbl_rows += (
                            f"<tr>"
                            f"<td style='color:#e5e7eb;padding:4px 8px;'>{_ind['entity']}</td>"
                            f"<td style='color:{_rl_c};padding:4px 8px;font-weight:700;'>{_rl}</td>"
                            f"<td style='color:#9ca3af;padding:4px 8px;text-align:right;'>{_sc or '—'}</td>"
                            f"<td style='color:#93c5fd;padding:4px 8px;text-align:right;'>{_dp:.4f}%</td>"
                            f"<td style='color:#86efac;padding:4px 8px;text-align:right;'>{_ip:.4f}%</td>"
                            f"<td style='color:#fde68a;padding:4px 8px;text-align:right;font-weight:700;'>{_tp:.4f}%</td>"
                            f"</tr>"
                        )
                    st.markdown(
                        f"<table style='width:100%;border-collapse:collapse;"
                        f"font-size:0.8rem;margin-bottom:10px;'>"
                        f"<thead><tr style='color:#6b7280;border-bottom:1px solid #374151;'>"
                        f"<th style='padding:4px 8px;text-align:left;'>Entidad</th>"
                        f"<th style='padding:4px 8px;text-align:left;'>Nivel</th>"
                        f"<th style='padding:4px 8px;text-align:right;'>GL Score</th>"
                        f"<th style='padding:4px 8px;text-align:right;'>Directa %</th>"
                        f"<th style='padding:4px 8px;text-align:right;'>Indirecta %</th>"
                        f"<th style='padding:4px 8px;text-align:right;'>Total %</th>"
                        f"</tr></thead><tbody>{_tbl_rows}</tbody></table>",
                        unsafe_allow_html=True,
                    )

                # ── Métricas comparativas GL ───────────────────────────
                _cur_score = current_record.get("gl_score")
                _cur_cont  = (
                    float(current_record.get("sof_cont_total") or 0)
                    + float(current_record.get("uof_cont_total") or 0)
                )
                _det_score = _pr.get("gl_score_detected")
                _det_cont  = (
                    (_sof["total_pct"] if _sof else 0.0)
                    + (_uof["total_pct"] if _uof else 0.0)
                )

                _mc1, _mc2, _mc3 = st.columns(3)
                with _mc1:
                    _sc_delta = (
                        f"{_det_score - _cur_score:+d} vs actual"
                        if _det_score is not None and _cur_score is not None
                        else None
                    )
                    st.metric(
                        "GL Score en PDF",
                        str(_det_score) if _det_score is not None else "—",
                        delta=_sc_delta,
                        delta_color="inverse",
                        help="Score extraído del texto del PDF vs. valor actual en BD.",
                    )
                with _mc2:
                    _cont_delta = (
                        f"{_det_cont - _cur_cont:+.4f}% vs actual"
                        if _cur_cont > 0 else None
                    )
                    st.metric(
                        "Contam. SoF+UoF detectada",
                        f"{_det_cont:.4f}%",
                        delta=_cont_delta,
                        delta_color="inverse",
                    )
                with _mc3:
                    st.metric(
                        "Indicadores Crítico/Alto",
                        str(_high),
                        delta=f"+{_high} señales" if _high > 0 else "0 señales",
                        delta_color="inverse" if _high > 0 else "off",
                    )

                # Top 3 rápido
                _top3 = [
                    i for i in _pr.get("indicators", [])
                    if i["risk_level"] in ("Crítico", "Alto")
                ][:3]
                if _top3:
                    _top3_txt = " | ".join(
                        f"{i['entity']} ({i['risk_level']}, {i['total_pct']:.4f}%)"
                        for i in _top3
                    )
                    st.caption(f"🔴 **Top 3 Crítico/Alto:** {_top3_txt}")

                if _sof:
                    st.caption(
                        f"📤 **SoF sugerido:** {_sof['entity']} "
                        f"— Directa: {_sof['direct_pct']:.4f}% "
                        f"/ Indirecta: {_sof['indirect_pct']:.4f}%"
                        f" | GL: {_sof.get('gl_score') or '—'}"
                    )
                if _uof:
                    st.caption(
                        f"📥 **UoF sugerido:** {_uof['entity']} "
                        f"— Directa: {_uof['direct_pct']:.4f}% "
                        f"/ Indirecta: {_uof['indirect_pct']:.4f}%"
                        f" | GL: {_uof.get('gl_score') or '—'}"
                    )

                # Botón de pre-llenado extendido
                if st.button(
                    "📥 Pre-llenar Pasos 2-3-4 con estos datos",
                    key="mon_prefill_btn",
                    type="primary",
                    use_container_width=True,
                ):
                    _sof_tipo_map = {
                        "Crítico": "Critical", "Alto": "High",
                        "Medio": "Medium", "Bajo": "Low",
                    }
                    # SoF
                    if _sof:
                        st.session_state["mon_sof_ind"]  = _find_gl_opt(_sof["entity"])
                        st.session_state["mon_sof_dc"]   = float(_sof["direct_pct"])
                        st.session_state["mon_sof_ic"]   = float(_sof["indirect_pct"])
                        st.session_state["mon_sof_dep"]  = int(_sof.get("depth") or 1)
                        st.session_state["mon_sof_tipo"] = _sof_tipo_map.get(
                            _sof.get("risk_level", ""), "Medium"
                        )
                    # UoF
                    if _uof:
                        st.session_state["mon_uof_ind"]  = _find_gl_opt(_uof["entity"])
                        st.session_state["mon_uof_dc"]   = float(_uof["direct_pct"])
                        st.session_state["mon_uof_ic"]   = float(_uof["indirect_pct"])
                        st.session_state["mon_uof_dep"]  = int(_uof.get("depth") or 1)
                    # GL Score + Nivel desde PDF
                    if _det_score is not None:
                        st.session_state["mon_gl_score"]    = _det_score
                        _auto_nivel = (
                            "Crítico" if _det_score < 20 else
                            "Alto"    if _det_score < 40 else
                            "Medio"   if _det_score < 70 else
                            "Bajo"
                        )
                        st.session_state["mon_nivel_manual"] = _auto_nivel
                    # Weekly delta (auto-generado vs historial)
                    _auto_delta = generate_weekly_delta(_pr, _prev_snapshot)
                    if _auto_delta:
                        st.session_state["mon_weekly_delta"] = _auto_delta
                    # Analyst observations (top-3 resumen)
                    if _top3:
                        _obs_lines = [
                            f"• {i['entity']}: GL:{i.get('gl_score', '—')}, "
                            f"Dir:{i['direct_pct']:.4f}%, Ind:{i['indirect_pct']:.4f}%"
                            for i in _top3
                        ]
                        _obs_txt = "Top indicadores GL (PDF):\n" + "\n".join(_obs_lines)
                        _obs_txt += f"\nContaminación total: {_det_cont:.4f}%"
                        st.session_state["mon_analyst_obs"] = _obs_txt
                    st.rerun()

        elif _pr.get("error"):
            st.warning(f"⚠️ Parser GL: {_pr['error']}", icon="📄")

    st.markdown("---")

    # Valores iniciales desde el registro actual
    init_chain_raw   = current_record.get("blockchain") or "ETH"
    init_score       = current_record.get("gl_score")
    init_nivel_raw   = current_record.get("riesgo_nivel") or "Sin Datos"
    chain_opts       = ["ETH", "BTC", "BNB", "TRX", "SOL", "MATIC", "Otro"]
    niveles          = ["Sin Datos", "Bajo", "Medio", "Alto", "Crítico"]
    status_opts      = ["Active", "Inactive", "Suspended", "Under Review"]
    tipo_riesgo_opts = ["Low", "Medium", "High", "Critical"]
    naturaleza_opts  = ["Directa", "Indirecta"]
    currency_opts    = ["USD", "EUR", "USDT", "USDC"]
    analyst_opts     = list(dict.fromkeys([
        user.get("nombre_completo") or user.get("username") or "Analista",
        "Adrian Cardona", "Jorge Jiménez",
    ]))
    chain_idx = chain_opts.index(init_chain_raw) if init_chain_raw in chain_opts else 0
    nivel_idx = niveles.index(init_nivel_raw) if init_nivel_raw in niveles else 0

    with st.form("form_monitoreo_semanal", clear_on_submit=True):
        # ── Paso 2: Identificación ────────────────────────
        step2_label = "📋 Paso 2 — Identificación"
        st.markdown(
            f"<div style='background:#0f172a;border-left:4px solid #6366f1;"
            f"padding:10px 16px;border-radius:6px;margin-bottom:12px;'>"
            f"<b style='color:#a5b4fc;'>{step2_label}</b></div>",
            unsafe_allow_html=True,
        )
        col_wa_d, col_chain, col_st_d = st.columns([4, 1, 2])
        with col_wa_d:
            st.text_input("💳 Wallet (bloqueada)", value=wallet_addr, disabled=True)
        with col_chain:
            blockchain = st.selectbox("Blockchain", chain_opts, index=chain_idx)
        with col_st_d:
            st.text_input("Cliente", value=cliente_nombre, disabled=True)

        col_sc, col_nv, col_an, col_fecha = st.columns(4)
        with col_sc:
            gl_score_val = st.number_input(
                "🎯 GL Score (0-100)",
                min_value=0, max_value=100,
                value=init_score, placeholder="Ej: 47",
                key="mon_gl_score",
            )
        with col_nv:
            riesgo_manual = st.selectbox("Nivel GL", niveles, index=nivel_idx, key="mon_nivel_manual")
        with col_an:
            monitoring_analyst = st.selectbox("👤 Analista", analyst_opts)
        with col_fecha:
            report_date = st.date_input("📅 Fecha Reporte", value=None)
        wallet_status_form = st.selectbox("Estado de la Wallet", status_opts)

        st.markdown("---")

        # ── Paso 3: SoF / UoF ────────────────────────────
        step3_label = "🔄 Paso 3 — Análisis SoF · UoF"
        st.markdown(
            f"<div style='background:#0f172a;border-left:4px solid #22c55e;"
            f"padding:10px 16px;border-radius:6px;margin-bottom:12px;'>"
            f"<b style='color:#86efac;'>{step3_label}</b></div>",
            unsafe_allow_html=True,
        )
        col_sof, col_uof = st.columns(2, gap="large")

        with col_sof:
            st.markdown(
                "<div style='background:#1e3a5f;padding:8px 14px;border-radius:8px;"
                "margin-bottom:12px;border-left:3px solid #3b82f6;'>"
                "<b style='color:#93c5fd;'>📥 SOURCE OF FUNDS (SoF)</b><br>"
                "<span style='color:#6b7280;font-size:0.78rem;'>Origen de los fondos que entran</span>"
                "</div>",
                unsafe_allow_html=True,
            )
            sof_tipo = st.selectbox("Tipología / Type of Risk", tipo_riesgo_opts, key="mon_sof_tipo")
            sof_ind_opt = st.selectbox(
                "Indicador GL", _GL_SELECTBOX, key="mon_sof_ind",
                help="Indicadores ordenados por score de riesgo (mayor primero)",
            )
            sof_naturaleza  = st.selectbox("Naturaleza", naturaleza_opts, key="mon_sof_nat")
            sof_profundidad = st.number_input(
                "Profundidad (nro. saltos)", min_value=1, max_value=50, value=1, key="mon_sof_dep",
            )
            st.markdown("**% Contaminación**")
            sc1, sc2 = st.columns(2)
            with sc1:
                sof_direct = st.number_input(
                    "Directa %", min_value=0.0, max_value=100.0,
                    value=0.0, step=0.01, format="%.4f", key="mon_sof_dc",
                )
            with sc2:
                sof_indirect = st.number_input(
                    "Indirecta %", min_value=0.0, max_value=100.0,
                    value=0.0, step=0.01, format="%.4f", key="mon_sof_ic",
                )
            sof_monto = st.number_input(
                "Amount Analyzed (USD)", min_value=0.0, step=1000.0, key="mon_sof_am",
            )

        with col_uof:
            st.markdown(
                "<div style='background:#1e3a2f;padding:8px 14px;border-radius:8px;"
                "margin-bottom:12px;border-left:3px solid #22c55e;'>"
                "<b style='color:#86efac;'>📤 USE OF FUNDS (UoF)</b><br>"
                "<span style='color:#6b7280;font-size:0.78rem;'>Destino / uso de los fondos que salen</span>"
                "</div>",
                unsafe_allow_html=True,
            )
            uof_ind_opt = st.selectbox(
                "Indicador GL", _GL_SELECTBOX, key="mon_uof_ind",
                help="Indicadores ordenados por score de riesgo (mayor primero)",
            )
            uof_naturaleza  = st.selectbox("Naturaleza", naturaleza_opts, key="mon_uof_nat")
            uof_profundidad = st.number_input(
                "Profundidad (nro. saltos)", min_value=1, max_value=50, value=1, key="mon_uof_dep",
            )
            st.markdown("**% Contaminación**")
            uc1, uc2 = st.columns(2)
            with uc1:
                uof_direct = st.number_input(
                    "Directa %", min_value=0.0, max_value=100.0,
                    value=0.0, step=0.01, format="%.4f", key="mon_uof_dc",
                )
            with uc2:
                uof_indirect = st.number_input(
                    "Indirecta %", min_value=0.0, max_value=100.0,
                    value=0.0, step=0.01, format="%.4f", key="mon_uof_ic",
                )
            uof_monto = st.number_input(
                "Amount Analyzed (USD)", min_value=0.0, step=1000.0, key="mon_uof_am",
            )

        st.markdown("---")

        # ── Paso 4: Validación GL + Conclusión ───────────
        step4_label = "📄 Paso 4 — Validación GL y Conclusión"
        st.markdown(
            f"<div style='background:#0f172a;border-left:4px solid #f59e0b;"
            f"padding:10px 16px;border-radius:6px;margin-bottom:12px;'>"
            f"<b style='color:#fde68a;'>{step4_label}</b></div>",
            unsafe_allow_html=True,
        )
        gl_raw = st.text_area(
            "Reporte Global Ledger (JSON o texto)",
            height=90,
            placeholder='{"address":"TAHQWz...","score":47,"labels":[...]}',
            key="mon_gl_raw",
        )
        analyst_observations = st.text_area(
            "📝 Analyst Observations", height=90,
            placeholder=(
                "Ej: Tiene 3 indicadores de riesgo indirectos:\n"
                "• High-Risk Exchange (ChangeNOW): 2.88%\n"
                "• Reported Hack: 0.42% · Total Contam.: 3.3%"
            ),
            key="mon_analyst_obs",
        )
        col_exp, col_cur = st.columns([3, 1])
        with col_exp:
            exposure = st.number_input(
                "💰 Exposición Total", min_value=0.0, value=0.0, step=1000.0,
            )
        with col_cur:
            exposure_currency = st.selectbox("Moneda", currency_opts)
        col_url, col_notas = st.columns(2)
        with col_url:
            pdf_url = st.text_input("📄 URL Reporte PDF (cloud)", placeholder="https://...")
        with col_notas:
            notas = st.text_area("Notas internas", height=68)
        st.markdown("**Risk Labels JSON** *(del reporte GL)*")
        labels_raw = st.text_area(
            "Risk Labels", value="", height=70, label_visibility="collapsed",
        )

        submitted = st.form_submit_button(
            "💾 Guardar Ciclo de Monitoreo", type="primary", use_container_width=True,
        )

    # ── Procesamiento del submit ──────────────────────────
    if submitted:
        if not weekly_delta.strip():
            st.warning("⚠️ El campo 'Resumen de Cambios Semanales (Delta)' es obligatorio.")
            return

        gl_parsed: dict = {}
        if gl_raw.strip():
            gl_parsed = _parse_gl_report(gl_raw)

        init_labels_raw = (
            labels_raw.strip() or
            json.dumps(gl_parsed.get("risk_labels") or [], ensure_ascii=False)
        )
        try:
            labels_parsed = json.loads(init_labels_raw) if init_labels_raw.strip() else []
            risk_labels   = [
                RiskLabel(**lbl) if isinstance(lbl, dict) else lbl
                for lbl in labels_parsed
            ]
        except Exception as exc:
            st.error(f"JSON de Risk Labels inválido: {exc}")
            return

        sof_indicador  = _parse_gl_opt(sof_ind_opt)
        sof_ind_score  = GL_SCORES.get(sof_indicador, 50) if sof_indicador else 50
        sof_total_pct  = sof_direct + sof_indirect
        sof_score_calc = round((sof_total_pct / 100.0) * sof_ind_score)
        sof_nivel_calc = score_gl_to_nivel(sof_score_calc)

        uof_indicador  = _parse_gl_opt(uof_ind_opt)
        uof_ind_score  = GL_SCORES.get(uof_indicador, 50) if uof_indicador else 50
        uof_total_pct  = uof_direct + uof_indirect
        uof_score_calc = round((uof_total_pct / 100.0) * uof_ind_score)
        uof_nivel_calc = score_gl_to_nivel(uof_score_calc)

        is_critico_locked = (sof_ind_score == 100 or uof_ind_score == 100)
        if sof_indicador and uof_indicador:
            final_risk_score_calc = (sof_score_calc + uof_score_calc) / 2.0
        elif sof_indicador:
            final_risk_score_calc = float(sof_score_calc)
        elif uof_indicador:
            final_risk_score_calc = float(uof_score_calc)
        else:
            final_risk_score_calc = None

        if is_critico_locked:
            final_risk_level_calc = "Crítico"
        elif final_risk_score_calc is not None:
            final_risk_level_calc = score_gl_to_nivel(round(final_risk_score_calc))
        else:
            final_risk_level_calc = riesgo_manual

        gl_score_int   = int(gl_score_val) if gl_score_val is not None else None
        calificacion   = calificar_labels([lbl.model_dump() for lbl in risk_labels])
        nivel_catalogo = calificacion["nivel_final"]
        nivel_base     = riesgo_manual
        if nivel_base == "Sin Datos" and gl_score_int is not None:
            nivel_base = score_a_nivel_riesgo(gl_score_int)
        nivel_gl = nivel_dominante(nivel_catalogo, nivel_base)
        if gl_score_int is not None and gl_score_int < 30:
            nivel_gl = "Crítico"
        riesgo_nivel_final = nivel_dominante(nivel_gl, final_risk_level_calc)

        if gl_parsed and gl_parsed.get("gl_score") is not None:
            score_diff = abs((gl_score_int or 0) - gl_parsed["gl_score"])
            if score_diff >= 10:
                gl_reported = gl_parsed["gl_score"]
                st.warning(
                    f"⚠️ Discrepancia GL: score manual ({gl_score_int}) difiere "
                    f"{score_diff} puntos del reporte GL ({gl_reported}). "
                    "Se guardará el valor manual."
                )

        if is_critico_locked:
            st.error(
                "🚨 Indicador de alto riesgo detectado. "
                "Calificación bloqueada en **CRÍTICO** según política AdamoServices."
            )

        new_cont_total = sof_total_pct + uof_total_pct
        st.markdown("##### 📊 Comparativo con ciclo anterior")
        _render_comparativo(current_record, gl_score_int, new_cont_total)

        pdf_ref = pdf_url.strip() or None
        if pdf_file and not pdf_ref:
            pdf_ref = f"[local] {pdf_file.name}"

        now_label    = datetime.now().strftime("%Y-%m-%d")
        delta_prefix = f"[Δ semana {now_label}] {weekly_delta.strip()}\n\n"
        obs_final    = delta_prefix + (analyst_observations.strip() or "")

        payload = WalletMonitorCreate(
            wallet_address        = wallet_addr,
            blockchain            = blockchain,
            crypto_cliente_id     = current_record.get("crypto_cliente_id"),
            client_nombre         = cliente_nombre,
            gl_score              = gl_score_int,
            riesgo_nivel          = riesgo_nivel_final,
            risk_labels           = risk_labels,
            total_exposure        = float(exposure),
            exposure_currency     = exposure_currency,
            wallet_status         = wallet_status_form,
            sof_tipo_riesgo       = sof_tipo,
            sof_indicador         = sof_indicador,
            sof_naturaleza        = sof_naturaleza,
            sof_profundidad       = sof_profundidad,
            sof_cont_directa      = sof_direct,
            sof_cont_indirecta    = sof_indirect,
            sof_cont_total        = sof_total_pct,
            sof_score             = sof_score_calc,
            sof_nivel             = sof_nivel_calc,
            sof_monto             = sof_monto or None,
            uof_indicador         = uof_indicador,
            uof_naturaleza        = uof_naturaleza,
            uof_profundidad       = uof_profundidad,
            uof_cont_directa      = uof_direct,
            uof_cont_indirecta    = uof_indirect,
            uof_cont_total        = uof_total_pct,
            uof_score             = uof_score_calc,
            uof_nivel             = uof_nivel_calc,
            uof_monto             = uof_monto or None,
            analyst_observations  = obs_final,
            monitoring_analyst    = monitoring_analyst,
            final_risk_score      = final_risk_score_calc,
            final_risk_level      = final_risk_level_calc,
            weekly_delta          = weekly_delta.strip(),
            pdf_report_url        = pdf_ref,
            last_report_date      = datetime.combine(report_date, datetime.min.time()) if report_date else None,
            registrado_por        = user.get("username"),
            notas                 = notas.strip() or None,
        )

        try:
            session = next(get_session())
            result  = CryptoRepository(session).monitor_wallet(payload)
            session.close()
            _get_wallets_cached.clear()
            _get_clientes_cached.clear()
            frl     = result.get("final_risk_level") or riesgo_nivel_final
            frs     = result.get("final_risk_score")
            frs_txt = f"{frs:.1f}" if frs is not None else "N/A"
            sof_lbl = sof_indicador or "N/A"
            uof_lbl = uof_indicador or "N/A"
            pdf_msg = f"\n\n📎 PDF: `{pdf_ref}`" if pdf_ref else ""
            st.success(
                f"✅ **{cliente_nombre}** — Ciclo guardado y archivado.\n\n"
                f"**Final Risk Level:** {frl} · **Score:** {frs_txt} · "
                f"GL: {gl_score_int or '—'}\n\n"
                f"SoF: {sof_lbl} → {sof_total_pct:.2f}% · score {sof_score_calc} "
                f"({sof_nivel_calc})\n\n"
                f"UoF: {uof_lbl} → {uof_total_pct:.2f}% · score {uof_score_calc} "
                f"({uof_nivel_calc})"
                + pdf_msg
            )
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Error al guardar ciclo de monitoreo: {exc}")


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

    # Stats filtradas por cliente o globales usando get_stats_gerencial
    stats_filtradas = repo.get_stats_gerencial(cliente_id=filtro_cliente_id) if filtro_cliente_id else stats

    total_wallets = int(stats_filtradas.get("total_wallets") or 0)
    total_exp     = float(stats_filtradas.get("total_exposure_usd") or 0)
    nivel_critico = int(stats_filtradas.get("nivel_critico") or 0)
    nivel_alto    = int(stats_filtradas.get("nivel_alto") or 0)
    nivel_medio   = int(stats_filtradas.get("nivel_medio") or 0)
    nivel_bajo    = int(stats_filtradas.get("nivel_bajo") or 0)
    sin_datos     = int(stats_filtradas.get("sin_datos") or 0)
    atencion      = int(stats_filtradas.get("atencion_prioritaria") or 0)

    # Wallets prioritarias según filtro
    if filtro_cliente_id:
        criticos = repo.get_wallets_by_cliente(filtro_cliente_id)
        criticos = [w for w in criticos if (w.get("gl_score") or 100) < 30
                    or w.get("riesgo_nivel") in ("Crítico", "Alto")]
        # Banner resumen ejecutivo del cliente
        if total_wallets > 0:
            nivel_predominante = max(
                [("Crítico", nivel_critico), ("Alto", nivel_alto), ("Medio", nivel_medio), ("Bajo", nivel_bajo)],
                key=lambda x: x[1],
            )[0]
            color_pred = _COLOR_NIVEL.get(nivel_predominante, "#6b7280")
            st.markdown(
                f"<div style='background:#1f2937;border-left:4px solid {color_pred};"
                f"padding:12px 16px;border-radius:8px;margin-bottom:12px;'>"
                f"<b style='color:#f9fafb;'>Resumen — {filtro_cliente_label}</b><br>"
                f"<span style='color:#9ca3af;font-size:0.85rem;'>"
                f"El cliente tiene <b style='color:#5fe9d0;'>{total_wallets} wallet{'s' if total_wallets != 1 else ''}</b> "
                f"con riesgo predominante <b style='color:{color_pred};'>{nivel_predominante}</b> "
                f"y una exposición total de <b style='color:#f59e0b;'>${total_exp:,.2f} USD</b>."
                f"</span></div>",
                unsafe_allow_html=True,
            )
    else:
        criticos = repo.get_atencion_prioritaria()

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

    tab_clientes, tab_monitor, tab_monitoreo, tab_gerencial = st.tabs([
        "👥 Clientes",
        "📋 Monitor de Wallets",
        "📈 Monitoreo Semanal",
        "📊 Reporte Gerencial",
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

    # ── Tab 3: Monitoreo Semanal ──────────────────────────────
    with tab_monitoreo:
        _tab_monitoreo_semanal(user)

    # ── Tab 4: Reporte Gerencial ──────────────────────────────
    with tab_gerencial:
        try:
            session = next(get_session())
            render_gerencial_crypto(session)
            session.close()
        except Exception as exc:
            st.error(f"Error cargando reporte gerencial: {exc}")
