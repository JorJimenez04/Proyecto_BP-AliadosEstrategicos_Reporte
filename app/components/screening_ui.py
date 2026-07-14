# app/components/screening_ui.py
import streamlit as st
from datetime import datetime
import pypdf
import re
import os
import io
from fpdf import FPDF

# ─── NUEVA PALETA DE COLORES EDITORIAL PREMIUM ───
COLOR_PRIMARY = (15, 32, 67)       # Azul Marino Profundo (Autoridad / Corporativo)
COLOR_ACCENT = (37, 99, 235)       # Azul Eléctrico (Sutiles acentos / Líneas de título)
COLOR_TEXT_MAIN = (15, 23, 42)     # Slate 900 (Títulos de alta densidad)
COLOR_TEXT_BODY = (30, 41, 59)     # Slate 800 (Cuerpo técnico de alta legibilidad)
COLOR_TEXT_MUTED = (100, 116, 139) # Slate 500 (Subtítulos y etiquetas secundarias)
COLOR_BG_GRID = (248, 250, 252)    # Slate 50 (Fondo bento homogéneo y limpio)
COLOR_LINE_TENUE = (226, 232, 240) # Slate 200 (Bordes ultra sutiles de contenedores)
COLOR_SUCCESS    = (22, 163, 74)   # Green 600 (Estado limpio / Aprobado)
COLOR_DANGER     = (220, 38, 38)   # Red 600   (Alerta crítica / Requiere auditoría)
COLOR_WARNING    = (217, 119, 6)   # Amber 600 (Revisión intensificada)


class ComplianceMaestroPDF(FPDF):
    """
    PDF institucional Bento Grid premium — estética SaaS/Fintech editorial.

    Regla de oro FPDF2: header() NO llama a set_xy/set_y al final.
    El margen top=38 absorbe los ~30mm del bloque de encabezado estático
    y garantiza que el flujo del cuerpo nunca colisione con él.
    """

    def __init__(self, logo_adamo=None, logo_holdings=None):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.logo_adamo    = logo_adamo
        self.logo_holdings = logo_holdings
        self.set_margins(left=15, top=38, right=15)

    def header(self):
        # ── Logotipos (posicionamiento absoluto propio del encabezado) ─────────
        if self.logo_adamo and os.path.exists(self.logo_adamo):
            self.image(self.logo_adamo, x=15, y=5, h=14)
        if self.logo_holdings and os.path.exists(self.logo_holdings):
            self.image(self.logo_holdings, x=167, y=8.5, h=11)

        # ── Títulos centrales (canal protegido entre logotipos) ───────────────
        self.set_xy(48, 9)
        self.set_font("Helvetica", "B", 8.5)
        self.set_text_color(*COLOR_PRIMARY)
        self.cell(114, 4.5, "EXPEDIENTE CONSOLIDADO DE DEBIDA DILIGENCIA Y CONTROL DE RIESGOS", align="C")

        self.set_xy(48, 14.5)
        self.set_font("Helvetica", "", 6.8)
        self.set_text_color(*COLOR_TEXT_MUTED)
        self.cell(114, 4, "SCREENING - PROCESOS DE VINCULACION Y MONITOREO CONTINUO", align="C")

        # ── Separador editorial doble: acento eléctrico + borde tenue ────────
        self.set_draw_color(*COLOR_ACCENT)
        self.set_line_width(0.7)
        self.line(15, 26, 195, 26)
        self.set_draw_color(*COLOR_LINE_TENUE)
        self.set_line_width(0.2)
        self.line(15, 27.5, 195, 27.5)

        # ✓ Restablecer cursor al inicio del cuerpo.
        # add_page() resetea a (l_margin, t_margin) ANTES de llamar a header(),
        # no después. Si no hacemos esto, el cuerpo empieza donde header() dejó
        # el cursor (dentro del área del encabezado) causando solapamiento con logos.
        self.set_y(self.t_margin)  # reset_x=True por defecto → x = l_margin = 15

    def footer(self):
        self.set_y(-15)
        self.set_draw_color(*COLOR_LINE_TENUE)
        self.set_line_width(0.25)
        self.line(15, self.get_y() - 1, 195, self.get_y() - 1)
        self.set_font("Helvetica", "I", 6.8)
        self.set_text_color(*COLOR_TEXT_MUTED)
        self.cell(120, 6, "CONFIDENCIAL - Uso Exclusivo Interno de Cumplimiento ALD/CFT", 0, 0, "L")
        self.cell(0, 6, f"Pág. {self.page_no()}/{{nb}}", 0, 0, "R")


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
    """Apunta directamente a la ruta física en el proyecto"""
    folder = os.path.join("app", "static", "img", "logos")
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
    """
    Genera el PDF institucional estilo Bento Grid premium.
    Arquitectura modular con helpers internos de diseño. Blindaje defensivo total.
    """
    path_adamo    = resolver_ruta_logo("Logo Adamo general")
    path_holdings = resolver_ruta_logo("Logo Holdings")

    pdf = ComplianceMaestroPDF(logo_adamo=path_adamo, logo_holdings=path_holdings)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=18)

    # ── Sanitización centralizada usando .get() para tolerancia a fallos ─────
    s_empresa   = _s(datos_master.get('empresa_principal', ''))
    s_nit       = _s(datos_master.get('nit_principal', ''))
    s_radicado  = _s(datos_master.get('radicado_caso', ''))
    s_direccion = _s(datos_master.get('direccion', ''))
    s_telefono  = _s(datos_master.get('telefono', ''))
    s_jurisdic  = _s(datos_master.get('jurisdiccion', ''))
    s_web       = _s(datos_master.get('sitio_web', ''))
    s_rep_nom   = _s(datos_master.get('rep_legal_nom', ''))
    s_rep_id    = _s(datos_master.get('rep_legal_id', ''))
    s_acc_nom   = _s(datos_master.get('accionista_nom', ''))
    s_acc_id    = _s(datos_master.get('accionista_id', ''))
    s_estado    = _s(datos_master.get('estado_global', ''))
    s_dictamen  = _s(datos_master.get('dictamen_motivo', ''))
    s_rues      = _s(datos_master.get('rues_noticias_raw', ''))
    s_fecha     = _s(datos_master.get('fecha', ''))
    s_analista  = _s(datos_master.get('analista', 'sistema'))

    # ── Helpers de diseño editorial (closures sobre el objeto pdf) ────────────

    def _section_title(numero: int, titulo: str):
        """Encabezado de sección con guía lateral de acento eléctrico."""
        pdf.ln(4)
        y0 = pdf.get_y()
        pdf.set_draw_color(*COLOR_ACCENT)
        pdf.set_line_width(0.8)
        pdf.line(15, y0 + 1, 15, y0 + 5.8)
        # Restablecer draw state para que elementos siguientes no hereden el azul
        pdf.set_draw_color(*COLOR_LINE_TENUE)
        pdf.set_line_width(0.2)
        pdf.set_x(20)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*COLOR_PRIMARY)
        pdf.cell(0, 6.5, f"{numero}. {_s(titulo).upper()}", ln=1)
        pdf.ln(1.5)

    def _bento_open(height: float) -> float:
        """
        Dibuja la tarjeta Bento (fondo Slate 50 + borde Slate 200).
        Devuelve la Y de inicio para que el caller pueda saltar el cursor al final del box.
        """
        y = pdf.get_y()
        pdf.set_fill_color(*COLOR_BG_GRID)
        pdf.set_draw_color(*COLOR_LINE_TENUE)
        pdf.set_line_width(0.2)
        pdf.rect(15, y, 180, height, style="FD")
        pdf.set_y(y + 3)
        return y

    def _kv(label: str, value: str, lw: float, vw: float, last: bool = False):
        """
        Par clave-valor con tipografía diferenciada:
        etiqueta en Slate 500 Bold 7.8pt / valor en Slate 800 Regular 8.3pt.
        last=True aplica ln de fila (cursor baja al inicio de la siguiente).
        """
        pdf.set_font("Helvetica", "B", 7.8)
        pdf.set_text_color(*COLOR_TEXT_MUTED)
        pdf.cell(lw, 5.5, label)
        pdf.set_font("Helvetica", "", 8.3)
        pdf.set_text_color(*COLOR_TEXT_BODY)
        pdf.cell(vw, 5.5, value, ln=1 if last else 0)

    # ── BLOQUE DE IDENTIFICACIÓN PRINCIPAL ───────────────────────────────────
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 9, s_empresa.upper(), ln=1)

    # Meta-strip del expediente: celda con fondo tenue (sin rect() para evitar artefactos)
    pdf.set_fill_color(*COLOR_BG_GRID)
    pdf.set_draw_color(*COLOR_BG_GRID)  # borde invisible (mismo color que relleno)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(0, 7, f"  NIT: {s_nit}   |   Radicado: {s_radicado}   |   Analista: {s_analista}   |   {s_fecha} COT", fill=True, ln=1)
    pdf.ln(4)

    # ── SECCIÓN 1: LOCALIZACIÓN Y CONTACTO ───────────────────────────────────
    _section_title(1, "Información de Localización y Contacto")
    sy = _bento_open(16)
    pdf.set_x(19); _kv("Dirección Fiscal:", s_direccion, 28, 60); _kv("Jurisdicción:", s_jurisdic, 23, 57, last=True)
    pdf.set_x(19); _kv("Teléfono:", s_telefono, 28, 60); _kv("Sitio Web:", s_web, 23, 57, last=True)
    pdf.set_y(sy + 16)
    pdf.ln(4)

    # ── SECCIÓN 2: ESTRUCTURA DIRECTIVA ──────────────────────────────────────
    _section_title(2, "Estructura Directiva y Vinculados Relacionados")
    sy = _bento_open(16)
    pdf.set_x(19); _kv("Representante Legal:", s_rep_nom, 34, 54); _kv("Identificación:", s_rep_id, 25, 55, last=True)
    pdf.set_x(19); _kv("Accionista Principal:", s_acc_nom, 34, 54); _kv("Identificación:", s_acc_id, 25, 55, last=True)
    pdf.set_y(sy + 16)
    pdf.ln(4)

    # ── SECCIÓN 3: EVALUACIÓN DE RIESGO Y CONCLUSIÓN LEGAL (ALTURA DINÁMICA) ─
    _section_title(3, "Evaluación de Riesgo y Conclusión Legal")

    _texto_dictamen = "Sustento Tecnico: " + s_dictamen
    _lineas_est = max(1, -(-len(_texto_dictamen) // 88))   # división techo, ~88 chars/línea a 8pt
    _box_h3 = max(20, 10.5 + _lineas_est * 4.2)

    _sy3 = pdf.get_y()
    pdf.set_fill_color(*COLOR_BG_GRID)
    pdf.set_draw_color(*COLOR_LINE_TENUE)
    pdf.set_line_width(0.2)
    pdf.rect(15, _sy3, 180, _box_h3, style="FD")

    pdf.set_y(_sy3 + 3)
    pdf.set_x(19)
    pdf.set_font("Helvetica", "B", 8); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(35, 5.5, "Dictamen de Aceptación:")
    _d_color = COLOR_SUCCESS if "APROBADO" in s_estado else COLOR_WARNING
    pdf.set_font("Helvetica", "B", 9.5); pdf.set_text_color(*_d_color)
    pdf.cell(0, 5.5, s_estado, ln=1)

    pdf.set_x(19)
    pdf.set_font("Helvetica", "I", 8); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.multi_cell(172, 4.2, _texto_dictamen)

    # Nunca retroceder: si multi_cell superó el rect estimado, avanzamos desde donde quedó
    pdf.set_y(max(pdf.get_y() + 2, _sy3 + _box_h3))
    pdf.ln(4)

    # ── SECCIÓN 4: MATRIZ DE TRAZABILIDAD ────────────────────────────────────
    _section_title(4, "Trazabilidad de Evidencias Indexadas (Cruce Anti-Lavado)")

    _COL = (52, 26, 46, 24, 32)   # nombre, id, rol, radicado, estado — suma exacta = 180mm

    # Cabecera navy + texto blanco (estética SaaS/dashboard contemporáneo)
    pdf.set_font("Helvetica", "B", 7.8)
    pdf.set_fill_color(*COLOR_PRIMARY)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(_COL[0], 6.5, "  Nombre / Sujeto Consultado", border=0, fill=True)
    pdf.cell(_COL[1], 6.5, " Identificación",               border=0, fill=True)
    pdf.cell(_COL[2], 6.5, " Rol de Contraparte",            border=0, fill=True)
    pdf.cell(_COL[3], 6.5, " Radicado",                      border=0, fill=True)
    pdf.cell(_COL[4], 6.5, " Estado Analítico",              border=0, fill=True, ln=1)

    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_draw_color(*COLOR_LINE_TENUE)  # bordes de filas en Slate 200 (reset tras section title)
    lista_entidades = datos_master.get('entidades_processed', datos_master.get('entidades_procesadas', []))

    for _row_idx, elemento in enumerate(lista_entidades):
        # ── Blindaje defensivo: normaliza string plano a dict estructurado ───
        if isinstance(elemento, str):
            ent = {"nombre": elemento, "identificacion": "No Declarada",
                   "rol_interno": "Sujeto de Consulta", "radicado": s_radicado,
                   "resultados": "0", "intensificada": "NO"}
        elif isinstance(elemento, dict):
            ent = elemento
        else:
            continue

        e_nombre = _s(ent.get('nombre', ''))
        e_id     = _s(ent.get('identificacion', ''))
        e_rol    = _s(ent.get('rol_interno', ''))
        e_rad    = _s(ent.get('radicado', ''))
        es_limpio  = ent.get('resultados', '0') == "0" and ent.get('intensificada', 'NO') == "NO"
        estado_txt = "  CONCORDANCIA LIMPIA" if es_limpio else "  REQUIERE AUDITORIA"
        estado_rgb = COLOR_SUCCESS if es_limpio else COLOR_DANGER

        _row_fill = COLOR_BG_GRID if _row_idx % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*_row_fill)
        pdf.set_text_color(*COLOR_TEXT_MAIN)
        pdf.cell(_COL[0], 5.5, "  " + e_nombre[:29], border="B", fill=True)
        pdf.cell(_COL[1], 5.5, "  " + e_id,          border="B", fill=True)
        pdf.cell(_COL[2], 5.5, "  " + e_rol[:25],    border="B", fill=True)
        pdf.cell(_COL[3], 5.5, "  " + e_rad,         border="B", fill=True)
        pdf.set_text_color(*estado_rgb)
        pdf.set_font("Helvetica", "B", 7)
        pdf.cell(_COL[4], 5.5, estado_txt, border="B", fill=True, ln=1)
        pdf.set_font("Helvetica", "", 7.5)

    # ── SECCIÓN 5: HALLAZGOS EN FUENTES ABIERTAS ─────────────────────────────
    pdf.ln(5)
    _section_title(5, "Hallazgos Complementarios en Fuentes Abiertas (RUES / Prensa)")
    pdf.set_font("Helvetica", "", 8.3)
    pdf.set_text_color(*COLOR_TEXT_BODY)
    _contenido_rues = s_rues.strip()
    pdf.multi_cell(0, 4.5, _contenido_rues if _contenido_rues else
        "No se identificaron referencias de prensa desfavorable ni anomalias "
        "mercantiles en los sistemas publicos de verificacion consultados.")

    # ── SELLO DIGITAL INSTITUCIONAL ───────────────────────────────────────────
    pdf.ln(6)
    _seal_y = pdf.get_y()
    pdf.set_fill_color(*COLOR_BG_GRID)
    pdf.set_draw_color(*COLOR_LINE_TENUE)
    pdf.set_line_width(0.2)
    pdf.rect(15, _seal_y, 180, 13, style="FD")
    pdf.set_draw_color(*COLOR_ACCENT)
    pdf.set_line_width(0.6)
    pdf.line(15, _seal_y, 195, _seal_y)
    pdf.set_y(_seal_y + 2)
    pdf.set_x(19)
    pdf.set_font("Helvetica", "", 7.3)
    pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(0, 4, f"Sellado: {s_fecha} COT   |   Responsable: {s_analista}", ln=1)
    pdf.set_x(19)
    pdf.set_font("Helvetica", "B", 7.3)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 4, f"Hash de Autenticidad: ADAMO-RISK-{s_nit.replace('-', '')}-{s_radicado.upper()}", ln=1)

    return pdf.output()


def compilar_expediente_completo(bytes_base: bytes, infolaft_bytes_list: list) -> bytes:
    """Fusiona el expediente con evidencias usando pypdf."""
    writer = pypdf.PdfWriter()
    reader_base = pypdf.PdfReader(io.BytesIO(bytes_base))
    for page in reader_base.pages:
        writer.add_page(page)
    for b in infolaft_bytes_list:
        if not b: continue
        try:
            reader_evi = pypdf.PdfReader(io.BytesIO(b))
            for page in reader_evi.pages:
                writer.add_page(page)
        except Exception:
            continue
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
        "entidades_processed": entidades_lista,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "analista": user.get("username", "sistema")
    }

    def _leer_bytes_uploader(f):
        if f is None: return None
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
    
    if st.session_state.get("v6_just_validated", False):
        st.session_state["v6_just_validated"] = False
    else:
        st.session_state["v6_f_errores"] = []
    if "v6_f_errores" not in st.session_state:
        st.session_state["v6_f_errores"] = []

    # Alerta de identidad corporativa — posicionada al inicio para acción inmediata
    _missing_logos = []
    if not resolver_ruta_logo("Logo Adamo general"): _missing_logos.append("'Logo Adamo general'")
    if not resolver_ruta_logo("Logo Holdings"): _missing_logos.append("'Logo Holdings'")
    if _missing_logos:
        st.markdown(
            f'<div class="ar-alert-strip ar-alert-strip-warning" style="margin-bottom: 18px; font-size: 0.82rem;">'
            f'⚠️ <b>Alerta de Identidad Corporativa:</b> No se detectan los archivos '
            f'{", ".join(_missing_logos)} en <code>app/static/img/logos/</code>. '
            f'El PDF se generará sin logotipos institucionales.</div>',
            unsafe_allow_html=True
        )

    # 🏢 SECCIÓN MODULE 1: Información Corporativa
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
                st.markdown(
                    '<div style="border: 1px dashed var(--border); border-radius: var(--radius-md); '
                    'padding: 18px 14px; margin-top: 10px; text-align: center; opacity: 0.5;">'
                    '<span style="font-size: 1.4rem;">📄</span>'
                    '<p style="margin: 6px 0 0 0; font-size: 0.75rem; color: var(--fg-subtle);">'
                    'Esperando reporte Infolaft de la sociedad</p></div>',
                    unsafe_allow_html=True
                )

    st.markdown('<div class="ar-divider" style="margin: 25px 0;"></div>', unsafe_allow_html=True)

    # 👥 SECCIÓN MODULE 2: Estructura de Administración
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
                st.markdown(
                    '<div style="border: 1px dashed var(--border); border-radius: var(--radius-md); '
                    'padding: 18px 14px; margin-top: 10px; text-align: center; opacity: 0.5;">'
                    '<span style="font-size: 1.4rem;">📄</span>'
                    '<p style="margin: 6px 0 0 0; font-size: 0.75rem; color: var(--fg-subtle);">'
                    'Esperando reporte Infolaft del representante legal</p></div>',
                    unsafe_allow_html=True
                )

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
                st.markdown(
                    '<div class="ar-alert-strip" style="margin-top: 10px; font-size: 0.82rem; '
                    'border-left: 3px solid var(--ai); padding: 10px 14px; '
                    'background: rgba(37, 99, 235, 0.06); border-radius: var(--radius-sm);">'
                    'ℹ️ <b>Modo duplicidad cero activo.</b> El reporte Infolaft del representante '
                    'se duplica automáticamente como evidencia del accionista.</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown("<p style='font-size:0.75rem; font-weight:700; color:var(--ai); text-transform:uppercase; margin-bottom:5px;'>📄 Reporte Infolaft (Accionista)</p>", unsafe_allow_html=True)
                file_accionista = st.file_uploader("Subir PDF Infolaft del Accionista", type=["pdf"], key="v6_pdf_acc", label_visibility="collapsed")
                parsed_accionista = procesar_archivo_pdf(file_accionista)
                if parsed_accionista:
                    parsed_accionista["rol_interno"] = "Accionista / Beneficiario Final"
                    render_resumen_validacion_ui(parsed_accionista)

    st.markdown('<div class="ar-divider" style="margin: 25px 0;"></div>', unsafe_allow_html=True)

    # 🧠 SECCIÓN MODULE 4: Dictamen del Oficial
    with st.container():
        st.markdown('<p class="ar-section-title">4. Dictamen del Oficial y Sustento Técnico</p>', unsafe_allow_html=True)
        st.text_area("Análisis Argumentativo Legal (Enfoque Basado en Riesgo) *", placeholder="Sustente rigurosamente el dictamen técnico de aceptación, rechazo o condicionamiento...", key="v6_dictamen_motivo")
        st.text_area("Notas de Prensa y Validation de Registro Mercantil (RUES)", placeholder="Pegue aquí el bloque de texto con los hallazgos de background check en fuentes abiertas...", key="v6_rues_noticias_raw")

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