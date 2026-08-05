"""
config/jurisdicciones_legacy.py
Equivalencias entre los valores heredados de Jurisdicciones.ALL y el catálogo ISO.

Contexto: `aliados.jurisdicciones` y `clientes.jurisdicciones` son TEXT[] que
guardan strings con emoji ("🇨🇴 Colombia"). El mapa necesita códigos ISO-3, y
las listas del GAFI y OFAC vienen con nombres en inglés. Este módulo es el
puente entre las tres representaciones.

Es deliberadamente explícito: 35 de los 37 valores los resolvería la búsqueda
automática de config.paises, pero una migración de datos no debe depender de
coincidencias de texto. Un fallo silencioso aquí deja partners sin clasificar
y altera su puntaje_riesgo sin que nadie se entere.

Módulo transitorio: se retira cuando la migración esté aplicada y la UI escriba
códigos ISO directamente.
"""

from __future__ import annotations

from typing import NamedTuple, Optional


class Equivalencia(NamedTuple):
    iso3: Optional[str]      # None = no corresponde a ningún país
    subregion: Optional[str] # zona dentro del país, si aplica
    nota: str


# ── Tabla de equivalencias ───────────────────────────────────
EQUIVALENCIAS: dict[str, Equivalencia] = {
    # ─ Latinoamérica ─────────────────────────────────────────
    "🇨🇴 Colombia":              Equivalencia("COL", None, ""),
    "🇧🇷 Brasil":                Equivalencia("BRA", None, ""),
    "🇲🇽 México":                Equivalencia("MEX", None, ""),
    "🇦🇷 Argentina":             Equivalencia("ARG", None, ""),
    "🇨🇱 Chile":                 Equivalencia("CHL", None, ""),
    "🇵🇪 Perú":                  Equivalencia("PER", None, ""),
    "🇪🇨 Ecuador":               Equivalencia("ECU", None, ""),
    "🇧🇴 Bolivia":               Equivalencia("BOL", None, ""),
    "🇵🇾 Paraguay":              Equivalencia("PRY", None, ""),
    "🇺🇾 Uruguay":               Equivalencia("URY", None, ""),
    "🇻🇪 Venezuela":             Equivalencia("VEN", None, ""),
    "🇨🇷 Costa Rica":            Equivalencia("CRI", None, ""),
    "🇬🇹 Guatemala":             Equivalencia("GTM", None, ""),
    "🇭🇳 Honduras":              Equivalencia("HND", None, ""),
    "🇸🇻 El Salvador":           Equivalencia("SLV", None, ""),
    "🇳🇮 Nicaragua":             Equivalencia("NIC", None, ""),
    "🇨🇺 Cuba":                  Equivalencia("CUB", None, ""),
    "🇩🇴 República Dominicana":  Equivalencia("DOM", None, ""),
    "🇭🇹 Haití":                 Equivalencia("HTI", None, ""),

    # ─ Centros financieros / Offshore ────────────────────────
    "🇵🇦 Panamá":                Equivalencia("PAN", None, ""),
    "🇰🇾 Islas Caimán":          Equivalencia("CYM", None, ""),
    "🇧🇸 Bahamas":               Equivalencia("BHS", None, ""),
    "🇧🇲 Bermuda":               Equivalencia("BMU", None, ""),
    "🇦🇼 Aruba":                 Equivalencia("ABW", None, ""),
    "🇻🇬 Islas Vírgenes (UK)":   Equivalencia(
        "VGB", None,
        "La ISO 3166 las denomina 'Islas Vírgenes Británicas'. La búsqueda "
        "automática por nombre no las resuelve; por eso se mapean a mano.",
    ),
    "🇵🇦 Panamá (ZLC)":          Equivalencia(
        "PAN", "Zona Libre de Colón",
        "No es un país sino una zona franca dentro de Panamá. En el mapa se "
        "pinta como Panamá; la distinción se conserva en el campo subregion "
        "para no perder información de la ficha del partner.",
    ),

    # ─ Norteamérica y Europa ─────────────────────────────────
    "🇺🇸 Estados Unidos":        Equivalencia("USA", None, ""),
    "🇨🇦 Canadá":                Equivalencia("CAN", None, ""),
    "🇪🇸 España":                Equivalencia("ESP", None, ""),
    "🇬🇧 Reino Unido":           Equivalencia("GBR", None, ""),
    "🇵🇹 Portugal":              Equivalencia("PRT", None, ""),
    "🇩🇪 Alemania":              Equivalencia("DEU", None, ""),
    "🇳🇱 Países Bajos":          Equivalencia("NLD", None, ""),
    "🇨🇭 Suiza":                 Equivalencia("CHE", None, ""),

    # ─ Alto riesgo GAFI ──────────────────────────────────────
    "🇮🇷 Irán":                  Equivalencia("IRN", None, ""),
    "🇰🇵 Corea del Norte":       Equivalencia("PRK", None, ""),
    "🇲🇲 Myanmar":               Equivalencia("MMR", None, ""),
}


def a_iso3(valor_legacy: str) -> Optional[str]:
    """
    Código ISO-3 de un valor heredado, o None si no está en la tabla.

    No adivina: un valor desconocido devuelve None para que la migración lo
    reporte en vez de asignarlo mal.
    """
    eq = EQUIVALENCIAS.get(valor_legacy.strip())
    return eq.iso3 if eq else None


def equivalencia(valor_legacy: str) -> Optional[Equivalencia]:
    return EQUIVALENCIAS.get(valor_legacy.strip())


# Valores que conservan información más allá del país
CON_SUBREGION: dict[str, str] = {
    k: v.subregion for k, v in EQUIVALENCIAS.items() if v.subregion
}
