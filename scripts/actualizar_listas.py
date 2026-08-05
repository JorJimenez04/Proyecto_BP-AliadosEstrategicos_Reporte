"""
scripts/actualizar_listas.py
Contrasta config/listas_riesgo.json con las fuentes oficiales y reporta diferencias.

POR DEFECTO NO ESCRIBE NADA. Un cambio en estas listas mueve el puntaje de
riesgo de partners reales, así que se revisa antes de aplicarse. Para escribir
hay que pasar --aplicar de forma explícita.

Fuentes:
  · OFAC  — ficheros XML públicos del Sanctions List Service (dominio público)
  · ONU   — lista consolidada del Consejo de Seguridad (XML público)
  · GAFI  — sin API. Solo se comprueba la antigüedad de la verificación manual.

Uso:
    python scripts/actualizar_listas.py                 # informe
    python scripts/actualizar_listas.py --fuente ofac   # solo una fuente
    python scripts/actualizar_listas.py --aplicar       # escribe los cambios

Nota sobre el alcance: OFAC no publica una lista de países en formato
procesable. Lo que sí es procesable son los programas de sanciones asociados a
cada entrada del SDN. De ahí se deduce qué programas por país están activos,
que es lo que interesa para clasificar una jurisdicción.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import requests
from defusedxml import ElementTree as ET

from config import listas_riesgo as LR
from config import paises

SEP = "─" * 68
TIMEOUT = 180  # El SDN de OFAC son decenas de MB; 60s se quedaba corto

FUENTES = {
    "ofac_sdn": "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML",
    "onu":      "https://scsanctions.un.org/resources/xml/en/consolidated.xml",
}

# Programas de OFAC de alcance integral: restringen la jurisdicción completa.
# Los sectoriales o dirigidos (RUSSIA-EO14024, VENEZUELA, BELARUS…) señalan a
# personas y entidades concretas, no al país entero, y por eso no entran en la
# capa 'ofac_integral'.
PROGRAMAS_INTEGRALES: dict[str, str] = {
    "CUBA":   "CUB",
    "IRAN":   "IRN",
    "DPRK":   "PRK",
    "SYRIA":  "SYR",
}


def _descargar(url: str) -> bytes | None:
    """
    Descarga con avisos de progreso.

    El SDN de OFAC pesa decenas de megas: sin estos mensajes la consola queda
    en silencio varios minutos y parece que el script se colgó.
    """
    print(f"  Descargando {url.split('/')[-1]} …", flush=True)
    try:
        r = requests.get(
            url,
            timeout=TIMEOUT,
            headers={"User-Agent": "AdamoServices-Compliance/1.0"},
            stream=True,
        )
        r.raise_for_status()

        trozos = []
        recibido = 0
        siguiente_aviso = 5 * 1024 * 1024
        for trozo in r.iter_content(chunk_size=256 * 1024):
            trozos.append(trozo)
            recibido += len(trozo)
            if recibido >= siguiente_aviso:
                print(f"    {recibido / 1024 / 1024:.0f} MB…", flush=True)
                siguiente_aviso += 5 * 1024 * 1024

        contenido = b"".join(trozos)
        print(f"  Descargado: {len(contenido) / 1024 / 1024:.1f} MB", flush=True)
        return contenido

    except requests.exceptions.Timeout:
        print(f"  ❌ Tiempo agotado tras {TIMEOUT}s. Reintenta o sube TIMEOUT.")
        return None
    except Exception as exc:
        print(f"  ❌ No se pudo descargar: {str(exc)[:140]}")
        return None


def _programas_ofac(xml: bytes) -> Counter[str]:
    """Programas de sanciones presentes en el SDN, con número de entradas."""
    raiz = ET.fromstring(xml)
    conteo: Counter[str] = Counter()
    for elem in raiz.iter():
        if elem.tag.endswith("program") and elem.text:
            conteo[elem.text.strip().upper()] += 1
    return conteo


def _paises_onu(xml: bytes) -> Counter[str]:
    """Nacionalidades presentes en la lista consolidada de la ONU."""
    raiz = ET.fromstring(xml)
    conteo: Counter[str] = Counter()
    for elem in raiz.iter():
        if elem.tag.split("}")[-1] in ("COUNTRY", "NATIONALITY", "VALUE") and elem.text:
            p = paises.buscar(elem.text.strip())
            if p:
                conteo[p.iso3] += 1
    return conteo


def revisar_ofac() -> set[str]:
    """Devuelve los ISO-3 con programa integral activo según el SDN."""
    print(f"\n{SEP}\nOFAC · Specially Designated Nationals\n{SEP}")
    xml = _descargar(FUENTES["ofac_sdn"])
    if not xml:
        return set()

    programas = _programas_ofac(xml)
    print(f"  Entradas por programa: {sum(programas.values())} en {len(programas)} programas\n")

    integrales: set[str] = set()
    for prog, iso in sorted(PROGRAMAS_INTEGRALES.items()):
        n = programas.get(prog, 0)
        estado = f"{n} entradas" if n else "sin entradas — ¿programa retirado?"
        print(f"  {'✓' if n else '?'}  {prog:<10} → {iso}  {paises.nombre(iso):<20} {estado}")
        if n:
            integrales.add(iso)

    otros = [p for p in programas if p not in PROGRAMAS_INTEGRALES]
    print(f"\n  Otros {len(otros)} programas son sectoriales o dirigidos y no")
    print("  restringen la jurisdicción completa. Muestra:")
    for prog, n in Counter({p: programas[p] for p in otros}).most_common(6):
        print(f"    {prog:<28} {n:>5} entradas")

    return integrales


def revisar_onu() -> None:
    print(f"\n{SEP}\nONU · Lista consolidada del Consejo de Seguridad\n{SEP}")
    xml = _descargar(FUENTES["onu"])
    if not xml:
        return
    conteo = _paises_onu(xml)
    print(f"  {sum(conteo.values())} referencias a país en {len(conteo)} jurisdicciones\n")
    print("  Más referenciadas:")
    for iso, n in conteo.most_common(10):
        marca = "señalada" if LR.capa_dominante(iso) else ""
        print(f"    {iso}  {paises.nombre(iso):<28} {n:>4}  {marca}")
    print("\n  La lista de la ONU señala personas y entidades, no jurisdicciones.")
    print("  Se muestra como contexto; no modifica la clasificación por país.")


def revisar_gafi() -> None:
    print(f"\n{SEP}\nGAFI · Listas negra y gris\n{SEP}")
    dias = LR.dias_desde_verificacion()
    nivel, mensaje = LR.estado_verificacion()
    print(f"  Última verificación: {LR.verificado()}  ({dias} días)")
    print(f"  {'⚠️ ' if nivel == 'warn' else '✓  '}{mensaje}")
    if nivel == "warn":
        print("\n  El GAFI no publica API. Revisar a mano:")
        for clave in ("gafi_negra", "gafi_gris"):
            capa = LR.capas().get(clave)
            if capa:
                print(f"    {capa.fuente}")
        print("\n  Tras contrastar, actualizar 'paises' y 'verificado' en")
        print("  config/listas_riesgo.json y ejecutar los tests.")


def comparar(integrales_ofac: set[str]) -> list[tuple[str, str, str]]:
    """Diferencias entre lo descargado y lo guardado. (accion, iso, motivo)"""
    guardado = LR.capas()["ofac_integral"].paises
    cambios = []
    for iso in sorted(integrales_ofac - guardado):
        cambios.append(("añadir", iso, "programa integral activo en el SDN"))
    for iso in sorted(guardado - integrales_ofac):
        cambios.append(("quitar", iso, "sin entradas en el SDN"))
    return cambios


def aplicar(cambios: list[tuple[str, str, str]]) -> None:
    datos = json.loads(LR.RUTA_DATASET.read_text(encoding="utf-8"))
    capa = datos["capas"]["ofac_integral"]
    actuales = set(capa["paises"])
    for accion, iso, _ in cambios:
        if accion == "añadir":
            actuales.add(iso)
        else:
            actuales.discard(iso)
    capa["paises"] = sorted(actuales)
    capa["verificado"] = date.today().isoformat()
    datos["verificado"] = date.today().isoformat()
    LR.RUTA_DATASET.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\n✅ Aplicados {len(cambios)} cambios en {LR.RUTA_DATASET.name}")
    print("   Ejecuta los tests antes de subir:  python -m pytest tests/ -q")


def main() -> None:
    argv = sys.argv[1:]
    solo = None
    for i, a in enumerate(argv):
        if a == "--fuente" and i + 1 < len(argv):
            solo = argv[i + 1].lower()
    escribir = "--aplicar" in argv

    print(f"\n{SEP}")
    print("CONTRASTE DE LISTAS DE RIESGO")
    print(f"Dataset: {LR.RUTA_DATASET.relative_to(RAIZ)}  ·  verificado {LR.verificado()}")
    print(SEP)

    integrales: set[str] = set()
    if solo in (None, "gafi", "todas"):
        revisar_gafi()
    if solo in (None, "ofac", "todas"):
        integrales = revisar_ofac()
    if solo in (None, "onu", "todas"):
        revisar_onu()

    if solo in (None, "ofac", "todas"):
        cambios = comparar(integrales)
        print(f"\n{SEP}\nDIFERENCIAS DETECTADAS\n{SEP}")
        if not cambios:
            print("  Ninguna. El dataset coincide con la fuente.")
        else:
            for accion, iso, motivo in cambios:
                print(f"  {accion.upper():<7} {iso}  {paises.nombre(iso):<24} {motivo}")
            if escribir:
                aplicar(cambios)
            else:
                print("\n  No se ha modificado nada. Para aplicarlos:")
                print("    python scripts/actualizar_listas.py --aplicar")

    print()


if __name__ == "__main__":
    main()
