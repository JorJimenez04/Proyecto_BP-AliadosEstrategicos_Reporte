# AdamoServices Partner Manager

Aplicación web profesional para la gestión de Banking Partners y Aliados Estratégicos.  
Desarrollada por el área de Compliance de AdamoServices.

## Stack Tecnológico

- **Lenguaje:** Python 3.10+
- **Frontend:** Streamlit
- **Base de Datos:** SQLite (local) → PostgreSQL (Railway en producción)
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

## Instalación

```bash
# 1. Clonar repositorio
git clone https://github.com/tu-org/adamoservices-partner-manager.git
cd adamoservices-partner-manager

# 2. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
copy .env.example .env
# Editar .env con tus valores

# 5. Inicializar base de datos
python -m db.database

# 6. Ejecutar aplicación
python -m streamlit run app/main.py
```

## Variables de Entorno

Ver `.env.example` para la lista completa de variables requeridas.

## Cumplimiento Regulatorio

Este sistema fue diseñado para soportar los requerimientos de:
- **SARLAFT** (Superintendencia Financiera de Colombia)
- **UIAF** — Reportes de operaciones sospechosas
- **Listas Restrictivas** — OFAC, ONU, UE

---
*AdamoServices — Compliance & Technology | [adamoservices.co](https://adamoservices.co)*
