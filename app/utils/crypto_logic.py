"""
app/utils/crypto_logic.py
Motor de calificacion de riesgo basado en el catalogo de indicadores
de Global Ledger (GL) — AdamoServices Cripto-Compliance.

Estructura de cada indicador en GL_INDICATORS:
  {
    "label_en":    str,           # Nombre canonico en ingles (GL)
    "label_es":    str,           # Traduccion para la UI en espanol
    "nivel":       str,           # "Critico" | "Alto" | "Medio" | "Bajo"
    "score_base":  int,           # Score de referencia (0-100, escala inversa GL)
    "flujo":       list[str],     # Dimensiones: ["SoF"], ["UoF"], o ["SoF","UoF"]
    "descripcion": str,           # Descripcion breve para el analista
  }

Regla de negocio inflexible (politica AdamoServices):
  El nivel final de la wallet = nivel del indicador MAS ALTO encontrado.
  Jerarquia: Critico > Alto > Medio > Bajo > Sin Datos
  Si cualquier label es Critico → la wallet es Critico, sin excepcion.

SoF (Source of Funds): origen del dinero que ingresa a la wallet.
UoF (Use of Funds):    destino / uso del dinero que sale de la wallet.
"""

from __future__ import annotations

from typing import Optional

# ── Jerarquia de niveles ──────────────────────────────────────
_NIVEL_PESO: dict[str, int] = {
    "Crítico":   4,
    "Alto":      3,
    "Medio":     2,
    "Bajo":      1,
    "Sin Datos": 0,
}

# ── Catalogo maestro de indicadores GL ───────────────────────
GL_INDICATORS: list[dict] = [
    # ── CRITICO ──────────────────────────────────────────────
    {
        "label_en":    "Child Abuse Material",
        "label_es":    "Material de Abuso Infantil",
        "nivel":       "Crítico",
        "score_base":  0,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Fondos vinculados a explotacion infantil — riesgo maxima severidad",
    },
    {
        "label_en":    "Child abuse",
        "label_es":    "Abuso Infantil",
        "nivel":       "Crítico",
        "score_base":  0,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Alias corto de Child Abuse Material en reportes GL",
    },
    {
        "label_en":    "Cybercrime",
        "label_es":    "Cibercrimen",
        "nivel":       "Crítico",
        "score_base":  2,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Actividad criminal digital: hacking, robo de credenciales, fraude online",
    },
    {
        "label_en":    "Darknet Market",
        "label_es":    "Mercado Darknet",
        "nivel":       "Crítico",
        "score_base":  3,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Plataforma anonima para comercio ilegal (drogas, armas, documentos falsos)",
    },
    {
        "label_en":    "Darknet marketplace",
        "label_es":    "Mercado Darknet",
        "nivel":       "Crítico",
        "score_base":  3,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Alias alternativo de Darknet Market en reportes GL",
    },
    {
        "label_en":    "Terrorism Financing",
        "label_es":    "Financiacion del Terrorismo",
        "nivel":       "Crítico",
        "score_base":  1,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Flujos asociados a entidades terroristas designadas (GAFI R.5/R.6)",
    },
    {
        "label_en":    "Sanctioned Entity",
        "label_es":    "Entidad Sancionada",
        "nivel":       "Crítico",
        "score_base":  2,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Entidad en listas OFAC, ONU, UE o Supersociedades Colombia",
    },
    {
        "label_en":    "Sanctioned Exchange",
        "label_es":    "Exchange Sancionado",
        "nivel":       "Crítico",
        "score_base":  2,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Exchange de criptomonedas bajo sancion internacional activa",
    },
    {
        "label_en":    "OFAC Sanctioned",
        "label_es":    "Sancionado OFAC",
        "nivel":       "Crítico",
        "score_base":  1,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Entidad o wallet en lista SDN de la OFAC (US Treasury)",
    },
    {
        "label_en":    "Ransomware",
        "label_es":    "Ransomware / Extorsion Digital",
        "nivel":       "Crítico",
        "score_base":  3,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Fondos relacionados con ataques de secuestro digital y extorsion",
    },
    {
        "label_en":    "Scam",
        "label_es":    "Estafa / Fraude",
        "nivel":       "Crítico",
        "score_base":  4,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Esquemas de fraude: phishing, Ponzi, rug pull, romance scam",
    },
    {
        "label_en":    "Exploit",
        "label_es":    "Exploit / Hackeo de Protocolo",
        "nivel":       "Crítico",
        "score_base":  3,
        "flujo":       ["SoF"],
        "descripcion": "Fondos provenientes de vulneracion de contratos inteligentes o protocolos DeFi",
    },
    {
        "label_en":    "Blacklisted Wallet",
        "label_es":    "Wallet en Lista Negra",
        "nivel":       "Crítico",
        "score_base":  5,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Direccion incluida en listas negras de proveedores de compliance",
    },
    {
        "label_en":    "Blacklisted",
        "label_es":    "En Lista Negra",
        "nivel":       "Crítico",
        "score_base":  5,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Alias corto de Blacklisted Wallet",
    },
    # ── ALTO ─────────────────────────────────────────────────
    {
        "label_en":    "High-Risk Exchange",
        "label_es":    "Exchange de Alto Riesgo",
        "nivel":       "Alto",
        "score_base":  25,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Exchange con controles KYC/AML debiles o presencia en jurisdicciones de riesgo",
    },
    {
        "label_en":    "Exchange (non-KYC)",
        "label_es":    "Exchange sin KYC",
        "nivel":       "Alto",
        "score_base":  28,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Plataforma de intercambio que no requiere verificacion de identidad",
    },
    {
        "label_en":    "P2P Exchange",
        "label_es":    "Exchange P2P",
        "nivel":       "Alto",
        "score_base":  30,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Transacciones peer-to-peer sin intermediario regulado — riesgo de lavado",
    },
    {
        "label_en":    "Stolen Funds",
        "label_es":    "Fondos Robados",
        "nivel":       "Alto",
        "score_base":  10,
        "flujo":       ["SoF"],
        "descripcion": "Activos provenientes de robo confirmado en exchange o protocolo",
    },
    {
        "label_en":    "Gambling",
        "label_es":    "Juego de Azar / Casino Cripto",
        "nivel":       "Alto",
        "score_base":  35,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Plataformas de apuestas cripto — uso comun para lavado de capitales",
    },
    # ── MEDIO ────────────────────────────────────────────────
    {
        "label_en":    "Mixer",
        "label_es":    "Mezclador / Tumbler",
        "nivel":       "Medio",
        "score_base":  42,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Servicio de mezcla de criptomonedas para dificultar la trazabilidad",
    },
    {
        "label_en":    "ATM",
        "label_es":    "Cajero Automatico Cripto (ATM)",
        "nivel":       "Medio",
        "score_base":  50,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Cajero fisico de criptomonedas — uso frecuente en smurfing",
    },
    {
        "label_en":    "Adult Entertainment",
        "label_es":    "Entretenimiento para Adultos",
        "nivel":       "Medio",
        "score_base":  55,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Plataformas de contenido adulto — riesgo de trata de personas",
    },
    {
        "label_en":    "Adult entertainment",
        "label_es":    "Entretenimiento para Adultos",
        "nivel":       "Medio",
        "score_base":  55,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Alias en minusculas de Adult Entertainment",
    },
    {
        "label_en":    "DeFi Protocol",
        "label_es":    "Protocolo DeFi",
        "nivel":       "Medio",
        "score_base":  58,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Protocolo financiero descentralizado — sin KYC, anonimidad variable",
    },
    {
        "label_en":    "NFT Platform",
        "label_es":    "Plataforma NFT",
        "nivel":       "Medio",
        "score_base":  60,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Plataforma NFT — uso para wash-trading y lavado de activos digitales",
    },
    # ── BAJO ─────────────────────────────────────────────────
    {
        "label_en":    "Mining",
        "label_es":    "Mineria de Criptomonedas",
        "nivel":       "Bajo",
        "score_base":  80,
        "flujo":       ["SoF"],
        "descripcion": "Recompensas de mineria — origen conocido y trazable",
    },
    {
        "label_en":    "Wallet Service",
        "label_es":    "Servicio de Billetera",
        "nivel":       "Bajo",
        "score_base":  75,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Proveedor de billetera custodial o no-custodial con buenas practicas",
    },
    {
        "label_en":    "Charity",
        "label_es":    "Organizacion Benefica",
        "nivel":       "Bajo",
        "score_base":  82,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "ONG o fundacion con fines benevoles — verificar transparencia",
    },
    {
        "label_en":    "Staking",
        "label_es":    "Staking / Validacion de Red",
        "nivel":       "Bajo",
        "score_base":  85,
        "flujo":       ["SoF"],
        "descripcion": "Fondos bloqueados en staking — origen en participacion de red",
    },
    {
        "label_en":    "Mainstream Exchange",
        "label_es":    "Exchange Principal Regulado",
        "nivel":       "Bajo",
        "score_base":  78,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Exchange con KYC robusto, regulado en multiples jurisdicciones",
    },
    {
        "label_en":    "Exchange",
        "label_es":    "Exchange de Criptomonedas",
        "nivel":       "Bajo",
        "score_base":  72,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Exchange generico — evaluar reputacion y jurisdiccion por separado",
    },
    {
        "label_en":    "DEX",
        "label_es":    "Exchange Descentralizado (DEX)",
        "nivel":       "Bajo",
        "score_base":  70,
        "flujo":       ["SoF", "UoF"],
        "descripcion": "Exchange on-chain sin custodia — anonimidad moderada",
    },
]

# ── Indice de busqueda rapida (label_en normalizado → dict) ──
_INDEX_BY_LABEL: dict[str, dict] = {}
for _ind in GL_INDICATORS:
    _key = _ind["label_en"].lower().strip()
    _INDEX_BY_LABEL[_key] = _ind


def lookup_label(label: str) -> Optional[dict]:
    """Busca un indicador por su nombre (case-insensitive, busqueda parcial)."""
    label_norm = label.lower().strip()
    # Coincidencia exacta
    if label_norm in _INDEX_BY_LABEL:
        return _INDEX_BY_LABEL[label_norm]
    # Busqueda parcial (GL a veces anade sufijos)
    for key, ind in _INDEX_BY_LABEL.items():
        if key in label_norm or label_norm in key:
            return ind
    return None


def calificar_labels(
    labels: list[dict],
) -> dict:
    """
    Evalua una lista de risk_labels y retorna la calificacion consolidada.

    Cada label debe tener al menos {"label": str}.
    Campos opcionales: "exposure_pct", "source", "flujo" (SoF/UoF).

    Retorna:
      {
        "nivel_final":    str,          # Critico / Alto / Medio / Bajo / Sin Datos
        "nivel_peso":     int,          # 0-4
        "score_sugerido": int,          # score GL aproximado (promedio ponderado)
        "indicadores":    list[dict],   # labels enriquecidos con catalogo
        "sof_max_nivel":  str,          # nivel mas alto por SoF
        "uof_max_nivel":  str,          # nivel mas alto por UoF
        "criticos_encontrados": int,    # conteo de labels de nivel Critico
        "altos_encontrados":    int,
        "medios_encontrados":   int,
        "bajos_encontrados":    int,
        "sin_catalogo":   list[str],    # labels que no se encontraron en catalogo
      }
    """
    if not labels:
        return {
            "nivel_final":          "Sin Datos",
            "nivel_peso":           0,
            "score_sugerido":       None,
            "indicadores":          [],
            "sof_max_nivel":        "Sin Datos",
            "uof_max_nivel":        "Sin Datos",
            "criticos_encontrados": 0,
            "altos_encontrados":    0,
            "medios_encontrados":   0,
            "bajos_encontrados":    0,
            "sin_catalogo":         [],
        }

    max_peso   = 0
    nivel_final = "Sin Datos"
    sof_peso   = 0
    uof_peso   = 0
    scores_found: list[int] = []
    indicadores_enriquecidos: list[dict] = []
    sin_catalogo: list[str] = []
    conteos = {"Crítico": 0, "Alto": 0, "Medio": 0, "Bajo": 0}

    for lbl in labels:
        label_text = lbl.get("label", "")
        if not label_text:
            continue

        ind = lookup_label(label_text)
        if ind:
            peso = _NIVEL_PESO[ind["nivel"]]
            enriquecido = {
                **lbl,
                "label_es":    ind["label_es"],
                "nivel":       ind["nivel"],
                "nivel_peso":  peso,
                "flujo":       ind["flujo"],
                "score_base":  ind["score_base"],
                "descripcion": ind["descripcion"],
            }
            indicadores_enriquecidos.append(enriquecido)
            scores_found.append(ind["score_base"])
            conteos[ind["nivel"]] = conteos.get(ind["nivel"], 0) + 1

            if peso > max_peso:
                max_peso    = peso
                nivel_final = ind["nivel"]

            # SoF / UoF independientes
            if "SoF" in ind["flujo"] and peso > sof_peso:
                sof_peso = peso
            if "UoF" in ind["flujo"] and peso > uof_peso:
                uof_peso = peso
        else:
            sin_catalogo.append(label_text)
            indicadores_enriquecidos.append({**lbl, "label_es": label_text, "nivel": None, "flujo": []})

    # Score sugerido: promedio de score_base de todos los indicadores encontrados
    score_sugerido: Optional[int] = int(sum(scores_found) / len(scores_found)) if scores_found else None

    # Invertir peso → nivel string para SoF/UoF
    _peso_a_nivel = {v: k for k, v in _NIVEL_PESO.items()}

    return {
        "nivel_final":          nivel_final,
        "nivel_peso":           max_peso,
        "score_sugerido":       score_sugerido,
        "indicadores":          indicadores_enriquecidos,
        "sof_max_nivel":        _peso_a_nivel.get(sof_peso, "Sin Datos"),
        "uof_max_nivel":        _peso_a_nivel.get(uof_peso, "Sin Datos"),
        "criticos_encontrados": conteos.get("Crítico", 0),
        "altos_encontrados":    conteos.get("Alto", 0),
        "medios_encontrados":   conteos.get("Medio", 0),
        "bajos_encontrados":    conteos.get("Bajo", 0),
        "sin_catalogo":         sin_catalogo,
    }


def nivel_dominante(nivel_a: str, nivel_b: str) -> str:
    """Retorna el nivel de mayor severidad entre dos."""
    peso_a = _NIVEL_PESO.get(nivel_a, 0)
    peso_b = _NIVEL_PESO.get(nivel_b, 0)
    return nivel_a if peso_a >= peso_b else nivel_b


# ── Catálogo completo GL (228 indicadores) ────────────────────
# Fuente: hoja "Risk Indicators GL" del Excel de monitoreo AdamoServices
# Formato: {label_en: score_gl}  (escala GL directa, diferente a score_base interno)
GL_SCORES: dict[str, int] = {
    # ── Score 100 ─────────────────────────────────────────
    "Child abuse": 100,
    "Cybercrime / Hack": 100,
    "Darknet community": 100,
    "Darknet marketplace": 100,
    "Darknet service": 100,
    "Drug smuggler": 100,
    "Drug store": 100,
    "Drug vendor": 100,
    "Exploit": 100,
    "Fake docs seller": 100,
    "Fake money seller": 100,
    "Hacker": 100,
    "Hackers group": 100,
    "Hacking services": 100,
    "Hitman hiring": 100,
    "Human trafficking": 100,
    "Illegal service": 100,
    "Palestian military correspondent": 100,
    "Personal data seller": 100,
    "Precursors distributor / manufacturer": 100,
    "Pro-Russian Telegram channel": 100,
    "Russian arms supplier": 100,
    "Russian Intelligence": 100,
    "Russian invasion funding": 100,
    "Russian military blogger": 100,
    "Russian military correspondent": 100,
    "Russian military news agency": 100,
    "Russian military-focused Telegram channel": 100,
    "Russian paramilitary group": 100,
    "Russian political actor": 100,
    "Russian political party": 100,
    "Sanctioned entity": 100,
    "Sanctioned exchange": 100,
    "Sanctioned individual": 100,
    "Stolen wallets seller": 100,
    "Terrorist financing": 100,
    "Terrorists organization": 100,
    "Torture streaming service": 100,
    "Weapon shop": 100,
    "Bitfinex hacked coins": 100,
    "Child porn buyer": 100,
    "EU Sanctions": 100,
    "FinCEN Sanctions": 100,
    "Flagged by SEC": 100,
    "Iran": 100,
    "MOFA Sanctions": 100,
    "NBCTF Sanctions": 100,
    "NSDO of Ukraine Sanctions": 100,
    "OFAC Sanctions": 100,
    "OFSI Sanctions": 100,
    "Ronin hacked coins": 100,
    "Russian invasion related": 100,
    "Sanctions evasion": 100,
    # ── Score 90 ──────────────────────────────────────────
    "Address poisoning": 90,
    "Cloud mining scam": 90,
    "Credit card dumps market": 90,
    "Darknet explorer": 90,
    "Exit scam": 90,
    "Fraud": 90,
    "Illegal services seller": 90,
    "Malware developer": 90,
    "Malware seller": 90,
    "Phishing": 90,
    "Ponzi scheme": 90,
    "Reported darknet": 90,
    "Reported hack": 90,
    "Reported phishing": 90,
    "Rug pull": 90,
    "Spam token": 90,
    "Stolen electronics seller": 90,
    # ── Score 80 ──────────────────────────────────────────
    "Hacked exchange": 80,
    "Hacked wallet": 80,
    "Investment scam": 80,
    "Pro-Russian political blogger": 80,
    "Ransomware": 80,
    "Reported blackmail": 80,
    "Reported extortion": 80,
    "Reported ransomware": 80,
    "Russian propagandist": 80,
    "Scam": 80,
    "Scam token": 80,
    "Scam token deployer": 80,
    "SIM cards seller": 80,
    # ── Score 75 ──────────────────────────────────────────
    "Anonymizer": 75,
    "Reported scam": 75,
    # ── Score 70 ──────────────────────────────────────────
    "High-risk donations": 70,
    "High-risk exchange": 70,
    "High-risk forum": 70,
    "High-risk payment service": 70,
    "High-risk service": 70,
    "mixing": 70,
    "Mixing service": 70,
    "Privacy transactions": 70,
    "Suspended yield farming platform": 70,
    # ── Score 65 ──────────────────────────────────────────
    "Extremism": 65,
    # ── Score 60 ──────────────────────────────────────────
    "Adult entertainment": 60,
    "ATM": 60,
    "Cloud mining": 60,
    "Cross-chain protocol": 60,
    "Gambling": 60,
    "Honeypot": 60,
    "Online wallet": 60,
    "Online wallet / Payment service": 60,
    "P2P exchange": 60,
    "Prediction platform": 60,
    "Proxy seller": 60,
    "Seized coins": 60,
    "Suspended ATM service": 60,
    "Suspended DeFi": 60,
    "Suspended DEX": 60,
    "Suspended exchange": 60,
    "Suspended faucet": 60,
    "Suspended gambling platform": 60,
    "Suspended gaming platform": 60,
    "Suspended investments / venture fund": 60,
    "Suspended marketplace": 60,
    "Suspended NFT project": 60,
    "Suspended online wallet": 60,
    "Suspended payment service": 60,
    "Suspended service": 60,
    # ── Score 55 ──────────────────────────────────────────
    "VPN": 55,
    # ── Score 50 ──────────────────────────────────────────
    "Agriculture": 50,
    "Airdrop / Distributor": 50,
    "Algorithmic stablecoin": 50,
    "Blogger": 50,
    "Cashback platform": 50,
    "Crowdfunding platform": 50,
    "DAO": 50,
    "dApps": 50,
    "DeFi": 50,
    "DeFi / Community platfrom": 50,
    "DeFi / DAO": 50,
    "DeFi / DEX": 50,
    "DeFi / Investments": 50,
    "DeFi / Lending": 50,
    "DeFi / NFT marketplace": 50,
    "DeFi / NFT project": 50,
    "DeFi / Social platform": 50,
    "DeFi / Staking": 50,
    "Delivery service": 50,
    "DEX": 50,
    "E-commerce": 50,
    "Exchange": 50,
    "fintech": 50,
    "Incubator / Launchpad": 50,
    "Insurance": 50,
    "Investments / Venture fund": 50,
    "Liquidity provider": 50,
    "maximum depth reached": 50,
    "Meme coin": 50,
    "MEV bot": 50,
    "MEV builder": 50,
    "Oracle": 50,
    "Paramilitary group": 50,
    "Payment service": 50,
    "small transactions": 50,
    "Smart contract management": 50,
    "Staking": 50,
    "Tokenized assets": 50,
    "Trading bot": 50,
    "Trading platform": 50,
    "Ukrainian political actor": 50,
    "unidentified service / exchange": 50,
    "unknown single wallet service": 50,
    "Yield farming": 50,
    "ZK-Rollup": 50,
    # ── Score 40 ──────────────────────────────────────────
    "Advertising": 40,
    "AI-based solutions": 40,
    "AR-related project": 40,
    "Auction": 40,
    "Bitcoin-OTC user": 40,
    "Blockchain solutions": 40,
    "Cloud services": 40,
    "Data analytics": 40,
    "Data exchange": 40,
    "Data storage": 40,
    "Data verification": 40,
    "DNS": 40,
    "Entertainment platform": 40,
    "Faucet": 40,
    "Gaming": 40,
    "HYIP hunter": 40,
    "Journalist": 40,
    "Lending": 40,
    "NFT artist": 40,
    "NFT marketplace": 40,
    "NFT project": 40,
    "Real estate": 40,
    "Rental platform": 40,
    "Software development": 40,
    "Sports": 40,
    "Technologies": 40,
    "Telecommunications": 40,
    "Ticketing / Events": 40,
    "Yacht-related services": 40,
    # ── Score 30 ──────────────────────────────────────────
    "Animal control": 30,
    "Anti-slavery organisation": 30,
    "Beauty industry": 30,
    "Charity": 30,
    "Community": 30,
    "Custodian": 30,
    "Cybersecurity": 30,
    "Donations": 30,
    "Educational platform": 30,
    "Energy sector / Ecology": 30,
    "Food industry": 30,
    "Hardware": 30,
    "Healthcare": 30,
    "Job search / Recruiting": 30,
    "Jurisprudence": 30,
    "Low-risk exchange": 30,
    "Music-related project": 30,
    "Non-profit organization": 30,
    "Political institution": 30,
    "Science-related project": 30,
    "Search engine": 30,
    "Service": 30,
    "Shipping / Logistics": 30,
    "Streaming platform": 30,
    "Travel-related platform": 30,
    "User wallet": 30,
    "Vehicle-related service": 30,
    "Voting platform": 30,
    "White-hat hackers": 30,
    # ── Score 20 ──────────────────────────────────────────
    "Marketplace": 20,
    # ── Score 10 ──────────────────────────────────────────
    "BitcoinTalk user": 10,
    "Blockchain": 10,
    "Blockchain analytics": 10,
    "Blockchain explorer": 10,
    "Blog": 10,
    "Burn address": 10,
    "DeFi analytics": 10,
    "Forum": 10,
    "mining": 10,
    "Mining pool": 10,
    "Mining service": 10,
    "Minting / Mining / Staking": 10,
    "News platform": 10,
    "Ransomware developer": 10,
    "Stablecoin": 10,
    "Validator": 10,
    "Wrapped token": 10,
    "Writer": 10,
    # ── Adicionales legacy (en GL_INDICATORS) ─────────────
    "Blocked Funds": 70,
    "Stolen Funds": 80,
    "Unknown smart contract": 50,
}

# Lista ordenada para selectbox (score desc → etiquetas críticas primero)
GL_ALL_LABELS_SORTED: list[tuple[str, int]] = sorted(
    GL_SCORES.items(), key=lambda x: -x[1]
)


def score_gl_to_nivel(score: int) -> str:
    """Convierte un GL score (escala Excel) a nivel AdamoServices."""
    if score >= 100:
        return "Crítico"
    if score >= 70:
        return "Alto"
    if score >= 50:
        return "Medio"
    return "Bajo"


