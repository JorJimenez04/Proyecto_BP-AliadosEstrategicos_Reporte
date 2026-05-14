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
    r'(?:gl[-\s]?score|wallet[-\s]?risk[-\s]?score|risk[-\s]?score'
    r'|score|puntuaci[o\u00f3]n)'
    r'[:\s=\n\r]+(\d{1,3})(?:\s*/\s*100)?\b',
    re.IGNORECASE | re.MULTILINE,
)
# Fallback: detecta "47/100" sin prefijo de etiqueta
_GL_SCORE_FRACTION_RE = re.compile(r'\b(\d{1,3})\s*/\s*100\b')
# Score como línea aislada: número solo entre \n y \n
# El PDF de GL coloca el score entre los labels de SoF y UoF
_GL_SCORE_ISOLATED_RE = re.compile(
    r'(?:^|\n)[ \t]*(\d{1,3})[ \t]*\n',
    re.MULTILINE,
)
# Detecta nivel de riesgo global en texto: "HIGH RISK", "MEDIUM RISK", etc.
_GL_RISK_LEVEL_RE = re.compile(
    r'\b(critical|high|medium|low|bajo|medio|alto|cr[i\u00ed]tico)\s*risk\b'
    r'|\brisk\s*level[:\s]*(critical|high|medium|low|bajo|medio|alto|cr[i\u00ed]tico)\b',
    re.IGNORECASE,
)
# Detecta fechas en texto libre del PDF (múltiples formatos)
_REPORT_DATE_RE = re.compile(
    r'(?:report\s+date|generated(?:\s+on)?|date|fecha)[:\s]+'
    r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
    r'|\d{4}-\d{2}-\d{2}'
    r'|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?'
    r'|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    r'\s+\d{1,2}(?:,\s*|\s+)\d{4}'
    r'|\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?'
    r'|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    r'(?:\s+\d{4})?)',
    re.IGNORECASE,
)
# Detecta fecha de última transacción en el PDF
_LAST_TX_DATE_RE = re.compile(
    r'(?:last\s+(?:activity|transaction|tx)\s*(?:date)?'
    r'|most\s+recent\s+(?:activity|transaction)'
    r'|\u00faltima\s+transacci\u00f3n'
    r'|last\s+seen)'
    r'[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
    r'|\d{4}-\d{2}-\d{2}'
    r'|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?'
    r'|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    r'\s+\d{1,2}(?:,\s*|\s+)\d{4}'
    r'|\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?'
    r'|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    r'(?:\s+\d{4})?)',
    re.IGNORECASE,
)
# Detecta montos totales SoF/UoF en el formato:
#   "Source of Funds Evaluated Transactions\n2,340,897.66 USD 48"
_SOF_TOTAL_AMOUNT_RE = re.compile(
    r'Source\s+of\s+Funds\s+Evaluated\s+Transactions\s*\n\s*([\d,]+\.?\d*)\s+USD',
    re.IGNORECASE,
)
_UOF_TOTAL_AMOUNT_RE = re.compile(
    r'Use\s+of\s+Funds\s+Evaluated\s+Transactions\s*\n\s*([\d,]+\.?\d*)\s+USD',
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
# Helper: normalizar fecha detectada a ISO string "YYYY-MM-DD"
# ─────────────────────────────────────────────────────────────────────────────

def _parse_report_date(raw: str) -> Optional[str]:
    """
    Convierte una cadena de fecha libre a ISO 'YYYY-MM-DD'.
    Acepta: '11/05/2026', '2026-05-11', '11-05-2026', 'May 11, 2026',
            '11 May 2026', 'May 11 2026', etc.
    Retorna None si no puede parsear.
    """
    from datetime import datetime as _dt  # noqa: PLC0415
    raw = raw.strip()
    _MONTH_MAP = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10,
        "november": 11, "december": 12,
    }
    # Intentar formatos estrictos
    # Quitar posible sufijo de hora ("11.05.2026 08:39" → "11.05.2026")
    raw = re.sub(r'\s+\d{1,2}:\d{2}(?::\d{2})?\s*$', '', raw).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
                "%d.%m.%Y", "%m.%d.%Y",
                "%B %d, %Y", "%B %d %Y", "%d %B %Y", "%d %B %Y"):
        try:
            return _dt.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    # Fallback: buscar dígitos y nombre de mes con regex
    _m = re.search(
        r'(\d{1,2})\s+([A-Za-z]+)(?:\s+(\d{4}))?'
        r'|([A-Za-z]+)\s+(\d{1,2})(?:,\s*|\s+)(\d{4})',
        raw,
    )
    if _m:
        try:
            if _m.group(1):  # "11 May 2026"
                day, mon_str, year = _m.group(1), _m.group(2), _m.group(3) or "2026"
            else:             # "May 11, 2026"
                mon_str, day, year = _m.group(4), _m.group(5), _m.group(6)
            month = _MONTH_MAP.get(mon_str.lower()[:3])
            if month:
                from datetime import date as _date  # noqa: PLC0415
                return _date(int(year), month, int(day)).isoformat()
        except (ValueError, TypeError):
            pass
    return None


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
        "risk_exposure_list": [],
        "residual_count": 0,
        "sof_total_pct": 0.0,
        "uof_total_pct": 0.0,
        "sof_total_amount": 0.0,
        "uof_total_amount": 0.0,
        "sof_top": None,
        "uof_top": None,
        "top_entity": None,
        "tables_found": 0,
        "wallet_detected": None,
        "gl_score_detected": None,
        "report_date": None,            # ISO str "YYYY-MM-DD" si se detecta
        "last_transaction_date": None,  # ISO str "YYYY-MM-DD" de última tx
        "gl_level": None,               # str: Bajo/Medio/Alto/Crítico/Sin Datos
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

                        # ── Limpiar entidad: separar nivel pegado al nombre ──
                        # Global Ledger a veces emite "High-risk exchangeHIGH"
                        entity_clean = re.sub(
                            r'\s*(HIGH|MEDIUM|LOW|CRITICAL|SEVERE)\s*$', '',
                            entity, flags=re.IGNORECASE
                        ).strip()
                        if not risk_raw:
                            # Intentar extraer nivel del final de la cadena entity
                            _m_lvl = re.search(
                                r'(HIGH|MEDIUM|LOW|CRITICAL|SEVERE)\s*$',
                                entity, re.IGNORECASE,
                            )
                            if _m_lvl:
                                risk_raw = _m_lvl.group(1).upper()

                        raw_rows.append({
                            "entity":         entity_clean,
                            "exposure_pct":   exposure,
                            "flow_type":      flow_type,
                            "risk_level_raw": risk_raw,
                            "depth":          depth,
                        })

    except Exception as exc:
        return {**_empty, "error": f"Error leyendo PDF: {exc}"}

    # ── Detección de metadatos desde texto libre ──────────────────────────────
    wallet_detected: Optional[str] = None
    gl_score_detected: Optional[int] = None
    _sof_amt_override: Optional[float] = None
    _uof_amt_override: Optional[float] = None
    gl_risk_level_text: Optional[str] = None  # detectado desde texto libre
    report_date_detected: Optional[str] = None
    last_tx_date_detected: Optional[str] = None
    _gl_anchor: int = -1  # posición de "GL-Score" en el texto; -1 si no hallado
    if full_text_pages:
        _full_text = "\n".join(full_text_pages)
        _mw = _WALLET_RE.search(_full_text)
        if _mw:
            wallet_detected = _mw.group(1)
        # Score con etiqueta (ej. "Score: 47" o "Score\n47")
        _ms = _GL_SCORE_RE.search(_full_text)
        if _ms:
            try:
                _sc = int(_ms.group(1))
                gl_score_detected = _sc if 0 <= _sc <= 100 else None
            except ValueError:
                pass
        # Fallback: "47/100" sin etiqueta
        if gl_score_detected is None:
            _mf = _GL_SCORE_FRACTION_RE.search(_full_text)
            if _mf:
                try:
                    _sc2 = int(_mf.group(1))
                    gl_score_detected = _sc2 if 0 <= _sc2 <= 100 else None
                except ValueError:
                    pass
        # Fallback: score como línea aislada — buscar cerca de "GL-Score" primero
        _gl_anchor = _full_text.find("GL-Score")
        if _gl_anchor == -1:
            _gl_anchor = _full_text.lower().find("gl score")
        if gl_score_detected is None:
            if _gl_anchor != -1:
                # Buscar número aislado en los 400 chars siguientes al marcador
                _window = _full_text[_gl_anchor:_gl_anchor + 400]
                for _m in _GL_SCORE_ISOLATED_RE.finditer(_window):
                    _candidate = int(_m.group(1))
                    if 1 <= _candidate <= 100:
                        gl_score_detected = _candidate
                        break
        if gl_score_detected is None:
            # Fallback global: número aislado en primera página
            _page1_text = _full_text[:2000]
            for _m in _GL_SCORE_ISOLATED_RE.finditer(_page1_text):
                _candidate = int(_m.group(1))
                if 1 <= _candidate <= 100:
                    _ctx = _page1_text[max(0, _m.start()-200):_m.end()+200]
                    if re.search(
                        r'GL.?Score|Blacklisted|High.Risk|Sanctioned|MEDIUM|HIGH',
                        _ctx, re.IGNORECASE,
                    ):
                        gl_score_detected = _candidate
                        break
        # Nivel de riesgo desde texto ("HIGH RISK", "Risk Level: High")
        _ml = _GL_RISK_LEVEL_RE.search(_full_text)
        if _ml:
            _raw_lvl = (_ml.group(1) or _ml.group(2) or "").lower()
            _lvl_map = {
                "critical": "Cr\u00edtico", "cr\u00edtico": "Cr\u00edtico",
                "high": "Alto", "alto": "Alto",
                "medium": "Medio", "medio": "Medio",
                "low": "Bajo", "bajo": "Bajo",
            }
            gl_risk_level_text = _lvl_map.get(_raw_lvl[:8])
        # Fecha del reporte
        _md = _REPORT_DATE_RE.search(_full_text)
        if _md:
            report_date_detected = _parse_report_date(_md.group(1))
        # Fallback fecha reporte: formato DD.MM.YYYY HH:MM (timestamp del reporte)
        if report_date_detected is None:
            _DOT_DT_RE = re.compile(r'\b(\d{2}\.\d{2}\.\d{4})\s+\d{1,2}:\d{2}\b')
            _mdt = _DOT_DT_RE.search(_full_text)
            if _mdt:
                report_date_detected = _parse_report_date(_mdt.group(1))
        # Fecha de última transacción
        last_tx_date_detected: Optional[str] = None
        _mlt = _LAST_TX_DATE_RE.search(_full_text)
        if _mlt:
            last_tx_date_detected = _parse_report_date(_mlt.group(1))
        # Fallback: max de todas las DD.MM.YYYY en el PDF (excluye fecha de reporte)
        if last_tx_date_detected is None:
            from datetime import datetime as _dt_p  # noqa: PLC0415
            _ALL_DATES_RE = re.compile(r'\b(\d{2}\.\d{2}\.\d{4})\b')
            _tx_dates = []
            for _d in _ALL_DATES_RE.findall(_full_text):
                try:
                    _parsed_d = _dt_p.strptime(_d, "%d.%m.%Y").date()
                    if report_date_detected and str(_parsed_d) == report_date_detected:
                        continue
                    _tx_dates.append(_parsed_d)
                except ValueError:
                    pass
            if _tx_dates:
                last_tx_date_detected = str(max(_tx_dates))
        # Montos totales SoF / UoF desde texto estructurado (override sobre suma de rows)
        _ms_sof_a = _SOF_TOTAL_AMOUNT_RE.search(_full_text)
        if _ms_sof_a:
            try:
                _sof_amt_override = float(_ms_sof_a.group(1).replace(',', ''))
            except ValueError:
                pass
        _ms_uof_a = _UOF_TOTAL_AMOUNT_RE.search(_full_text)
        if _ms_uof_a:
            try:
                _uof_amt_override = float(_ms_uof_a.group(1).replace(',', ''))
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

    # ── Construir risk_exposure_list con reglas de filtrado y consolidación ────
    #
    # REGLA DE ORO      : CRITICAL/HIGH → siempre visible, sin importar el %
    # REGLA DE RELEVANCIA: MEDIUM/LOW con % ≥ 5 → visible
    # REGLA RESIDUAL    : MEDIUM/LOW con % < 5  → agrupados en nota aclaratoria
    #
    _risk_level_map = {
        "Crítico": "CRITICAL", "Alto": "HIGH", "Medio": "MEDIUM",
        "Bajo": "LOW", "Sin Datos": "UNKNOWN",
    }

    # ── Extraer monto numérico del texto de entidad cuando viene embebido ─────
    # GL a veces emite "Gambling$1,234.56" o "High-risk exchange 5678.90"
    _AMOUNT_RE = re.compile(r'\$?\s*([\d,]+(?:\.\d{1,2})?)\s*$')

    def _extract_amount(entity_str: str, raw_row_amount: float) -> tuple[str, float]:
        """
        Extrae monto al final del nombre de entidad si está embebido.
        Retorna (entity_clean, amount).
        """
        m = _AMOUNT_RE.search(entity_str)
        if m:
            try:
                amt = float(m.group(1).replace(",", ""))
                clean = entity_str[:m.start()].strip()
                return clean, amt
            except ValueError:
                pass
        return entity_str, raw_row_amount

    # Consolidar: un entry por (entity, type) para sumar duplicados
    _consolidated: dict[tuple[str, str], dict] = {}
    for ind in indicators:
        _lvl_str  = _risk_level_map.get(ind["risk_level"], "UNKNOWN")
        _flow     = ind.get("flow", "unknown")
        _types    = (
            ["SoF"]        if _flow == "sof"  else
            ["UoF"]        if _flow == "uof"  else
            ["SoF", "UoF"]  # mixed o unknown → aparece en ambas tablas
        )
        _clean_entity, _amt = _extract_amount(ind["entity"], 0.0)

        for _t in _types:
            _key = (_clean_entity, _t)
            if _key in _consolidated:
                _consolidated[_key]["percentage"] += ind["total_pct"]
                _consolidated[_key]["amount"]     += _amt
            else:
                _consolidated[_key] = {
                    "label":      _clean_entity,
                    "level":      _lvl_str,
                    "amount":     _amt,
                    "percentage": ind["total_pct"],
                    "type":       _t,
                }

    # Aplicar reglas de filtrado
    _HIGH_LEVELS = {"CRITICAL", "HIGH"}
    _RELEVANCE_THRESHOLD = 5.0

    risk_exposure_list: list[dict] = []   # tabla principal
    _residuals: list[dict]          = []  # nota aclaratoria

    for item in _consolidated.values():
        item["percentage"] = round(item["percentage"], 6)
        _is_high = item["level"] in _HIGH_LEVELS
        _is_relevant = item["percentage"] >= _RELEVANCE_THRESHOLD
        if _is_high or _is_relevant:
            risk_exposure_list.append(item)
        else:
            _residuals.append(item)

    # Ordenar: HIGH/CRITICAL primero, luego por % desc
    _order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}
    risk_exposure_list.sort(
        key=lambda x: (_order.get(x["level"], 9), -x["percentage"])
    )

    # Totales globales SoF / UoF
    _sof_total_pct = sum(
        r["percentage"] for r in _consolidated.values() if r["type"] == "SoF"
    )
    _uof_total_pct = sum(
        r["percentage"] for r in _consolidated.values() if r["type"] == "UoF"
    )
    _sof_total_amt = sum(
        r["amount"] for r in _consolidated.values() if r["type"] == "SoF"
    )
    _uof_total_amt = sum(
        r["amount"] for r in _consolidated.values() if r["type"] == "UoF"
    )
    # Aplicar montos desde texto estructurado si se extrajeron (más precisos que la suma de rows)
    if _sof_amt_override is not None:
        _sof_total_amt = _sof_amt_override
    if _uof_amt_override is not None:
        _uof_total_amt = _uof_amt_override

    top_entity = indicators[0]["entity"] if indicators else None

    # ── GL Level: derivar del score (fuente primaria más confiable) ─────────
    _gl_level_detected: Optional[str] = None
    if gl_score_detected is not None:
        if gl_score_detected < 20:
            _gl_level_detected = "Crítico"
        elif gl_score_detected < 40:
            _gl_level_detected = "Alto"
        elif gl_score_detected <= 60:
            _gl_level_detected = "Medio"
        else:
            _gl_level_detected = "Bajo"
    else:
        _gl_level_detected = gl_risk_level_text  # None si tampoco hay detección de texto

    # Validación secundaria: buscar nivel inline cerca del score en el PDF
    _nivel_map_lv = {
        "critical": "Crítico", "critico": "Crítico",
        "high":     "Alto",    "alto":    "Alto",
        "medium":   "Medio",   "medio":   "Medio",
        "low":      "Bajo",    "bajo":    "Bajo",
    }
    if _gl_anchor != -1 and gl_score_detected is not None:
        _gl_window_lv = _full_text[_gl_anchor:_gl_anchor + 300].lower()
        _nivel_inline = re.search(
            r'\b\d{1,3}\b.*?\n\s*(critical|critico|high|medium|low|alto|medio|bajo)\b',
            _gl_window_lv, re.IGNORECASE,
        )
        if _nivel_inline:
            _nivel_raw = _nivel_inline.group(1).lower()
            _gl_level_detected = _nivel_map_lv.get(_nivel_raw, _gl_level_detected)

    # Garantizar que gl_level tenga valor derivado del score si todo lo demás falla
    if _gl_level_detected is None and gl_score_detected is not None:
        _gl_level_detected = (
            "Crítico" if gl_score_detected < 20 else
            "Alto"    if gl_score_detected < 40 else
            "Medio"   if gl_score_detected <= 60 else
            "Bajo"
        )
    return {
        "ok":                  True,
        "error":               None,
        "total_rows":          len(raw_rows),
        "high_risk_count":     len(high_risk),
        "medium_risk_count":   len(medium_risk),
        "indicators":          indicators,
        "risk_exposure_list":  risk_exposure_list,
        "residual_count":      len(_residuals),       # ← nota aclaratoria
        "sof_total_pct":       round(_sof_total_pct, 4),
        "uof_total_pct":       round(_uof_total_pct, 4),
        "sof_total_amount":    round(_sof_total_amt, 2),
        "uof_total_amount":    round(_uof_total_amt, 2),
        "sof_top":             sof_top,
        "uof_top":             uof_top,
        "top_entity":          top_entity,
        "tables_found":        tables_inspected,
        "wallet_detected":     wallet_detected,
        "gl_score_detected":   gl_score_detected,
        "report_date":           report_date_detected,
        "last_transaction_date": last_tx_date_detected,
        "gl_level":              _gl_level_detected,
        "gl_risk_level_text":    gl_risk_level_text,  # nivel desde texto (sin score)
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
