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
