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
