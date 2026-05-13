# 🗂️ Estructura del Proyecto — AdamoServices Partner Manager

> Aplicación web de gestión de Banking Partners y Aliados Estratégicos.  
> Stack: Python 3.12 · Streamlit · PostgreSQL · SQLAlchemy (raw SQL) · Pydantic v2  
> Última actualización: 2026-05-13 (rev. 17)

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
│   │                                  #   _nav_opts: entrada única 🤝 Gestión de Alianzas (todos)
│   │                                  #     admin/compliance               → 📋 Log de Auditoría
│   │                                  #     CAN_VIEW_AGENTES               → 👥 Gestión de Agentes
│   │                                  #     admin/compliance/comercial/consulta → 📚 Centro Documental
│                                      #     CAN_VIEW_CRYPTO (admin/compliance) → 🛡️ Cripto Compliance
│                                      #   Expander "🏢 Equipos Operativos": carga agentes desde BD
│                                      #   nav_agente en session_state — nunca toca la clave del widget
│                                      # main() router — gatekeepers server-side antes de cada page_*()
│                                      #   🤝 Gestión de Alianzas → page_alianzas(user) (lazy import)
│                                      #   bloquea Auditoría y Gestión de Agentes si rol insuficiente
│                                      #   📚 Centro Documental → page_compliance(user) (lazy import)
│                                      #   🛡️ Cripto Compliance → page_crypto_compliance(user) (lazy import)
│                                      #     RBAC: CAN_VIEW_CRYPTO = {admin, compliance}
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
│   │   ├── 📄 partners_ui.py          # 🤝 Gestión de Alianzas — módulo maestro Banking Partners Hub
│   │                              # page_alianzas(user): entrada principal — 3 pestañas dinámicas st.tabs
│   │                              #   📊 Monitor    → page_dashboard(user)
│   │                              #   📋 Portafolio → page_partners(user)
│   │                              #   ➕ Alta de Partner → _tab_alta_partner(user) [CAN_CREATE solo]
│   │   │                              # Banner de éxito post-creación: _alianzas_nuevo_partner en session_state
│   │   │                              # st.toast() al registrar + st.success() en próximo render
│   │   │                              # page_partners(user): tabla tarjetas con filtros y KPIs
│   │   │                              #   Filtros: Estado · Riesgo · Búsqueda · PEP
│   │   │                              #   Métricas rápidas: Total · Activos · Alto Riesgo · PEPs
│   │   │                              # _panel_editar(): formulario inline 3 secciones
│   │   │                              #   (Básica / Relación Corporativa / Perfil Operativo)
│   │   │                              #   Editar: ADMIN / COMPLIANCE / COMERCIAL
│   │   │                              #   Campos SARLAFT/riesgo/PEP deshabilitados para rol comercial
│   │   │                              #   try/except en get_by_id() con mensaje de error UI
│   │   │                              #   valores_anteriores/nuevos como dict (JSON real en log)
│   │   │                              # _panel_eliminar(): confirmación roja — solo ADMIN
│   │   │                              #   try/except protegido · valores_anteriores como dict
│   │   │                              # _tab_alta_partner(user): formulario 4 secciones (Alta de Partner)
│   │   │                              #   Identificación · Relación Corporativa · Perfil Operativo · Compliance
│   │   │                              #   AliadoCreate + repo.create() + audit.registrar()
│   │   │                              #   clear_on_submit=True · st.toast() en éxito
│   │   │                              # _tab_analisis_riesgo(user): análisis SARLAFT + riesgo
│   │   │                              #   Termómetro SARLAFT · Distribución riesgo · Pipeline estados
│   │   │                              #   Lista vencidos SARLAFT · Lista revisiones próximas 30d
│   │   │                              #   Rol comercial: banner read-only (sin cambios de estado)
│   │   │                              # Auditoría automática en CREATE / UPDATE / DELETE
│   │   │                              # _COLORES_RIESGO["Bajo"] = #5fe9d0 · _pill() · _capacidad_badge()
│   │   ├── 📄 audit_ui.py             # Log de Auditoría — page_auditoria()
│   │   │                              # Tabla paginada de log_auditoria
│   │   ├── 📄 alerts.py               # Centro de Notificaciones de Compliance
│   │   │                              # render_centro_notificaciones() — SARLAFT vencidas
│   │   │                              # Cards con botón ⚡ Acción Rápida (re-calificación)
│   │   │                              # Cards próximas revisiones 30 días · DDI (GAFI R.1/R.12)
│   │   ├── 📄 crypto_ui.py            # 🛡️ Cripto Compliance — VASP Monitor (Global Ledger)
│   │   │                              # Acceso: solo admin y compliance (RBAC)
│   │   │                              # page_crypto_compliance(user): 4 tabs
│   │   │                              #   👥 Clientes (tab_clientes) → _tab_clientes(user):
│   │   │                              #     Vinculador inline: si show_vinculador en session_state,
│   │   │                              #       muestra _form_nueva_wallet() antes del listado + botón cancelar
│   │   │                              #     Registro de clientes corporativos (crypto_clientes)
│   │   │                              #     Cards HTML con razon_social · NIT · representante
│   │   │                              #     Expander por cliente: wallets vinculadas + exposure
│   │   │                              #     Botones por cliente (2 columnas):
│   │   │                              #       📋 Ver en Monitor → filtro crypto_cliente_filtro
│   │   │                              #       ➕ Vincular Wallet → activa show_vinculador + rerun
│   │   │                              #     Formulario crear cliente (CryptoClienteCreate)
│   │   │                              #   📋 Monitor de Wallets (tab_monitor):
│   │   │                              #     filtros: nivel riesgo · blockchain · solo_criticos · texto
│   │   │                              #     búsqueda textual incluye razon_social via JOIN
│   │   │                              #     _card_wallet(): score-bar GL, pill nivel, badge labels,
│   │   │                              #       exposure USD, botón 📋 Ver Ficha
│   │   │                              #     _ficha_wallet(): panel detalle 3 tabs
│   │   │                              #       📊 Resumen: score-bar, exposure, cliente, metadatos
│   │   │                              #       🚩 Risk Labels: lista con color por severidad
│   │   │                              #         labels críticos: Sanctioned Exchange, OFAC, Darknet,
│   │   │                              #         Ransomware, Scam, Terrorism Financing, Mixer, etc.
│   │   │                              #       📝 Notas & Reporte: link_button PDF · notas internas
│   │   │                              #   📈 Monitoreo Semanal (tab_monitoreo) → _tab_monitoreo_semanal(user):
│   │   │                              #     Selectbox de todas las wallets (label: cliente — addr · chain · nivel)
│   │   │                              #     _render_comparativo(current_record): métricas delta vs snapshot anterior
│   │   │                              #       st.metric con delta: GL score · SoF score · UoF score · exposure
│   │   │                              #       muestra "Estado Actual (se archivará al guardar)"
│   │   │                              #     st.file_uploader PDF (fuera del form, key mon_pdf_upload)
│   │   │                              #     Área weekly_delta: resumen de cambios de la semana
│   │   │                              #     st.form("form_monitoreo_semanal"): Pasos 2-4
│   │   │                              #       Paso 2: SoF (tipo_riesgo, indicador, naturaleza, profundidad,
│   │   │                              #         cont_directa/indirecta/total, score, nivel, monto)
│   │   │                              #       Paso 3: UoF (indicador, naturaleza, profundidad,
│   │   │                              #         cont_directa/indirecta/total, score, nivel, monto)
│   │   │                              #       Paso 3b: GL Validation (selectbox GL labels, GL score manual)
│   │   │                              #       Paso 4: Conclusión (analyst_observations, monitoring_analyst,
│   │   │                              #         final_risk_score, final_risk_level, wallet_status)
│   │   │                              #     Submit: CryptoRepository.monitor_wallet() — archiva + actualiza
│   │   │                              #     Widget keys prefijados "mon_" para evitar colisiones
│   │   │                              #   📊 Reporte Gerencial (tab_gerencial):
│   │   │                              #     render_gerencial_crypto(session):
│   │   │                              #       selectbox filtro por cliente (todos o específico)
│   │   │                              #       4 KPI cards: total · exposure USD · atención · críticas
│   │   │                              #       Pie chart distribución riesgo (Plotly)
│   │   │                              #       Bar chart distribución por blockchain
│   │   │                              #       Tabla atención prioritaria (score<30 o Crítico/Alto)
│   │   │                              # Helpers internos:
│   │   │                              #   _form_nueva_wallet(user, cliente_id, cliente_nombre):
│   │   │                              #     Formulario de PRIMERA vinculación (cliente pre-fijado)
│   │                                  #     📤 Carga PDF GL → crypto_parser.parse_gl_pdf() → auto-fill:
│   │                                  #       📅 Fecha Reporte: ISO detectada del texto o del
│   │                                  #         nombre de archivo (DD-MM-YYYY / YYYY-MM-DD)
│   │                                  #         widget deshabilitado si detectado desde PDF
│   │                                  #       Nivel GL: derivado del score o nivel texto;
│   │                                  #         st.text_input disabled si viene del PDF,
│   │                                  #         st.selectbox si no hay detección PDF
│   │                                  #       📥 Source of Funds (Global): campo read-only
│   │                                  #         muestra monto USD (>0) o % exposición
│   │                                  #       📤 Use of Funds (Global): campo read-only
│   │                                  #     Risk Exposure — dos tablas lado a lado:
│   │                                  #       _render_exposure_table(rows, title, color)
│   │                                  #       📥 SoF (col izq) · 📤 UoF (col der)
│   │                                  #       st.dataframe sin columna "type" · 0.0 → None
│   │                                  #       emoji de nivel en columna level
│   │                                  #     Métricas SoF/UoF: % como valor primario,
│   │                                  #       monto USD como delta (delta_color="off")
│   │                                  #     💰 Exposición Total (_exp_pdf = max(sof_amt, uof_amt)):
│   │                                  #       🟢 deshabilitado y pre-rellenado si PDF tiene montos
│   │                                  #       🟡 captura manual si PDF no reporta montos
│   │                                  #     Moneda exposición: selectbox USD/EUR/USDT/USDC (🟡 manual)
│   │   │                              #     Llama CryptoRepository.create_wallet() — INSERT puro
│   │   │                              #     Captura ValueError en duplicado · borra show_vinculador al éxito
│   │   │                              #     Widget keys sufijadas _{cliente_id} para soporte multi-cliente
│   │   │                              #   _render_comparativo(prev, new_gl_score):
│   │   │                              #     Compara snapshot historial vs valores actuales/nuevos
│   │   │                              #     4 st.metric con delta coloreado
│   │   │                              #   _field_label(text, from_pdf) → str — prefija 🟢 (PDF) o 🟡 (manual)
│   │   │                              #     aplicado a todos los labels de _form_nueva_wallet
│   │   │                              #   _parse_gl_opt(opt) · _parse_labels()
│   │   │                              #   _pill() · _score_bar() · _card_wallet() · _ficha_wallet()
│   │   │                              # Cache: _get_clientes_cached(ttl=300) · _get_wallets_cached()
│   │   │                              # Paleta: Crítico=#ef4444 · Alto=#f97316 · Medio=#f59e0b
│   │   │                              #   Bajo=#22c55e · Sin Datos=#6b7280
│   │   │                              # Iconos blockchain: ⟠ETH · ₿BTC · 🔶BNB · 🔴TRX · ◎SOL
│   │   │                              # Constantes módulo: _GL_SELECTBOX · _GL_OPTS_NONE · _COLOR_NIVEL
│   │   │                              #   _BLOCKCHAIN_ICONS · _LABELS_CRITICOS
│   │   ├── 📄 compliance_ui.py        # Centro Documental de Cumplimiento — page_compliance(user)
│   │   │                              # Accesible para roles: admin · compliance · comercial · consulta
│   │   │                              # Filtro empresa: Todas · Holdings BPO · PayCOP · Adamo Services
│   │   │                              # _kpi_cards(stats): 4 tarjetas (Total / Vigentes / Pendientes / Vencidos)
│   │   │                              # _doc_card(doc, puede_editar, key_prefix): tarjeta oscura con badges
│   │   │                              #   badge formato (PDF/DOCX/XLSX/PPTX/OTRO) · badge estado · badge empresa
│   │   │                              #   versión · fecha de emisión
│   │   │                              #   CON url: ✏️ Editar (solo editors) | 🔗 Abrir (link_button, pestaña nueva)
│   │   │                              #   SIN url: editors → ✏️ Editar + texto «Sin enlace — añade la URL en ✏️ Editar»
│   │   │                              #            lectura → texto «Sin enlace — requiere URL para habilitar el acceso»
│   │   │                              #   limpieza automática de título: .replace('}','').strip() al guardar
│   │   │                              #   SIN iframes ni previsualización embebida (prohibido)
│   │   │                              #   📜 Historial de cambios — expander narrativo con diff automático
│   │   │                              #     _diff_campos(antes, despues) detecta: versión · estado · URL
│   │   │                              #       fecha_emision · título · empresa
│   │   │                              #     _fmt_narrativa(dt) → "el 14 de abril de 2026"
│   │   │                              #     "🕐 el X de mes de YYYY, username editó este documento."
│   │   │                              #     "↳ campo: \"antes\" → \"después\""
│   │   │                              # _form_editar(doc): st.form — título · carpeta · empresa · estado
│   │   │                              #   versión · 📅 fecha de emisión (date_input) · URL · descripción cambio
│   │   │                              #   st.rerun() tras guardar para reflejar cambios al instante
│   │   │                              # _form_nuevo_documento(user): expander + form — solo admin/compliance
│   │   │                              #   campo «URL del documento» (acepta cualquier URL, no solo OneDrive)
│   │   │                              #   _is_onedrive_url() solo para warning no-bloqueante si no es SharePoint
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
│   │   │                              # Utilidades: _is_onedrive_url() — warning no-bloqueante en creación
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
│       ├── 📄 crypto_parser.py        # Parser PDF — Reportes Global Ledger (pdfplumber)
│       │                              # parse_gl_pdf(file_like) → dict con claves:
│       │                              #   gl_score · riesgo_nivel · risk_labels[]
│       │                              #   sof_total_amount · sof_total_pct
│       │                              #   uof_total_amount · uof_total_pct
│       │                              #   risk_exposure[] — lista de rows con type/indicator/
│       │                              #     depth/direct_pct/indirect_pct/total_pct/amount/level
│       │                              #   report_date (ISO str YYYY-MM-DD o None)
│       │                              #   gl_level (str: Bajo/Medio/Alto/Crítico/Sin Datos o None)
│       │                              #   gl_risk_level_text — detección raw desde texto
│       │                              # Regexes de módulo:
│       │                              #   _GL_SCORE_RE — captura "gl score: 47" / "47/100"
│       │                              #   _GL_SCORE_FRACTION_RE — fallback "47/100"
│       │                              #   _GL_RISK_LEVEL_RE — critical/high/medium/low/
│       │                              #     bajo/medio/alto/crítico + variantes i18n
│       │                              #   _REPORT_DATE_RE — fecha en múltiples formatos
│       │                              #     (ISO, DD/MM/YY, nombre de mes EN/ES)
│       │                              # _parse_report_date(raw) → str|None — normaliza a ISO
│       │                              # GL Level derivado de score (≤30→Bajo, ≤60→Medio, >60→Alto)
│       │                              #   fallback: texto detectado por _GL_RISK_LEVEL_RE
│       │                              # flow mapping: unknown → ["SoF","UoF"] (ambas tablas)
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
│                                      # Jurisdicciones.ALL (~45 países con emoji) · Jurisdicciones.ALTO_RIESGO
│                                      #   (GAFI blacklist: Irán · Corea del Norte · Cuba · Venezuela · offshore)
│                                      # Roles.CAN_EDIT_JURISDICTIONS = frozenset({"admin","compliance"})
│                                      # Roles.CAN_EDIT_COMPLIANCE    = frozenset({"admin","compliance"})
│                                      # Roles.CAN_VIEW_CRYPTO        = frozenset({"admin","compliance"})
│                                      # TiposRiel: Dispersión · Recaudo · Crypto · Mixto · N/A
│                                      # NivelesCriticidad: DDI - Entidad Regulada · DDI · DDS-Alto
│                                      #   DDS-Simplificado · Estándar (ISO/GAFI operativo)
│                                      # CertificacionesISO: ISO 27001 · PCI-DSS · SOC 2 · ISO 9001 · ISO 20000
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
│   │                                  # ALL_MIGRATIONS: lista explícita 001–023 (orden de aplicación)
│   │                                  # Uso: python db/sync_db.py [--only 005 006] [--check]
│   ├── 📄 models.py                   # Modelos Pydantic v2
│   │                                  # AliadoBase · AliadoCreate · AliadoUpdate · AliadoOut
│   │                                  # UsuarioBase · UsuarioCreate · UsuarioUpdate · UsuarioOut
│   │                                  # AliadoBase.jurisdicciones: List[str] = [] (campo de dominio)
│   │                                  # AliadoUpdate.jurisdicciones: Optional[List[str]] = None
│   │                                  # — Ficha Técnica del Riel (migración 018) —
│   │                                  # AliadoBase: tipo_riel · sla_garantizado · numero_licencia
│   │                                  #   fecha_ultima_auditoria · certificaciones[] · es_entidad_regulada
│   │                                  #   partner_respaldo · pct_concentracion · nivel_criticidad
│   │                                  #   validator nivel_criticidad tolerante (None → 'Estándar')
│   │                                  # — Cripto Compliance (migración 019) —
│   │                                  # RiskLabel: label · exposure_pct · source
│   │                                  # WalletMonitorCreate: wallet_address · blockchain · client_id
│   │                                  #   crypto_cliente_id (FK) · gl_score(0-100) · riesgo_nivel
│   │                                  #   risk_labels[RiskLabel] · total_exposure · pdf_report_url
│   │                                  #   last_report_date · validator: normaliza address, calcula nivel
│   │                                  # — SoF/UoF y Conclusión (migración 021) —
│   │                                  # WalletMonitorCreate: sof_tipo_riesgo · sof_indicador · sof_naturaleza
│   │                                  #   sof_profundidad · sof_cont_directa/indirecta/total · sof_score
│   │                                  #   sof_nivel · sof_monto — igual para uof_*
│   │                                  #   analyst_observations · monitoring_analyst
│   │                                  #   final_risk_score · final_risk_level · wallet_status
│   │                                  # — Monitoreo Semanal (migración 022) —
│   │                                  # WalletMonitorCreate: weekly_delta Optional[str]
│   │                                  # WalletMonitorOut: modelo completo de salida
│   │                                  # — Clientes Corporativos Cripto (migración 020) —
│   │                                  # CryptoClienteCreate: razon_social · nit · representante_legal
│   │                                  #   correo_corporativo · telefono · direccion
│   │                                  #   fecha_onboarding · notas · creado_por
│   │                                  # CryptoClienteOut: todos los campos de Create + id
│   │                                  #   created_at · updated_at · total_wallets=0 · exposure_total=0.0
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
│   │   ├── 📄 016_add_nuevas_carpetas.sql        # Amplía CHECK constraint con 4 nuevas carpetas
│   │   │                                        #   Contratos · Actas y Formatos · Matrices · Tecnologia
│   │   ├── 📄 017_add_partner_jurisdictions.sql  # Columna jurisdicciones TEXT[] NOT NULL DEFAULT '{}'
│   │   │                                        #   índice GIN para búsquedas array eficientes
│   │   ├── 📄 018_ficha_tecnica_riel.sql         # Ficha Técnica del Riel y Criticidad Operativa
│   │   │                                        #   tipo_riel · sla_garantizado · numero_licencia
│   │   │                                        #   fecha_ultima_auditoria · certificaciones TEXT[]
│   │   │                                        #   es_entidad_regulada · partner_respaldo
│   │   │                                        #   pct_concentracion · nivel_criticidad
│   │   │                                        #   índices: nivel_criticidad · entidad_regulada · GIN certs
│   │   │                                        #   backfill nivel_criticidad en registros existentes
│   │   └── 📄 019_create_crypto_compliance_schema.sql  # Módulo Cripto Compliance (VASP Monitor)
│       │                                               #   tabla crypto_monitoreo:
│       │                                               #     wallet_address (UNIQUE) · blockchain
│       │                                               #     client_id (FK aliados ON DELETE SET NULL)
│       │                                               #     gl_score INT (0-100) · riesgo_nivel TEXT
│       │                                               #     risk_labels JSONB DEFAULT '[]'
│       │                                               #     total_exposure NUMERIC · pdf_report_url
│       │                                               #     last_report_date · registrado_por · notas
│       │                                               #   índices: client_id · riesgo_nivel · gl_score
│       │                                               #     GIN risk_labels · trigger updated_at
│       └── 📄 020_create_crypto_clients_table.sql    # Clientes Corporativos para VASP
│                                                       #   tabla crypto_clientes:
│                                                       #     id SERIAL PK · razon_social (NOT NULL)
│                                                       #     nit (UNIQUE) · representante_legal
│                                                       #     correo_corporativo · telefono · direccion
│                                                       #     fecha_onboarding DATE · notas
│                                                       #     creado_por · created_at · updated_at
│                                                       #   ALTER TABLE crypto_monitoreo:
│                                                       #     ADD COLUMN crypto_cliente_id INTEGER
│                                                       #       REFERENCES crypto_clientes(id)
│                                                       #       ON DELETE SET NULL
│                                                       #   índice: crypto_cliente_id · trigger updated_at
│   │   ├── 📄 021_sof_uof_fields.sql                  # Metodología SoF/UoF (Wallets Monitoring AdamoServices)
│   │   │                                              #   ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS:
│   │   │                                              #   — Source of Funds: sof_tipo_riesgo · sof_indicador
│   │   │                                              #     sof_naturaleza · sof_profundidad · sof_cont_directa
│   │   │                                              #     sof_cont_indirecta · sof_cont_total · sof_score
│   │   │                                              #     sof_nivel · sof_monto NUMERIC(20,2)
│   │   │                                              #   — Use of Funds: uof_indicador · uof_naturaleza
│   │   │                                              #     uof_profundidad · uof_cont_directa/indirecta/total
│   │   │                                              #     uof_score · uof_nivel · uof_monto NUMERIC(20,2)
│   │   │                                              #   — Conclusión: analyst_observations · monitoring_analyst
│   │   │                                              #     final_risk_score NUMERIC(6,2) · final_risk_level
│   │   │                                              #     wallet_status TEXT DEFAULT 'Active'
│   │   │                                              #   Índices: sof_nivel · uof_nivel · final_risk_level
│   │   │                                              #     monitoring_analyst
│   │   ├── 📄 022_weekly_monitoring_historial.sql     # Ciclo de monitoreo semanal + historial
│       │                                              #   weekly_delta TEXT en crypto_monitoreo
│       │                                              #   tabla crypto_monitoreo_historial (snapshots):
│       │                                              #     id · original_id · snapshot_date · wallet_address
│       │                                              #     gl_score · riesgo_nivel · sof/uof scores y niveles
│       │                                              #     final_risk_score · final_risk_level · weekly_delta
│       │                                              #     analyst_observations · monitoring_analyst
│       │                                              #     registrado_por · pdf_report_url · total_exposure
│       │                                              #   Índices: wallet_address · original_id · snapshot_date
│   │   └── 📄 023_document_history.sql               # Versionamiento inmutable de documentos compliance
│       │                                              #   tabla compliance_documentos_historial
│       │                                              #     → espejo de compliance_documentos + documento_raiz_id (FK)
│       │                                              #     + descripcion_cambio · snapshot_por · snapshot_at
│       │                                              #   append-only: solo INSERT (nunca UPDATE/DELETE)
│       │                                              #   ON DELETE CASCADE desde documento raíz
│       │                                              #   Índices: idx_doc_hist_raiz · idx_doc_hist_snapshot_at
│   │
│   └── 📂 repositories/              # Patrón Repository — CRUD desacoplado de la UI
│       ├── 📄 __init__.py
│       ├── 📄 partner_repo.py         # CRUD completo de aliados
│       │                              # create() — inserta + calcula puntaje_riesgo automático
│       │                              # update() — recalcula puntaje_riesgo si toca campos SARLAFT
│       │                              #   _CAMPOS_RIESGO: es_pep · crypto_friendly · adult_friendly
│       │                              #   estado_sarlaft · estado_due_diligence · contrato_firmado
│       │                              #   listas_verificadas · lista_ofac_ok · rut_recibido
│       │                              #   camara_comercio_recibida · permite_monetizacion · jurisdicciones
│       │                              # get_by_id() · delete()
│       │                              # get_lista_enriquecida() · get_stats_pipeline()
│       │                              # get_stats_riesgo() · get_sarlaft_vencidas()
│       │                              # get_revisiones_proximas(dias=30)
│       │                              # get_salud_grupo() · get_stats_capacidades()
│       │                              # get_termometro_sarlaft() · get_resumen_volumen()
│       │                              # get_partners_por_empresa(empresa)
│       │                              # calcular_puntaje_riesgo() — rubrica SARLAFT-compatible
│       │                              #   +15 pts: ≥1 jurisdicción GAFI alto riesgo
│       │                              #   +10 pts adicionales: ≥2 jurisdicciones GAFI
│       │                              #   +5 pts: exposición múltiple (≥5 jurisdicciones cualquier tipo)
│       ├── 📄 audit_repo.py           # Log de auditoría inmutable (solo escritura/lectura)
│       │                              # registrar() — normaliza resultado · convierte dict a JSON
│       │                              #   acepta valores_anteriores/nuevos como dict (no str)
│       │                              #   usuario_id=0 → NULL (FK safe)
│       │                              # list_log() · get_actividad_usuario()
│       ├── 📄 crypto_repo.py          # Repositorio Cripto Compliance — Clientes + VASP Monitor
│       │                              # CryptoRepository(session):
│       │                              # ⚠️ Todas las queries usan exec_driver_sql(sql, params)
│       │                              #   con placeholders %(param)s — nunca SQLAlchemy text()
│       │                              #   JSONB: %(risk_labels)s::jsonb — sin CAST() wrapper
│       │                              #   sof_monto / uof_monto: None pass-through (nullable)
│       │                              # — Clientes Corporativos:
│       │                              #   crear_cliente(CryptoClienteCreate) → dict
│       │                              #   get_clientes(search='') → list[dict]
│       │                              #     LEFT JOIN con crypto_monitoreo si FK existe
│       │                              #     fallback via information_schema.columns
│       │                              #   get_cliente_by_id(id) → Optional[dict]
│       │                              #   get_wallets_by_cliente(cliente_id) → list[dict]
│       │                              #   get_stats_by_cliente(cliente_id) → dict
│       │                              #     exposure_total · distribución por nivel
│       │                              # — Wallets VASP (ciclo de vida separado):
│       │                              #   create_wallet(WalletMonitorCreate) → dict
│       │                              #     INSERT puro — no ON CONFLICT. Primera vinculación.
│       │                              #     Lanza ValueError con mensaje amigable en duplicado
│       │                              #   monitor_wallet(WalletMonitorCreate) → dict
│       │                              #     Ciclo semanal: archive_current → UPDATE registro activo
│       │                              #     Lanza ValueError si wallet no existe
│       │                              #     Lanza RuntimeError si archive falla
│       │                              #   upsert_from_gl(WalletMonitorCreate) — ON CONFLICT wallet_address
│       │                              #     (legado — mantener por compatibilidad)
│       │                              #   get_previous_snapshot(wallet_address) → Optional[dict]
│       │                              #     Último historial de crypto_monitoreo_historial
│       │                              #   archive_current_to_history(wallet_address) → bool
│       │                              #     INSERT INTO crypto_monitoreo_historial SELECT … FROM crypto_monitoreo
│       │                              #   get_by_address(addr) · get_by_id(id)
│       │                              #   get_lista(client_id, riesgo_nivel, blockchain,
│       │                              #     solo_criticos, search_text):
│       │                              #     LEFT JOIN crypto_clientes → razon_social via COALESCE
│       │                              #     búsqueda textual incluye razon_social
│       │                              #     fallback sin JOIN si columna FK no existe aún
│       │                              #   get_stats_gerencial() — information_schema check primero
│       │                              #     conteos por nivel · exposure total · por_blockchain
│       │                              #   get_atencion_prioritaria() — score<30 o Crítico/Alto
│       │                              #   delete(wallet_id) → bool
│       │                              # — Helpers:
│       │                              #   score_a_nivel_riesgo(score) — ≥70=Bajo, 40-70=Medio,
│       │                              #     20-40=Alto, <20=Crítico
│       │                              #   _columna_existe(tabla, columna) → bool (info_schema)
│       │                              # _LABELS_CRITICOS: Sanctioned Exchange · OFAC · Darknet
│       │                              #   Ransomware · Scam · Terrorism Financing · Mixer
│       ├── 📄 compliance_repo.py      # CRUD de compliance_documentos
│       │                              # get_stats(empresa=None) — totales por estado + por_carpeta
│       │                              #   por_carpeta incluye: total · vigentes · pendientes · vencidos
│       │                              # get_documentos(carpeta, estado, empresa) — filtros opcionales
│       │                              # get_by_id() · crear(data, creado_por) → int
│       │                              # actualizar(doc_id, data, actualizado_por)
│       │                              #   guarda snapshot en compliance_documentos_historial antes del UPDATE
│       │                              # get_historial(doc_id) → list[dict] — versiones desc por snapshot_at
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

### 🤝 Gestión de Alianzas — Banking Partners Hub (`app/components/partners_ui.py`)
Módulo maestro consolidado con **3 pestañas dinámicas**. Entrada única en el menú lateral (todos los roles).

#### Tab 📊 Monitor
Renderiza `page_dashboard(user)` completo:
- **KPIs** — Total partners · Activos · Alto Riesgo · PEPs · En Onboarding
- **Salud Corporativa** — Tarjeta por empresa (HoldingsBPO Corp / Adamo / Paycop)
- **Monitor de Riesgo** — Donut Plotly (capacidades riesgo) + termómetro SARLAFT
- **Análisis de Volumen** — Ranking por volumen real mensual
- **Centro de Alertas** — SARLAFT vencidas · próximas 30 días · ⚡ Acción Rápida

#### Tab 📋 Portafolio
Renderiza `page_partners(user)`:
- **Filtros**: Estado Pipeline · Nivel Riesgo · búsqueda texto · Solo PEP · 🌍 Jurisdicción de Operación
- **KPIs rápidos**: Total · Activos · Alto Riesgo · PEPs
- **Tabla por tarjetas**: pills pipeline/riesgo/SARLAFT + badges capacidades operativas + badges de jurisdicciones (rojo para GAFI alto riesgo, gris para resto; máx 6 + contador overflow)
- **Edición inline** (ADMIN / COMPLIANCE / COMERCIAL): formulario 3 secciones; campos SARLAFT/riesgo y **Jurisdicciones** bloqueados para `comercial`
- **Eliminación** (solo ADMIN): panel borde rojo + auditoría `DELETE`

#### Tab ➕ Alta de Partner
Solo visible para roles `CAN_CREATE_PARTNERS` (admin · compliance · comercial). Pestaña oculta para `consulta`:
- Formulario 4 secciones: Identificación · Relación Corporativa · Perfil Operativo · Compliance
- **Relación Corporativa** incluye `🌍 Jurisdicciones de Operación` (multiselect de `Jurisdicciones.ALL`)
- `AliadoCreate` validado con Pydantic + `repo.create()` + `audit.registrar()`
- `clear_on_submit=True` + `st.toast()` al registrar · banner de éxito en siguiente render

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
- **Con URL** → `✏️ Editar` (solo admin/compliance) + `🔗 Abrir` (`st.link_button`, pestaña nueva)
- **Sin URL** → Editores: `✏️ Editar` + aviso *«Sin enlace — añade la URL en ✏️ Editar»*; Solo lectura: aviso *«Sin enlace — requiere URL para habilitar el acceso»*
- Sin iframes ni previsualización embebida

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

| Rol           | Tab Monitor | Tab Portafolio | Tab Alta Partner | Auditoría | Eliminar | Gestión Agentes | Centro Documental | Editar Jurisd. |
|---------------|:-----------:|:--------------:|:----------------:|:---------:|:--------:|:---------------:|:-----------------:|:--------------:|
| `admin`       | ✅ completo | ✅ + editar    | ✅               | ✅        | ✅       | ✅              | ✅ (editar)       | ✅             |
| `compliance`  | ✅ completo | ✅ + editar    | ✅               | ✅        | ❌       | ✅              | ✅ (editar)       | ✅             |
| `comercial`   | ✅ completo | ✅ + editar op.| ✅               | ❌        | ❌       | ❌              | ✅ (solo lectura) | 🔒 deshabilitado|
| `consulta`    | ✅ completo | ✅ solo lectura| 🔒 oculto        | ❌        | ❌       | ❌              | ✅ (solo lectura) | 🔒 deshabilitado|

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
- **f-strings con condicionales**: nunca usar comillas alternativas ni `\` dentro de expresiones `f"...{...}"` — SyntaxError en Railway. Pre-computar siempre en variable previa: `border = "#x" if cond else "#y"` → `f'...{border}...'`

---

*AdamoServices S.A.S. · Compliance & Technology · [adamoservices.co](https://adamoservices.co)*
