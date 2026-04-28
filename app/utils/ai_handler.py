"""
app/utils/ai_handler.py
Motor de IA centralizado — AdamoServices Partner Manager.

Proveedores soportados (vía AI_PROVIDER en .env):
  - "gemini"  (default) → google-generativeai
  - "openai"            → openai

Características:
  - Anonimización de PII antes de enviar a la API.
  - Caché en session_state con TTL de 30 minutos para evitar
    consumo innecesario de créditos.
  - Respuesta estructurada: urgencia, resumen, red_flags.
  - Retorna estado de error sin romper la UI si no hay API key.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────────────────────
AI_PROVIDER:  str = os.getenv("AI_PROVIDER", "gemini").lower()
GEMINI_KEY:   str = os.getenv("GEMINI_API_KEY", "")
OPENAI_KEY:   str = os.getenv("OPENAI_API_KEY", "")
# El nombre canónico para google-generativeai es sin prefijo "models/"
# La librería lo resuelve automáticamente contra la API v1 estable.
# gemini-2.0-flash es el modelo estable de la generación actual (abril 2026).
GEMINI_MODEL:  str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
# Cadena de fallback — se prueba en orden si el modelo principal da 404/not found
_GEMINI_FALLBACK_CHAIN: list[str] = [
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro",
]
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_CACHE_TTL_SECONDS: int = 30 * 60  # 30 min

# ─────────────────────────────────────────────────────────────
# Prompt del sistema — Oficial de Cumplimiento
# ─────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = (
    "Eres un Oficial de Cumplimiento experto en el sector financiero colombiano "
    "(SARLAFT, UIAF, Superfinanciera). Analiza la información operativa de un "
    "Banking Partner y extrae en formato JSON estricto:\n"
    "{\n"
    '  "urgencia": "<Bajo|Medio|Alto>",\n'
    '  "resumen": "<máximo 15 palabras>",\n'
    '  "red_flags": ["<señal 1>", "<señal 2>"]  // lista vacía si no hay\n'
    "}\n"
    "Responde SOLO el objeto JSON, sin explicaciones adicionales."
)

_USER_PROMPT_TEMPLATE = (
    "Analiza la siguiente gestión operativa de un Banking Partner "
    "(datos anonimizados):\n\n{texto}\n\n"
    "Recuerda: responde SOLO el JSON."
)

# ─────────────────────────────────────────────────────────────
# Anonimización de PII
# ─────────────────────────────────────────────────────────────
# Patrones a censurar antes de enviar a la API
_PII_PATTERNS: list[tuple[re.Pattern, str]] = [
    # NIT (ej: 900.123.456-1 | 9001234561)
    (re.compile(r"\b\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d\b"), "[NIT]"),
    # Cédula colombiana (6–10 dígitos aislados)
    (re.compile(r"\b\d{6,10}\b"), "[ID]"),
    # Emails
    (re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"), "[EMAIL]"),
    # Teléfonos colombianos (7–10 dígitos, con prefijo +57 opcional)
    (re.compile(r"(\+57[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}"), "[TEL]"),
    # Números de cuenta / tarjeta (12–19 dígitos continuos)
    (re.compile(r"\b\d{12,19}\b"), "[CUENTA]"),
    # Nombres propios en mayúsculas (heurístico: 2+ palabras todo mayúscula)
    (re.compile(r"\b([A-ZÁÉÍÓÚÑ]{3,}\s){1,3}[A-ZÁÉÍÓÚÑ]{3,}\b"), "[NOMBRE]"),
]


def anonymize_text(text: str) -> str:
    """Elimina PII del texto antes de enviarlo a la API de IA."""
    if not text:
        return text
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# ─────────────────────────────────────────────────────────────
# Caché en session_state
# ─────────────────────────────────────────────────────────────
def _cache_key(data: str) -> str:
    return "ai_cache_" + hashlib.sha256(data.encode()).hexdigest()[:16]


def _get_cached(key: str) -> dict | None:
    """Recupera resultado cacheado si aún no expiró."""
    try:
        import streamlit as st
        entry = st.session_state.get(key)
        if entry and (time.time() - entry["ts"]) < _CACHE_TTL_SECONDS:
            return entry["result"]
    except Exception:
        pass
    return None


def _set_cached(key: str, result: dict) -> None:
    try:
        import streamlit as st
        st.session_state[key] = {"result": result, "ts": time.time()}
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# Parseo de respuesta JSON del LLM
# ─────────────────────────────────────────────────────────────
def _parse_ai_response(raw: str) -> dict:
    """Parsea el JSON del LLM con fallback robusto."""
    import json

    # Eliminar bloques de código markdown si el modelo los añadió
    clean = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()

    try:
        data = json.loads(clean)
        urgencia   = str(data.get("urgencia", "Medio")).strip().capitalize()
        resumen    = str(data.get("resumen", "Sin resumen disponible")).strip()
        red_flags  = [str(f).strip() for f in data.get("red_flags", []) if f]
        # Normalizar urgencia
        if urgencia not in ("Bajo", "Medio", "Alto"):
            urgencia = "Medio"
        return {
            "urgencia":  urgencia,
            "resumen":   resumen,
            "red_flags": red_flags,
            "ok":        True,
        }
    except Exception as exc:
        logger.warning("ai_handler: error parseando respuesta JSON: %s | raw=%s", exc, raw[:200])
        return {
            "urgencia":  "Medio",
            "resumen":   "No se pudo parsear la respuesta.",
            "red_flags": [],
            "ok":        False,
            "error":     str(exc),
        }


# ─────────────────────────────────────────────────────────────
# Clientes LLM
# ─────────────────────────────────────────────────────────────
def _call_gemini(prompt: str, _tried: list[str] | None = None) -> str:
    """
    Llama a la API de Gemini usando la librería google-generativeai.
    - El nombre de modelo NO debe llevar prefijo 'models/'.
    - En caso de 404/not found prueba la cadena _GEMINI_FALLBACK_CHAIN en orden.
    """
    import google.generativeai as genai  # type: ignore

    if _tried is None:
        _tried = []

    # Determinar el modelo a intentar ahora
    if not _tried:
        target_model = GEMINI_MODEL
    else:
        remaining = [m for m in _GEMINI_FALLBACK_CHAIN if m not in _tried]
        if not remaining:
            raise RuntimeError(
                f"Todos los modelos Gemini fallaron: {_tried}. "
                "Verifica GEMINI_MODEL en .env o espera unos minutos."
            )
        target_model = remaining[0]

    # Normalizar: sin prefijo 'models/'
    target_model = target_model.removeprefix("models/")
    _tried.append(target_model)

    genai.configure(api_key=GEMINI_KEY)
    try:
        model = genai.GenerativeModel(
            model_name=target_model,
            system_instruction=_SYSTEM_PROMPT,
        )
        response = model.generate_content(prompt)
        if target_model != GEMINI_MODEL.removeprefix("models/"):
            logger.info(
                "ai_handler: usando modelo de fallback '%s' (principal: '%s')",
                target_model, GEMINI_MODEL,
            )
        return response.text
    except Exception as exc:
        err_str = str(exc).lower()
        # 404 / not found / invalid → modelo no disponible en esta API key
        if "404" in err_str or "not found" in err_str or "invalid argument" in err_str:
            logger.warning(
                "ai_handler: modelo '%s' no disponible (%s). "
                "Probando siguiente en cadena de fallback…",
                target_model, exc,
            )
            return _call_gemini(prompt, _tried=_tried)
        raise


def _call_openai(prompt: str) -> str:
    from openai import OpenAI  # type: ignore
    client = OpenAI(api_key=OPENAI_KEY)
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.2,
        max_tokens=256,
    )
    return resp.choices[0].message.content or ""


# ─────────────────────────────────────────────────────────────
# Función pública principal
# ─────────────────────────────────────────────────────────────
def analyze_gestion(context_data: dict) -> dict:
    """
    Analiza las notas de gestión de un aliado/partner.

    Parámetros:
        context_data: dict con claves relevantes del aliado:
          - nombre_alias: str (ya anonimizado o genérico)
          - tipo_aliado: str
          - nivel_riesgo: str
          - estado_pipeline: str
          - estado_sarlaft: str
          - estado_due_diligence: str
          - es_pep: bool
          - resultado_listas: str
          - alertas_activas: int
          - observaciones: str (texto libre de compliance)

    Retorna:
        {
          "urgencia":  "Bajo" | "Medio" | "Alto",
          "resumen":   "<15 palabras>",
          "red_flags": ["..."],
          "ok":        True | False,
          "error":     "<msg si ok=False>",   # opcional
          "cached":    True | False,
        }
    """
    # Verificar que haya API key activa
    api_key = GEMINI_KEY if AI_PROVIDER == "gemini" else OPENAI_KEY
    if not api_key:
        return {
            "urgencia":  "—",
            "resumen":   "API key no configurada.",
            "red_flags": [],
            "ok":        False,
            "error":     "no_key",
            "cached":    False,
        }

    # Armar texto a analizar con anonimización
    # Sanear observaciones: eliminar caracteres de control y normalizar saltos de línea
    obs_raw  = context_data.get("observaciones") or ""
    obs_clean = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", obs_raw)   # ctrl chars
    obs_clean = re.sub(r"\r\n|\r", "\n", obs_clean).strip()           # normalize CRLF
    obs_anon  = anonymize_text(obs_clean) or "Sin observaciones registradas."

    texto = (
        f"Tipo: {context_data.get('tipo_aliado', 'N/A')}\n"
        f"Riesgo: {context_data.get('nivel_riesgo', 'N/A')}\n"
        f"Pipeline: {context_data.get('estado_pipeline', 'N/A')}\n"
        f"SARLAFT: {context_data.get('estado_sarlaft', 'N/A')}\n"
        f"Due Diligence: {context_data.get('estado_due_diligence', 'N/A')}\n"
        f"PEP: {'Sí' if context_data.get('es_pep') else 'No'}\n"
        f"Listas restrictivas: {context_data.get('resultado_listas', 'N/A')}\n"
        f"Alertas activas: {context_data.get('alertas_activas', 0)}\n"
        f"Observaciones:\n{obs_anon}"
    )

    ckey = _cache_key(texto)
    cached = _get_cached(ckey)
    if cached:
        return {**cached, "cached": True}

    prompt = _USER_PROMPT_TEMPLATE.format(texto=texto)

    try:
        if AI_PROVIDER == "gemini":
            raw = _call_gemini(prompt)
        else:
            raw = _call_openai(prompt)

        result = _parse_ai_response(raw)
    except Exception as exc:
        err_str = str(exc)
        logger.error("ai_handler: error llamando a %s: %s", AI_PROVIDER, err_str)
        # Mensaje de ayuda contextual
        if "404" in err_str or "not found" in err_str.lower():
            hint = (
                "Modelo no encontrado. Revisa GEMINI_MODEL en .env — "
                "usa 'gemini-1.5-flash' (sin prefijo 'models/')."
            )
        elif "api_key" in err_str.lower() or "authentication" in err_str.lower():
            hint = "API key inválida. Verifica GEMINI_API_KEY en .env."
        else:
            hint = err_str
        result = {
            "urgencia":  "Medio",
            "resumen":   "Error al contactar la API de IA.",
            "red_flags": [],
            "ok":        False,
            "error":     hint,
        }

    _set_cached(ckey, result)
    return {**result, "cached": False}
