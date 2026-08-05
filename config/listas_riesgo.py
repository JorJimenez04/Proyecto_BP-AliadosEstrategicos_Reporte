"""
config/listas_riesgo.py
Carga y consulta del dataset de listas de riesgo por jurisdicción.

Fuente única de verdad: data/listas_riesgo.json, indexado por código ISO-3.
Antes las listas vivían como conjuntos de strings con emoji escritos a mano en
settings.py, lo que hacía imposible cruzarlas con las publicaciones del GAFI o
de OFAC — que usan nombres en inglés — y obligaba a mantener la misma
información en dos formatos.

Un país puede estar en varias capas a la vez. Venezuela, por ejemplo, está en
la lista gris del GAFI y además tiene sanciones dirigidas de OFAC. Para el
cálculo de riesgo prevalece la capa más severa; para explicárselo al usuario
se muestran todas.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

BASE_DIR = Path(__file__).resolve().parent.parent
RUTA_DATASET = BASE_DIR / "data" / "listas_riesgo.json"

# De más severa a menos. El orden define qué capa manda en el cálculo.
ORDEN_SEVERIDAD: tuple[str, ...] = (
    "gafi_negra",
    "ofac_integral",
    "gafi_gris",
    "politica_interna",
)


class Capa(NamedTuple):
    clave: str
    etiqueta: str
    descripcion: str
    peso: int
    fuente: str
    verificado: str
    paises: frozenset[str]


@lru_cache(maxsize=1)
def _dataset() -> dict:
    with RUTA_DATASET.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def capas() -> dict[str, Capa]:
    """Capas del dataset, ordenadas de más a menos severa."""
    crudo = _dataset()["capas"]
    resultado: dict[str, Capa] = {}
    for clave in ORDEN_SEVERIDAD:
        if clave not in crudo:
            continue
        c = crudo[clave]
        resultado[clave] = Capa(
            clave=clave,
            etiqueta=c["etiqueta"],
            descripcion=c["descripcion"],
            peso=int(c["peso"]),
            fuente=c["fuente"],
            verificado=c["verificado"],
            paises=frozenset(c["paises"]),
        )
    return resultado


def capas_de(iso3: str) -> list[Capa]:
    """Todas las capas en las que figura un país, de más a menos severa."""
    if not iso3:
        return []
    codigo = iso3.upper()
    return [c for c in capas().values() if codigo in c.paises]


def capa_dominante(iso3: str) -> Capa | None:
    """
    Capa más severa de un país, o None si no figura en ninguna.

    Es la que define el peso en el cálculo de riesgo: un país en lista negra
    y además sancionado no suma dos veces, porque su riesgo lo determina la
    condición más grave, no la acumulación.
    """
    encontradas = capas_de(iso3)
    return encontradas[0] if encontradas else None


def peso_de(iso3: str) -> int:
    """Puntos que aporta un país al puntaje de riesgo."""
    capa = capa_dominante(iso3)
    return capa.peso if capa else 0


def paises_senalados() -> frozenset[str]:
    """Todos los códigos ISO-3 que figuran en alguna capa."""
    return frozenset().union(*(c.paises for c in capas().values()))


def nota_de(iso3: str) -> str:
    """Aclaración específica de un país, si la hay."""
    return _dataset().get("notas_por_pais", {}).get(iso3.upper(), "")


def verificado() -> str:
    """Fecha de la última verificación del dataset completo."""
    return _dataset()["verificado"]


def resumen_por_capa() -> dict[str, int]:
    """Cuántos países hay en cada capa. Útil para el mapa y la auditoría."""
    return {c.etiqueta: len(c.paises) for c in capas().values()}


# ── Vigencia ─────────────────────────────────────────────────
# El GAFI revisa sus listas tres veces al año y no publica API, así que la
# verificación es manual. Cuatro meses es el umbral: si se supera, con toda
# probabilidad hubo una plenaria sin contrastar.
MESES_HASTA_CADUCAR = 4


def dias_desde_verificacion() -> int:
    """Días transcurridos desde la última verificación del dataset."""
    from datetime import date

    y, m, d = (int(x) for x in verificado().split("-"))
    return (date.today() - date(y, m, d)).days


def verificacion_caducada(meses: int = MESES_HASTA_CADUCAR) -> bool:
    """True si el dataset lleva demasiado sin contrastarse con la fuente."""
    return dias_desde_verificacion() > meses * 30


def estado_verificacion() -> tuple[str, str]:
    """
    (nivel, mensaje) para mostrar en la interfaz.

    nivel es 'ok' o 'warn', apto para ui_kit.
    """
    dias = dias_desde_verificacion()
    if verificacion_caducada():
        return "warn", (
            f"Listas sin verificar desde hace {dias} días. "
            f"El GAFI celebra plenaria cada cuatro meses."
        )
    return "ok", f"Verificado hace {dias} días"
