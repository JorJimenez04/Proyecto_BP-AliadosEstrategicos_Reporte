"""
db/repositories/partner_repo.py
Repositorio de Aliados — Capa de acceso a datos desacoplada de la UI.
Maneja la persistencia incluyendo métricas de gestión corporativa y operativa.
"""

from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.models import AliadoCreate, AliadoUpdate


# ─────────────────────────────────────────────────────────────
# Scoring de Riesgo Automático
# Rubrica SARLAFT-compatible basada en capacidades operativas,
# estado documental y factores de exposición.
# ─────────────────────────────────────────────────────────────

_RISK_WEIGHTS: dict[str, int] = {
    "es_pep":                       25,   # Persona Expuesta Políticamente
    "crypto_friendly":              20,   # Actividad cripto = riesgo regulatorio alto
    "adult_friendly":               15,   # Industria adulta = AML exposure
    "crypto_and_monetizacion":      10,   # Combinación cripto + monetización = exposición máxima
    "listas_sin_verificar":         15,   # No se han chequeado listas restrictivas
    "lista_ofac_pendiente":         10,   # OFAC no limpia
    "due_diligence_rechazado":      30,   # Rechazo explícito en DD
    "sarlaft_vencido":              20,   # Revisión SARLAFT expirada
    "sarlaft_pendiente":            10,   # Sin revisión iniciada
    "sin_contrato":                  5,   # Contrato no firmado
    "sin_rut":                       5,   # RUT no recibido
    "sin_camara_comercio":           5,   # Cámara de comercio ausente
    "sin_due_diligence":            10,   # DD nunca iniciado
}

_NIVEL_POR_SCORE: list[tuple[int, str]] = [
    (25,  "Bajo"),
    (50,  "Medio"),
    (75,  "Alto"),
    (100, "Muy Alto"),
]


def calcular_puntaje_riesgo(data: dict) -> tuple[float, str]:
    """
    Calcula el puntaje de riesgo (0-100) y el nivel correspondiente
    a partir de los datos del aliado.

    Retorna (puntaje: float, nivel: str)
    """
    score = 0

    if data.get("es_pep"):
        score += _RISK_WEIGHTS["es_pep"]
    if data.get("crypto_friendly"):
        score += _RISK_WEIGHTS["crypto_friendly"]
    if data.get("adult_friendly"):
        score += _RISK_WEIGHTS["adult_friendly"]
    if data.get("crypto_friendly") and data.get("permite_monetizacion"):
        score += _RISK_WEIGHTS["crypto_and_monetizacion"]

    if not data.get("listas_verificadas", False):
        score += _RISK_WEIGHTS["listas_sin_verificar"]
    elif not data.get("lista_ofac_ok", True):
        score += _RISK_WEIGHTS["lista_ofac_pendiente"]

    estado_dd = data.get("estado_due_diligence", "Pendiente")
    if estado_dd == "Rechazado":
        score += _RISK_WEIGHTS["due_diligence_rechazado"]
    elif estado_dd == "Pendiente":
        score += _RISK_WEIGHTS["sin_due_diligence"]

    estado_sarlaft = data.get("estado_sarlaft", "Pendiente")
    if estado_sarlaft == "Vencido":
        score += _RISK_WEIGHTS["sarlaft_vencido"]
    elif estado_sarlaft == "Pendiente":
        score += _RISK_WEIGHTS["sarlaft_pendiente"]

    if not data.get("contrato_firmado", False):
        score += _RISK_WEIGHTS["sin_contrato"]
    if not data.get("rut_recibido", False):
        score += _RISK_WEIGHTS["sin_rut"]
    if not data.get("camara_comercio_recibida", False):
        score += _RISK_WEIGHTS["sin_camara_comercio"]

    score = min(score, 100)

    nivel = "Muy Alto"
    for umbral, nombre in _NIVEL_POR_SCORE:
        if score <= umbral:
            nivel = nombre
            break

    return float(score), nivel


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

        # Recalcular score de riesgo automáticamente al crear
        score, nivel = calcular_puntaje_riesgo(payload)
        payload["puntaje_riesgo"] = score
        # Solo escalar nivel, nunca bajar el que el usuario seleccionó
        _escala = ["Bajo", "Medio", "Alto", "Muy Alto"]
        if _escala.index(nivel) > _escala.index(payload.get("nivel_riesgo", "Medio")):
            payload["nivel_riesgo"] = nivel

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

    # ── Alertas SARLAFT ───────────────────────────────────
    def get_sarlaft_vencidas(self) -> list[dict]:
        """Aliados con estado_sarlaft='Vencido' o fecha_proxima_revision pasada."""
        rows = self.session.execute(
            text("""
                SELECT id, nombre_razon_social, nit, nivel_riesgo, puntaje_riesgo,
                       estado_sarlaft, fecha_proxima_revision, estado_pipeline
                FROM aliados
                WHERE estado_sarlaft = 'Vencido'
                   OR (fecha_proxima_revision IS NOT NULL AND fecha_proxima_revision < CURRENT_DATE)
                ORDER BY fecha_proxima_revision ASC NULLS LAST
            """)
        ).mappings().all()
        return [dict(r) for r in rows]

    def get_revisiones_proximas(self, dias: int = 30) -> list[dict]:
        """Aliados cuya próxima revisión SARLAFT vence en los próximos `dias` días."""
        rows = self.session.execute(
            text("""
                SELECT id, nombre_razon_social, nit, nivel_riesgo, puntaje_riesgo,
                       estado_sarlaft, fecha_proxima_revision
                FROM aliados
                WHERE fecha_proxima_revision BETWEEN CURRENT_DATE AND (CURRENT_DATE + :dias * INTERVAL '1 day')
                  AND estado_sarlaft != 'Vencido'
                ORDER BY fecha_proxima_revision ASC
            """),
            {"dias": dias},
        ).mappings().all()
        return [dict(r) for r in rows]

    # ── Recalcular Score de Riesgo en DB ─────────────────
    def recalcular_puntaje(self, aliado_id: int, actualizado_por: int) -> tuple[float, str]:
        """
        Recalcula el puntaje y nivel de riesgo de un aliado existente
        usando los datos actuales en DB y persiste el resultado.
        """
        row = self.get_by_id(aliado_id)
        if not row:
            return 0.0, "Medio"
        score, nivel = calcular_puntaje_riesgo(row)
        id_final = actualizado_por if actualizado_por > 0 else 1
        self.session.execute(
            text("""
                UPDATE aliados
                SET puntaje_riesgo = :score, nivel_riesgo = :nivel,
                    actualizado_por = :uid
                WHERE id = :id
            """),
            {"score": score, "nivel": nivel, "uid": id_final, "id": aliado_id},
        )
        self.session.commit()
        return score, nivel

    # ── Comparativa de Salud Corporativa ─────────────────
    def get_salud_grupo(self) -> dict:
        """
        Calcula métricas de 'salud de relación' por empresa del grupo.

        Retorna un dict con estructura:
        {
          "hbpocorp": {"activos": N, "inactivos": N, "sin_relacion": N, "pct_activos": float},
          "adamo":    {...},
          "paycop":   {...},
        }
        """
        resultado = {}
        for empresa in ("hbpocorp", "adamo", "paycop"):
            col = f"estado_{empresa}"
            rows = self.session.execute(
                text(f"SELECT {col} as estado, COUNT(*) as total FROM aliados GROUP BY {col}")
            ).mappings().all()
            conteos = {r["estado"]: int(r["total"]) for r in rows}
            activos = conteos.get("Activo", 0)
            inactivos = conteos.get("Inactivo", 0)
            sin_rel = conteos.get("Sin relación", 0)
            total_rel = activos + inactivos
            resultado[empresa] = {
                "activos":      activos,
                "inactivos":    inactivos,
                "sin_relacion": sin_rel,
                "pct_activos":  round(activos / total_rel * 100, 1) if total_rel else 0.0,
            }
        return resultado