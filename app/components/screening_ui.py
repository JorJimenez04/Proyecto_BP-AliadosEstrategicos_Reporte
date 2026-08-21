# app/components/screening_ui.py
import streamlit as st
from datetime import datetime
from app.utils.pdf_generator import (
    procesar_archivo_pdf,
    generar_pdf_base,
    compilar_expediente_completo,
    resolver_ruta_logo,
    TIPO_PERSONA_JURIDICA,
    TIPO_PERSONA_NATURAL,
)

# ── Tipo de entidad evaluada ───────────────────────────────────────
# El expediente se segmenta desde la raíz: una Persona Jurídica screenea
# Empresa + Rep. Legal + Accionista/UBO (3 PDFs). Una Persona Natural es un
# dossier individual 100% autónomo — sin Razón Social, NIT ni PDFs
# corporativos — que screenea solo a esa persona (1 PDF). Ambos comparten
# únicamente Radicado y Dictamen (Sección 4).
TIPO_PERSONA_OPTIONS = [TIPO_PERSONA_JURIDICA, TIPO_PERSONA_NATURAL]
ROL_RELACION_OPTIONS = [
    "Beneficiario Final (UBO)",
    "Representante Legal",
    "Socio / Accionista Individual",
    "Cliente Cripto / Persona Natural",
    "Empleado / Contratista",
    "Otro",
]


def render_resumen_validacion_ui(datos_extracted: dict):
    """Pinta una microtarjeta de validación digital en tiempo real para Streamlit"""
    if not datos_extracted:
        return

    es_limpio = datos_extracted['resultados'] == "0" and datos_extracted['intensificada'] == "NO"
    requiere_manual = datos_extracted.get('requiere_revision_manual', False)

    if requiere_manual:
        # El PDF no se pudo leer con confianza (escaneo, formato distinto, etc.)
        # — nunca se muestra como "limpio" solo porque los defaults son "0"/"NO".
        badge_html = '<span class="ar-badge ar-badge-medium">⚠ Lectura no confiable — revisar manualmente</span>'
    elif es_limpio:
        badge_html = '<span class="ar-badge ar-badge-low">✓ Certificado Limpio</span>'
    else:
        badge_html = '<span class="ar-badge ar-badge-critical">⚠ Alerta Detectada</span>'

    st.markdown(
        f'<div style="background: rgba(255, 255, 255, 0.01); border: 1px dashed var(--border); border-radius: var(--radius-md); padding: 14px; margin-top: 10px;">'
        f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">'
        f'<span style="font-size: 0.65rem; color: var(--ai); font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">Evidencia Indexada</span>'
        f'{badge_html}'
        f'</div>'
        f'<p style="margin: 0; font-size: 0.88rem; font-weight: 600; color: #ffffff;">{datos_extracted["nombre"]}</p>'
        f'<p style="margin: 2px 0 0 0; font-size: 0.78rem; color: var(--fg-subtle);">'
        f'ID: <code>{datos_extracted["identificacion"]}</code> | Consulta: <code>{datos_extracted["radicado"]}</code>'
        f'</p>'
        f'</div>',
        unsafe_allow_html=True
    )


def _calcular_estado_global(entidades_lista: list) -> str:
    """
    Tres niveles, en orden de severidad. Una coincidencia real en listas
    siempre pesa más que una lectura no confiable, pero ninguna de las dos
    puede terminar en "aprobado" — un PDF ilegible con los defaults
    ("0" / "NO") no se aprueba igual que un caso limpio de verdad.
    """
    hay_coincidencia_real = any(
        ent['resultados'] != "0" or ent['intensificada'] == "SI" for ent in entidades_lista
    )
    hay_lectura_no_confiable = any(
        ent.get('requiere_revision_manual', False) for ent in entidades_lista
    )

    if hay_coincidencia_real:
        return "REQUIERE REVISIÓN INTENSIFICADA"
    if hay_lectura_no_confiable:
        return "REQUIERE REVISIÓN MANUAL"
    return "APROBADO S/ANOMALÍAS"


def _leer_bytes_uploader(f):
    if f is None:
        return None
    try:
        f.seek(0)
        return f.read()
    except Exception:
        return None


def _validar_y_construir_juridica(campos_faltantes: list):
    """Recolecta y valida los campos del bloque Persona Jurídica. Devuelve
    (entidades_lista, payload_extra, infolaft_keys, nombre_para_archivo,
    identificador_principal) o None si faltan campos (en cuyo caso ya dejó
    los errores acumulados en campos_faltantes)."""
    v_empresa = st.session_state.get("v6_empresa_master", "").strip()
    v_nit = st.session_state.get("v6_nit_master", "").strip()
    v_jurisdiccion = st.session_state.get("v6_jurisdiccion", "").strip()
    v_sitio_web = st.session_state.get("v6_sitio_web", "").strip()
    v_rep_nom = st.session_state.get("v6_rep_legal_nom", "").strip()
    v_rep_id = st.session_state.get("v6_rep_legal_id", "").strip()

    es_mismo = st.session_state.get("v6_chk_accionista_es_rep", False)
    if es_mismo:
        v_acc_nom = v_rep_nom
        v_acc_id = v_rep_id
    else:
        v_acc_nom = st.session_state.get("v6_acc_nom_en", "").strip()
        v_acc_id = st.session_state.get("v6_acc_id_en", "").strip()

    file_empresa = st.session_state.get("v6_pdf_empresa")
    file_rep = st.session_state.get("v6_pdf_rep")
    file_acc = st.session_state.get("v6_pdf_acc")

    if not v_empresa: campos_faltantes.append("Razón Social de la Empresa")
    if not v_nit: campos_faltantes.append("NIT Comercial")
    if not v_jurisdiccion: campos_faltantes.append("Jurisdicción de Riesgo / Ciudad")
    if not v_rep_nom: campos_faltantes.append("Nombre del Representante Legal")
    if not v_rep_id: campos_faltantes.append("Documento de Identidad del Representante Legal")
    if not es_mismo:
        if not v_acc_nom: campos_faltantes.append("Nombre del Accionista Mayoritario")
        if not v_acc_id: campos_faltantes.append("Identificación del Accionista Mayoritario")

    # Sin el reporte Infolaft no hay screening real contra listas restrictivas.
    if file_empresa is None:
        campos_faltantes.append("Reporte Infolaft de la Empresa (PDF)")
    if file_rep is None:
        campos_faltantes.append("Reporte Infolaft del Representante Legal (PDF)")
    if not es_mismo and file_acc is None:
        campos_faltantes.append("Reporte Infolaft del Accionista Mayoritario (PDF)")

    if campos_faltantes:
        return None

    parsed_empresa = procesar_archivo_pdf(file_empresa)
    parsed_replegal = procesar_archivo_pdf(file_rep)
    parsed_accionista = procesar_archivo_pdf(file_acc)

    entidades_lista = []
    if parsed_empresa:
        parsed_empresa["rol_interno"] = "Empresa Principal"
        entidades_lista.append(parsed_empresa)
    if parsed_replegal:
        parsed_replegal["rol_interno"] = "Representante Legal"
        entidades_lista.append(parsed_replegal)
        if es_mismo:
            clon_accionista = parsed_replegal.copy()
            clon_accionista["rol_interno"] = "Accionista / Beneficiario Final"
            entidades_lista.append(clon_accionista)
    if not es_mismo and parsed_accionista:
        parsed_accionista["rol_interno"] = "Accionista / Beneficiario Final"
        entidades_lista.append(parsed_accionista)

    payload_extra = {
        "tipo_persona": TIPO_PERSONA_JURIDICA,
        "es_individual": False,
        "empresa_principal": v_empresa,
        "nit_principal": v_nit,
        "jurisdiccion": v_jurisdiccion,
        "sitio_web": v_sitio_web if v_sitio_web else "No Registrado",
        "rep_legal_nom": v_rep_nom,
        "rep_legal_id": v_rep_id,
        "accionista_nom": v_acc_nom,
        "accionista_id": v_acc_id,
    }
    infolaft_keys = ("v6_pdf_empresa", "v6_pdf_rep", "v6_pdf_acc")
    nombre_para_archivo = v_empresa
    identificador_principal = v_nit
    return entidades_lista, payload_extra, infolaft_keys, nombre_para_archivo, identificador_principal


def _validar_y_construir_natural(campos_faltantes: list):
    """Recolecta y valida los campos del bloque Persona Natural. Es un
    dossier individual 100% autónomo: no depende de datos corporativos ni de
    los PDFs de Empresa/Rep. Legal/Accionista. Devuelve (entidades_lista,
    payload_extra, infolaft_keys, nombre_para_archivo, identificador_principal)
    o None si faltan campos."""
    v_nombre = st.session_state.get("v6_pn_nombre_completo", "").strip()
    v_num_doc = st.session_state.get("v6_pn_numero_documento", "").strip()
    v_rol_rel = st.session_state.get("v6_pn_rol_relacion", "").strip()
    v_pais_res = st.session_state.get("v6_pn_pais_residencia", "").strip()
    file_natural = st.session_state.get("v6_pdf_natural")

    if not v_nombre: campos_faltantes.append("Nombre Completo")
    if not v_num_doc: campos_faltantes.append("Número de Documento")
    if not v_rol_rel: campos_faltantes.append("Calidad / Rol Evaluado")
    if not v_pais_res: campos_faltantes.append("País de Residencia / Nacionalidad")

    # Un único PDF Infolaft de la persona — nunca se exigen los 2 PDFs
    # corporativos adicionales (Empresa / Accionista) en este flujo.
    if file_natural is None:
        campos_faltantes.append("Reporte Infolaft de la Persona Natural (PDF)")

    if campos_faltantes:
        return None

    parsed_natural = procesar_archivo_pdf(file_natural)

    entidades_lista = []
    if parsed_natural:
        parsed_natural["rol_interno"] = TIPO_PERSONA_NATURAL
        entidades_lista.append(parsed_natural)

    payload_extra = {
        "tipo_persona": TIPO_PERSONA_NATURAL,
        "es_individual": True,
        "nombre_completo": v_nombre,
        "numero_documento": v_num_doc,
        "rol_relacion": v_rol_rel,
        "pais_residencia": v_pais_res,
        # Un expediente individual no tiene Razón Social, NIT, Rep. Legal ni
        # estructura accionaria — se marca explícitamente en vez de dejar
        # claves ausentes, para que nunca aparezca "No detectado" en el PDF
        # como si se hubiera omitido un dato por error.
        "direccion": "N/A (Individual)",
        "telefono": "N/A (Individual)",
        "correo_contacto": "N/A (Individual)",
        "empresa_principal": "N/A (Individual)",
        "nit_principal": "N/A (Individual)",
        "jurisdiccion": "N/A (Individual)",
        "sitio_web": "N/A (Individual)",
        "rep_legal_nom": "N/A (Individual)",
        "rep_legal_id": "N/A (Individual)",
        "accionista_nom": "N/A (Individual)",
        "accionista_id": "N/A (Individual)",
    }
    infolaft_keys = ("v6_pdf_natural",)
    nombre_para_archivo = v_nombre
    identificador_principal = v_num_doc
    return entidades_lista, payload_extra, infolaft_keys, nombre_para_archivo, identificador_principal


def callback_ejecutar_compilacion(user: dict):
    """Procesador prioritario en memoria RAM"""
    tipo_persona = st.session_state.get("v6_tipo_persona_selector", TIPO_PERSONA_JURIDICA)

    # ── Campos comunes a ambos tipos de entidad ───────────────────
    v_radicado = st.session_state.get("v6_radicado_caso", "").strip()
    v_dictamen = st.session_state.get("v6_dictamen_motivo", "").strip()
    v_direccion = st.session_state.get("v6_direccion", "").strip()
    v_telefono = st.session_state.get("v6_telefono", "").strip()
    v_correo = st.session_state.get("v6_correo", "").strip()
    v_rues_news = st.session_state.get("v6_rues_noticias_raw", "").strip()

    campos_faltantes = []
    if not v_radicado: campos_faltantes.append("Código de Radicado Único Interno")
    if not v_dictamen: campos_faltantes.append("Análisis Argumentativo Legal (Dictamen)")

    # ── Validación específica del tipo de entidad seleccionado ────
    # Solo se exigen los campos del bloque activo — evita bloqueos erróneos
    # al evaluar una Persona Natural con campos que solo aplican a Jurídica.
    if tipo_persona == TIPO_PERSONA_JURIDICA:
        resultado = _validar_y_construir_juridica(campos_faltantes)
    else:
        resultado = _validar_y_construir_natural(campos_faltantes)

    if campos_faltantes or resultado is None:
        st.session_state["v6_just_validated"] = True
        st.session_state["v6_f_errores"] = campos_faltantes
        st.session_state["v6_f_pdf_bytes"] = None
        st.session_state["v6_f_nit"] = ""
        return

    entidades_lista, payload_extra, infolaft_keys, nombre_para_archivo, identificador_principal = resultado
    estado_global = _calcular_estado_global(entidades_lista)

    # Procesamiento de imágenes de evidencias en memoria RAM
    evidencias_cargadas = st.session_state.get("v6_evidencias_imagenes", [])
    bytes_evidencias = []
    if evidencias_cargadas:
        for f in evidencias_cargadas:
            try:
                f.seek(0)
                bytes_evidencias.append(f.read())
            except Exception:
                continue

    # Estructura de datos consolidada para el generador
    payload_maestro = {
        "direccion": v_direccion if v_direccion else "No Declarada",
        "telefono": v_telefono if v_telefono else "No Declarado",
        "correo_contacto": v_correo if v_correo else "No Registrado",
        "radicado_caso": v_radicado,
        "dictamen_motivo": v_dictamen,
        "rues_noticias_raw": v_rues_news,
        "estado_global": estado_global,
        "entidades_processed": entidades_lista,
        "evidencias_imagenes": bytes_evidencias,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "analista": user.get("username", "sistema"),
        **payload_extra,
    }

    # Extracción de binarios PDF de Infolaft (varían según tipo de entidad)
    infolaft_bytes = [
        b for fk in infolaft_keys
        if (b := _leer_bytes_uploader(st.session_state.get(fk))) is not None
    ]

    st.session_state["v6_f_errores"] = []
    bytes_base = generar_pdf_base(payload_maestro)
    st.session_state["v6_f_pdf_bytes"] = compilar_expediente_completo(bytes_base, infolaft_bytes)
    st.session_state["v6_f_nit"] = identificador_principal
    st.session_state["v6_f_estado_global"] = estado_global
    st.session_state["v6_f_dictamen"] = v_dictamen

    # 🚀 Sanitización dinámica ultra segura del nombre/razón social y Radicado
    emp_clean = "".join(c if (c.isalnum() or c in ("_", "-")) else "_" for c in nombre_para_archivo)
    rad_clean = "".join(c if (c.isalnum() or c in ("_", "-")) else "_" for c in v_radicado)

    # Reducción de guiones bajos consecutivos para mantener una estética premium
    while "__" in emp_clean: emp_clean = emp_clean.replace("__", "_")
    while "__" in rad_clean: rad_clean = rad_clean.replace("__", "_")
    emp_clean = emp_clean.strip("_").upper()
    rad_clean = rad_clean.strip("_").upper()

    st.session_state["v6_f_filename"] = f"Reporte_Compliance_{emp_clean}_{rad_clean}.pdf"


def _render_bloque_juridica():
    # 🏢 SECCIÓN MODULE 1: Información Corporativa
    with st.container():
        st.markdown('<p class="ar-section-title">1. Información Corporativa y Evidencia Digital</p>', unsafe_allow_html=True)
        col_m1_left, col_m1_right = st.columns([1.1, 0.9])

        with col_m1_left:
            st.text_input("Razón Social de la Empresa *", placeholder="Ej: CompanyName S.A.S.", key="v6_empresa_master")
            st.text_input("NIT Comercial (Con Dígito de Verificación) *", placeholder="Ej: 900.000.000-1", key="v6_nit_master")
            st.text_input("Dirección Fiscal / Domicilio", placeholder="Dirección de la Empresa", key="v6_direccion")
            st.text_input("Teléfono de Contacto Operativo", placeholder="Telefono de contacto", key="v6_telefono")
            st.text_input("Correo Electronico de Contacto", placeholder="Ej: contacto@empresa.com", key="v6_correo")
            st.text_input("Jurisdicción de Riesgo / Ciudad *", placeholder="País y Ciudad de Registro empresarial", key="v6_jurisdiccion")
            st.text_input("Canal Digital / Sitio Web", placeholder="Ej: www.companyname.co", key="v6_sitio_web")

        with col_m1_right:
            st.markdown("<p style='font-size:0.75rem; font-weight:700; color:var(--ai); text-transform:uppercase; margin-bottom:5px;'>📄 Reporte Infolaft (Sociedad) *</p>", unsafe_allow_html=True)
            file_empresa = st.file_uploader("Subir PDF Infolaft de la Empresa", type=["pdf"], key="v6_pdf_empresa", label_visibility="collapsed")
            parsed_empresa = procesar_archivo_pdf(file_empresa)
            if parsed_empresa:
                parsed_empresa["rol_interno"] = "Empresa Principal"
                render_resumen_validacion_ui(parsed_empresa)
            else:
                st.caption("Esperando archivo PDF oficial de la sociedad...")

    st.markdown('<div class="ar-divider" style="margin: 25px 0;"></div>', unsafe_allow_html=True)

    # 👥 SECCIÓN MODULE 2: Estructura de Administración
    with st.container():
        st.markdown('<p class="ar-section-title">2. Estructura de Administración y Control Directivo</p>', unsafe_allow_html=True)
        col_m2_left, col_m2_right = st.columns([1.1, 0.9])

        with col_m2_left:
            st.text_input("Nombre Completo (Representante Legal) *", placeholder="Nombre del firmante legal", key="v6_rep_legal_nom")
            st.text_input("Documento de Identidad (Representante Legal) *", placeholder="Número de cédula o pasaporte", key="v6_rep_legal_id")

        with col_m2_right:
            st.markdown("<p style='font-size:0.75rem; font-weight:700; color:var(--ai); text-transform:uppercase; margin-bottom:5px;'>📄 Reporte Infolaft (Representante) *</p>", unsafe_allow_html=True)
            file_replegal = st.file_uploader("Subir PDF Infolaft del Rep. Legal", type=["pdf"], key="v6_pdf_rep", label_visibility="collapsed")
            parsed_replegal = procesar_archivo_pdf(file_replegal)
            if parsed_replegal:
                parsed_replegal["rol_interno"] = "Representante Legal"
                render_resumen_validacion_ui(parsed_replegal)
            else:
                st.caption("Esperando archivo PDF oficial del representante...")

    st.markdown('<div class="ar-divider" style="margin: 25px 0;"></div>', unsafe_allow_html=True)

    # 📊 SECCIÓN MODULE 3: Composición Accionaria
    with st.container():
        st.markdown('<p class="ar-section-title">3. Composición Accionaria y Beneficiarios Finales</p>', unsafe_allow_html=True)
        st.checkbox("El Accionista Principal es el mismo Representante Legal de la compañía", value=False, key="v6_chk_accionista_es_rep")

        col_m3_left, col_m3_right = st.columns([1.1, 0.9])
        current_rep_nom = st.session_state.get("v6_rep_legal_nom", "")
        current_rep_id = st.session_state.get("v6_rep_legal_id", "")

        with col_m3_left:
            if st.session_state.get("v6_chk_accionista_es_rep", False):
                st.text_input("Nombre Completo (Accionista Mayoritario)", value=current_rep_nom, disabled=True, key="v6_acc_nom_dis")
                st.text_input("Identificación (Accionista Mayoritario)", value=current_rep_id, disabled=True, key="v6_acc_id_dis")
            else:
                st.text_input("Nombre Completo (Accionista Mayoritario) *", placeholder="Nombre del socio principal", key="v6_acc_nom_en")
                st.text_input("Identificación (Accionista Mayoritario) *", placeholder="ID del socio principal", key="v6_acc_id_en")

        with col_m3_right:
            if st.session_state.get("v6_chk_accionista_es_rep", False):
                st.info("ℹ️ Sistema en modo de duplicidad cero.")
            else:
                st.markdown("<p style='font-size:0.75rem; font-weight:700; color:var(--ai); text-transform:uppercase; margin-bottom:5px;'>📄 Reporte Infolaft (Accionista) *</p>", unsafe_allow_html=True)
                file_accionista = st.file_uploader("Subir PDF Infolaft del Accionista", type=["pdf"], key="v6_pdf_acc", label_visibility="collapsed")
                parsed_accionista = procesar_archivo_pdf(file_accionista)
                if parsed_accionista:
                    parsed_accionista["rol_interno"] = "Accionista / Beneficiario Final"
                    render_resumen_validacion_ui(parsed_accionista)

    st.markdown('<div class="ar-divider" style="margin: 25px 0;"></div>', unsafe_allow_html=True)


def _render_bloque_natural():
    # Dossier individual 100% autónomo: solo los 4 datos que identifican a
    # la persona + su único PDF Infolaft. Sin Razón Social, NIT, ni campos
    # de contacto corporativo — esos "N/A (Individual)" se rellenan en el
    # payload, no se le piden al usuario.
    with st.container():
        st.markdown('<p class="ar-section-title">1. Identificación de la Persona Natural</p>', unsafe_allow_html=True)
        col_n_left, col_n_right = st.columns([1.1, 0.9])

        with col_n_left:
            st.text_input("Nombre Completo *", placeholder="Nombre completo de la persona", key="v6_pn_nombre_completo")
            st.text_input("Número de Documento (CC/CE/Pasaporte/Tax ID) *", placeholder="Ej: 1.234.567.890", key="v6_pn_numero_documento")
            st.selectbox("Calidad / Rol Evaluado *", options=ROL_RELACION_OPTIONS, key="v6_pn_rol_relacion")
            st.text_input("País de Residencia / Nacionalidad *", placeholder="Ej: Colombia", key="v6_pn_pais_residencia")

        with col_n_right:
            st.markdown("<p style='font-size:0.75rem; font-weight:700; color:var(--ai); text-transform:uppercase; margin-bottom:5px;'>📄 Reporte Infolaft (Persona Natural) *</p>", unsafe_allow_html=True)
            file_natural = st.file_uploader("Subir PDF Infolaft de la Persona Natural", type=["pdf"], key="v6_pdf_natural", label_visibility="collapsed")
            parsed_natural = procesar_archivo_pdf(file_natural)
            if parsed_natural:
                parsed_natural["rol_interno"] = TIPO_PERSONA_NATURAL
                render_resumen_validacion_ui(parsed_natural)
            else:
                st.caption("Esperando archivo PDF oficial de la persona natural...")

    st.markdown('<div class="ar-divider" style="margin: 25px 0;"></div>', unsafe_allow_html=True)


def render_screening_workspace(user: dict):
    st.markdown('<p class="ar-section-title" style="margin-bottom:0px;">Intelligence Workspace</p>', unsafe_allow_html=True)
    st.markdown('<h1 style="margin-top:0px; font-weight:800; letter-spacing:-0.03em;">Debida Diligencia Corporativa</h1>', unsafe_allow_html=True)

    if "v6_f_pdf_bytes" not in st.session_state: st.session_state["v6_f_pdf_bytes"] = None
    if "v6_f_nit" not in st.session_state: st.session_state["v6_f_nit"] = ""

    if st.session_state.get("v6_just_validated", False):
        st.session_state["v6_just_validated"] = False
    else:
        st.session_state["v6_f_errores"] = []
    if "v6_f_errores" not in st.session_state:
        st.session_state["v6_f_errores"] = []

    # 🔀 SECCIÓN 0: Tipo de Entidad Evaluada — segmenta todo el formulario
    with st.container():
        st.markdown('<p class="ar-section-title">Tipo de Entidad Evaluada</p>', unsafe_allow_html=True)
        st.radio(
            "Tipo de Entidad",
            options=TIPO_PERSONA_OPTIONS,
            key="v6_tipo_persona_selector",
            horizontal=True,
            label_visibility="collapsed",
        )

    st.markdown('<div class="ar-divider" style="margin: 20px 0;"></div>', unsafe_allow_html=True)

    tipo_persona_label = st.session_state.get("v6_tipo_persona_selector", TIPO_PERSONA_OPTIONS[0])
    if tipo_persona_label == TIPO_PERSONA_JURIDICA:
        _render_bloque_juridica()
    else:
        _render_bloque_natural()

    # 🧠 SECCIÓN MODULE 4: Dictamen del Oficial e Imágenes de Evidencia (común a ambos tipos)
    with st.container():
        st.markdown('<p class="ar-section-title">4. Datos del Expediente y Dictamen del Oficial</p>', unsafe_allow_html=True)
        st.text_input("Código de Radicado Único Interno *", placeholder="Ej: EXP-CASO-2026", key="v6_radicado_caso")
        st.text_area("Análisis Argumentativo Legal (Enfoque Basado en Riesgo) *", placeholder="Sustente rigurosamente el dictamen técnico de aceptación, rechazo o condicionamiento...", key="v6_dictamen_motivo")
        st.text_area("Notas de Prensa y Validación de Registro Mercantil (RUES)", placeholder="Pegue aquí el bloque de texto con los hallazgos de background check en fuentes abiertas...", key="v6_rues_noticias_raw")

        # 📸 Cargador de Capturas de Pantalla / Evidencias
        st.markdown("<p style='font-size:0.75rem; font-weight:700; color:var(--ai); text-transform:uppercase; margin-top:15px; margin-bottom:5px;'>📸 Registro de Evidencias de Consultas Abiertas (Capturas de Pantalla)</p>", unsafe_allow_html=True)
        st.file_uploader(
            "Arrastra capturas de pantalla de RUES, Procuraduría, Contraloría o Google News",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="v6_evidencias_imagenes",
            label_visibility="collapsed"
        )

    # Mapeo de logos
    missing_logos = []
    if not resolver_ruta_logo("Logo Adamo general"): missing_logos.append("'Logo Adamo general'")
    if not resolver_ruta_logo("Logo Holdings"): missing_logos.append("'Logo Holdings'")
    if missing_logos:
        st.warning(f"⚠️ Alerta de Identidad: No se detectan los archivos {', '.join(missing_logos)} en la ruta 'app/static/img/logos/'.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.button("⚡ Compilar y Validar Expediente de Caso", on_click=callback_ejecutar_compilacion, args=(user,), use_container_width=True)

    # Errores y buffers
    if st.session_state.get("v6_f_errores"):
        st.markdown('<div class="ar-alert-strip ar-alert-strip-critical" style="margin-top:15px;">', unsafe_allow_html=True)
        st.markdown("❌ <b>Error Operacional:</b> Por favor diligencie los siguientes campos mandatorios:", unsafe_allow_html=True)
        st.markdown("<ul>" + "".join([f"<li>{campo}</li>" for campo in st.session_state["v6_f_errores"]]) + "</ul>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get("v6_f_pdf_bytes"):
        est_glob = st.session_state.get("v6_f_estado_global", "")
        # Coincidencia real en listas > lectura de PDF no confiable > aprobado limpio.
        if "INTENSIFICADA" in est_glob:
            strip_class = "ar-alert-strip-critical"
        elif "MANUAL" in est_glob:
            strip_class = "ar-alert-strip-warning"
        else:
            strip_class = "ar-alert-strip-success"

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
            <div class="ar-card ar-ai-glow">
                <p class="ar-section-title" style="color:var(--ai);">Expediente Corporativo Homologado</p>
                <div style="font-size: 1.75rem; font-weight: 800; color: #ffffff; letter-spacing: -0.02em;">{est_glob}</div>
                <div class="ar-alert-strip {strip_class}" style="margin-top: 12px; font-size:0.85rem;">
                    <b>Sustento Técnico del Oficial:</b> {st.session_state.get("v6_f_dictamen", "")}
                </div>
            </div>
            <br>
        """, unsafe_allow_html=True)
        # Botón de descarga con mapeo dinámico y sanitizado de nombre
        st.download_button(
            label="📥 Descargar Expediente Maestro de Cumplimiento Certificado (.pdf)",
            data=st.session_state["v6_f_pdf_bytes"],
            file_name=st.session_state.get("v6_f_filename", "Reporte_Compliance_Final.pdf"),
            mime="application/pdf",
            use_container_width=True
        )
