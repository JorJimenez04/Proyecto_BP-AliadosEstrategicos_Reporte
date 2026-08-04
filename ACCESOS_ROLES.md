# 🔐 Estructura de Accesos — AdamoServices Partner Manager

> Documento de referencia oficial de roles, permisos y módulos del sistema.  
> Basado en `config/settings.py` · Actualizado: mayo 2026

---

## 1. Roles del Sistema

### Roles Canónicos (activos)

| Rol | Identificador | Descripción |
|-----|---------------|-------------|
| **Super Admin** | `super_admin` | Acceso total sin restricciones. Gestión de usuarios y configuración crítica. |
| **Compliance** | `compliance` | Compliance 360. Acceso a todos los módulos operativos, SARLAFT, documentos y cripto. |
| **Manager de Operaciones** | `manager_ops` | Gestión de pagos y recursos humanos. Edita partners y KPIs. Ve equipos de agentes. |
| **Manager Comercial** | `manager_comercial` | Acceso a Gestión de Alianzas y Centro Documental (carpetas comerciales). |
| **Manager Legal** | `manager_legal` | Acceso a Gestión de Alianzas y Centro Documental (carpetas legales y empresariales). |
| **Agente** | `agente` | Senior y Junior. Solo puede ver su propio perfil. Sin acceso a módulos de gestión. |
| **CIC** | `cic` | Comercial Inteligencia Comercial. Replica exactamente los permisos del rol legacy `comercial`. |

### Roles Legacy (aliases — compatibilidad hacia atrás)

| Rol | Identificador | Equivalente Actual |
|-----|---------------|--------------------|
| Admin | `admin` | `super_admin` |
| Comercial | `comercial` | `manager_comercial` / parcial |
| Agente KYC | `agente_kyc` | Acceso específico a campos SARLAFT |
| Agente Operativo | `agente_operativo` | Acceso de edición en partners |
| Consulta | `consulta` | Lectura en Centro Documental |

---

## 2. Módulos y Permisos por Rol

### 📌 Visibilidad de Módulos en el Sidebar

| Módulo | `super_admin` | `compliance` | `manager_ops` | `manager_comercial` | `manager_legal` | `agente` |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|
| 🤝 Gestión de Alianzas | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| 📋 Log de Auditoría | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| 👥 Gestión de Agentes | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| 📚 Centro Documental | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| 🛡️ Cripto Compliance | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| 👤 Mi Perfil | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 🏢 Equipos Operativos (sidebar) | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

### Módulos visibles para `cic`

| Módulo | `cic` | Nota |
|--------|:---:|------|
| Infraestructura Financiera | ✅ | Ver, crear y editar partners · registrar KPIs |
| Centro Documental | ✅ | Solo lectura, carpetas acotadas (ver sección 4.1) |
| Gestión de Clientes | ✅ | |
| Gestión de Agentes | ✅ | **Solo lectura** — no crea ni edita colaboradores |
| Equipos Operativos (sidebar) | ✅ | Deriva de `CAN_VIEW_AGENTES` |
| Log de Auditoría | ❌ | Expone la actividad de todos los usuarios |
| Screening de Cumplimiento | ❌ | Compliance |
| Cripto Compliance | ❌ | Compliance |
| Bandeja de Cumplimiento | ❌ | Compliance |

---

## 3. Permisos Detallados por Acción

### 🤝 Gestión de Alianzas (Partners)

| Acción | `super_admin` | `compliance` | `manager_ops` | `manager_comercial` | `manager_legal` | `agente` |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|
| Ver listado de aliados | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Crear nuevo partner | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Editar campos operativos | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Editar campos SARLAFT / PEP | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Editar nivel de riesgo | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Editar jurisdicciones | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Editar compliance (aprobaciones) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Registrar KPIs de gestión | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Eliminar partner | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

### 📋 Log de Auditoría

| Acción | `super_admin` | `compliance` | otros |
|--------|:---:|:---:|:---:|
| Ver log completo | ✅ | ✅ | ❌ |
| Filtrar por usuario / acción / fecha | ✅ | ✅ | ❌ |

### 👥 Gestión de Agentes

| Acción | `super_admin` | `compliance` | `manager_ops` | otros |
|--------|:---:|:---:|:---:|:---:|
| Ver listado de equipos completo | ✅ | ✅ | ✅ | ❌ |
| Ver perfil de cualquier agente | ✅ | ✅ | ✅ | ❌ |
| Ver su propio perfil | ✅ | ✅ | ✅ | ✅ |
| Crear / editar agente | ✅ | ✅ | ✅ | ❌ |
| Eliminar agente | ✅ | ❌ | ❌ | ❌ |

### 📚 Centro Documental

| Acción | `super_admin` | `compliance` | `manager_comercial` | `manager_legal` | `consulta` | otros |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|
| Ver todas las carpetas | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Ver carpeta Empresariales | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Ver Contratos / Actas / Governanza | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Crear / editar documentos | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Eliminar documentos | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

### 🛡️ Cripto Compliance

| Acción | `super_admin` | `compliance` | otros |
|--------|:---:|:---:|:---:|
| Acceder al módulo | ✅ | ✅ | ❌ |
| Ver clientes cripto | ✅ | ✅ | ❌ |
| Crear / editar clientes cripto | ✅ | ✅ | ❌ |

### ⚙️ Administración del Sistema

| Acción | `super_admin` | `admin` | otros |
|--------|:---:|:---:|:---:|
| Crear / editar / desactivar usuarios | ✅ | ✅ | ❌ |
| Eliminar cualquier registro | ✅ | ✅ | ❌ |

---

## 4. Roles Legacy — Tabla de Permisos

> Los roles legacy siguen activos para compatibilidad con registros existentes.

| Módulo | `admin` | `comercial` | `agente_kyc` | `agente_operativo` | `consulta` |
|--------|:---:|:---:|:---:|:---:|:---:|
| 🤝 Gestión de Alianzas (ver) | ✅ | ✅ | ❌ | ❌ | ❌ |
| 🤝 Partners (editar operativo) | ✅ | ✅ | ✅ | ✅ | ❌ |
| 🤝 Partners (SARLAFT / PEP) | ❌ | ❌ | ✅ | ❌ | ❌ |
| 🤝 Partners (crear) | ✅ | ✅ | ❌ | ❌ | ❌ |
| 🤝 Partners (eliminar) | ✅ | ❌ | ❌ | ❌ | ❌ |
| 📋 Log de Auditoría | ✅ | ❌ | ❌ | ❌ | ❌ |
| 👥 Gestión de Agentes | ✅ | ❌ | ❌ | ❌ | ❌ |
| 📚 Centro Documental (ver) | ✅ | ✅ | ❌ | ❌ | ✅ |
| 📚 Centro Documental (editar) | ✅ | ❌ | ❌ | ❌ | ❌ |
| 🛡️ Cripto Compliance | ✅ | ❌ | ❌ | ❌ | ❌ |
| Registrar KPIs | ✅ | ✅ | ❌ | ❌ | ❌ |

---

## 4.1 Rol CIC — Paridad con `comercial`

El rol `cic` (Comercial Inteligencia Comercial) se creó como **clon exacto** del rol legacy
`comercial`. Pertenece a los mismos conjuntos de permiso en `config/settings.py`:

| Conjunto de permiso | `comercial` | `cic` |
|---------------------|:---:|:---:|
| `CAN_VIEW_ALIANZAS` | ✅ | ✅ |
| `CAN_EDIT_PARTNERS` | ✅ | ✅ |
| `CAN_CREATE_PARTNERS` | ✅ | ✅ |
| `CAN_REGISTER_KPIS` | ✅ | ✅ |
| `CAN_VIEW_DOCS` | ✅ | ✅ |
| `CAN_VIEW_AGENTES` | ❌ | ✅ **(divergencia)** |
| `CAN_DELETE_PARTNERS` | ❌ | ❌ |
| `CAN_EDIT_SARLAFT` | ❌ | ❌ |
| `CAN_EDIT_COMPLIANCE` | ❌ | ❌ |
| `CAN_EDIT_JURISDICTIONS` | ❌ | ❌ |
| `CAN_VIEW_AUDIT` | ❌ | ❌ |
| `CAN_EDIT_AGENTES` | ❌ | ❌ |
| `CAN_EDIT_DOCS` | ❌ | ❌ |
| `CAN_VIEW_CRYPTO` | ❌ | ❌ |
| `CAN_MANAGE_USERS` | ❌ | ❌ |
| Gestión de Clientes (sidebar + router) | ✅ | ✅ |

### Divergencias deliberadas

| Conjunto | Motivo |
|----------|--------|
| `CAN_VIEW_AGENTES` | CIC necesita conocer la operación y los equipos. Acceso de **solo lectura**: no está en `CAN_EDIT_AGENTES`. |

Al separar `cic` de `comercial`, registrar la diferencia en tres sitios:
`DIVERGENCIAS` de `scripts/verify_cic_parity.py`, `_DIVERGENCIAS_CIC` de
`tests/test_smoke.py` y esta tabla. El script y el test fallan si una divergencia
no está declarada, y también si una declarada dejó de existir.

### Carpetas del Centro Documental

`cic` tiene conjunto propio (`Roles.CARPETAS_CIC`). Antes caía en el `else` de
`compliance_ui.py` y veía **todas** las carpetas, más que `manager_comercial`.

| Rol | Carpetas visibles |
|-----|-------------------|
| `cic` | Empresariales · Contratos · Actas y Formatos · Onboarding · Capacitacion · Procesos y Procedimientos · Manuales · Tecnologia |
| `manager_comercial` | Empresariales |
| `manager_legal` | Empresariales · Contratos · Actas y Formatos · Governanza |
| `manager_ops` | Empresariales · Contratos · Actas y Formatos · Capacitacion · Onboarding |

Excluidas para `cic`: **Politicas**, **Governanza** y **Matrices** — documentación
de compliance y junta directiva. Para ampliar o recortar, editar únicamente
`Roles.CARPETAS_CIC` en `config/settings.py`.

**Migración:** `db/migrations/034_rol_cic.sql` · **Seed:** `scripts/create_cic_sergio.py`

---

## 5. Pipeline de Estados de Aliados

```
Prospecto → En Calificación → Onboarding → Activo → Suspendido → Terminado
```

### Transiciones Permitidas

| Estado Actual | Puede pasar a |
|---------------|---------------|
| Prospecto | En Calificación · Terminado |
| En Calificación | Onboarding · Terminado |
| Onboarding | Activo · Suspendido · Terminado |
| Activo | Suspendido · Terminado |
| Suspendido | Activo · Terminado |
| Terminado | — (estado final) |

---

## 6. Referencias de Código

| Constante | Archivo | Descripción |
|-----------|---------|-------------|
| `Roles.CAN_VIEW_ALIANZAS` | `config/settings.py` | Roles que ven Gestión de Alianzas |
| `Roles.CAN_VIEW_AUDIT` | `config/settings.py` | Roles que ven Log de Auditoría |
| `Roles.CAN_VIEW_AGENTES` | `config/settings.py` | Roles que ven Gestión de Agentes |
| `Roles.CAN_VIEW_DOCS` | `config/settings.py` | Roles que ven Centro Documental |
| `Roles.CAN_VIEW_CRYPTO` | `config/settings.py` | Roles que ven Cripto Compliance |
| `Roles.CAN_EDIT_PARTNERS` | `config/settings.py` | Roles que editan partners |
| `Roles.CAN_DELETE_PARTNERS` | `config/settings.py` | Roles que eliminan partners |
| `Roles.CAN_EDIT_SARLAFT` | `config/settings.py` | Roles que editan campos SARLAFT |
| `Roles.CAN_EDIT_COMPLIANCE` | `config/settings.py` | Roles que editan campos de compliance |
| `Roles.CAN_EDIT_JURISDICTIONS` | `config/settings.py` | Roles que editan jurisdicciones |
| `Roles.CAN_REGISTER_KPIS` | `config/settings.py` | Roles que registran KPIs |
| `Roles.CAN_MANAGE_USERS` | `config/settings.py` | Roles que gestionan usuarios del sistema |
| `Roles.CARPETAS_COMERCIAL` | `config/settings.py` | Carpetas visibles para rol comercial |
| `Roles.CARPETAS_LEGAL` | `config/settings.py` | Carpetas visibles para rol legal |
| `sidebar()` | `app/main.py` | Construye el menú según el rol del usuario activo |
| `main()` | `app/main.py` | Router principal — verifica rol antes de renderizar cada módulo |
