"""
db/repositories/crypto_repo.py
Repositorio del módulo Cripto Compliance (VASP Monitor).
Gestiona el registro, actualización y consulta de wallets
monitoreadas a través de Global Ledger.
"""

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from db.models import WalletMonitorCreate, CryptoClienteCreate

logger = logging.getLogger(__name__)

# Mensaje canónico para tabla no inicializada
_MSG_TABLA_NO_INIT = (
    "Advertencia: Tabla de monitoreo cripto no inicializada. "
    "Aplica la migración 019_create_crypto_compliance_schema.sql en Railway."
)

_STATS_VACIAS_CLIENTES: dict = {
    "_tabla_no_existe": True,
    "total": 0,
}

_STATS_VACIAS: dict = {
    "total_wallets": 0,
    "total_exposure_usd": 0.0,
    "atencion_prioritaria": 0,
    "nivel_critico": 0,
    "nivel_alto": 0,
    "nivel_medio": 0,
    "nivel_bajo": 0,
    "sin_datos": 0,
    "por_blockchain": [],
    "_tabla_no_existe": True,
}

# Labels que activan alerta prioritaria (independiente del score)
_LABELS_CRITICOS: frozenset[str] = frozenset({
    "Sanctioned Exchange",
    "OFAC Sanctioned",
    "Darknet Market",
    "Ransomware",
    "Scam",
    "Terrorism Financing",
    "Child Abuse Material",
    "Mixer",
})

# Mapeo score → nivel de riesgo (umbral inferior inclusive)
_SCORE_A_NIVEL: list[tuple[int, str]] = [
    (70, "Bajo"),
    (40, "Medio"),
    (20, "Alto"),
    (0,  "Crítico"),
]


def score_a_nivel_riesgo(score: Optional[int]) -> str:
    """Convierte el score GL (0-100) al nivel de riesgo canónico."""
    if score is None:
        return "Sin Datos"
    for umbral, nivel in _SCORE_A_NIVEL:
        if score >= umbral:
            return nivel
    return "Crítico"


class CryptoRepository:
    """Acceso a las tablas crypto_clientes y crypto_monitoreo."""

    def __init__(self, session: Session):
        self.session = session

    # ── CRUD Clientes Corporativos ────────────────────────────
    def crear_cliente(self, data: "CryptoClienteCreate") -> dict:
        """Inserta un nuevo cliente corporativo. Retorna el registro creado."""
        row = self.session.execute(text("""
            INSERT INTO crypto_clientes
                (razon_social, nit, representante_legal, correo_corporativo,
                 telefono, direccion, fecha_onboarding, notas, creado_por)
            VALUES
                (:razon_social, :nit, :representante_legal, :correo_corporativo,
                 :telefono, :direccion, :fecha_onboarding, :notas, :creado_por)
            RETURNING *
        """), {
            "razon_social":        data.razon_social.strip(),
            "nit":                 data.nit.strip() if data.nit else None,
            "representante_legal": data.representante_legal,
            "correo_corporativo":  data.correo_corporativo,
            "telefono":            data.telefono,
            "direccion":           data.direccion,
            "fecha_onboarding":    data.fecha_onboarding.isoformat() if data.fecha_onboarding else None,
            "notas":               data.notas,
            "creado_por":          data.creado_por,
        }).mappings().first()
        self.session.commit()
        logger.info("crypto_cliente.crear: %s", data.razon_social)
        return dict(row)

    def get_clientes(self, search: str = "") -> list[dict]:
        """Lista todos los clientes. Con search filtra por razon_social o NIT."""
        try:
            tabla_existe = self.session.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name   = 'crypto_clientes'
                )
            """)).scalar()
            if not tabla_existe:
                return []

            # Verificar si la columna FK ya existe en crypto_monitoreo
            col_fk_existe = self.session.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name   = 'crypto_monitoreo'
                      AND column_name  = 'crypto_cliente_id'
                )
            """)).scalar()

            if col_fk_existe:
                # Query completa con conteo de wallets y exposición
                if search:
                    rows = self.session.execute(text("""
                        SELECT cc.*,
                               COUNT(cm.id) AS total_wallets,
                               COALESCE(SUM(cm.total_exposure), 0) AS exposure_total
                        FROM crypto_clientes cc
                        LEFT JOIN crypto_monitoreo cm ON cm.crypto_cliente_id = cc.id
                        WHERE cc.razon_social ILIKE :s OR cc.nit ILIKE :s
                        GROUP BY cc.id
                        ORDER BY cc.razon_social
                    """), {"s": f"%{search}%"}).mappings().all()
                else:
                    rows = self.session.execute(text("""
                        SELECT cc.*,
                               COUNT(cm.id) AS total_wallets,
                               COALESCE(SUM(cm.total_exposure), 0) AS exposure_total
                        FROM crypto_clientes cc
                        LEFT JOIN crypto_monitoreo cm ON cm.crypto_cliente_id = cc.id
                        GROUP BY cc.id
                        ORDER BY cc.razon_social
                    """)).mappings().all()
            else:
                # Fallback: query simple sin JOIN (columna FK aún no existe)
                logger.warning("get_clientes: columna crypto_cliente_id no existe, usando query simple")
                if search:
                    rows = self.session.execute(text("""
                        SELECT *, 0 AS total_wallets, 0 AS exposure_total
                        FROM crypto_clientes
                        WHERE razon_social ILIKE :s OR nit ILIKE :s
                        ORDER BY razon_social
                    """), {"s": f"%{search}%"}).mappings().all()
                else:
                    rows = self.session.execute(text("""
                        SELECT *, 0 AS total_wallets, 0 AS exposure_total
                        FROM crypto_clientes
                        ORDER BY razon_social
                    """)).mappings().all()

            return [dict(r) for r in rows]
        except Exception as exc:
            self.session.rollback()
            logger.warning("get_clientes error: %s", exc)
            return []

    def get_cliente_by_id(self, cliente_id: int) -> Optional[dict]:
        try:
            row = self.session.execute(
                text("SELECT * FROM crypto_clientes WHERE id = :id"),
                {"id": cliente_id},
            ).mappings().first()
            return dict(row) if row else None
        except Exception:
            self.session.rollback()
            return None

    def get_wallets_by_cliente(self, cliente_id: int) -> list[dict]:
        """Devuelve todas las wallets vinculadas a un cliente corporativo."""
        try:
            rows = self.session.execute(text("""
                SELECT id, wallet_address, blockchain,
                       crypto_cliente_id, client_id, client_nombre,
                       gl_score, riesgo_nivel, risk_labels,
                       total_exposure, exposure_currency,
                       pdf_report_url, last_report_date,
                       registrado_por, notas, created_at, updated_at
                FROM crypto_monitoreo
                WHERE crypto_cliente_id = :cid
                ORDER BY gl_score ASC NULLS LAST
            """), {"cid": cliente_id}).mappings().all()
            return [dict(r) for r in rows]
        except Exception as exc:
            self.session.rollback()
            logger.warning("get_wallets_by_cliente error: %s", exc)
            return []

    def get_stats_by_cliente(self, cliente_id: int) -> dict:
        """Exposure total y distribución de riesgo para un cliente."""
        try:
            row = self.session.execute(text("""
                SELECT
                    COUNT(*)                                              AS total_wallets,
                    COALESCE(SUM(total_exposure), 0)                     AS exposure_total,
                    COUNT(*) FILTER (WHERE riesgo_nivel = 'Critico')     AS nivel_critico,
                    COUNT(*) FILTER (WHERE riesgo_nivel = 'Alto')        AS nivel_alto,
                    COUNT(*) FILTER (WHERE riesgo_nivel = 'Medio')       AS nivel_medio,
                    COUNT(*) FILTER (WHERE riesgo_nivel = 'Bajo')        AS nivel_bajo,
                    COUNT(*) FILTER (WHERE riesgo_nivel = 'Sin Datos')   AS sin_datos
                FROM crypto_monitoreo
                WHERE crypto_cliente_id = :cid
            """), {"cid": cliente_id}).mappings().first()
            return dict(row) if row else {}
        except Exception:
            self.session.rollback()
            return {}

    # ── Upsert (registro desde JSON de Global Ledger) ─────────
    def upsert_from_gl(self, data: WalletMonitorCreate) -> dict:
        """
        Crea o actualiza una wallet a partir de la respuesta de Global Ledger.
        Retorna el registro resultante como dict.
        """
        # Calcular nivel de riesgo automáticamente si no viene explícito
        nivel = data.riesgo_nivel
        if nivel == "Sin Datos" and data.gl_score is not None:
            nivel = score_a_nivel_riesgo(data.gl_score)

        risk_labels_json = json.dumps(
            [lbl.model_dump() for lbl in data.risk_labels]
        )
        last_report = data.last_report_date.isoformat() if data.last_report_date else None

        row = self.session.execute(text("""
            INSERT INTO crypto_monitoreo (
                wallet_address, blockchain,
                crypto_cliente_id, client_id, client_nombre,
                gl_score, riesgo_nivel, risk_labels,
                total_exposure, exposure_currency,
                pdf_report_url, last_report_date,
                registrado_por, notas
            ) VALUES (
                :wallet_address, :blockchain,
                :crypto_cliente_id, :client_id, :client_nombre,
                :gl_score, :riesgo_nivel, :risk_labels::jsonb,
                :total_exposure, :exposure_currency,
                :pdf_report_url, :last_report_date,
                :registrado_por, :notas
            )
            ON CONFLICT (wallet_address) DO UPDATE SET
                blockchain          = EXCLUDED.blockchain,
                crypto_cliente_id   = COALESCE(EXCLUDED.crypto_cliente_id, crypto_monitoreo.crypto_cliente_id),
                client_id           = COALESCE(EXCLUDED.client_id, crypto_monitoreo.client_id),
                client_nombre       = COALESCE(EXCLUDED.client_nombre, crypto_monitoreo.client_nombre),
                gl_score            = EXCLUDED.gl_score,
                riesgo_nivel        = EXCLUDED.riesgo_nivel,
                risk_labels         = EXCLUDED.risk_labels,
                total_exposure      = EXCLUDED.total_exposure,
                exposure_currency   = EXCLUDED.exposure_currency,
                pdf_report_url      = COALESCE(EXCLUDED.pdf_report_url, crypto_monitoreo.pdf_report_url),
                last_report_date    = EXCLUDED.last_report_date,
                registrado_por      = EXCLUDED.registrado_por,
                notas               = COALESCE(EXCLUDED.notas, crypto_monitoreo.notas),
                updated_at          = NOW()
            RETURNING *
        """), {
            "wallet_address":    data.wallet_address,
            "blockchain":        data.blockchain,
            "crypto_cliente_id": data.crypto_cliente_id,
            "client_id":         data.client_id,
            "client_nombre":     data.client_nombre,
            "gl_score":          data.gl_score,
            "riesgo_nivel":      nivel,
            "risk_labels":       risk_labels_json,
            "total_exposure":    data.total_exposure,
            "exposure_currency": data.exposure_currency,
            "pdf_report_url":    data.pdf_report_url,
            "last_report_date":  last_report,
            "registrado_por":    data.registrado_por,
            "notas":             data.notas,
        }).mappings().first()

        self.session.commit()
        logger.info("crypto.upsert: wallet=%s nivel=%s score=%s",
                    data.wallet_address, nivel, data.gl_score)
        return dict(row)

    # ── Lectura individual ────────────────────────────────────
    def get_by_address(self, wallet_address: str) -> Optional[dict]:
        try:
            row = self.session.execute(
                text("SELECT * FROM crypto_monitoreo WHERE wallet_address = :addr"),
                {"addr": wallet_address.strip()},
            ).mappings().first()
            return dict(row) if row else None
        except ProgrammingError:
            self.session.rollback()
            logger.warning(_MSG_TABLA_NO_INIT)
            return None

    def get_by_id(self, wallet_id: int) -> Optional[dict]:
        try:
            row = self.session.execute(
                text("SELECT * FROM crypto_monitoreo WHERE id = :id"),
                {"id": wallet_id},
            ).mappings().first()
            return dict(row) if row else None
        except ProgrammingError:
            self.session.rollback()
            logger.warning(_MSG_TABLA_NO_INIT)
            return None

    # ── Listado con filtros ───────────────────────────────────
    def get_lista(
        self,
        client_id: Optional[int] = None,
        riesgo_nivel: Optional[str] = None,
        blockchain: Optional[str] = None,
        solo_criticos: bool = False,
        search_text: Optional[str] = None,
    ) -> list[dict]:
        """
        Devuelve la lista de wallets con filtros opcionales.
        solo_criticos = True → score < 30 O contiene label sancionada.
        Retorna [] si la tabla aún no existe (migración pendiente).
        """
        # Columnas en el SELECT deben coincidir 1:1 con el esquema de crypto_monitoreo
        # y con los campos que consume la UI (client_nombre, exposure_currency incluidos).
        query = """
            SELECT id, wallet_address, blockchain,
                   client_id, client_nombre,
                   gl_score, riesgo_nivel, risk_labels,
                   total_exposure, exposure_currency,
                   pdf_report_url, last_report_date,
                   registrado_por, notas, created_at, updated_at
            FROM crypto_monitoreo
            WHERE 1=1
        """
        params: dict = {}

        if client_id:
            query += " AND client_id = :client_id"
            params["client_id"] = client_id
        if riesgo_nivel:
            query += " AND riesgo_nivel = :riesgo_nivel"
            params["riesgo_nivel"] = riesgo_nivel
        if blockchain:
            query += " AND blockchain = :blockchain"
            params["blockchain"] = blockchain
        if solo_criticos:
            query += " AND (gl_score < 30 OR riesgo_nivel IN ('Crítico','Alto'))"
        if search_text:
            query += " AND (wallet_address ILIKE :search OR client_nombre ILIKE :search)"
            params["search"] = f"%{search_text}%"

        query += " ORDER BY gl_score ASC NULLS LAST, updated_at DESC"

        try:
            rows = self.session.execute(text(query), params).mappings().all()
            return [dict(r) for r in rows]
        except ProgrammingError:
            self.session.rollback()
            logger.warning(_MSG_TABLA_NO_INIT)
            return []

    # ── Métricas para reporte gerencial ──────────────────────
    def get_stats_gerencial(self) -> dict:
        """
        Retorna métricas consolidadas para el dashboard gerencial.
        Si la tabla no existe (migración pendiente), retorna _STATS_VACIAS
        con '_tabla_no_existe': True para que la UI muestre el aviso correcto.
        """
        # Verificar existencia con information_schema antes de consultar
        # (evita ProgrammingError y estados de conexión corruptos en el pool)
        try:
            tabla_existe = self.session.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name   = 'crypto_monitoreo'
                )
            """)).scalar()
        except Exception:
            return dict(_STATS_VACIAS)

        if not tabla_existe:
            logger.warning(_MSG_TABLA_NO_INIT)
            return dict(_STATS_VACIAS)

        try:
            stats = self.session.execute(text("""
                SELECT
                    COUNT(*)                                            AS total_wallets,
                    COALESCE(SUM(total_exposure), 0)                   AS total_exposure_usd,
                    COUNT(*) FILTER (WHERE gl_score < 30
                                  OR riesgo_nivel IN ('Crítico','Alto')) AS atencion_prioritaria,
                    COUNT(*) FILTER (WHERE riesgo_nivel = 'Crítico')   AS nivel_critico,
                    COUNT(*) FILTER (WHERE riesgo_nivel = 'Alto')      AS nivel_alto,
                    COUNT(*) FILTER (WHERE riesgo_nivel = 'Medio')     AS nivel_medio,
                    COUNT(*) FILTER (WHERE riesgo_nivel = 'Bajo')      AS nivel_bajo,
                    COUNT(*) FILTER (WHERE riesgo_nivel = 'Sin Datos') AS sin_datos
                FROM crypto_monitoreo
            """)).mappings().first()
        except ProgrammingError:
            self.session.rollback()
            logger.warning(_MSG_TABLA_NO_INIT)
            return dict(_STATS_VACIAS)

        # COUNT(*) nunca devuelve NULL, pero si la tabla estuviera vacía
        # first() puede ser None en algunos drivers — garantizamos un dict seguro.
        stats_dict: dict = dict(stats) if stats else {}

        try:
            por_blockchain = self.session.execute(text("""
                SELECT blockchain, COUNT(*) AS total
                FROM crypto_monitoreo
                GROUP BY blockchain ORDER BY total DESC
            """)).mappings().all()
            por_bc_list = [dict(r) for r in por_blockchain]
        except ProgrammingError:
            self.session.rollback()
            logger.warning(_MSG_TABLA_NO_INIT)
            por_bc_list = []

        return {
            "total_wallets":        int(stats_dict.get("total_wallets", 0) or 0),
            "total_exposure_usd":   float(stats_dict.get("total_exposure_usd", 0) or 0),
            "atencion_prioritaria": int(stats_dict.get("atencion_prioritaria", 0) or 0),
            "nivel_critico":        int(stats_dict.get("nivel_critico", 0) or 0),
            "nivel_alto":           int(stats_dict.get("nivel_alto", 0) or 0),
            "nivel_medio":          int(stats_dict.get("nivel_medio", 0) or 0),
            "nivel_bajo":           int(stats_dict.get("nivel_bajo", 0) or 0),
            "sin_datos":            int(stats_dict.get("sin_datos", 0) or 0),
            "por_blockchain":       por_bc_list,
            "_tabla_no_existe":     False,
        }

    # ── Wallets en atención prioritaria ──────────────────────
    def get_atencion_prioritaria(self) -> list[dict]:
        """Score < 30 O nivel Crítico/Alto — ordenadas por score ascendente.
        Retorna [] si la tabla aún no existe."""
        try:
            rows = self.session.execute(text("""
                SELECT id, wallet_address, blockchain, client_nombre,
                       gl_score, riesgo_nivel, risk_labels,
                       total_exposure, exposure_currency, pdf_report_url, last_report_date
                FROM crypto_monitoreo
                WHERE gl_score < 30
                   OR riesgo_nivel IN ('Crítico', 'Alto')
                ORDER BY gl_score ASC NULLS FIRST, total_exposure DESC
            """)).mappings().all()
            return [dict(r) for r in rows]
        except ProgrammingError:
            self.session.rollback()
            logger.warning(_MSG_TABLA_NO_INIT)
            return []

    # ── Eliminar ──────────────────────────────────────────────
    def delete(self, wallet_id: int) -> bool:
        try:
            result = self.session.execute(
                text("DELETE FROM crypto_monitoreo WHERE id = :id"),
                {"id": wallet_id},
            )
            self.session.commit()
            return result.rowcount > 0
        except ProgrammingError:
            self.session.rollback()
            logger.warning(_MSG_TABLA_NO_INIT)
            return False
