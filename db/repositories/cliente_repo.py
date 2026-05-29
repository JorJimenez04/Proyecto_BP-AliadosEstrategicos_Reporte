"""
db/repositories/cliente_repo.py
Repositorio del módulo Gestión de Clientes — AdamoServices Partner Manager.
Gestiona CRUD sobre clientes, personas, contratos, servicios,
documentos y calificaciones de riesgo SARLAFT.
"""

import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class ClienteRepository:

    def __init__(self, session: Session):
        self.session = session

    # ──────────────────────────────────────────────────────────
    # Helpers internos
    # ──────────────────────────────────────────────────────────

    def _nivel_desde_puntaje(self, puntaje: int) -> str:
        if puntaje <= 20:
            return "Sin calificar"
        if puntaje <= 40:
            return "Bajo"
        if puntaje <= 60:
            return "Medio"
        if puntaje <= 80:
            return "Alto"
        return "Muy Alto"

    def _proxima_revision(self, nivel: str) -> date:
        hoy = date.today()
        delta = {
            "Bajo": 365,
            "Medio": 180,
            "Alto": 90,
            "Muy Alto": 30,
        }.get(nivel, 365)
        return hoy + timedelta(days=delta)

    def _calcular_puntaje(
        self,
        es_pep: int,
        exposicion_cripto: int,
        crypto_friendly: int,
        jurisdicciones: list,
        en_listas_restriccion: int,
        contratos_sin_firma: bool = False,
    ) -> int:
        from config.settings import Jurisdicciones
        puntaje = 0
        if es_pep:
            puntaje += 20
        if exposicion_cripto:
            puntaje += 15
        if crypto_friendly:
            puntaje += 10
        # Jurisdicciones GAFI alto riesgo
        juris_alto = [j for j in jurisdicciones if j in Jurisdicciones.ALTO_RIESGO]
        if len(juris_alto) >= 1:
            puntaje += 15
        if len(juris_alto) >= 2:
            puntaje += 10
        if len(jurisdicciones) >= 5:
            puntaje += 5
        if en_listas_restriccion:
            puntaje += 10
        if contratos_sin_firma:
            puntaje += 5
        return min(puntaje, 100)

    def _auditar(
        self,
        accion: str,
        entidad_id: int,
        valores_anteriores: Optional[dict],
        valores_nuevos: Optional[dict],
        usuario: str,
    ) -> None:
        from db.repositories.audit_repo import AuditRepository
        audit = AuditRepository(self.session)
        audit.registrar(
            username=usuario,
            accion=accion,
            entidad="clientes",
            descripcion=f"{accion} cliente id={entidad_id}",
            entidad_id=entidad_id,
            valores_anteriores=valores_anteriores,
            valores_nuevos=valores_nuevos,
        )

    def _tiene_contratos_sin_firma(self, cliente_id: int) -> bool:
        row = self.session.execute(text("""
            SELECT COUNT(*) FROM cliente_contratos
            WHERE cliente_id = :cliente_id
              AND estado = 'Activo'
              AND contrato_firmado = 0
        """), {"cliente_id": cliente_id}).scalar()
        return bool(row and row > 0)

    # ──────────────────────────────────────────────────────────
    # Clientes
    # ──────────────────────────────────────────────────────────

    def crear(self, data) -> dict:
        """INSERT cliente + historial de riesgo inicial si trae puntaje."""
        from db.models import ClienteCreate
        if not isinstance(data, ClienteCreate):
            from db.models import ClienteCreate as _M
            data = _M(**data)

        puntaje = data.puntaje_riesgo
        if puntaje is None:
            puntaje = self._calcular_puntaje(
                es_pep=data.es_pep,
                exposicion_cripto=data.exposicion_cripto,
                crypto_friendly=data.crypto_friendly,
                jurisdicciones=data.jurisdicciones or [],
                en_listas_restriccion=0,
            )
        nivel = self._nivel_desde_puntaje(puntaje)
        proxima = self._proxima_revision(nivel) if nivel != "Sin calificar" else None

        row = self.session.execute(text("""
            INSERT INTO clientes (
                razon_social, nit, tipo_sociedad, fecha_constitucion,
                pais_constitucion, sector_ciiu, sitio_web, direccion,
                nivel_riesgo, puntaje_riesgo, fecha_ultima_calificacion,
                proxima_revision, es_pep, exposicion_cripto, crypto_friendly,
                jurisdicciones, estado, notas, creado_por
            ) VALUES (
                :razon_social, :nit, :tipo_sociedad, :fecha_constitucion,
                :pais_constitucion, :sector_ciiu, :sitio_web, :direccion,
                :nivel_riesgo, :puntaje_riesgo, :fecha_ultima_calificacion,
                :proxima_revision, :es_pep, :exposicion_cripto, :crypto_friendly,
                :jurisdicciones, :estado, :notas, :creado_por
            )
            RETURNING *
        """), {
            "razon_social": data.razon_social,
            "nit": data.nit,
            "tipo_sociedad": data.tipo_sociedad,
            "fecha_constitucion": data.fecha_constitucion,
            "pais_constitucion": data.pais_constitucion,
            "sector_ciiu": data.sector_ciiu,
            "sitio_web": data.sitio_web,
            "direccion": data.direccion,
            "nivel_riesgo": nivel,
            "puntaje_riesgo": puntaje,
            "fecha_ultima_calificacion": date.today(),
            "proxima_revision": proxima,
            "es_pep": data.es_pep,
            "exposicion_cripto": data.exposicion_cripto,
            "crypto_friendly": data.crypto_friendly,
            "jurisdicciones": data.jurisdicciones or [],
            "estado": data.estado,
            "notas": data.notas,
            "creado_por": data.creado_por,
        }).mappings().fetchone()

        cliente = dict(row)
        self.session.commit()

        # Historial inicial
        self.session.execute(text("""
            INSERT INTO cliente_historial_riesgo (
                cliente_id, puntaje_anterior, puntaje_nuevo,
                nivel_anterior, nivel_nuevo, motivo,
                era_pep, tenia_cripto, jurisdicciones_snap, registrado_por
            ) VALUES (
                :cliente_id, NULL, :puntaje_nuevo,
                NULL, :nivel_nuevo, 'Creación de cliente',
                :era_pep, :tenia_cripto, :jurisdicciones_snap, :registrado_por
            )
        """), {
            "cliente_id": cliente["id"],
            "puntaje_nuevo": puntaje,
            "nivel_nuevo": nivel,
            "era_pep": data.es_pep,
            "tenia_cripto": data.exposicion_cripto,
            "jurisdicciones_snap": data.jurisdicciones or [],
            "registrado_por": data.creado_por,
        })
        self.session.commit()

        self._auditar("CREATE", cliente["id"], None, {
            "razon_social": data.razon_social,
            "nit": data.nit,
            "estado": data.estado,
        }, data.creado_por)

        return cliente

    def get_by_id(self, cliente_id: int) -> Optional[dict]:
        row = self.session.execute(text("""
            SELECT * FROM clientes WHERE id = :id
        """), {"id": cliente_id}).mappings().fetchone()
        if not row:
            return None
        cliente = dict(row)
        cliente["contratos"] = self.get_contratos(cliente_id)
        cliente["personas"] = self.get_personas(cliente_id)
        return cliente

    def get_lista(
        self,
        estado: Optional[str] = None,
        nivel_riesgo: Optional[str] = None,
        empresa_grupo: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list:
        conditions = ["1=1"]
        params: dict = {}

        if estado and estado != "Todos":
            conditions.append("c.estado = :estado")
            params["estado"] = estado
        if nivel_riesgo and nivel_riesgo != "Todos":
            conditions.append("c.nivel_riesgo = :nivel_riesgo")
            params["nivel_riesgo"] = nivel_riesgo
        if search:
            conditions.append(
                "(LOWER(c.razon_social) LIKE :search OR c.nit LIKE :search)"
            )
            params["search"] = f"%{search.lower()}%"

        where = " AND ".join(conditions)

        if empresa_grupo and empresa_grupo != "Todos":
            params["empresa_grupo"] = empresa_grupo
            query = f"""
                SELECT DISTINCT c.*
                FROM clientes c
                JOIN cliente_contratos cc ON cc.cliente_id = c.id
                    AND cc.empresa_grupo = :empresa_grupo
                WHERE {where}
                ORDER BY c.razon_social
            """
        else:
            query = f"""
                SELECT c.*
                FROM clientes c
                WHERE {where}
                ORDER BY c.razon_social
            """

        rows = self.session.execute(text(query), params).mappings().fetchall()
        return [dict(r) for r in rows]

    def actualizar(self, cliente_id: int, data, usuario: str) -> dict:
        from db.models import ClienteUpdate
        if not isinstance(data, ClienteUpdate):
            from db.models import ClienteUpdate as _M
            data = _M(**data)

        anterior = self.session.execute(text("""
            SELECT * FROM clientes WHERE id = :id
        """), {"id": cliente_id}).mappings().fetchone()
        if not anterior:
            raise ValueError(f"Cliente {cliente_id} no encontrado")
        ant = dict(anterior)

        campos = data.model_dump(exclude_none=True)
        if not campos:
            return ant

        # Recalcular puntaje con valores actuales + cambios
        es_pep = campos.get("es_pep", ant["es_pep"])
        exposicion_cripto = campos.get("exposicion_cripto", ant["exposicion_cripto"])
        crypto_friendly = campos.get("crypto_friendly", ant["crypto_friendly"])
        jurisdicciones = campos.get("jurisdicciones", ant["jurisdicciones"] or [])
        en_listas = campos.get("en_listas_restriccion", ant["en_listas_restriccion"])
        sin_firma = self._tiene_contratos_sin_firma(cliente_id)

        nuevo_puntaje = self._calcular_puntaje(
            es_pep=es_pep,
            exposicion_cripto=exposicion_cripto,
            crypto_friendly=crypto_friendly,
            jurisdicciones=jurisdicciones,
            en_listas_restriccion=en_listas,
            contratos_sin_firma=sin_firma,
        )
        nuevo_nivel = self._nivel_desde_puntaje(nuevo_puntaje)

        campos["puntaje_riesgo"] = nuevo_puntaje
        campos["nivel_riesgo"] = nuevo_nivel
        campos["fecha_ultima_calificacion"] = date.today()
        if nuevo_nivel != "Sin calificar":
            campos["proxima_revision"] = self._proxima_revision(nuevo_nivel)

        set_parts = ", ".join(f"{k} = :{k}" for k in campos)
        params = dict(campos)
        params["id"] = cliente_id

        row = self.session.execute(text(f"""
            UPDATE clientes SET {set_parts}
            WHERE id = :id
            RETURNING *
        """), params).mappings().fetchone()
        self.session.commit()
        nuevo = dict(row)

        # Registrar en historial si cambió puntaje
        if nuevo_puntaje != ant.get("puntaje_riesgo") or nuevo_nivel != ant.get("nivel_riesgo"):
            self.session.execute(text("""
                INSERT INTO cliente_historial_riesgo (
                    cliente_id, puntaje_anterior, puntaje_nuevo,
                    nivel_anterior, nivel_nuevo, motivo,
                    era_pep, tenia_cripto, jurisdicciones_snap, registrado_por
                ) VALUES (
                    :cliente_id, :puntaje_anterior, :puntaje_nuevo,
                    :nivel_anterior, :nivel_nuevo, 'Actualización de datos',
                    :era_pep, :tenia_cripto, :jurisdicciones_snap, :registrado_por
                )
            """), {
                "cliente_id": cliente_id,
                "puntaje_anterior": ant.get("puntaje_riesgo"),
                "puntaje_nuevo": nuevo_puntaje,
                "nivel_anterior": ant.get("nivel_riesgo"),
                "nivel_nuevo": nuevo_nivel,
                "era_pep": es_pep,
                "tenia_cripto": exposicion_cripto,
                "jurisdicciones_snap": jurisdicciones,
                "registrado_por": usuario,
            })
            self.session.commit()

        self._auditar("UPDATE", cliente_id, ant, campos, usuario)
        return nuevo

    def cambiar_estado(self, cliente_id: int, nuevo_estado: str, usuario: str) -> bool:
        ant = self.session.execute(text("""
            SELECT estado FROM clientes WHERE id = :id
        """), {"id": cliente_id}).mappings().fetchone()
        if not ant:
            return False
        self.session.execute(text("""
            UPDATE clientes SET estado = :estado WHERE id = :id
        """), {"estado": nuevo_estado, "id": cliente_id})
        self.session.commit()
        self._auditar("UPDATE", cliente_id,
                      {"estado": ant["estado"]},
                      {"estado": nuevo_estado},
                      usuario)
        return True

    def get_stats(self) -> dict:
        from datetime import date as _date
        hoy = _date.today()
        en_30d = hoy + timedelta(days=30)

        row = self.session.execute(text("""
            SELECT
                COUNT(*)                                                    AS total,
                COUNT(*) FILTER (WHERE estado = 'Prospecto')               AS prospectos,
                COUNT(*) FILTER (WHERE estado = 'Activo')                  AS activos,
                COUNT(*) FILTER (WHERE estado = 'Suspendido')              AS suspendidos,
                COUNT(*) FILTER (WHERE estado = 'Terminado')               AS terminados,
                COUNT(*) FILTER (WHERE nivel_riesgo = 'Bajo')              AS riesgo_bajo,
                COUNT(*) FILTER (WHERE nivel_riesgo = 'Medio')             AS riesgo_medio,
                COUNT(*) FILTER (WHERE nivel_riesgo = 'Alto')              AS riesgo_alto,
                COUNT(*) FILTER (WHERE nivel_riesgo = 'Muy Alto')          AS riesgo_muy_alto,
                COUNT(*) FILTER (WHERE nivel_riesgo = 'Sin calificar')     AS riesgo_sin_calificar,
                COUNT(*) FILTER (WHERE es_pep = 1 AND estado = 'Activo')   AS peps_activos,
                COUNT(*) FILTER (WHERE en_listas_restriccion = 1)          AS en_listas
            FROM clientes
        """), {}).mappings().fetchone()

        proximas = self.session.execute(text("""
            SELECT COUNT(*) FROM clientes
            WHERE proxima_revision <= :fecha
              AND estado IN ('Activo','Suspendido')
        """), {"fecha": en_30d}).scalar() or 0

        contratos_30d = self.session.execute(text("""
            SELECT COUNT(*) FROM cliente_contratos
            WHERE fecha_vencimiento <= :fecha
              AND estado = 'Activo'
        """), {"fecha": en_30d}).scalar() or 0

        return {
            "total": int(row["total"]),
            "prospectos": int(row["prospectos"]),
            "activos": int(row["activos"]),
            "suspendidos": int(row["suspendidos"]),
            "terminados": int(row["terminados"]),
            "riesgo_bajo": int(row["riesgo_bajo"]),
            "riesgo_medio": int(row["riesgo_medio"]),
            "riesgo_alto": int(row["riesgo_alto"]),
            "riesgo_muy_alto": int(row["riesgo_muy_alto"]),
            "riesgo_sin_calificar": int(row["riesgo_sin_calificar"]),
            "peps_activos": int(row["peps_activos"]),
            "en_listas": int(row["en_listas"]),
            "proximas_revisiones_30d": int(proximas),
            "contratos_vencimiento_30d": int(contratos_30d),
        }

    def get_ficha_completa(self, cliente_id: int) -> Optional[dict]:
        row = self.session.execute(text("""
            SELECT * FROM clientes WHERE id = :id
        """), {"id": cliente_id}).mappings().fetchone()
        if not row:
            return None
        cliente = dict(row)

        personas = self.session.execute(text("""
            SELECT * FROM cliente_personas
            WHERE cliente_id = :id AND activo = 1
            ORDER BY rol, nombre_completo
        """), {"id": cliente_id}).mappings().fetchall()
        cliente["personas"] = [dict(p) for p in personas]

        contratos = self.session.execute(text("""
            SELECT cc.*,
                   COALESCE(json_agg(cs.*) FILTER (WHERE cs.id IS NOT NULL), '[]') AS servicios
            FROM cliente_contratos cc
            LEFT JOIN contrato_servicios cs ON cs.contrato_id = cc.id
            WHERE cc.cliente_id = :id
            GROUP BY cc.id
            ORDER BY cc.empresa_grupo
        """), {"id": cliente_id}).mappings().fetchall()
        cliente["contratos"] = [dict(c) for c in contratos]

        historial = self.session.execute(text("""
            SELECT * FROM cliente_historial_riesgo
            WHERE cliente_id = :id
            ORDER BY registrado_en DESC
            LIMIT 5
        """), {"id": cliente_id}).mappings().fetchall()
        cliente["historial_riesgo"] = [dict(h) for h in historial]

        return cliente

    # ──────────────────────────────────────────────────────────
    # Personas
    # ──────────────────────────────────────────────────────────

    def agregar_persona(self, data) -> dict:
        from db.models import PersonaCreate
        if not isinstance(data, PersonaCreate):
            from db.models import PersonaCreate as _M
            data = _M(**data)

        row = self.session.execute(text("""
            INSERT INTO cliente_personas (
                cliente_id, nombre_completo, tipo_documento, numero_documento,
                nacionalidad, rol, pct_participacion, es_pep,
                en_listas_restriccion, fecha_verificacion, notas, creado_por
            ) VALUES (
                :cliente_id, :nombre_completo, :tipo_documento, :numero_documento,
                :nacionalidad, :rol, :pct_participacion, :es_pep,
                :en_listas_restriccion, :fecha_verificacion, :notas, :creado_por
            )
            RETURNING *
        """), {
            "cliente_id": data.cliente_id,
            "nombre_completo": data.nombre_completo,
            "tipo_documento": data.tipo_documento,
            "numero_documento": data.numero_documento,
            "nacionalidad": data.nacionalidad,
            "rol": data.rol,
            "pct_participacion": data.pct_participacion,
            "es_pep": data.es_pep,
            "en_listas_restriccion": data.en_listas_restriccion,
            "fecha_verificacion": data.fecha_verificacion,
            "notas": data.notas,
            "creado_por": data.creado_por,
        }).mappings().fetchone()
        self.session.commit()

        persona = dict(row)
        self._auditar("CREATE", data.cliente_id,
                      None,
                      {"persona": data.nombre_completo, "rol": data.rol},
                      data.creado_por)
        return persona

    def get_personas(self, cliente_id: int) -> list:
        rows = self.session.execute(text("""
            SELECT * FROM cliente_personas
            WHERE cliente_id = :id
            ORDER BY activo DESC, rol, nombre_completo
        """), {"id": cliente_id}).mappings().fetchall()
        return [dict(r) for r in rows]

    def actualizar_persona(self, persona_id: int, data: dict, usuario: str) -> dict:
        anterior = self.session.execute(text("""
            SELECT * FROM cliente_personas WHERE id = :id
        """), {"id": persona_id}).mappings().fetchone()
        if not anterior:
            raise ValueError(f"Persona {persona_id} no encontrada")

        campos = {k: v for k, v in data.items() if v is not None}
        if not campos:
            return dict(anterior)

        set_parts = ", ".join(f"{k} = :{k}" for k in campos)
        params = dict(campos)
        params["id"] = persona_id

        row = self.session.execute(text(f"""
            UPDATE cliente_personas SET {set_parts}
            WHERE id = :id
            RETURNING *
        """), params).mappings().fetchone()
        self.session.commit()

        self._auditar("UPDATE", anterior["cliente_id"],
                      dict(anterior), campos, usuario)
        return dict(row)

    def desactivar_persona(self, persona_id: int, usuario: str) -> bool:
        ant = self.session.execute(text("""
            SELECT cliente_id FROM cliente_personas WHERE id = :id
        """), {"id": persona_id}).mappings().fetchone()
        if not ant:
            return False
        self.session.execute(text("""
            UPDATE cliente_personas SET activo = 0 WHERE id = :id
        """), {"id": persona_id})
        self.session.commit()
        self._auditar("UPDATE", ant["cliente_id"],
                      {"persona_id": persona_id, "activo": 1},
                      {"persona_id": persona_id, "activo": 0},
                      usuario)
        return True

    # ──────────────────────────────────────────────────────────
    # Contratos
    # ──────────────────────────────────────────────────────────

    def crear_contrato(self, data) -> dict:
        from db.models import ContratoCreate
        if not isinstance(data, ContratoCreate):
            from db.models import ContratoCreate as _M
            data = _M(**data)

        existente = self.session.execute(text("""
            SELECT id FROM cliente_contratos
            WHERE cliente_id = :cliente_id AND empresa_grupo = :empresa_grupo
        """), {"cliente_id": data.cliente_id, "empresa_grupo": data.empresa_grupo}).scalar()
        if existente:
            raise ValueError(
                f"Ya existe un contrato para {data.empresa_grupo} con este cliente. "
                "Actualice el contrato existente."
            )

        row = self.session.execute(text("""
            INSERT INTO cliente_contratos (
                cliente_id, empresa_grupo, estado, fecha_inicio, fecha_vencimiento,
                contrato_firmado, fecha_firma, numero_contrato,
                contacto_operativo, email_operativo, telefono_operativo,
                contacto_compliance, email_compliance, sla_contratado,
                volumen_mensual_cop, num_transacciones_mes,
                fuente_volumen, notas, creado_por
            ) VALUES (
                :cliente_id, :empresa_grupo, :estado, :fecha_inicio, :fecha_vencimiento,
                :contrato_firmado, :fecha_firma, :numero_contrato,
                :contacto_operativo, :email_operativo, :telefono_operativo,
                :contacto_compliance, :email_compliance, :sla_contratado,
                :volumen_mensual_cop, :num_transacciones_mes,
                :fuente_volumen, :notas, :creado_por
            )
            RETURNING *
        """), {
            "cliente_id": data.cliente_id,
            "empresa_grupo": data.empresa_grupo,
            "estado": data.estado,
            "fecha_inicio": data.fecha_inicio,
            "fecha_vencimiento": data.fecha_vencimiento,
            "contrato_firmado": data.contrato_firmado,
            "fecha_firma": data.fecha_firma,
            "numero_contrato": data.numero_contrato,
            "contacto_operativo": data.contacto_operativo,
            "email_operativo": data.email_operativo,
            "telefono_operativo": data.telefono_operativo,
            "contacto_compliance": data.contacto_compliance,
            "email_compliance": data.email_compliance,
            "sla_contratado": data.sla_contratado,
            "volumen_mensual_cop": data.volumen_mensual_cop,
            "num_transacciones_mes": data.num_transacciones_mes,
            "fuente_volumen": data.fuente_volumen,
            "notas": data.notas,
            "creado_por": data.creado_por,
        }).mappings().fetchone()
        self.session.commit()

        contrato = dict(row)
        self._auditar("CREATE", data.cliente_id,
                      None,
                      {"empresa_grupo": data.empresa_grupo, "estado": data.estado},
                      data.creado_por)
        return contrato

    def actualizar_contrato(self, contrato_id: int, data: dict, usuario: str) -> dict:
        anterior = self.session.execute(text("""
            SELECT * FROM cliente_contratos WHERE id = :id
        """), {"id": contrato_id}).mappings().fetchone()
        if not anterior:
            raise ValueError(f"Contrato {contrato_id} no encontrado")

        campos = {k: v for k, v in data.items() if v is not None}
        if not campos:
            return dict(anterior)

        set_parts = ", ".join(f"{k} = :{k}" for k in campos)
        params = dict(campos)
        params["id"] = contrato_id

        row = self.session.execute(text(f"""
            UPDATE cliente_contratos SET {set_parts}
            WHERE id = :id
            RETURNING *
        """), params).mappings().fetchone()
        self.session.commit()

        self._auditar("UPDATE", anterior["cliente_id"],
                      dict(anterior), campos, usuario)
        return dict(row)

    def get_contratos(self, cliente_id: int) -> list:
        contratos = self.session.execute(text("""
            SELECT * FROM cliente_contratos
            WHERE cliente_id = :id
            ORDER BY empresa_grupo
        """), {"id": cliente_id}).mappings().fetchall()

        result = []
        for c in contratos:
            contrato = dict(c)
            servicios = self.session.execute(text("""
                SELECT * FROM contrato_servicios
                WHERE contrato_id = :cid
                ORDER BY servicio
            """), {"cid": contrato["id"]}).mappings().fetchall()
            contrato["servicios"] = [dict(s) for s in servicios]
            result.append(contrato)
        return result

    def actualizar_volumen(
        self,
        contrato_id: int,
        volumen_cop: int,
        num_transacciones: int,
        usuario: str,
    ) -> bool:
        ant = self.session.execute(text("""
            SELECT cliente_id FROM cliente_contratos WHERE id = :id
        """), {"id": contrato_id}).mappings().fetchone()
        if not ant:
            return False
        self.session.execute(text("""
            UPDATE cliente_contratos
            SET volumen_mensual_cop = :vol,
                num_transacciones_mes = :txns,
                fecha_ultimo_volumen = CURRENT_DATE,
                fuente_volumen = 'manual'
            WHERE id = :id
        """), {"vol": volumen_cop, "txns": num_transacciones, "id": contrato_id})
        self.session.commit()
        self._auditar("UPDATE", ant["cliente_id"],
                      {"contrato_id": contrato_id},
                      {"volumen_mensual_cop": volumen_cop, "num_transacciones_mes": num_transacciones},
                      usuario)
        return True

    # ──────────────────────────────────────────────────────────
    # Servicios
    # ──────────────────────────────────────────────────────────

    def agregar_servicio(self, data) -> dict:
        from db.models import ServicioCreate
        if not isinstance(data, ServicioCreate):
            from db.models import ServicioCreate as _M
            data = _M(**data)

        existente = self.session.execute(text("""
            SELECT id FROM contrato_servicios
            WHERE contrato_id = :contrato_id AND servicio = :servicio
        """), {"contrato_id": data.contrato_id, "servicio": data.servicio}).scalar()
        if existente:
            raise ValueError(
                f"El servicio '{data.servicio}' ya existe en este contrato."
            )

        row = self.session.execute(text("""
            INSERT INTO contrato_servicios (
                contrato_id, servicio, estado, fecha_activacion, notas, creado_por
            ) VALUES (
                :contrato_id, :servicio, :estado, :fecha_activacion,
                :notas, :creado_por
            )
            RETURNING *
        """), {
            "contrato_id": data.contrato_id,
            "servicio": data.servicio,
            "estado": data.estado,
            "fecha_activacion": data.fecha_activacion,
            "notas": data.notas,
            "creado_por": data.creado_por,
        }).mappings().fetchone()
        self.session.commit()
        return dict(row)

    def actualizar_servicio(self, servicio_id: int, estado: str, usuario: str) -> bool:
        ant = self.session.execute(text("""
            SELECT cs.contrato_id, cc.cliente_id
            FROM contrato_servicios cs
            JOIN cliente_contratos cc ON cc.id = cs.contrato_id
            WHERE cs.id = :id
        """), {"id": servicio_id}).mappings().fetchone()
        if not ant:
            return False

        if estado == "Terminado":
            self.session.execute(text("""
                UPDATE contrato_servicios
                SET estado = :estado, fecha_terminacion = CURRENT_DATE
                WHERE id = :id
            """), {"estado": estado, "id": servicio_id})
        else:
            self.session.execute(text("""
                UPDATE contrato_servicios SET estado = :estado WHERE id = :id
            """), {"estado": estado, "id": servicio_id})
        self.session.commit()

        self._auditar("UPDATE", ant["cliente_id"],
                      {"servicio_id": servicio_id},
                      {"estado": estado},
                      usuario)
        return True

    def get_servicios(self, contrato_id: int) -> list:
        rows = self.session.execute(text("""
            SELECT * FROM contrato_servicios
            WHERE contrato_id = :id
            ORDER BY servicio
        """), {"id": contrato_id}).mappings().fetchall()
        return [dict(r) for r in rows]

    # ──────────────────────────────────────────────────────────
    # Documentos
    # ──────────────────────────────────────────────────────────

    def crear_documento(self, data) -> int:
        from db.models import ClienteDocumentoCreate
        if not isinstance(data, ClienteDocumentoCreate):
            from db.models import ClienteDocumentoCreate as _M
            data = _M(**data)

        row = self.session.execute(text("""
            INSERT INTO cliente_documentos (
                cliente_id, contrato_id, titulo, carpeta, estado,
                formato, url, version, fecha_emision, descripcion_cambio, creado_por
            ) VALUES (
                :cliente_id, :contrato_id, :titulo, :carpeta, :estado,
                :formato, :url, :version, :fecha_emision,
                :descripcion_cambio, :creado_por
            )
            RETURNING id
        """), {
            "cliente_id": data.cliente_id,
            "contrato_id": data.contrato_id,
            "titulo": data.titulo,
            "carpeta": data.carpeta,
            "estado": data.estado,
            "formato": data.formato,
            "url": data.url,
            "version": data.version,
            "fecha_emision": data.fecha_emision,
            "descripcion_cambio": data.descripcion_cambio,
            "creado_por": data.creado_por,
        }).scalar()
        self.session.commit()

        self._auditar("CREATE", data.cliente_id,
                      None,
                      {"titulo": data.titulo, "carpeta": data.carpeta},
                      data.creado_por)
        return row

    def actualizar_documento(self, doc_id: int, data: dict, usuario: str) -> None:
        anterior = self.session.execute(text("""
            SELECT * FROM cliente_documentos WHERE id = :id
        """), {"id": doc_id}).mappings().fetchone()
        if not anterior:
            raise ValueError(f"Documento {doc_id} no encontrado")
        ant = dict(anterior)

        # Snapshot antes de actualizar
        self.session.execute(text("""
            INSERT INTO cliente_documentos_historial (
                documento_raiz_id, cliente_id, contrato_id,
                titulo, carpeta, estado, formato, url,
                version, fecha_emision, descripcion_cambio, snapshot_por
            ) VALUES (
                :doc_id, :cliente_id, :contrato_id,
                :titulo, :carpeta, :estado, :formato, :url,
                :version, :fecha_emision, :descripcion_cambio, :snapshot_por
            )
        """), {
            "doc_id": doc_id,
            "cliente_id": ant["cliente_id"],
            "contrato_id": ant["contrato_id"],
            "titulo": ant["titulo"],
            "carpeta": ant["carpeta"],
            "estado": ant["estado"],
            "formato": ant["formato"],
            "url": ant["url"],
            "version": ant["version"],
            "fecha_emision": ant["fecha_emision"],
            "descripcion_cambio": data.get("descripcion_cambio"),
            "snapshot_por": usuario,
        })

        campos = {k: v for k, v in data.items() if v is not None}
        campos["actualizado_por"] = usuario
        set_parts = ", ".join(f"{k} = :{k}" for k in campos)
        params = dict(campos)
        params["id"] = doc_id

        self.session.execute(text(f"""
            UPDATE cliente_documentos SET {set_parts} WHERE id = :id
        """), params)
        self.session.commit()

        self._auditar("UPDATE", ant["cliente_id"], ant, campos, usuario)

    def get_documentos(
        self,
        cliente_id: int,
        contrato_id: Optional[int] = None,
        carpeta: Optional[str] = None,
        estado: Optional[str] = None,
    ) -> list:
        conditions = ["cliente_id = :cliente_id", "estado != 'Archivado'"]
        params: dict = {"cliente_id": cliente_id}

        if contrato_id is not None:
            conditions.append("contrato_id = :contrato_id")
            params["contrato_id"] = contrato_id
        if carpeta:
            conditions.append("carpeta = :carpeta")
            params["carpeta"] = carpeta
        if estado and estado != "Todos":
            conditions.append("estado = :estado")
            params["estado"] = estado

        where = " AND ".join(conditions)
        rows = self.session.execute(text(f"""
            SELECT * FROM cliente_documentos
            WHERE {where}
            ORDER BY carpeta, titulo
        """), params).mappings().fetchall()
        return [dict(r) for r in rows]

    def get_historial_documento(self, doc_id: int) -> list:
        rows = self.session.execute(text("""
            SELECT * FROM cliente_documentos_historial
            WHERE documento_raiz_id = :id
            ORDER BY snapshot_at DESC
        """), {"id": doc_id}).mappings().fetchall()
        return [dict(r) for r in rows]

    def get_stats_documentos(self, cliente_id: int) -> dict:
        row = self.session.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE estado != 'Archivado')  AS total,
                COUNT(*) FILTER (WHERE estado = 'Vigente')     AS vigentes,
                COUNT(*) FILTER (WHERE estado = 'Pendiente')   AS pendientes,
                COUNT(*) FILTER (WHERE estado = 'Vencido')     AS vencidos,
                COUNT(*) FILTER (WHERE estado = 'Archivado')   AS archivados
            FROM cliente_documentos
            WHERE cliente_id = :id
        """), {"id": cliente_id}).mappings().fetchone()

        por_carpeta = self.session.execute(text("""
            SELECT
                carpeta,
                COUNT(*) FILTER (WHERE estado != 'Archivado')  AS total,
                COUNT(*) FILTER (WHERE estado = 'Vigente')     AS vigentes,
                COUNT(*) FILTER (WHERE estado = 'Pendiente')   AS pendientes,
                COUNT(*) FILTER (WHERE estado = 'Vencido')     AS vencidos
            FROM cliente_documentos
            WHERE cliente_id = :id
            GROUP BY carpeta
            ORDER BY carpeta
        """), {"id": cliente_id}).mappings().fetchall()

        return {
            "total": int(row["total"]) if row["total"] else 0,
            "vigentes": int(row["vigentes"]) if row["vigentes"] else 0,
            "pendientes": int(row["pendientes"]) if row["pendientes"] else 0,
            "vencidos": int(row["vencidos"]) if row["vencidos"] else 0,
            "archivados": int(row["archivados"]) if row["archivados"] else 0,
            "por_carpeta": [dict(r) for r in por_carpeta],
        }

    # ──────────────────────────────────────────────────────────
    # Calificación de riesgo
    # ──────────────────────────────────────────────────────────

    def calificar(self, data) -> dict:
        from db.models import CalificacionRiesgoCreate
        if not isinstance(data, CalificacionRiesgoCreate):
            from db.models import CalificacionRiesgoCreate as _M
            data = _M(**data)

        # Obtener cliente actual para snapshot
        cliente = self.session.execute(text("""
            SELECT es_pep, exposicion_cripto, jurisdicciones FROM clientes WHERE id = :id
        """), {"id": data.cliente_id}).mappings().fetchone()
        era_pep = cliente["es_pep"] if cliente else 0
        tenia_cripto = cliente["exposicion_cripto"] if cliente else 0
        jurisdicciones = list(cliente["jurisdicciones"] or []) if cliente else []

        row = self.session.execute(text("""
            INSERT INTO cliente_historial_riesgo (
                cliente_id, puntaje_anterior, puntaje_nuevo,
                nivel_anterior, nivel_nuevo, motivo, observaciones,
                era_pep, tenia_cripto, jurisdicciones_snap, registrado_por
            ) VALUES (
                :cliente_id, :puntaje_anterior, :puntaje_nuevo,
                :nivel_anterior, :nivel_nuevo, :motivo, :observaciones,
                :era_pep, :tenia_cripto, :jurisdicciones_snap, :registrado_por
            )
            RETURNING *
        """), {
            "cliente_id": data.cliente_id,
            "puntaje_anterior": data.puntaje_anterior,
            "puntaje_nuevo": data.puntaje_nuevo,
            "nivel_anterior": data.nivel_anterior,
            "nivel_nuevo": data.nivel_nuevo,
            "motivo": data.motivo,
            "observaciones": data.observaciones,
            "era_pep": era_pep,
            "tenia_cripto": tenia_cripto,
            "jurisdicciones_snap": jurisdicciones,
            "registrado_por": data.registrado_por,
        }).mappings().fetchone()

        proxima = self._proxima_revision(data.nivel_nuevo) if data.nivel_nuevo != "Sin calificar" else None

        self.session.execute(text("""
            UPDATE clientes
            SET puntaje_riesgo = :puntaje,
                nivel_riesgo = :nivel,
                fecha_ultima_calificacion = CURRENT_DATE,
                proxima_revision = :proxima
            WHERE id = :id
        """), {
            "puntaje": data.puntaje_nuevo,
            "nivel": data.nivel_nuevo,
            "proxima": proxima,
            "id": data.cliente_id,
        })
        self.session.commit()

        self._auditar("UPDATE", data.cliente_id,
                      {"nivel_riesgo": data.nivel_anterior, "puntaje_riesgo": data.puntaje_anterior},
                      {"nivel_riesgo": data.nivel_nuevo, "puntaje_riesgo": data.puntaje_nuevo},
                      data.registrado_por)
        return dict(row)

    def get_historial_riesgo(self, cliente_id: int) -> list:
        rows = self.session.execute(text("""
            SELECT * FROM cliente_historial_riesgo
            WHERE cliente_id = :id
            ORDER BY registrado_en DESC
        """), {"id": cliente_id}).mappings().fetchall()
        return [dict(r) for r in rows]
