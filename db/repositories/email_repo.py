"""
db/repositories/email_repo.py
Repositorio de la Bandeja de Cumplimiento.
Gestiona CRUD sobre email_casos con auditoría completa.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

from db.models import EmailCasoCreate, EmailCasoUpdate

logger = logging.getLogger(__name__)

_ESTADOS_VALIDOS    = {"Nuevo", "En gestión", "Resuelto", "Escalado"}
_PRIORIDADES_VALIDAS = {"Alta", "Normal", "Baja"}

# Columnas a seleccionar — la columna tiene tilde en BD, se alías como 'buzon'
_SELECT_COLS = """
    id, empresa, "buzón" AS buzon, remitente, asunto,
    cuerpo, fecha_recepcion, message_id_externo,
    estado, prioridad, notas_internas, atendido_por,
    fecha_resolucion, creado_en, actualizado_en
"""


class EmailRepository:
    """Acceso a la tabla email_casos."""

    def __init__(self, session: Session):
        self.session = session

    # ── Helper de auditoría ───────────────────────────────────

    def _auditar(
        self,
        accion: str,
        entidad_id: int,
        descripcion: str,
        usuario: str,
        valores_anteriores: Optional[dict] = None,
        valores_nuevos: Optional[dict] = None,
    ) -> None:
        from db.repositories.audit_repo import AuditRepository
        AuditRepository(self.session).registrar(
            username=usuario,
            accion=accion,
            entidad="email_casos",
            descripcion=descripcion,
            entidad_id=entidad_id,
            valores_anteriores=valores_anteriores,
            valores_nuevos=valores_nuevos,
        )

    # ── Creación ──────────────────────────────────────────────

    def crear(self, data: EmailCasoCreate) -> dict:
        """
        Inserta un nuevo caso.
        Idempotente: si message_id_externo ya existe, retorna el caso existente
        sin error (evita duplicados en reenvíos de Power Automate).
        """
        if data.message_id_externo:
            existing = self.session.execute(text(f"""
                SELECT {_SELECT_COLS}
                FROM email_casos
                WHERE message_id_externo = :mid
            """), {"mid": data.message_id_externo}).mappings().first()
            if existing:
                logger.debug("email_caso.crear: idempotente, message_id ya existe %s", data.message_id_externo)
                return dict(existing)

        fecha = data.fecha_recepcion or datetime.now(tz=timezone.utc)
        row = self.session.execute(text(f"""
            INSERT INTO email_casos
                (empresa, "buzón", remitente, asunto, cuerpo,
                 fecha_recepcion, message_id_externo, prioridad)
            VALUES
                (:empresa, :buzon, :remitente, :asunto, :cuerpo,
                 :fecha_recepcion, :message_id_externo, :prioridad)
            RETURNING {_SELECT_COLS}
        """), {
            "empresa":            data.empresa,
            "buzon":              data.buzon,
            "remitente":          data.remitente,
            "asunto":             data.asunto,
            "cuerpo":             data.cuerpo,
            "fecha_recepcion":    fecha.isoformat(),
            "message_id_externo": data.message_id_externo,
            "prioridad":          data.prioridad,
        }).mappings().first()

        self.session.commit()
        logger.info("email_caso.crear id=%s remitente=%s", row["id"], data.remitente)
        return dict(row)

    # ── Lectura ───────────────────────────────────────────────

    def get_by_id(self, caso_id: int) -> Optional[dict]:
        row = self.session.execute(text(f"""
            SELECT {_SELECT_COLS}
            FROM email_casos
            WHERE id = :caso_id
        """), {"caso_id": caso_id}).mappings().first()
        return dict(row) if row else None

    def get_lista(
        self,
        empresa: Optional[str] = None,
        estado: Optional[str] = None,
        prioridad: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[dict]:
        where: list[str] = []
        params: dict = {}

        if empresa:
            where.append("empresa = :empresa")
            params["empresa"] = empresa
        if estado:
            where.append("estado = :estado")
            params["estado"] = estado
        if prioridad:
            where.append("prioridad = :prioridad")
            params["prioridad"] = prioridad
        if search:
            where.append("(asunto ILIKE :s OR remitente ILIKE :s)")
            params["s"] = f"%{search}%"

        where_clause = ("WHERE " + " AND ".join(where)) if where else ""

        rows = self.session.execute(text(f"""
            SELECT {_SELECT_COLS}
            FROM email_casos
            {where_clause}
            ORDER BY fecha_recepcion DESC
        """), params).mappings().all()

        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        row = self.session.execute(text("""
            SELECT
                COUNT(*)                                        AS total,
                COUNT(*) FILTER (WHERE estado = 'Nuevo')        AS nuevos,
                COUNT(*) FILTER (WHERE estado = 'En gestión')   AS en_gestion,
                COUNT(*) FILTER (WHERE estado = 'Resuelto')     AS resueltos,
                COUNT(*) FILTER (WHERE estado = 'Escalado')     AS escalados
            FROM email_casos
        """)).mappings().fetchone()
        return dict(row)

    def get_casos_por_empresa(self) -> dict:
        rows = self.session.execute(text("""
            SELECT empresa, COUNT(*) AS total
            FROM email_casos
            GROUP BY empresa
            ORDER BY empresa
        """)).mappings().all()
        return {r["empresa"]: r["total"] for r in rows}

    # ── Actualización ─────────────────────────────────────────

    def actualizar(self, caso_id: int, data: EmailCasoUpdate, usuario: str) -> dict:
        """UPDATE campos permitidos + registra auditoría."""
        anterior = self.get_by_id(caso_id)
        if not anterior:
            raise ValueError(f"Caso {caso_id} no encontrado")

        sets: list[str] = []
        params: dict = {"caso_id": caso_id}

        if data.estado is not None:
            if data.estado not in _ESTADOS_VALIDOS:
                raise ValueError(f"Estado inválido: {data.estado}")
            sets.append("estado = :estado")
            params["estado"] = data.estado
            if data.estado == "Resuelto":
                sets.append("fecha_resolucion = NOW()")

        if data.prioridad is not None:
            if data.prioridad not in _PRIORIDADES_VALIDAS:
                raise ValueError(f"Prioridad inválida: {data.prioridad}")
            sets.append("prioridad = :prioridad")
            params["prioridad"] = data.prioridad

        if data.notas_internas is not None:
            sets.append("notas_internas = :notas_internas")
            params["notas_internas"] = data.notas_internas

        if data.atendido_por is not None:
            sets.append("atendido_por = :atendido_por")
            params["atendido_por"] = data.atendido_por

        if data.fecha_resolucion is not None:
            sets.append("fecha_resolucion = :fecha_resolucion")
            params["fecha_resolucion"] = data.fecha_resolucion.isoformat()

        if not sets:
            return anterior

        self.session.execute(text(f"""
            UPDATE email_casos
            SET {', '.join(sets)}
            WHERE id = :caso_id
        """), params)
        self.session.commit()

        nuevo = self.get_by_id(caso_id)
        self._auditar(
            accion="UPDATE",
            entidad_id=caso_id,
            descripcion=f"Actualización caso #{caso_id}: {anterior.get('asunto', '')}",
            usuario=usuario,
            valores_anteriores=anterior,
            valores_nuevos=nuevo,
        )
        return nuevo

    def cambiar_estado(self, caso_id: int, nuevo_estado: str, usuario: str) -> bool:
        """Cambia estado + si es 'Resuelto' setea fecha_resolucion = NOW()."""
        if nuevo_estado not in _ESTADOS_VALIDOS:
            raise ValueError(f"Estado inválido: {nuevo_estado}")

        anterior = self.get_by_id(caso_id)
        if not anterior:
            return False

        fecha_extra = ", fecha_resolucion = NOW()" if nuevo_estado == "Resuelto" else ""
        self.session.execute(text(f"""
            UPDATE email_casos
            SET estado = :estado{fecha_extra}
            WHERE id = :caso_id
        """), {"caso_id": caso_id, "estado": nuevo_estado})
        self.session.commit()

        self._auditar(
            accion="ESTADO_CHANGE",
            entidad_id=caso_id,
            descripcion=f"Estado caso #{caso_id}: {anterior['estado']} → {nuevo_estado}",
            usuario=usuario,
            valores_anteriores={"estado": anterior["estado"]},
            valores_nuevos={"estado": nuevo_estado},
        )
        return True
