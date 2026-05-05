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

    def ensure_seed(self) -> int:
        """
        Seed de documentos base DESACTIVADO intencionalmente.
        La carga de documentos reales se realiza de forma manual desde la UI.
        Retorna 0 siempre sin modificar la tabla.
        """
        logger.info("[Compliance] ensure_seed: seed desactivado — carga manual requerida.")
        return 0

        # ── SEED DESACTIVADO ── no borrar este bloque, sirve como referencia ──
        # Si necesitas restaurar el seed de prueba, elimina el `return 0` de arriba.
        count = self.session.execute(  # type: ignore[unreachable]
            text("SELECT COUNT(*) FROM compliance_documentos")
        ).scalar()
        if count and count > 0:
            logger.info("[Compliance] ensure_seed: tabla ya tiene %d filas, skip.", count)
            return 0

        _SEED = [
            ("Politicas",    "POL-001", "Politica AML-SARO v1.0",                       "DOCX", "1.0", "Vigente",  "2024-06-01", "Version editable vigente"),
            ("Politicas",    "POL-001", "Politica AML-SARO Firmada",                     "PDF",  "1.0", "Vigente",  "2024-06-01", "Documento firmado"),
            ("Politicas",    "POL-002", "Politica Manejo de Informacion v1.0",            "DOCX", "1.0", "Vigente",  "2024-06-01", "Version editable"),
            ("Politicas",    "POL-002", "Politica Manejo Informacion Firmada",            "PDF",  "1.0", "Vigente",  "2024-06-01", "Firmada"),
            ("Politicas",    "POL-003", "Politica PEPs v1.0",                             "DOCX", "1.0", "Vigente",  "2024-06-01", "Version editable"),
            ("Politicas",    "POL-003", "Politica PEPs Firmada",                          "PDF",  "1.0", "Vigente",  "2024-06-01", "Firmada"),
            ("Manuales",     "MAN-001", "Manual SAGRILAFT Borrador",                      "DOCX", "1.0", "Vigente",  "2024-06-01", "Borrador editable"),
            ("Manuales",     "MAN-001", "Manual SAGRILAFT Firmado",                       "PDF",  "1.0", "Vigente",  "2024-06-01", "Version firmada"),
            ("Manuales",     "MAN-002", "Manual PTEE Cumplimiento Borrador",              "DOCX", "1.0", "Vigente",  "2024-06-01", "Borrador editable"),
            ("Manuales",     "MAN-002", "Manual PTEE Firmado",                            "PDF",  "1.0", "Vigente",  "2024-06-01", "Firmado"),
            ("Manuales",     "MAN-003", "Manual Procedimientos de Pagos",                 "DOCX", "1.0", "Pendiente","2024-03-01", "Requiere revision"),
            ("Manuales",     "MAN-004", "Proceso Compliance v1.0",                        "DOCX", "1.0", "Vigente",  "2024-06-01", None),
            ("Manuales",     "MAN-005", "ROS Interno",                                    "DOCX", "1.0", "Vigente",  "2024-06-01", None),
            ("Manuales",     "MAN-006", "Flujo Compliance Firmado",                       "PDF",  "1.0", "Vigente",  "2024-06-01", None),
            ("Onboarding",   "ONB-001", "Onboarding Procedure EN",                        "PDF",  "1.07","Vigente",  "2024-06-01", "Version en ingles"),
            ("Onboarding",   "ONB-002", "Proceso Vinculacion ES",                         "PDF",  "1.07","Vigente",  "2024-06-01", "Version en espanol"),
            ("Onboarding",   "ONB-003", "Flujo Nuevos Clientes Firmado",                  "PDF",  "1.0", "Vigente",  "2024-06-01", None),
            ("Onboarding",   "ONB-004", "Alertas Monitoreo Transacciones",                "DOCX", "1.0", "Vigente",  "2024-06-01", None),
            ("Onboarding",   "ONB-005", "Documentos Soporte Compliance Request",          "DOCX", "1.0", "Vigente",  "2024-06-01", "Checklist"),
            ("Procesos y Procedimientos", "ETI-001", "Codigo de Etica y Conducta Borrador",            "DOCX", "1.0", "Vigente",  "2024-06-01", None),
            ("Procesos y Procedimientos", "ETI-001", "Codigo de Etica y Conducta Firmado",             "PDF",  "1.0", "Vigente",  "2024-06-01", "Firmado"),
            ("Procesos y Procedimientos", "ETI-002", "Programa Transparencia Etica Publica 2024",      "DOCX", "2024","Vigente",  "2024-01-01", "PTEE anual"),
            ("Procesos y Procedimientos", "ETI-003", "PTEE Firmado",                                   "PDF",  "2024","Vigente",  "2024-01-01", "Firmado"),
            ("Governanza",   "RIE-001", "Matriz de Riesgos 2022",                         "XLSX", "2022","Vencido",  "2022-06-01", "Actualizar a version 2025"),
            ("Governanza",   "RIE-002", "ADAMO RISK Documento",                           "DOCX", "1.0", "Vigente",  "2025-01-01", None),
            ("Governanza",   "RIE-003", "Politica AML-SARO v1.6 (Adamo Risk)",            "DOCX", "1.6", "Pendiente","2024-06-01", "Version anotada"),
            ("Governanza",   "RIE-004", "Preguntas Kick Off Adamo Risk",                  "DOCX", "1.0", "Vigente",  "2025-01-01", None),
            ("Governanza",   "RIE-005", "CERL ADAMO Enero 2025",                          "PDF",  "2025","Vigente",  "2025-01-01", None),
            ("Empresariales","EMP-001", "Certificado Existencia y Rep. Legal Ene 2026",   "PDF",  "2026","Vigente",  "2026-01-01", "Vigente"),
            ("Empresariales","EMP-002", "Certificacion Composicion Accionaria Ene 2026",  "PDF",  "2026","Vigente",  "2026-01-01", "Vigente"),
            ("Empresariales","EMP-003", "Estados Financieros 2024-2023",                  "PDF",  "2024","Vigente",  "2024-12-01", None),
            ("Empresariales","EMP-004", "Certificacion EEFF 2024",                        "PDF",  "2024","Vigente",  "2024-12-01", None),
            ("Empresariales","EMP-005", "RUT ADAMO",                                      "PDF",  "2024","Vigente",  "2024-06-01", None),
            ("Empresariales","EMP-006", "Contrato Confidencialidad Paxum",                "DOCX", "1.0", "Pendiente","2023-06-01", "Revisar vencimiento"),
            ("Capacitacion", "CAP-001", "Training Schedule",                              "DOCX", "2024","Vigente",  "2024-01-01", None),
            ("Capacitacion", "CAP-002", "Ejemplo Certificado Entrenamiento",              "PDF",  "1.0", "Vigente",  "2024-06-01", "Plantilla"),
            ("Capacitacion", "CAP-003", "Estructura Depto Cumplimiento",                  "DOCX", "1.0", "Vigente",  "2024-06-01", None),
            ("Capacitacion", "CAP-003", "Estructura Depto Cumplimiento Publicada",        "PDF",  "1.0", "Vigente",  "2024-06-01", "Publicada"),
            ("Capacitacion", "CAP-004", "Template Corporativo ADAMO",                     "DOCX", "1.0", "Vigente",  "2024-06-01", "Plantilla base"),
        ]

        inserted = 0
        for carpeta, codigo, nombre, fmt, ver, estado, fecha, desc in _SEED:
            self.session.execute(text("""
                INSERT INTO compliance_documentos
                    (carpeta, codigo, nombre, formato, version, estado,
                     fecha_emision, descripcion, creado_por)
                VALUES
                    (:carpeta, :codigo, :nombre, :formato, :version, :estado,
                     :fecha_emision, :descripcion, 'sistema')
            """), {
                "carpeta": carpeta, "codigo": codigo, "nombre": nombre,
                "formato": fmt, "version": ver, "estado": estado,
                "fecha_emision": fecha, "descripcion": desc,
            })
            inserted += 1
        self.session.commit()
        logger.info("[Compliance] ensure_seed: %d documentos insertados.", inserted)
        return inserted

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
                empresa          = :empresa,
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

    def archivar(self, doc_id: int, actualizado_por: str) -> None:
        """Soft delete: cambia estado a Archivado."""
        self.session.execute(text("""
            UPDATE compliance_documentos
            SET estado = 'Archivado', actualizado_por = :actualizado_por
            WHERE id = :id
        """), {"id": doc_id, "actualizado_por": actualizado_por})
        self.session.commit()
        logger.info("[Compliance] Doc id=%s archivado por %s", doc_id, actualizado_por)
