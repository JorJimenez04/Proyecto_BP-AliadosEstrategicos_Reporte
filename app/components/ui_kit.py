"""
app/components/ui_kit.py
Kit de componentes visuales — AdamoServices Partner Manager.

Punto único donde vive el aspecto de la interfaz. Cada función devuelve un
string de HTML; el módulo que la usa lo pinta con st.markdown(..., unsafe_allow_html=True)
o con el atajo render().

Reglas del sistema:
  · Los colores salen de las variables CSS definidas en app/main.py.
    Nunca escribir hex a mano en los módulos de UI — añadir un token aquí.
  · Iconos SVG inline (trazo, 1.5px), nunca emojis.
  · Números en peso 500. El 700/800 satura y resta legibilidad.
  · Etiquetas a 11-12px en --fg-muted, sin mayúsculas forzadas.

Uso típico:
    from app.components import ui_kit as ui

    ui.render(ui.section_header("Monitor operativo", "Capacidad comercial", icon="chart"))
    ui.render(ui.kpi_grid([
        ui.kpi("Total partners", 9, "en el portafolio"),
        ui.kpi("Activos", 5, "56% del total", tone="ok"),
    ]))
"""

from __future__ import annotations

from typing import Literal, Sequence

import streamlit as st

# ── Tokens ───────────────────────────────────────────────────
# Se referencian las variables CSS de main.py con un fallback literal, para que
# los componentes sigan siendo legibles si el bloque <style> no llegó a cargar.
BG          = "var(--bg, #0d0e14)"
CARD        = "var(--bg-card, #12141c)"
CARD_RAISED = "var(--bg-card-raised, #151720)"
BORDER      = "var(--border, #1e2130)"
FG          = "var(--fg, #f0f1f5)"
FG_SUBTLE   = "var(--fg-subtle, #9ca3af)"
FG_MUTED    = "var(--fg-muted, #6b7280)"
PRIMARY     = "var(--primary, #7857ff)"
RADIUS      = "var(--radius-md, 12px)"

# Tonos semánticos — usar el nombre, no el color
TONES: dict[str, str] = {
    "neutral":  FG,
    "muted":    FG_MUTED,
    "primary":  PRIMARY,
    "ok":       "var(--risk-low, #22c55e)",
    "warn":     "var(--risk-medium, #f59e0b)",
    "high":     "var(--risk-high, #f97316)",
    "danger":   "var(--risk-critical, #ef4444)",
    "info":     "#378add",
    "teal":     "#1d9e75",
}

Tone = Literal["neutral", "muted", "primary", "ok", "warn", "high", "danger", "info", "teal"]


def tone_color(tone: str) -> str:
    """Color de un tono semántico. Acepta también un hex directo."""
    if tone.startswith("#") or tone.startswith("var("):
        return tone
    return TONES.get(tone, FG)


# ── Iconos ───────────────────────────────────────────────────
# Trazos de 24x24 con stroke currentColor. Añadir aquí los que hagan falta.
_ICON_PATHS: dict[str, str] = {
    "chart":      '<path d="M3 20h18"/><rect x="5" y="10" width="4" height="7" rx="1"/><rect x="11" y="5" width="4" height="12" rx="1"/><rect x="17" y="13" width="4" height="4" rx="1"/>',
    "bank":       '<path d="M3 21h18M4 10h16M5 10V21M19 10V21M9 10v11M15 10v11M12 3l9 5H3z"/>',
    "server":     '<rect x="3" y="4" width="18" height="6" rx="2"/><rect x="3" y="14" width="18" height="6" rx="2"/><path d="M7 7h.01M7 17h.01"/>',
    "card":       '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/>',
    "docs":       '<path d="M4 5a2 2 0 012-2h9l5 5v11a2 2 0 01-2 2H6a2 2 0 01-2-2z"/><path d="M14 3v6h6"/>',
    "users":      '<path d="M9 11a4 4 0 100-8 4 4 0 000 8z"/><path d="M3 21v-1a6 6 0 016-6h0a6 6 0 016 6v1"/><path d="M17 11a3 3 0 100-6M21 21v-1a5 5 0 00-3-4.6"/>',
    "shield":     '<path d="M12 3l8 3v6c0 5-3.4 8.4-8 9-4.6-.6-8-4-8-9V6z"/>',
    "audit":      '<path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6M9 16h4"/>',
    "building":   '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M9 7h.01M15 7h.01M9 11h.01M15 11h.01M9 15h.01M15 15h.01"/>',
    "alert":      '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9L2.4 17a2 2 0 001.7 3h15.8a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z"/>',
    "check":      '<path d="M20 6L9 17l-5-5"/>',
    "clock":      '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "search":     '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
    "coin":       '<circle cx="12" cy="12" r="9"/><path d="M12 7v10M9.5 9.5h4a1.5 1.5 0 010 3h-3a1.5 1.5 0 000 3h4"/>',
    "mail":       '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
    "plus":       '<path d="M12 5v14M5 12h14"/>',
    "list":       '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
}


def icon(name: str, size: int = 16, color: str = "currentColor") -> str:
    """SVG inline de un icono del set. Devuelve '' si el nombre no existe."""
    paths = _ICON_PATHS.get(name)
    if not paths:
        return ""
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{tone_color(color) if color != "currentColor" else color}" '
        f'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" '
        f'style="flex:0 0 auto;vertical-align:-2px" aria-hidden="true">{paths}</svg>'
    )


# ── Utilidades ───────────────────────────────────────────────
def render(html: str) -> None:
    """Atajo para pintar HTML del kit."""
    st.markdown(html, unsafe_allow_html=True)


def spacer(alto: int = 16) -> str:
    return f'<div style="height:{alto}px"></div>'


def _pct(parte: float, total: float) -> float:
    return (parte / total * 100) if total else 0.0


# ── Cabecera de sección ──────────────────────────────────────
def section_header(
    titulo: str,
    subtitulo: str = "",
    icon_name: str = "",
    meta: str = "",
) -> str:
    """Título de página o pestaña, con subtítulo opcional y meta a la derecha."""
    ico = (
        f'<span style="color:{PRIMARY};display:inline-flex">{icon(icon_name, 18)}</span>'
        if icon_name else ""
    )
    sub = (
        f'<div style="font-size:12px;color:{FG_MUTED};margin-top:3px;'
        f'padding-left:{26 if icon_name else 0}px">{subtitulo}</div>'
        if subtitulo else ""
    )
    der = (
        f'<div style="font-size:11px;color:{FG_MUTED};white-space:nowrap;padding-top:3px">{meta}</div>'
        if meta else ""
    )
    return (
        f'<div style="display:flex;align-items:flex-start;justify-content:space-between;'
        f'gap:12px;padding-bottom:14px;border-bottom:1px solid {BORDER};margin-bottom:16px">'
        f'<div><div style="display:flex;align-items:center;gap:8px">{ico}'
        f'<span style="font-size:17px;font-weight:500;color:{FG};letter-spacing:-0.01em">{titulo}</span>'
        f'</div>{sub}</div>{der}</div>'
    )


def subsection(titulo: str, icon_name: str = "") -> str:
    """Encabezado de bloque dentro de una página."""
    ico = (
        f'<span style="color:{FG_SUBTLE};display:inline-flex">{icon(icon_name, 15)}</span>'
        if icon_name else ""
    )
    return (
        f'<div style="display:flex;align-items:center;gap:7px;margin:18px 0 10px">'
        f'{ico}<span style="font-size:13px;font-weight:500;color:{FG}">{titulo}</span></div>'
    )


# ── Tarjetas KPI ─────────────────────────────────────────────
def kpi(
    etiqueta: str,
    valor: object,
    pie: str = "",
    tone: str = "neutral",
) -> str:
    """Una tarjeta de indicador. Combinar con kpi_grid()."""
    color = tone_color(tone)
    pie_html = (
        f'<div style="font-size:11px;color:{FG_MUTED};margin-top:2px">{pie}</div>'
        if pie else ""
    )
    return (
        f'<div style="background:{CARD};border-radius:{RADIUS};padding:14px 16px">'
        f'<div style="font-size:11px;color:{FG_MUTED};letter-spacing:0.04em">{etiqueta}</div>'
        f'<div style="font-size:26px;font-weight:500;color:{color};line-height:1.2;'
        f'margin-top:4px">{valor}</div>{pie_html}</div>'
    )


def kpi_grid(tarjetas: Sequence[str], min_ancho: int = 120) -> str:
    """
    Rejilla responsiva de tarjetas. Se pinta como un único bloque HTML para que
    todas queden a la misma altura — st.columns no lo garantiza.
    """
    return (
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax({min_ancho}px,1fr));'
        f'gap:10px">{"".join(tarjetas)}</div>'
    )


# ── Badges y píldoras ────────────────────────────────────────
# Tinte tenue del propio tono + texto claro del mismo tono.
# La interfaz es oscura: un fondo claro convierte el badge en lo más brillante
# del bloque y se come la jerarquía del dato principal.
_BADGE_TONES: dict[str, tuple[str, str]] = {
    "info":    ("rgba(55,138,221,0.14)",  "#85b7eb"),
    "teal":    ("rgba(29,158,117,0.14)",  "#5dcaa5"),
    "ok":      ("rgba(34,197,94,0.14)",   "#86efac"),
    "warn":    ("rgba(245,158,11,0.14)",  "#fac775"),
    "danger":  ("rgba(239,68,68,0.14)",   "#f09595"),
    "primary": ("rgba(120,87,255,0.14)",  "#afa9ec"),
    "muted":   ("rgba(148,163,184,0.10)", "#9ca3af"),
}


def badge(texto: str, tone: str = "muted") -> str:
    """
    Píldora de metadato.

    Para texto puramente descriptivo bajo un título, preferir un subtítulo
    apagado: el badge llama la atención y solo debe usarse cuando el valor
    cambia (un estado, un conteo), no cuando es una etiqueta fija.
    """
    bg, fg = _BADGE_TONES.get(tone, _BADGE_TONES["muted"])
    return (
        f'<span style="display:inline-block;font-size:11px;background:{bg};color:{fg};'
        f'padding:2px 8px;border-radius:4px;white-space:nowrap">{texto}</span>'
    )


def dot(color: str) -> str:
    return (
        f'<span style="display:inline-block;width:8px;height:8px;border-radius:2px;'
        f'background:{tone_color(color)};margin-right:7px"></span>'
    )


# ── Barras ───────────────────────────────────────────────────
def bar(pct: float, color: str = "primary", alto: int = 5) -> str:
    """Barra de progreso simple."""
    ancho = max(0.0, min(100.0, pct))
    return (
        f'<div style="height:{alto}px;background:{BORDER};border-radius:3px;overflow:hidden">'
        f'<div style="width:{ancho:.0f}%;height:100%;background:{tone_color(color)}"></div></div>'
    )


def stacked_bar(segmentos: Sequence[tuple[float, str]], alto: int = 5) -> str:
    """
    Barra apilada. segmentos = [(porcentaje, tono), ...].
    Los porcentajes deben sumar 100; el kit no los normaliza para que un
    desajuste sea visible en revisión.
    """
    trozos = "".join(
        f'<div style="width:{p:.0f}%;background:{tone_color(c)}"></div>'
        for p, c in segmentos if p > 0
    )
    return (
        f'<div style="display:flex;height:{alto}px;border-radius:3px;overflow:hidden;'
        f'background:{BORDER}">{trozos}</div>'
    )


def legend_row(etiqueta: str, valor: str, pct: float, color: str) -> str:
    """Fila de leyenda con barra — sustituye a las leyendas flotantes de Plotly."""
    apagado = pct <= 0
    col_txt = FG_SUBTLE if apagado else FG
    return (
        f'<div style="margin-bottom:10px">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;'
        f'font-size:12px;margin-bottom:5px">'
        f'<span style="color:{col_txt}">{dot("muted" if apagado else color)}{etiqueta}</span>'
        f'<span style="color:{FG_MUTED}">{valor}</span></div>'
        f'{bar(pct, color)}</div>'
    )


# ── Donut ────────────────────────────────────────────────────
def donut(
    segmentos: Sequence[tuple[float, str]],
    centro_valor: object,
    centro_etiqueta: str = "",
    tam: int = 120,
) -> str:
    """
    Donut en SVG puro. segmentos = [(valor, tono), ...].

    Sustituye al Pie de Plotly: pesa menos, no arrastra leyenda flotante y hereda
    los tokens de color. Para la leyenda usar legend_row().
    """
    total = sum(v for v, _ in segmentos)
    r = tam * 0.383
    circ = 2 * 3.14159265 * r
    cx = cy = tam / 2
    grosor = tam * 0.117

    aros = [
        f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="none" stroke="{BORDER}" '
        f'stroke-width="{grosor:.1f}"/>'
    ]
    offset = 0.0
    for valor, color in segmentos:
        if valor <= 0 or total <= 0:
            continue
        largo = circ * (valor / total)
        aros.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="none" '
            f'stroke="{tone_color(color)}" stroke-width="{grosor:.1f}" '
            f'stroke-dasharray="{largo:.1f} {circ - largo:.1f}" '
            f'stroke-dashoffset="{-offset:.1f}" transform="rotate(-90 {cx} {cy})"/>'
        )
        offset += largo

    etiqueta = (
        f'<text x="{cx}" y="{cy + tam * 0.117:.0f}" text-anchor="middle" fill="{FG_MUTED}" '
        f'font-size="11" font-family="Inter,sans-serif">{centro_etiqueta}</text>'
        if centro_etiqueta else ""
    )
    return (
        f'<svg width="{tam}" height="{tam}" viewBox="0 0 {tam} {tam}" role="img" '
        f'aria-label="{centro_valor} {centro_etiqueta}" style="flex:0 0 auto">'
        f'{"".join(aros)}'
        f'<text x="{cx}" y="{cy - tam * 0.025:.0f}" text-anchor="middle" fill="{FG}" '
        f'font-size="{tam * 0.2:.0f}" font-weight="500" font-family="Inter,sans-serif">{centro_valor}</text>'
        f'{etiqueta}</svg>'
    )


# ── Contenedores ─────────────────────────────────────────────
def card(contenido: str, titulo: str = "", acento: str = "") -> str:
    """Tarjeta genérica. 'acento' pinta un borde superior de 2px."""
    borde = f'border-top:2px solid {tone_color(acento)};' if acento else ""
    cab = (
        f'<div style="font-size:13px;font-weight:500;color:{FG};margin-bottom:14px">{titulo}</div>'
        if titulo else ""
    )
    return (
        f'<div style="background:{CARD};border-radius:{RADIUS};{borde}padding:16px 18px">'
        f'{cab}{contenido}</div>'
    )


def split(izquierda: str, derecha: str, gap: int = 24, min_der: int = 260) -> str:
    """Dos bloques lado a lado que colapsan en vertical si no caben."""
    return (
        f'<div style="display:flex;align-items:center;gap:{gap}px;flex-wrap:wrap">'
        f'{izquierda}<div style="flex:1 1 {min_der}px;min-width:0">{derecha}</div></div>'
    )


def grid(bloques: Sequence[str], min_ancho: int = 190, gap: int = 10) -> str:
    return (
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax({min_ancho}px,1fr));'
        f'gap:{gap}px">{"".join(bloques)}</div>'
    )


def empty_state(mensaje: str, detalle: str = "", icon_name: str = "search") -> str:
    """Estado vacío — invitación, no disculpa."""
    det = (
        f'<div style="font-size:12px;color:{FG_MUTED};margin-top:4px">{detalle}</div>'
        if detalle else ""
    )
    return (
        f'<div style="background:{CARD};border-radius:{RADIUS};padding:28px 20px;text-align:center">'
        f'<div style="color:{FG_MUTED};display:flex;justify-content:center;margin-bottom:8px">'
        f'{icon(icon_name, 22)}</div>'
        f'<div style="font-size:13px;color:{FG_SUBTLE}">{mensaje}</div>{det}</div>'
    )


# ── Tarjeta de entidad del grupo ─────────────────────────────
def _conteo_leyenda(valor: int, color: str) -> str:
    return (
        f'<span style="display:inline-flex;align-items:center">'
        f'<span style="display:inline-block;width:6px;height:6px;border-radius:2px;'
        f'background:{tone_color(color)};margin-right:5px"></span>{valor}</span>'
    )


def entity_card(
    nombre: str,
    etiqueta: str,
    icon_name: str,
    activos: int,
    inactivos: int,
    sin_relacion: int,
    total_portafolio: int,
    acento: str = "info",
    badge_tone: str = "info",   # conservado por compatibilidad; ya no se usa
) -> str:
    """
    Tarjeta de una empresa del holding con su reparto de partners.

    El descriptor va como subtítulo apagado, no como badge: es una etiqueta fija
    y en píldora se llevaba la atención por delante del número.

    Cuando la entidad no tiene ningún partner activo, la tarjeta se apaga entera
    — el color de marca prometía una actividad que no existe.
    """
    total = activos + inactivos + sin_relacion
    apagado = activos == 0

    color_acento = tone_color("muted") if apagado else tone_color(acento)
    color_nombre = FG_SUBTLE if apagado else FG
    color_num    = "#4b5563" if apagado else FG
    color_pct    = "#4b5563" if apagado else color_acento
    pct_activos  = round(_pct(activos, total_portafolio)) if total_portafolio else 0

    segmentos = [
        (_pct(activos, total), "ok"),
        (_pct(inactivos, total), "warn"),
    ]
    return (
        f'<div style="background:{CARD};border-radius:{RADIUS};'
        f'border-top:2px solid {color_acento};padding:16px">'

        # Identidad: icono + nombre con descriptor debajo
        f'<div style="display:flex;align-items:flex-start;gap:9px">'
        f'<span style="color:{color_acento};display:inline-flex;margin-top:1px">'
        f'{icon(icon_name, 17)}</span>'
        f'<div style="min-width:0">'
        f'<div style="font-size:13px;font-weight:500;color:{color_nombre};line-height:1.3">{nombre}</div>'
        f'<div style="font-size:11px;color:{FG_MUTED};margin-top:1px">{etiqueta}</div>'
        f'</div></div>'

        # Cifra protagonista + porcentaje como segundo anclaje
        f'<div style="display:flex;align-items:flex-end;justify-content:space-between;margin-top:16px">'
        f'<div style="display:flex;align-items:baseline;gap:6px">'
        f'<span style="font-size:30px;font-weight:500;color:{color_num};line-height:1">{activos}</span>'
        f'<span style="font-size:12px;color:{FG_MUTED}">de {total_portafolio}</span></div>'
        f'<div style="text-align:right">'
        f'<div style="font-size:15px;font-weight:500;color:{color_pct};line-height:1">{pct_activos}%</div>'
        f'<div style="font-size:11px;color:{FG_MUTED};margin-top:2px">activos</div>'
        f'</div></div>'

        f'<div style="margin-top:12px">{stacked_bar(segmentos)}</div>'

        # Desglose: el significado de cada color ya lo da la barra
        f'<div style="display:flex;justify-content:space-between;font-size:11px;'
        f'color:{FG_MUTED};margin-top:8px">'
        f'{_conteo_leyenda(activos, "muted" if apagado else "ok")}'
        f'{_conteo_leyenda(inactivos, "muted" if inactivos == 0 else "warn")}'
        f'{_conteo_leyenda(sin_relacion, "muted")}'
        f'</div></div>'
    )
