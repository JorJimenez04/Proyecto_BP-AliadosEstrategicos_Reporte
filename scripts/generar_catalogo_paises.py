"""
scripts/generar_catalogo_paises.py
Genera config/paises.py a partir del estándar ISO 3166-1.

Se ejecuta una sola vez (o cuando la ISO publique cambios, que es raro).
El fichero generado no tiene dependencias en runtime: pycountry solo hace
falta aquí, no en producción.

Uso:
    pip install pycountry
    python scripts/generar_catalogo_paises.py

El script verifica antes de escribir:
  · que los 249 códigos queden asignados a exactamente una región
  · que no haya códigos inventados en las listas de regiones
"""

from __future__ import annotations

import gettext
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

try:
    import pycountry
except ImportError:
    print("❌ Falta pycountry. Instálalo solo para generar:  pip install pycountry")
    sys.exit(1)

SALIDA = RAIZ / "config" / "paises.py"

# ── Regiones ─────────────────────────────────────────────────
# Agrupación operativa, no política. 'Caribe y Offshore' separa los centros
# financieros del resto de América porque es la distinción que usa compliance.
REGIONES: dict[str, str] = {
    "África": """
        DZA AGO BEN BWA BFA BDI CPV CMR CAF TCD COM COG COD CIV DJI EGY GNQ
        ERI SWZ ETH GAB GMB GHA GIN GNB KEN LSO LBR LBY MDG MWI MLI MRT MUS
        MAR MOZ NAM NER NGA RWA STP SEN SYC SLE SOM ZAF SSD SDN TZA TGO TUN
        UGA ZMB ZWE ESH MYT REU SHN IOT ATF
    """,
    "Europa": """
        ALB AND AUT BLR BEL BIH BGR HRV CYP CZE DNK EST FIN FRA DEU GRC HUN
        ISL IRL ITA LVA LIE LTU LUX MLT MDA MCO MNE NLD MKD NOR POL PRT ROU
        RUS SMR SRB SVK SVN ESP SWE CHE UKR GBR VAT FRO GIB GGY IMN JEY ALA
        SJM
    """,
    "Asia": """
        AFG ARM AZE BHR BGD BTN BRN KHM CHN GEO IND IDN IRN IRQ ISR JPN JOR
        KAZ KWT KGZ LAO LBN MYS MDV MNG MMR NPL PRK OMN PAK PSE PHL QAT SAU
        SGP KOR LKA SYR TWN TJK THA TLS TUR TKM ARE UZB VNM YEM HKG MAC CCK
        CXR
    """,
    "Norteamérica": "CAN USA MEX GRL SPM BMU",
    "Latinoamérica": """
        ARG BLZ BOL BRA CHL COL CRI ECU SLV GTM GUY HND NIC PAN PRY PER SUR
        URY VEN GUF
    """,
    "Caribe y Offshore": """
        ATG BHS BRB CUB DMA DOM GRD HTI JAM KNA LCA VCT TTO AIA ABW BES VGB
        CYM CUW GLP MTQ MSR PRI BLM MAF SXM TCA VIR
    """,
    "Oceanía": """
        AUS FJI KIR MHL FSM NRU NZL PLW PNG WSM SLB TON TUV VUT ASM COK PYF
        GUM NCL NIU NFK MNP PCN TKL UMI WLF
    """,
    "Otros": "ATA FLK SGS HMD BVT",
}

# ── Nombres de uso común ─────────────────────────────────────
# La ISO usa denominaciones oficiales que nadie escribe en un formulario.
NOMBRES_ES: dict[str, str] = {
    "PRK": "Corea del Norte",
    "KOR": "Corea del Sur",
    "MMR": "Myanmar",
    "BOL": "Bolivia",
    "VEN": "Venezuela",
    "IRN": "Irán",
    "SYR": "Siria",
    "TZA": "Tanzania",
    "MDA": "Moldavia",
    "LAO": "Laos",
    "VNM": "Vietnam",
    "BRN": "Brunéi",
    "GBR": "Reino Unido",
    "USA": "Estados Unidos",
    "RUS": "Rusia",
    "CZE": "Chequia",
    "VAT": "Ciudad del Vaticano",
    "PSE": "Palestina",
    "TWN": "Taiwán",
    "COD": "República Democrática del Congo",
    "COG": "República del Congo",
    "CIV": "Costa de Marfil",
    "CPV": "Cabo Verde",
    "SWZ": "Esuatini",
    "MKD": "Macedonia del Norte",
    "TLS": "Timor Oriental",
    "FSM": "Micronesia",
    "VGB": "Islas Vírgenes Británicas",
    "VIR": "Islas Vírgenes de EE. UU.",
    "BES": "Caribe Neerlandés",
    "SXM": "Sint Maarten",
    "MAF": "San Martín",
    "BLM": "San Bartolomé",
    "SHN": "Santa Elena",
    "STP": "Santo Tomé y Príncipe",
    "TCA": "Islas Turcas y Caicos",
    "FLK": "Islas Malvinas",
    "SJM": "Svalbard y Jan Mayen",
    "ATF": "Tierras Australes Francesas",
    "SGS": "Georgia del Sur",
    "UMI": "Islas menores de EE. UU.",
    "IOT": "Territorio Británico del Océano Índico",
    "CCK": "Islas Cocos",
    "CXR": "Isla de Navidad",
    "ALA": "Åland",
    "GGY": "Guernsey",
    "IMN": "Isla de Man",
}


# ── Alias ────────────────────────────────────────────────────
# Denominaciones cortas con las que el GAFI, OFAC y la UE nombran a los países
# en sus publicaciones. Sin esto, casar "Iran" o "North Korea" con el catálogo
# falla y el país se queda sin clasificar en el mapa.
ALIAS: dict[str, str] = {
    "iran": "IRN", "islamic republic of iran": "IRN",
    "north korea": "PRK", "dprk": "PRK",
    "democratic people's republic of korea": "PRK",
    "south korea": "KOR", "republic of korea": "KOR",
    "burma": "MMR",
    "russia": "RUS", "russian federation": "RUS",
    "syria": "SYR", "syrian arab republic": "SYR",
    "bolivia": "BOL", "venezuela": "VEN",
    "tanzania": "TZA", "united republic of tanzania": "TZA",
    "laos": "LAO", "lao people's democratic republic": "LAO",
    "moldova": "MDA", "republic of moldova": "MDA",
    "vietnam": "VNM", "viet nam": "VNM",
    "brunei": "BRN", "brunei darussalam": "BRN",
    "united kingdom": "GBR", "uk": "GBR", "great britain": "GBR",
    "united states": "USA", "usa": "USA", "united states of america": "USA",
    "czechia": "CZE", "czech republic": "CZE",
    "palestine": "PSE", "state of palestine": "PSE",
    "taiwan": "TWN",
    "turkey": "TUR", "turkiye": "TUR", "türkiye": "TUR",
    "united arab emirates": "ARE", "uae": "ARE",
    "democratic republic of the congo": "COD", "dr congo": "COD",
    "congo, democratic republic of the": "COD",
    "republic of the congo": "COG", "congo": "COG",
    "ivory coast": "CIV", "cote d'ivoire": "CIV", "côte d'ivoire": "CIV",
    "cote d ivoire": "CIV",
    "cape verde": "CPV", "cabo verde": "CPV",
    "eswatini": "SWZ", "swaziland": "SWZ",
    "north macedonia": "MKD", "macedonia": "MKD",
    "east timor": "TLS", "timor-leste": "TLS",
    "micronesia": "FSM",
    "cayman islands": "CYM",
    "british virgin islands": "VGB", "virgin islands (uk)": "VGB",
    "bosnia and herzegovina": "BIH", "bosnia": "BIH",
    "vatican": "VAT", "holy see": "VAT",
    "netherlands": "NLD", "holland": "NLD",
    "bahamas": "BHS", "the bahamas": "BHS",
    "gambia": "GMB", "the gambia": "GMB",
    "philippines": "PHL", "the philippines": "PHL",
    "sudan": "SDN", "south sudan": "SSD",
}


def _expandir(codigos: str) -> list[str]:
    return codigos.split()


def main() -> None:
    es = gettext.translation("iso3166-1", pycountry.LOCALES_DIR, languages=["es"])

    # ── Verificar la asignación de regiones ───────────────────
    por_codigo: dict[str, str] = {}
    duplicados: list[str] = []
    for region, codigos in REGIONES.items():
        for c in _expandir(codigos):
            if c in por_codigo:
                duplicados.append(f"{c} ({por_codigo[c]} y {region})")
            por_codigo[c] = region

    todos = {p.alpha_3 for p in pycountry.countries}
    inventados = sorted(set(por_codigo) - todos)
    sin_region = sorted(todos - set(por_codigo))

    if duplicados or inventados:
        print("❌ Error en la tabla de regiones")
        for d in duplicados:
            print(f"   duplicado: {d}")
        for i in inventados:
            print(f"   código inexistente: {i}")
        sys.exit(1)

    if sin_region:
        print(f"⚠️  {len(sin_region)} códigos sin región, van a 'Otros': {', '.join(sin_region)}")

    # ── Construir filas ───────────────────────────────────────
    filas = []
    for p in sorted(pycountry.countries, key=lambda x: x.alpha_3):
        nombre_es = NOMBRES_ES.get(p.alpha_3) or es.gettext(p.name)
        filas.append((
            p.alpha_3,
            p.alpha_2,
            nombre_es,
            p.name,
            por_codigo.get(p.alpha_3, "Otros"),
        ))

    cuerpo = "\n".join(
        f'    ("{a3}", "{a2}", "{es_}", "{en}", "{reg}"),'.replace("\\", "")
        for a3, a2, es_, en, reg in filas
    )

    alias_cuerpo = "\n".join(
        f'    "{k}": "{v}",' for k, v in sorted(ALIAS.items())
    )

    contenido = f'''"""
config/paises.py
Catálogo canónico de países — ISO 3166-1.

GENERADO AUTOMÁTICAMENTE por scripts/generar_catalogo_paises.py
No editar a mano: los cambios se pierden en la siguiente generación.
Para corregir un nombre, edita NOMBRES_ES en el generador y vuelve a ejecutarlo.

Es la pieza que permite cruzar cuatro cosas que hasta ahora no se hablaban:
las listas del GAFI (en inglés), los ficheros de OFAC (en inglés), las
jurisdicciones guardadas en la base de datos (en español con emoji) y la
geometría del mapa (por código ISO-3).
"""

from __future__ import annotations

import unicodedata
from typing import NamedTuple


class Pais(NamedTuple):
    iso3: str
    iso2: str
    nombre: str        # español, uso común
    nombre_en: str     # inglés oficial ISO — para casar con GAFI y OFAC
    region: str


# (iso3, iso2, nombre_es, nombre_en, region)
_DATOS: tuple[tuple[str, str, str, str, str], ...] = (
{cuerpo}
)

PAISES: tuple[Pais, ...] = tuple(Pais(*d) for d in _DATOS)

POR_ISO3: dict[str, Pais] = {{p.iso3: p for p in PAISES}}
POR_ISO2: dict[str, Pais] = {{p.iso2: p for p in PAISES}}

# Denominaciones cortas usadas por GAFI, OFAC y la UE en sus publicaciones.
ALIAS: dict[str, str] = {{
{alias_cuerpo}
}}


def normalizar(texto: str) -> str:
    """
    Minúsculas, sin acentos y sin emojis ni signos.

    El GAFI escribe 'Iran' y la base de datos guarda '🇮🇷 Irán'. Sin
    normalizar, son dos cosas distintas y el país se queda sin clasificar.
    """
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    limpio = "".join(
        c for c in sin_acentos
        if c.isalpha() or c.isspace() or c in ".,'-()"
    )
    return " ".join(limpio.lower().split())


# Índice de búsqueda: nombres en español e inglés, normalizados
POR_NOMBRE: dict[str, Pais] = {{}}
for _p in PAISES:
    POR_NOMBRE[normalizar(_p.nombre)] = _p
    POR_NOMBRE.setdefault(normalizar(_p.nombre_en), _p)

REGIONES: tuple[str, ...] = tuple(dict.fromkeys(p.region for p in PAISES))


def buscar(texto: str) -> Pais | None:
    """
    Resuelve un país desde código ISO, nombre en español o inglés, o alias.

    Tolera los valores heredados con emoji delante y la ausencia de tildes.
    Devuelve None si no hay coincidencia — nunca adivina.
    """
    if not texto:
        return None
    t = texto.strip()

    if len(t) == 3 and t.upper() in POR_ISO3:
        return POR_ISO3[t.upper()]
    if len(t) == 2 and t.upper() in POR_ISO2:
        return POR_ISO2[t.upper()]

    clave = normalizar(t)
    if clave in ALIAS:
        return POR_ISO3[ALIAS[clave]]
    return POR_NOMBRE.get(clave)


def nombre(iso3: str) -> str:
    """Nombre en español, o el propio código si no se reconoce."""
    p = POR_ISO3.get(iso3.upper())
    return p.nombre if p else iso3
'''

    SALIDA.write_text(contenido, encoding="utf-8")
    print(f"✅ {SALIDA.relative_to(RAIZ)} — {len(filas)} países")
    for region in REGIONES:
        n = sum(1 for f in filas if f[4] == region)
        print(f"   {region:<20} {n:>3}")


if __name__ == "__main__":
    main()
