"""
db/repositories/agente_repo.py
Repositorio del catálogo de agentes operativos.

Los agentes son registros informativos — NO son usuarios del sistema.
Los KPIs se calculan en base a los aliados asignados (aliados.agente_id).
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Campos editables desde la UI (whitelist de seguridad)
_CAMPOS_EDITABLES = frozenset({
    "nombre_completo",
    "equipo",
    "cargo",
    "email",
    "telefono",
    "foto_url",
    "meta_mensual_gestiones",
    "notas",
    "activo",
    "kpi_cuentas_pers_activas",
    "kpi_cuentas_com_activas",
    "kpi_cuentas_pers_aprobadas",
    "kpi_cuentas_pers_rechazadas",
    "kpi_cuentas_pers_investigacion",
    "kpi_cuentas_com_aprobadas",
    "kpi_cuentas_com_rechazadas",
    "kpi_cuentas_com_investigacion",
})

# Columnas de KPI manuales — editables vía editor inline y carga Excel
_KPI_COLUMNS: tuple[str, ...] = (
    "kpi_docs_personales",
    "kpi_docs_comerciales",
    "kpi_sanciones_revisadas",
    "kpi_alertas_hardstop",
    "kpi_tx_ongoing",
)


class AgenteRepository:
    """CRUD e indicadores de desempeño del catálogo de agentes."""

    def __init__(self, session: Session):
        self.session = session

    # ── Consultas ─────────────────────────────────────────

    def get_all_active(self) -> list[dict]:
        """Todos los agentes activos ordenados por equipo y nombre."""
        rows = self.session.execute(text("""
            SELECT id, username, nombre_completo, equipo, cargo,
                   email, telefono, foto_url, meta_mensual_gestiones,
                   notas, activo, created_at, updated_at
            FROM agentes
            WHERE activo = TRUE
            ORDER BY equipo, nombre_completo
        """)).mappings().all()
        return [dict(r) for r in rows]

    def get_all(self) -> list[dict]:
        """Todos los agentes (activos + inactivos)."""
        rows = self.session.execute(text("""
            SELECT id, username, nombre_completo, equipo, cargo,
                   email, telefono, foto_url, meta_mensual_gestiones,
                   notas, activo, created_at, updated_at
            FROM agentes
            ORDER BY equipo, nombre_completo
        """)).mappings().all()
        return [dict(r) for r in rows]

    def get_by_username(self, username: str) -> Optional[dict]:
        row = self.session.execute(
            text("SELECT * FROM agentes WHERE username = :u"),
            {"u": username},
        ).mappings().first()
        return dict(row) if row else None

    def get_by_id(self, agente_id: int) -> Optional[dict]:
        row = self.session.execute(
            text("SELECT * FROM agentes WHERE id = :id"),
            {"id": agente_id},
        ).mappings().first()
        return dict(row) if row else None

    def username_exists(self, username: str) -> bool:
        cnt = self.session.execute(
            text("SELECT COUNT(*) FROM agentes WHERE username = :u"),
            {"u": username},
        ).scalar()
        return int(cnt or 0) > 0

    # ── Crear ─────────────────────────────────────────────

    def create(
        self,
        username: str,
        nombre_completo: str,
        equipo: str,
        cargo: Optional[str] = None,
        email: Optional[str] = None,
        telefono: Optional[str] = None,
        foto_url: Optional[str] = None,
        meta_mensual_gestiones: int = 50,
        notas: Optional[str] = None,
    ) -> int:
        """Inserta un nuevo agente en el catálogo y retorna su ID."""
        result = self.session.execute(text("""
            INSERT INTO agentes (
                username, nombre_completo, equipo, cargo,
                email, telefono, foto_url,
                meta_mensual_gestiones, notas, activo
            ) VALUES (
                :username, :nombre_completo, :equipo, :cargo,
                :email, :telefono, :foto_url,
                :meta_mensual_gestiones, :notas, TRUE
            ) RETURNING id
        """), {
            "username":               username,
            "nombre_completo":        nombre_completo,
            "equipo":                 equipo,
            "cargo":                  cargo,
            "email":                  email,
            "telefono":               telefono,
            "foto_url":               foto_url,
            "meta_mensual_gestiones": meta_mensual_gestiones,
            "notas":                  notas,
        })
        self.session.commit()
        uid = result.scalar()
        logger.info("[AGENTE] Creado: %s (id=%s) equipo=%s", username, uid, equipo)
        return uid

    # ── Actualizar ────────────────────────────────────────

    def update(self, agente_id: int, fields: dict) -> bool:
        """Actualiza los campos permitidos de un agente."""
        safe = {k: v for k, v in fields.items() if k in _CAMPOS_EDITABLES}
        if not safe:
            return False
        set_clause = ", ".join(f"{k} = :{k}" for k in safe)
        safe["id"] = agente_id
        self.session.execute(
            text(f"UPDATE agentes SET {set_clause} WHERE id = :id"),
            safe,
        )
        self.session.commit()
        logger.info("[AGENTE] Actualizado id=%s campos=%s", agente_id, list(fields))
        return True

    # ── KPIs de Gestión ───────────────────────────────────

    def get_metrics(self, agente_id: int) -> dict:
        """
        Calcula indicadores de gestión a partir de los aliados asignados.

        Retorna:
            total_partners:       Total de aliados asignados al agente.
            partners_activos:     Aliados en estado_pipeline = 'Activo'.
            partners_riesgo_alto: Aliados con nivel_riesgo IN ('Alto', 'Muy Alto').
            tasa_activacion_pct:  % de partners que llegaron a estado 'Activo'.
            distribucion_riesgo:  {nivel_riesgo: count} de partners asignados.
            distribucion_estado:  {estado_pipeline: count} de partners asignados.
            meta_mensual:         Meta configurada en el perfil del agente.
        """
        agente = self.get_by_id(agente_id)
        meta   = int(agente["meta_mensual_gestiones"]) if agente else 50

        resumen = self.session.execute(text("""
            SELECT
                COUNT(*)                                                      AS total,
                COUNT(*) FILTER (WHERE estado_pipeline = 'Activo')            AS activos,
                COUNT(*) FILTER (WHERE nivel_riesgo IN ('Alto', 'Muy Alto'))  AS riesgo_alto
            FROM aliados
            WHERE agente_id = :id
        """), {"id": agente_id}).mappings().first()

        total    = int(resumen["total"]      or 0)
        activos  = int(resumen["activos"]    or 0)
        alto     = int(resumen["riesgo_alto"] or 0)
        tasa_act = round(activos / total * 100, 1) if total > 0 else 0.0

        # Distribución por nivel de riesgo
        riesgo_rows = self.session.execute(text("""
            SELECT nivel_riesgo, COUNT(*) AS cnt
            FROM aliados
            WHERE agente_id = :id
            GROUP BY nivel_riesgo
            ORDER BY cnt DESC
        """), {"id": agente_id}).mappings().all()
        dist_riesgo = {r["nivel_riesgo"]: int(r["cnt"]) for r in riesgo_rows}

        # Distribución por estado del pipeline
        estado_rows = self.session.execute(text("""
            SELECT estado_pipeline, COUNT(*) AS cnt
            FROM aliados
            WHERE agente_id = :id
            GROUP BY estado_pipeline
            ORDER BY cnt DESC
        """), {"id": agente_id}).mappings().all()
        dist_estado = {r["estado_pipeline"]: int(r["cnt"]) for r in estado_rows}

        return {
            "total_partners":       total,
            "partners_activos":     activos,
            "partners_riesgo_alto": alto,
            "tasa_activacion_pct":  tasa_act,
            "distribucion_riesgo":  dist_riesgo,
            "distribucion_estado":  dist_estado,
            "meta_mensual":         meta,
        }

    # ── KPIs de Compliance por equipo ────────────────────────

    def get_compliance_kpis(self, agente_id: int) -> dict:
        """
        KPIs especializados para agentes del equipo Cumplimiento.

        Extrae conteos derivados de los campos de documentación, listas y
        due-diligence de los aliados asignados, segmentando entre tipo_aliado
        personal ('Banking Partner', 'Aliado Estratégico') y comercial
        ('Corresponsal Bancario', 'Proveedor de Servicios').

        Retorna:
            docs_personales:           Aliados tipo personal con contrato firmado.
            docs_comerciales:          Aliados tipo comercial con contrato firmado.
            cuentas_personales:        Aliados tipo personal en estado 'Activo'.
            cuentas_comerciales:       Aliados tipo comercial en estado 'Activo'.
            sanciones_revisadas:       Aliados con listas_verificadas = TRUE.
            sanciones_pendientes:      Aliados con listas_verificadas = FALSE.
            hardstop_resueltos:        Aliados con estado_sarlaft = 'Al Día'.
            hardstop_pendientes:       Aliados con estado_sarlaft IN ('Vencido', 'En Revisión').
            tx_ongoing_personal:       Aliados personales con estado_due_diligence = 'Completado'.
            tx_ongoing_comercial:      Aliados comerciales con estado_due_diligence = 'Completado'.
        """
        _TIPOS_PERSONAL  = ("'Banking Partner'", "'Aliado Estratégico'")
        _TIPOS_COMERCIAL = ("'Corresponsal Bancario'", "'Proveedor de Servicios'")
        tp  = ", ".join(_TIPOS_PERSONAL)
        tc  = ", ".join(_TIPOS_COMERCIAL)

        row = self.session.execute(text(f"""
            SELECT
                -- Documentación
                COUNT(*) FILTER (WHERE tipo_aliado IN ({tp}) AND contrato_firmado = TRUE)
                    AS docs_personales,
                COUNT(*) FILTER (WHERE tipo_aliado IN ({tc}) AND contrato_firmado = TRUE)
                    AS docs_comerciales,
                -- Cuentas activas
                COUNT(*) FILTER (WHERE tipo_aliado IN ({tp}) AND estado_pipeline = 'Activo')
                    AS cuentas_personales,
                COUNT(*) FILTER (WHERE tipo_aliado IN ({tc}) AND estado_pipeline = 'Activo')
                    AS cuentas_comerciales,
                -- Sanciones
                COUNT(*) FILTER (WHERE listas_verificadas = TRUE)
                    AS sanciones_revisadas,
                COUNT(*) FILTER (WHERE listas_verificadas = FALSE)
                    AS sanciones_pendientes,
                -- SARLAFT / Hardstop
                COUNT(*) FILTER (WHERE estado_sarlaft = 'Al Día')
                    AS hardstop_resueltos,
                COUNT(*) FILTER (WHERE estado_sarlaft IN ('Vencido', 'En Revisión'))
                    AS hardstop_pendientes,
                -- TX Ongoing (due-diligence completado)
                COUNT(*) FILTER (
                    WHERE tipo_aliado IN ({tp}) AND estado_due_diligence = 'Completado'
                ) AS tx_ongoing_personal,
                COUNT(*) FILTER (
                    WHERE tipo_aliado IN ({tc}) AND estado_due_diligence = 'Completado'
                ) AS tx_ongoing_comercial
            FROM aliados
            WHERE agente_id = :id
        """), {"id": agente_id}).mappings().first()

        def _int(v: object) -> int:
            return int(v or 0)

        return {
            "docs_personales":      _int(row["docs_personales"]),
            "docs_comerciales":     _int(row["docs_comerciales"]),
            "cuentas_personales":   _int(row["cuentas_personales"]),
            "cuentas_comerciales":  _int(row["cuentas_comerciales"]),
            "sanciones_revisadas":  _int(row["sanciones_revisadas"]),
            "sanciones_pendientes": _int(row["sanciones_pendientes"]),
            "hardstop_resueltos":   _int(row["hardstop_resueltos"]),
            "hardstop_pendientes":  _int(row["hardstop_pendientes"]),
            "tx_ongoing_personal":  _int(row["tx_ongoing_personal"]),
            "tx_ongoing_comercial": _int(row["tx_ongoing_comercial"]),
        }

    # ── Editor de KPIs Inline ─────────────────────────────

    def get_kpi_table(self, equipo: Optional[str] = None):
        """
        Devuelve un DataFrame de Pandas con los KPIs manuales editables
        de cada agente activo.

        Parámetros:
            equipo: Si se indica, filtra por equipo (ej: 'Cumplimiento').
                    None → todos los equipos (solo para administradores).

        Columnas del DataFrame:
            id, username, nombre_completo, equipo, cargo,
            kpi_docs_personales, kpi_docs_comerciales,
            kpi_sanciones_revisadas, kpi_alertas_hardstop, kpi_tx_ongoing.
        """
        import pandas as pd

        where  = "WHERE activo = TRUE"
        params: dict = {}
        if equipo:
            where += " AND equipo = :equipo"
            params["equipo"] = equipo

        cols   = ", ".join(_KPI_COLUMNS)
        rows   = self.session.execute(text(f"""
            SELECT id, username, nombre_completo, equipo, cargo, {cols}
            FROM agentes
            {where}
            ORDER BY equipo, nombre_completo
        """), params).mappings().all()

        df_cols = ["id", "username", "nombre_completo", "equipo", "cargo"] + list(_KPI_COLUMNS)
        if not rows:
            return pd.DataFrame(columns=df_cols)

        df = pd.DataFrame([dict(r) for r in rows])
        for col in _KPI_COLUMNS:
            df[col] = df[col].fillna(0).astype(int)
        return df

    def update_kpis_from_editor(self, df_editado, usuario: dict) -> dict:
        """
        Actualiza las columnas kpi_* de la tabla agentes desde el DataFrame
        devuelto por ``st.data_editor``.

        Detecta cambios comparando contra los valores actuales en BD.
        Registra en ``log_auditoria`` cada fila que haya cambiado.

        Parámetros:
            df_editado: DataFrame con los cambios del editor.
                        Debe incluir la columna ``id``.
            usuario:    Dict del usuario autenticado {id, username}.

        Retorna:
            {"actualizados": int}  — número de filas con cambios guardados.
        """
        import pandas as pd
        from db.repositories.audit_repo import AuditRepository

        if "id" not in df_editado.columns:
            raise ValueError("El DataFrame debe contener la columna 'id'.")

        kpi_cols = [c for c in _KPI_COLUMNS if c in df_editado.columns]
        if not kpi_cols:
            raise ValueError(
                f"El DataFrame no contiene columnas KPI válidas. "
                f"Esperadas: {list(_KPI_COLUMNS)}"
            )

        audit        = AuditRepository(self.session)
        actualizados = 0
        cols_sql     = ", ".join(kpi_cols)

        try:
            for _, row in df_editado.iterrows():
                agente_id = int(row["id"])

                updates: dict = {}
                for col in kpi_cols:
                    val = row.get(col)
                    if pd.notna(val):
                        updates[col] = max(0, int(val))

                if not updates:
                    continue

                # Valores actuales en BD para auditoría y detección de cambios
                prev = self.session.execute(
                    text(f"SELECT {cols_sql} FROM agentes WHERE id = :id"),
                    {"id": agente_id},
                ).mappings().first()

                prev_vals = dict(prev) if prev else {}

                # Omitir si no hubo cambios reales
                if all(int(prev_vals.get(k) or 0) == v for k, v in updates.items()):
                    continue

                set_clause = ", ".join(f"{col} = :{col}" for col in updates)
                self.session.execute(
                    text(
                        f"UPDATE agentes "
                        f"SET {set_clause}, updated_at = now() "
                        f"WHERE id = :id"
                    ),
                    {**updates, "id": agente_id},
                )

                audit.registrar(
                    username    = usuario.get("username", "sistema"),
                    usuario_id  = usuario.get("id"),
                    accion      = "UPDATE",
                    entidad     = "agentes",
                    entidad_id  = agente_id,
                    descripcion = (
                        f"KPIs actualizados vía editor inline: "
                        f"{row.get('username', agente_id)}"
                    ),
                    valores_anteriores = {k: int(prev_vals.get(k) or 0) for k in updates},
                    valores_nuevos     = updates,
                )
                actualizados += 1

            self.session.commit()

        except (ValueError, TypeError) as exc:
            self.session.rollback()
            raise ValueError(f"Error de tipo de datos en el editor: {exc}") from exc

        logger.info(
            "[AGENTE] update_kpis_from_editor: actualizados=%s usuario=%s",
            actualizados, usuario.get("username"),
        )
        return {"actualizados": actualizados}

    # ── Bitácora Diaria de KPIs ───────────────────────────

    def get_kpi_diario(self, agente_id: int, fecha=None) -> Optional[dict]:
        """
        Devuelve el registro de ``agente_kpi_diario`` para el agente en la
        fecha indicada (por defecto CURRENT_DATE).  Retorna None si no existe.
        """
        if fecha is None:
            row = self.session.execute(text("""
                SELECT id, agente_id, fecha,
                       docs_personales, docs_comerciales,
                       sanciones, hardstop, tx_ongoing,
                       observaciones,
                       updated_at
                FROM agente_kpi_diario
                WHERE agente_id = :id
                  AND fecha = CURRENT_DATE
            """), {"id": agente_id}).mappings().first()
        else:
            row = self.session.execute(text("""
                SELECT id, agente_id, fecha,
                       docs_personales, docs_comerciales,
                       sanciones, hardstop, tx_ongoing,
                       observaciones,
                       updated_at
                FROM agente_kpi_diario
                WHERE agente_id = :id
                  AND fecha = :fecha
            """), {"id": agente_id, "fecha": fecha}).mappings().first()
        return dict(row) if row else None

    def upsert_kpi_diario(self, agente_id: int, data: dict) -> None:
        """
        Inserta o actualiza el registro de KPIs del día actual para el agente.

        ``data`` puede contener cualquier subconjunto de las columnas editables:
        docs_personales, docs_comerciales, sanciones, hardstop, tx_ongoing,
        observaciones.

        Usa INSERT … ON CONFLICT (agente_id, fecha) DO UPDATE.
        """
        _COLS_INT  = ("docs_personales", "docs_comerciales", "sanciones", "hardstop", "tx_ongoing")
        _COLS_TEXT = ("observaciones",)
        safe: dict = {}
        for k in _COLS_INT:
            if k in data:
                safe[k] = max(0, int(data[k] or 0))
        for k in _COLS_TEXT:
            if k in data:
                val = data[k]
                safe[k] = str(val).strip() if val else None
        if not safe:
            return

        col_names  = ", ".join(safe)
        col_values = ", ".join(f":{k}" for k in safe)
        col_update = ", ".join(f"{k} = EXCLUDED.{k}" for k in safe)

        self.session.execute(text(f"""
            INSERT INTO agente_kpi_diario (agente_id, fecha, {col_names})
            VALUES (:agente_id, CURRENT_DATE, {col_values})
            ON CONFLICT (agente_id, fecha) DO UPDATE
            SET {col_update},
                updated_at = CURRENT_TIMESTAMP
        """), {"agente_id": agente_id, **safe})
        self.session.commit()
        logger.info("[AGENTE] upsert_kpi_diario agente_id=%s data=%s", agente_id, safe)

    def get_agente_stats_global(self, agente_id: int) -> dict:
        """
        Calcula la sumatoria histórica de todos los registros diarios del agente.

        Retorna:
            docs_personales_total, docs_comerciales_total,
            sanciones_total, hardstop_total, tx_ongoing_total,
            dias_registrados  — número de días con al menos un registro.
        """
        row = self.session.execute(text("""
            SELECT
                COALESCE(SUM(docs_personales),  0) AS docs_personales_total,
                COALESCE(SUM(docs_comerciales), 0) AS docs_comerciales_total,
                COALESCE(SUM(sanciones),        0) AS sanciones_total,
                COALESCE(SUM(hardstop),         0) AS hardstop_total,
                COALESCE(SUM(tx_ongoing),       0) AS tx_ongoing_total,
                COUNT(*)                           AS dias_registrados
            FROM agente_kpi_diario
            WHERE agente_id = :id
        """), {"id": agente_id}).mappings().first()

        def _int(v: object) -> int:
            return int(v or 0)

        return {
            "docs_personales_total":  _int(row["docs_personales_total"]),
            "docs_comerciales_total": _int(row["docs_comerciales_total"]),
            "sanciones_total":        _int(row["sanciones_total"]),
            "hardstop_total":         _int(row["hardstop_total"]),
            "tx_ongoing_total":       _int(row["tx_ongoing_total"]),
            "dias_registrados":       _int(row["dias_registrados"]),
        }

    def get_stats_agente(self, agente_id: int) -> dict:
        """
        Retorna en una sola llamada los totales históricos acumulados y el
        registro del día actual para el agente indicado.

        Retorna:
            totales: dict — resultado de get_agente_stats_global
            hoy:     dict — registro de CURRENT_DATE (vacío si no existe)
        """
        return {
            "totales": self.get_agente_stats_global(agente_id),
            "hoy":     self.get_kpi_diario(agente_id) or {},
        }

    def registrar_gestion_diaria(
        self, agente_id: int, data: dict, admin_user: dict
    ) -> None:
        """
        UPSERT del registro de KPIs del día en ``agente_kpi_diario`` +
        entrada de auditoría en ``log_auditoria``.

        Parámetros:
            agente_id:  ID del agente al que se registra la gestión.
            data:       Diccionario con columnas editables (docs_personales,
                        docs_comerciales, sanciones, hardstop, tx_ongoing).
            admin_user: Dict del usuario administrador {id, username}.
        """
        from db.repositories.audit_repo import AuditRepository

        _COLS_DIARIO = ("docs_personales", "docs_comerciales", "sanciones", "hardstop", "tx_ongoing", "observaciones")
        prev = self.get_kpi_diario(agente_id) or {}
        self.upsert_kpi_diario(agente_id, data)

        AuditRepository(self.session).registrar(
            username           = admin_user.get("username", "sistema"),
            usuario_id         = admin_user.get("id"),
            accion             = "UPDATE",
            entidad            = "agente_kpi_diario",
            entidad_id         = agente_id,
            descripcion        = (
                f"Bitácora diaria actualizada: agente_id={agente_id} "
                f"por {admin_user.get('username', 'sistema')}"
            ),
            valores_anteriores = {k: prev.get(k) for k in _COLS_DIARIO if k in prev},
            valores_nuevos     = {k: data.get(k) for k in _COLS_DIARIO if k in data},
        )

    # ── IA Insights — Gestiones recientes para análisis ───

    def get_recent_gestiones(self, agente_id: int, limit: int = 5) -> list[dict]:
        """
        Recupera los últimos `limit` aliados asignados al agente con sus datos
        de compliance, enriquecidos con las notas de jornada de agente_kpi_diario.

        Lógica de notas:
        - Toma los últimos `limit` registros de agente_kpi_diario ordenados
          por fecha DESC (sin filtro de fecha estricto).
        - Construye un bloque de texto unificado con todas las notas no vacías.
        - Si ningún registro tiene notas, el campo `observaciones` queda None
          (la IA analiza sólo los campos estructurados del aliado).

        Las observaciones se devuelven SIN anonimizar — la anonimización
        ocurre en ai_handler.anonymize_text() antes de enviar a la API.
        """
        # ── 1. Últimas notas de jornada (sin filtro de fecha estricto) ───────
        kpi_rows = self.session.execute(text("""
            SELECT fecha, observaciones
            FROM agente_kpi_diario
            WHERE agente_id = :id
              AND observaciones IS NOT NULL
              AND TRIM(observaciones) <> ''
            ORDER BY fecha DESC, created_at DESC
            LIMIT :lim
        """), {"id": agente_id, "lim": limit}).mappings().all()

        # Sanity check: log para depuración en Railway
        if kpi_rows:
            primer_obs = (kpi_rows[0]["observaciones"] or "")[:20]
            logger.info(
                "[IA] agente_id=%s notas_diario=%d primera_obs='%s...'",
                agente_id, len(kpi_rows), primer_obs,
            )
        else:
            logger.info("[IA] agente_id=%s sin notas de jornada registradas.", agente_id)

        # Bloque unificado de notas ordenadas cronológicamente
        bloques = []
        for row in kpi_rows:
            fecha_str = str(row["fecha"])[:10]
            bloques.append(f"[{fecha_str}] {(row['observaciones'] or '').strip()}")
        notas_unificadas: str = "\n".join(bloques) if bloques else ""

        # ── 2. Últimos aliados asignados (contexto estructurado) ─────────────
        rows = self.session.execute(text("""
            SELECT
                LEFT(nombre_razon_social, 3) || '***' AS nombre_alias,
                tipo_aliado,
                nivel_riesgo,
                estado_pipeline,
                estado_sarlaft,
                estado_due_diligence,
                COALESCE(es_pep, FALSE)              AS es_pep,
                COALESCE(resultado_listas,
                    'Sin coincidencias')             AS resultado_listas,
                COALESCE(alertas_activas, 0)         AS alertas_activas,
                observaciones_compliance             AS observaciones,
                updated_at
            FROM aliados
            WHERE agente_id = :id
            ORDER BY updated_at DESC NULLS LAST
            LIMIT :lim
        """), {"id": agente_id, "lim": limit}).mappings().all()

        result = [dict(r) for r in rows]

        # ── 3. Enriquecer primer registro con notas de jornada ───────────────
        if notas_unificadas and result:
            obs_partner = result[0].get("observaciones") or ""
            if obs_partner:
                result[0]["observaciones"] = (
                    obs_partner
                    + "\n\n[Notas de jornada del colaborador]:\n"
                    + notas_unificadas
                )
            else:
                result[0]["observaciones"] = (
                    "[Notas de jornada del colaborador]:\n" + notas_unificadas
                )

        return result
