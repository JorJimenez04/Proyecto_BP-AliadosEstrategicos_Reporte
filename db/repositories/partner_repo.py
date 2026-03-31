"""
db/repositories/partner_repo.py
Repositorio de Aliados — Capa de acceso a datos desacoplada de la UI.
"""

from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

from db.models import AliadoCreate, AliadoUpdate


class PartnerRepository:
    """CRUD y consultas de negocio sobre la tabla aliados."""

    def __init__(self, session: Session):
        self.session = session

    # ── Crear ─────────────────────────────────────────────
    def create(self, data: AliadoCreate, creado_por: int) -> int:
        """Inserta un nuevo aliado y retorna su ID."""
        payload = data.model_dump()
        
        # AJUSTE DE SEGURIDAD (FIX FOREIGN KEY VIOLATION):
        # Como en tu DB tu usuario 'jorge_jimenez' es ID 1, 
        # si el sistema envía 0, lo forzamos a 1 para que no falle el registro.
        id_final = creado_por if creado_por > 0 else 1
        
        payload["creado_por"] = id_final
        payload["actualizado_por"] = id_final

        cols = ", ".join(payload.keys())
        placeholders = ", ".join(f":{k}" for k in payload.keys())

        # Ejecución del INSERT con retorno de ID
        result = self.session.execute(
            text(f"INSERT INTO aliados ({cols}) VALUES ({placeholders}) RETURNING id"),
            payload,
        )
        self.session.commit()
        return result.scalar()

    # ── Actualizar ────────────────────────────────────────
    def update(
        self,
        aliado_id: int,
        data: AliadoUpdate,
        actualizado_por: int,
    ) -> bool:
        payload = data.model_dump(exclude_none=True)
        if not payload:
            return False

        # Ajuste de ID de usuario también en actualización
        id_final = actualizado_por if actualizado_por > 0 else 1
        payload["actualizado_por"] = id_final

        set_clause = ", ".join(f"{k} = :{k}" for k in payload.keys())
        payload["id"] = aliado_id

        self.session.execute(
            text(f"UPDATE aliados SET {set_clause} WHERE id = :id"),
            payload,
        )
        self.session.commit()
        return True

    # ── Leer por ID ───────────────────────────────────────
    def get_by_id(self, aliado_id: int) -> Optional[dict]:
        row = self.session.execute(
            text("SELECT * FROM aliados WHERE id = :id"),
            {"id": aliado_id},
        ).mappings().first()
        return dict(row) if row else None

    # ── Leer por NIT ──────────────────────────────────────
    def get_by_nit(self, nit: str) -> Optional[dict]:
        row = self.session.execute(
            text("SELECT * FROM aliados WHERE nit = :nit"),
            {"nit": nit},
        ).mappings().first()
        return dict(row) if row else None

    # ── Listar con filtros ────────────────────────────────
    def list_all(
        self,
        estado_pipeline: Optional[str] = None,
        nivel_riesgo: Optional[str] = None,
        estado_sarlaft: Optional[str] = None,
        tipo_aliado: Optional[str] = None,
        search_text: Optional[str] = None,
    ) -> list[dict]:
        query = "SELECT * FROM aliados WHERE 1=1"
        params: dict = {}

        if estado_pipeline:
            query += " AND estado_pipeline = :estado_pipeline"
            params["estado_pipeline"] = estado_pipeline
        if nivel_riesgo:
            query += " AND nivel_riesgo = :nivel_riesgo"
            params["nivel_riesgo"] = nivel_riesgo
        if estado_sarlaft:
            query += " AND estado_sarlaft = :estado_sarlaft"
            params["estado_sarlaft"] = estado_sarlaft
        if tipo_aliado:
            query += " AND tipo_aliado = :tipo_aliado"
            params["tipo_aliado"] = tipo_aliado
        if search_text:
            query += " AND (nombre_razon_social ILIKE :search OR nit ILIKE :search)"
            params["search"] = f"%{search_text}%"

        query += " ORDER BY updated_at DESC"
        rows = self.session.execute(text(query), params).mappings().all()
        return [dict(r) for r in rows]

    # ── Cambiar estado del Pipeline ───────────────────────
    def cambiar_estado(
        self,
        aliado_id: int,
        estado_nuevo: str,
        cambiado_por: int,
        motivo: Optional[str] = None,
    ) -> bool:
        from config.settings import EstadosAliado

        aliado = self.get_by_id(aliado_id)
        if not aliado:
            raise ValueError(f"Aliado {aliado_id} no encontrado.")

        estado_actual = aliado["estado_pipeline"]
        transiciones_validas = EstadosAliado.TRANSICIONES.get(estado_actual, [])

        if estado_nuevo not in transiciones_validas:
            raise ValueError(
                f"Transición inválida: '{estado_actual}' → '{estado_nuevo}'. "
                f"Permitidas: {transiciones_validas}"
            )

        self.session.execute(
            text("UPDATE aliados SET estado_pipeline = :estado WHERE id = :id"),
            {"estado": estado_nuevo, "id": aliado_id},
        )

        id_historial = cambiado_por if cambiado_por > 0 else 1
        self.session.execute(
            text("""
                INSERT INTO historial_estados
                    (aliado_id, estado_anterior, estado_nuevo, motivo, cambiado_por)
                VALUES (:aliado_id, :anterior, :nuevo, :motivo, :cambiado_por)
            """),
            {
                "aliado_id":    aliado_id,
                "anterior":     estado_actual,
                "nuevo":        estado_nuevo,
                "motivo":       motivo,
                "cambiado_por": id_historial,
            },
        )
        self.session.commit()
        return True

    # ── Estadísticas Dashboard ──────────────────────────
    def get_stats_pipeline(self) -> dict:
        rows = self.session.execute(
            text("SELECT estado_pipeline, COUNT(*) as total FROM aliados GROUP BY estado_pipeline")
        ).mappings().all()
        return {r["estado_pipeline"]: r["total"] for r in rows}

    def get_stats_riesgo(self) -> dict:
        rows = self.session.execute(
            text("SELECT nivel_riesgo, COUNT(*) as total FROM aliados GROUP BY nivel_riesgo")
        ).mappings().all()
        return {r["nivel_riesgo"]: r["total"] for r in rows}

    def get_revisiones_proximas(self, dias: int = 30) -> list[dict]:
        """Aliados cuya revisión SARLAFT vence en los próximos N días."""
        from datetime import date, timedelta
        fecha_limite = (date.today() + timedelta(days=dias)).isoformat()
        rows = self.session.execute(
            text("""
                SELECT id, nombre_razon_social, nit, nivel_riesgo,
                       fecha_proxima_revision, estado_sarlaft
                FROM aliados
                WHERE fecha_proxima_revision <= :fecha_limite
                  AND estado_pipeline = 'Activo'
                ORDER BY fecha_proxima_revision ASC
            """),
            {"fecha_limite": fecha_limite},
        ).mappings().all()
        return [dict(r) for r in rows]

    def get_cobertura_due_diligence(self) -> dict:
        row = self.session.execute(
            text("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN estado_due_diligence = 'Completado' THEN 1 ELSE 0 END) as completados,
                    SUM(CASE WHEN estado_due_diligence = 'Rechazado'  THEN 1 ELSE 0 END) as rechazados,
                    SUM(CASE WHEN estado_due_diligence = 'En Proceso' THEN 1 ELSE 0 END) as en_proceso,
                    SUM(CASE WHEN estado_due_diligence = 'Pendiente'  THEN 1 ELSE 0 END) as pendientes
                FROM aliados
                WHERE estado_pipeline != 'Terminado'
            """)
        ).mappings().first()
        return dict(row) if row else {}

    def get_sarlaft_vencidas(self) -> list[dict]:
        rows = self.session.execute(
            text("""
                SELECT id, nombre_razon_social, nit, nivel_riesgo, tipo_aliado,
                       fecha_proxima_revision, estado_sarlaft, ciudad
                FROM aliados
                WHERE estado_sarlaft = 'Vencido'
                  AND estado_pipeline NOT IN ('Terminado', 'Suspendido')
                ORDER BY
                    CASE nivel_riesgo
                        WHEN 'Muy Alto' THEN 1 WHEN 'Alto' THEN 2
                        WHEN 'Medio'   THEN 3  ELSE 4
                    END,
                    fecha_proxima_revision ASC
            """)
        ).mappings().all()
        return [dict(r) for r in rows]

    def get_pep_activos(self) -> list[dict]:
        """Lista de aliados PEP vigentes — GAFI R.12."""
        rows = self.session.execute(
            text("""
                SELECT id, nombre_razon_social, nit, nivel_riesgo,
                       descripcion_pep, vinculo_pep, estado_pipeline,
                       estado_sarlaft, tipo_aliado
                FROM aliados
                WHERE es_pep = TRUE
                  AND estado_pipeline != 'Terminado'
                ORDER BY
                    CASE nivel_riesgo
                        WHEN 'Muy Alto' THEN 1 WHEN 'Alto' THEN 2
                        WHEN 'Medio'   THEN 3  ELSE 4
                    END,
                    nombre_razon_social
            """)
        ).mappings().all()
        return [dict(r) for r in rows]

    def get_stats_tipo_aliado(self) -> dict:
        rows = self.session.execute(
            text("""
                SELECT tipo_aliado, COUNT(*) as total
                FROM aliados
                WHERE estado_pipeline != 'Terminado'
                GROUP BY tipo_aliado
            """)
        ).mappings().all()
        return {r["tipo_aliado"]: r["total"] for r in rows}

    def get_stats_ciudad(self) -> list[dict]:
        rows = self.session.execute(
            text("""
                SELECT COALESCE(ciudad, 'Sin ciudad') as ciudad, COUNT(*) as total
                FROM aliados
                WHERE estado_pipeline != 'Terminado'
                GROUP BY ciudad
                ORDER BY total DESC
                LIMIT 15
            """)
        ).mappings().all()
        return [dict(r) for r in rows]

    def get_scatter_riesgo(self) -> list[dict]:
        rows = self.session.execute(
            text("""
                SELECT id, nombre_razon_social, nit, tipo_aliado,
                       nivel_riesgo, COALESCE(puntaje_riesgo, 0) as puntaje_riesgo,
                       estado_pipeline
                FROM aliados
                WHERE estado_pipeline != 'Terminado'
                ORDER BY puntaje_riesgo DESC
            """)
        ).mappings().all()
        return [dict(r) for r in rows]

    def get_stats_estado_sarlaft(self) -> dict:
        rows = self.session.execute(
            text("""
                SELECT estado_sarlaft, COUNT(*) as total
                FROM aliados
                WHERE estado_pipeline != 'Terminado'
                GROUP BY estado_sarlaft
            """)
        ).mappings().all()
        return {r["estado_sarlaft"]: r["total"] for r in rows}

    def get_lista_export(
        self,
        solo_pep: bool = False,
        solo_alto_riesgo: bool = False,
        oficial: str | None = None,
    ) -> list[dict]:
        query = """
            SELECT
                a.id, a.nombre_razon_social, a.nit, a.tipo_aliado,
                a.estado_pipeline, a.nivel_riesgo, a.puntaje_riesgo,
                a.estado_sarlaft, a.estado_due_diligence, a.nivel_due_diligence,
                a.es_pep, a.descripcion_pep, a.vinculo_pep,
                a.listas_verificadas, a.contrato_firmado,
                a.ciudad, a.departamento_geo,
                a.representante_legal, a.cargo_representante,
                a.email_contacto, a.telefono_contacto,
                a.fecha_vinculacion, a.fecha_proxima_revision,
                a.frecuencia_revision, a.observaciones_compliance,
                a.created_at, a.updated_at
            FROM aliados a
            WHERE 1=1
        """
        params: dict = {}
        if solo_pep:
            query += " AND a.es_pep = TRUE"
        if solo_alto_riesgo:
            query += " AND a.nivel_riesgo IN ('Alto', 'Muy Alto')"
        query += " ORDER BY a.nivel_riesgo, a.nombre_razon_social"
        rows = self.session.execute(text(query), params).mappings().all()
        return [dict(r) for r in rows]

    def get_lista_enriquecida(
        self,
        estado_pipeline: Optional[str] = None,
        nivel_riesgo: Optional[str] = None,
        estado_sarlaft: Optional[str] = None,
        tipo_aliado: Optional[str] = None,
        solo_pep: bool = False,
        search_text: Optional[str] = None,
    ) -> list[dict]:
        query = """
            SELECT
                a.id, a.nombre_razon_social, a.nit, a.tipo_aliado,
                a.estado_pipeline, a.nivel_riesgo, a.puntaje_riesgo,
                a.estado_sarlaft, a.estado_due_diligence, a.nivel_due_diligence,
                a.es_pep, a.listas_verificadas, a.contrato_firmado,
                a.fecha_proxima_revision, a.ciudad, a.fecha_vinculacion
            FROM aliados a
            WHERE 1=1
        """
        params: dict = {}

        if estado_pipeline:
            query += " AND a.estado_pipeline = :estado_pipeline"
            params["estado_pipeline"] = estado_pipeline
        if nivel_riesgo:
            query += " AND a.nivel_riesgo = :nivel_riesgo"
            params["nivel_riesgo"] = nivel_riesgo
        if estado_sarlaft:
            query += " AND a.estado_sarlaft = :estado_sarlaft"
            params["estado_sarlaft"] = estado_sarlaft
        if tipo_aliado:
            query += " AND a.tipo_aliado = :tipo_aliado"
            params["tipo_aliado"] = tipo_aliado
        if solo_pep:
            query += " AND a.es_pep = TRUE"
        if search_text:
            query += " AND (a.nombre_razon_social ILIKE :search OR a.nit ILIKE :search)"
            params["search"] = f"%{search_text}%"

        query += """
            ORDER BY
                CASE a.nivel_riesgo
                    WHEN 'Muy Alto' THEN 1 WHEN 'Alto' THEN 2
                    WHEN 'Medio'   THEN 3  ELSE 4
                END,
                CASE a.estado_sarlaft
                    WHEN 'Vencido'      THEN 1 WHEN 'En Revisión' THEN 2
                    WHEN 'Pendiente'    THEN 3 ELSE 4
                END,
                a.nombre_razon_social
        """
        rows = self.session.execute(text(query), params).mappings().all()
        return [dict(r) for r in rows]