# 🗂️ Estructura del Proyecto — AdamoServices Partner Manager

> Aplicación web de gestión de Banking Partners y Aliados Estratégicos.  
> Stack: Python 3.12 · Streamlit · PostgreSQL · SQLAlchemy (raw SQL) · Pydantic v2

---

## 📁 Árbol de archivos

```
Proyecto_PartnersStatus/
│
├── 📄 .env.example                    # Plantilla de variables de entorno (no subir .env al repo)
├── 📄 .gitignore                      # Exclusiones de Git (.env, .venv, __pycache__)
├── 📄 .dockerignore                   # Exclusiones del build Docker (.env, .venv, tests/)
├── 📄 Dockerfile                      # Imagen Docker basada en python:3.12-slim para Railway
├── 📄 entrypoint.sh                   # Script de arranque: migraciones → Streamlit (Puerto $PORT)
├── 📄 railway.toml                    # Configuración Railway (Dockerfile builder, healthcheck /_stcore/health)
├── 📄 requirements.txt                # Dependencias Python (incluye psycopg2-binary para PG)
├── 📄 README.md                       # Documentación principal del proyecto
├── 📄 ESTRUCTURA.md                   # Este archivo — mapa del proyecto
│
├── 📂 .streamlit/                     # Configuración nativa de Streamlit
│   └── 📄 config.toml                 # Tema dark AdamoServices · CSRF · anti-clickjacking · no telemetría
│
├── 📂 app/                            # Capa de presentación (Streamlit)
│   ├── 📄 __init__.py
│   ├── 📄 main.py                     # Entry point · router de páginas · CSS global
│   │                                  # sidebar() · page_nuevo_partner() · main()
│   │                                  # Rutas: Dashboard · Partners · Nuevo Partner · Auditoría
│   │
│   ├── 📂 auth/                       # Sistema de autenticación y control de acceso
│   │   ├── 📄 __init__.py
│   │   └── 📄 login.py                # authenticate() — ENV → bcrypt BD → PLACEHOLDER_HASH (dev)
│   │                                  # login_screen() — st.form + rate-limiting progresivo
│   │                                  #   (delay 1-3 s + bloqueo 60 s tras 5 fallos consecutivos)
│   │                                  # require_auth() — gate de sesión, llama st.stop()
│   │                                  # _get_client_ip() · _audit_login()
│   │
│   ├── 📂 pages/                      # Páginas como módulos independientes (expansión futura)
│   │   └── 📄 __init__.py
│   │
│   ├── 📂 components/                 # Componentes UI por página
│   │   ├── 📄 __init__.py
│   │   ├── 📄 dashboard_ui.py         # Dashboard Ejecutivo — page_dashboard()
│   │   │                              # 5 secciones: KPIs · Salud Corporativa · Monitor Riesgo
│   │   │                              #              Análisis Volumen · Centro de Alertas
│   │   │                              # _empresa_card(): tarjeta por empresa con lista de partners
│   │   │                              # _termometro_row() · _kpi() · _section() · _spacer()
│   │   ├── 📄 partners_ui.py          # Portafolio de Banking Partners — page_partners()
│   │   │                              # Tabla por tarjetas con filtros y KPIs rápidos
│   │   │                              # _panel_editar(): formulario inline 3 secciones
│   │   │                              #   (Básica / Relación Corporativa / Perfil Operativo)
│   │   │                              #   Editar: ADMIN / COMPLIANCE / COMERCIAL
│   │   │                              #   Campos compliance deshabilitados para rol comercial
│   │   │                              # _panel_eliminar(): confirmación roja — solo ADMIN
│   │   │                              # Auditoría automática en UPDATE y DELETE
│   │   │                              # _pill() · _capacidad_badge() · _idx()
│   │   ├── 📄 audit_ui.py             # Log de Auditoría — page_auditoria()
│   │   │                              # Tabla paginada de log_auditoria
│   │   └── 📄 alerts.py               # Centro de Notificaciones de Compliance
│   │                                  # render_centro_notificaciones() — SARLAFT vencidas
│   │                                  # Cards con botón ⚡ Acción Rápida (re-calificación)
│   │                                  # Cards próximas revisiones 30 días · DDI (GAFI R.1/R.12)
│   │
│   └── 📂 utils/                      # Funciones auxiliares de utilidad
│       ├── 📄 __init__.py
│       └── 📄 production_check.py     # Hardening pre-arranque (GAFI R.1 / CSBF Circular 027)
│                                      # raise_if_insecure() · run_checks()
│                                      # SECRET_KEY ≥ 43 chars · ADMIN_PASSWORD ≥ 16 chars
│                                      # DATABASE_URL debe ser PostgreSQL · ADMIN_USERNAME/EMAIL presentes
│
├── 📂 config/                         # Configuración centralizada
│   ├── 📄 __init__.py
│   └── 📄 settings.py                 # APP_NAME · DATABASE_URL · SECRET_KEY
│                                      # Roles · EstadosAliado · NivelesRiesgo · EstadosSARLAFT · TiposAliado
│
├── 📂 db/                             # Capa de datos
│   ├── 📄 __init__.py
│   ├── 📄 database.py                 # Motor SQLAlchemy · QueuePool PostgreSQL
│   │                                  # SessionLocal (generador) · init_database() · health_check()
│   │                                  # Uso: with next(get_session()) as session:
│   ├── 📄 models.py                   # Modelos Pydantic v2
│   │                                  # AliadoBase · AliadoCreate · AliadoUpdate · AliadoOut
│   │                                  # UsuarioBase · UsuarioCreate · UsuarioUpdate · UsuarioOut
│   │
│   ├── 📂 migrations/                 # Scripts SQL versionados (PostgreSQL)
│   │   ├── 📄 001_initial_schema_pg.sql          # Esquema inicial: tablas, índices y triggers
│   │   ├── 📄 002_add_corporate_metrics.sql       # Columnas gestión corporativa (estado_hbpocorp/adamo/paycop)
│   │   └── 📄 003_fix_constraints_and_corporate_metrics.sql  # Fix constraints + perfil operativo
│   │
│   └── 📂 repositories/              # Patrón Repository — CRUD desacoplado de la UI
│       ├── 📄 __init__.py
│       ├── 📄 partner_repo.py         # CRUD completo de aliados
│       │                              # create() · update() · get_by_id() · delete()
│       │                              # get_lista_enriquecida() · get_stats_pipeline()
│       │                              # get_stats_riesgo() · get_sarlaft_vencidas()
│       │                              # get_revisiones_proximas(dias=30) · recalcular_puntaje()
│       │                              # get_salud_grupo() · get_stats_capacidades()
│       │                              # get_termometro_sarlaft() · get_resumen_volumen()
│       │                              # get_partners_por_empresa(empresa)
│       └── 📄 audit_repo.py           # Log de auditoría inmutable (solo escritura/lectura)
│                                      # registrar() — CREATE · UPDATE · DELETE · LOGIN · EXPORT
│
└── 📂 tests/                          # Suite de pruebas
    └── 📄 __init__.py
```

---

##  Pipeline de Estados

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

## 📊 Páginas de la Aplicación

### Dashboard Ejecutivo (`app/components/dashboard_ui.py`)
**5 secciones verticales:**
1. **KPIs** — Total partners · Activos · Alto Riesgo · PEPs · SARLAFT vencidos
2. **Salud Corporativa** — Tarjeta por empresa (HoldingsBPO Corp / Adamo / Paycop)
   - Counters Activo/Inactivo · barra de progreso · lista de partners con estado y riesgo
3. **Monitor de Riesgo** — Donut Plotly (distribución por riesgo) + termómetro SARLAFT por estado
4. **Análisis de Volumen** — Ranking de partners por volumen (`get_resumen_volumen()`)
5. **Centro de Alertas** — SARLAFT vencidas · próximas revisiones 30 días · botón ⚡ Acción Rápida

### Portafolio de Partners (`app/components/partners_ui.py`)
- **Filtros**: Estado Pipeline · Nivel Riesgo · búsqueda texto · Solo PEP
- **KPIs rápidos**: Total · Activos · Alto Riesgo · PEPs
- **Tabla por tarjetas**: pills de colores (pipeline/riesgo/SARLAFT) + badges de capacidades operativas
- **Edición inline** (ADMIN / COMPLIANCE / COMERCIAL): formulario 3 secciones; campos de compliance deshabilitados para rol `comercial`; auditoría automática al guardar
- **Eliminación** (solo ADMIN): panel de confirmación con borde rojo + auditoría automática (`DELETE`)
- Fila activa resaltada: cian = editando · rojo = eliminando

### Log de Auditoría (`app/components/audit_ui.py`)
- Tabla paginada de `log_auditoria` — acciones CREATE · UPDATE · DELETE · LOGIN · EXPORT

---

## 👥 Roles de Acceso (RBAC)

| Rol           | Dashboard | Ver Partners | Crear/Editar | Cambiar Estado | Auditoría | Eliminar |
|---------------|:---------:|:------------:|:------------:|:--------------:|:---------:|:--------:|
| `admin`       | ✅        | ✅           | ✅           | ✅             | ✅        | ✅       |
| `compliance`  | ✅        | ✅           | ✅           | ✅             | ✅        | ❌       |
| `comercial`   | ✅        | ✅           | Parcial      | Parcial        | ❌        | ❌       |
| `consulta`    | ✅        | ✅           | ❌           | ❌             | ❌        | ❌       |

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
| `DATABASE_URL`        | Ambos           | Cadena de conexión BD                      | PostgreSQL en Railway — obligatorio       |
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
- **Auditoría**: cada `CREATE`, `UPDATE`, `DELETE`, cambio de estado y `LOGIN` se registra en `log_auditoria`
- **Sesiones BD**: `get_session()` es un generador — usar siempre `with next(get_session()) as session:`
- **HTML en Streamlit**: sin comentarios `<!-- -->`, sin `position:absolute` — rompen el renderizador. Todo el HTML de una tarjeta en un único `st.markdown()` (una sola llamada por bloque)
- **Lazy imports**: todos los imports de DB y repos dentro de las funciones `page_*()`, no en el módulo global
- **Seguridad**: passwords hasheadas con `bcrypt` (12 rounds) — nunca texto plano en BD
- **Hardening**: `SECRET_KEY` ≥ 43 chars · `ADMIN_PASSWORD` ≥ 16 chars con 4 clases · `DEBUG=false` en producción
- **Auth**: `require_auth()` como gate en `main()` — ENV bootstrap → bcrypt BD → PLACEHOLDER_HASH (solo dev)
- **Rate-limiting**: `st.session_state["login_fails"]` + `login_locked_until` — bloqueo 60 s tras 5 fallos
- **Pool BD**: `QueuePool` en PostgreSQL (pool_size=5, pool_recycle=30min)
- **EBR**: registros ordenados por riesgo descendente (Muy Alto → Alto → Medio → Bajo) según GAFI R.1
- **Componentes UI**: lógica de negocio visual en `app/components/` — importados lazy dentro de `page_*()`
- **Session State edición**: `st.session_state["edit_id"]` / `st.session_state["delete_id"]` para acciones en tabla
- **Acción Rápida**: `cambiar_estado()` + `AuditRepository.registrar()` siempre en el mismo bloque try/finally
- **Docker**: `.dockerignore` excluye `.env`, `.venv` y tests del contenedor de producción

---

*AdamoServices S.A.S. · Compliance & Technology · [adamoservices.co](https://adamoservices.co)*
