"""
app/webhook.py
Webhook HTTP para Power Automate — Bandeja de Cumplimiento.

Corre como servidor Flask independiente en PORT_WEBHOOK (default 8502).
Lanzado en segundo plano desde entrypoint.sh: python app/webhook.py &

Endpoint:
    POST /webhook/email
    Header: X-Webhook-Secret: <WEBHOOK_SECRET>
    Body: JSON con campos de EmailCasoCreate
"""

from __future__ import annotations

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Ajustar path para imports del proyecto
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flask import Flask, request, jsonify

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [webhook] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
PORT_WEBHOOK   = int(os.getenv("PORT_WEBHOOK", "8502"))


def _secret_ok(req) -> bool:
    """Valida X-Webhook-Secret. En dev (sin WEBHOOK_SECRET) permite todo."""
    if not WEBHOOK_SECRET:
        logger.warning("WEBHOOK_SECRET no configurado — validación deshabilitada")
        return True
    return req.headers.get("X-Webhook-Secret", "") == WEBHOOK_SECRET


@app.route("/webhook/email", methods=["POST"])
def webhook_email():
    """Recibe un correo de Power Automate y lo registra como caso."""
    if not _secret_ok(request):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"ok": False, "error": "Se requiere JSON en el body"}), 400

    required = ("empresa", "buzon", "remitente", "asunto")
    missing  = [f for f in required if not payload.get(f)]
    if missing:
        return jsonify({"ok": False, "error": f"Campos requeridos: {missing}"}), 422

    try:
        from db.database import get_session
        from db.repositories.email_repo import EmailRepository
        from db.models import EmailCasoCreate

        fecha_raw = payload.get("fecha_recepcion")
        fecha_dt: datetime | None = None
        if fecha_raw:
            try:
                fecha_dt = datetime.fromisoformat(fecha_raw.replace("Z", "+00:00"))
            except ValueError:
                logger.warning("webhook_email: fecha_recepcion inválida '%s', usando NOW()", fecha_raw)

        data = EmailCasoCreate(
            empresa            = payload["empresa"],
            buzon              = payload["buzon"],
            remitente          = payload["remitente"],
            asunto             = payload["asunto"],
            cuerpo             = payload.get("cuerpo"),
            fecha_recepcion    = fecha_dt,
            message_id_externo = payload.get("message_id_externo"),
            prioridad          = payload.get("prioridad", "Normal"),
        )

        with next(get_session()) as session:
            repo = EmailRepository(session)
            caso = repo.crear(data)

        logger.info("webhook_email: caso_id=%s empresa=%s", caso["id"], data.empresa)
        return jsonify({"ok": True, "caso_id": caso["id"]}), 200

    except ValueError as exc:
        logger.warning("webhook_email: validación: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 422
    except Exception as exc:
        logger.error("webhook_email: error inesperado: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": "Error interno del servidor"}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "webhook"}), 200


if __name__ == "__main__":
    logger.info("Iniciando webhook en puerto %s", PORT_WEBHOOK)
    app.run(host="0.0.0.0", port=PORT_WEBHOOK, debug=False)
