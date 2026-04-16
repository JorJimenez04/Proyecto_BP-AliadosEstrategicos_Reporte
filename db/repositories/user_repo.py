"""
db/repositories/user_repo.py
Repositorio de Usuarios — CRUD y métricas de desempeño de agentes.
"""

import logging
from typing import Optional

import bcrypt
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Campos que se pueden actualizar desde la UI (whitelist de seguridad)
_CAMPOS_ACTUALIZABLES = frozenset({
    "nombre_completo",
    "email",
    "rol",
    "departamento",
    "equipo",
    "cargo",
    "foto_url",
    "meta_mensual_gestiones",
    "activo",
})


class UserRepository:
    """CRUD de usuarios y cálculo de KPIs de desempeño de agentes."""

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

    def get_all_active(self) -> list[dict]:
        """Retorna todos los usuarios activos ordenados por nombre."""
        rows = self.session.execute(
            text("""
                SELECT id, username, nombre_completo, email, rol, departamento,
                       equipo, cargo, foto_url, meta_mensual_gestiones,
                       activo, ultimo_acceso, created_at
                FROM usuarios
                WHERE activo = 1
                ORDER BY nombre_completo
            """),
        ).mappings().all()
        return [dict(r) for r in rows]

    # ── Crear ─────────────────────────────────────────────

    def create_user(
        self,
        username: str,
        nombre_completo: str,
        email: str,
        password_plain: str,
        rol: str = "consulta",
        departamento: Optional[str] = None,
        equipo: Optional[str] = None,
        cargo: Optional[str] = None,
        foto_url: Optional[str] = None,
        meta_mensual_gestiones: int = 50,
    ) -> int:
        """Crea un nuevo usuario. La contraseña se hashea con bcrypt antes de persistir."""
        password_hash = bcrypt.hashpw(
            password_plain.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")

        result = self.session.execute(
            text("""
                INSERT INTO usuarios (
                    username, nombre_completo, email, password_hash, rol,
                    departamento, equipo, cargo, foto_url,
                    meta_mensual_gestiones, activo
                ) VALUES (
                    :username, :nombre_completo, :email, :password_hash, :rol,
                    :departamento, :equipo, :cargo, :foto_url,
                    :meta_mensual_gestiones, 1
                )
                RETURNING id
            """),
            {
                "username":               username,
                "nombre_completo":        nombre_completo,
                "email":                  email,
                "password_hash":          password_hash,
                "rol":                    rol,
                "departamento":           departamento,
                "equipo":                 equipo,
                "cargo":                  cargo,
                "foto_url":               foto_url,
                "meta_mensual_gestiones": meta_mensual_gestiones,
            },
        )
        self.session.commit()
        uid = result.scalar()
        logger.info("[USER] Creado usuario %s (id=%s)", username, uid)
        return uid

    # ── Actualizar ────────────────────────────────────────

    def update_user(self, user_id: int, fields: dict) -> bool:
        """
        Actualiza los campos especificados de un usuario.
        Solo se procesan los campos en _CAMPOS_ACTUALIZABLES.
        """
        safe = {k: v for k, v in fields.items() if k in _CAMPOS_ACTUALIZABLES}
        if not safe:
            return False

        # activo column is INTEGER in DB: convert Python bool → 1/0
        if "activo" in safe and isinstance(safe["activo"], bool):
            safe["activo"] = 1 if safe["activo"] else 0

        set_clause = ", ".join(f"{k} = :{k}" for k in safe)
        set_clause += ", updated_at = CURRENT_TIMESTAMP"
        safe["id"] = user_id

        self.session.execute(
            text(f"UPDATE usuarios SET {set_clause} WHERE id = :id"),
            safe,
        )
        self.session.commit()
        logger.info("[USER] Actualizado usuario id=%s campos=%s", user_id, list(fields))
        return True

    # ── KPIs de Desempeño ─────────────────────────────────

    def get_metrics_agente(self, username: str) -> dict:
        """
        Calcula KPIs de desempeño para un agente a partir de los logs de auditoría
        y los registros de aliados asociados.

        Retorna:
            productividad_mes:        Total de registros auditados en el mes actual.
            meta_mensual:             Meta mensual configurada en el perfil del agente.
            calidad_pct:              % de partners creados por el agente en estado 'Activo'.
            efectividad_sarlaft_dias: Promedio de días desde creación del prospecto
                                      hasta su primera revisión SARLAFT.
            tasa_errores_pct:         % de acciones en log con resultado='fallido'.
            distribucion_riesgo:      {nivel_riesgo: count} de partners asignados al agente.
            total_gestiones:          Total histórico de gestiones registradas.
        """
        _empty = {
            "productividad_mes":        0,
            "meta_mensual":             50,
            "calidad_pct":              0.0,
            "efectividad_sarlaft_dias": None,
            "tasa_errores_pct":         0.0,
            "distribucion_riesgo":      {},
            "total_gestiones":          0,
        }

        row_user = self.session.execute(
            text("""
                SELECT id, meta_mensual_gestiones
                FROM usuarios
                WHERE username = :u
            """),
            {"u": username},
        ).mappings().first()

        if not row_user:
            return _empty

        uid          = row_user["id"]
        meta_mensual = int(row_user["meta_mensual_gestiones"] or 50)

        # ── KPI 1: Productividad — gestiones en el mes actual ──
        prod = self.session.execute(
            text("""
                SELECT COUNT(*) AS cnt
                FROM log_auditoria
                WHERE usuario_id = :uid
                  AND DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
            """),
            {"uid": uid},
        ).mappings().first()
        productividad_mes = int(prod["cnt"] or 0)

        # Total histórico de gestiones
        total_row = self.session.execute(
            text("SELECT COUNT(*) AS cnt FROM log_auditoria WHERE usuario_id = :uid"),
            {"uid": uid},
        ).mappings().first()
        total_gestiones = int(total_row["cnt"] or 0)

        # ── KPI 2: Calidad — % partners creados que alcanzaron estado 'Activo' ──
        cal = self.session.execute(
            text("""
                SELECT
                    COUNT(*) AS total_creados,
                    COUNT(*) FILTER (WHERE estado_pipeline = 'Activo') AS activos
                FROM aliados
                WHERE creado_por = :uid
            """),
            {"uid": uid},
        ).mappings().first()
        total_creados  = int(cal["total_creados"] or 0)
        activos_cnt    = int(cal["activos"] or 0)
        calidad_pct    = round(activos_cnt / total_creados * 100, 1) if total_creados > 0 else 0.0

        # ── KPI 3: Efectividad SARLAFT — días promedio hasta primera revisión ──
        efect = self.session.execute(
            text("""
                SELECT AVG(
                    EXTRACT(EPOCH FROM (
                        fecha_ultima_revision::timestamp - fecha_vinculacion::timestamp
                    )) / 86400
                )::NUMERIC(10,1) AS avg_dias
                FROM aliados
                WHERE creado_por = :uid
                  AND fecha_ultima_revision IS NOT NULL
                  AND fecha_vinculacion     IS NOT NULL
            """),
            {"uid": uid},
        ).mappings().first()
        efectividad_dias = float(efect["avg_dias"]) if efect and efect["avg_dias"] else None

        # ── Tasa de Errores — % de acciones con resultado='fallido' ──
        err = self.session.execute(
            text("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE resultado = 'fallido') AS fallidos
                FROM log_auditoria
                WHERE usuario_id = :uid
            """),
            {"uid": uid},
        ).mappings().first()
        total_accs   = int(err["total"] or 0)
        fallidos_cnt = int(err["fallidos"] or 0)
        tasa_errores = round(fallidos_cnt / total_accs * 100, 1) if total_accs > 0 else 0.0

        # ── Distribución de Riesgo — partners asignados como ejecutivo de cuenta ──
        riesgo_rows = self.session.execute(
            text("""
                SELECT nivel_riesgo, COUNT(*) AS cnt
                FROM aliados
                WHERE ejecutivo_cuenta_id = :uid
                GROUP BY nivel_riesgo
                ORDER BY cnt DESC
            """),
            {"uid": uid},
        ).mappings().all()
        distribucion_riesgo = {r["nivel_riesgo"]: int(r["cnt"]) for r in riesgo_rows}

        return {
            "productividad_mes":        productividad_mes,
            "meta_mensual":             meta_mensual,
            "calidad_pct":              calidad_pct,
            "efectividad_sarlaft_dias": efectividad_dias,
            "tasa_errores_pct":         tasa_errores,
            "distribucion_riesgo":      distribucion_riesgo,
            "total_gestiones":          total_gestiones,
        }
