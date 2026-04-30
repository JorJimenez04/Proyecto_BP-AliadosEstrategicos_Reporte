# 🔑 Credenciales de Prueba — AdamoServices Partner Manager

> **Solo para desarrollo local.** No subir al repositorio. Agregar a `.gitignore` si se modifica con passwords reales.  
> La contraseña de todos los usuarios es el valor de `ADMIN_PASSWORD` en tu archivo `.env`.

---

## 👤 Usuarios disponibles

| Usuario           | Contraseña       | Rol         | Acceso                                               |
|-------------------|------------------|-------------|------------------------------------------------------|
| `admin`           | (tu ADMIN_PASSWORD) | `admin`  | Todo — Dashboard · Partners · Nuevo · Auditoría · Gestión de Agentes |
| `test_compliance` | (tu ADMIN_PASSWORD) | `compliance` | Dashboard · Partners · Nuevo · Auditoría · Gestión de Agentes · Editar ficha agente |
| `test_comercial`  | (tu ADMIN_PASSWORD) | `comercial`  | Dashboard · Partners · Nuevo Partner (solo campos operativos) |
| `test_consulta`   | (tu ADMIN_PASSWORD) | `consulta`   | Dashboard · Partners (solo lectura, sin editar ni eliminar) |

---

## 🗂️ Tabla de permisos por sección

| Sección              | `admin` | `compliance` | `comercial` | `consulta` |
|----------------------|:-------:|:------------:|:-----------:|:----------:|
| 📊 Dashboard         | ✅      | ✅           | ✅          | ✅         |
| 🤝 Partners (ver)    | ✅      | ✅           | ✅          | ✅         |
| 🤝 Partners (editar) | ✅      | ✅           | Parcial ¹   | ❌         |
| 🤝 Partners (SARLAFT/PEP/Riesgo) | ✅ | ❌      | ❌          | ❌         |
| 🤝 Partners (eliminar) | ✅    | ❌           | ❌          | ❌         |
| ➕ Nuevo Partner     | ✅      | ✅           | ✅          | ❌         |
| 📋 Log de Auditoría  | ✅      | ✅           | ❌          | ❌         |
| 👥 Gestión de Agentes | ✅     | ✅           | ❌          | ❌         |
| ✏️ Editar ficha agente | ✅    | ✅           | ❌          | ❌         |
| 🏢 Equipos (sidebar) | ✅      | ✅           | ✅          | ✅         |

> ¹ **Parcial** — `comercial` puede editar campos operativos básicos, pero no SARLAFT · PEP · Nivel de Riesgo · Adult Friendly.

---

## 🚀 Preparar usuarios de prueba

```powershell
# 1. Asegúrate de que Docker esté corriendo
docker compose up -d postgres

# 2. Insertar usuarios de prueba (idempotente — se puede ejecutar varias veces)
.venv\Scripts\python.exe db/seed_test_users.py

# 3. Levantar la app
.venv\Scripts\streamlit.exe run app/main.py --server.port 8501
```

Abre http://localhost:8501 y usa las credenciales de la tabla de arriba.

---

## 🔄 Flujo de prueba recomendado

1. Ingresa como `admin` → verifica que ves todo el menú.
2. Cierra sesión (botón 🚪 del sidebar).
3. Ingresa como `test_compliance` → verifica que ves Auditoría y Gestión de Agentes, pero no puedes editar SARLAFT en Partners.
4. Cierra sesión → ingresa como `test_comercial` → verifica que **no** ves Auditoría ni Gestión de Agentes.
5. Cierra sesión → ingresa como `test_consulta` → verifica que solo ves Dashboard y Partners (sin botones de editar/eliminar).

---

*Solo entorno de desarrollo — `PLACEHOLDER_HASH` está bloqueado en `APP_ENV=production`.*
