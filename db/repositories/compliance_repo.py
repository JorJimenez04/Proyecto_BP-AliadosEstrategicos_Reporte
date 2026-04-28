"""
db/repositories/compliance_repo.py
Repositorio del modulo Centro Documental de Cumplimiento.
Gestiona CRUD sobre compliance_documentos con auditoria.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class ComplianceRepository:
    """Acceso a la tabla compliance_documentos."""

    def __init__(self, session: Session):
        self.session = session

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """
        Devuelve metricas agregadas para los KPI cards.
        Retorna: {total, vigentes, pendientes, vencidos, archivados, por_carpeta}
        """
        row = self.session.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE estado != 'Archivado')                    AS total,
                COUNT(*) FILTER (WHERE estado = 'Vigente')                       AS vigentes,
                COUNT(*) FILTER (WHERE estado = 'Pendiente')                     AS pendientes,
                COUNT(*) FILTER (WHERE estado = 'Vencido')                       AS vencidos,
                COUNT(*) FILTER (WHERE estado = 'Archivado')                     AS archivados
            FROM compliance_documentos
        """)).mappings().fetchone()

        por_carpeta = self.session.execute(text("""
            SELECT
                carpeta,
                COUNT(*) FILTER (WHERE estado != 'Archivado') AS total,
                COUNT(*) FILTER (WHERE estado = 'Vigente')    AS vigentes
            FROM compliance_documentos
            GROUP BY carpeta
            ORDER BY carpeta
        """)).mappings().fetchall()

        return {
            "total":      int(row["total"])     if row["total"]      else 0,
            "vigentes":   int(row["vigentes"])  if row["vigentes"]   else 0,
            "pendientes": int(row["pendientes"])if row["pendientes"] else 0,
            "vencidos":   int(row["vencidos"])  if row["vencidos"]   else 0,
            "archivados": int(row["archivados"])if row["archivados"] else 0,
            "por_carpeta": [dict(r) for r in por_carpeta],
        }

    def get_documentos(
        self,
        carpeta: Optional[str] = None,
        estado: Optional[str] = None,
    ) -> list:
        """
        Devuelve documentos activos (no archivados) con filtros opcionales.
        """
        conditions = ["estado != 'Archivado'"]
        params: dict = {}

        if carpeta:
            conditions.append("carpeta = :carpeta")
            params["carpeta"] = carpeta
        if estado and estado != "Todos":
            conditions.append("estado = :estado")
            params["estado"] = estado

        where = " AND ".join(conditions)
        rows = self.session.execute(text(f"""
            SELECT id, carpeta, codigo, nombre, descripcion,
                   version, estado, formato, url_documento,
                   fecha_emision, fecha_vencimiento,
                   creado_por, actualizado_por,
                   created_at, updated_at
            FROM compliance_documentos
            WHERE {where}
            ORDER BY carpeta, codigo, nombre
        """), params).mappings().fetchall()
        return [dict(r) for r in rows]

    def get_by_id(self, doc_id: int) -> Optional[dict]:
        row = self.session.execute(text("""
            SELECT * FROM compliance_documentos WHERE id = :id
        """), {"id": doc_id}).mappings().fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def crear(self, data: dict, creado_por: str) -> int:
        """
        Inserta un nuevo documento.
        Retorna el id generado.
        """
        result = self.session.execute(text("""
            INSERT INTO compliance_documentos
                (carpeta, codigo, nombre, descripcion, version, estado,
                 formato, url_documento, fecha_emision, fecha_vencimiento,
                 creado_por)
            VALUES
                (:carpeta, :codigo, :nombre, :descripcion, :version, :estado,
                 :formato, :url_documento, :fecha_emision, :fecha_vencimiento,
                 :creado_por)
            RETURNING id
        """), {
            "carpeta":          data.get("carpeta"),
            "codigo":           data.get("codigo", ""),
            "nombre":           data.get("nombre", ""),
            "descripcion":      data.get("descripcion"),
            "version":          data.get("version", "1.0"),
            "estado":           data.get("estado", "Vigente"),
            "formato":          data.get("formato", "PDF"),
            "url_documento":    data.get("url_documento"),
            "fecha_emision":    data.get("fecha_emision"),
            "fecha_vencimiento":data.get("fecha_vencimiento"),
            "creado_por":       creado_por,
        })
        self.session.commit()
        new_id = result.scalar()
        logger.info("[Compliance] Documento creado id=%s por %s", new_id, creado_por)
        return new_id

    def actualizar(self, doc_id: int, data: dict, actualizado_por: str) -> None:
        """Actualiza campos editables de un documento."""
        self.session.execute(text("""
            UPDATE compliance_documentos
            SET carpeta          = :carpeta,
                codigo           = :codigo,
                nombre           = :nombre,
                descripcion      = :descripcion,
                version          = :version,
                estado           = :estado,
                formato          = :formato,
                url_documento    = :url_documento,
                fecha_emision    = :fecha_emision,
                fecha_vencimiento= :fecha_vencimiento,
                actualizado_por  = :actualizado_por
            WHERE id = :id
        """), {**data, "id": doc_id, "actualizado_por": actualizado_por})
        self.session.commit()
        logger.info("[Compliance] Documento id=%s actualizado por %s", doc_id, actualizado_por)

    def nueva_version(
        self,
        doc_id: int,
        nueva_version: str,
        nueva_url: Optional[str],
        descripcion_cambio: Optional[str],
        actualizado_por: str,
    ) -> None:
        """
        Sube version, actualiza URL y estado → Vigente.
        Registra la auditoria si hay sesion disponible.
        """
        doc_anterior = self.get_by_id(doc_id)
        self.session.execute(text("""
            UPDATE compliance_documentos
            SET version         = :version,
                url_documento   = :url,
                estado          = 'Vigente',
                descripcion     = COALESCE(:descripcion, descripcion),
                actualizado_por = :actualizado_por
            WHERE id = :id
        """), {
            "version":       nueva_version,
            "url":           nueva_url,
            "descripcion":   descripcion_cambio,
            "actualizado_por": actualizado_por,
            "id":            doc_id,
        })
        self.session.commit()

        try:
            from db.repositories.audit_repo import AuditRepository
            audit = AuditRepository(self.session)
            audit.registrar(
                username=actualizado_por,
                accion="UPDATE",
                entidad="compliance_documentos",
                descripcion=(
                    f"Nueva versión {nueva_version} para documento id={doc_id}: "
                    f"{descripcion_cambio or '-'}"
                ),
                entidad_id=doc_id,
                valores_anteriores={"version": doc_anterior.get("version")} if doc_anterior else None,
                valores_nuevos={"version": nueva_version},
                resultado="exitoso",
            )
        except Exception as exc:
            logger.warning("[Compliance] Auditoria no registrada: %s", exc)

        logger.info(
            "[Compliance] Doc id=%s → v%s por %s", doc_id, nueva_version, actualizado_por
        )

    def archivar(self, doc_id: int, actualizado_por: str) -> None:
        """Soft delete: cambia estado a Archivado."""
        self.session.execute(text("""
            UPDATE compliance_documentos
            SET estado = 'Archivado', actualizado_por = :actualizado_por
            WHERE id = :id
        """), {"id": doc_id, "actualizado_por": actualizado_por})
        self.session.commit()
        logger.info("[Compliance] Doc id=%s archivado por %s", doc_id, actualizado_por)
