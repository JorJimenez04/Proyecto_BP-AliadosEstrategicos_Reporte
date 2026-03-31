# Documentación Técnica — AdamoServices Partner Manager
**Compliance & Technology | AdamoServices**  
**Versión:** 1.1 | **Motor BD:** PostgreSQL 16 | **Runtime:** Python 3.10+ | **Actualizado:** 2026-03-31

---

## 1. Descripción General

**AdamoServices Partner Manager** es una aplicación web interna de gestión de cumplimiento regulatorio para la administración de **Banking Partners y Aliados Estratégicos**. Su objetivo principal es centralizar el ciclo de vida completo de cada aliado comercial bajo los estándares exigidos por la Superintendencia Financiera de Colombia.

### Funciones principales

| Módulo | Descripción |
|--------|-------------|
| **Registro de Aliados** | Alta, edición y baja de Banking Partners, Aliados Estratégicos, Corresponsales y Proveedores. Cada registro incluye información de contacto, comercial y de cumplimiento. |
| **Pipeline de Estado** | Trazabilidad del ciclo de vida: `Prospecto → En Calificación → Onboarding → Activo → Suspendido → Terminado`. Cada transición queda registrada con motivo y responsable. |
| **Módulo SARLAFT** | Gestión del Sistema de Administración del Riesgo de LA/FT: nivel de riesgo, puntaje, revisiones periódicas, verificación de listas restrictivas (OFAC, ONU, UE, Superfinanciera local), Due Diligence y clasificación PEP. |
| **Log de Auditoría** | Registro inmutable de cada acción del sistema (CREATE, UPDATE, DELETE, LOGIN, EXPORT, ESTADO_CHANGE) con usuario, IP, timestamp y diff JSON de valores antes/después. Requerido por Circular 042 de la Superfinanciera. |
| **Control de Acceso (RBAC)** | Cuatro roles con permisos diferenciados: `admin`, `compliance`, `comercial`, `consulta`. |
| **Autenticación** | Login con rate-limiting (bloqueo tras 5 intentos fallidos, 60 s de cooldown). Cada intento —exitoso o fallido— se registra en el log de auditoría con IP del cliente. |

---

## 2. Stack Tecnológico

### Por qué cada tecnología

**Python 3.10+**  
Lenguaje principal. Eligido por su ecosistema maduro en análisis de datos y compliance financiero, tipado estático opcional (type hints) y la amplísima disponibilidad de librerías para bcrypt, SQLAlchemy y Pydantic.

**Streamlit**  
Framework web para Python que permite construir interfaces de usuario web interactivas sin JavaScript. Es ideal para aplicaciones internas de negocio donde la velocidad de desarrollo y la visualización de datos son prioritarias sobre la programación frontend. Streamlit gestiona el estado de sesión del servidor, el routing básico y el renderizado de componentes.

**SQLAlchemy**  
ORM y capa de abstracción de base de datos. No se usa el ORM declarativo (modelos como clases), sino el modo **Core** con `text()` — SQL explícito sin abstracciones que dificulten la auditoría o el debugging. SQLAlchemy gestiona el pool de conexiones (`QueuePool`) y la serialización de transacciones.

**PostgreSQL 16 (Railway)**  
Motor de base de datos relacional en producción. Elegido sobre alternativas por:
- Soporte nativo de `SERIAL`, triggers `plpgsql` y `ON CONFLICT DO ...` (necesario para la lógica de seed de usuarios).
- Concurrencia real (múltiples conexiones simultáneas), a diferencia de SQLite.
- Backups automáticos y alta disponibilidad gestionados por Railway.
- Compatibilidad total con los estándares de seguridad requeridos.

**Pydantic v2**  
Validación y serialización de datos en los modelos `AliadoCreate` / `AliadoUpdate`. Garantiza que ningún dato malformado llegue a la capa SQL.

**bcrypt**  
Hashing de contraseñas con `rounds=12`. bcrypt es resistente a ataques de diccionario por diseño (función lenta con factor de costo ajustable). Nunca se almacena la contraseña en texto plano.

**Railway**  
Plataforma de despliegue como servicio (PaaS). Gestiona la infraestructura del servidor, el balanceo de carga, los certificados TLS, los despliegues automáticos desde GitHub y el aprovisionamiento de la base de datos PostgreSQL.

**GitHub**  
Repositorio de código y disparo del pipeline CI/CD. Cada `git push` a la rama principal inicia automáticamente un nuevo despliegue en Railway.

---

## 3. Arquitectura de Datos

### Esquema de tablas

```
usuarios ──────────────────────────────────────────────────────┐
  id, username, nombre_completo, email,                         │
  password_hash (bcrypt), rol, departamento,                    │ FK
  activo, ultimo_acceso, created_at, updated_at                 │
                                                                │
aliados ──────────────────────────────────────────────────────┐ │
  id, nombre_razon_social, nit (UNIQUE),                       │ │
  tipo_aliado, fecha_vinculacion, estado_pipeline,             │ │
  [datos de contacto],                                         │ │
  [datos comerciales],                                         │ │
  [campos SARLAFT: nivel_riesgo, puntaje, PEP, listas,        │─┘
   due_diligence, fechas de revisión],                         │
  [documentación: RUT, cámara, contrato, póliza],              │
  ejecutivo_cuenta_id FK → usuarios                            │
  oficial_compliance_id FK → usuarios                          │
  creado_por FK → usuarios                                     │
  actualizado_por FK → usuarios                                │
                                                               │
historial_estados                                              │
  aliado_id FK → aliados                                       │
  estado_anterior, estado_nuevo, motivo                        │
  cambiado_por FK → usuarios                                   │
                                                               │
revisiones_sarlaft                                             │
  aliado_id FK → aliados                                       │
  oficial_id FK → usuarios                                     │
  nivel_riesgo_previo/nuevo, puntaje_previo/nuevo              │
  hallazgos, acciones_requeridas, proxima_revision             │
  aprobado_por FK → usuarios                                   │
                                                               │
log_auditoria (SOLO APPEND — nunca UPDATE ni DELETE)           │
  usuario_id FK → usuarios                                     │
  username (denormalizado para inmutabilidad)                  │
  accion: CREATE|UPDATE|DELETE|LOGIN|LOGIN_FAIL|EXPORT|ESTADO_CHANGE
  entidad, entidad_id                                          │
  descripcion (texto legible)                                  │
  valores_anteriores (JSON), valores_nuevos (JSON)             │
  ip_address, user_agent                                       │
  resultado: exitoso|fallido|rechazado                         │
```

### Índices creados automáticamente

Los índices aceleran las consultas más frecuentes en producción:

```sql
idx_aliados_nit              -- búsqueda por NIT
idx_aliados_estado_pipeline  -- filtro de pipeline
idx_aliados_nivel_riesgo     -- filtro de riesgo
idx_aliados_estado_sarlaft   -- filtro SARLAFT
idx_aliados_proxima_revision -- alertas de revisiones próximas
idx_historial_aliado         -- historial por aliado
idx_revisiones_aliado        -- revisiones por aliado
idx_auditoria_usuario        -- log por usuario
idx_auditoria_entidad        -- log por tabla+ID
idx_auditoria_fecha          -- log por rango de fechas
```

### Triggers de `updated_at`

Un trigger `plpgsql` (`fn_set_updated_at`) actualiza automáticamente `updated_at = CURRENT_TIMESTAMP` en las tablas `aliados` y `usuarios` cada vez que se hace un `UPDATE`. Esto garantiza trazabilidad temporal sin depender del código de aplicación.

### Conexión a la base de datos

La conexión a PostgreSQL se configura exclusivamente mediante la variable de entorno `DATABASE_URL`. El código en `db/database.py` normaliza automáticamente el esquema `postgres://` → `postgresql://` (Railway históricamente emite la URL con el esquema antiguo).

**En producción (Railway):** la URL usa la red interna de Railway (`postgres.railway.internal:5432`). Esta es la dirección preferida porque:
- El tráfico nunca sale a internet — viaja por la red privada del datacenter.
- Latencia de ~0 ms (misma región, mismo host).
- Sin costos de transferencia de datos.
- Sin riesgo de exposición de credenciales en tránsito (aunque la URL externa también es TLS).

**En desarrollo local:** la URL apunta a `localhost:5432` donde corre el contenedor Docker.

### Pool de conexiones

```python
QueuePool(
    pool_size=5,       # Conexiones mantenidas abiertas en reposo
    max_overflow=10,   # Conexiones adicionales bajo carga pico
    pool_timeout=30,   # Máximo de espera para obtener una conexión (s)
    pool_recycle=1800, # Recicla conexiones cada 30 min (evita timeouts de Railway)
    pool_pre_ping=True # Verifica la conexión antes de usarla (evita errores silenciosos)
)
```

---

## 4. Variables de Entorno

Todas las variables se leen en `config/settings.py` usando `python-dotenv`. En producción se inyectan directamente en Railway → Service → Variables (nunca en archivos `.env` en el repositorio).

| Variable | Requerida | Descripción | Por qué es crítica |
|----------|-----------|-------------|-------------------|
| `DATABASE_URL` | ✅ Sí | URL completa de conexión PostgreSQL: `postgresql://user:pass@host:port/db` | Sin ella la app no arranca (lanza `EnvironmentError`). Contiene credenciales de la BD. |
| `SECRET_KEY` | ✅ Sí (producción) | Token URL-safe de 32 bytes (43 chars). Genera con: `python -c "import secrets; print(secrets.token_urlsafe(32))"` | Firma criptográfica de las cookies de sesión de Streamlit (`STREAMLIT_SERVER_COOKIE_SECRET`). Si se compromete, un atacante puede forjar sesiones. En producción, el arranque se bloquea si esta clave es débil o ausente. |
| `APP_ENV` | ✅ Sí | `development` o `production` | Activa validaciones bloqueantes de seguridad en producción (SECRET_KEY fuerte, no PLACEHOLDER_HASH). En desarrollo relaja estas restricciones para facilitar el trabajo local. |
| `ADMIN_USERNAME` | ✅ Sí | Username del administrador inicial (ej. `jorge_jimenez`) | Se usa como bypass de BD para el primer login. Permite acceder incluso si la BD está vacía. |
| `ADMIN_PASSWORD` | ✅ Sí | Contraseña del administrador. Mínimo 16 chars con mayúsculas, minúsculas, números y símbolos. | Se hashea con bcrypt al inicializar y se guarda en la tabla `usuarios`. Si está en texto plano en un `.env` del repo, es una vulnerabilidad crítica. |
| `ADMIN_EMAIL` | Sí | Email del administrador seed | Se registra en la tabla `usuarios`. |
| `PORT` | Railway | Railway lo inyecta automáticamente. El `entrypoint.sh` lo recoge con `${PORT:-8501}`. | Sin el puerto correcto, el healthcheck de Railway falla y el container se reinicia en loop. |
| `DEBUG` | No | `true` o `false`. Activa `echo=True` en SQLAlchemy (imprime todo el SQL en consola). | **Nunca `true` en producción** — expone todas las queries con sus parámetros en los logs. |
| `SESSION_TIMEOUT_MINUTES` | No | Duración máxima de sesión inactiva (default: 30). | Recomendación GAFI R.1: minimizar la ventana de sesión para reducir riesgo de sesión robada. |
| `STREAMLIT_SERVER_ADDRESS` | No | `0.0.0.0` para aceptar tráfico de cualquier interfaz. | Necesario en contenedores Docker/Railway para que el servidor sea accesible desde fuera. |

### Generación de `SECRET_KEY` segura

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

El resultado (43 caracteres) se pega directamente en Railway → Variables → `SECRET_KEY`. **Nunca compartir ni versionar este valor.**

---

## 5. Flujo de Despliegue (CI/CD)

```
VS Code (Local)
     │
     │  git commit -m "feat: ..."
     │  git push origin main
     ▼
GitHub (Repositorio)
     │
     │  Railway detecta el push vía webhook
     ▼
Railway Build Pipeline
     │
     ├─ Lee railway.toml  →  builder = "DOCKERFILE"
     ├─ Construye imagen desde Dockerfile
     │     ├─ python:3.10-slim
     │     ├─ pip install -r requirements.txt
     │     └─ COPY del código fuente
     │
     ├─ Arranca el contenedor con: /entrypoint.sh
     │     ├─ [Si APP_ENV=production] python -c "from app.utils.production_check import run_checks; run_checks()"
     │     │     └─ Valida: SECRET_KEY fuerte, DATABASE_URL → PostgreSQL, variables presentes
     │     ├─ python -m db.database   → ejecuta 001_initial_schema_pg.sql + seed usuario
     │     ├─ export STREAMLIT_SERVER_COOKIE_SECRET=$SECRET_KEY
     │     └─ streamlit run app/main.py --server.port $PORT ...
     │
     └─ Healthcheck: GET /_stcore/health (timeout 30s)
           ├─ OK → despliegue exitoso, tráfico commutado al nuevo container
           └─ FAIL → Railway reintenta (máx 3 veces, política ON_FAILURE)
```

### Configuración en `railway.toml`

```toml
[build]
builder        = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand            = "/entrypoint.sh"
healthcheckPath         = "/_stcore/health"
healthcheckTimeout      = 30
restartPolicyType       = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

### Idempotencia del despliegue

El script de migración usa `CREATE TABLE IF NOT EXISTS` y `CREATE INDEX IF NOT EXISTS`, por lo que es seguro ejecutarlo en cada despliegue. La semilla del usuario admin usa `ON CONFLICT DO NOTHING`, evitando duplicados.

---

## 6. Guía de Mantenimiento

### Ejecutar migraciones manualmente (Railway CLI)

Si necesitas ejecutar cambios de esquema fuera del ciclo normal de despliegue:

```bash
# 1. Instalar Railway CLI (una sola vez)
npm install -g @railway/cli

# 2. Autenticarse
railway login

# 3. Vincular al proyecto
railway link

# 4. Ejecutar el script de migración dentro del entorno Railway
railway run python -m db.database
```

### Agregar un nuevo usuario desde la terminal de Railway

```bash
railway run python - << 'EOF'
import bcrypt, os
from db.database import engine
from sqlalchemy import text

username  = "nuevo_usuario"
password  = "ContraseñaSegura_2026!"
email     = "nuevo@adamoservices.co"
nombre    = "Nombre Completo"
rol       = "compliance"   # admin | compliance | comercial | consulta

h = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

with engine.connect() as conn:
    conn.execute(text("""
        INSERT INTO usuarios (username, nombre_completo, email, password_hash, rol)
        VALUES (:u, :n, :e, :h, :r)
        ON CONFLICT (username) DO NOTHING
    """), {"u": username, "n": nombre, "e": email, "h": h, "r": rol})
    conn.commit()

print(f"✅ Usuario '{username}' creado con rol '{rol}'.")
EOF
```

### Desactivar un usuario (sin eliminar)

```bash
railway run python -c "
from db.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text(\"UPDATE usuarios SET activo=0 WHERE username=:u\"), {'u': 'username_a_desactivar'})
    conn.commit()
print('Usuario desactivado.')
"
```

### Agregar una nueva migración de esquema

1. Crear el archivo `db/migrations/002_nombre_cambio.sql` con las sentencias DDL.
2. Modificar `init_database()` en `db/database.py` para ejecutar también el nuevo archivo (o usar el archivo directamente con `railway run psql $DATABASE_URL -f db/migrations/002_...sql`).
3. Hacer commit y push — Railway aplicará la migración en el siguiente despliegue.

### Ver el log de auditoría desde psql

```bash
railway run python -c "
from db.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    rows = conn.execute(text(\"SELECT username, accion, entidad, descripcion, created_at FROM log_auditoria ORDER BY created_at DESC LIMIT 20\")).mappings().all()
for r in rows:
    print(r)
"
```

---

## 7. Arquitectura de la Aplicación

### Patrón de capas

```
app/main.py              ← Entry point, UI Streamlit, gestión de sesión
  _MAP_RIESGO            ← Constante de módulo: etiquetas con emoji para nivel de riesgo
  _MAP_SARLAFT           ← Constante de módulo: etiquetas con emoji para estado SARLAFT
app/auth/login.py        ← Autenticación, rate-limiting, audit de login
app/pages/               ← Páginas: Dashboard, Partners, Pipeline, SARLAFT, Auditoría
app/components/          ← Componentes UI reutilizables (alertas, tablas)
    alerts.py            ← Renderizado de alertas de cumplimiento
app/utils/
    production_check.py  ← Validación de variables antes de arranque en prod
        │
db/database.py           ← Motor SQLAlchemy, pool, init_database(), seed
db/repositories/
    partner_repo.py      ← CRUD de la tabla aliados
    audit_repo.py        ← Solo-escritura/solo-lectura del log_auditoria
db/models.py             ← Pydantic: AliadoCreate, AliadoUpdate (validación)
db/migrations/
    001_initial_schema_pg.sql  ← DDL completo PostgreSQL (tablas, índices, triggers)
        │
config/settings.py       ← Lectura de variables de entorno, validación de seguridad
```

> **Nota de diseño:** Los mapas `_MAP_RIESGO` y `_MAP_SARLAFT` se definen una sola vez a nivel de módulo en `main.py` y son compartidos por `_build_table_df()` (tabla de aliados) y `_tab_alertas()` (panel de alertas). Así se evita la duplicación de literales y cualquier desincronización futura.

### Flujo de autenticación

```
Usuario ingresa credenciales en login.py
        │
        ├─ Rate-limit: ¿más de 5 fallos recientes? → Bloqueo 60s
        │
        ├─ ¿username == ADMIN_USERNAME y password == ADMIN_PASSWORD (env)?
        │     └─ Sí → sesión de admin (bypass de BD, para recuperación de emergencia)
        │
        └─ No → consulta tabla usuarios WHERE username = ?
                  └─ bcrypt.checkpw(password, hash almacenado)
                        ├─ OK y activo=1 → sesión iniciada
                        └─ FAIL → registra LOGIN_FAIL en log_auditoria con IP
```

### Flujo de registro en auditoría

Cada operación de escritura (create/update/delete de aliados, cambios de estado, exportaciones) llama a `AuditRepository.registrar()`:

```python
AuditRepository(session).registrar(
    username="jorge_jimenez",
    accion="UPDATE",
    entidad="aliados",
    entidad_id=42,
    descripcion="Actualización de nivel de riesgo: Medio → Alto",
    valores_anteriores={"nivel_riesgo": "Medio"},
    valores_nuevos={"nivel_riesgo": "Alto"},
    ip_address="192.168.1.10",
    resultado="exitoso",
)
```

El `log_auditoria` **nunca se modifica ni elimina** — es el registro legal del sistema.

### Patrón Repository

Toda consulta a la base de datos pasa por los repositorios (`PartnerRepository`, `AuditRepository`). La UI de Streamlit nunca ejecuta SQL directamente. Esto:
- Centraliza la lógica de negocio en un lugar testeable.
- Evita inyección SQL (todos los parámetros se pasan con `:nombre` a SQLAlchemy, nunca por concatenación de strings).
- Facilita el mantenimiento: cambiar una consulta no requiere tocar la UI.

---

## 8. Seguridad

### Controles implementados

| Control | Implementación |
|---------|----------------|
| **Hashing de contraseñas** | bcrypt con `rounds=12`. El hash almacenado nunca es reversible. |
| **Firma de sesiones** | `STREAMLIT_SERVER_COOKIE_SECRET = SECRET_KEY`. Sin esta firma, cualquier cookie podría ser manipulada. |
| **Validación de arranque** | En `APP_ENV=production`, el proceso no arranca si `SECRET_KEY` es débil, corta o ausente. |
| **Rate-limiting** | 5 intentos fallidos → bloqueo de 60 s por `st.session_state`. Mitiga fuerza bruta. |
| **Log de intentos fallidos** | `LOGIN_FAIL` con IP y timestamp registrado en `log_auditoria`. |
| **Parámetros SQL** | Toda query usa `:parametro` — nunca f-strings con input del usuario. Previene SQL injection. |
| **Sin credenciales en el repo** | `.env` está en `.gitignore`. Las variables de producción solo existen en Railway → Variables. |
| **RBAC** | Cuatro roles con permisos distintos. La tabla `usuarios.rol` tiene un `CHECK()` constraint a nivel de BD. |

### Lo que NO hace este sistema (fuera de alcance)

- No gestiona 2FA (autenticación de dos factores).
- No implementa cifrado de datos en reposo a nivel de columna (solo a nivel de disco por Railway).
- No tiene expiración automática de sesión basada en tiempo de inactividad en la capa de red (lo hace `SESSION_TIMEOUT_MINUTES` en la lógica de Streamlit).

---

*AdamoServices — Compliance & Technology | [adamoservices.co](https://adamoservices.co)*
