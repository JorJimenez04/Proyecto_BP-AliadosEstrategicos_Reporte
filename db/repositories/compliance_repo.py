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

    def get_stats(self, empresa: Optional[str] = None) -> dict:
        """
        Devuelve metricas agregadas para los KPI cards.
        Retorna: {total, vigentes, pendientes, vencidos, archivados, por_carpeta}
        Filtra por empresa cuando se indica; NULL empresa = compartido.
        """
        where_parts: list[str] = []
        params: dict = {}
        if empresa:
            where_parts.append("empresa = :empresa")
            params["empresa"] = empresa
        where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

        row = self.session.execute(text(f"""
            SELECT
                COUNT(*) FILTER (WHERE estado != 'Archivado')  AS total,
                COUNT(*) FILTER (WHERE estado = 'Vigente')     AS vigentes,
                COUNT(*) FILTER (WHERE estado = 'Pendiente')   AS pendientes,
                COUNT(*) FILTER (WHERE estado = 'Vencido')     AS vencidos,
                COUNT(*) FILTER (WHERE estado = 'Archivado')   AS archivados
            FROM compliance_documentos
            {where_clause}
        """), params).mappings().fetchone()

        por_carpeta = self.session.execute(text(f"""
            SELECT
                carpeta,
                COUNT(*) FILTER (WHERE estado != 'Archivado')  AS total,
                COUNT(*) FILTER (WHERE estado = 'Vigente')     AS vigentes,
                COUNT(*) FILTER (WHERE estado = 'Pendiente')   AS pendientes,
                COUNT(*) FILTER (WHERE estado = 'Vencido')     AS vencidos
            FROM compliance_documentos
            {where_clause}
            GROUP BY carpeta
            ORDER BY carpeta
        """), params).mappings().fetchall()

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
        empresa: Optional[str] = None,
    ) -> list:
        """
        Devuelve documentos activos (no archivados) con filtros opcionales.
        empresa="Todos" o None → sin filtro de empresa (retorna todos).
        Siempre retorna una lista Python; nunca una fuente alternativa.
        """
        # Normalizar: "Todos" equivale a sin filtro
        if empresa == "Todos":
            empresa = None

        conditions = ["estado != 'Archivado'"]
        params: dict = {}

        if carpeta:
            conditions.append("carpeta = :carpeta")
            params["carpeta"] = carpeta
        if estado and estado != "Todos":
            conditions.append("estado = :estado")
            params["estado"] = estado
        if empresa:
            conditions.append("empresa = :empresa")
            params["empresa"] = empresa

        where = " AND ".join(conditions)
        rows = self.session.execute(text(f"""
            SELECT id, carpeta, codigo, nombre, descripcion,
                   version, estado, formato, url_documento,
                   fecha_emision, fecha_vencimiento, empresa,
                   creado_por, actualizado_por,
                   created_at, updated_at
            FROM compliance_documentos
            WHERE {where}
            ORDER BY carpeta, codigo, nombre
        """), params).mappings().fetchall()
        result = [dict(r) for r in rows]
        logger.debug("[Compliance] get_documentos → %d filas (carpeta=%s empresa=%s)",
                     len(result), carpeta, empresa)
        return result

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
                 empresa, creado_por)
            VALUES
                (:carpeta, :codigo, :nombre, :descripcion, :version, :estado,
                 :formato, :url_documento, :fecha_emision, :fecha_vencimiento,
                 :empresa, :creado_por)
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
            "empresa":          data.get("empresa"),
            "creado_por":       creado_por,
        })
        self.session.commit()
        new_id = result.scalar()
        logger.info("[Compliance] Documento creado id=%s por %s", new_id, creado_por)
        return new_id

    def actualizar(self, doc_id: int, data: dict, actualizado_por: str) -> None:
        """
        Actualiza campos editables de un documento.
        Antes de aplicar el UPDATE congela la versión actual en
        compliance_documentos_historial (versionamiento inmutable).
        """
        # ── 1. Congelar versión actual ─────────────────────────────────
        anterior = self.get_by_id(doc_id)
        if anterior:
            self.session.execute(text("""
                INSERT INTO compliance_documentos_historial
                    (documento_raiz_id, carpeta, codigo, nombre, descripcion,
                     version, estado, formato, url_documento,
                     fecha_emision, fecha_vencimiento, empresa,
                     creado_por, actualizado_por,
                     descripcion_cambio, snapshot_por, snapshot_at)
                VALUES
                    (:documento_raiz_id, :carpeta, :codigo, :nombre, :descripcion,
                     :version, :estado, :formato, :url_documento,
                     :fecha_emision, :fecha_vencimiento, :empresa,
                     :creado_por, :actualizado_por,
                     :descripcion_cambio, :snapshot_por, CURRENT_TIMESTAMP)
            """), {
                "documento_raiz_id":  doc_id,
                "carpeta":            anterior.get("carpeta"),
                "codigo":             anterior.get("codigo"),
                "nombre":             anterior.get("nombre"),
                "descripcion":        anterior.get("descripcion"),
                "version":            anterior.get("version"),
                "estado":             anterior.get("estado"),
                "formato":            anterior.get("formato"),
                "url_documento":      anterior.get("url_documento"),
                "fecha_emision":      anterior.get("fecha_emision"),
                "fecha_vencimiento":  anterior.get("fecha_vencimiento"),
                "empresa":            anterior.get("empresa"),
                "creado_por":         anterior.get("creado_por"),
                "actualizado_por":    anterior.get("actualizado_por"),
                "descripcion_cambio": data.get("descripcion"),
                "snapshot_por":       actualizado_por,
            })

        # ── 2. Aplicar cambios en la tabla principal ───────────────────
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
                empresa          = :empresa,
                actualizado_por  = :actualizado_por
            WHERE id = :id
        """), {**data, "id": doc_id, "actualizado_por": actualizado_por})
        self.session.commit()
        logger.info("[Compliance] Documento id=%s actualizado por %s (snapshot guardado)", doc_id, actualizado_por)

    def get_historial(self, doc_id: int) -> list[dict]:
        """
        Devuelve todas las versiones históricas de un documento,
        ordenadas por snapshot_at descendente (más reciente primero).
        """
        rows = self.session.execute(text("""
            SELECT id, version, fecha_emision, descripcion_cambio,
                   url_documento, estado, snapshot_por, snapshot_at
            FROM compliance_documentos_historial
            WHERE documento_raiz_id = :doc_id
            ORDER BY snapshot_at DESC
        """), {"doc_id": doc_id}).mappings().fetchall()
        return [dict(r) for r in rows]

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

    def get_stats_grupo(self) -> dict:
        """
        Retorna métricas agregadas para el Dashboard de Gobernanza Corporativa.

        Estructura devuelta:
          {
            "por_empresa": [
                {"empresa": str, "total": int, "vigentes": int,
                 "pendientes": int, "vencidos": int},
                ...
            ],
            "por_empresa_carpeta": [
                {"empresa": str, "carpeta": str, "total": int, "vigentes": int},
                ...
            ],
            "gap_total": int,   # pendientes + vencidos (toda la corporación)
            "vigencia_pct": float,  # % vigentes sobre total no archivado
          }
        """
        _EMPRESAS_GRUPO = ("Holdings BPO", "PayCOP", "Adamo Services")

        por_empresa = self.session.execute(text("""
            SELECT
                COALESCE(empresa, 'Compartido') AS empresa,
                COUNT(*) FILTER (WHERE estado != 'Archivado')  AS total,
                COUNT(*) FILTER (WHERE estado = 'Vigente')     AS vigentes,
                COUNT(*) FILTER (WHERE estado = 'Pendiente')   AS pendientes,
                COUNT(*) FILTER (WHERE estado = 'Vencido')     AS vencidos
            FROM compliance_documentos
            WHERE empresa IN :empresas
            GROUP BY empresa
            ORDER BY empresa
        """), {"empresas": _EMPRESAS_GRUPO}).mappings().fetchall()

        por_empresa_carpeta = self.session.execute(text("""
            SELECT
                COALESCE(empresa, 'Compartido') AS empresa,
                carpeta,
                COUNT(*) FILTER (WHERE estado != 'Archivado')  AS total,
                COUNT(*) FILTER (WHERE estado = 'Vigente')     AS vigentes
            FROM compliance_documentos
            WHERE empresa IN :empresas
            GROUP BY empresa, carpeta
            ORDER BY empresa, carpeta
        """), {"empresas": _EMPRESAS_GRUPO}).mappings().fetchall()

        # Totales corporativos
        totales = self.session.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE estado != 'Archivado')        AS total,
                COUNT(*) FILTER (WHERE estado = 'Vigente')           AS vigentes,
                COUNT(*) FILTER (WHERE estado IN ('Pendiente','Vencido')) AS gap
            FROM compliance_documentos
        """)).mappings().fetchone()

        total_corp   = int(totales["total"])   if totales["total"]   else 0
        vigentes_corp = int(totales["vigentes"]) if totales["vigentes"] else 0
        gap_total    = int(totales["gap"])     if totales["gap"]     else 0
        vigencia_pct = round(vigentes_corp / total_corp * 100, 1) if total_corp else 0.0

        return {
            "por_empresa":         [dict(r) for r in por_empresa],
            "por_empresa_carpeta": [dict(r) for r in por_empresa_carpeta],
            "gap_total":           gap_total,
            "vigencia_pct":        vigencia_pct,
        }

