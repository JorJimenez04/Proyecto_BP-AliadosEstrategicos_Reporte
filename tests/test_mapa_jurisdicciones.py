"""
tests/test_mapa_jurisdicciones.py
Visibilidad de las jurisdicciones en el mapa.

Un mapa coroplético rellena países por superficie, así que las jurisdicciones
diminutas no se dibujan. La ironía es que en compliance son justo las que más
importan: Islas Caimán, Bermuda, Mónaco o las Islas Vírgenes son centros
financieros con peso propio y ocupan unos pocos píxeles.

Estos tests impiden que una jurisdicción señalada quede invisible.
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://smoke:smoke@localhost:5432/smoke")

from app.components.jurisdicciones_ui import _COLOR_CAPA, _MICRO
from config import listas_riesgo as lr
from config import paises


# ── Coordenadas ──────────────────────────────────────────────
def test_las_coordenadas_son_de_paises_reales() -> None:
    for iso in _MICRO:
        assert iso in paises.POR_ISO3, f"'{iso}' no es un código ISO 3166 válido"


def test_las_coordenadas_estan_en_rango() -> None:
    for iso, (lat, lon) in _MICRO.items():
        assert -90 <= lat <= 90, f"{iso}: latitud fuera de rango ({lat})"
        assert -180 <= lon <= 180, f"{iso}: longitud fuera de rango ({lon})"


def test_ninguna_coordenada_esta_en_el_origen() -> None:
    """(0, 0) cae en el golfo de Guinea: síntoma de coordenada sin rellenar."""
    for iso, (lat, lon) in _MICRO.items():
        assert (lat, lon) != (0.0, 0.0), f"{iso} apunta al océano"


# ── Cobertura ────────────────────────────────────────────────
def test_los_offshore_de_politica_interna_son_visibles() -> None:
    """
    La capa de política interna la componen centros offshore, todos islas
    pequeñas. Sin marcador, esa capa aparecería en la leyenda sin un solo
    píxel pintado en el mapa — que es como estaba antes.
    """
    for iso in lr.capas()["politica_interna"].paises:
        assert iso in _MICRO, (
            f"{iso} ({paises.nombre(iso)}) es un centro offshore sin coordenada; "
            "quedaría invisible en el mapa"
        )


def test_las_jurisdicciones_pequenas_conocidas_tienen_marcador() -> None:
    """Las que hoy figuran en alguna capa y no se dibujan por tamaño."""
    for iso in ("CYM", "BHS", "BMU", "VGB", "MCO"):
        if lr.capa_dominante(iso):
            assert iso in _MICRO, f"{iso} está señalada pero sería invisible"


def test_cada_capa_tiene_color_asignado() -> None:
    """Una capa sin color caería al gris por defecto y se confundiría."""
    for clave in lr.capas():
        assert clave in _COLOR_CAPA, f"la capa '{clave}' no tiene color propio"


def test_los_colores_de_capa_son_distinguibles() -> None:
    usados = [_COLOR_CAPA[c] for c in lr.capas()]
    assert len(set(usados)) == len(usados), "dos capas comparten color"
