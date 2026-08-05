"""
app/components/jurisdicciones_ui.py
Mapa mundial de jurisdicciones por nivel de riesgo regulatorio.

El color dice qué; el panel de contexto dice por qué. Es la distinción que se
perdía cuando todo iba fundido en un único conjunto de "alto riesgo": Cuba
aparece señalada por sanciones de OFAC, no por deficiencias antilavado, y esa
diferencia importa a la hora de justificar una decisión ante un auditor.

Fuente de los datos: config/listas_riesgo.json (ver config/listas_riesgo.py).
"""

from __future__ import annotations

import streamlit as st

from config import listas_riesgo as lr
from config import paises
from config.jurisdicciones_legacy import a_iso3
from app.components import ui_kit as ui

# Color de cada capa. Coincide con los tonos del kit para que el mapa no
# introduzca una paleta propia.
_COLOR_CAPA: dict[str, str] = {
    "gafi_negra":       "#ef4444",
    "ofac_integral":    "#f97316",
    "gafi_gris":        "#f59e0b",
    "politica_interna": "#a78bfa",
}
_COLOR_OPERA = "#1d9e75"
_COLOR_TIERRA = "#232735"
_COLOR_FONDO = "#0d0e14"

# Jurisdicciones demasiado pequeñas para verse en un mapa mundial.
# Es una ironía del oficio: los centros financieros offshore y los
# microestados son precisamente los que más importan en compliance, y
# precisamente los que el relleno por país no llega a dibujar. Se marcan
# con un punto sobre su posición.
_MICRO: dict[str, tuple[float, float]] = {
    # Caribe
    "CYM": (19.31, -81.25),   "BHS": (25.03, -77.40),
    "BMU": (32.32, -64.76),   "VGB": (18.42, -64.64),
    "ABW": (12.52, -69.97),   "BRB": (13.19, -59.54),
    "JAM": (18.11, -77.30),   "TCA": (21.69, -71.80),
    "ATG": (17.06, -61.80),   "KNA": (17.36, -62.78),
    "LCA": (13.91, -60.98),   "VCT": (13.25, -61.20),
    "GRD": (12.12, -61.68),   "DMA": (15.41, -61.37),
    "CUW": (12.17, -68.99),   "SXM": (18.04, -63.06),
    "AIA": (18.22, -63.07),   "MSR": (16.74, -62.19),
    # Europa
    "MCO": (43.73, 7.42),     "AND": (42.51, 1.52),
    "LIE": (47.17, 9.55),     "SMR": (43.94, 12.46),
    "VAT": (41.90, 12.45),    "MLT": (35.94, 14.38),
    "GIB": (36.14, -5.35),    "JEY": (49.21, -2.13),
    "GGY": (49.46, -2.58),    "IMN": (54.24, -4.55),
    # Otras
    "SGP": (1.35, 103.82),    "HKG": (22.32, 114.17),
    "MAC": (22.20, 113.54),   "MUS": (-20.35, 57.55),
    "SYC": (-4.68, 55.49),    "MDV": (3.20, 73.22),
    "BHR": (26.07, 50.56),    "LBN": (33.85, 35.86),
    "KWT": (29.31, 47.48),    "HTI": (18.97, -72.29),
}


def _exposicion_por_iso(filas: list[dict]) -> dict[str, int]:
    """Cuántos registros propios operan en cada país, por código ISO."""
    conteo: dict[str, int] = {}
    for f in filas:
        for j in (f.get("jurisdicciones") or []):
            iso = a_iso3(j) or (p.iso3 if (p := paises.buscar(j)) else None)
            if iso:
                conteo[iso] = conteo.get(iso, 0) + 1
    return conteo


def _cargar_exposicion() -> dict[str, int]:
    from db.database import get_session
    from db.repositories.partner_repo import PartnerRepository

    try:
        with next(get_session()) as s:
            filas = PartnerRepository(s).get_lista_enriquecida()
    except Exception:
        return {}
    return _exposicion_por_iso([dict(f) if not isinstance(f, dict) else f for f in filas])


def _mapa(exposicion: dict[str, int]) -> None:
    import plotly.graph_objects as go

    señalados = lr.paises_senalados()
    opera_limpio = sorted(set(exposicion) - señalados)

    trazas = []

    # Países donde se opera sin señalamiento: al fondo, para que cualquier
    # capa de riesgo los pise si coinciden.
    if opera_limpio:
        trazas.append(go.Choropleth(
            locations=opera_limpio,
            z=[1] * len(opera_limpio),
            locationmode="ISO-3",
            colorscale=[[0, _COLOR_OPERA], [1, _COLOR_OPERA]],
            showscale=False,
            name="Opera sin señalamiento",
            showlegend=True,
            marker=dict(line=dict(color=_COLOR_FONDO, width=0.5)),
            hovertemplate="<b>%{text}</b><br>Sin señalamiento<extra></extra>",
            text=[paises.nombre(i) for i in opera_limpio],
        ))

    for clave, capa in lr.capas().items():
        codigos = sorted(capa.paises)
        if not codigos:
            continue
        color = _COLOR_CAPA.get(clave, "#6b7280")
        etiquetas = []
        for i in codigos:
            n = exposicion.get(i, 0)
            extra = f"<br>{n} partner(s) tuyos" if n else ""
            etiquetas.append(f"{paises.nombre(i)}|{capa.etiqueta}{extra}")
        trazas.append(go.Choropleth(
            locations=codigos,
            z=[1] * len(codigos),
            locationmode="ISO-3",
            colorscale=[[0, color], [1, color]],
            showscale=False,
            name=capa.etiqueta,
            showlegend=True,
            marker=dict(line=dict(color=_COLOR_FONDO, width=0.5)),
            customdata=[e.split("|") for e in etiquetas],
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>",
        ))

    # Marcadores para lo que el relleno no alcanza a dibujar
    for clave, capa in lr.capas().items():
        micro = sorted(capa.paises & set(_MICRO))
        if not micro:
            continue
        trazas.append(go.Scattergeo(
            lon=[_MICRO[i][1] for i in micro],
            lat=[_MICRO[i][0] for i in micro],
            mode="markers",
            marker=dict(
                size=9,
                color=_COLOR_CAPA.get(clave, "#6b7280"),
                line=dict(color=_COLOR_FONDO, width=1.5),
                symbol="circle",
            ),
            name=capa.etiqueta,
            showlegend=False,          # ya aparece por la traza del relleno
            hovertemplate="<b>%{text}</b><br>" + capa.etiqueta + "<extra></extra>",
            text=[paises.nombre(i) for i in micro],
        ))

    micro_limpio = sorted(set(opera_limpio) & set(_MICRO))
    if micro_limpio:
        trazas.append(go.Scattergeo(
            lon=[_MICRO[i][1] for i in micro_limpio],
            lat=[_MICRO[i][0] for i in micro_limpio],
            mode="markers",
            marker=dict(
                size=9, color=_COLOR_OPERA,
                line=dict(color=_COLOR_FONDO, width=1.5),
            ),
            name="Opera sin señalamiento",
            showlegend=False,
            hovertemplate="<b>%{text}</b><br>Sin señalamiento<extra></extra>",
            text=[paises.nombre(i) for i in micro_limpio],
        ))

    fig = go.Figure(trazas)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=0, b=0, l=0, r=0),
        height=430,
        geo=dict(
            projection_type="natural earth",
            bgcolor="rgba(0,0,0,0)",
            showframe=False,
            showcoastlines=False,
            showland=True,
            landcolor=_COLOR_TIERRA,
            showocean=False,
            showlakes=False,
            showcountries=True,
            countrycolor=_COLOR_FONDO,
        ),
        legend=dict(
            orientation="h", x=0.5, xanchor="center", y=-0.04,
            font=dict(color="#9ca3af", size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
        font=dict(family="Inter, system-ui, sans-serif"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _panel_pais(iso: str, exposicion: dict[str, int]) -> str:
    """Ficha de contexto: qué listas señalan al país y desde qué fuente."""
    capas = lr.capas_de(iso)
    nombre = paises.nombre(iso)
    n = exposicion.get(iso, 0)

    if capas:
        color = _COLOR_CAPA.get(capas[0].clave, "#6b7280")
        titulo_tono = capas[0].etiqueta
    else:
        color = _COLOR_OPERA if n else "#6b7280"
        titulo_tono = "Sin señalamiento vigente"

    filas = "".join(
        f'<div style="display:flex;justify-content:space-between;gap:8px;'
        f'font-size:11px;margin-bottom:7px">'
        f'<span style="color:#9ca3af">{c.etiqueta}</span>'
        f'<span style="color:#6b7280;white-space:nowrap">{c.verificado}</span></div>'
        for c in capas
    ) or (
        '<div style="font-size:11px;color:#6b7280">No figura en ninguna lista '
        'de las que se controlan.</div>'
    )

    nota = lr.nota_de(iso)
    nota_html = (
        f'<div style="border-top:1px solid var(--border,#1e2130);margin:10px 0"></div>'
        f'<div style="font-size:12px;color:#9ca3af;line-height:1.6">{nota}</div>'
        if nota else ""
    )

    return (
        f'<div style="display:flex;align-items:center;gap:8px">'
        f'<span style="display:inline-block;width:9px;height:9px;border-radius:2px;'
        f'background:{color}"></span>'
        f'<span style="font-size:14px;font-weight:500;color:#f0f1f5">{nombre}</span></div>'
        f'<div style="font-size:11px;color:{color};margin-top:4px">{titulo_tono}</div>'
        f'<div style="border-top:1px solid var(--border,#1e2130);margin:12px 0 10px"></div>'
        f'{filas}'
        f'<div style="border-top:1px solid var(--border,#1e2130);margin:10px 0"></div>'
        f'<div><div style="font-size:20px;font-weight:500;color:#f0f1f5;line-height:1">{n}</div>'
        f'<div style="font-size:11px;color:#6b7280;margin-top:2px">partners tuyos operan aquí</div></div>'
        f'{nota_html}'
    )


def page_mapa_jurisdicciones(user: dict) -> None:
    """Pestaña Mapa de jurisdicciones dentro del módulo Compliance."""
    exposicion = _cargar_exposicion()
    señalados = lr.paises_senalados()

    expuesto_señalado = sorted(
        (i for i in exposicion if i in señalados),
        key=lambda i: -lr.peso_de(i),
    )
    negra = lr.capas()["gafi_negra"].paises
    en_negra = [i for i in exposicion if i in negra]

    ui.render(ui.kpi_grid([
        ui.kpi("Jurisdicciones señaladas", len(señalados), "de 249 del catálogo"),
        ui.kpi(
            "Tu exposición",
            len(expuesto_señalado),
            "países señalados donde operas",
            tone="warn" if expuesto_señalado else "ok",
        ),
        ui.kpi(
            "Lista negra",
            len(en_negra),
            "sin exposición" if not en_negra else "requiere acción",
            tone="danger" if en_negra else "ok",
        ),
        ui.kpi("Verificado", lr.verificado(), f"hace {lr.dias_desde_verificacion()} días"),
    ]))

    ui.render(ui.spacer(10))
    _mapa(exposicion)

    _invisibles = sorted(señalados & set(_MICRO))
    if _invisibles:
        ui.render(
            f'<div style="font-size:11px;color:var(--fg-muted,#6b7280);'
            f'text-align:center;margin-top:-6px">'
            f'Los puntos marcan jurisdicciones demasiado pequeñas para colorear: '
            f'{", ".join(paises.nombre(i) for i in _invisibles)}.</div>'
        )

    # ── Detalle por país ──────────────────────────────────────
    ui.render(ui.subsection("Consultar jurisdicción", icon_name="search"))

    col_sel, col_ficha = st.columns([1, 1])

    with col_sel:
        opciones = sorted(
            señalados | set(exposicion),
            key=lambda i: paises.nombre(i),
        )
        if not opciones:
            ui.render(ui.empty_state("Sin jurisdicciones que consultar"))
            return
        elegido = st.selectbox(
            "País",
            options=opciones,
            format_func=lambda i: f"{paises.nombre(i)} ({i})",
            label_visibility="collapsed",
        )

        if expuesto_señalado:
            ui.render(ui.spacer(6))
            ui.render(ui.subsection("Tu exposición en países señalados"))
            for iso in expuesto_señalado[:8]:
                capa = lr.capa_dominante(iso)
                color = _COLOR_CAPA.get(capa.clave, "#6b7280") if capa else "#6b7280"
                ui.render(
                    f'<div style="display:flex;justify-content:space-between;'
                    f'font-size:12px;margin-bottom:8px">'
                    f'<span style="color:#f0f1f5">{ui.dot(color)}{paises.nombre(iso)}</span>'
                    f'<span style="color:#6b7280">{exposicion[iso]} partner(s)</span></div>'
                )

    with col_ficha:
        ui.render(ui.card(_panel_pais(elegido, exposicion)))
