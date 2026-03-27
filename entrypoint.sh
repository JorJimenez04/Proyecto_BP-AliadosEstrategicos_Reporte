#!/bin/bash
# entrypoint.sh — AdamoServices Partner Manager
# Ejecuta migraciones y luego arranca Streamlit.
# Usado por Docker/Railway como punto de entrada del contenedor.
set -euo pipefail

# ── 1. Verificación de variables críticas (solo en producción) ────
APP_ENV="${APP_ENV:-development}"
if [ "$APP_ENV" = "production" ]; then
    python -c "from app.utils.production_check import run_checks; run_checks()"
fi

# ── 2. Inicialización / migración de la base de datos ────────────
echo "[AdamoServices] Ejecutando migraciones de base de datos..."
python -m db.database
echo "[AdamoServices] Migraciones completadas."

# ── 3. Puerto dinámico: Railway inyecta $PORT; defecto 8501 ──────
PORT="${PORT:-8501}"

# ── 4. Arrancar Streamlit ─────────────────────────────────────────
echo "[AdamoServices] Iniciando Streamlit en el puerto $PORT..."
exec python -m streamlit run app/main.py \
    --server.port "$PORT" \
    --server.address "0.0.0.0" \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection true \
    --browser.gatherUsageStats false
