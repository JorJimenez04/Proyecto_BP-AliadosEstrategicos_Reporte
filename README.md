# AdamoServices Partner Manager

Aplicación web profesional para la gestión de Banking Partners y Aliados Estratégicos.  
Desarrollada por el área de Compliance de AdamoServices.

## Stack Tecnológico

- **Lenguaje:** Python 3.10+
- **Frontend:** Streamlit
- **Base de Datos:** PostgreSQL (Docker local, Railway en producción)
- **Autenticación:** Basada en roles (RBAC)
- **Auditoría:** Log completo de cambios para cumplimiento regulatorio

## Estructura del Proyecto

```
AdamoServices_Partner_Manager/
├── app/                        # Lógica de la aplicación Streamlit
│   ├── main.py                 # Entry point principal
│   ├── auth/                   # Autenticación y control de acceso
│   ├── pages/                  # Páginas de la app (Dashboard, Partners, Pipeline, Auditoría)
│   ├── components/             # Componentes UI reutilizables
│   └── utils/                  # Funciones utilitarias
├── db/                         # Capa de datos
│   ├── database.py             # Gestor de conexión (SQLite / PostgreSQL)
│   ├── models.py               # Modelos de datos (Pydantic)
│   ├── repositories/           # Patrón Repository (CRUD desacoplado)
│   └── migrations/             # Scripts SQL de migración
├── config/                     # Configuración centralizada
│   └── settings.py
├── tests/                      # Suite de pruebas
├── data/                       # Archivo SQLite local (gitignored)
├── .env.example                # Variables de entorno de ejemplo
├── requirements.txt
└── README.md
```

## Módulos de Pipeline (Estados)

```
Prospecto → En Calificación → Onboarding → Activo → Suspendido → Terminado
```

## Roles de Acceso

| Rol              | Permisos                                                  |
|------------------|-----------------------------------------------------------|
| `admin`          | Acceso total. Gestión de usuarios.                        |
| `compliance`     | CRUD completo. Aprobación SARLAFT. Log de auditoría.      |
| `comercial`      | Crear prospectos. Editar campos comerciales.              |
| `consulta`       | Solo lectura.                                             |

## Ejecución en Local

**Requisito previo:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y en ejecución (solo para la BD).

**1. Levantar PostgreSQL**

```bash
docker compose up -d postgres
```

**2. Preparar entorno Python**

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
```

**3. Crear `.env` en la raíz del proyecto**

```env
APP_ENV=development
SECRET_KEY=cualquier_string_de_desarrollo_local
ADMIN_USERNAME=jorge_jimenez
ADMIN_PASSWORD=AdamoCompliance_2026!
ADMIN_EMAIL=compliance@adamoservices.co
DATABASE_URL=postgresql://adamo:adamo_dev_2026@localhost:5432/adamoservices
```

**4. Inicializar BD y ejecutar**

```bash
python -m db.database
streamlit run app/main.py
```

Acceder en `http://localhost:8501`.

Para detener la BD: `docker compose down`

## Instalación (resumen mínimo)

```bash
git clone https://github.com/tu-org/adamoservices-partner-manager.git
cd adamoservices-partner-manager
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
```

## Variables de Entorno

Ver `.env.example` para la lista completa y descripción de cada variable.

## Cumplimiento Regulatorio

Este sistema fue diseñado para soportar los requerimientos de:
- **SARLAFT** (Superintendencia Financiera de Colombia)
- **UIAF** — Reportes de operaciones sospechosas
- **Listas Restrictivas** — OFAC, ONU, UE

---
*AdamoServices — Compliance & Technology | [adamoservices.co](https://adamoservices.co)*
