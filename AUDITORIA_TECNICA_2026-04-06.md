# Auditoría Técnica — AdamoPay Partner Manager
**Fecha:** 06 de Abril de 2026  
**Alcance:** Corrección de errores, integridad de importaciones, lógica de negocio de compliance y propuesta de analítica de riesgo.  
**Stack:** Python 3.12 · Streamlit · SQLAlchemy · PostgreSQL (Railway) · Pydantic v2

---

## Resumen Ejecutivo

Se auditaron los módulos `db/models.py`, `db/repositories/partner_repo.py`, `app/main.py` y la estructura de componentes UI. Se identificaron **5 errores** (2 bloqueantes, 3 funcionales), se aplicaron todas las correcciones y se crearon los archivos faltantes. Al finalizar, todos los imports fueron verificados en consola Python con resultado `OK`.

---

## Hallazgos y Correcciones

### BUG-01 — Import prematuro y muerto en `app/main.py`
**Severidad:** 🔴 Bloqueante  
**Archivo:** `app/main.py` línea 12  

**Problema:**  
```python
import db.repositories.partner_repo as pr   # línea 12
sys.path.insert(0, ...)                      # línea 15  ← demasiado tarde
```
El alias `pr` se importaba **antes** de que `sys.path` apuntara a la raíz del proyecto, causando `ModuleNotFoundError` si el proceso se iniciaba desde cualquier directorio distinto a la raíz. Adicionalmente, el alias `pr` **nunca se usaba** en ningún lugar del archivo (import muerto).

**Corrección aplicada:**  
Se eliminó la línea `import db.repositories.partner_repo as pr`. El `sys.path.insert` quedó como primera instrucción antes de cualquier import local.

---

### BUG-02 — Columnas corporativas nuevas sin migración SQL
**Severidad:** 🔴 Bloqueante  
**Archivos:** `db/models.py` vs `db/migrations/001_initial_schema_pg.sql`  

**Problema:**  
13 columnas definidas en Pydantic (`AliadoBase`) no existían en el esquema PostgreSQL de Railway, causando `column does not exist` en cualquier operación `INSERT` o `SELECT`:

| Columna | Tipo Pydantic | Tipo SQL requerido |
|---|---|---|
| `estado_hbpocorp` | `str` | `TEXT NOT NULL DEFAULT 'Sin relación'` |
| `estado_adamo` | `str` | `TEXT NOT NULL DEFAULT 'Sin relación'` |
| `estado_paycop` | `str` | `TEXT NOT NULL DEFAULT 'Sin relación'` |
| `crypto_friendly` | `bool` | `BOOLEAN NOT NULL DEFAULT FALSE` |
| `adult_friendly` | `bool` | `BOOLEAN NOT NULL DEFAULT FALSE` |
| `permite_monetizacion` | `bool` | `BOOLEAN NOT NULL DEFAULT FALSE` |
| `permite_dispersion` | `bool` | `BOOLEAN NOT NULL DEFAULT FALSE` |
| `monedas_soportadas` | `Optional[str]` | `TEXT` |
| `clientes_vinculados` | `Optional[str]` | `TEXT` |
| `volumen_real_mensual` | `Optional[str]` | `TEXT` |
| `motivo_inactividad` | `Optional[str]` | `TEXT` |
| `fecha_inicio_relacion` | `Optional[date]` | `DATE` |
| `fecha_fin_relacion` | `Optional[date]` | `DATE` |

**Corrección aplicada:**  
Creado `db/migrations/002_add_corporate_metrics.sql` con `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` (idempotente) para las 13 columnas, más 5 índices de optimización:
```sql
CREATE INDEX IF NOT EXISTS idx_aliados_estado_hbpocorp ON aliados(estado_hbpocorp);
CREATE INDEX IF NOT EXISTS idx_aliados_estado_adamo    ON aliados(estado_adamo);
CREATE INDEX IF NOT EXISTS idx_aliados_estado_paycop   ON aliados(estado_paycop);
CREATE INDEX IF NOT EXISTS idx_aliados_crypto   ON aliados(crypto_friendly) WHERE crypto_friendly = TRUE;
CREATE INDEX IF NOT EXISTS idx_aliados_adult    ON aliados(adult_friendly)  WHERE adult_friendly  = TRUE;
```
> ⚠ **Acción requerida:** Ejecutar esta migración en Railway antes del próximo deploy.

---

### BUG-03 — `_coerce_bools` convirtiendo columnas `BOOLEAN` a entero
**Severidad:** 🟠 Funcional  
**Archivo:** `db/repositories/partner_repo.py`  

**Problema:**  
La función `_coerce_bools` convertía `True → 1` y `False → 0` en todos los campos booleanos antes del INSERT/UPDATE, asumiendo que la DB almacenaba enteros. Sin embargo, las columnas declaradas en el esquema SQL son `BOOLEAN` nativo de PostgreSQL (no `INTEGER`). psycopg2 y SQLAlchemy manejan `True`/`False` de Python de forma transparente con columnas `BOOLEAN`. La coerción forzada no causaba error directo pero rompía cualquier query con `WHERE campo = TRUE` desde la DB.

**Corrección aplicada:**  
Se eliminó la función `_coerce_bools` y todas sus llamadas en `create()` y `update()`. Se reemplazó por la función de scoring `calcular_puntaje_riesgo()` que aporta valor real al flujo.

---

### BUG-04 — Métodos `get_sarlaft_vencidas()` y `get_revisiones_proximas()` faltantes
**Severidad:** 🟠 Funcional  
**Archivos:** `app/components/alerts.py` → `db/repositories/partner_repo.py`  

**Problema:**  
`alerts.py` invocaba `repo.get_sarlaft_vencidas()` y `repo.get_revisiones_proximas(dias=30)` pero ninguno de los dos métodos existía en `PartnerRepository`, causando `AttributeError` al renderizar el dashboard.

**Corrección aplicada:**  
Implementados ambos métodos en `PartnerRepository`:
- `get_sarlaft_vencidas()` — devuelve aliados con `estado_sarlaft = 'Vencido'` o `fecha_proxima_revision < CURRENT_DATE`.
- `get_revisiones_proximas(dias)` — devuelve aliados cuya próxima revisión vence dentro de N días.

---

### BUG-05 — Módulos UI referenciados pero no existentes
**Severidad:** 🟠 Funcional  
**Archivo:** `app/main.py`  

**Problema:**  
`main.py` importaba dinámicamente tres módulos al navegar entre páginas:
```python
from app.components.dashboard_ui import page_dashboard
from app.components.partners_ui  import page_partners
from app.components.audit_ui     import page_auditoria
```
Ninguno de los tres archivos existía → `ModuleNotFoundError` al intentar acceder a cualquier página distinta al formulario de creación.

**Corrección aplicada:**  
Creados los tres módulos con lógica completa:

| Archivo creado | Contenido |
|---|---|
| `app/components/dashboard_ui.py` | KPIs globales, comparativa de salud corporativa, distribución de riesgo SARLAFT, alertas |
| `app/components/partners_ui.py` | Tabla enriquecida con filtros por pipeline, riesgo, SARLAFT, tipo y búsqueda libre |
| `app/components/audit_ui.py` | Log de auditoría filtrable por acción, entidad y rango de fechas |

---

## Mejoras de Negocio Implementadas

### Motor de Score de Riesgo Automático
**Función:** `calcular_puntaje_riesgo(data: dict) → tuple[float, str]`  
**Ubicación:** `db/repositories/partner_repo.py`

Rubrica de puntuación basada en criterios SARLAFT-GAFI:

| Factor de Riesgo | Puntos |
|---|---|
| Persona Expuesta Políticamente (PEP) | +25 |
| Crypto Friendly | +20 |
| Adult Friendly | +15 |
| Crypto + Monetización (combinación) | +10 |
| Listas restrictivas sin verificar | +15 |
| OFAC no limpia | +10 |
| Due Diligence rechazado | +30 |
| SARLAFT vencido | +20 |
| SARLAFT pendiente | +10 |
| Sin contrato firmado | +5 |
| Sin RUT | +5 |
| Sin Cámara de Comercio | +5 |
| Sin Due Diligence iniciado | +10 |

Escala de nivel por puntaje:

| Rango | Nivel |
|---|---|
| 0 – 25 | Bajo |
| 26 – 50 | Medio |
| 51 – 75 | Alto |
| 76 – 100 | Muy Alto |

### Escalado Preventivo en Pydantic (`model_validator`)
**Ubicación:** `db/models.py` — clase `AliadoBase`

Al crear o validar un `AliadoCreate`, el validador escala automáticamente `nivel_riesgo` si el perfil operativo lo justifica, **nunca bajando** el nivel que el usuario eligió:

| Capacidad operativa | Nivel mínimo forzado |
|---|---|
| `crypto_friendly = True` | **Alto** |
| `adult_friendly = True` | **Alto** |
| `crypto_friendly = True` AND `adult_friendly = True` | **Muy Alto** |

**Verificado en consola:**
```
Riesgo escalado (Bajo → con crypto_friendly=True): Alto
Score (crypto+adult+pep): 100.0 → Muy Alto
```

### Comparativa de Salud Corporativa
**Método:** `get_salud_grupo() → dict`  
**Ubicación:** `db/repositories/partner_repo.py`

Calcula por cada empresa del grupo (HoldingsBPO, Adamo, Paycop):
- Cantidad de partners `Activos` / `Inactivos` / `Sin relación`
- `pct_activos`: porcentaje de activación sobre el total con relación

Visualizado en `dashboard_ui.py` con tarjetas y barras de progreso independientes por empresa.

---

## Validadores Pydantic Añadidos

Agregado en `AliadoBase` el validador para los 3 campos de estado corporativo (faltaban y cualquier valor inválido pasaba silenciosamente):

```python
@field_validator("estado_hbpocorp", "estado_adamo", "estado_paycop")
@classmethod
def _check_estado_empresa(cls, v: str) -> str:
    validos = {"Activo", "Inactivo", "Sin relación"}
    if v not in validos:
        raise ValueError(f"Estado de empresa inválido. Opciones: {sorted(validos)}")
    return v
```

---

## Archivos Modificados / Creados

| Archivo | Operación | Descripción |
|---|---|---|
| `app/main.py` | Modificado | Eliminado import prematuro y muerto `pr` |
| `db/models.py` | Modificado | Validador `_check_estado_empresa` + `model_validator` de escalado de riesgo |
| `db/repositories/partner_repo.py` | Modificado | Eliminado `_coerce_bools`; añadidos `calcular_puntaje_riesgo`, `get_sarlaft_vencidas`, `get_revisiones_proximas`, `recalcular_puntaje`, `get_salud_grupo` |
| `db/migrations/002_add_corporate_metrics.sql` | Creado | Migración idempotente para las 13 columnas nuevas + 5 índices |
| `app/components/dashboard_ui.py` | Creado | Dashboard ejecutivo con KPIs, salud corporativa y alertas |
| `app/components/partners_ui.py` | Creado | Tabla de partners con filtros avanzados |
| `app/components/audit_ui.py` | Creado | Log de auditoría filtrable |

---

## Acciones Pendientes (Post-Auditoría)

1. **Ejecutar migración en Railway:**
   ```bash
   psql $DATABASE_URL -f db/migrations/002_add_corporate_metrics.sql
   ```

2. **Recalcular scores de partners existentes** tras la migración:
   ```python
   with next(get_session()) as session:
       repo = PartnerRepository(session)
       for p in repo.get_lista_enriquecida():
           repo.recalcular_puntaje(p["id"], actualizado_por=1)
   ```

3. **Completar `AliadoUpdate`** con campos de compliance adicionales (fechas de documentos, revisiones SARLAFT) si se requiere actualización parcial avanzada desde la UI.

4. **Tests unitarios** para `calcular_puntaje_riesgo` y el `model_validator` de escalado (casos: solo crypto, solo adult, ambos, ninguno, con PEP).
