"""
tests/test_scoring_jurisdicciones.py
Scoring de riesgo por jurisdicción, separado en capas.

Protegen dos correcciones concretas:

  1. Antes existía un único ALTO_RIESGO que fundía listados GAFI, sanciones
     OFAC y política interna sobre offshore. Operar en Irán pesaba lo mismo
     que operar en Islas Caimán, y la app afirmaba que el GAFI señalaba a
     Caimán, cosa falsa desde octubre de 2023.

  2. Un partner sin jurisdicciones sumaba cero en ese bloque, exactamente
     igual que uno que solo opera en Colombia. La falta de datos se leía
     como ausencia de riesgo.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://smoke:smoke@localhost:5432/smoke")

from config import listas_riesgo as LR
from config.settings import Jurisdicciones as J
from db.repositories.partner_repo import (
    _RISK_WEIGHTS,
    calcular_puntaje_riesgo,
    calificacion_incompleta,
)

PESO = {clave: capa.peso for clave, capa in LR.capas().items()}

# Partner sin ningún otro factor de riesgo: aísla el efecto de la jurisdicción
BASE = dict(
    contrato_firmado=True,
    rut_recibido=True,
    camara_comercio_recibida=True,
    listas_verificadas=True,
    lista_ofac_ok=True,
    estado_due_diligence="Aprobado",
    estado_sarlaft="Al Día",
)


def _score(jurisdicciones: list[str]) -> float:
    return calcular_puntaje_riesgo({**BASE, "jurisdicciones": jurisdicciones})[0]


# ── Dataset ──────────────────────────────────────────────────
def test_el_dataset_tiene_las_cuatro_capas() -> None:
    assert set(LR.capas()) == {
        "gafi_negra", "ofac_integral", "gafi_gris", "politica_interna"
    }


def test_lista_gris_tiene_las_22_jurisdicciones() -> None:
    """
    Cifra oficial tras la plenaria del 19/06/2026.

    Los agregadores de terceros publicaban listas contradictorias — uno decía
    22 y a continuación enumeraba más de treinta, incluyendo países ya
    retirados como Panamá. El dataset se construye desde fatf-gafi.org.
    """
    assert len(LR.capas()["gafi_gris"].paises) == 22


def test_paises_que_los_agregadores_omitian() -> None:
    """Venezuela e Islas Vírgenes (UK) sí están en la lista gris del GAFI."""
    gris = LR.capas()["gafi_gris"].paises
    for iso in ("VEN", "VGB", "MCO", "BGR", "NPL"):
        assert iso in gris, f"{iso} falta en la lista gris"


def test_panama_no_esta_en_ninguna_capa() -> None:
    """Salió de la lista gris. Penalizarlo sería un falso positivo."""
    assert LR.capa_dominante("PAN") is None


def test_cada_capa_declara_su_fuente() -> None:
    for capa in LR.capas().values():
        assert capa.fuente, f"{capa.clave} sin fuente declarada"
        assert capa.verificado, f"{capa.clave} sin fecha de verificación"
        assert capa.peso > 0


def test_alto_riesgo_es_la_union_de_las_capas() -> None:
    """Se mantiene por compatibilidad; debe seguir cuadrando."""
    union = (
        J.LISTA_NEGRA_GAFI | J.LISTA_GRIS_GAFI
        | J.SANCIONES_INTERNACIONALES | J.OFFSHORE_POLITICA_INTERNA
    )
    assert J.ALTO_RIESGO == union


def test_lista_negra_es_la_del_gafi_vigente() -> None:
    """Junio de 2026: sin cambios desde febrero de 2020."""
    assert J.LISTA_NEGRA_GAFI == frozenset({
        "🇮🇷 Irán", "🇰🇵 Corea del Norte", "🇲🇲 Myanmar",
    })


def test_un_pais_puede_estar_en_varias_capas() -> None:
    """
    Irán está en la lista negra del GAFI y además tiene programa integral de
    OFAC. Son dos hechos distintos y ambos deben poder mostrarse.
    """
    capas_iran = J.capas_de("🇮🇷 Irán")
    assert "gafi_negra" in capas_iran
    assert "ofac_integral" in capas_iran
    # Para el cálculo manda la más severa
    assert J.capa_de("🇮🇷 Irán") == "gafi_negra"


def test_bolivia_penalizada_como_haiti() -> None:
    """
    Ambas están en la lista gris del GAFI. Antes se penalizaba Haití y no
    Bolivia, lo que dejaba un partner boliviano infravalorado.
    """
    assert "🇧🇴 Bolivia" in J.LISTA_GRIS_GAFI
    assert "🇭🇹 Haití" in J.LISTA_GRIS_GAFI
    assert _score(["🇧🇴 Bolivia"]) == _score(["🇭🇹 Haití"])


def test_offshore_no_se_atribuye_al_gafi() -> None:
    """
    Islas Caimán salió de la lista gris en 2023 y Bahamas en 2020.
    Siguen penalizadas, pero como política interna declarada.
    """
    for offshore in ("🇰🇾 Islas Caimán", "🇧🇸 Bahamas", "🇧🇲 Bermuda"):
        assert offshore in J.OFFSHORE_POLITICA_INTERNA
        assert offshore not in J.LISTA_NEGRA_GAFI
        assert offshore not in J.LISTA_GRIS_GAFI
        assert J.capa_de(offshore) == "politica_interna"


def test_venezuela_y_vgb_son_lista_gris_no_politica_interna() -> None:
    """
    Corrección de agosto de 2026. Las webs agregadoras las omitían de la lista
    gris; la página oficial del GAFI las incluye. Islas Vírgenes (UK) estaba
    clasificada como offshore por decisión propia cuando en realidad hay
    señalamiento oficial, que pesa casi el doble.
    """
    for pais in ("🇻🇪 Venezuela", "🇻🇬 Islas Vírgenes (UK)"):
        assert J.capa_de(pais) == "gafi_gris"
        assert pais in J.LISTA_GRIS_GAFI
        assert pais not in J.OFFSHORE_POLITICA_INTERNA


def test_cuba_es_sancion_sin_señalamiento_gafi() -> None:
    """Motivo geopolítico, no deficiencia antilavado."""
    assert J.capa_de("🇨🇺 Cuba") == "ofac_integral"
    assert "🇨🇺 Cuba" not in J.LISTA_GRIS_GAFI


def test_capa_de_devuelve_none_si_no_penaliza() -> None:
    assert J.capa_de("🇨🇴 Colombia") is None
    assert J.capa_de("🇪🇸 España") is None
    assert J.capa_de("país inexistente") is None


# ── Jerarquía de pesos ───────────────────────────────────────
def test_la_severidad_se_refleja_en_el_puntaje() -> None:
    """
    Relación prohibida con contramedidas obligatorias no puede pesar lo mismo
    que un centro offshore. Antes ambos sumaban 15.
    """
    negra    = _score(["🇮🇷 Irán"])
    sancion  = _score(["🇨🇺 Cuba"])
    gris     = _score(["🇧🇴 Bolivia"])
    offshore = _score(["🇰🇾 Islas Caimán"])

    assert negra > sancion > gris > offshore > 0


@pytest.mark.parametrize("jurisdiccion,capa", [
    ("🇮🇷 Irán",           "gafi_negra"),
    ("🇨🇺 Cuba",           "ofac_integral"),
    ("🇧🇴 Bolivia",        "gafi_gris"),
    ("🇰🇾 Islas Caimán",   "politica_interna"),
])
def test_cada_capa_aporta_su_peso(jurisdiccion: str, capa: str) -> None:
    assert _score([jurisdiccion]) == PESO[capa]


def test_solo_pesa_la_capa_mas_severa() -> None:
    """
    Un partner en Irán y en Islas Caimán tiene el riesgo de Irán, no la suma.
    Sumar capas inflaría el puntaje sin reflejar una realidad distinta.
    """
    esperado = PESO["gafi_negra"] + _RISK_WEIGHTS["jurisdiccion_multiple_riesgo"]
    assert _score(["🇮🇷 Irán", "🇰🇾 Islas Caimán"]) == esperado


def test_recargo_por_varias_jurisdicciones_señaladas() -> None:
    una = _score(["🇧🇴 Bolivia"])
    dos = _score(["🇧🇴 Bolivia", "🇭🇹 Haití"])
    assert dos == una + _RISK_WEIGHTS["jurisdiccion_multiple_riesgo"]


def test_jurisdicciones_limpias_no_penalizan() -> None:
    assert _score(["🇨🇴 Colombia"]) == 0
    assert _score(["🇨🇴 Colombia", "🇲🇽 México", "🇪🇸 España"]) == 0


def test_diversificacion_amplia_suma() -> None:
    """5+ jurisdicciones implica exposición aunque ninguna esté señalada."""
    muchas = ["🇨🇴 Colombia", "🇲🇽 México", "🇪🇸 España", "🇧🇷 Brasil", "🇨🇱 Chile"]
    assert _score(muchas) == _RISK_WEIGHTS["jurisdiccion_exposicion"]


# ── Calificación incompleta ──────────────────────────────────
def test_sin_jurisdicciones_se_marca_incompleta() -> None:
    faltantes = calificacion_incompleta({**BASE, "jurisdicciones": []})
    assert faltantes == ["Jurisdicciones de operación"]


def test_con_jurisdicciones_la_calificacion_esta_completa() -> None:
    assert calificacion_incompleta({**BASE, "jurisdicciones": ["🇨🇴 Colombia"]}) == []


def test_el_vacio_puntua_igual_que_lo_limpio_pero_queda_señalado() -> None:
    """
    El puntaje no puede distinguirlos —no hay información para hacerlo—, y
    justo por eso hace falta la marca: sin ella, 'no sabemos' se presenta
    como 'riesgo bajo'.
    """
    vacio = {**BASE, "jurisdicciones": []}
    limpio = {**BASE, "jurisdicciones": ["🇨🇴 Colombia"]}

    assert calcular_puntaje_riesgo(vacio)[0] == calcular_puntaje_riesgo(limpio)[0]
    assert calificacion_incompleta(vacio)
    assert not calificacion_incompleta(limpio)


def test_campo_ausente_cuenta_como_faltante() -> None:
    """No es lo mismo lista vacía que campo que ni siquiera viene."""
    assert calificacion_incompleta(dict(BASE)) == ["Jurisdicciones de operación"]
    assert calificacion_incompleta({**BASE, "jurisdicciones": None})
