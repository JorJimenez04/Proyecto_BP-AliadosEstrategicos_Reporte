"""
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
    ("ABW", "AW", "Aruba", "Aruba", "Caribe y Offshore"),
    ("AFG", "AF", "Afganistán", "Afghanistan", "Asia"),
    ("AGO", "AO", "Angola", "Angola", "África"),
    ("AIA", "AI", "Anguila", "Anguilla", "Caribe y Offshore"),
    ("ALA", "AX", "Åland", "Åland Islands", "Europa"),
    ("ALB", "AL", "Albania", "Albania", "Europa"),
    ("AND", "AD", "Andorra", "Andorra", "Europa"),
    ("ARE", "AE", "Emiratos Árabes Unidos", "United Arab Emirates", "Asia"),
    ("ARG", "AR", "Argentina", "Argentina", "Latinoamérica"),
    ("ARM", "AM", "Armenia", "Armenia", "Asia"),
    ("ASM", "AS", "Samoa Estadounidense", "American Samoa", "Oceanía"),
    ("ATA", "AQ", "Antártida", "Antarctica", "Otros"),
    ("ATF", "TF", "Tierras Australes Francesas", "French Southern Territories", "África"),
    ("ATG", "AG", "Antigua y Barbuda", "Antigua and Barbuda", "Caribe y Offshore"),
    ("AUS", "AU", "Australia", "Australia", "Oceanía"),
    ("AUT", "AT", "Austria", "Austria", "Europa"),
    ("AZE", "AZ", "Azerbaiyán", "Azerbaijan", "Asia"),
    ("BDI", "BI", "Burundi", "Burundi", "África"),
    ("BEL", "BE", "Bélgica", "Belgium", "Europa"),
    ("BEN", "BJ", "Benín", "Benin", "África"),
    ("BES", "BQ", "Caribe Neerlandés", "Bonaire, Sint Eustatius and Saba", "Caribe y Offshore"),
    ("BFA", "BF", "Burquina Faso", "Burkina Faso", "África"),
    ("BGD", "BD", "Bangladés", "Bangladesh", "Asia"),
    ("BGR", "BG", "Bulgaria", "Bulgaria", "Europa"),
    ("BHR", "BH", "Baréin", "Bahrain", "Asia"),
    ("BHS", "BS", "Bahamas", "Bahamas", "Caribe y Offshore"),
    ("BIH", "BA", "Bosnia y Herzegovina", "Bosnia and Herzegovina", "Europa"),
    ("BLM", "BL", "San Bartolomé", "Saint Barthélemy", "Caribe y Offshore"),
    ("BLR", "BY", "Bielorrusia", "Belarus", "Europa"),
    ("BLZ", "BZ", "Belice", "Belize", "Latinoamérica"),
    ("BMU", "BM", "Islas Bermudas", "Bermuda", "Norteamérica"),
    ("BOL", "BO", "Bolivia", "Bolivia, Plurinational State of", "Latinoamérica"),
    ("BRA", "BR", "Brasil", "Brazil", "Latinoamérica"),
    ("BRB", "BB", "Barbados", "Barbados", "Caribe y Offshore"),
    ("BRN", "BN", "Brunéi", "Brunei Darussalam", "Asia"),
    ("BTN", "BT", "Bután", "Bhutan", "Asia"),
    ("BVT", "BV", "Isla Bouvet", "Bouvet Island", "Otros"),
    ("BWA", "BW", "Botsuana", "Botswana", "África"),
    ("CAF", "CF", "República Centroafricana", "Central African Republic", "África"),
    ("CAN", "CA", "Canadá", "Canada", "Norteamérica"),
    ("CCK", "CC", "Islas Cocos", "Cocos (Keeling) Islands", "Asia"),
    ("CHE", "CH", "Suiza", "Switzerland", "Europa"),
    ("CHL", "CL", "Chile", "Chile", "Latinoamérica"),
    ("CHN", "CN", "China", "China", "Asia"),
    ("CIV", "CI", "Costa de Marfil", "Côte d'Ivoire", "África"),
    ("CMR", "CM", "Camerún", "Cameroon", "África"),
    ("COD", "CD", "República Democrática del Congo", "Congo, The Democratic Republic of the", "África"),
    ("COG", "CG", "República del Congo", "Congo", "África"),
    ("COK", "CK", "Islas Cook", "Cook Islands", "Oceanía"),
    ("COL", "CO", "Colombia", "Colombia", "Latinoamérica"),
    ("COM", "KM", "Comores, Islas", "Comoros", "África"),
    ("CPV", "CV", "Cabo Verde", "Cabo Verde", "África"),
    ("CRI", "CR", "Costa Rica", "Costa Rica", "Latinoamérica"),
    ("CUB", "CU", "Cuba", "Cuba", "Caribe y Offshore"),
    ("CUW", "CW", "Curazao", "Curaçao", "Caribe y Offshore"),
    ("CXR", "CX", "Isla de Navidad", "Christmas Island", "Asia"),
    ("CYM", "KY", "Islas Caimán", "Cayman Islands", "Caribe y Offshore"),
    ("CYP", "CY", "Chipre", "Cyprus", "Europa"),
    ("CZE", "CZ", "Chequia", "Czechia", "Europa"),
    ("DEU", "DE", "Alemania", "Germany", "Europa"),
    ("DJI", "DJ", "Yibuti", "Djibouti", "África"),
    ("DMA", "DM", "Dominica", "Dominica", "Caribe y Offshore"),
    ("DNK", "DK", "Dinamarca", "Denmark", "Europa"),
    ("DOM", "DO", "República Dominicana", "Dominican Republic", "Caribe y Offshore"),
    ("DZA", "DZ", "Algeria", "Algeria", "África"),
    ("ECU", "EC", "Ecuador", "Ecuador", "Latinoamérica"),
    ("EGY", "EG", "Egipto", "Egypt", "África"),
    ("ERI", "ER", "Eritrea", "Eritrea", "África"),
    ("ESH", "EH", "Sahara Occidental", "Western Sahara", "África"),
    ("ESP", "ES", "España", "Spain", "Europa"),
    ("EST", "EE", "Estonia", "Estonia", "Europa"),
    ("ETH", "ET", "Etiopía", "Ethiopia", "África"),
    ("FIN", "FI", "Finlandia", "Finland", "Europa"),
    ("FJI", "FJ", "Fiyi", "Fiji", "Oceanía"),
    ("FLK", "FK", "Islas Malvinas", "Falkland Islands (Malvinas)", "Otros"),
    ("FRA", "FR", "Francia", "France", "Europa"),
    ("FRO", "FO", "Islas Feroe", "Faroe Islands", "Europa"),
    ("FSM", "FM", "Micronesia", "Micronesia, Federated States of", "Oceanía"),
    ("GAB", "GA", "Gabón", "Gabon", "África"),
    ("GBR", "GB", "Reino Unido", "United Kingdom", "Europa"),
    ("GEO", "GE", "Georgia", "Georgia", "Asia"),
    ("GGY", "GG", "Guernsey", "Guernsey", "Europa"),
    ("GHA", "GH", "Ghana", "Ghana", "África"),
    ("GIB", "GI", "Gibraltar", "Gibraltar", "Europa"),
    ("GIN", "GN", "Guinea", "Guinea", "África"),
    ("GLP", "GP", "Guadalupe", "Guadeloupe", "Caribe y Offshore"),
    ("GMB", "GM", "Gambia", "Gambia", "África"),
    ("GNB", "GW", "Guinea-Bisáu", "Guinea-Bissau", "África"),
    ("GNQ", "GQ", "Guinea Ecuatorial", "Equatorial Guinea", "África"),
    ("GRC", "GR", "Grecia", "Greece", "Europa"),
    ("GRD", "GD", "Granada", "Grenada", "Caribe y Offshore"),
    ("GRL", "GL", "Groenlandia", "Greenland", "Norteamérica"),
    ("GTM", "GT", "Guatemala", "Guatemala", "Latinoamérica"),
    ("GUF", "GF", "Guayana Francesa", "French Guiana", "Latinoamérica"),
    ("GUM", "GU", "Guam", "Guam", "Oceanía"),
    ("GUY", "GY", "Guyana", "Guyana", "Latinoamérica"),
    ("HKG", "HK", "Hong Kong", "Hong Kong", "Asia"),
    ("HMD", "HM", "Isla Heard e Islas McDonald", "Heard Island and McDonald Islands", "Otros"),
    ("HND", "HN", "Honduras", "Honduras", "Latinoamérica"),
    ("HRV", "HR", "Croacia", "Croatia", "Europa"),
    ("HTI", "HT", "Haití", "Haiti", "Caribe y Offshore"),
    ("HUN", "HU", "Hungría", "Hungary", "Europa"),
    ("IDN", "ID", "Indonesia", "Indonesia", "Asia"),
    ("IMN", "IM", "Isla de Man", "Isle of Man", "Europa"),
    ("IND", "IN", "India", "India", "Asia"),
    ("IOT", "IO", "Territorio Británico del Océano Índico", "British Indian Ocean Territory", "África"),
    ("IRL", "IE", "Irlanda", "Ireland", "Europa"),
    ("IRN", "IR", "Irán", "Iran, Islamic Republic of", "Asia"),
    ("IRQ", "IQ", "Irak", "Iraq", "Asia"),
    ("ISL", "IS", "Islandia", "Iceland", "Europa"),
    ("ISR", "IL", "Israel", "Israel", "Asia"),
    ("ITA", "IT", "Italia", "Italy", "Europa"),
    ("JAM", "JM", "Jamaica", "Jamaica", "Caribe y Offshore"),
    ("JEY", "JE", "Jersey", "Jersey", "Europa"),
    ("JOR", "JO", "Jordania", "Jordan", "Asia"),
    ("JPN", "JP", "Japón", "Japan", "Asia"),
    ("KAZ", "KZ", "Kazajistán", "Kazakhstan", "Asia"),
    ("KEN", "KE", "Kenia", "Kenya", "África"),
    ("KGZ", "KG", "Kirguistán", "Kyrgyzstan", "Asia"),
    ("KHM", "KH", "Camboya", "Cambodia", "Asia"),
    ("KIR", "KI", "Kiribati", "Kiribati", "Oceanía"),
    ("KNA", "KN", "San Cristóbal y Nieves", "Saint Kitts and Nevis", "Caribe y Offshore"),
    ("KOR", "KR", "Corea del Sur", "Korea, Republic of", "Asia"),
    ("KWT", "KW", "Kuwait", "Kuwait", "Asia"),
    ("LAO", "LA", "Laos", "Lao People's Democratic Republic", "Asia"),
    ("LBN", "LB", "Líbano", "Lebanon", "Asia"),
    ("LBR", "LR", "Liberia", "Liberia", "África"),
    ("LBY", "LY", "Libia", "Libya", "África"),
    ("LCA", "LC", "Santa Lucía", "Saint Lucia", "Caribe y Offshore"),
    ("LIE", "LI", "Liechtenstein", "Liechtenstein", "Europa"),
    ("LKA", "LK", "Sri Lanka", "Sri Lanka", "Asia"),
    ("LSO", "LS", "Lesoto", "Lesotho", "África"),
    ("LTU", "LT", "Lituania", "Lithuania", "Europa"),
    ("LUX", "LU", "Luxemburgo", "Luxembourg", "Europa"),
    ("LVA", "LV", "Letonia", "Latvia", "Europa"),
    ("MAC", "MO", "Macao", "Macao", "Asia"),
    ("MAF", "MF", "San Martín", "Saint Martin (French part)", "Caribe y Offshore"),
    ("MAR", "MA", "Marruecos", "Morocco", "África"),
    ("MCO", "MC", "Mónaco", "Monaco", "Europa"),
    ("MDA", "MD", "Moldavia", "Moldova, Republic of", "Europa"),
    ("MDG", "MG", "Madagascar", "Madagascar", "África"),
    ("MDV", "MV", "Islas Maldivas", "Maldives", "Asia"),
    ("MEX", "MX", "México", "Mexico", "Norteamérica"),
    ("MHL", "MH", "Islas Marshall", "Marshall Islands", "Oceanía"),
    ("MKD", "MK", "Macedonia del Norte", "North Macedonia", "Europa"),
    ("MLI", "ML", "Malí", "Mali", "África"),
    ("MLT", "MT", "Malta", "Malta", "Europa"),
    ("MMR", "MM", "Myanmar", "Myanmar", "Asia"),
    ("MNE", "ME", "Montenegro", "Montenegro", "Europa"),
    ("MNG", "MN", "Mongolia", "Mongolia", "Asia"),
    ("MNP", "MP", "Islas Marianas del Norte", "Northern Mariana Islands", "Oceanía"),
    ("MOZ", "MZ", "Mozambique", "Mozambique", "África"),
    ("MRT", "MR", "Mauritania", "Mauritania", "África"),
    ("MSR", "MS", "Montserrat", "Montserrat", "Caribe y Offshore"),
    ("MTQ", "MQ", "Martinica", "Martinique", "Caribe y Offshore"),
    ("MUS", "MU", "Mauricio", "Mauritius", "África"),
    ("MWI", "MW", "Malaui", "Malawi", "África"),
    ("MYS", "MY", "Malasia", "Malaysia", "Asia"),
    ("MYT", "YT", "Mayotte", "Mayotte", "África"),
    ("NAM", "NA", "Namibia", "Namibia", "África"),
    ("NCL", "NC", "Nueva Caledonia", "New Caledonia", "Oceanía"),
    ("NER", "NE", "Niger", "Niger", "África"),
    ("NFK", "NF", "Isla Norfolk", "Norfolk Island", "Oceanía"),
    ("NGA", "NG", "Nigeria", "Nigeria", "África"),
    ("NIC", "NI", "Nicaragua", "Nicaragua", "Latinoamérica"),
    ("NIU", "NU", "Niue", "Niue", "Oceanía"),
    ("NLD", "NL", "Países Bajos", "Netherlands", "Europa"),
    ("NOR", "NO", "Noruega", "Norway", "Europa"),
    ("NPL", "NP", "Nepal", "Nepal", "Asia"),
    ("NRU", "NR", "Nauru", "Nauru", "Oceanía"),
    ("NZL", "NZ", "Nueva Zelanda", "New Zealand", "Oceanía"),
    ("OMN", "OM", "Omán", "Oman", "Asia"),
    ("PAK", "PK", "Pakistán", "Pakistan", "Asia"),
    ("PAN", "PA", "Panamá", "Panama", "Latinoamérica"),
    ("PCN", "PN", "Pitcairn", "Pitcairn", "Oceanía"),
    ("PER", "PE", "Perú", "Peru", "Latinoamérica"),
    ("PHL", "PH", "Filipinas", "Philippines", "Asia"),
    ("PLW", "PW", "Palaos", "Palau", "Oceanía"),
    ("PNG", "PG", "Papúa Nueva Guinea", "Papua New Guinea", "Oceanía"),
    ("POL", "PL", "Polonia", "Poland", "Europa"),
    ("PRI", "PR", "Puerto Rico", "Puerto Rico", "Caribe y Offshore"),
    ("PRK", "KP", "Corea del Norte", "Korea, Democratic People's Republic of", "Asia"),
    ("PRT", "PT", "Portugal", "Portugal", "Europa"),
    ("PRY", "PY", "Paraguay", "Paraguay", "Latinoamérica"),
    ("PSE", "PS", "Palestina", "Palestine, State of", "Asia"),
    ("PYF", "PF", "Polinesia Francesa", "French Polynesia", "Oceanía"),
    ("QAT", "QA", "Catar", "Qatar", "Asia"),
    ("REU", "RE", "Reunión", "Réunion", "África"),
    ("ROU", "RO", "Rumanía", "Romania", "Europa"),
    ("RUS", "RU", "Rusia", "Russian Federation", "Europa"),
    ("RWA", "RW", "Ruanda", "Rwanda", "África"),
    ("SAU", "SA", "Arabia Saudí", "Saudi Arabia", "Asia"),
    ("SDN", "SD", "Sudán", "Sudan", "África"),
    ("SEN", "SN", "Senegal", "Senegal", "África"),
    ("SGP", "SG", "Singapur", "Singapore", "Asia"),
    ("SGS", "GS", "Georgia del Sur", "South Georgia and the South Sandwich Islands", "Otros"),
    ("SHN", "SH", "Santa Elena", "Saint Helena, Ascension and Tristan da Cunha", "África"),
    ("SJM", "SJ", "Svalbard y Jan Mayen", "Svalbard and Jan Mayen", "Europa"),
    ("SLB", "SB", "Islas Salomón", "Solomon Islands", "Oceanía"),
    ("SLE", "SL", "Sierra Leona", "Sierra Leone", "África"),
    ("SLV", "SV", "El Salvador", "El Salvador", "Latinoamérica"),
    ("SMR", "SM", "San Marino", "San Marino", "Europa"),
    ("SOM", "SO", "Somalia", "Somalia", "África"),
    ("SPM", "PM", "San Pedro y Miquelon", "Saint Pierre and Miquelon", "Norteamérica"),
    ("SRB", "RS", "Serbia", "Serbia", "Europa"),
    ("SSD", "SS", "Sudán del Sur", "South Sudan", "África"),
    ("STP", "ST", "Santo Tomé y Príncipe", "Sao Tome and Principe", "África"),
    ("SUR", "SR", "Surinám", "Suriname", "Latinoamérica"),
    ("SVK", "SK", "Eslovaquia", "Slovakia", "Europa"),
    ("SVN", "SI", "Eslovenia", "Slovenia", "Europa"),
    ("SWE", "SE", "Suecia", "Sweden", "Europa"),
    ("SWZ", "SZ", "Esuatini", "Eswatini", "África"),
    ("SXM", "SX", "Sint Maarten", "Sint Maarten (Dutch part)", "Caribe y Offshore"),
    ("SYC", "SC", "Seychelles", "Seychelles", "África"),
    ("SYR", "SY", "Siria", "Syrian Arab Republic", "Asia"),
    ("TCA", "TC", "Islas Turcas y Caicos", "Turks and Caicos Islands", "Caribe y Offshore"),
    ("TCD", "TD", "Chad", "Chad", "África"),
    ("TGO", "TG", "Togo", "Togo", "África"),
    ("THA", "TH", "Tailandia", "Thailand", "Asia"),
    ("TJK", "TJ", "Tayikistán", "Tajikistan", "Asia"),
    ("TKL", "TK", "Tokelau", "Tokelau", "Oceanía"),
    ("TKM", "TM", "Turkmenistán", "Turkmenistan", "Asia"),
    ("TLS", "TL", "Timor Oriental", "Timor-Leste", "Asia"),
    ("TON", "TO", "Tonga", "Tonga", "Oceanía"),
    ("TTO", "TT", "Trinidad y Tobago", "Trinidad and Tobago", "Caribe y Offshore"),
    ("TUN", "TN", "Tunez", "Tunisia", "África"),
    ("TUR", "TR", "Turquía", "Türkiye", "Asia"),
    ("TUV", "TV", "Tuvalu", "Tuvalu", "Oceanía"),
    ("TWN", "TW", "Taiwán", "Taiwan, Province of China", "Asia"),
    ("TZA", "TZ", "Tanzania", "Tanzania, United Republic of", "África"),
    ("UGA", "UG", "Uganda", "Uganda", "África"),
    ("UKR", "UA", "Ucrania", "Ukraine", "Europa"),
    ("UMI", "UM", "Islas menores de EE. UU.", "United States Minor Outlying Islands", "Oceanía"),
    ("URY", "UY", "Uruguay", "Uruguay", "Latinoamérica"),
    ("USA", "US", "Estados Unidos", "United States", "Norteamérica"),
    ("UZB", "UZ", "Uzbekistán", "Uzbekistan", "Asia"),
    ("VAT", "VA", "Ciudad del Vaticano", "Holy See (Vatican City State)", "Europa"),
    ("VCT", "VC", "San Vicente y las Granadinas", "Saint Vincent and the Grenadines", "Caribe y Offshore"),
    ("VEN", "VE", "Venezuela", "Venezuela, Bolivarian Republic of", "Latinoamérica"),
    ("VGB", "VG", "Islas Vírgenes Británicas", "Virgin Islands, British", "Caribe y Offshore"),
    ("VIR", "VI", "Islas Vírgenes de EE. UU.", "Virgin Islands, U.S.", "Caribe y Offshore"),
    ("VNM", "VN", "Vietnam", "Viet Nam", "Asia"),
    ("VUT", "VU", "Vanuatu", "Vanuatu", "Oceanía"),
    ("WLF", "WF", "Wallis y Futuna", "Wallis and Futuna", "Oceanía"),
    ("WSM", "WS", "Samoa", "Samoa", "Oceanía"),
    ("YEM", "YE", "Yemen", "Yemen", "Asia"),
    ("ZAF", "ZA", "Sudáfrica", "South Africa", "África"),
    ("ZMB", "ZM", "Zambia", "Zambia", "África"),
    ("ZWE", "ZW", "Zimbabue", "Zimbabwe", "África"),
)

PAISES: tuple[Pais, ...] = tuple(Pais(*d) for d in _DATOS)

POR_ISO3: dict[str, Pais] = {p.iso3: p for p in PAISES}
POR_ISO2: dict[str, Pais] = {p.iso2: p for p in PAISES}

# Denominaciones cortas usadas por GAFI, OFAC y la UE en sus publicaciones.
ALIAS: dict[str, str] = {
    "bahamas": "BHS",
    "bolivia": "BOL",
    "bosnia": "BIH",
    "bosnia and herzegovina": "BIH",
    "british virgin islands": "VGB",
    "brunei": "BRN",
    "brunei darussalam": "BRN",
    "burma": "MMR",
    "cabo verde": "CPV",
    "cape verde": "CPV",
    "cayman islands": "CYM",
    "congo": "COG",
    "congo, democratic republic of the": "COD",
    "cote d'ivoire": "CIV",
    "czech republic": "CZE",
    "czechia": "CZE",
    "côte d'ivoire": "CIV",
    "democratic people's republic of korea": "PRK",
    "democratic republic of the congo": "COD",
    "dprk": "PRK",
    "dr congo": "COD",
    "east timor": "TLS",
    "eswatini": "SWZ",
    "gambia": "GMB",
    "great britain": "GBR",
    "holland": "NLD",
    "holy see": "VAT",
    "iran": "IRN",
    "islamic republic of iran": "IRN",
    "ivory coast": "CIV",
    "lao people's democratic republic": "LAO",
    "laos": "LAO",
    "macedonia": "MKD",
    "micronesia": "FSM",
    "moldova": "MDA",
    "netherlands": "NLD",
    "north korea": "PRK",
    "north macedonia": "MKD",
    "palestine": "PSE",
    "philippines": "PHL",
    "republic of korea": "KOR",
    "republic of moldova": "MDA",
    "republic of the congo": "COG",
    "russia": "RUS",
    "russian federation": "RUS",
    "south korea": "KOR",
    "south sudan": "SSD",
    "state of palestine": "PSE",
    "sudan": "SDN",
    "swaziland": "SWZ",
    "syria": "SYR",
    "syrian arab republic": "SYR",
    "taiwan": "TWN",
    "tanzania": "TZA",
    "the bahamas": "BHS",
    "the gambia": "GMB",
    "the philippines": "PHL",
    "timor-leste": "TLS",
    "turkey": "TUR",
    "turkiye": "TUR",
    "türkiye": "TUR",
    "uae": "ARE",
    "uk": "GBR",
    "united arab emirates": "ARE",
    "united kingdom": "GBR",
    "united republic of tanzania": "TZA",
    "united states": "USA",
    "united states of america": "USA",
    "usa": "USA",
    "vatican": "VAT",
    "venezuela": "VEN",
    "viet nam": "VNM",
    "vietnam": "VNM",
    "virgin islands (uk)": "VGB",
}


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
POR_NOMBRE: dict[str, Pais] = {}
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
