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
    "Beneficiario Final / UBO (Participación > 5% / Control)",
    "Persona Expuesta Políticamente (PEP)",
    "Representante Legal / Gerente General",
    "Miembro de Junta Directiva / Administrador",
    "Apoderado / Firmante Autorizado",
    "Accionista / Socio Persona Natural",
    "Cliente Cripto / VASP Individual",
    "Proveedor / Contratista Persona Natural",
    "Empleado / Colaborador Interno",
    "Otro Vinculado Individual",
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


def _render_checklist_express():
    """
    Checklist en tiempo real de los 4 campos "core" del Modo Screening
    Express (Razón Social, NIT/Tax ID, Radicado, Dictamen). Se apoya en
    session_state en vez de recibir los valores por parámetro porque
    Radicado y Dictamen se diligencian en la Sección 4, renderizada más
    abajo en el flujo — el checklist siempre refleja el estado ya
    confirmado en el run anterior, como cualquier resumen en vivo de
    Streamlit ubicado antes de sus propios campos.
    """
    campos_check = [
        ("Razón Social", st.session_state.get("v6_empresa_master", "")),
        ("NIT / Tax ID", st.session_state.get("v6_nit_master", "")),
        ("Radicado", st.session_state.get("v6_radicado_caso", "")),
        ("Dictamen Comercial", st.session_state.get("v6_dictamen_motivo", "")),
    ]
    chips_html = ""
    for etiqueta, valor in campos_check:
        completo = bool((valor or "").strip())
        icono = "✅" if completo else "🔴"
        chips_html += (
            '<div style="display:flex; align-items:center; gap:6px; padding:6px 10px; '
            'background: rgba(255,255,255,0.02); border:1px solid var(--border); border-radius:8px;">'
            f'<span>{icono}</span>'
            f'<span style="font-size:0.78rem; color: var(--fg-subtle); font-weight:600;">{etiqueta}</span>'
            '</div>'
        )
    st.markdown(
        f'<div style="display:flex; flex-wrap:wrap; gap:8px; margin:4px 0 5px 0;">{chips_html}</div>',
        unsafe_allow_html=True,
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
    (entidades_lista, payload_extra, infolaft_bytes, nombre_para_archivo,
    identificador_principal) o None si faltan campos (en cuyo caso ya dejó
    los errores acumulados en campos_faltantes).

    Modo Screening Express (Prospectos / BDM): cuando v6_modo_prospecto
    está activo, se omite por completo la estructura de administración
    (Representante Legal / Accionista, con sus PDF Infolaft) — el equipo
    comercial genera un VoBo preliminar solo con Razón Social, NIT,
    Radicado y Dictamen. No reemplaza el Onboarding Formal SARLAFT."""
    es_prospecto = st.session_state.get("v6_modo_prospecto", False)

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
    # Sin el reporte Infolaft de la Empresa no hay screening real contra
    # listas restrictivas — se exige en ambos modos, Formal y Express.
    if file_empresa is None:
        campos_faltantes.append("Reporte Infolaft de la Empresa (PDF)")

    if not es_prospecto:
        if not v_jurisdiccion: campos_faltantes.append("Jurisdicción de Riesgo / Ciudad")
        if not v_rep_nom: campos_faltantes.append("Nombre del Representante Legal")
        if not v_rep_id: campos_faltantes.append("Documento de Identidad del Representante Legal")
        if not es_mismo:
            if not v_acc_nom: campos_faltantes.append("Nombre del Accionista Mayoritario")
            if not v_acc_id: campos_faltantes.append("Identificación del Accionista Mayoritario")
        if file_rep is None:
            campos_faltantes.append("Reporte Infolaft del Representante Legal (PDF)")
        if not es_mismo and file_acc is None:
            campos_faltantes.append("Reporte Infolaft del Accionista Mayoritario (PDF)")

    if campos_faltantes:
        return None

    parsed_empresa = procesar_archivo_pdf(file_empresa)
    parsed_replegal = procesar_archivo_pdf(file_rep) if file_rep is not None else None
    parsed_accionista = procesar_archivo_pdf(file_acc) if file_acc is not None else None

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

    # 🌎 Entidades Pagadoras Cross-Border (solo en Modo Express) ────────
    # Registro informativo de hasta 2 entidades pagadoras vinculadas en el
    # exterior (ej. LLCs en EE. UU.). No tienen PDF Infolaft propio en esta
    # etapa preliminar, por lo que se marcan "requiere_revision_manual" —
    # nunca deben aparecer como "limpias" sin haber sido efectivamente
    # consultadas contra listas restrictivas.
    if es_prospecto:
        for idx in (1, 2):
            nom_pagadora = st.session_state.get(f"v6_pagadora_{idx}_nombre", "").strip()
            tax_id_pagadora = st.session_state.get(f"v6_pagadora_{idx}_tax_id", "").strip()
            if not nom_pagadora and not tax_id_pagadora:
                continue
            entidades_lista.append({
                "nombre": nom_pagadora.upper() if nom_pagadora else "ENTIDAD PAGADORA SIN NOMBRE DECLARADO",
                "identificacion": tax_id_pagadora if tax_id_pagadora else "No detectado",
                "radicado": "N/A - Sin Consulta InfoLAFT",
                "resultados": "0",
                "intensificada": "NO",
                "requiere_revision_manual": True,
                "rol_interno": "Entidad Pagadora (EE. UU. / Exterior)",
            })

    payload_extra = {
        "tipo_persona": TIPO_PERSONA_JURIDICA,
        "es_individual": False,
        "empresa_principal": v_empresa,
        "nit_principal": v_nit,
        "jurisdiccion": v_jurisdiccion if v_jurisdiccion else "No Declarada",
        "sitio_web": v_sitio_web if v_sitio_web else "No Registrado",
        "rep_legal_nom": v_rep_nom,
        "rep_legal_id": v_rep_id,
        "accionista_nom": v_acc_nom,
        "accionista_id": v_acc_id,
        "modo_prospecto": es_prospecto,
    }
    infolaft_bytes = [
        b for f in (file_empresa, file_rep, file_acc)
        if (b := _leer_bytes_uploader(f)) is not None
    ]
    nombre_para_archivo = v_empresa
    identificador_principal = v_nit
    return entidades_lista, payload_extra, infolaft_bytes, nombre_para_archivo, identificador_principal


def _validar_y_construir_natural(campos_faltantes: list):
    """Recolecta y valida los campos del bloque Persona Natural. Es un
    dossier individual 100% autónomo: no depende de datos corporativos ni de
    los PDFs de Empresa/Rep. Legal/Accionista. Acepta 1..N evidencias PDF
    (ej. Infolaft, listas cripto/VASP, PEP) — cada una se procesa y se lista
    por separado en el reporte final. Devuelve (entidades_lista,
    payload_extra, infolaft_bytes, nombre_para_archivo,
    identificador_principal) o None si faltan campos."""
    v_nombre = st.session_state.get("v6_pn_nombre_completo", "").strip()
    v_num_doc = st.session_state.get("v6_pn_numero_documento", "").strip()
    v_rol_rel = st.session_state.get("v6_pn_rol_relacion", "").strip()
    v_pais_res = st.session_state.get("v6_pn_pais_residencia", "").strip()
    files_natural = st.session_state.get("v6_pdf_natural") or []

    if not v_nombre: campos_faltantes.append("Nombre Completo")
    if not v_num_doc: campos_faltantes.append("Número de Documento")
    if not v_rol_rel: campos_faltantes.append("Calidad / Rol Evaluado")
    if not v_pais_res: campos_faltantes.append("País de Residencia / Nacionalidad")

    # Al menos 1 PDF de evidencia — nunca se exigen los 2 PDFs corporativos
    # adicionales (Empresa / Accionista) en este flujo individual.
    if not files_natural:
        campos_faltantes.append("Reporte(s) Infolaft de la Persona Natural (PDF) — mínimo 1 archivo")

    if campos_faltantes:
        return None

    total_archivos = len(files_natural)
    entidades_lista = []
    for idx, f in enumerate(files_natural, start=1):
        parsed = procesar_archivo_pdf(f)
        if parsed:
            # Nota: fpdf2 (fuentes core) no soporta el guion largo "—" — se
            # usa "-" a propósito, no es un descuido de estilo (ver
            # pdf_generator.py, mismo caso ya resuelto ahí).
            etiqueta = f"{TIPO_PERSONA_NATURAL} - Evidencia {idx}/{total_archivos}" if total_archivos > 1 else TIPO_PERSONA_NATURAL
            parsed["rol_interno"] = etiqueta
            entidades_lista.append(parsed)

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
    infolaft_bytes = [
        b for f in files_natural
        if (b := _leer_bytes_uploader(f)) is not None
    ]
    nombre_para_archivo = v_nombre
    identificador_principal = v_num_doc
    return entidades_lista, payload_extra, infolaft_bytes, nombre_para_archivo, identificador_principal


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

    entidades_lista, payload_extra, infolaft_bytes, nombre_para_archivo, identificador_principal = resultado

    # ── Anexos de Soporte (Capturas / Documentos) ──────────────────────
    # Esta sección es evidencia documental de respaldo (RUES, Procuraduría,
    # Google News, etc.), NUNCA una consulta oficial de InfoLAFT — jamás
    # entra al screening LAFT ni recibe badge de estado. Solo se registra
    # su nombre/fecha para el manifiesto de anexos; un PDF aquí se adjunta
    # como página física al expediente final, pero no se procesa con
    # procesar_archivo_pdf() ni se suma a entidades_lista/estado_global.
    archivos_soporte = st.session_state.get("v6_evidencias_soportes", []) or []
    bytes_evidencias = []
    anexos_soporte_meta = []
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    for f in archivos_soporte:
        nombre_archivo = getattr(f, "name", "Archivo sin nombre") or "Archivo sin nombre"
        anexos_soporte_meta.append({"nombre": nombre_archivo, "fecha": fecha_hoy})
        b = _leer_bytes_uploader(f)
        if b is None:
            continue
        if nombre_archivo.lower().endswith(".pdf"):
            infolaft_bytes.append(b)
        else:
            bytes_evidencias.append(b)

    estado_global = _calcular_estado_global(entidades_lista)

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
        "anexos_soporte": anexos_soporte_meta,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "analista": user.get("username", "sistema"),
        **payload_extra,
    }

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

    # El toggle de Modo Express vive dentro del bloque Jurídica — se guarda
    # explícitamente contra tipo_persona para que un flag residual en
    # session_state nunca contamine el nombre de un expediente de Natural.
    es_prospecto_activo = tipo_persona == TIPO_PERSONA_JURIDICA and st.session_state.get("v6_modo_prospecto", False)
    prefijo_archivo = "Screening_PRELIMINAR" if es_prospecto_activo else "Reporte_Compliance"

    st.session_state["v6_f_filename"] = f"{prefijo_archivo}_{emp_clean}_{rad_clean}.pdf"


def _render_bloque_juridica():
    # ⚡ Modo Screening Express (Clientes Prospectos / BDM) ─────────────
    # Permite al equipo comercial generar un VoBo preliminar con datos
    # mínimos cuando aún no existe la estructura completa de administración
    # exigida en el Onboarding Formal SARLAFT (Representante Legal /
    # Accionistas). Se lee ANTES del resto del bloque para que la relajación
    # de "*" y validaciones tome efecto en el mismo render.
    st.toggle("⚡ Activar Modo Screening Express (Clientes Prospectos / BDM)", key="v6_modo_prospecto")
    es_prospecto = st.session_state.get("v6_modo_prospecto", False)

    # Sufijos dinámicos de etiqueta: los 4 campos "core" del VoBo preliminar
    # (Razón Social, NIT, Radicado, Dictamen) siguen siendo obligatorios en
    # Express — se resalta con ⚡ en vez de ocultarlo. Rep. Legal/Accionista
    # pasan a opcionales (⚪) porque pertenecen al Onboarding Formal.
    req_express = " ⚡ [REQUERIDO EXPRESS]" if es_prospecto else " *"
    req_formal = " ⚪ (Opcional en Prospecto)" if es_prospecto else " *"

    if es_prospecto:
        st.info(
            "ℹ️ Modo Express activo: se relajan las validaciones de campos obligatorios. Solo se exige "
            "Razón Social, NIT/Tax ID, Radicado y Dictamen. Este certificado es un VoBo comercial "
            "preliminar y NO reemplaza el Onboarding Formal SARLAFT (Representante Legal, Accionistas "
            "y sus respectivos PDF Infolaft)."
        )
        _render_checklist_express()

    # 🏢 SECCIÓN MODULE 1: Información Corporativa
    with st.container():
        st.markdown('<p class="ar-section-title">1. Información Corporativa y Evidencia Digital</p>', unsafe_allow_html=True)
        col_m1_left, col_m1_right = st.columns([1.1, 0.9])

        with col_m1_left:
            st.text_input(f"Razón Social de la Empresa{req_express}", placeholder="Ej: CompanyName S.A.S.", key="v6_empresa_master")
            st.text_input(f"NIT Comercial (Con Dígito de Verificación){req_express}", placeholder="Ej: 900.000.000-1", key="v6_nit_master")
            st.text_input("Dirección Fiscal / Domicilio", placeholder="Dirección de la Empresa", key="v6_direccion")
            st.text_input("Teléfono de Contacto Operativo", placeholder="Telefono de contacto", key="v6_telefono")
            st.text_input("Correo Electronico de Contacto", placeholder="Ej: contacto@empresa.com", key="v6_correo")
            st.text_input(f"Jurisdicción de Riesgo / Ciudad{req_formal}", placeholder="País y Ciudad de Registro empresarial", key="v6_jurisdiccion")
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

    # 🌎 Entidades Pagadoras Cross-Border (solo visible en Modo Express) ─
    # Clientes pagadores relacionados en el exterior (ej. LLCs en EE. UU.)
    # que aún no tienen PDF Infolaft propio en esta etapa preliminar.
    if es_prospecto:
        with st.expander("🌎 Entidades Pagadoras Vinculadas en el Exterior (Opcional, máx. 2)"):
            st.caption("Registra entidades pagadoras relacionadas en el exterior asociadas al prospecto (ej. Business and Digital Lab LLC). No requieren PDF Infolaft en este modo.")
            col_pag1, col_pag2 = st.columns(2)
            with col_pag1:
                st.markdown("**Entidad Pagadora 1**")
                st.text_input("Razón Social", placeholder="Ej: Business and Digital Lab LLC", key="v6_pagadora_1_nombre")
                st.text_input("Tax ID / EIN", placeholder="Ej: 88-1234567", key="v6_pagadora_1_tax_id")
            with col_pag2:
                st.markdown("**Entidad Pagadora 2**")
                st.text_input("Razón Social", placeholder="Ej: Otra Entidad LLC", key="v6_pagadora_2_nombre")
                st.text_input("Tax ID / EIN", placeholder="Ej: 88-7654321", key="v6_pagadora_2_tax_id")

        st.markdown('<div class="ar-divider" style="margin: 25px 0;"></div>', unsafe_allow_html=True)

    # 👥 SECCIÓN MODULE 2: Estructura de Administración
    with st.container():
        st.markdown('<p class="ar-section-title">2. Estructura de Administración y Control Directivo</p>', unsafe_allow_html=True)
        if es_prospecto:
            st.caption("No requerido en Modo Screening Express — diligéncielo únicamente si ya cuenta con la información.")
        col_m2_left, col_m2_right = st.columns([1.1, 0.9])

        with col_m2_left:
            # No se deshabilitan: "Opcional en Prospecto" significa que no
            # bloquean la compilación si quedan vacíos (ver
            # _validar_y_construir_juridica), no que el analista no pueda
            # diligenciarlos si ya cuenta con la información.
            st.text_input(f"Nombre Completo (Representante Legal){req_formal}", placeholder="Nombre del firmante legal", key="v6_rep_legal_nom")
            st.text_input(f"Documento de Identidad (Representante Legal){req_formal}", placeholder="Número de cédula o pasaporte", key="v6_rep_legal_id")

        with col_m2_right:
            st.markdown(f"<p style='font-size:0.75rem; font-weight:700; color:var(--ai); text-transform:uppercase; margin-bottom:5px;'>📄 Reporte Infolaft (Representante){req_formal}</p>", unsafe_allow_html=True)
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
                st.text_input(f"Nombre Completo (Accionista Mayoritario){req_formal}", placeholder="Nombre del socio principal", key="v6_acc_nom_en")
                st.text_input(f"Identificación (Accionista Mayoritario){req_formal}", placeholder="ID del socio principal", key="v6_acc_id_en")

        with col_m3_right:
            if st.session_state.get("v6_chk_accionista_es_rep", False):
                st.info("ℹ️ Sistema en modo de duplicidad cero.")
            else:
                st.markdown(f"<p style='font-size:0.75rem; font-weight:700; color:var(--ai); text-transform:uppercase; margin-bottom:5px;'>📄 Reporte Infolaft (Accionista){req_formal}</p>", unsafe_allow_html=True)
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
            st.markdown("<p style='font-size:0.75rem; font-weight:700; color:var(--ai); text-transform:uppercase; margin-bottom:5px;'>📄 Reporte(s) Infolaft — mínimo 1 archivo *</p>", unsafe_allow_html=True)
            files_natural = st.file_uploader(
                "Subir PDF(s) Infolaft de la Persona Natural",
                type=["pdf"],
                accept_multiple_files=True,
                key="v6_pdf_natural",
                label_visibility="collapsed",
            )
            if files_natural:
                total = len(files_natural)
                for idx, f in enumerate(files_natural, start=1):
                    parsed = procesar_archivo_pdf(f)
                    if parsed:
                        parsed["rol_interno"] = f"{TIPO_PERSONA_NATURAL} - Evidencia {idx}/{total}" if total > 1 else TIPO_PERSONA_NATURAL
                        render_resumen_validacion_ui(parsed)
            else:
                st.caption("Esperando al menos un archivo PDF oficial de la persona natural...")

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

    # El toggle de Modo Express solo se renderiza dentro del bloque
    # Jurídica — se guarda contra tipo_persona_label para que un flag
    # residual en session_state nunca "resalte" estos campos en Natural.
    es_prospecto_s4 = tipo_persona_label == TIPO_PERSONA_JURIDICA and st.session_state.get("v6_modo_prospecto", False)
    req_express_s4 = " ⚡ [REQUERIDO EXPRESS]" if es_prospecto_s4 else " *"

    # 🧠 SECCIÓN MODULE 4: Dictamen del Oficial e Imágenes de Evidencia (común a ambos tipos)
    with st.container():
        st.markdown('<p class="ar-section-title">4. Datos del Expediente y Dictamen del Oficial</p>', unsafe_allow_html=True)
        st.text_input(f"Código de Radicado Único Interno{req_express_s4}", placeholder="Ej: EXP-CASO-2026", key="v6_radicado_caso")
        st.text_area(f"Análisis Argumentativo Legal (Enfoque Basado en Riesgo){req_express_s4}", placeholder="Sustente rigurosamente el dictamen técnico de aceptación, rechazo o condicionamiento...", key="v6_dictamen_motivo")
        st.text_area("Notas de Prensa y Validación de Registro Mercantil (RUES)", placeholder="Pegue aquí el bloque de texto con los hallazgos de background check en fuentes abiertas...", key="v6_rues_noticias_raw")

        # 📸 Cargador de Capturas de Pantalla / Documentos de Soporte
        # Acepta imágenes (anexo visual sin análisis) y PDF (se procesan con
        # el mismo pipeline de screening que los Infolaft — ver
        # callback_ejecutar_compilacion, bloque de clasificación por extensión).
        st.markdown("<p style='font-size:0.75rem; font-weight:700; color:var(--ai); text-transform:uppercase; margin-top:15px; margin-bottom:5px;'>📸 Registro de Evidencias de Consultas Abiertas (Capturas de Pantalla / Soportes)</p>", unsafe_allow_html=True)
        st.file_uploader(
            "Subir Capturas de Pantalla o Documentos de Soporte (PNG, JPG, PDF) *",
            type=["png", "jpg", "jpeg", "pdf"],
            accept_multiple_files=True,
            key="v6_evidencias_soportes",
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
