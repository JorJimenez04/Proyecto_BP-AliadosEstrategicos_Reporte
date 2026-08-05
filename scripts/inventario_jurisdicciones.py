"""
scripts/inventario_jurisdicciones.py
Inventario de lo que hay realmente guardado en las columnas de jurisdicciones.

SOLO LECTURA. No modifica ni una fila. Su función es responder, antes de migrar,
a tres preguntas:

  1. ¿Qué valores existen de verdad en la base? (no los que declara el catálogo)
  2. ¿Cuáles no tienen equivalencia ISO y hay que decidir a mano?
  3. ¿Qué partners cambiarían de puntaje si el scoring pasara a leer del GAFI real?

Uso:
    python scripts/inventario_jurisdicciones.py
    python scripts/inventario_jurisdicciones.py --database-url postgresql://...

Si no puedes conectarte desde tu equipo, ejecútalo desde la consola del
servicio Postgres en Railway, donde la red no es un problema.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from sqlalchemy import text

from config import paises
from config.jurisdicciones_legacy import EQUIVALENCIAS, equivalencia
from config.settings import Jurisdicciones
from scripts._db_target import crear_engine

# Tablas con columna jurisdicciones TEXT[]
TABLAS = [("aliados", "nombre_razon_social"), ("clientes", "nombre_razon_social")]

SEP = "─" * 66


def _existe_tabla(conn, tabla: str) -> bool:
    return bool(conn.execute(text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = :t"
    ), {"t": tabla}).fetchone())


def _tiene_columna(conn, tabla: str, columna: str) -> bool:
    return bool(conn.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = :c"
    ), {"t": tabla, "c": columna}).fetchone())


def main() -> None:
    engine, destino = crear_engine()
    print(f"\n🎯 Destino : {destino}")
    print("🔒 Modo    : solo lectura\n")

    conteo_global: Counter[str] = Counter()
    filas_por_tabla: dict[str, int] = {}

    with engine.connect() as conn:
        for tabla, col_nombre in TABLAS:
            if not _existe_tabla(conn, tabla):
                print(f"⚠️  Tabla '{tabla}' no existe — se omite")
                continue
            if not _tiene_columna(conn, tabla, "jurisdicciones"):
                print(f"⚠️  '{tabla}' no tiene columna jurisdicciones — se omite")
                continue

            filas = conn.execute(text(
                f"SELECT id, {col_nombre} AS nombre, jurisdicciones FROM {tabla}"
            )).fetchall()
            filas_por_tabla[tabla] = len(filas)

            local: Counter[str] = Counter()
            sin_juris = 0
            for f in filas:
                vals = f.jurisdicciones or []
                if not vals:
                    sin_juris += 1
                for v in vals:
                    local[v] += 1
                    conteo_global[v] += 1

            print(SEP)
            print(f"TABLA {tabla}  ·  {len(filas)} registros  ·  {sin_juris} sin jurisdicciones")
            print(SEP)
            for valor, n in local.most_common():
                eq = equivalencia(valor)
                if eq and eq.iso3:
                    destino_txt = eq.iso3 + (f" · {eq.subregion}" if eq.subregion else "")
                    marca = "OK"
                else:
                    auto = paises.buscar(valor)
                    destino_txt = f"{auto.iso3} (por nombre)" if auto else "SIN EQUIVALENCIA"
                    marca = "??" if not auto else "~ "
                print(f"  {marca}  {n:>4}×  {valor:<32} → {destino_txt}")
            print()

    if not conteo_global:
        print("No se encontraron jurisdicciones registradas.\n")
        return

    # ── Valores fuera del catálogo declarado ──────────────────
    print(SEP)
    print("VALORES EN BASE QUE NO ESTÁN EN Jurisdicciones.ALL")
    print(SEP)
    huerfanos = [v for v in conteo_global if v not in Jurisdicciones.ALL]
    if huerfanos:
        for v in sorted(huerfanos):
            print(f"  {conteo_global[v]:>4}×  {v!r}")
        print("\n  Son valores que la UI ya no ofrece pero siguen guardados.")
    else:
        print("  Ninguno — la base solo contiene valores del catálogo.\n")

    # ── Sin equivalencia ISO ──────────────────────────────────
    print(SEP)
    print("SIN EQUIVALENCIA ISO — requieren decisión")
    print(SEP)
    pendientes = [
        v for v in conteo_global
        if not (equivalencia(v) and equivalencia(v).iso3) and not paises.buscar(v)
    ]
    if pendientes:
        for v in sorted(pendientes):
            print(f"  {conteo_global[v]:>4}×  {v!r}")
    else:
        print("  Ninguno — todos los valores en uso tienen destino ISO.")

    # ── Impacto en el scoring ─────────────────────────────────
    print()
    print(SEP)
    print("IMPACTO POTENCIAL EN EL SCORING")
    print(SEP)
    en_alto_riesgo_actual = {
        v: n for v, n in conteo_global.items() if v in Jurisdicciones.ALTO_RIESGO
    }
    print("  Penalizados hoy por ALTO_RIESGO:")
    if en_alto_riesgo_actual:
        for v, n in sorted(en_alto_riesgo_actual.items(), key=lambda x: -x[1]):
            print(f"    {n:>4}×  {v}")
    else:
        print("    ninguno")

    # Lista negra GAFI vigente (junio 2026) — se moverá al dataset en la fase 2
    negra_gafi = {"IRN", "PRK", "MMR"}
    penalizados_iso = {
        (equivalencia(v).iso3 if equivalencia(v) else None)
        for v in en_alto_riesgo_actual
    }
    fuera_de_gafi = sorted(c for c in penalizados_iso if c and c not in negra_gafi)
    if fuera_de_gafi:
        print("\n  Penalizados sin estar en la lista negra del GAFI:")
        for c in fuera_de_gafi:
            print(f"    {c}  {paises.nombre(c)}")
        print("    → decidir si se mantienen como política interna")

    print(f"\n{SEP}")
    print(f"Registros analizados: {sum(filas_por_tabla.values())}")
    print(f"Valores distintos:    {len(conteo_global)}")
    print(f"Equivalencias declaradas: {len(EQUIVALENCIAS)}")
    print(f"{SEP}\n")


if __name__ == "__main__":
    main()
