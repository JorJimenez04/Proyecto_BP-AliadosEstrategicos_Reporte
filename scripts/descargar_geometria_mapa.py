"""
scripts/descargar_geometria_mapa.py
Descarga la geometría del mapa mundial para servirla desde la propia aplicación.

Por qué hace falta: Plotly reparte el trabajo en dos. El servidor manda los
códigos de país y sus colores; el navegador tiene que dibujar las fronteras, y
para eso pide la geometría a cdn.plot.ly en el momento de renderizar. Es una
petición a un tercero que ni controlas ni está en tu repositorio.

Si esa petición falla —CDN caído, cortafuegos corporativo, red restringida—
llegan los colores pero no las formas: el mapa sale vacío con la leyenda
debajo. Para una herramienta de compliance, que suele usarse justo en redes
de banca, es una dependencia difícil de justificar.

Este script trae los ficheros una vez y los deja en app/static/topojson/,
que Streamlit sirve como estáticos. A partir de ahí el navegador los pide a
tu propia aplicación.

Uso:
    python scripts/descargar_geometria_mapa.py

Ejecutar de nuevo solo si actualizas la versión de Plotly. Las fronteras
cambian cada muchos años; la geometría no es un dato que caduque.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import requests

DESTINO = RAIZ / "app" / "static" / "topojson"

# Misma versión que empaqueta plotly.py, servida por un CDN de paquetes npm.
VERSION_PLOTLYJS = "2.27.0"
BASE = f"https://cdn.jsdelivr.net/npm/plotly.js@{VERSION_PLOTLYJS}/dist/topojson"

# El mapa mundial usa la resolución 110m. La 50m tiene más detalle en costas y
# fronteras pequeñas, pero pesa unas cuatro veces más y a escala mundial no se
# aprecia. Se descargan ambas para poder cambiar sin volver aquí.
FICHEROS = [
    "world_110m.json",
    "world_50m.json",
]

TIMEOUT = 120


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    print(f"\nDestino: {DESTINO.relative_to(RAIZ)}")
    print(f"Origen : {BASE}\n")

    total = 0
    fallos = 0

    for nombre in FICHEROS:
        url = f"{BASE}/{nombre}"
        salida = DESTINO / nombre
        print(f"  {nombre} …", end="", flush=True)
        try:
            r = requests.get(url, timeout=TIMEOUT)
            r.raise_for_status()

            # Comprobación mínima de que llegó geometría y no una página de error
            if not r.content.lstrip().startswith(b"{"):
                print(" ❌ la respuesta no es JSON")
                fallos += 1
                continue

            salida.write_bytes(r.content)
            kb = len(r.content) / 1024
            total += len(r.content)
            print(f" {kb:,.0f} KB")

        except Exception as exc:
            print(f" ❌ {str(exc)[:100]}")
            fallos += 1

    print()
    if fallos:
        print(f"❌ {fallos} fichero(s) no se pudieron descargar.")
        print("   El mapa seguirá funcionando con el CDN de Plotly como hasta ahora.")
        sys.exit(1)

    print(f"✅ Geometría descargada — {total / 1024:,.0f} KB en total")
    print("\n   La aplicación la detecta sola: si los ficheros están, los usa;")
    print("   si no, cae al CDN de Plotly. No hay que tocar código.")
    print("\n   Recuerda incluirlos en el commit:  git add app/static/topojson\n")


if __name__ == "__main__":
    main()
