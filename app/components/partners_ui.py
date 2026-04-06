"""
app/components/partners_ui.py
Vista de tabla de Banking Partners — AdamoServices Partner Manager.

Muestra las columnas de capacidades operativas (crypto_friendly, adult_friendly)
como indicadores visuales junto a los filtros estándar de pipeline y riesgo.

ARQUITECTURA: Imports de DB y settings dentro de page_partners()
para evitar fallos en cascada durante la carga del módulo.
"""

import streamlit as st

# ------------------------------------------------------------------
# Paletas — no dependen de imports externos
# ------------------------------------------------------------------
_COLORES_RIESGO: dict[str, str] = {
    "Bajo":     "#5fe9d0",
    "Medio":    "#f59e0b",
    "Alto":     "#fb923c",
    "Muy Alto": "#ef4444",
}

_COLORES_PIPELINE: dict[str, str] = {
    "Activo":          "#5fe9d0",
    "Onboarding":      "#7839ee",
    "En Calificación": "#60a5fa",
    "Prospecto":       "#9ca3af",
    "Suspendido":      "#f59e0b",
    "Terminado":       "#6b7280",
}

_COLORES_SARLAFT: dict[str, str] = {
    "Al Día":      "#5fe9d0",
    "En Revisión": "#60a5fa",
    "Pendiente":   "#f59e0b",
    "Vencido":     "#ef4444",
}

# ------------------------------------------------------------------
# Helpers de UI
# ------------------------------------------------------------------

def _pill(text: str, color: str) -> str:
    return (
        f"<span style='background:{color}20;color:{color};padding:2px 10px;"
        f"border-radius:20px;font-size:0.72rem;font-weight:700;"
        f"white-space:nowrap;'>{text}</span>"
    )


def _capacidad_badge(activo: bool, etiqueta: str, color_si: str) -> str:
    if activo:
        return (
            f"<span style='background:{color_si}20;color:{color_si};"
            f"padding:2px 8px;border-radius:20px;font-size:0.7rem;"
            f"font-weight:700;'>{etiqueta}</span>"
        )
    return "<span style='color:#374151;font-size:0.8rem;'>—</span>"


# ------------------------------------------------------------------
# Función de página
# ------------------------------------------------------------------

def page_partners(user: dict) -> None:
    """
    Renderiza la tabla de Banking Partners con:
    - Filtros por pipeline, riesgo, SARLAFT, tipo y búsqueda libre
    - Columnas de capacidades: crypto_friendly, adult_friendly
    - Puntaje de riesgo numérico junto al nivel
    """
    # -- Lazy imports --------------------------------------------------
    from db.database import get_session
    from db.repositories.partner_repo import PartnerRepository
    from config.settings import EstadosAliado, TiposAliado, NivelesRiesgo, EstadosSARLAFT

    st.markdown("<h1>🤝 Portafolio de Banking Partners</h1>", unsafe_allow_html=True)
    st.markdown(
        "<hr style='border-color:#293056;margin-bottom:20px;'>",
        unsafe_allow_html=True,
    )

    # -- Panel de Filtros -----------------------------------------------
    with st.expander("🔍 Filtros de búsqueda", expanded=True):
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            filtro_pipeline = st.selectbox(
                "Estado Pipeline", ["Todos"] + EstadosAliado.ALL
            )
        with f2:
            filtro_riesgo = st.selectbox(
                "Nivel Riesgo", ["Todos"] + NivelesRiesgo.ALL
            )
        with f3:
            filtro_sarlaft = st.selectbox(
                "Estado SARLAFT", ["Todos"] + EstadosSARLAFT.ALL
            )
        with f4:
            filtro_tipo = st.selectbox(
                "Tipo Aliado", ["Todos"] + TiposAliado.ALL
            )

        fa1, fa2, fa3 = st.columns([3, 1, 1])
        with fa1:
            filtro_texto = st.text_input(
                "Buscar por Razón Social o NIT", placeholder="Ej: Davivienda / 900123456"
            )
        with fa2:
            solo_crypto = st.checkbox("Solo Crypto Friendly")
        with fa3:
            solo_adult = st.checkbox("Solo Adult Friendly")

    # -- Consulta -------------------------------------------------------
    try:
        with next(get_session()) as session:
            repo  = PartnerRepository(session)
            filas = repo.get_lista_enriquecida(
                estado_pipeline=None if filtro_pipeline == "Todos" else filtro_pipeline,
                nivel_riesgo   =None if filtro_riesgo   == "Todos" else filtro_riesgo,
                estado_sarlaft =None if filtro_sarlaft  == "Todos" else filtro_sarlaft,
                tipo_aliado    =None if filtro_tipo     == "Todos" else filtro_tipo,
                search_text    =filtro_texto.strip() or None,
            )
    except Exception as exc:
        st.error(f"Error al consultar partners: {exc}")
        return

    # -- Filtros locales de capacidades (sin extra DB) ------------------
    if solo_crypto:
        filas = [r for r in filas if r.get("crypto_friendly")]
    if solo_adult:
        filas = [r for r in filas if r.get("adult_friendly")]

    if not filas:
        st.info("No se encontraron partners con los filtros seleccionados.")
        return

    col_count, _ = st.columns([2, 8])
    col_count.markdown(
        f"<span style='color:#9ca3af;font-size:0.82rem;'>{len(filas)} partner(s)</span>",
        unsafe_allow_html=True,
    )

    # -- Cabecera de tabla ----------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    COLS = [3.5, 2,   2.2, 1.8, 1.8, 1,   1,   2  ]
    HDRS = [
        "Razón Social / NIT", "Tipo", "Pipeline", "SARLAFT",
        "Riesgo (score)", "Crypto", "Adult", "Próx. Revisión",
    ]
    hdr = st.columns(COLS)
    for col, lbl in zip(hdr, HDRS):
        col.markdown(
            f"<span style='color:#5fe9d0;font-size:0.72rem;font-weight:700;"
            f"text-transform:uppercase;letter-spacing:0.8px;'>{lbl}</span>",
            unsafe_allow_html=True,
        )
    st.markdown(
        "<hr style='border-color:#293056;margin:4px 0 10px;'>",
        unsafe_allow_html=True,
    )

    # -- Filas de datos -------------------------------------------------
    for r in filas:
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(COLS)

        c1.markdown(
            f"<div style='color:#f9fafb;font-weight:600;font-size:0.88rem;'>"
            f"{r['nombre_razon_social']}</div>"
            f"<div style='color:#6b7280;font-size:0.74rem;'>{r['nit']}</div>",
            unsafe_allow_html=True,
        )
        c2.markdown(
            f"<span style='color:#9ca3af;font-size:0.78rem;'>"
            f"{r.get('tipo_aliado', '')}</span>",
            unsafe_allow_html=True,
        )
        c3.markdown(
            _pill(
                r["estado_pipeline"],
                _COLORES_PIPELINE.get(r["estado_pipeline"], "#9ca3af"),
            ),
            unsafe_allow_html=True,
        )
        c4.markdown(
            _pill(
                r["estado_sarlaft"],
                _COLORES_SARLAFT.get(r["estado_sarlaft"], "#9ca3af"),
            ),
            unsafe_allow_html=True,
        )

        nivel   = r.get("nivel_riesgo", "Medio")
        score   = r.get("puntaje_riesgo", 0)
        color_r = _COLORES_RIESGO.get(nivel, "#9ca3af")
        c5.markdown(
            f"{_pill(nivel, color_r)}"
            f"<span style='color:#6b7280;font-size:0.72rem;margin-left:5px;'>"
            f"{int(score)}</span>",
            unsafe_allow_html=True,
        )
        c6.markdown(
            _capacidad_badge(bool(r.get("crypto_friendly")), "CRYPTO", "#f59e0b"),
            unsafe_allow_html=True,
        )
        c7.markdown(
            _capacidad_badge(bool(r.get("adult_friendly")), "ADULT", "#fb923c"),
            unsafe_allow_html=True,
        )

        prox = r.get("fecha_proxima_revision")
        c8.markdown(
            f"<span style='color:#f59e0b;font-size:0.8rem;'>{prox}</span>"
            if prox else
            "<span style='color:#374151;font-size:0.8rem;'>—</span>",
            unsafe_allow_html=True,
        )
