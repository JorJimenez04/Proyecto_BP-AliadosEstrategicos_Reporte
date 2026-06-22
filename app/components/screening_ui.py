# app/components/screening_ui.py
import streamlit as st
from datetime import datetime
import pypdf
import re
from fpdf import FPDF

class ComplianceMaestroPDF(FPDF):
    """Diseño institucional para expedientes consolidados multi-entidad"""
    def header(self):
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(31, 41, 55)
        self.cell(0, 5, "ADAMOSERVICES SYSTEM RISK · DEPARTAMENTO DE CUMPLIMIENTO", ln=1)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(107, 114, 128)
        self.cell(0, 4, "EXPEDIENTE MAESTRO DE DEBIDA DILIGENCIA CONSOLIDADO (CONTRAPARTE Y VINCULADOS)", ln=1)
        self.set_draw_color(120, 87, 255)
        self.set_line_width(0.5)
        self.line(10, 18, 200, 18)
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(156, 163, 175)
        self.cell(0, 10, f"Prueba documental de cumplimiento unificado - Pagina {self.page_no()}/{{nb}}", 0, 0, "C")


def parsear_texto_infolaft(texto: str) -> dict:
    """Analiza las cadenas de texto del PDF de Infolaft mediante expresiones regulares"""
    res = {
        "nombre": "No detectado",
        "identificacion": "No detectado",
        "radicado": "No detectado",
        "fecha_consulta": "No detectado",
        "resultados": "0",
        "intensificada": "NO"
    }
    texto_plano = texto.replace("\n", " ")

    radicado_match = re.search(r"NÚMERO DE CONSULTA:\s*.*?\b(\d{9})\b", texto_plano, re.IGNORECASE)
    if radicado_match: res["radicado"] = radicado_match.group(1)
    
    id_match = re.search(r"DOCUMENTO DE IDENTIDAD:\s*([\d-]+)", texto_plano, re.IGNORECASE)
    if id_match: res["identificacion"] = id_match.group(1).strip()

    fecha_match = re.search(r"FECHA Y HORA DE CONSULTA:?\s*([\d/]+ [\d:]+)", texto_plano, re.IGNORECASE)
    if fecha_match: res["fecha_consulta"] = fecha_match.group(1).strip()

    resultados_match = re.search(r"RESUMEN DE RESULTADOS:\s*(\d+)", texto_plano, re.IGNORECASE)
    if resultados_match: res["resultados"] = resultados_match.group(1)

    gafi_match = re.search(r"RIESGO GAFI\??:\s*(NO|SI)", texto_plano, re.IGNORECASE)
    if gafi_match: res["intensificada"] = gafi_match.group(1)

    lines = [line.strip() for line in texto.split("\n") if line.strip()]
    for i, line in enumerate(lines):
        if "SU CONSULTA FUE:" in line:
            if i + 1 < len(lines) and "DOCUMENTO" not in lines[i+1]: res["nombre"] = lines[i+1]
            elif i - 1 >= 0 and "DATOS CONSULTADOS" not in lines[i-1]: res["nombre"] = lines[i-1]
        elif "DATOS CONSULTADOS" in line and i + 1 < len(lines) and "SU CONSULTA" not in lines[i+1]:
            res["nombre"] = lines[i+1]

    return res


def generar_pdf_consolidado(datos_master: dict) -> bytes:
    pdf = ComplianceMaestroPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # --- Cabecera Perfil Empresa ---
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(17, 24, 39)
    pdf.cell(0, 6, datos_master['empresa_principal'].upper(), ln=1)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(107, 114, 128)
    pdf.cell(0, 5, f"NIT: {datos_master['nit_principal']} | Radicado del Expediente: {datos_master['radicado_caso']}", ln=1)
    pdf.ln(3)

    # --- Ficha Técnica extendida corporativa ---
    pdf.set_fill_color(243, 244, 246)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(17, 24, 39)
    pdf.cell(0, 6, " 1. INFORMACION CORPORATIVA DE LA CONTRAPARTE", ln=1, fill=True)
    pdf.ln(2)
    
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(40, 5, "Direccion:", font_style="B"); pdf.cell(60, 5, datos_master['direccion'])
    pdf.cell(35, 5, "Jurisdiccion:", font_style="B"); pdf.cell(0, 5, datos_master['jurisdiccion'], ln=1)
    
    pdf.cell(40, 5, "Telefono:", font_style="B"); pdf.cell(60, 5, datos_master['telefono'])
    pdf.cell(35, 5, "Sitio Web:", font_style="B"); pdf.cell(0, 5, datos_master['sitio_web'], ln=1)
    pdf.ln(3)

    # --- Gobierno Corporativo ---
    pdf.cell(0, 6, " 2. ESTRUCTURA DE GOBIERNO Y CONTROL COMPARTIDO", ln=1, fill=True)
    pdf.ln(2)
    pdf.cell(40, 5, "Representante Legal:", font_style="B"); pdf.cell(60, 5, datos_master['rep_legal_nom'])
    pdf.cell(35, 5, "Identificacion:", font_style="B"); pdf.cell(0, 5, datos_master['rep_legal_id'], ln=1)
    
    pdf.cell(40, 5, "Accionista Principal:", font_style="B"); pdf.cell(60, 5, datos_master['accionista_nom'])
    pdf.cell(35, 5, "Identificacion:", font_style="B"); pdf.cell(0, 5, datos_master['accionista_id'], ln=1)
    pdf.ln(4)

    # --- Dictamen Centralizado ---
    pdf.cell(0, 6, " 3. EVALUACION DE RIESGO Y DICTAMEN DE CUMPLIMIENTO", ln=1, fill=True)
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(40, 5, "Dictamen Global:")
    if "APROBADO" in datos_master['estado_global']:
        pdf.set_text_color(34, 197, 94)
    else:
        pdf.set_text_color(245, 158, 11)
    pdf.cell(0, 5, datos_master['estado_global'], ln=1)
    
    pdf.set_text_color(17, 24, 39)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 4.5, datos_master['dictamen_motivo'])
    pdf.ln(4)

    # --- Matriz Unificada ---
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, " 4. TRAZABILIDAD AUTOMATICA DE ARCHIVOS INDEXADOS (INFOLAFT)", ln=1, fill=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(229, 231, 235)
    pdf.cell(65, 5, "Sujeto Consultado", border=1, fill=True)
    pdf.cell(30, 5, "ID Documento", border=1, fill=True)
    pdf.cell(32, 5, "Rol Asignado", border=1, fill=True)
    pdf.cell(28, 5, "Radicado Infolaft", border=1, fill=True)
    pdf.cell(35, 5, "Resultado Cruce", border=1, fill=True, ln=1)

    pdf.set_font("Helvetica", "", 8)
    for ent in datos_master['entidades_procesadas']:
        pdf.cell(65, 5, ent['nombre'][:38], border=1)
        pdf.cell(30, 5, ent['identificacion'], border=1)
        pdf.cell(32, 5, ent['rol_interno'], border=1)
        pdf.cell(28, 5, ent['radicado'], border=1)
        
        if ent['resultados'] == "0" and ent['intensificada'] == "NO":
            pdf.set_text_color(34, 197, 94)
            pdf.cell(35, 5, "SIN COINCIDENCIA", border=1, ln=1)
        else:
            pdf.set_text_color(239, 68, 68)
            pdf.cell(35, 5, "REQUIERE AUDITORIA", border=1, ln=1)
        pdf.set_text_color(17, 24, 39)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, "HISTORIAL Y ANTECEDENTES COMPLEMENTARIOS:", ln=1)
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(0, 4, datos_master['rues_noticias_raw'] if datos_master['rues_noticias_raw'].strip() else "Sin novedades registradas.")

    return pdf.output()


def render_screening_workspace(user: dict):
    # ── Encabezado Minimalista de Alta Gama ───────────────────
    st.markdown('<p class="ar-section-title" style="margin-bottom:0px;">Intelligence Workspace</p>', unsafe_allow_html=True)
    st.markdown('<h1 style="margin-top:0px; font-weight:800; letter-spacing:-0.03em;">Debida Diligencia Corporativa</h1>', unsafe_allow_html=True)
    
    st.markdown(
        f'<div class="ar-alert-strip" style="margin-bottom: 25px;">'
        f'Módulo de control técnico activo para el oficial de cumplimiento: <code style="color:var(--ai); font-weight:600;">{user.get("username", "sistema")}</code>. '
        f'Todos los campos con asterisco (*) son obligatorios para la certificación legal del expediente.'
        f'</div>', 
        unsafe_allow_html=True
    )

    entidades_lista = []

    # ── Formulario Central de Entrada de Datos ────────────────
    with st.form("form_caso_consolidado_v4", clear_on_submit=False):
        
        # 🏢 SECCIÓN 1: Perfil de la Contraparte
        st.markdown('<p class="ar-section-title">1. Información Corporativa y de Contacto</p>', unsafe_allow_html=True)
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            empresa_master = st.text_input("Razón Social de la Empresa *", placeholder="Ej: JMNZ S.A.S.")
            direccion = st.text_input("Dirección Fiscal / Domicilio", placeholder="Ej: Av. Circunvalar No. 12-45")
            telefono = st.text_input("Teléfono de Contacto Operativo", placeholder="Ej: +57 312 456 7890")
        with col_c2:
            nit_master = st.text_input("NIT Comercial (Con Dígito de Verificación) *", placeholder="Ej: 902049753-0")
            jurisdiccion = st.text_input("Jurisdicción de Riesgo / Ciudad *", placeholder="Ej: Pereira, Risaralda")
            sitio_web = st.text_input("Canal Digital / Sitio Web", placeholder="Ej: www.jmnz.co")
            
        radicado_caso = st.text_input("Código de Radicado Único Interno *", placeholder="Ej: EXP-JMNZ-2026")

        st.markdown('<div class="ar-divider"></div>', unsafe_allow_html=True)

        # 👥 SECCIÓN 2: Estructura de Poder y Gobierno
        st.markdown('<p class="ar-section-title">2. Estructura de Control y Gobierno Corporativo</p>', unsafe_allow_html=True)
        
        st.markdown("<p style='font-size:0.85rem; font-weight:600; color:#ffffff; margin-bottom:2px;'>Director / Representante Legal Principal</p>", unsafe_allow_html=True)
        col_rl1, col_rl2 = st.columns(2)
        with col_rl1:
            rep_legal_nom = st.text_input("Nombre Completo (Representante) *", placeholder="Nombre del firmante legal")
        with col_rl2:
            rep_legal_id = st.text_input("Documento de Identidad (Representante) *", placeholder="Número de cédula o pasaporte")

        st.markdown("<p style='font-size:0.85rem; font-weight:600; color:#ffffff; margin-top:15px; margin-bottom:2px;'>Beneficiario Final / Composición Accionaria</p>", unsafe_allow_html=True)
        
        # Checkbox integrado discretamente
        accionista_es_rep_legal = st.checkbox(
            "El Accionista Principal es el mismo Representante Legal de la compañía", 
            value=False,
            help="Habilita esta opción para mitigar duplicidad manual de datos en la base de control."
        )

        col_acc1, col_acc2 = st.columns(2)
        with col_acc1:
            if accionista_es_rep_legal:
                accionista_nom = st.text_input("Nombre Completo (Accionista)", value=rep_legal_nom, disabled=True, key="acc_nom_dis")
            else:
                accionista_nom = st.text_input("Nombre Completo (Accionista) *", placeholder="Nombre del accionista mayoritario", key="acc_nom_en")
        with col_acc2:
            if accionista_es_rep_legal:
                accionista_id = st.text_input("Identificación (Accionista)", value=rep_legal_id, disabled=True, key="acc_id_dis")
            else:
                accionista_id = st.text_input("Identificación (Accionista) *", placeholder="ID del accionista mayoritario", key="acc_id_en")

        st.markdown('<div class="ar-divider"></div>', unsafe_allow_html=True)

        # 🧠 SECCIÓN 3: Conclusiones de Cumplimiento
        st.markdown('<p class="ar-section-title">3. Dictamen de Cierre y Sustento Técnico</p>', unsafe_allow_html=True)
        dictamen_motivo = st.text_area(
            "Análisis Argumentativo Legal (Enfoque Basado en Riesgo) *",
            placeholder="Argumente detalladamente la aceptación o condicionamiento de la contraparte para la auditoría..."
        )

        st.markdown('<p class="ar-section-title" style="margin-top:15px;">4. Trazabilidad de Evidencia en Fuentes Abiertas</p>', unsafe_allow_html=True)
        rues_noticias_raw = st.text_area(
            "Notas de Prensa y Validación de Registro Mercantil (RUES)",
            placeholder="Pega aquí los fragmentos textuales de las consultas complementarias realizadas en la web..."
        )

        st.markdown("<br>", unsafe_allow_html=True)
        submit_btn = st.form_submit_button("⚡ Compilar y Validar Expediente de Caso")

    # 📥 SECCIÓN 4: Carga y Procesamiento de Certificados Infolaft
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p class="ar-section-title">5. Depósito Documental (Validación Digital Automática)</p>', unsafe_allow_html=True)
    
    archivos_cargados = st.file_uploader(
        "Arrastra en lote los reportes de Infolaft de la Empresa, Representantes y Socios",
        type=["pdf"],
        accept_multiple_files=True,
        key="uploader_maestro_v4",
        label_visibility="collapsed"
    )

    # Tarjeta contenedora minimalista para los resultados del Parser
    if archivos_cargados:
        st.markdown('<div class="ar-card">', unsafe_allow_html=True)
        st.markdown('<p class="ar-section-title" style="color:var(--ai);">Certificados Indexados en Memoria</p>', unsafe_allow_html=True)
        
        for idx, file in enumerate(archivos_cargados):
            try:
                reader = pypdf.PdfReader(file)
                full_text = ""
                for page in reader.pages:
                    t = page.extract_text()
                    if t: full_text += t + "\n"
                
                datos_parsea = parsear_texto_infolaft(full_text)
                
                col_det, col_rol = st.columns([3, 1])
                with col_det:
                    status_badge = '<span class="ar-badge ar-badge-low">Limpio</span>' if datos_parsea['resultados'] == "0" else '<span class="ar-badge ar-badge-critical">Alerta</span>'
                    st.markdown(
                        f"<div style='margin-bottom:8px;'>"
                        f"{status_badge} <b style='color:#ffffff;'>{datos_parsea['nombre']}</b> — ID: <code>{datos_parsea['identificacion']}</code>"
                        f"<br><span style='color:var(--fg-muted); font-size:0.78rem;'>Radicado Infolaft: {datos_parsea['radicado']} | Registros Encontrados: {datos_parsea['resultados']}</span>"
                        f"</div>", 
                        unsafe_allow_html=True
                    )
                with col_rol:
                    rol_elegido = st.selectbox(
                        "Rol Estructural",
                        ["Empresa Principal", "Representante Legal", "Beneficiario Final", "Accionista", "Miembro de Junta"],
                        key=f"rol_v4_{idx}_{datos_parsea['identificacion']}",
                        label_visibility="collapsed"
                    )
                
                datos_parsea["rol_interno"] = rol_elegido
                entidades_lista.append(datos_parsea)
                if idx < len(archivos_cargados) - 1:
                    st.markdown('<div class="ar-divider" style="margin:8px 0;"></div>', unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"Error procesando el archivo {file.name}: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Ejecución de Cierre de Caso y Renderizado de Salida ──
    if submit_btn:
        if not empresa_master or not nit_master or not dictamen_motivo or not rep_legal_nom or not radicado_caso:
            st.markdown('<div class="ar-alert-strip ar-alert-strip-critical" style="margin-top:15px;">❌ Error operacional: Diligencie los campos mandatorios corporativos y el Dictamen para cerrar el radicado.</div>', unsafe_allow_html=True)
            st.stop()

        # Análisis automático de alertas del lote
        alertas_vivas = any([ent['resultados'] != "0" or ent['intensificada'] == "SI" for ent in entidades_lista])
        estado_global = "REQUIERE REVISIÓN INTENSIFICADA" if alertas_vivas else "APROBADO S/ANOMALÍAS"
        strip_class = "ar-alert-strip-warning" if alertas_vivas else "ar-alert-strip-success"

        # Armar el Payload Estructurado para el Reporte
        payload_maestro = {
            "empresa_principal": empresa_master,
            "nit_principal": nit_master,
            "direccion": direccion if direccion else "No Declarada",
            "telefono": telefono if telefono else "No Declarado",
            "jurisdiccion": jurisdiccion,
            "sitio_web": sitio_web if sitio_web else "No Registrado",
            "rep_legal_nom": rep_legal_nom,
            "rep_legal_id": rep_legal_id,
            "accionista_nom": accionista_nom,
            "accionista_id": accionista_id,
            "radicado_caso": radicado_caso,
            "dictamen_motivo": dictamen_motivo,
            "rues_noticias_raw": rues_noticias_raw,
            "estado_global": estado_global,
            "entidades_processed": entidades_lista,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "analista": user.get("username", "sistema")
        }

        # Renderizado del bloque SaaS Premium
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
            <div class="ar-card ar-ai-glow">
                <p class="ar-section-title" style="color:var(--ai);">Expediente Corporativo Homologado</p>
                <div style="font-size: 1.75rem; font-weight: 800; color: #ffffff; letter-spacing: -0.02em;">{estado_global}</div>
                <div class="ar-alert-strip {strip_class}" style="margin-top: 12px; font-size:0.85rem;">
                    <b>Sustento Técnico del Oficial:</b> {dictamen_motivo}
                </div>
            </div>
            <br>
        """, unsafe_allow_html=True)
        
        # Generar PDF
        pdf_bytes = generar_pdf_consolidado(payload_maestro)

        st.download_button(
            label="📥 Descargar Expediente Maestro de Cumplimiento Certificado (.pdf)",
            data=pdf_bytes,
            file_name=f"Expediente_Consolidado_{nit_master}.pdf",
            mime="application/pdf",
            use_container_width=True
        )