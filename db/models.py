"""
db/models.py
Modelos de datos (Pydantic v2) para validación y serialización.
Espejo tipado de las tablas definidas en Railway + Métricas de Gestión Corporativa.
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
# ALIADO (BANKING PARTNERS)
# ─────────────────────────────────────────────────────────────

class AliadoBase(BaseModel):
    # Información básica e Identificación
    nombre_razon_social: str  = Field(..., min_length=2, max_length=200)
    nit:                 str  = Field(..., pattern=r"^\d{8,10}-\d$")  # Formato: 900123456-1
    tipo_aliado:         str
    fecha_vinculacion:   date
    estado_pipeline:     str  = "Prospecto"

    # Contacto y Ubicación
    representante_legal:  Optional[str] = None
    cargo_representante:  Optional[str] = None
    email_contacto:       Optional[EmailStr] = None
    telefono_contacto:    Optional[str] = None
    ciudad:               Optional[str] = None
    departamento_geo:     Optional[str] = None
    direccion:            Optional[str] = None

    # Métricas Comerciales
    ejecutivo_cuenta_id:         Optional[int]   = None
    segmento_negocio:            Optional[str]   = None
    volumen_estimado_mensual:    Optional[float] = 0.0

    # SARLAFT — Gestión de Riesgo
    nivel_riesgo:    str   = "Medio"
    puntaje_riesgo:  float = Field(default=0.0, ge=0.0, le=100.0)
    metodologia_riesgo: Optional[str] = None

    # Exposición Política (PEP)
    es_pep:           bool = False
    descripcion_pep:  Optional[str] = None
    vinculo_pep:      Optional[str] = None

    # Revisiones Periódicas
    estado_sarlaft:         str = "Pendiente"
    fecha_ultima_revision:  Optional[date] = None
    fecha_proxima_revision: Optional[date] = None
    frecuencia_revision:    str = "Anual"
    oficial_compliance_id:  Optional[int] = None

    # Listas Restrictivas (Compliance Checks)
    listas_verificadas:         bool = False
    fecha_verificacion_listas:  Optional[date] = None
    resultado_listas:           str  = "Sin coincidencias"
    lista_ofac_ok:              bool = False
    lista_onu_ok:               bool = False
    lista_ue_ok:                bool = False
    lista_local_ok:             bool = False

    # Debida Diligencia
    estado_due_diligence:   str  = "Pendiente"
    fecha_due_diligence:    Optional[date] = None
    nivel_due_diligence:    str  = "Básico"

    # Gestión Documental
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

    # ── NUEVAS MÉTRICAS DE GESTIÓN CORPORATIVA (RELATIONSHIP STATUS) ──
    estado_hbpocorp:      str = "Sin relación"
    estado_adamo:         str = "Sin relación"
    estado_paycop:        str = "Sin relación"
    
    # Perfil Operativo (Banking Capabilities)
    crypto_friendly:      bool = False
    adult_friendly:       bool = False
    permite_monetizacion: bool = False
    permite_dispersion:   bool = False
    
    # Detalle de Operación
    monedas_soportadas:   Optional[str] = None
    clientes_vinculados:  Optional[str] = None
    volumen_real_mensual: Optional[str] = None
    
    # Trazabilidad de la Relación
    motivo_inactividad:   Optional[str] = None
    fecha_inicio_relacion: Optional[date] = None
    fecha_fin_relacion:    Optional[date] = None

    # Observaciones Generales
    observaciones_compliance: Optional[str] = None
    motivo_suspension:        Optional[str] = None


    # ── Validadores de enumerados ─────────────────────────────
    @field_validator("tipo_aliado")
    @classmethod
    def _check_tipo_aliado(cls, v: str) -> str:
        validos = {"Banking Partner", "Aliado Estratégico",
                   "Corresponsal Bancario", "Proveedor de Servicios"}
        if v not in validos:
            raise ValueError(f"tipo_aliado inválido. Opciones: {sorted(validos)}")
        return v

    @field_validator("nivel_riesgo")
    @classmethod
    def _check_nivel_riesgo(cls, v: str) -> str:
        validos = {"Bajo", "Medio", "Alto", "Muy Alto"}
        if v not in validos:
            raise ValueError(f"nivel_riesgo inválido. Opciones: {sorted(validos)}")
        return v

    @field_validator("estado_sarlaft")
    @classmethod
    def _check_estado_sarlaft(cls, v: str) -> str:
        validos = {"Al Día", "Pendiente", "En Revisión", "Vencido"}
        if v not in validos:
            raise ValueError(f"estado_sarlaft inválido. Opciones: {sorted(validos)}")
        return v

    @field_validator("estado_pipeline")
    @classmethod
    def _check_estado_pipeline(cls, v: str) -> str:
        validos = {"Prospecto", "En Calificación", "Onboarding",
                   "Activo", "Suspendido", "Terminado"}
        if v not in validos:
            raise ValueError(f"estado_pipeline inválido. Opciones: {sorted(validos)}")
        return v

    @field_validator("estado_due_diligence")
    @classmethod
    def _check_estado_dd(cls, v: str) -> str:
        validos = {"Pendiente", "En Proceso", "Completado", "Rechazado"}
        if v not in validos:
            raise ValueError(f"estado_due_diligence inválido. Opciones: {sorted(validos)}")
        return v

    @field_validator("estado_hbpocorp", "estado_adamo", "estado_paycop")
    @classmethod
    def _check_estado_empresa(cls, v: str) -> str:
        validos = {"Activo", "Inactivo", "Sin relación"}
        if v not in validos:
            raise ValueError(f"Estado de empresa inválido. Opciones: {sorted(validos)}")
        return v

    # ── Validación cruzada de fechas ──────────────────────────
    @model_validator(mode="after")
    def _check_fechas_revision(self) -> "AliadoBase":
        fu = self.fecha_ultima_revision
        fp = self.fecha_proxima_revision
        if fu and fp and fp < fu:
            raise ValueError(
                "fecha_proxima_revision no puede ser anterior a fecha_ultima_revision."
            )
        return self

    # ── Escalado preventivo de riesgo por capacidades operativas ─
    @model_validator(mode="after")
    def _escalar_riesgo_operativo(self) -> "AliadoBase":
        """
        Sube preventivamente el nivel_riesgo si el perfil operativo
        del partner incluye actividades de alto riesgo regulatorio
        (crypto / adult content), conforme criterios SARLAFT GAFI.
        El puntaje_riesgo nunca baja al usuario; solo escala hacia arriba.
        """
        _escala = ["Bajo", "Medio", "Alto", "Muy Alto"]
        nivel_actual = self.nivel_riesgo
        nivel_minimo = nivel_actual  # por defecto no cambia

        if self.crypto_friendly and self.adult_friendly:
            nivel_minimo = "Muy Alto"
        elif self.crypto_friendly:
            nivel_minimo = "Alto"
        elif self.adult_friendly:
            nivel_minimo = "Alto"

        if _escala.index(nivel_minimo) > _escala.index(nivel_actual):
            self.nivel_riesgo = nivel_minimo

        return self


class AliadoCreate(AliadoBase):
    """Modelo para crear un nuevo aliado."""
    pass


class AliadoUpdate(BaseModel):
    """Modelo para actualizar un aliado (campos opcionales)."""
    nombre_razon_social:             Optional[str]   = None
    tipo_aliado:                     Optional[str]   = None
    estado_pipeline:                 Optional[str]   = None
    nivel_riesgo:                    Optional[str]   = None
    es_pep:                          Optional[bool]  = None
    estado_sarlaft:                  Optional[str]   = None
    
    # Nuevas métricas de gestión para actualización
    estado_hbpocorp:      Optional[str] = None
    estado_adamo:         Optional[str] = None
    estado_paycop:        Optional[str] = None
    crypto_friendly:      Optional[bool] = None
    adult_friendly:       Optional[bool] = None
    permite_monetizacion: Optional[bool] = None
    permite_dispersion:   Optional[bool] = None
    monedas_soportadas:   Optional[str] = None
    clientes_vinculados:  Optional[str] = None
    volumen_real_mensual: Optional[str] = None
    motivo_inactividad:   Optional[str] = None
    fecha_inicio_relacion: Optional[date] = None
    fecha_fin_relacion:    Optional[date] = None

    actualizado_por:                 Optional[int]   = None


class AliadoOut(AliadoBase):
    """Modelo de salida completo."""
    id:             int
    creado_por:     Optional[int]     = None
    actualizado_por: Optional[int]    = None
    created_at:     datetime
    updated_at:     datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────
# AUDITORÍA Y LOGS
# ─────────────────────────────────────────────────────────────

class AuditoriaOut(BaseModel):
    id:                 int
    usuario_id:         Optional[int] = None
    username:           str
    accion:             str
    entidad:            str
    entidad_id:         Optional[int] = None
    descripcion:        str
    resultado:          str
    created_at:         datetime

    model_config = {"from_attributes": True}