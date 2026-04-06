"""
app/components/partners_ui.py
Vista de tabla de Partners con filtros avanzados — AdamoServices Partner Manager.
"""

import streamlit as st
from db.database import get_session
from db.repositories.partner_repo import PartnerRepository
from config.settings import EstadosAliado, TiposAliado, NivelesRiesgo, EstadosSARLAFT


_COLORES_RIESGO = {
    "Bajo": "#5fe9d0", "Medio": "#f59e0b",
    "Alto": "#fb923c", "Muy Alto": "#ef4444",
}
_COLORES_PIPELINE = {
    "Activo": "#5fe9d0", "Onboarding": "#7839ee", "En Calificación": "#60a5fa",
    "Prospecto": "#9ca3af", "Suspendido": "#f59e0b", "Terminado": "#6b7280",
}


def _pill(text: str, color: str) -> str:
    return (
        f"<span style='background:{color}20;color:{color};padding:2px 10px;"
        f"border-radius:20px;font-size:0.72rem;font-weight:700;'>{text}</span>"
    )


def page_partners(user: dict):
    st.markdown("<h1>🤝 Portafolio de Banking Partners</h1>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#293056;'>", unsafe_allow_html=True)

    # ── Filtros ───────────────────────────────────────────────────────────────
    with st.expander("🔍 Filtros", expanded=True):
        f1, f2, f3, f4, f5 = st.columns(5)
        with f1:
            filtro_pipeline = st.selectbox(
                "Estado Pipeline", ["Todos"] + EstadosAliado.ALL, index=0
            )
        with f2:
            filtro_riesgo = st.selectbox(
                "Nivel Riesgo", ["Todos"] + NivelesRiesgo.ALL, index=0
            )
        with f3:
            filtro_sarlaft = st.selectbox(
                "Estado SARLAFT", ["Todos"] + EstadosSARLAFT.ALL, index=0
            )
        with f4:
            filtro_tipo = st.selectbox(
                "Tipo Aliado", ["Todos"] + TiposAliado.ALL, index=0
            )
        with f5:
            filtro_texto = st.text_input("Buscar (Nombre / NIT)")

    with next(get_session()) as session:
        repo = PartnerRepository(session)
        filas = repo.get_lista_enriquecida(
            estado_pipeline=None if filtro_pipeline == "Todos" else filtro_pipeline,
            nivel_riesgo=None if filtro_riesgo == "Todos" else filtro_riesgo,
            estado_sarlaft=None if filtro_sarlaft == "Todos" else filtro_sarlaft,
            tipo_aliado=None if filtro_tipo == "Todos" else filtro_tipo,
            search_text=filtro_texto or None,
        )

    if not filas:
        st.info("No se encontraron partners con los filtros seleccionados.")
        return

    st.markdown(f"**{len(filas)}** partner(s) encontrado(s)")

    # ── Tabla enriquecida ─────────────────────────────────────────────────────
    header = st.columns([3, 2, 2, 2, 1, 1, 1, 2])
    for col, lbl in zip(header, ["Razón Social", "NIT", "Pipeline", "SARLAFT",
                                   "Riesgo", "Crypto", "Adult", "Próx. Revisión"]):
        col.markdown(f"<span style='color:#5fe9d0;font-size:0.75rem;font-weight:700;'>{lbl}</span>",
                     unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#293056;margin:4px 0 8px;'>", unsafe_allow_html=True)

    for r in filas:
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([3, 2, 2, 2, 1, 1, 1, 2])
        c1.markdown(f"**{r['nombre_razon_social']}**")
        c2.markdown(f"<span style='color:#9ca3af;font-size:0.82rem;'>{r['nit']}</span>",
                    unsafe_allow_html=True)
        c3.markdown(
            _pill(r["estado_pipeline"],
                  _COLORES_PIPELINE.get(r["estado_pipeline"], "#9ca3af")),
            unsafe_allow_html=True,
        )
        c4.markdown(
            _pill(r["estado_sarlaft"],
                  "#ef4444" if r["estado_sarlaft"] == "Vencido" else
                  "#f59e0b" if r["estado_sarlaft"] == "Pendiente" else "#5fe9d0"),
            unsafe_allow_html=True,
        )
        c5.markdown(
            _pill(r["nivel_riesgo"], _COLORES_RIESGO.get(r["nivel_riesgo"], "#9ca3af")),
            unsafe_allow_html=True,
        )
        c6.markdown("🟢" if r.get("crypto_friendly") else "⚪")
        c7.markdown("🟠" if r.get("adult_friendly") else "⚪")
        prox = r.get("fecha_proxima_revision")
        c8.markdown(
            f"<span style='color:#f59e0b;font-size:0.8rem;'>{prox}</span>" if prox
            else "<span style='color:#6b7280;font-size:0.8rem;'>—</span>",
            unsafe_allow_html=True,
        )
