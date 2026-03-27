# 🗂️ Estructura del Proyecto — AdamoServices Partner Manager

> Aplicación web de gestión de Banking Partners y Aliados Estratégicos.  
> Stack: Python 3.10+ · Streamlit · SQLite → PostgreSQL · SQLAlchemy · Pydantic v2

---

## 📁 Árbol de archivos

```
Proyecto_PartnersStatus/
│
├── 📄 .env.example                    # Plantilla de variables de entorno (no subir .env al repo)
├── 📄 .gitignore                      # Exclusiones de Git (.env, *.db, .venv, __pycache__)
├── 📄 .dockerignore                   # Exclusiones del build Docker (*.db, .env, .venv, tests/)
├── 📄 Dockerfile                      # Imagen Docker basada en python:3.10-slim para Railway
├── 📄 entrypoint.sh                   # Script de arranque: migraciones → Streamlit (Puerto $PORT)
├── 📄 railway.toml                    # Configuración de despliegue Railway (builder, healthcheck)
├── 📄 requirements.txt                # Dependencias Python (incluye psycopg2-binary para PG)
├── 📄 README.md                       # Documentación principal del proyecto
├── 📄 ESTRUCTURA.md                   # Este archivo — mapa del proyecto
│
├── 📂 .streamlit/                     # Configuración nativa de Streamlit
│   └── 📄 config.toml                 # Tema dark AdamoServices · CSRF · anti-clickjacking · no telemetría
│
├── 📂 app/                            # Capa de presentación (Streamlit)
│   ├── 📄 __init__.py
│   ├── 📄 main.py                     # Entry point · router de páginas · CSS global · EBR dashboard
│   │                                  # sidebar() con filtros de monitoreo · page_dashboard()
│   │                                  # _kpi_bar() · _tab_pipeline() · _tab_mapa_riesgos() · _tab_alertas()
│   │
│   ├── 📂 auth/                       # Sistema de autenticación y control de acceso
│   │   ├── 📄 __init__.py
│   │   └── 📄 login.py                # Módulo de autenticación completo
│   │                                  # authenticate() — prioridad: ENV → bcrypt BD → PLACEHOLDER_HASH (dev)
│   │                                  # login_screen() — formulario st.form + rate-limiting progresivo
│   │                                  #   (delay 1-3 s + bloqueo 60 s tras 5 fallos consecutivos)
│   │                                  # require_auth() — gate: verifica session_state, llama st.stop()
│   │                                  # _get_client_ip() — X-Forwarded-For / X-Real-IP / fallback 127.0.0.1
│   │                                  # _audit_login() — registra LOGIN / LOGIN_FAIL en log_auditoria
│   │
│   ├── 📂 pages/                      # [Próximamente] Páginas como módulos independientes
│   │   └── 📄 __init__.py
│   │
│   ├── 📂 components/                 # Componentes UI reutilizables
│   │   ├── 📄 __init__.py
│   │   └── 📄 alerts.py               # Centro de Notificaciones de Compliance
│   │                                  # render_centro_notificaciones() — SARLAFT vencidas
│   │                                  # Cards con botón ⚡ Acción Rápida (re-calificación)
│   │                                  # Cards próximas revisiones 30 días · DDI (GAFI R.1/R.12)
│   │
│   └── 📂 utils/                      # Funciones auxiliares de utilidad
│       ├── 📄 __init__.py
│       └── 📄 production_check.py     # Hardening de configuración pre-arranque (GAFI R.1 / CSBF Circular 027)
│                                          # raise_if_insecure() → lanza RuntimeError (uso en código/tests)
│                                          # run_checks()        → imprime a stderr + sys.exit(1) (entrypoint.sh)
│                                          # Controles: SECRET_KEY ≥ 43 chars (token_urlsafe 256 bits)
│                                          #            ADMIN_PASSWORD ≥ 16 chars + 4 clases de caracteres
│                                          #            DATABASE_URL debe ser PostgreSQL, no SQLite
│                                          #            ADMIN_USERNAME y ADMIN_EMAIL presentes
│
├── 📂 config/                         # Configuración centralizada
│   ├── 📄 __init__.py
│   └── 📄 settings.py                 # APP_NAME · DATABASE_URL · Roles · EstadosAliado
│                                      # NivelesRiesgo · EstadosSARLAFT · TiposAliado
│
├── 📂 db/                             # Capa de datos
│   ├── 📄 __init__.py
│   ├── 📄 database.py                 # Motor SQLAlchemy · QueuePool PG / NullPool SQLite
│   │                                  # SessionLocal · init_database() · health_check()
│   ├── 📄 models.py                   # Modelos Pydantic v2 (validación y serialización)
│   │
│   ├── 📂 migrations/                 # Scripts SQL versionados
│   │   └── 📄 001_initial_schema.sql  # Esquema inicial: tablas, índices y triggers
│   │
│   └── 📂 repositories/              # Patrón Repository — CRUD desacoplado de la UI
│       ├── 📄 __init__.py
│       ├── 📄 partner_repo.py         # CRUD aliados · pipeline · EBR stats · alertas SARLAFT
│       │                              # get_lista_enriquecida · get_cobertura_due_diligence
│       │                              # get_sarlaft_vencidas · get_pep_activos
│       │                              # get_stats_tipo_aliado · get_stats_estado_sarlaft
│       │                              # get_revisiones_proximas(dias=30)
│       └── 📄 audit_repo.py           # Log de auditoría inmutable (solo escritura/lectura)
│
├── 📂 data/                           # Base de datos SQLite local (excluida del repo)
│   └── 📄 adamoservices.db            # Generada con: python -m db.database
│
└── 📂 tests/                          # Suite de pruebas
    └── 📄 __init__.py
```

---

## 🗃️ Esquema de Base de Datos

```
┌─────────────────┐     ┌──────────────────────┐
│    usuarios     │     │       aliados         │
├─────────────────┤     ├──────────────────────┤
│ id (PK)         │◄────┤ ejecutivo_cuenta_id   │
│ username        │◄────┤ oficial_compliance_id │
│ nombre_completo │◄────┤ creado_por            │
│ email           │◄────┤ actualizado_por       │
│ password_hash   │     │                      │
│ rol             │     │ — Datos generales —  │
│ departamento    │     │ nombre_razon_social   │
│ activo          │     │ nit (UNIQUE)          │
│ ultimo_acceso   │     │ tipo_aliado           │
└─────────────────┘     │ fecha_vinculacion     │
         ▲              │ estado_pipeline       │
         │              │                      │
         │              │ — SARLAFT —          │
         │              │ nivel_riesgo          │
         │              │ puntaje_riesgo        │
         │              │ es_pep                │
         │              │ estado_sarlaft         │
         │              │ fecha_ultima_revision  │
         │              │ fecha_proxima_revision │
         │              │ listas_verificadas    │
         │              │ resultado_listas       │
         │              │ estado_due_diligence  │
         │              └──────────────────────┘
         │                        │ (1 a N)
         │              ┌─────────┴────────────┐
         │              │                      │
         │    ┌─────────▼──────────┐  ┌────────▼────────────┐
         │    │ historial_estados  │  │ revisiones_sarlaft  │
         │    ├────────────────────┤  ├─────────────────────┤
         │    │ id (PK)            │  │ id (PK)             │
         │    │ aliado_id (FK)     │  │ aliado_id (FK)      │
         │    │ estado_anterior    │  │ fecha_revision       │
         │    │ estado_nuevo       │  │ oficial_id (FK)      │
         │    │ motivo             │  │ nivel_riesgo_nuevo   │
         │    │ cambiado_por (FK)──┘  │ puntaje_nuevo       │
         │    │ changed_at         │  │ hallazgos           │
         │    └────────────────────┘  │ aprobado            │
         │                            └─────────────────────┘
         │
    ┌────┴──────────────────┐
    │     log_auditoria     │
    ├───────────────────────┤
    │ id (PK)               │
    │ usuario_id (FK)       │
    │ username (denorm.)    │  ← inmutable por diseño
    │ accion                │  CREATE·UPDATE·DELETE·LOGIN·EXPORT
    │ entidad               │
    │ entidad_id            │
    │ descripcion           │
    │ valores_anteriores    │  JSON
    │ valores_nuevos        │  JSON
    │ ip_address            │
    │ resultado             │
    │ created_at            │
    └───────────────────────┘
```

---

## 🔄 Pipeline de Estados

```
  ┌───────────┐    ┌────────────────┐    ┌────────────┐
  │ Prospecto │───►│ En Calificación│───►│ Onboarding │
  └───────────┘    └────────────────┘    └────────────┘
                           │                    │
                           ▼                    ▼
                      ┌─────────┐          ┌────────┐
                      │Terminado│◄─────────│ Activo │
                      └─────────┘          └────────┘
                                               │
                                               ▼
                                         ┌───────────┐
                                         │ Suspendido│
                                         └───────────┘
```

---

## � Funcionalidades del Dashboard (EBR)

### Centro de Notificaciones (`app/components/alerts.py`)
- Banner crítico con conteo de revisiones SARLAFT vencidas (referencia CSBF / Circular 027 de 2020)
- **Cards de aliados vencidos** con nivel de riesgo, score EBR, fecha de vencimiento
- **Botón ⚡ Acción Rápida** por cada card: inicia re-calificación (`Prospecto → En Calificación`), registra auditoría automáticamente con motivo de DDI (GAFI R.1 / R.12)
- **Cards de próximas revisiones** (ventana 30 días) ordenadas por nivel de riesgo

### Barra Lateral — Filtros de Monitoreo (`sidebar()` en `main.py`)
| Filtro | Session State Key | Descripción |
|---|---|---|
| Solo Exposición PEP | `filtro_pep` | Muestra aliados con exposición política — DDI obligatoria (GAFI R.12) |
| Solo Riesgo Alto / Muy Alto | `filtro_alto` | Monitoreo Intensificado — DDI requerida (GAFI R.1) |
| Oficial de Cumplimiento | `filtro_oficial` | Filtra por oficial; lista dinámica desde tabla `usuarios` |

### KPIs del Dashboard
| Métrica | Fuente | Descripción |
|---|---|---|
| Total Partners | `get_stats_pipeline()` | Suma de todos los estados activos |
| Cobertura Due Diligence | `get_cobertura_due_diligence()` | % completados / total (excl. Terminados) |
| Alertas SARLAFT Vencidas | `get_stats_estado_sarlaft()` | Conteo de `estado_sarlaft = 'Vencido'` |
| Riesgo Alto / Muy Alto | `get_stats_riesgo()` | Suma Alto + Muy Alto |
| Sujetos PEP Activos | `get_pep_activos()` | Partners con `es_pep = 1` no Terminados |
| Exposición PEP % | Calculado | `len(pep_list) / total * 100` |
| Promedio Onboarding | Calculado | Promedio días desde `fecha_vinculacion` para estado Onboarding |

### Tabs EBR
- **🔄 Vista de Pipeline** — gráfico de barras Plotly + kanban + tabla interactiva ordenada por riesgo
- **🗺️ Mapa de Riesgos** — donut EBR + barras SARLAFT + tabla DDI aliados Alto/Muy Alto
- **🚨 Alertas de Cumplimiento** — vencidas · próximas 30d · tabla PEP con nota DDI (GAFI R.12)

---

## �👥 Roles de Acceso (RBAC)

| Rol           | Dashboard | Ver Partners | Crear/Editar | Cambiar Estado | Auditoría |
|---------------|:---------:|:------------:|:------------:|:--------------:|:---------:|
| `admin`       | ✅        | ✅           | ✅           | ✅             | ✅        |
| `compliance`  | ✅        | ✅           | ✅           | ✅             | ✅        |
| `comercial`   | ✅        | ✅           | Parcial      | Parcial        | ❌        |
| `consulta`    | ✅        | ✅           | ❌           | ❌             | ❌        |

---

## 🚀 Comandos útiles

```bash
# ── Desarrollo local ──────────────────────────────────────────
# Instalar dependencias
pip install -r requirements.txt

# Inicializar / resetear la base de datos SQLite
python -m db.database

# Ejecutar la aplicación en local
python -m streamlit run app/main.py --server.port 8501

# Verificar variables de producción (sin arrancar la app — modo CLI)
python app/utils/production_check.py

# Validar desde Python (lanza RuntimeError si falla — útil en tests)
python -c "from app.utils.production_check import raise_if_insecure; raise_if_insecure()"

# Generar SECRET_KEY de 256 bits (43 chars URL-safe)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generar ADMIN_PASSWORD de alta entropía (20 chars)
python -c "import secrets, string; a=string.ascii_letters+string.digits+'!@#%&*'; print(''.join(secrets.choice(a) for _ in range(20)))"

# ── Docker local ──────────────────────────────────────────────
# Construir imagen
docker build -t adamoservices-partner-manager .

# Correr contenedor con BD SQLite local (desarrollo)
docker run -p 8501:8501 \
  -e APP_ENV=development \
  -v $(pwd)/data:/app/data \
  adamoservices-partner-manager

# Correr contenedor con PostgreSQL (simular Railway)
docker run -p 8501:8501 \
  -e APP_ENV=production \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e SECRET_KEY=tu-secret-key-de-32-chars \
  -e ADMIN_PASSWORD=tu-admin-password \
  -e ADMIN_EMAIL=compliance@adamoservices.co \
  -e ADMIN_USERNAME=admin \
  adamoservices-partner-manager

# ── Railway ───────────────────────────────────────────────────
# El deploy se activa automáticamente al hacer push a la rama
# conectada en Railway. El entrypoint.sh ejecuta:
#   1. production_check.py  (valida variables críticas)
#   2. python -m db.database  (migraciones)
#   3. streamlit run app/main.py --server.port $PORT
```

---

## 🔧 Variables de entorno clave

| Variable              | Entorno         | Descripción                               | Default / Notas                          |
|-----------------------|-----------------|-------------------------------------------|------------------------------------------|
| `APP_NAME`            | Ambos           | Nombre de la aplicación                    | `AdamoServices Partner Manager`          |
| `APP_ENV`             | Ambos           | Entorno activo                            | `development` · `production`             |
| `DATABASE_URL`        | Ambos           | Cadena de conexión BD                      | SQLite local · PostgreSQL en Railway      |
| `SECRET_KEY`          | **Producción**  | Clave para firmar sesiones/tokens         | ≥ 43 chars (`secrets.token_urlsafe(32)`) — **obligatorio** |
| `ADMIN_PASSWORD`      | **Producción**  | Password del usuario admin seed           | ≥ 16 chars, 4 clases de chars (Circular 027) — **obligatorio** |
| `SESSION_TIMEOUT_MINUTES` | Ambos       | Duración de sesión inactiva               | `30` en prod · `60` en dev               |
| `ADMIN_EMAIL`         | **Producción**  | Email del administrador                   | `compliance@adamoservices.co`            |
| `ADMIN_USERNAME`      | **Producción**  | Username del admin seed                   | `admin`                                  |
| `PORT`                | Railway (auto)  | Puerto inyectado por Railway              | `8501` en local                          |
| `DEBUG`               | Desarrollo      | Muestra SQL en consola                    | `true` en dev, `false` en prod           |

> ⚠️ `production_check.py` bloquea el arranque si `SECRET_KEY` ( < 43 chars) o `ADMIN_PASSWORD` (< 16 chars o sin complejidad suficiente) usan valores débiles cuando `APP_ENV=production`.  
> Usa `raise_if_insecure()` en tests de integración para validar la configuración programáticamente.

---

## 📐 Convenciones del código

- **Repositorios**: toda query SQL pasa por `db/repositories/` — nunca SQL directo en `app/`
- **Modelos Pydantic**: validación en el borde del sistema (entrada de formularios)
- **Auditoría**: cada `CREATE`, `UPDATE`, cambio de estado y `LOGIN` se registra en `log_auditoria`
- **Sesiones BD**: usar `get_session()` como generador con `next()` + bloque `try/finally`
- **Seguridad**: passwords hasheadas con `bcrypt` (12 rounds) — nunca texto plano en BD
- **Hardening**: `SECRET_KEY` ≥ 43 chars · `ADMIN_PASSWORD` ≥ 16 chars con 4 clases · `DEBUG=false` en producción
- **Auth**: `require_auth()` como gate en `main()` — ENV bootstrap → bcrypt BD → PLACEHOLDER_HASH (solo dev)
- **Rate-limiting**: `st.session_state["login_fails"]` + `login_locked_until` — bloqueo 60 s tras 5 fallos
- **Pool BD**: `QueuePool` en PostgreSQL (pool_size=5, pool_recycle=30min) · `NullPool` en SQLite
- **EBR**: registros ordenados por riesgo descendente (Muy Alto → Alto → Medio → Bajo) según GAFI R.1
- **Componentes UI**: lógica de negocio visual en `app/components/` — importados en `main.py`
- **Session State**: filtros de sidebar en `st.session_state["filtro_*"]` — persistentes entre reruns
- **Acción Rápida**: `cambiar_estado()` + `AuditRepository.registrar()` siempre en el mismo bloque try/finally
- **Docker**: `.dockerignore` excluye `.env`, `data/`, `.venv` y tests del contenedor de producción

---

*AdamoServices S.A.S. · Compliance & Technology · [adamoservices.co](https://adamoservices.co)*
