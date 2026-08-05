"""
tests/test_paises.py
Catálogo canónico de países y equivalencias con los valores heredados.

Estos tests protegen la pieza sobre la que se apoyan el mapa de jurisdicciones
y el cálculo de riesgo. Un error aquí no rompe la app: deja partners mal
clasificados, que es peor porque no se nota.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://smoke:smoke@localhost:5432/smoke")

from config import paises
from config.jurisdicciones_legacy import EQUIVALENCIAS, a_iso3, equivalencia
from config.settings import Jurisdicciones


# ── Integridad del catálogo ──────────────────────────────────
def test_catalogo_completo_y_sin_duplicados() -> None:
    assert len(paises.PAISES) == 249, "ISO 3166-1 tiene 249 códigos asignados"

    iso3 = [p.iso3 for p in paises.PAISES]
    assert len(set(iso3)) == len(iso3), "hay códigos ISO-3 repetidos"

    iso2 = [p.iso2 for p in paises.PAISES]
    assert len(set(iso2)) == len(iso2), "hay códigos ISO-2 repetidos"


def test_todo_pais_tiene_nombre_y_region() -> None:
    for p in paises.PAISES:
        assert p.nombre.strip(), f"{p.iso3} sin nombre en español"
        assert p.nombre_en.strip(), f"{p.iso3} sin nombre en inglés"
        assert p.region.strip(), f"{p.iso3} sin región"
        assert len(p.iso3) == 3 and p.iso3.isupper()
        assert len(p.iso2) == 2 and p.iso2.isupper()


def test_nombres_de_uso_comun_no_los_oficiales() -> None:
    """La ISO llama 'Birmania' a Myanmar. En un formulario eso confunde."""
    assert paises.POR_ISO3["MMR"].nombre == "Myanmar"
    assert paises.POR_ISO3["PRK"].nombre == "Corea del Norte"
    assert paises.POR_ISO3["BOL"].nombre == "Bolivia"
    assert paises.POR_ISO3["USA"].nombre == "Estados Unidos"
    assert paises.POR_ISO3["GBR"].nombre == "Reino Unido"


# ── Búsqueda ─────────────────────────────────────────────────
@pytest.mark.parametrize("entrada,esperado", [
    ("COL", "COL"),
    ("co", "COL"),
    ("Colombia", "COL"),
    ("Panamá", "PAN"),
    ("Panama", "PAN"),          # sin tilde
    ("🇰🇾 Islas Caimán", "CYM"),  # valor heredado con emoji
    ("Cayman Islands", "CYM"),
])
def test_buscar_resuelve_las_tres_representaciones(entrada: str, esperado: str) -> None:
    p = paises.buscar(entrada)
    assert p is not None, f"no resolvió {entrada!r}"
    assert p.iso3 == esperado


@pytest.mark.parametrize("nombre_fuente,esperado", [
    ("Iran", "IRN"),                     # GAFI y OFAC lo escriben así
    ("North Korea", "PRK"),
    ("Burma", "MMR"),                    # OFAC usa el nombre antiguo
    ("Russia", "RUS"),
    ("Turkey", "TUR"),
    ("Türkiye", "TUR"),
    ("Viet Nam", "VNM"),
    ("United Arab Emirates", "ARE"),
    ("Bosnia and Herzegovina", "BIH"),
    ("Democratic Republic of the Congo", "COD"),
])
def test_buscar_casa_los_nombres_de_gafi_y_ofac(nombre_fuente: str, esperado: str) -> None:
    """
    Sin esto, un país listado por el GAFI se queda sin clasificar en el mapa
    y sin penalizar en el scoring.
    """
    p = paises.buscar(nombre_fuente)
    assert p is not None, f"'{nombre_fuente}' no casa con el catálogo"
    assert p.iso3 == esperado


def test_buscar_no_adivina() -> None:
    """Ante lo desconocido devuelve None; nunca una coincidencia aproximada."""
    for basura in ("", "   ", "Narnia", "XYZ", "país inventado"):
        assert paises.buscar(basura) is None


# ── Equivalencias heredadas ──────────────────────────────────
def test_todo_valor_del_catalogo_legacy_tiene_equivalencia() -> None:
    """
    Cada opción que la UI ofrece hoy debe poder migrarse.

    Si alguien añade una jurisdicción a Jurisdicciones.ALL sin registrarla
    aquí, la migración la perdería en silencio.
    """
    sin_mapear = [v for v in Jurisdicciones.ALL if v not in EQUIVALENCIAS]
    assert not sin_mapear, f"Valores sin equivalencia declarada: {sin_mapear}"


def test_las_equivalencias_apuntan_a_paises_reales() -> None:
    for legacy, eq in EQUIVALENCIAS.items():
        if eq.iso3 is None:
            continue
        assert eq.iso3 in paises.POR_ISO3, (
            f"{legacy!r} apunta a '{eq.iso3}', que no existe en ISO 3166"
        )


def test_casos_que_la_busqueda_automatica_no_resuelve() -> None:
    """
    Los dos valores que obligaron a hacer la tabla explícita.

    Islas Vírgenes: la ISO las llama 'Británicas', no '(UK)'.
    Panamá (ZLC): es una zona franca, no un país.
    """
    assert paises.buscar("🇻🇬 Islas Vírgenes (UK)") is None
    assert a_iso3("🇻🇬 Islas Vírgenes (UK)") == "VGB"

    assert paises.buscar("🇵🇦 Panamá (ZLC)") is None
    zlc = equivalencia("🇵🇦 Panamá (ZLC)")
    assert zlc.iso3 == "PAN"
    assert zlc.subregion == "Zona Libre de Colón", (
        "la distinción de zona franca no debe perderse en la migración"
    )


def test_a_iso3_devuelve_none_ante_lo_desconocido() -> None:
    assert a_iso3("🇦🇹 Austria") is None
    assert a_iso3("") is None


# ── Coherencia con el riesgo actual ──────────────────────────
def test_alto_riesgo_actual_es_mapeable() -> None:
    """Todo país hoy penalizado debe tener código ISO para el nuevo scoring."""
    for v in Jurisdicciones.ALTO_RIESGO:
        assert a_iso3(v), f"{v!r} está en ALTO_RIESGO pero no se puede mapear a ISO"


def test_lista_negra_gafi_presente_en_el_catalogo() -> None:
    """Irán, Corea del Norte y Myanmar: lista negra vigente en junio de 2026."""
    for iso in ("IRN", "PRK", "MMR"):
        assert iso in paises.POR_ISO3
        assert any(a_iso3(v) == iso for v in Jurisdicciones.ALTO_RIESGO), (
            f"{iso} debería estar penalizado y no lo está"
        )
