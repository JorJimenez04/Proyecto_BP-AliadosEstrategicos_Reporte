"""
db/repositories/audit_repo.py
Repositorio del Log de Auditoría.
Registro inmutable de todas las acciones para cumplimiento regulatorio.
"""

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class AuditRepository:
    """
    Gestiona el registro y consulta del log de auditoría.
    El log es de SOLO ESCRITURA y SOLO LECTURA — nunca se edita ni elimina.
    """

    def __init__(self, session: Session):
        self.session = session

    def registrar(
        self,
        username: str,
        accion: str,
        entidad: str,
        descripcion: str,
        usuario_id: Optional[int] = None,
        entidad_id: Optional[int] = None,
        valores_anteriores: Optional[dict] = None,
        valores_nuevos: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resultado: str = "exitoso",
    ) -> None:
        """
        Registra una acción en el log de auditoría.

        Args:
            username:           Nombre de usuario que ejecutó la acción.
            accion:             Tipo de acción: CREATE | UPDATE | DELETE | LOGIN | EXPORT | ESTADO_CHANGE.
            entidad:            Tabla afectada: 'aliados', 'usuarios', etc.
            descripcion:        Descripción legible en español del cambio.
            usuario_id:         ID del usuario en la tabla usuarios.
            entidad_id:         ID del registro afectado.
            valores_anteriores: Dict con campos antes del cambio (serializado a JSON).
            valores_nuevos:     Dict con campos después del cambio (serializado a JSON).
            ip_address:         IP del cliente.
            user_agent:         User agent del navegador.
            resultado:          'exitoso' | 'fallido' | 'rechazado'.
        """
        self.session.execute(
            text("""
                INSERT INTO log_auditoria (
                    usuario_id, username, accion, entidad, entidad_id,
                    descripcion, valores_anteriores, valores_nuevos,
                    ip_address, user_agent, resultado
                ) VALUES (
                    :usuario_id, :username, :accion, :entidad, :entidad_id,
                    :descripcion, :valores_anteriores, :valores_nuevos,
                    :ip_address, :user_agent, :resultado
                )
            """),
            {
                "usuario_id":         usuario_id,
                "username":           username,
                "accion":             accion,
                "entidad":            entidad,
                "entidad_id":         entidad_id,
                "descripcion":        descripcion,
                "valores_anteriores": json.dumps(valores_anteriores, default=str) if valores_anteriores else None,
                "valores_nuevos":     json.dumps(valores_nuevos, default=str) if valores_nuevos else None,
                "ip_address":         ip_address,
                "user_agent":         user_agent,
                "resultado":          resultado,
            },
        )
        self.session.commit()
        logger.info(f"[AUDIT] {username} | {accion} | {entidad}:{entidad_id} | {resultado}")

    def list_log(
        self,
        usuario_id: Optional[int] = None,
        entidad: Optional[str] = None,
        accion: Optional[str] = None,
        fecha_desde: Optional[str] = None,
        fecha_hasta: Optional[str] = None,
        limit: int = 200,
    ) -> list[dict]:
        """
        Consulta el log con filtros opcionales.
        Retorna registros ordenados del más reciente al más antiguo.
        """
        query = "SELECT * FROM log_auditoria WHERE 1=1"
        params: dict = {}

        if usuario_id:
            query += " AND usuario_id = :usuario_id"
            params["usuario_id"] = usuario_id

        if entidad:
            query += " AND entidad = :entidad"
            params["entidad"] = entidad

        if accion:
            query += " AND accion = :accion"
            params["accion"] = accion

        if fecha_desde:
            query += " AND created_at::date >= :fecha_desde"
            params["fecha_desde"] = fecha_desde

        if fecha_hasta:
            query += " AND created_at::date <= :fecha_hasta"
            params["fecha_hasta"] = fecha_hasta

        query += f" ORDER BY created_at DESC LIMIT {int(limit)}"
        rows = self.session.execute(text(query), params).mappings().all()
        return [dict(r) for r in rows]

    def get_actividad_usuario(self, usuario_id: int, limit: int = 50) -> list[dict]:
        """Retorna las últimas N acciones de un usuario específico."""
        rows = self.session.execute(
            text("""
                SELECT * FROM log_auditoria
                WHERE usuario_id = :id
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"id": usuario_id, "limit": limit},
        ).mappings().all()
        return [dict(r) for r in rows]
