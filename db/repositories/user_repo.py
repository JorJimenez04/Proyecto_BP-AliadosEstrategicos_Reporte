"""
db/repositories/user_repo.py
Repositorio de Usuarios — consulta de usuarios para autenticación.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class UserRepository:
    """Consultas de usuarios usadas por el flujo de autenticación."""

    def __init__(self, session: Session):
        self.session = session

    # ── Consultas ─────────────────────────────────────────

    def get_by_username(self, username: str) -> Optional[dict]:
        row = self.session.execute(
            text("SELECT * FROM usuarios WHERE username = :u"),
            {"u": username},
        ).mappings().first()
        return dict(row) if row else None

    def get_by_id(self, user_id: int) -> Optional[dict]:
        row = self.session.execute(
            text("SELECT * FROM usuarios WHERE id = :id"),
            {"id": user_id},
        ).mappings().first()
        return dict(row) if row else None


    # ── Crear ─────────────────────────────────────────────


    # ── Actualizar ────────────────────────────────────────


    # ── KPIs de Desempeño ─────────────────────────────────

