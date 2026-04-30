# 🗂️ Estructura del Proyecto — AdamoServices Partner Manager

> Aplicación web de gestión de Banking Partners y Aliados Estratégicos.  
> Stack: Python 3.12 · Streamlit · PostgreSQL · SQLAlchemy (raw SQL) · Pydantic v2  
> Última actualización: 2026-04-30 (rev. 9)

---

## 📁 Árbol de archivos

```
Proyecto_PartnersStatus/
│
├── 📄 .env.example                    # Plantilla de variables de entorno (no subir .env al repo)
├── 📄 .gitignore                      # Exclusiones de Git (.env, .venv, __pycache__)
├── 📄 .dockerignore                   # Exclusiones del build Docker (.env, .venv, tests/)
├── 📄 Dockerfile                      # Imagen Docker basada en python:3.12-slim para Railway
├── 📄 entrypoint.sh                   # Script de arranque: production_check → migraciones → seed → Streamlit ($PORT)
│                                      # Paso 3 (nuevo): seed_test_users.py --password $ADMIN_PASSWORD
│                                      #   idempotente: ON CONFLICT DO NOTHING, nunca falla en redeploy
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
│   │                                  # _on_nav_radio_change() — callback on_change del radio
│   │                                  # sidebar() → tuple(page, agente_username | None)
│   │                                  #   _nav_opts construido condicionalmente por rol (RBAC):
│   │                                  #     CAN_CREATE_PARTNERS           → ➕ Nuevo Partner
│   │                                  #     admin/compliance               → 📋 Log de Auditoría
│   │                                  #     CAN_VIEW_AGENTES               → 👥 Gestión de Agentes
│   │                                  #     admin/compliance/comercial/consulta → 📚 Centro Documental
│   │                                  #   Expander "🏢 Equipos Operativos": carga agentes desde BD
│   │                                  #   nav_agente en session_state — nunca toca la clave del widget
│   │                                  # main() router — gatekeepers server-side antes de cada page_*()
│   │                                  #   bloquea Auditoría y Gestión de Agentes si rol insuficiente
│   │                                  #   📚 Centro Documental → page_compliance(user) (lazy import)
│   │                                  # page_nuevo_partner() · main()
│   │
│   ├── 📂 auth/                       # Sistema de autenticación y control de acceso
│   │   ├── 📄 __init__.py
│   │   └── 📄 login.py                # authenticate() — ENV → bcrypt BD → PLACEHOLDER_HASH (dev)
│   │                                  # login_screen() — st.form + rate-limiting progresivo
│   │                                  #   (delay 1-3 s + bloqueo 60 s tras 5 fallos consecutivos)
│   │                                  # require_auth() — gate de sesión, llama st.stop()
│   │                                  # logout() — borra cookie + limpia session_state + _logged_out=True
│   │                                  #   _logged_out flag bloquea restauración de cookie en el rerun
│   │                                  #   (fix: stx.CookieManager.delete() es asíncrono)
│   │                                  # check_active_session() — cm.get() antes de cm.delete()
│   │                                  #   try/except KeyError: evita crash si la cookie ya no existe
│   │                                  # SQL: activo = 1 (INTEGER — la columna no es BOOLEAN)
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
│   │   │                              #   try/except en get_by_id() con mensaje de error UI
│   │   │                              #   valores_anteriores/nuevos como dict (JSON real en log)
│   │   │                              # _panel_eliminar(): confirmación roja — solo ADMIN
│   │   │                              #   try/except protegido · valores_anteriores como dict
│   │   │                              # Auditoría automática en UPDATE y DELETE
│   │   │                              # _COLORES_RIESGO["Bajo"] = #5fe9d0 (cyan Adamo)
│   │   │                              # _pill() · _capacidad_badge() · _idx()
│   │   ├── 📄 audit_ui.py             # Log de Auditoría — page_auditoria()
│   │   │                              # Tabla paginada de log_auditoria
│   │   ├── 📄 alerts.py               # Centro de Notificaciones de Compliance
│   │   │                              # render_centro_notificaciones() — SARLAFT vencidas
│   │   │                              # Cards con botón ⚡ Acción Rápida (re-calificación)
│   │   │                              # Cards próximas revisiones 30 días · DDI (GAFI R.1/R.12)
│   │   ├── 📄 compliance_ui.py        # Centro Documental de Cumplimiento — page_compliance(user)
│   │   │                              # Accesible para roles: admin · compliance · comercial · consulta
│   │   │                              # Filtro empresa: Todas · Holdings BPO · PayCOP · Adamo Services
│   │   │                              # _kpi_cards(stats): 4 tarjetas (Total / Vigentes / Pendientes / Vencidos)
│   │   │                              # _doc_card(doc, puede_editar, key_prefix): tarjeta oscura con badges
│   │   │                              #   badge formato (PDF/DOCX/XLSX/PPTX/OTRO) · badge estado · badge empresa
│   │   │                              #   versión · fecha de emisión
│   │   │                              #   botón ✏️ Editar (solo admin/compliance): toggle formulario inline
│   │   │                              #   botón 🔗 Abrir: link directo en pestaña nueva
│   │   │                              #   limpieza automática de título: .replace('}','').strip() al guardar
│   │   │                              # _form_editar(doc): st.form — título · carpeta · empresa · estado
│   │   │                              #   versión · URL · descripción cambio (auditoría)
│   │   │                              #   st.rerun() tras guardar para reflejar cambios al instante
│   │   │                              # _form_nuevo_documento(user): expander + form — solo admin/compliance
│   │   │                              #   empresa pre-seleccionada y bloqueada cuando viene del filtro
│   │   │                              #   carpeta pre-seleccionada cuando viene de tab específica
│   │   │                              #   llama compliance_repo.crear()
│   │   │                              # page_compliance(user): carga stats + docs, KPI cards,
│   │   │                              #   tabs por carpeta (Todos + 11),
│   │   │                              #   tab Todos: panel ejecutivo con búsqueda, resumen por carpeta
│   │   │                              #     (barras de progreso + badges vencidos/pendientes),
│   │   │                              #     lista "Atención prioritaria" (Vencido/Pendiente)
│   │   │                              #   tabs carpeta: barra progreso · filtro estado · grid 3 cols
│   │   │                              #   formulario carga fijo debajo de tabs (solo empresa seleccionada)
│   │   │                              # Utilidades SharePoint/OneDrive: _is_onedrive_url() · _to_drive_preview()
│   │   │                              #   _to_drive_preview(): OneDrive /redir→/embed+em=2
│   │   │                              #     SharePoint (incl. holdingsbposas-my.sharepoint.com): +?action=embedview
│   │   │                              # Constantes: _CARPETA_ICON · _ESTADO_COLOR · _FORMATO_COLOR
│   │   │                              #             _EMPRESA_COLOR · _ALLOWED_ONEDRIVE · _SHAREPOINT_RE
│   │   │                              # _CARPETAS_ORDEN = [Politicas, Manuales, Onboarding,
│   │   │                              #   Procesos y Procedimientos, Governanza, Empresariales,
│   │   │                              #   Capacitacion, Contratos, Actas y Formatos, Matrices, Tecnologia]
│   │   └── 📄 agentes_ui.py           # Módulo INFORMATIVO de Equipos Operativos
│   │                                  #   (gerencia / líderes de equipo — los agentes NO acceden al sistema)
│   │                                  # EQUIPOS dict: 🛡️ Cumplimiento · 💸 Pagos · 🎧 Soporte (fallback estático)
│   │                                  # _EQUIPOS_COLORES · _EQUIPOS_ICONOS · _COLORES_RIESGO
│   │                                  # _USERNAME_TO_EQUIPO — mapa rápido username→equipo (fallback)
│   │                                  # _foto_base64(username) — busca en static/img/agentes/
│   │                                  #   formatos: .jpg .jpeg .png .webp
│   │                                  #   lee bytes + codifica Base64 → data-URI (compatible Railway)
│   │                                  #   try/except en read_bytes(): archivos corruptos → logger.warning
│   │                                  #   fallback: inicial del nombre con color del equipo
│   │                                  # _render_header_agente(): avatar circular border:3px + box-shadow
│   │                                  #   glow doble capa con color del equipo (0 0 12px / 0 0 24px)
│   │                                  #   aplica tanto a foto real como a avatar de inicial
│   │                                  # GESTIÓN DINÁMICA DE AVATARES:
│   │                                  # _foto_base64(username) — fallback filesystem → session_state → None
│   │                                  #   prioridad: static/img/agentes/<username>.ext > session upload
│   │                                  # _preview_avatar(data_uri, equipo_color) — círculo 52px con glow
│   │                                  # _seccion_foto_uploader(username, color, key, puede_subir)
│   │                                  #   st.file_uploader JPG/PNG → data-URI base64
│   │                                  #   auto-save al disco en local al seleccionar (sin clic extra)
│   │                                  #   producción: st.download_button para commit posterior
│   │                                  #   guarda en session_state[_foto_upload_{username}]
│   │                                  # _guardar_foto_agente(username) — persiste al filesystem local
│   │                                  # TARJETAS de equipo: botón 📷 Foto (solo admin) por cada agente
│   │                                  #   toggle _show_cam_{username} → abre uploader inline
│   │                                  # get_agentes_sidebar() — lee tabla agentes (fallback: EQUIPOS dict)
│   │                                  # render_perfil_agente(username, user):
│   │                                  #   Header: foto/avatar + nombre + cargo + badge equipo
│   │                                  #   Tab 📈 KPIs de Gestión: total/activos/riesgo_alto/tasa activación
│   │                                  #     2 Plotly pie (distribución riesgo + pipeline) + barra de meta
│   │                                  #   Tab 📋 Información: ficha contacto + notas
│   │                                  #     admin: form inline de edición (sin contraseña)
│   │                                  #   Tab 📅 Actividad: últimas acciones del sistema (log_auditoria)
│   │                                  #   Tab 🤖 IA Insights: análisis LLM de las últimas 5 gestiones
│   │                                  #     badge urgencia color-coded · resumen ejecutivo
│   │                                  #     red flags resaltadas en rojo · caché 30 min
│   │                                  #     botón 🔄 Refrescar (limpia caché IA del agente)
│   │                                  #     info de configuración si API key no está presente
│   │                                  # render_gestion_agentes(user): ADMIN y COMPLIANCE
│                                  #   puede_editar = rol in {ADMIN, COMPLIANCE}
│   │                                  #   Tab 🏢 Vista por Equipo: cards agrupadas por equipo
│   │                                  #   Tab ➕ Nuevo Colaborador: form sin contraseña → agente_repo.create()
│   │                                  #   Tab ✏️ Editar Colaborador: select + form → agente_repo.update()
│   │                                  # _kpi_card() · _section_title() · _render_header_agente()
│   │
│   ├── 📂 static/
│   │   └── 📂 img/
│   │       ├── 📂 logos/              # Logos corporativos (logo_adamo_blanco.* / logo_adamo_color.*)
│   │       └── 📂 agentes/            # Fotos de agentes — convención: <username>.(jpg|png|webp)
│   │                                  # Se leen como bytes y se incrustan como data-URI base64
│   │                                  # Agregar foto: copiar archivo y hacer git commit
│   │
│   └── 📂 utils/                      # Funciones auxiliares de utilidad
│       ├── 📄 __init__.py
│       ├── 📄 production_check.py     # Hardening pre-arranque (GAFI R.1 / CSBF Circular 027)
│       │                              # raise_if_insecure() · run_checks()
│       │                              # SECRET_KEY ≥ 43 chars · ADMIN_PASSWORD ≥ 16 chars
│       │                              # DATABASE_URL debe ser PostgreSQL · ADMIN_USERNAME/EMAIL presentes
│       └── 📄 ai_handler.py           # Motor centralizado de IA — Gemini / OpenAI
│                                      # AI_PROVIDER · GEMINI_KEY · OPENAI_KEY (desde .env)
│                                      # anonymize_text() — elimina NIT, CC, teléfonos, emails,
│                                      #   cuentas y nombres en MAYÚSCULAS antes de enviar a API
│                                      # analyze_gestion(context_data) → {urgencia, resumen, red_flags}
│                                      #   Prompt: Oficial de Cumplimiento SARLAFT
│                                      #   Proveedores: _call_gemini() / _call_openai()
│                                      #   Caché session_state con TTL 30 min (sha256 del texto)
│                                      #   Retorna ok=False (sin romper UI) si no hay API key
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
│   ├── 📄 sync_db.py                  # Script CLI de sincronización de migraciones
│   │                                  # Aplica scripts SQL en orden numérico y valida relaciones
│   │                                  # _run_migration(): reintenta hasta 3 veces (delay 3s) ante
│   │                                  #   errores de conexión — robusto ante cold-start Railway
│   │                                  # Uso: python db/sync_db.py [--only 005 006] [--check]
│   ├── 📄 models.py                   # Modelos Pydantic v2
│   │                                  # AliadoBase · AliadoCreate · AliadoUpdate · AliadoOut
│   │                                  # UsuarioBase · UsuarioCreate · UsuarioUpdate · UsuarioOut
│   │
│   ├── 📂 migrations/                 # Scripts SQL versionados (PostgreSQL · idempotentes)
│   │   ├── 📄 001_initial_schema_pg.sql          # Esquema inicial: tablas, índices y triggers
│   │   ├── 📄 002_add_corporate_metrics.sql       # Columnas gestión corporativa (estado_hbpocorp/adamo/paycop)
│   │   ├── 📄 003_fix_constraints_and_corporate_metrics.sql  # Fix constraints + perfil operativo
│   │   ├── 📄 004_agentes_perfil.sql              # foto_url · equipo · cargo en tabla usuarios
│   ├── 📄 005_tabla_agentes.sql              # Tabla agentes (catálogo sin credenciales)
│   │                                         #   + columna agente_id FK en aliados
│   │                                         #   + trigger updated_at · índices equipo/activo/agente_id
│   ├── 📄 006_kpi_fields.sql                 # Columnas KPI manuales en agentes (edición inline)
│   ├── 📄 007_kpi_history.sql                # Tabla historial diario de KPIs por agente
│   ├── 📄 008_cuentas_segmentadas.sql        # Segmentación cuentas: aprobadas/rechazadas/investigación
│   │                                         #   separadas entre tipo personal y comercial
│   ├── 📄 009_rbac_roles.sql                 # Jerarquía RBAC extendida — expande CHECK constraint
│   │                                         #   usuarios.rol: admin·compliance·comercial·consulta
│   ├── 📄 010_kpi_diario_observaciones.sql   # Añade columna observaciones TEXT a agente_kpi_diario
│   │                                         #   permite notas de campo en la bitácora diaria del agente
│   │   ├── 📄 011_compliance_documentos.sql      # Tabla compliance_documentos (solo DDL — sin seed)
│   │   │                                        #   carpetas: Politicas/Manuales/Onboarding/
│   │   │                                        #     Procesos y Procedimientos/Governanza/
│   │   │                                        #     Empresariales/Capacitacion/Contratos/
│   │   │                                        #     Actas y Formatos/Matrices/Tecnologia
│   │   │                                        #   estados: Vigente/Pendiente/Vencido/Archivado
│   │   │                                        #   trigger updated_at · índices carpeta/estado/codigo
│   │   ├── 📄 012_compliance_empresa.sql         # Columna empresa en compliance_documentos
│   │   │                                        #   entidades: Holdings BPO · PayCOP · Adamo Services · NULL (Compartido)
│   │   ├── 📄 013_cleanup_seed_documentos.sql   # Limpieza idempotente de docs seed (creado_por='sistema')
│   │   │                                        #   DELETE + RESTART SEQUENCE si tabla queda vacía
│   │   ├── 📄 014_rename_carpeta_etica.sql       # Renombra carpeta 'Etica' → 'Procesos y Procedimientos'
│   │   │                                        #   UPDATE filas + DROP/ADD CHECK constraint
│   │   ├── 📄 015_rename_carpeta_riesgos.sql     # Renombra carpeta 'Riesgos' → 'Governanza'
│   │   │                                        #   UPDATE filas + DROP/ADD CHECK constraint
│   │   └── 📄 016_add_nuevas_carpetas.sql        # Amplía CHECK constraint con 4 nuevas carpetas
│                                                #   Contratos · Actas y Formatos · Matrices · Tecnologia
│   │
│   └── 📂 repositories/              # Patrón Repository — CRUD desacoplado de la UI
│       ├── 📄 __init__.py
│       ├── 📄 partner_repo.py         # CRUD completo de aliados
│       │                              # create() — inserta + calcula puntaje_riesgo automático
│       │                              # update() — recalcula puntaje_riesgo si toca campos SARLAFT
│       │                              #   _CAMPOS_RIESGO: es_pep · crypto_friendly · adult_friendly
│       │                              #   estado_sarlaft · estado_due_diligence · contrato_firmado
│       │                              #   listas_verificadas · lista_ofac_ok · rut_recibido
│       │                              #   camara_comercio_recibida · permite_monetizacion
│       │                              # get_by_id() · delete()
│       │                              # get_lista_enriquecida() · get_stats_pipeline()
│       │                              # get_stats_riesgo() · get_sarlaft_vencidas()
│       │                              # get_revisiones_proximas(dias=30)
│       │                              # get_salud_grupo() · get_stats_capacidades()
│       │                              # get_termometro_sarlaft() · get_resumen_volumen()
│       │                              # get_partners_por_empresa(empresa)
│       │                              # calcular_puntaje_riesgo() — rubrica SARLAFT-compatible
│       ├── 📄 audit_repo.py           # Log de auditoría inmutable (solo escritura/lectura)
│       │                              # registrar() — normaliza resultado · convierte dict a JSON
│       │                              #   acepta valores_anteriores/nuevos como dict (no str)
│       │                              #   usuario_id=0 → NULL (FK safe)
│       │                              # list_log() · get_actividad_usuario()
│       ├── 📄 compliance_repo.py      # CRUD de compliance_documentos
│       │                              # get_stats(empresa=None) — totales por estado + por_carpeta
│       │                              #   por_carpeta incluye: total · vigentes · pendientes · vencidos
│       │                              # get_documentos(carpeta, estado, empresa) — filtros opcionales
│       │                              # get_by_id() · crear(data, creado_por) → int
│       │                              # actualizar(doc_id, data, actualizado_por)
│       │                              # nueva_version(doc_id, version, url, descripcion, user)
│       │                              #   UPDATE + audit_repo.registrar() automático
│       │                              # archivar(doc_id, actualizado_por) — soft delete (→ Archivado)
│       ├── 📄 agente_repo.py          # Catálogo de colaboradores operativos (sin credenciales)
│       │                              # get_all_active() · get_all() · get_by_username() · get_by_id()
│       │                              # username_exists() · create() · update() (whitelist _CAMPOS_EDITABLES)
│       │                              # get_metrics(agente_id) — KPIs desde aliados.agente_id:
│       │                              #   total_partners · partners_activos · partners_riesgo_alto
│       │                              #   tasa_activacion_pct · distribucion_riesgo · distribucion_estado
│       │                              # get_compliance_kpis(agente_id) — docs/cuentas/sanciones/SARLAFT
│       │                              # get_kpi_table() · update_kpis_from_editor() — editor inline
│       │                              # get_kpi_diario() · upsert_kpi_diario() — bitácora diaria
│       │                              # registrar_gestion_diaria() — upsert + auditoría
│       │                              # get_recent_gestiones(agente_id, limit=5) — para análisis IA
│       │                              #   retorna tipo, riesgo, pipeline, SARLAFT, PEP, listas,
│       │                              #   alertas, observaciones; nombre parcialmente enmascarado
│       ├── 📄 user_repo.py            # CRUD de usuarios del sistema (con bcrypt)
│       │                              # create_user() · update_user() · get_by_username()
│       │                              # activo = 1 (INTEGER) en inserts y queries
│       └── 📄 seed_test_users.py      # Seed idempotente de usuarios de prueba (RBAC)
│                                      # Modos: PLACEHOLDER_HASH (dev) · bcrypt real (prod)
│                                      #   --password CLI > ADMIN_PASSWORD env > modo dev
│                                      # ON CONFLICT (username) DO NOTHING — nunca falla en redeploy
│                                      # Usuarios: test_compliance · test_comercial · test_consulta
│                                      # Llamado automáticamente por entrypoint.sh en cada deploy
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
- **Tabla por tarjetas**: pills de colores (pipeline/riesgo/SARLAFT) + badges capacidades operativas
- **Edición inline** (ADMIN / COMPLIANCE / COMERCIAL): formulario 3 secciones; campos compliance deshabilitados para rol `comercial`; `try/except` en carga de BD; `valores_anteriores` como `dict` real (JSON correcto en log)
- **Eliminación** (solo ADMIN): panel confirmación con borde rojo + auditoría `DELETE`; `valores_anteriores=dict(aliado)`
- Fila activa resaltada: cian = editando · rojo = eliminando

### Log de Auditoría (`app/components/audit_ui.py`)
- Tabla paginada de `log_auditoria` — acciones CREATE · UPDATE · DELETE · LOGIN · EXPORT

### 📚 Centro Documental de Cumplimiento (`app/components/compliance_ui.py`)
Repositorio centralizado de documentos regulatorios de ADAMO Services.

- Accesible para todos los roles (admin · compliance · comercial · consulta)
- **Edición** (nueva versión, nuevo documento) restringida a `admin` y `compliance`
- **Filtro por empresa**: Todas · Holdings BPO · PayCOP · Adamo Services

**11 carpetas:**

| Icono | Carpeta |
|---|---|
| 📋 | Politicas |
| 📖 | Manuales |
| 🔗 | Onboarding |
| ⚙️ | Procesos y Procedimientos |
| 🛡️ | Governanza |
| 🏢 | Empresariales |
| 🎓 | Capacitacion |
| 📝 | Contratos |
| 📑 | Actas y Formatos |
| 📊 | Matrices |
| 💻 | Tecnologia |

**Estados de documento:** `Vigente` · `Pendiente` · `Vencido` · `Archivado` (soft delete)  
**Formatos:** `PDF` · `DOCX` · `XLSX` · `PPTX` · `OTRO`

**Tab "Todos" — Panel ejecutivo:**
- Búsqueda en tiempo real por nombre/código/descripción
- Resumen por carpeta con barra de progreso y badges de alertas (vencidos/pendientes)
- Lista "Requieren atención" — documentos `Vencido` o `Pendiente` ordenados por urgencia

**Acciones por tarjeta:**
- **✏️ Editar** (solo admin/compliance): abre formulario inline con todos los metadatos; `st.rerun()` al guardar
- **🔗 Abrir**: `st.link_button` que abre el documento en pestaña nueva

**Flujo de edición:**
1. Clic "✏️ Editar" → toggle `_nv_open_{id}` en session_state
2. `_form_editar()` → `compliance_repo.actualizar()` + `audit_repo.registrar()`
3. `st.rerun()` automático para reflejar cambios en la grilla

---

### 🏢 Equipos Operativos (`app/components/agentes_ui.py`)
Módulo **informativo** para gerencia y líderes de equipo. Los agentes son entradas del catálogo — **no tienen acceso al sistema**.

- Accesible desde el expander **🏢 Equipos Operativos** del sidebar (todos los roles)
- Página **👥 Gestión de Agentes** en el menú principal (solo `admin`)

**Fuente de datos:** tabla `agentes` (BD). Fallback al catálogo estático `EQUIPOS` si la tabla está vacía.

**Estructura del equipo (catálogo estático de respaldo):**

| Equipo | Color | Colaboradores |
|---|---|---|
| 🛡️ Cumplimiento | `#5fe9d0` | Samuel Mora · Laura Cano · Daniel Reyes |
| 💸 Pagos | `#7839ee` | Andrea Ospina · Carlos Méndez |
| 🎧 Soporte | `#f59e0b` | Sofía Villa · Miguel Torres |

**Perfil de colaborador (`render_perfil_agente(username, user)`):**
- **Foto**: `app/static/img/agentes/<username>.(jpg|jpeg|png|webp)` → data-URI base64; fallback = inicial con color del equipo
- **Tab KPIs**: `total_partners`, `partners_activos`, `partners_riesgo_alto`, `tasa_activacion_pct` (desde `aliados.agente_id`); 2 pie charts Plotly (riesgo + pipeline); barra de prog. vs `meta_mensual_gestiones`
- **Tab Información**: email · teléfono · notas; admin puede editar sin contraseña

**Gestión del catálogo (`render_gestion_agentes(user)`) — solo `admin`:**
- Vista por equipo (cards), Nuevo Colaborador (sin contraseña), Editar Colaborador
- Toda acción registra auditoría en `log_auditoria` con `valores_anteriores` / `valores_nuevos`

**Asignación partner → agente:** desde la UI de Partners, campo `agente_id` en `aliados`.

**Agregar foto de un agente:**
```bash
# Copiar el archivo con el username exacto como nombre
cp foto.jpg app/static/img/agentes/samuel_mora.jpg
git add app/static/img/agentes/
git commit -m "feat: foto agente samuel_mora"
git push origin main   # Railway reconstruye la imagen con la foto incluida
```

---

## 👥 Roles de Acceso (RBAC)

| Rol           | Dashboard | Ver Partners | Crear/Editar | Cambiar Estado | Auditoría | Eliminar | Equipos | Gestión Agentes | Centro Documental |
|---------------|:---------:|:------------:|:------------:|:--------------:|:---------:|:--------:|:-------:|:---------------:|:-----------------:|
| `admin`       | ✅        | ✅           | ✅           | ✅             | ✅        | ✅       | ✅      | ✅              | ✅ (editar)       |
| `compliance`  | ✅        | ✅           | ✅           | ✅             | ✅        | ❌       | ✅      | ✅              | ✅ (editar)       |
| `comercial`   | ✅        | ✅           | Parcial      | Parcial        | ❌        | ❌       | ✅      | ❌              | ✅ (solo lectura) |
| `consulta`    | ✅        | ✅           | ❌           | ❌             | ❌        | ❌       | ✅      | ❌              | ✅ (solo lectura) |

---

## 🚀 Comandos útiles

```bash
# ── Desarrollo local ──────────────────────────────────────────
# Instalar dependencias
pip install -r requirements.txt

# Inicializar / resetear la base de datos
python -m db.database

# Aplicar todas las migraciones pendientes
python db/sync_db.py

# Aplicar migraciones específicas
python db/sync_db.py --only 008 009

# Solo validar que las tablas críticas existen (sin aplicar nada)
python db/sync_db.py --check

# Ejecutar la aplicación en local (usar ejecutable del venv en Windows)
.venv\Scripts\streamlit.exe run app/main.py --server.port 8501

# Verificar variables de producción (sin arrancar la app)
python app/utils/production_check.py

# Generar SECRET_KEY de 256 bits (43 chars URL-safe)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generar ADMIN_PASSWORD de alta entropía (20 chars)
python -c "import secrets, string; a=string.ascii_letters+string.digits+'!@#%&*'; print(''.join(secrets.choice(a) for _ in range(20)))"

# ── Base de datos Docker ──────────────────────────────────────
docker compose up -d postgres     # Levantar PostgreSQL local
docker compose down               # Detener
docker compose down -v            # Detener + borrar volumen de datos

# ── Fotos de agentes ──────────────────────────────────────────
# Agregar foto: nombre de archivo = username exacto del agente
cp foto.jpg app/static/img/agentes/<username>.jpg
git add app/static/img/agentes/
git commit -m "feat: foto agente <username>"
git push origin main              # Railway reconstruye con la foto incluida

# ── Seed manual contra Railway (opcional) ────────────────────
# El entrypoint.sh ya ejecuta el seed automáticamente en cada deploy.
# Solo usar esto si necesitas insertar usuarios sin redesplegar:
$env:DATABASE_URL="postgresql://usuario:password@host.railway.app:5432/railway"
.venv\Scripts\python.exe db/seed_test_users.py --password $env:ADMIN_PASSWORD

# ── Deploy a Railway ──────────────────────────────────────────
# Railway usa auto-deploy desde GitHub (rama main)
# El entrypoint.sh ejecuta: production_check → db.database → seed → streamlit
git add .
git commit -m "mensaje"
git push origin main
```
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
| `AI_PROVIDER`         | Ambos           | Proveedor LLM activo                      | `gemini` (default) · `openai`            |
| `GEMINI_API_KEY`      | Ambos           | API key de Google AI Studio               | [aistudio.google.com](https://aistudio.google.com/apikey) · tier gratuito |
| `GEMINI_MODEL`        | Ambos           | Modelo Gemini a usar                      | `gemini-1.5-flash`                       |
| `OPENAI_API_KEY`      | Ambos           | API key de OpenAI (alternativa)           | Solo si `AI_PROVIDER=openai`             |
| `OPENAI_MODEL`        | Ambos           | Modelo OpenAI a usar                      | `gpt-4o-mini`                            |

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
- **Logout**: `_logged_out=True` en session_state bloquea restauración de cookie hasta el siguiente login exitoso
- **CookieManager.delete()**: siempre verificar con `cm.get()` antes de llamar `cm.delete()` — lanza `KeyError` si la cookie no existe en el dict interno
- **activo**: columna `INTEGER` (1/0) en tabla `usuarios` — nunca comparar con `true`/`false` en SQL
- **Rate-limiting**: `st.session_state["login_fails"]` + `login_locked_until` — bloqueo 60 s tras 5 fallos
- **Pool BD**: `QueuePool` en PostgreSQL (pool_size=5, pool_recycle=30min)
- **EBR**: registros ordenados por riesgo descendente (Muy Alto → Alto → Medio → Bajo) según GAFI R.1
- **Componentes UI**: lógica de negocio visual en `app/components/` — importados lazy dentro de `page_*()`
- **Session State edición**: `st.session_state["edit_id"]` / `st.session_state["delete_id"]` para acciones en tabla
- **Acción Rápida**: `cambiar_estado()` + `AuditRepository.registrar()` siempre en el mismo bloque try/finally
- **Docker**: `.dockerignore` excluye `.env`, `.venv` y tests del contenedor de producción
- **Fotos de agentes**: el archivo debe llamarse exactamente `<username>.jpg` (todo minúsculas) — Linux/Railway es case-sensitive. Convención: `adrian_c.jpg` para username `adrian_c`
- **Avatar upload**: `_seccion_foto_uploader()` auto-save al disco en local al seleccionar el archivo — no se requiere botón extra. En producción, ofrece `st.download_button` para commit manual
- **IA Insights**: `ai_handler.analyze_gestion()` anonimiza PII con regex antes de enviar a la API. Caché en `session_state` (TTL 30 min, clave = sha256 del texto). La pestaña funciona en modo degradado (sin romper UI) si `AI_PROVIDER` o API key no están configurados

---

*AdamoServices S.A.S. · Compliance & Technology · [adamoservices.co](https://adamoservices.co)*
