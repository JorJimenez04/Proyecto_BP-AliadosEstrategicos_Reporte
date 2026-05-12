"""
crypto_parser.py — Transaction-Level Parser for Global Ledger PDF Reports

Extrae la tabla de transacciones de riesgo de un PDF de Global Ledger y
la cruza con el catálogo GL_SCORES de crypto_logic.py para pre-llenar
automáticamente los campos SoF / UoF del formulario de monitoreo.

Uso:
    from app.utils.crypto_parser import parse_gl_pdf

    result = parse_gl_pdf(pdf_bytes)
    if result["ok"]:
        sof = result["sof_top"]
        uof = result["uof_top"]
"""

from __future__ import annotations

import re
from typing import Optional

# ── Importación lazy de pdfplumber ────────────────────────────────────────────
# Se importa aquí para no romper el arranque si el paquete no está instalado.
try:
    import pdfplumber  # type: ignore
    _PDFPLUMBER_OK = True
except ImportError:
    _PDFPLUMBER_OK = False

# ── Catálogo GL (importado en tiempo de ejecución para evitar circulares) ─────
def _get_gl_scores() -> dict[str, int]:
    from app.utils.crypto_logic import GL_SCORES  # noqa: PLC0415
    return GL_SCORES


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de limpieza
# ─────────────────────────────────────────────────────────────────────────────

def _clean_pct(raw: str) -> float:
    """
    Convierte una cadena de porcentaje GL a float en escala 0-100.

    Ejemplos:
        "< 0.01%"  → 0.01   (mínimo técnico para no perder la señal)
        "13.66%"   → 13.66
        "0.00%"    → 0.0
        "2,341.5%" → 2341.5  (edge-case tablas corruptas, se acepta)
    """
    if not raw:
        return 0.0
    s = str(raw).strip()
    # Símbolo menor (<) → usar el número que sigue o 0.01 si no hay
    if s.startswith("<"):
        m = re.search(r"[\d.,]+", s)
        if m:
            num = float(m.group().replace(",", ""))
            return num if num > 0 else 0.01
        return 0.01
    # Quitar % y comas de miles
    s = s.replace("%", "").replace(",", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _normalize_col(name: str) -> str:
    """Normaliza un nombre de columna quitando espacios y caracteres especiales."""
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


# ── Mapeo flexible de nombres de columna ─────────────────────────────────────
# Columna canónica → lista de variantes normalizadas aceptadas
_COL_MAP: dict[str, list[str]] = {
    "risk_level":   ["risklevel", "risk", "level", "riesgo", "risklvl"],
    "entity":       ["entity", "category", "entityname", "entitytype",
                     "name", "categoria", "entidad", "indicator", "indicador"],
    "exposure_pct": ["exposure", "exposurepct", "exposure%", "exposurepercentage",
                     "pct", "percent", "porcentaje", "%exposure"],
    "flow_type":    ["type", "direction", "flowtype", "transactiontype",
                     "flow", "sentido", "tipo", "dir"],
    "depth":        ["depth", "distance", "hops", "profundidad", "saltos"],
}

# ── Patrones de detección de metadatos del reporte (anchor-based) ────────────
# Detectan wallet address y GL Score en el texto libre del PDF.
_WALLET_RE = re.compile(
    r'\b('
    r'0x[0-9a-fA-F]{40}'                    # EVM: ETH / BNB / MATIC
    r'|[13][a-km-zA-HJ-NP-Z1-9]{25,34}'    # BTC legacy P2PKH / P2SH
    r'|bc1[a-z0-9]{6,87}'                   # BTC bech32 / bech32m
    r'|T[0-9A-Za-z]{33}'                    # TRX / TRON
    r'|[1-9A-HJ-NP-Za-km-z]{44}'            # Solana (base58, 44 chars)
    r')\b'
)
_GL_SCORE_RE = re.compile(
    r'(?:gl[-\s]?score|risk[-\s]?score|score|puntuaci[o\u00f3]n)[:\s=]+(\d{1,3})\b',
    re.IGNORECASE,
)


def _identify_columns(header: list) -> Optional[dict[str, int]]:
    """
    Intenta mapear columnas de la cabecera a nombres canónicos.

    Retorna {canonical_name: col_index} si se encuentran los campos mínimos
    (entity + exposure_pct), o None si la tabla no es relevante.
    """
    found: dict[str, int] = {}
    for i, cell in enumerate(header):
        norm = _normalize_col(str(cell))
        for canonical, aliases in _COL_MAP.items():
            if canonical not in found and norm in aliases:
                found[canonical] = i
                break

    # Campos mínimos obligatorios
    if "entity" in found and "exposure_pct" in found:
        return found
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Agrupación y scoring
# ─────────────────────────────────────────────────────────────────────────────

def _flow_from_type(raw_type: str) -> str:
    """
    Determina si una fila corresponde a SoF o UoF.

    GL usa:
        "Direct" / "Indirect"  → tipo de contaminación (no flujo)
        "Incoming"             → Source of Funds (SoF)
        "Outgoing"             → Use of Funds (UoF)
        Otros / vacío          → "unknown"
    """
    t = str(raw_type).strip().lower()
    if t in ("incoming", "input", "received", "in"):
        return "sof"
    if t in ("outgoing", "output", "sent", "out"):
        return "uof"
    return "unknown"


def _contamination_type(raw_type: str) -> str:
    """Retorna 'direct' o 'indirect' según el valor de la columna Type."""
    t = str(raw_type).strip().lower()
    if t in ("indirect", "indirecto", "indirecta"):
        return "indirect"
    return "direct"   # default: directo


def _risk_level_from_score(score: int) -> str:
    if score >= 100:
        return "Crítico"
    if score >= 70:
        return "Alto"
    if score >= 50:
        return "Medio"
    return "Bajo"


def _group_rows(rows: list[dict], gl_scores: dict[str, int]) -> list[dict]:
    """
    Agrupa filas por entidad, acumulando % directos e indirectos,
    y cruza con GL_SCORES para obtener el score de riesgo.

    Cada elemento del resultado:
    {
        "entity":       str,
        "gl_score":     int | None,
        "risk_level":   str,
        "direct_pct":   float,   # suma de filas type=Direct o flow=sof
        "indirect_pct": float,   # suma de filas type=Indirect o flow=uof
        "total_pct":    float,
        "depth":        int,     # máximo de profundidad observado
        "flow":         str,     # "sof" | "uof" | "mixed" | "unknown"
    }
    """
    grouped: dict[str, dict] = {}

    for row in rows:
        entity = str(row.get("entity", "")).strip()
        if not entity:
            continue

        pct       = row.get("exposure_pct", 0.0)
        raw_type  = str(row.get("flow_type", "")).strip()
        cont_type = _contamination_type(raw_type)
        flow      = _flow_from_type(raw_type)
        depth     = int(row.get("depth") or 1)

        if entity not in grouped:
            # Buscar score en GL_SCORES (case-insensitive)
            gl_score = None
            entity_lower = entity.lower()
            for lbl, sc in gl_scores.items():
                if lbl.lower() == entity_lower:
                    gl_score = sc
                    break
            # Partial match si no hay exacto
            if gl_score is None:
                for lbl, sc in gl_scores.items():
                    if entity_lower in lbl.lower() or lbl.lower() in entity_lower:
                        gl_score = sc
                        break

            grouped[entity] = {
                "entity":       entity,
                "gl_score":     gl_score,
                "risk_level":   _risk_level_from_score(gl_score) if gl_score else "Sin Datos",
                "direct_pct":   0.0,
                "indirect_pct": 0.0,
                "total_pct":    0.0,
                "depth":        depth,
                "flow":         flow,
            }
        else:
            grouped[entity]["depth"] = max(grouped[entity]["depth"], depth)
            # Actualizar flujo
            prev_flow = grouped[entity]["flow"]
            if prev_flow != flow and flow != "unknown":
                grouped[entity]["flow"] = "mixed" if prev_flow != "unknown" else flow

        if cont_type == "direct" or flow in ("sof", "unknown"):
            grouped[entity]["direct_pct"] += pct
        else:
            grouped[entity]["indirect_pct"] += pct

        grouped[entity]["total_pct"] = (
            grouped[entity]["direct_pct"] + grouped[entity]["indirect_pct"]
        )

    # Re-calcular risk_level desde el row original si estaba disponible
    result = list(grouped.values())
    result.sort(key=lambda x: (x.get("gl_score") or 0) + x["total_pct"], reverse=True)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Entrada principal
# ─────────────────────────────────────────────────────────────────────────────

def parse_gl_pdf(pdf_bytes: bytes) -> dict:
    """
    Extrae y procesa la tabla de transacciones de riesgo de un PDF Global Ledger.

    Returns:
        {
            "ok":               bool,
            "error":            str | None,
            "total_rows":       int,
            "high_risk_count":  int,   # Crítico + Alto
            "medium_risk_count": int,
            "indicators":       list[dict],   # todos los indicadores agrupados
            "sof_top":          dict | None,  # mejor candidato SoF
            "uof_top":          dict | None,  # mejor candidato UoF
            "top_entity":       str | None,   # indicador dominante por total %
            "tables_found":     int,          # nro de tablas inspeccionadas
        }
    """
    _empty = {
        "ok": False,
        "error": None,
        "total_rows": 0,
        "high_risk_count": 0,
        "medium_risk_count": 0,
        "indicators": [],
        "sof_top": None,
        "uof_top": None,
        "top_entity": None,
        "tables_found": 0,
        "wallet_detected": None,
        "gl_score_detected": None,
    }

    if not _PDFPLUMBER_OK:
        return {**_empty, "error": "pdfplumber no instalado. Ejecuta: pip install pdfplumber"}

    if not pdf_bytes:
        return {**_empty, "error": "PDF vacío."}

    gl_scores = _get_gl_scores()
    raw_rows: list[dict] = []
    tables_inspected = 0
    full_text_pages: list[str] = []

    import io  # noqa: PLC0415

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                full_text_pages.append(page.extract_text() or "")
                tables = page.extract_tables()
                if not tables:
                    continue
                for table in tables:
                    if len(table) < 2:
                        continue

                    # Primera fila como cabecera
                    header = [str(c).strip() if c else "" for c in table[0]]
                    col_map = _identify_columns(header)
                    if col_map is None:
                        continue

                    tables_inspected += 1

                    for row in table[1:]:
                        if not row or all(c is None or str(c).strip() == "" for c in row):
                            continue

                        def _cell(col: str) -> str:
                            idx = col_map.get(col)
                            if idx is None or idx >= len(row):
                                return ""
                            return str(row[idx]).strip() if row[idx] is not None else ""

                        entity    = _cell("entity")
                        exposure  = _clean_pct(_cell("exposure_pct"))
                        flow_type = _cell("flow_type")
                        risk_raw  = _cell("risk_level")
                        depth_raw = _cell("depth")

                        if not entity or exposure == 0.0:
                            continue

                        depth = 1
                        if depth_raw:
                            try:
                                depth = int(re.search(r"\d+", depth_raw).group())
                            except (AttributeError, ValueError):
                                depth = 1

                        raw_rows.append({
                            "entity":       entity,
                            "exposure_pct": exposure,
                            "flow_type":    flow_type,
                            "risk_level_raw": risk_raw,
                            "depth":        depth,
                        })

    except Exception as exc:
        return {**_empty, "error": f"Error leyendo PDF: {exc}"}

    # ── Detección de metadatos desde texto libre ──────────────────────────────
    wallet_detected: Optional[str] = None
    gl_score_detected: Optional[int] = None
    if full_text_pages:
        _full_text = "\n".join(full_text_pages)
        _mw = _WALLET_RE.search(_full_text)
        if _mw:
            wallet_detected = _mw.group(1)
        _ms = _GL_SCORE_RE.search(_full_text)
        if _ms:
            try:
                _sc = int(_ms.group(1))
                gl_score_detected = _sc if 0 <= _sc <= 100 else None
            except ValueError:
                pass

    if not raw_rows:
        # Intento fallback: texto plano con regex si las tablas no detectaron nada
        raw_rows = _fallback_text_extraction(pdf_bytes, gl_scores)

    if not raw_rows:
        return {
            **_empty,
            "ok": False,
            "tables_found": tables_inspected,
            "error": (
                "No se detectó una tabla de transacciones GL en el PDF. "
                "Verifica que el reporte incluya la sección 'Transactions'."
            ),
        }

    # Agrupar y cruzar con GL_SCORES
    indicators = _group_rows(raw_rows, gl_scores)

    high_risk   = [i for i in indicators if i["risk_level"] in ("Crítico", "Alto")]
    medium_risk = [i for i in indicators if i["risk_level"] == "Medio"]

    # Top SoF: mayor total % entre indicadores de flujo sof/mixed/unknown, con score alto
    def _score_key(ind: dict) -> float:
        return float(ind.get("gl_score") or 0) * 0.4 + ind["total_pct"] * 0.6

    sof_candidates = [
        i for i in indicators
        if i["flow"] in ("sof", "mixed", "unknown") and i["total_pct"] > 0
    ]
    uof_candidates = [
        i for i in indicators
        if i["flow"] in ("uof", "mixed", "unknown") and i["total_pct"] > 0
    ]

    sof_top = max(sof_candidates, key=_score_key) if sof_candidates else None
    uof_top = (
        max(uof_candidates, key=_score_key)
        if uof_candidates else
        (indicators[1] if len(indicators) > 1 else None)
    )
    # SoF y UoF no deben ser el mismo indicador si hay más opciones
    if sof_top and uof_top and sof_top["entity"] == uof_top["entity"]:
        if len(indicators) > 1:
            uof_top = next(
                (i for i in indicators if i["entity"] != sof_top["entity"]),
                uof_top,
            )

    top_entity = indicators[0]["entity"] if indicators else None

    return {
        "ok":                True,
        "error":             None,
        "total_rows":        len(raw_rows),
        "high_risk_count":   len(high_risk),
        "medium_risk_count": len(medium_risk),
        "indicators":        indicators,
        "sof_top":           sof_top,
        "uof_top":           uof_top,
        "top_entity":        top_entity,
        "tables_found":      tables_inspected,
        "wallet_detected":   wallet_detected,
        "gl_score_detected": gl_score_detected,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Fallback: extracción por texto libre cuando pdfplumber no encuentra tablas
# ─────────────────────────────────────────────────────────────────────────────

def _fallback_text_extraction(pdf_bytes: bytes, gl_scores: dict[str, int]) -> list[dict]:
    """
    Extrae indicadores de riesgo del texto plano cuando las tablas no son
    detectables por pdfplumber (PDFs escaneados o con formato no tabular).

    Busca patrones como:
        "High-risk exchange   13.66%   Direct"
        "Ransomware < 0.01%"
    """
    import io  # noqa: PLC0415

    raw_rows: list[dict] = []
    known_labels = sorted(gl_scores.keys(), key=len, reverse=True)  # longest first

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            full_text = "\n".join(
                page.extract_text() or "" for page in pdf.pages
            )
    except Exception:
        return []

    for label in known_labels:
        # Buscar "LabelName   X.XX%   [Type]"
        pattern = re.compile(
            r"\b" + re.escape(label) + r"\b"
            r".*?"
            r"(<?\s*[\d.,]+\s*%)",
            re.IGNORECASE,
        )
        for m in pattern.finditer(full_text):
            pct_raw = m.group(1)
            pct = _clean_pct(pct_raw)
            if pct > 0:
                raw_rows.append({
                    "entity":         label,
                    "exposure_pct":   pct,
                    "flow_type":      "",
                    "risk_level_raw": "",
                    "depth":          1,
                })
                break  # una fila por indicador en el fallback

    return raw_rows


# ─────────────────────────────────────────────────────────────────────────────
# Generador de nota delta automática (comparación con snapshot previo)
# ─────────────────────────────────────────────────────────────────────────────

def generate_weekly_delta(parsed: dict, prev_snapshot: Optional[dict]) -> str:
    """
    Compara el resultado de parse_gl_pdf() con el snapshot previo del historial
    y genera el texto automático del campo weekly_delta.

    Returns vacío si parsed no es ok. Nunca lanza excepción.
    """
    if not parsed.get("ok"):
        return ""

    import datetime  # noqa: PLC0415
    now_label = datetime.date.today().isoformat()
    lines: list[str] = []

    # ── GL Score ──────────────────────────────────────────────
    new_score  = parsed.get("gl_score_detected")
    prev_score = (
        int(prev_snapshot["gl_score"])
        if prev_snapshot and prev_snapshot.get("gl_score") is not None
        else None
    )
    if new_score is not None and prev_score is not None:
        diff = new_score - prev_score
        if diff == 0:
            lines.append(f"GL Score sin cambio: {new_score}.")
        elif diff > 0:
            lines.append(
                f"GL Score aumentó {diff:+d} pts ({prev_score} → {new_score}): riesgo en escalada."
            )
        else:
            lines.append(
                f"GL Score mejoró {diff:+d} pts ({prev_score} → {new_score}): riesgo a la baja."
            )
    elif new_score is not None:
        lines.append(f"GL Score detectado en PDF: {new_score}.")

    # ── Contaminación total ───────────────────────────────────
    _sof = parsed.get("sof_top")
    _uof = parsed.get("uof_top")
    new_cont = (_sof["total_pct"] if _sof else 0.0) + (_uof["total_pct"] if _uof else 0.0)
    prev_cont = 0.0
    if prev_snapshot:
        prev_cont = (
            float(prev_snapshot.get("sof_cont_total") or 0)
            + float(prev_snapshot.get("uof_cont_total") or 0)
        )
    if prev_cont > 0 and new_cont > 0:
        diff_c = round(new_cont - prev_cont, 4)
        if abs(diff_c) < 0.001:
            lines.append(f"Contaminación total sin variación significativa: {new_cont:.4f}%.")
        elif diff_c > 0:
            lines.append(
                f"Contaminación total aumentó {diff_c:+.4f}% ({prev_cont:.4f}% → {new_cont:.4f}%)."
            )
        else:
            lines.append(
                f"Contaminación total disminuyó {diff_c:+.4f}% ({prev_cont:.4f}% → {new_cont:.4f}%)."
            )
    elif new_cont > 0:
        lines.append(f"Contaminación total detectada: {new_cont:.4f}%.")

    # ── Indicadores críticos ──────────────────────────────────
    high  = parsed.get("high_risk_count", 0)
    top_e = parsed.get("top_entity") or "—"
    if high > 0:
        lines.append(
            f"Se detectaron {high} indicadores Crítico/Alto. Indicador dominante: {top_e}."
        )

    if not lines:
        return "Sin cambios significativos detectados respecto al periodo anterior."

    return f"[Auto-delta {now_label}] " + " | ".join(lines)
