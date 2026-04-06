"""
db/repositories/partner_repo.py
Repositorio de Aliados — Capa de acceso a datos desacoplada de la UI.
Maneja la persistencia incluyendo métricas de gestión corporativa y operativa.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.models import AliadoCreate, AliadoUpdate


def _coerce_bools(payload: dict) -> dict:
    """
    Convierte valores booleanos de Python a enteros (True→1, False→0) 
    para asegurar compatibilidad con la estructura de la DB en Postgres.
    """
    # Lista exhaustiva de campos que deben guardarse como enteros
    bool_fields = [
        'es_pep', 'listas_verificadas', 'rut_recibido', 'camara_comercio_recibida',
        'estados_financieros_recibidos', 'formulario_vinculacion_recibido', 
        'contrato_firmado', 'poliza_recibida', 'lista_ofac_ok', 'lista_onu_ok',
        'lista_ue_ok', 'lista_local_ok',
        # Nuevas métricas operativas de la reestructuración
        'crypto_friendly', 'adult_friendly', 'permite_monetizacion', 'permite_dispersion'
    ]
    
    clean_payload = payload.copy()
    for field in bool_fields:
        if field in clean_payload:
            val = clean_payload[field]
            if isinstance(val, bool):
                clean_payload[field] = 1 if val else 0
    return clean_payload


class PartnerRepository:
    """CRUD y consultas de negocio sobre la tabla aliados."""

    def __init__(self, session: Session):
        self.session = session

    # ── Crear ─────────────────────────────────────────────
    def create(self, data: AliadoCreate, creado_por: int) -> int:
        """Inserta un nuevo aliado incluyendo métricas corporativas y retorna su ID."""
        payload = data.model_dump()
        
        # Ajuste de seguridad: Forzamos ID 1 si el sistema envía 0
        id_final = creado_por if creado_por > 0 else 1
        payload["creado_por"] = id_final
        payload["actualizado_por"] = id_final
        
        # Conversión de tipos de datos para Postgres
        payload = _coerce_bools(payload)

        cols = ", ".join(payload.keys())
        placeholders = ", ".join(f":{k}" for k in payload.keys())

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
        """Actualiza la información del aliado y sus métricas de gestión."""
        payload = data.model_dump(exclude_none=True)
        if not payload:
            return False

        id_final = actualizado_por if actualizado_por > 0 else 1
        payload["actualizado_por"] = id_final
        
        payload = _coerce_bools(payload)
        
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

    # ── Listar Enriquecida (Dashboard Principal) ──────────
    def get_lista_enriquecida(
        self,
        estado_pipeline: Optional[str] = None,
        nivel_riesgo: Optional[str] = None,
        estado_sarlaft: Optional[str] = None,
        tipo_aliado: Optional[str] = None,
        solo_pep: bool = False,
        search_text: Optional[str] = None,
    ) -> list[dict]:
        """Consulta que incluye los estados corporativos para la tabla de visualización."""
        query = """
            SELECT 
                id, nombre_razon_social, nit, tipo_aliado, estado_pipeline, 
                nivel_riesgo, puntaje_riesgo, estado_sarlaft,
                estado_hbpocorp, estado_adamo, estado_paycop,
                crypto_friendly, adult_friendly, fecha_proxima_revision
            FROM aliados 
            WHERE 1=1
        """
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
        if solo_pep:
            query += " AND es_pep = TRUE"
        if search_text:
            query += " AND (nombre_razon_social ILIKE :search OR nit ILIKE :search)"
            params["search"] = f"%{search_text}%"

        query += " ORDER BY updated_at DESC"
        rows = self.session.execute(text(query), params).mappings().all()
        return [dict(r) for r in rows]

    # ── Métricas para Dashboard ───────────────────────────
    def get_stats_relacion_grupo(self) -> dict:
        """Calcula estadísticas rápidas por empresa del grupo."""
        stats = {}
        for empresa in ['hbpocorp', 'adamo', 'paycop']:
            rows = self.session.execute(
                text(f"SELECT estado_{empresa}, COUNT(*) as total FROM aliados GROUP BY estado_{empresa}")
            ).mappings().all()
            stats[empresa] = {r[f"estado_{empresa}"]: r["total"] for r in rows}
        return stats

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