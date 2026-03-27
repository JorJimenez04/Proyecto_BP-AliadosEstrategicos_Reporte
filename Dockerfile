# ─────────────────────────────────────────────────────────────────
# Dockerfile — AdamoServices Partner Manager
# Base: python:3.10-slim  |  Target: Railway (PostgreSQL)
# ─────────────────────────────────────────────────────────────────

FROM python:3.10-slim AS base

# Evitar archivos .pyc y que Python bufferice stdout (logs en tiempo real)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Telemetría de Streamlit desactivada en producción
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true

# ── Dependencias del sistema mínimas ─────────────────────────────
# libpq-dev + gcc son necesarios para psycopg2-binary en slim
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Directorio de trabajo ─────────────────────────────────────────
WORKDIR /app

# ── Dependencias Python (capa separada para mejor cache) ─────────
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# ── Copiar el código fuente ───────────────────────────────────────
COPY . .

# ── Script de entrada ─────────────────────────────────────────────
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ── Puerto dinámico Railway ($PORT) o 8501 por defecto ───────────
# Railway inyecta $PORT; Streamlit lo leerá vía entrypoint.sh
EXPOSE 8501

# ── Healthcheck ───────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8501}/_stcore/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
