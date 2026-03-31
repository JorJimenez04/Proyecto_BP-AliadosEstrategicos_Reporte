"""
db/models.py
Modelos de datos (Pydantic v2) para validación y serialización.
Espejo tipado de las tablas definidas en 001_initial_schema.sql.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ─────────────────────────────────────────────────────────────
# USUARIO
# ─────────────────────────────────────────────────────────────

class UsuarioBase(BaseModel):
    username: str         = Field(..., min_length=3, max_length=50)
    nombre_completo: str  = Field(..., min_length=2, max_length=150)
    email: EmailStr
    rol: str              = Field(default="consulta")
    departamento: Optional[str] = None
    activo: bool          = True

    @field_validator("rol")
    @classmethod
    def validar_rol(cls, v: str) -> str:
        roles_validos = {"admin", "compliance", "comercial", "consulta"}
        if v not in roles_validos:
            raise ValueError(f"Rol inválido. Opciones: {roles_validos}")
        return v


class UsuarioCreate(UsuarioBase):
    """Modelo para crear un nuevo usuario (incluye password en texto plano)."""
    password: str = Field(..., min_length=8)


class UsuarioUpdate(BaseModel):
    """Modelo para actualizar un usuario (todos los campos son opcionales)."""
    nombre_completo: Optional[str] = None
    email:           Optional[EmailStr] = None
    rol:             Optional[str] = None
    departamento:    Optional[str] = None
    activo:          Optional[bool] = None


class UsuarioOut(UsuarioBase):
    """Modelo de salida: NUNCA incluye password_hash."""
    id: int
    ultimo_acceso: Optional[datetime] = None
    created_at:   datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────
# ALIADO
# ─────────────────────────────────────────────────────────────

class AliadoBase(BaseModel):
    # Información básica
    nombre_razon_social: str  = Field(..., min_length=2, max_length=200)
    nit:                 str  = Field(..., pattern=r"^\d{8,10}-\d$")  # Formato: 900123456-1
    tipo_aliado:         str
    fecha_vinculacion:   date
    estado_pipeline:     str  = "Prospecto"

    # Contacto
    representante_legal:  Optional[str] = None
    cargo_representante:  Optional[str] = None
    email_contacto:       Optional[EmailStr] = None
    telefono_contacto:    Optional[str] = None
    ciudad:               Optional[str] = None
    departamento_geo:     Optional[str] = None
    direccion:            Optional[str] = None

    # Comercial
    ejecutivo_cuenta_id:         Optional[int]   = None
    segmento_negocio:            Optional[str]   = None
    volumen_estimado_mensual:    Optional[float] = 0.0

    # SARLAFT — Riesgo
    nivel_riesgo:    str   = "Medio"
    puntaje_riesgo:  float = Field(default=0.0, ge=0.0, le=100.0)
    metodologia_riesgo: Optional[str] = None

    # PEP
    es_pep:           bool = False
    descripcion_pep:  Optional[str] = None
    vinculo_pep:      Optional[str] = None

    # Revisiones SARLAFT
    estado_sarlaft:         str = "Pendiente"
    fecha_ultima_revision:  Optional[date] = None
    fecha_proxima_revision: Optional[date] = None
    frecuencia_revision:    str = "Anual"
    oficial_compliance_id:  Optional[int] = None

    # Listas restrictivas
    listas_verificadas:         bool = False
    fecha_verificacion_listas:  Optional[date] = None
    resultado_listas:           str  = "Sin coincidencias"
    lista_ofac_ok:              bool = False
    lista_onu_ok:               bool = False
    lista_ue_ok:                bool = False
    lista_local_ok:             bool = False

    # Due Diligence
    estado_due_diligence:   str  = "Pendiente"
    fecha_due_diligence:    Optional[date] = None
    nivel_due_diligence:    str  = "Básico"

    # Documentación
    rut_recibido:                    bool = False
    camara_comercio_recibida:        bool = False
    fecha_vencimiento_camara:        Optional[date] = None
    estados_financieros_recibidos:   bool = False
    formulario_vinculacion_recibido: bool = False
    contrato_firmado:                bool = False
    fecha_firma_contrato:            Optional[date] = None
    fecha_vencimiento_contrato:      Optional[date] = None
    poliza_recibida:                 bool = False
    fecha_vencimiento_poliza:        Optional[date] = None

    # Observaciones
    observaciones_compliance: Optional[str] = None
    motivo_suspension:        Optional[str] = None


    # ── Validadores de enumerados ─────────────────────────────
    @field_validator("tipo_aliado")
    @classmethod
    def _check_tipo_aliado(cls, v: str) -> str:
        validos = {"Banking Partner", "Aliado Estratégico",
                   "Corresponsal Bancario", "Proveedor de Servicios"}
        if v not in validos:
            raise ValueError(f"tipo_aliado inválido. Debe ser uno de: {sorted(validos)}")
        return v

    @field_validator("nivel_riesgo")
    @classmethod
    def _check_nivel_riesgo(cls, v: str) -> str:
        validos = {"Bajo", "Medio", "Alto", "Muy Alto"}
        if v not in validos:
            raise ValueError(f"nivel_riesgo inválido. Debe ser uno de: {sorted(validos)}")
        return v

    @field_validator("estado_sarlaft")
    @classmethod
    def _check_estado_sarlaft(cls, v: str) -> str:
        validos = {"Al Día", "Pendiente", "En Revisión", "Vencido"}
        if v not in validos:
            raise ValueError(f"estado_sarlaft inválido. Debe ser uno de: {sorted(validos)}")
        return v

    @field_validator("estado_pipeline")
    @classmethod
    def _check_estado_pipeline(cls, v: str) -> str:
        validos = {"Prospecto", "En Calificación", "Onboarding",
                   "Activo", "Suspendido", "Terminado"}
        if v not in validos:
            raise ValueError(f"estado_pipeline inválido. Debe ser uno de: {sorted(validos)}")
        return v

    @field_validator("estado_due_diligence")
    @classmethod
    def _check_estado_dd(cls, v: str) -> str:
        validos = {"Pendiente", "En Proceso", "Completado", "Rechazado"}
        if v not in validos:
            raise ValueError(f"estado_due_diligence inválido. Debe ser uno de: {sorted(validos)}")
        return v

    @field_validator("frecuencia_revision")
    @classmethod
    def _check_frecuencia(cls, v: str) -> str:
        validos = {"Anual", "Semestral", "Trimestral", "Mensual"}
        if v not in validos:
            raise ValueError(f"frecuencia_revision inválida. Debe ser una de: {sorted(validos)}")
        return v

    # ── Validación cruzada de fechas (SARLAFT) ────────────────
    @model_validator(mode="after")
    def _check_fechas_revision(self) -> "AliadoBase":
        """
        La fecha de próxima revisión no puede ser anterior
        a la fecha de última revisión (lógica SARLAFT / EBR).
        """
        fu = self.fecha_ultima_revision
        fp = self.fecha_proxima_revision
        if fu and fp and fp < fu:
            raise ValueError(
                "fecha_proxima_revision no puede ser anterior a fecha_ultima_revision. "
                f"Última revisión: {fu} — Próxima revisión propuesta: {fp}"
            )
        return self


class AliadoCreate(AliadoBase):
    """Modelo para crear un nuevo aliado."""
    pass


class AliadoUpdate(BaseModel):
    """Modelo para actualizar un aliado (todos los campos opcionales)."""
    nombre_razon_social:             Optional[str]   = None
    tipo_aliado:                     Optional[str]   = None
    estado_pipeline:                 Optional[str]   = None
    representante_legal:             Optional[str]   = None
    email_contacto:                  Optional[EmailStr] = None
    telefono_contacto:               Optional[str]   = None
    ciudad:                          Optional[str]   = None
    nivel_riesgo:                    Optional[str]   = None
    puntaje_riesgo:                  Optional[float] = Field(default=None, ge=0.0, le=100.0)
    es_pep:                          Optional[bool]  = None
    estado_sarlaft:                  Optional[str]   = None
    fecha_ultima_revision:           Optional[date]  = None
    fecha_proxima_revision:          Optional[date]  = None
    listas_verificadas:              Optional[bool]  = None
    resultado_listas:                Optional[str]   = None
    estado_due_diligence:            Optional[str]   = None
    rut_recibido:                    Optional[bool]  = None
    camara_comercio_recibida:        Optional[bool]  = None
    formulario_vinculacion_recibido: Optional[bool]  = None
    contrato_firmado:                Optional[bool]  = None
    observaciones_compliance:        Optional[str]   = None
    motivo_suspension:               Optional[str]   = None
    actualizado_por:                 Optional[int]   = None

    @model_validator(mode="after")
    def _check_fechas_revision(self) -> "AliadoUpdate":
        fu = self.fecha_ultima_revision
        fp = self.fecha_proxima_revision
        if fu and fp and fp < fu:
            raise ValueError(
                "fecha_proxima_revision no puede ser anterior a fecha_ultima_revision. "
                f"Última revisión: {fu} — Próxima revisión propuesta: {fp}"
            )
        return self


class AliadoOut(AliadoBase):
    """Modelo de salida completo."""
    id:             int
    creado_por:     Optional[int]     = None
    actualizado_por: Optional[int]    = None
    created_at:     datetime
    updated_at:     datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────
# HISTORIAL DE ESTADOS (Pipeline)
# ─────────────────────────────────────────────────────────────

class HistorialEstadoOut(BaseModel):
    id:              int
    aliado_id:       int
    estado_anterior: Optional[str] = None
    estado_nuevo:    str
    motivo:          Optional[str] = None
    cambiado_por:    int
    changed_at:      datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────
# REVISIÓN SARLAFT
# ─────────────────────────────────────────────────────────────

class RevisionSarlaftCreate(BaseModel):
    aliado_id:          int
    fecha_revision:     date
    oficial_id:         int
    nivel_riesgo_nuevo: str
    puntaje_nuevo:      float = Field(ge=0.0, le=100.0)
    hallazgos:          Optional[str] = None
    acciones_requeridas: Optional[str] = None
    proxima_revision:   Optional[date] = None


class RevisionSarlaftOut(RevisionSarlaftCreate):
    id:                 int
    nivel_riesgo_previo: Optional[str]  = None
    puntaje_previo:      Optional[float] = None
    aprobado:           bool = False
    aprobado_por:       Optional[int] = None
    created_at:         datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────
# LOG DE AUDITORÍA
# ─────────────────────────────────────────────────────────────

class AuditoriaOut(BaseModel):
    id:                int
    usuario_id:        Optional[int] = None
    username:          str
    accion:            str
    entidad:           str
    entidad_id:        Optional[int] = None
    descripcion:       str
    valores_anteriores: Optional[str] = None
    valores_nuevos:    Optional[str]  = None
    ip_address:        Optional[str]  = None
    resultado:         str
    created_at:        datetime

    model_config = {"from_attributes": True}
