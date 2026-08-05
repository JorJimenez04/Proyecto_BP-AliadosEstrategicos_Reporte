"""
tests/test_listas_riesgo.py
Dataset de listas de riesgo y su vigencia.

El dataset alimenta el puntaje de riesgo de partners y clientes. Un error aquí
no rompe la aplicación: la deja calculando mal en silencio.
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://smoke:smoke@localhost:5432/smoke")

from config import listas_riesgo as LR
from config import paises


# ── Integridad ───────────────────────────────────────────────
def test_el_dataset_es_json_valido() -> None:
    datos = json.loads(LR.RUTA_DATASET.read_text(encoding="utf-8"))
    assert "capas" in datos
    assert "verificado" in datos


def test_todo_codigo_del_dataset_existe_en_iso_3166() -> None:
    """
    Un código inventado deja al país fuera del mapa y sin penalizar, sin dar
    ningún error visible.
    """
    for capa in LR.capas().values():
        for iso in capa.paises:
            assert iso in paises.POR_ISO3, (
                f"'{iso}' en la capa {capa.clave} no es un código ISO 3166 válido"
            )


def test_no_hay_codigos_repetidos_dentro_de_una_capa() -> None:
    datos = json.loads(LR.RUTA_DATASET.read_text(encoding="utf-8"))
    for clave, capa in datos["capas"].items():
        lista = capa["paises"]
        assert len(lista) == len(set(lista)), f"códigos repetidos en {clave}"


def test_los_pesos_respetan_la_severidad() -> None:
    """El orden de ORDEN_SEVERIDAD debe corresponderse con los pesos."""
    pesos = [LR.capas()[c].peso for c in LR.ORDEN_SEVERIDAD if c in LR.capas()]
    assert pesos == sorted(pesos, reverse=True), (
        f"una capa más severa pesa menos que otra menos severa: {pesos}"
    )


def test_cada_capa_declara_fuente_y_fecha() -> None:
    for capa in LR.capas().values():
        assert capa.fuente, f"{capa.clave} sin fuente"
        assert capa.verificado, f"{capa.clave} sin fecha de verificación"
        # La fecha debe ser parseable
        date.fromisoformat(capa.verificado)


# ── Consultas ────────────────────────────────────────────────
def test_capa_dominante_es_la_mas_severa() -> None:
    """Irán está en lista negra del GAFI y en programa integral de OFAC."""
    todas = [c.clave for c in LR.capas_de("IRN")]
    assert "gafi_negra" in todas
    assert "ofac_integral" in todas
    assert LR.capa_dominante("IRN").clave == "gafi_negra"


def test_peso_de_usa_la_capa_dominante() -> None:
    assert LR.peso_de("IRN") == LR.capas()["gafi_negra"].peso
    assert LR.peso_de("CUB") == LR.capas()["ofac_integral"].peso
    assert LR.peso_de("BOL") == LR.capas()["gafi_gris"].peso
    assert LR.peso_de("CYM") == LR.capas()["politica_interna"].peso


def test_pais_limpio_no_pesa() -> None:
    for iso in ("COL", "ESP", "MEX", "PAN"):
        assert LR.capa_dominante(iso) is None
        assert LR.peso_de(iso) == 0


def test_consultas_toleran_entradas_invalidas() -> None:
    assert LR.capas_de("") == []
    assert LR.capa_dominante("XXX") is None
    assert LR.peso_de("no es un codigo") == 0


def test_mayusculas_y_minusculas_dan_igual() -> None:
    assert LR.capa_dominante("irn") is LR.capa_dominante("IRN")


def test_paises_senalados_reune_todas_las_capas() -> None:
    señalados = LR.paises_senalados()
    for capa in LR.capas().values():
        assert capa.paises <= señalados


# ── Vigencia ─────────────────────────────────────────────────
def test_el_dataset_esta_verificado_hoy() -> None:
    """Si este test falla es que toca contrastar contra las fuentes."""
    assert not LR.verificacion_caducada(), (
        f"El dataset lleva {LR.dias_desde_verificacion()} días sin verificar. "
        "Ejecuta: python scripts/actualizar_listas.py"
    )


def test_estado_verificacion_avisa_al_caducar() -> None:
    nivel, mensaje = LR.estado_verificacion()
    assert nivel in ("ok", "warn")
    assert mensaje


def test_la_fecha_de_verificacion_no_esta_en_el_futuro() -> None:
    y, m, d = (int(x) for x in LR.verificado().split("-"))
    assert date(y, m, d) <= date.today(), "fecha de verificación en el futuro"


def test_dias_desde_verificacion_es_coherente() -> None:
    dias = LR.dias_desde_verificacion()
    assert dias >= 0
    assert dias == (date.today() - date.fromisoformat(LR.verificado())).days


# ── Reglas de negocio del dataset ────────────────────────────
def test_la_capa_de_politica_interna_no_pisa_listados_oficiales() -> None:
    """
    Si un país entra en una lista oficial, debe salir de la capa interna:
    mantenerlo en ambas lo dejaría con el peso menor de las dos.
    """
    interna = LR.capas()["politica_interna"].paises
    oficiales = (
        LR.capas()["gafi_negra"].paises
        | LR.capas()["gafi_gris"].paises
        | LR.capas()["ofac_integral"].paises
    )
    solapan = interna & oficiales
    assert not solapan, (
        f"{solapan} está en política interna y además en una lista oficial; "
        "debe quedarse solo en la oficial"
    )


def test_la_lista_negra_pesa_mas_que_cualquier_otra() -> None:
    negra = LR.capas()["gafi_negra"].peso
    for clave, capa in LR.capas().items():
        if clave != "gafi_negra":
            assert negra > capa.peso
