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

# ── 3. Propagar SECRET_KEY como clave de firma de cookies de sesión ────────
# Streamlit usa STREAMLIT_SERVER_COOKIE_SECRET para firmar el token de sesión.
# La misma clave configura el firmado criptográfico del lado del servidor.
if [ -n "${SECRET_KEY:-}" ]; then
    export STREAMLIT_SERVER_COOKIE_SECRET="$SECRET_KEY"
    echo "[AdamoServices] STREAMLIT_SERVER_COOKIE_SECRET configurado desde SECRET_KEY."
else
    echo "[AdamoServices] ADVERTENCIA: SECRET_KEY no definida — las sesiones no serán seguras."
fi

# ── 4. Puerto dinámico: Railway inyecta $PORT; defecto 8501 ──────
PORT="${PORT:-8501}"

# ── 5. Arrancar Streamlit ─────────────────────────────────────────
echo "[AdamoServices] Iniciando Streamlit en el puerto $PORT..."
exec python -m streamlit run app/main.py \
    --server.port "$PORT" \
    --server.address "0.0.0.0" \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection true \
    --browser.gatherUsageStats false
