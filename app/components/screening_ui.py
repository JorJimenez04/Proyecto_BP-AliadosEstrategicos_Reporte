# app/components/screening_ui.py
import streamlit as st
from datetime import datetime
import pypdf
import re
import os
from fpdf import FPDF

COLOR_PRIMARY = (37, 99, 235)      # Azul Institucional Adamo
COLOR_TEXT_MAIN = (15, 23, 42)     # Slate 900 (Títulos de alta densidad)
COLOR_TEXT_BODY = (51, 65, 85)     # Slate 700 (Cuerpo técnico legible)
COLOR_TEXT_MUTED = (100, 116, 139) # Slate 500 (Indicadores de etiquetas)
COLOR_BG_GRID = (248, 250, 252)    # Slate 50 (Sombreado bento de secciones)
COLOR_LINE_TENUE = (226, 232, 240)  # Slate 200 (Divisores editoriales limpios)

class ComplianceMaestroPDF(FPDF):
    """Estructura de diseño institucional con doble logo simétrico."""

    def __init__(self, logo_adamo=None, logo_holdings=None):
        super().__init__()
        self.logo_adamo = logo_adamo
        self.logo_holdings = logo_holdings
        # top=42 garantiza que el cuerpo nunca se superponga al encabezado
        self.set_margins(left=15, top=42, right=15)

    def header(self):
        # Logos en coordenadas absolutas — no afectan el flujo del cursor
        if self.logo_adamo and os.path.exists(self.logo_adamo):
            self.image(self.logo_adamo, x=15, y=8, w=28)
        if self.logo_holdings and os.path.exists(self.logo_holdings):
            self.image(self.logo_holdings, x=167, y=8, w=28)

        # Textos centrados en la franja entre logos
        self.set_xy(48, 12)
        self.set_font("Helvetica", "B", 9.5)
        self.set_text_color(*COLOR_TEXT_MAIN)
        self.cell(114, 4.5, "ADAMOSERVICES SYSTEM RISK", align="C")

        self.set_xy(48, 17)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*COLOR_TEXT_MUTED)
        self.cell(114, 4, "EXPEDIENTE CONSOLIDADO DE DEBIDA DILIGENCIA Y CONTROL DE RIESGOS", align="C")

        # Línea divisoria azul fija — nunca se mueve
        self.set_draw_color(37, 99, 235)   # #2563eb
        self.set_line_width(0.8)
        self.line(15, 30, 195, 30)

        # Fuerza el cursor al primer renglón seguro del cuerpo
        self.set_y(42)

    def footer(self):
        self.set_y(-18)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*COLOR_TEXT_MUTED)
        self.set_draw_color(*COLOR_LINE_TENUE)
        self.line(15, self.get_y() - 2, 195, self.get_y() - 2)
        self.cell(0, 8, f"Reporte de Cumplimiento Certificado - Confidencial - Pagina {self.page_no()}/{{nb}}", 0, 0, "C")


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


def procesar_archivo_pdf(uploaded_file) -> dict:
    """Extrae el texto completo de un archivo en memoria"""
    if uploaded_file is None:
        return None
    try:
        reader = pypdf.PdfReader(uploaded_file)
        full_text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t: full_text += t + "\n"
        return parsear_texto_infolaft(full_text)
    except Exception:
        return None


def render_resumen_validacion_ui(datos_extracted: dict):
    """Pinta una microtarjeta minimalista de validación digital en tiempo real"""
    if not datos_extracted:
        return
    
    es_limpio = datos_extracted['resultados'] == "0" and datos_extracted['intensificada'] == "NO"
    badge_html = '<span class="ar-badge ar-badge-low">✓ Certificado Limpio</span>' if es_limpio else '<span class="ar-badge ar-badge-critical">⚠ Alerta Detectada</span>'
    
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


def resolver_ruta_logo(nombre_base: str) -> str:
    """Apunta directamente a la ruta física compartida por el usuario"""
    # Construcción de ruta multiplataforma para app/static/img/logos
    folder = os.path.join("app", "static", "img", "logos")
    
    # Soporte por si Streamlit ejecuta el contexto desde la carpeta interna /app
    if not os.path.exists(folder):
        folder = os.path.join("static", "img", "logos")
        
    if os.path.exists(folder):
        for archivo in os.listdir(folder):
            if archivo.lower().startswith(nombre_base.lower()):
                return os.path.join(folder, archivo)
    return None


def _s(texto) -> str:
    """Sanitiza cadenas para FPDF: elimina caracteres fuera del rango latin-1."""
    if not texto:
        return ""
    return str(texto).replace("\u00bf", "").encode("latin-1", "ignore").decode("latin-1")


def generar_pdf_base(datos_master: dict) -> bytes:
    path_adamo = resolver_ruta_logo("Logo Adamo general")
    path_holdings = resolver_ruta_logo("Logo Holdings")

    # set_margins ya está definido en el constructor (top=42)
    pdf = ComplianceMaestroPDF(logo_adamo=path_adamo, logo_holdings=path_holdings)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=18)

    # ── Sanitización de todos los campos de texto ──
    s_empresa   = _s(datos_master['empresa_principal'])
    s_nit       = _s(datos_master['nit_principal'])
    s_radicado  = _s(datos_master['radicado_caso'])
    s_direccion = _s(datos_master['direccion'])
    s_telefono  = _s(datos_master['telefono'])
    s_jurisdic  = _s(datos_master['jurisdiccion'])
    s_web       = _s(datos_master['sitio_web'])
    s_rep_nom   = _s(datos_master['rep_legal_nom'])
    s_rep_id    = _s(datos_master['rep_legal_id'])
    s_acc_nom   = _s(datos_master['accionista_nom'])
    s_acc_id    = _s(datos_master['accionista_id'])
    s_estado    = _s(datos_master['estado_global'])
    s_dictamen  = _s(datos_master['dictamen_motivo'])
    s_rues      = _s(datos_master['rues_noticias_raw'])
    s_fecha     = _s(datos_master['fecha'])

    # ─── ENCABEZADO DE COMPAÑÍA ───
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*COLOR_TEXT_MAIN)
    pdf.cell(0, 7, s_empresa.upper(), ln=1)

    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(0, 4, "NIT Identificador: " + s_nit + "   .   Radicado de Control Interno: " + s_radicado, ln=1)
    pdf.ln(5)

    def render_subseccion_titulo(titulo):
        pdf.set_fill_color(*COLOR_BG_GRID)
        pdf.set_text_color(*COLOR_PRIMARY)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6.5, "  " + _s(titulo).upper(), ln=1, fill=True)
        pdf.ln(3)

    # ─── SECCIÓN 1: LOCALIZACIÓN Y CONTACTO ───
    render_subseccion_titulo("1. Informacion de Localizacion y Contacto")
    pdf.set_font("Helvetica", "B", 8.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(28, 5, "Direccion Fiscal:")
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.cell(62, 5, s_direccion)

    pdf.set_font("Helvetica", "B", 8.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(25, 5, "Jurisdiccion:")
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.cell(0, 5, s_jurisdic, ln=1)

    pdf.set_font("Helvetica", "B", 8.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(28, 5, "Telefono:")
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.cell(62, 5, s_telefono)

    pdf.set_font("Helvetica", "B", 8.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(25, 5, "Sitio Web:")
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.cell(0, 5, s_web, ln=1)
    pdf.ln(5)

    # ─── SECCIÓN 2: ESTRUCTURA DIRECTIVA ───
    render_subseccion_titulo("2. Estructura Directiva y Vinculados Relacionados")
    pdf.set_font("Helvetica", "B", 8.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(35, 5, "Representante Legal:")
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.cell(55, 5, s_rep_nom)

    pdf.set_font("Helvetica", "B", 8.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(25, 5, "Identificacion:")
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.cell(0, 5, s_rep_id, ln=1)

    pdf.set_font("Helvetica", "B", 8.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(35, 5, "Accionista Principal:")
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.cell(55, 5, s_acc_nom)

    pdf.set_font("Helvetica", "B", 8.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(25, 5, "Identificacion:")
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.cell(0, 5, s_acc_id, ln=1)
    pdf.ln(5)

    # ─── SECCIÓN 3: DICTAMEN ───
    render_subseccion_titulo("3. Evaluacion de Riesgo y Conclusion Legal")
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.cell(38, 6, "Dictamen de Aceptacion:  ")

    dictamen_color = (22, 163, 74) if "APROBADO" in s_estado else (217, 119, 6)
    pdf.set_text_color(*dictamen_color)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(0, 6, s_estado, ln=1)

    pdf.ln(1)
    pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.multi_cell(0, 4.2, "Argumentacion Tecnica Corporativa: " + s_dictamen)
    pdf.ln(5)

    # ─── SECCIÓN 4: MATRIZ DE TRAZABILIDAD ───
    render_subseccion_titulo("4. Trazabilidad de Evidencias Indexadas (Cruce Anti-Lavado)")

    w_nombre = 52; w_ident = 25; w_rol = 48; w_rad = 25; w_estado = 30

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(*COLOR_LINE_TENUE)
    pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(w_nombre, 6, "  Nombre / Sujeto Consultado", border="B", fill=True)
    pdf.cell(w_ident,  6, " Identificacion",               border="B", fill=True)
    pdf.cell(w_rol,    6, " Rol de Contraparte",            border="B", fill=True)
    pdf.cell(w_rad,    6, " Radicado Consult",              border="B", fill=True)
    pdf.cell(w_estado, 6, " Estado Analitico",              border="B", fill=True, ln=1)

    pdf.set_font("Helvetica", "", 7.5)
    for ent in datos_master['entidades_procesadas']:
        e_nombre = _s(ent.get('nombre', ''))
        e_id     = _s(ent.get('identificacion', ''))
        e_rol    = _s(ent.get('rol_interno', ''))
        e_rad    = _s(ent.get('radicado', ''))
        es_limpio  = ent.get('resultados', '0') == "0" and ent.get('intensificada', 'NO') == "NO"
        estado_txt = "  CONCORDANCIA LIMPIA" if es_limpio else "  REQUIERE AUDITORIA"
        estado_rgb = (22, 163, 74) if es_limpio else (220, 38, 38)

        pdf.set_text_color(*COLOR_TEXT_MAIN)
        pdf.cell(w_nombre, 5.5, "  " + e_nombre[:30], border="B")
        pdf.cell(w_ident,  5.5, "  " + e_id,          border="B")
        pdf.cell(w_rol,    5.5, "  " + e_rol[:28],     border="B")
        pdf.cell(w_rad,    5.5, "  " + e_rad,          border="B")
        pdf.set_text_color(*estado_rgb)
        pdf.cell(w_estado, 5.5, estado_txt, border="B", ln=1)

    # ─── SECCIÓN 5: HALLAZGOS FUENTES ABIERTAS ───
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(0, 5, "5. Hallazgos Complementarios en Fuentes Abiertas (RUES / Prensa):", ln=1)

    pdf.ln(1)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*COLOR_TEXT_BODY)
    contenido_rues = s_rues.strip()
    pdf.multi_cell(0, 4, contenido_rues if contenido_rues else
        "No se identificaron referencias de prensa desfavorable o anomalias mercantiles en los sistemas publicos de verificacion.")

    # ── Sellado de seguridad digital ──
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(0, 3.5, "Fecha y hora del sellado digital: " + s_fecha + " COT", ln=1)
    pdf.cell(0, 3.5, "Hash de Autenticidad: ADAMO-RISK-" + s_nit.replace('-', '') + "-" + s_radicado.upper(), ln=1)

    raw_pdf = pdf.output()
    return bytes(raw_pdf) if isinstance(raw_pdf, (bytearray, list)) else raw_pdf


def compilar_expediente_completo(bytes_base: bytes, infolaft_bytes_list: list) -> bytes:
    """
    Fusiona el expediente institucional con los PDF de Infolaft como evidencia adjunta.
    Operacion vectorial pura en memoria usando pypdf — sin dependencias del sistema.
    """
    import io
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()

    # 1. Paginas del expediente institucional
    reader_base = PdfReader(io.BytesIO(bytes_base))
    for page in reader_base.pages:
        writer.add_page(page)

    # 2. Adjuntar cada reporte Infolaft completo como evidencia
    for b in infolaft_bytes_list:
        if not b:
            continue
        try:
            reader_evi = PdfReader(io.BytesIO(b))
            for page in reader_evi.pages:
                writer.add_page(page)
        except Exception:
            continue  # PDF invalido — se omite sin romper el expediente

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def callback_ejecutar_compilacion(user: dict):
    """Procesador prioritario en memoria RAM"""
    v_empresa = st.session_state.get("v6_empresa_master", "").strip()
    v_nit = st.session_state.get("v6_nit_master", "").strip()
    v_radicado = st.session_state.get("v6_radicado_caso", "").strip()
    v_rep_nom = st.session_state.get("v6_rep_legal_nom", "").strip()
    v_rep_id = st.session_state.get("v6_rep_legal_id", "").strip()
    v_dictamen = st.session_state.get("v6_dictamen_motivo", "").strip()
    
    v_direccion = st.session_state.get("v6_direccion", "").strip()
    v_telefono = st.session_state.get("v6_telefono", "").strip()
    v_jurisdiccion = st.session_state.get("v6_jurisdiccion", "").strip()
    v_sitio_web = st.session_state.get("v6_sitio_web", "").strip()
    v_rues_news = st.session_state.get("v6_rues_noticias_raw", "").strip()

    es_mismo = st.session_state.get("v6_chk_accionista_es_rep", False)
    if es_mismo:
        v_acc_nom = v_rep_nom
        v_acc_id = v_rep_id
    else:
        v_acc_nom = st.session_state.get("v6_acc_nom_en", "").strip()
        v_acc_id = st.session_state.get("v6_acc_id_en", "").strip()

    campos_faltantes = []
    if not v_empresa: campos_faltantes.append("Razón Social de la Empresa")
    if not v_nit: campos_faltantes.append("NIT Comercial")
    if not v_radicado: campos_faltantes.append("Código de Radicado Único Interno")
    if not v_rep_nom: campos_faltantes.append("Nombre del Representante Legal")
    if not v_dictamen: campos_faltantes.append("Análisis Argumentativo Legal (Dictamen)")

    if campos_faltantes:
        st.session_state["v6_just_validated"] = True
        st.session_state["v6_f_errores"] = campos_faltantes
        st.session_state["v6_f_pdf_bytes"] = None
        st.session_state["v6_f_nit"] = ""
        return

    file_empresa = st.session_state.get("v6_pdf_empresa")
    file_rep = st.session_state.get("v6_pdf_rep")
    file_acc = st.session_state.get("v6_pdf_acc")

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

    alertas_vivas = any([ent['resultados'] != "0" or ent['intensificada'] == "SI" for ent in entidades_lista])
    estado_global = "REQUIERE REVISIÓN INTENSIFICADA" if alertas_vivas else "APROBADO S/ANOMALÍAS"

    payload_maestro = {
        "empresa_principal": v_empresa,
        "nit_principal": v_nit,
        "direccion": v_direccion if v_direccion else "No Declarada",
        "telefono": v_telefono if v_telefono else "No Declarado",
        "jurisdiccion": v_jurisdiccion,
        "sitio_web": v_sitio_web if v_sitio_web else "No Registrado",
        "rep_legal_nom": v_rep_nom,
        "rep_legal_id": v_rep_id,
        "accionista_nom": v_acc_nom,
        "accionista_id": v_acc_id,
        "radicado_caso": v_radicado,
        "dictamen_motivo": v_dictamen,
        "rues_noticias_raw": v_rues_news,
        "estado_global": estado_global,
        "entidades_procesadas": entidades_lista,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "analista": user.get("username", "sistema")
    }

    # Lectura de bytes de los archivos Infolaft para adjunto vectorial
    def _leer_bytes_uploader(f):
        if f is None:
            return None
        try:
            f.seek(0)
            return f.read()
        except Exception:
            return None

    infolaft_bytes = [
        b for fk in ("v6_pdf_empresa", "v6_pdf_rep", "v6_pdf_acc")
        if (b := _leer_bytes_uploader(st.session_state.get(fk))) is not None
    ]

    st.session_state["v6_f_errores"] = []
    bytes_base = generar_pdf_base(payload_maestro)
    st.session_state["v6_f_pdf_bytes"] = compilar_expediente_completo(bytes_base, infolaft_bytes)
    st.session_state["v6_f_nit"] = v_nit
    st.session_state["v6_f_estado_global"] = estado_global
    st.session_state["v6_f_dictamen"] = v_dictamen


def render_screening_workspace(user: dict):
    st.markdown('<p class="ar-section-title" style="margin-bottom:0px;">Intelligence Workspace</p>', unsafe_allow_html=True)
    st.markdown('<h1 style="margin-top:0px; font-weight:800; letter-spacing:-0.03em;">Debida Diligencia Corporativa</h1>', unsafe_allow_html=True)
    
    if "v6_f_pdf_bytes" not in st.session_state: st.session_state["v6_f_pdf_bytes"] = None
    if "v6_f_nit" not in st.session_state: st.session_state["v6_f_nit"] = ""
    # Errores solo persisten el ciclo inmediato después del clic del botón.
    # Si el flag no está activo (navegación, rerun por otro widget), se limpian.
    if st.session_state.get("v6_just_validated", False):
        st.session_state["v6_just_validated"] = False
    else:
        st.session_state["v6_f_errores"] = []
    if "v6_f_errores" not in st.session_state:
        st.session_state["v6_f_errores"] = []

    # 🏢 SECCIÓN MODULE 1: Información Corporativa y Evidencia Digital
    with st.container():
        st.markdown('<p class="ar-section-title">1. Información Corporativa y Evidencia Digital</p>', unsafe_allow_html=True)
        col_m1_left, col_m1_right = st.columns([1.1, 0.9])
        
        with col_m1_left:
            st.text_input("Razón Social de la Empresa *", placeholder="Ej: JMNZ S.A.S.", key="v6_empresa_master")
            st.text_input("NIT Comercial (Con Dígito de Verificación) *", placeholder="Ej: 902049753-0", key="v6_nit_master")
            st.text_input("Código de Radicado Único Interno *", placeholder="Ej: EXP-JMNZ-2026", key="v6_radicado_caso")
            st.text_input("Dirección Fiscal / Domicilio", placeholder="Ej: Av. Circunvalar No. 12-45", key="v6_direccion")
            st.text_input("Teléfono de Contacto Operativo", placeholder="Ej: +57 312 456 7890", key="v6_telefono")
            st.text_input("Jurisdicción de Riesgo / Ciudad *", placeholder="Ej: Pereira, Risaralda", key="v6_jurisdiccion")
            st.text_input("Canal Digital / Sitio Web", placeholder="Ej: www.jmnz.co", key="v6_sitio_web")
        
        with col_m1_right:
            st.markdown("<p style='font-size:0.75rem; font-weight:700; color:var(--ai); text-transform:uppercase; margin-bottom:5px;'>📄 Reporte Infolaft (Sociedad)</p>", unsafe_allow_html=True)
            file_empresa = st.file_uploader("Subir PDF Infolaft de la Empresa", type=["pdf"], key="v6_pdf_empresa", label_visibility="collapsed")
            parsed_empresa = procesar_archivo_pdf(file_empresa)
            if parsed_empresa:
                parsed_empresa["rol_interno"] = "Empresa Principal"
                render_resumen_validacion_ui(parsed_empresa)
            else:
                st.caption("Esperando archivo PDF oficial de la sociedad...")

    st.markdown('<div class="ar-divider" style="margin: 25px 0;"></div>', unsafe_allow_html=True)

    # 👥 SECCIÓN MODULE 2: Estructura de Administración y Control Directivo
    with st.container():
        st.markdown('<p class="ar-section-title">2. Estructura de Administración y Control Directivo</p>', unsafe_allow_html=True)
        col_m2_left, col_m2_right = st.columns([1.1, 0.9])
        
        with col_m2_left:
            st.text_input("Nombre Completo (Representante Legal) *", placeholder="Nombre del firmante legal", key="v6_rep_legal_nom")
            st.text_input("Documento de Identidad (Representante Legal) *", placeholder="Número de cédula o pasaporte", key="v6_rep_legal_id")
        
        with col_m2_right:
            st.markdown("<p style='font-size:0.75rem; font-weight:700; color:var(--ai); text-transform:uppercase; margin-bottom:5px;'>📄 Reporte Infolaft (Representante)</p>", unsafe_allow_html=True)
            file_replegal = st.file_uploader("Subir PDF Infolaft del Rep. Legal", type=["pdf"], key="v6_pdf_rep", label_visibility="collapsed")
            parsed_replegal = procesar_archivo_pdf(file_replegal)
            if parsed_replegal:
                parsed_replegal["rol_interno"] = "Representante Legal"
                render_resumen_validacion_ui(parsed_replegal)
            else:
                st.caption("Esperando archivo PDF oficial del representante...")

    st.markdown('<div class="ar-divider" style="margin: 25px 0;"></div>', unsafe_allow_html=True)

    # 📊 SECCIÓN MODULE 3: Composición Accionaria y Beneficiarios Finales
    with st.container():
        st.markdown('<p class="ar-section-title">3. Composición Accionaria y Beneficiarios Finales</p>', unsafe_allow_html=True)
        
        accionista_es_rep_legal = st.checkbox(
            "El Accionista Principal es el mismo Representante Legal de la compañía", 
            value=False,
            key="v6_chk_accionista_es_rep"
        )
        
        col_m3_left, col_m3_right = st.columns([1.1, 0.9])
        current_rep_nom = st.session_state.get("v6_rep_legal_nom", "")
        current_rep_id = st.session_state.get("v6_rep_legal_id", "")
        
        with col_m3_left:
            if accionista_es_rep_legal:
                st.text_input("Nombre Completo (Accionista Mayoritario)", value=current_rep_nom, disabled=True, key="v6_acc_nom_dis")
                st.text_input("Identificación (Accionista Mayoritario)", value=current_rep_id, disabled=True, key="v6_acc_id_dis")
            else:
                st.text_input("Nombre Completo (Accionista Mayoritario) *", placeholder="Nombre del socio principal", key="v6_acc_nom_en")
                st.text_input("Identificación (Accionista Mayoritario) *", placeholder="ID del socio principal", key="v6_acc_id_en")
        
        with col_m3_right:
            if st.session_state.v6_chk_accionista_es_rep:
                st.info("ℹ️ Sistema en modo de duplicidad cero.")
                parsed_accionista = None
            else:
                st.markdown("<p style='font-size:0.75rem; font-weight:700; color:var(--ai); text-transform:uppercase; margin-bottom:5px;'>📄 Reporte Infolaft (Accionista)</p>", unsafe_allow_html=True)
                file_accionista = st.file_uploader("Subir PDF Infolaft del Accionista", type=["pdf"], key="v6_pdf_acc", label_visibility="collapsed")
                parsed_accionista = procesar_archivo_pdf(file_accionista)
                if parsed_accionista:
                    parsed_accionista["rol_interno"] = "Accionista / Beneficiario Final"
                    render_resumen_validacion_ui(parsed_accionista)

    st.markdown('<div class="ar-divider" style="margin: 25px 0;"></div>', unsafe_allow_html=True)

    # 🧠 SECCIÓN MODULE 4: Dictamen del Oficial y Sustento Técnico
    with st.container():
        st.markdown('<p class="ar-section-title">4. Dictamen del Oficial y Sustento Técnico</p>', unsafe_allow_html=True)
        st.text_area("Análisis Argumentativo Legal (Enfoque Basado en Riesgo) *", placeholder="Sustente rigurosamente el dictamen técnico de aceptación, rechazo o condicionamiento...", key="v6_dictamen_motivo")
        st.text_area("Notas de Prensa y Validación de Registro Mercantil (RUES)", placeholder="Pegue aquí el bloque de texto con los hallazgos de background check en fuentes abiertas...", key="v6_rues_noticias_raw")

    # Mapeo informativo sobre la ruta exacta del proyecto
    missing_logos = []
    if not resolver_ruta_logo("Logo Adamo general"): missing_logos.append("'Logo Adamo general'")
    if not resolver_ruta_logo("Logo Holdings"): missing_logos.append("'Logo Holdings'")
    
    if missing_logos:
        st.warning(f"⚠️ Alerta de Identidad: No se detectan los archivos {', '.join(missing_logos)} en la ruta 'app/static/img/logos/'. El PDF adaptará su espaciado de forma automática.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.button("⚡ Compilar y Validar Expediente de Caso", on_click=callback_ejecutar_compilacion, args=(user,), use_container_width=True)

    # Renderizador asíncrono de buffers congelados
    if st.session_state["v6_f_errores"]:
        st.markdown('<div class="ar-alert-strip ar-alert-strip-critical" style="margin-top:15px;">', unsafe_allow_html=True)
        st.markdown("❌ <b>Error Operacional:</b> Por favor diligencie los siguientes campos mandatorios:", unsafe_allow_html=True)
        st.markdown(f"<ul>" + "".join([f"<li>{campo}</li>" for campo in st.session_state["v6_f_errores"]]) + "</ul>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state["v6_f_pdf_bytes"]:
        est_glob = st.session_state.get("v6_f_estado_global", "")
        strip_class = "ar-alert-strip-warning" if "REVISIÓN" in est_glob else "ar-alert-strip-success"
        
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
        
        st.download_button(
            label="📥 Descargar Expediente Maestro de Cumplimiento Certificado (.pdf)",
            data=st.session_state["v6_f_pdf_bytes"],
            file_name=f"Expediente_Consolidado_{st.session_state['v6_f_nit']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )