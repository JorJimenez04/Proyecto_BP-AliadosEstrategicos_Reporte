# app/utils/pdf_generator.py
import os
import io
import re
import pypdf
from fpdf import FPDF
from PIL import Image as PILImage  # 🚀 Para calcular el Aspect Ratio de las capturas

# ─── PALETA DE COLORES EDITORIAL PREMIUM (FINTECH) ───
COLOR_PRIMARY = (15, 32, 67)       # Azul Marino Profundo
COLOR_ACCENT = (37, 99, 235)       # Azul Eléctrico
COLOR_TEXT_MAIN = (15, 23, 42)     # Slate 900
COLOR_TEXT_BODY = (30, 41, 59)     # Slate 800
COLOR_TEXT_MUTED = (100, 116, 139) # Slate 500
COLOR_BG_GRID = (248, 250, 252)    # Slate 50
COLOR_LINE_TENUE = (226, 232, 240) # Slate 200


class ComplianceMaestroPDF(FPDF):
    """Estructura de diseño institucional con doble logo simétrico para HBPO-Adamo-Paycop."""

    def __init__(self, logo_adamo=None, logo_holdings=None):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.logo_adamo = logo_adamo
        self.logo_holdings = logo_holdings
        self.set_margins(left=15, top=42, right=15)

    def header(self):
        current_x = self.get_x()

        # 📐 ALINEACIÓN SIMÉTRICA OPTIMIZADA CON LOGOS MÁS GRANDES (Y_mid = 16.5mm)
        if self.logo_adamo and os.path.exists(self.logo_adamo):
            self.image(self.logo_adamo, x=15, y=10, h=13)
            
        if self.logo_holdings and os.path.exists(self.logo_holdings):
            self.image(self.logo_holdings, x=163, y=10.5, h=12)

        # Canal central de texto protegido
        self.set_xy(45, 11.5)
        self.set_font("Helvetica", "B", 9.0)
        self.set_text_color(*COLOR_PRIMARY)
        self.cell(115, 4.5, "INFORME DE EVALUACIÓN DE RIESGO Y COMPLIANCE CORPORATIVO", align="C")

        self.set_xy(45, 16.5)
        self.set_font("Helvetica", "", 6.5)
        self.set_text_color(*COLOR_TEXT_MUTED)
        self.cell(115, 4, "VERIFICACIÓN DE ANTECEDENTES, LISTAS DE CONTROL Y VALIDACIÓN DE SEGURIDAD OPERATIVA", align="C")

        # Línea divisoria principal
        self.set_draw_color(*COLOR_PRIMARY)
        self.set_line_width(0.6)
        self.line(15, 30, 195, 30)

        self.set_xy(current_x, 42)

    def footer(self):
        self.set_y(-18)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*COLOR_TEXT_MUTED)
        self.set_draw_color(*COLOR_LINE_TENUE)
        self.line(15, self.get_y() - 2, 195, self.get_y() - 2)
        self.cell(0, 8, f"Certificación de Cumplimiento - Confidencial Interno/Externo - Página {self.page_no()}/{{nb}}", 0, 0, "C")


def parsear_texto_infolaft(texto: str) -> dict:
    """
    Analiza el texto plano extraído del PDF de Infolaft y extrae la información 
    estructurada del vinculado aplicando un algoritmo de aislamiento por marcas de corte.
    """
    res = {
        "nombre": "No detectado",
        "identificacion": "No detectado",
        "radicado": "No detectado",
        "fecha_consulta": "No detectado",
        "resultados": "0",
        "intensificada": "NO"
    }
    
    texto_plano = " ".join(texto.split())

    # Extracción de metadatos con Regex de amplio espectro
    radicado_match = re.search(r"(?:NÚMERO DE CONSULTA|CONSULTA N[ÚU]MERO|RADICADO)[:\s]*\b(\d{5,12})\b", texto_plano, re.IGNORECASE)
    if radicado_match: 
        res["radicado"] = radicado_match.group(1)
    
    id_match = re.search(r"(?:DOCUMENTO DE IDENTIDAD|IDENTIFICACI[ÓO]N|NIT|C[ÉE]DULA)[:\s]*([\d\.\s-]+)", texto_plano, re.IGNORECASE)
    if id_match: 
        cleaned_id = re.sub(r"[^\d-]", "", id_match.group(1).strip())
        if cleaned_id:
            res["identificacion"] = cleaned_id

    fecha_match = re.search(r"(?:FECHA Y HORA DE CONSULTA|FECHA CONSULTA)[:\s]*([\d/]+ [\d:]+(?:\s*(?:AM|PM))?)", texto_plano, re.IGNORECASE)
    if fecha_match: 
        res["fecha_consulta"] = fecha_match.group(1).strip()

    resultados_match = re.search(r"(?:RESUMEN DE RESULTADOS|COINCIDENCIAS|RESULTADOS)[:\s]*(\d+)", texto_plano, re.IGNORECASE)
    if resultados_match: 
        res["resultados"] = resultados_match.group(1)

    gafi_match = re.search(r"(?:RIESGO GAFI|MONITOREO INTENSIFICADO)\??[:\s]*(SI|NO)", texto_plano, re.IGNORECASE)
    if gafi_match: 
        res["intensificada"] = gafi_match.group(1).upper()

    # 🚀 NUEVO: Localización física del candidato con escaneo prospectivo multilínea
    lines = [line.strip() for line in texto.split("\n") if line.strip()]
    nombre_candidato = ""
    
    # Palabras de control administrativo que nunca pueden componer un nombre real
    palabras_prohibidas = [
        "DOCUMENTO", "IDENTIDAD", "NIT", "CÉDULA", "CEDULA", 
        "SU CONSULTA", "DATOS CONSULTADOS", "FECHA", "HORA", 
        "NÚMERO", "NUMERO", "RESULTADOS", "COINCIDENCIAS", 
        "RIESGO", "GAFI", "DEBIDA", "DILIGENCIA", "PEP", "JURISDICCIÓN"
    ]

    for i, line in enumerate(lines):
        line_upper = line.upper()
        if "SU CONSULTA FUE" in line_upper or "DATOS CONSULTADOS" in line_upper:
            # Opción A: Intentar limpiar la misma línea por si el nombre está al lado
            cleaned_same_line = re.sub(r"(?:SU CONSULTA FUE|DATOS CONSULTADOS)[:\s]*", "", line, flags=re.IGNORECASE).strip()
            if cleaned_same_line and len(cleaned_same_line) > 3 and not any(p in cleaned_same_line.upper() for p in palabras_prohibidas):
                nombre_candidato = cleaned_same_line
                break
            
            # Opción B: Escaneo dinámico hacia abajo (hasta 5 líneas físicas)
            for j in range(1, 6):
                if i + j < len(lines):
                    candidate_line = lines[i + j].strip()
                    candidate_upper = candidate_line.upper()
                    
                    # Filtros de exclusión secuenciales
                    if not candidate_line:
                        continue
                    if any(p in candidate_upper for p in palabras_prohibidas):
                        continue
                    if re.match(r"^[\d\.\s-]+$", candidate_line): # Si es solo números (NIT o cédula), se ignora
                        continue
                    
                    # Si superó todos los filtros, ¡este es el nombre real!
                    nombre_candidato = candidate_line
                    break
            break

    # Aislamiento por Marcas de Corte
    if nombre_candidato:
        marcas_de_corte = [
            r"DOCUMENTO\s*DE\s*IDENTIDAD",
            r"REQUIERE\s*DEBIDA",
            r"DEBIDA\s*DILIGENCIA",
            r"POR\s*CONCEPTO\s*PEP",
            r"RIESGO\s*GAFI",
            r"JURISDICCI[ÓO]N\s*DE\s*RIESGO",
            r"FECHA\s*Y\s*HORA",
            r"N[ÚU]MERO\s*DE\s*CONSULTA",
            r"RESUMEN\s*DE\s*RESULTADOS"
        ]
        
        nombre_limpio = nombre_candidato
        for marca in marcas_de_corte:
            nombre_limpio = re.split(marca, nombre_limpio, flags=re.IGNORECASE)[0]
        
        nombre_limpio = re.sub(r"[\s,:\-\.\?¿]+$", "", nombre_limpio).strip()
        nombre_limpio = re.sub(r"^[\s,:\-\.\?¿]+", "", nombre_limpio).strip()
        
        if len(nombre_limpio) >= 3:
            res["nombre"] = nombre_limpio.upper()

    return res


def procesar_archivo_pdf(uploaded_file) -> dict:
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


def resolver_ruta_logo(nombre_base: str) -> str:
    folder = os.path.join("app", "static", "img", "logos")
    if not os.path.exists(folder):
        folder = os.path.join("static", "img", "logos")
        
    if os.path.exists(folder):
        for archivo in os.listdir(folder):
            if archivo.lower().startswith(nombre_base.lower().replace(" ", "_")):
                return os.path.join(folder, archivo)
            elif archivo.lower().startswith(nombre_base.lower()):
                return os.path.join(folder, archivo)
    return None


def _s(texto) -> str:
    if not texto:
        return ""
    return str(texto).replace("\u00bf", "").encode("latin-1", "ignore").decode("latin-1")


def generar_pdf_base(datos_master: dict) -> bytes:
    path_adamo = resolver_ruta_logo("Logo Adamo general")
    path_holdings = resolver_ruta_logo("Logo Holdings")

    pdf = ComplianceMaestroPDF(logo_adamo=path_adamo, logo_holdings=path_holdings)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=18)

    # 🛡️ DECLARACIÓN TEMPRANA DE FUNCIONES AUXILIARES
    def _limitar_texto(texto, max_caracteres=38):
        if len(texto) > max_caracteres:
            return texto[:max_caracteres - 3] + "..."
        return texto

    def render_subseccion_moderna(titulo):
        # 🛡️ Control de desborde preventivo para encabezados de sección
        if pdf.get_y() > 245:
            pdf.add_page()
        pdf.set_text_color(*COLOR_PRIMARY)
        pdf.set_font("Helvetica", "B", 10)
        current_y = pdf.get_y()
        pdf.set_draw_color(*COLOR_ACCENT)
        pdf.set_line_width(0.7)
        pdf.line(15, current_y + 1.2, 15, current_y + 5.2)
        pdf.cell(4, 6, "")
        pdf.cell(0, 6, _s(titulo).upper(), ln=1)
        pdf.ln(2)

    def render_infolaft_snippet(entidad_rol):
        lista = datos_master.get('entidades_processed', datos_master.get('entidades_procesadas', []))
        ent = None
        for item in lista:
            if isinstance(item, dict) and item.get('rol_interno') == entidad_rol:
                ent = item
                break
            elif isinstance(item, str) and entidad_rol == "Representante Legal" and item == datos_master.get('rep_legal_nom'):
                ent = {
                    "nombre": item,
                    "identificacion": datos_master.get('rep_legal_id', 'N/D'),
                    "radicado": datos_master.get('radicado_caso', 'N/D'),
                    "resultados": "0",
                    "intensificada": "NO"
                }
                break
        if not ent:
            return

        # Determinar estatus y paleta de colores semánticos
        es_limpio = ent.get('resultados', '0') == "0" and ent.get('intensificada', 'NO') == "NO"
        if es_limpio:
            badge_bg = (240, 253, 244)
            badge_border = (187, 247, 208)
            badge_text = (21, 128, 61)
            est_texto = "SIN COINCIDENCIAS"
        else:
            badge_bg = (254, 242, 242)
            badge_border = (254, 202, 202)
            badge_text = (185, 28, 28)
            est_texto = "REQUIERE AUDITORÍA INTERNA LAFT"

        # ── Parámetros de alineación síncrona ──
        SNIP_IZQ = 23
        SNIP_DER = 109
        SNIP_W   = 82
        H_LBL    = 3.0
        H_DET    = 3.5
        PAD_TOP  = 3.5
        PAD_BOT  = 3.0

        texto_completo = f"{entidad_rol.upper()}: {ent.get('nombre', 'N/D')}"

        # Cálculo dinámico de líneas requeridas por el nombre
        pdf.set_font("Helvetica", "B", 8.5)
        ancho_texto_medido = pdf.get_string_width(texto_completo)
        lineas_nombre = max(1, int(ancho_texto_medido / SNIP_W) + 1)
        h_nombre = lineas_nombre * 3.8
        h_row_contenido = max(h_nombre, 6.0)

        # Altura Bento de esta tarjeta
        H_SNIP = PAD_TOP + H_LBL + 1.2 + h_row_contenido + 2.0 + 1.5 + H_DET + PAD_BOT

        # 🛡️ CONTROL DE DESBORDE DE TARJETA INDIVIDUAL (Si no cabe en la página, salta de página)
        if pdf.get_y() + H_SNIP > 262:
            pdf.add_page()

        pdf.ln(2.0)
        s_y = pdf.get_y()

        # Dibujar Bento
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(*COLOR_LINE_TENUE)
        pdf.set_line_width(0.2)
        pdf.rect(19, s_y, 172, H_SNIP, style="FD")

        # Ejes Y calculados dinámicamente
        y_lbl = s_y + PAD_TOP
        y_val_bdg = y_lbl + H_LBL + 1.2
        y_div = y_val_bdg + h_row_contenido + 2.0
        y_det = y_div + 1.5

        # Divisor horizontal interno
        pdf.set_draw_color(*COLOR_LINE_TENUE)
        pdf.set_line_width(0.15)
        pdf.line(SNIP_IZQ, y_div, 187, y_div)

        # Columna Izquierda: Nombre
        pdf.set_xy(SNIP_IZQ, y_lbl)
        pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
        pdf.cell(SNIP_W, H_LBL, "VINCULADO / ROL EVALUADO")
        
        pdf.set_xy(SNIP_IZQ, y_val_bdg)
        pdf.set_font("Helvetica", "B", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
        pdf.multi_cell(SNIP_W, 3.8, _s(texto_completo))

        # Columna Derecha: Badge
        pdf.set_xy(SNIP_DER, y_lbl)
        pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
        pdf.cell(74, H_LBL, "ESTATUS DE EVALUACIÓN LAFT")
        
        pdf.set_fill_color(*badge_bg)
        pdf.set_draw_color(*badge_border)
        pdf.set_line_width(0.15)
        pdf.rect(SNIP_DER, y_val_bdg, 74, 6.0, style="FD")
        
        pdf.set_xy(SNIP_DER + 3, y_val_bdg + 1.0)
        pdf.set_font("Helvetica", "B", 7.0); pdf.set_text_color(*badge_text)
        pdf.cell(68, 4.2, est_texto)

        # Detalle técnico
        pdf.set_xy(SNIP_IZQ, y_det)
        pdf.set_font("Helvetica", "", 7.0); pdf.set_text_color(*COLOR_TEXT_MUTED)
        detalle_str = f"No. Registro Consulta: {ent.get('radicado', 'N/A')}   |   Coincidencias Halladas: {ent.get('resultados', '0')}   |   Monitoreo Intensificado (GAFI): {ent.get('intensificada', 'NO')}"
        pdf.cell(164, H_DET, _s(detalle_str))

        pdf.set_y(s_y + H_SNIP)


    # ─── SANITIZACIÓN ESTRUCTURAL DE DATOS ───
    s_empresa   = _s(datos_master['empresa_principal'])
    s_nit       = _s(datos_master['nit_principal'])
    s_radicado  = _s(datos_master['radicado_caso'])
    s_direccion = _s(datos_master['direccion'])
    s_telefono  = _s(datos_master['telefono'])
    s_correo    = _s(datos_master.get('correo_contacto', 'No Registrado'))
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

    # ─── ENCABEZADO DE COMPAÑÍA ESTILO DASHBOARD ───
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 8, s_empresa.upper(), ln=1)

    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(0, 4, f"Identificación Comercial: {s_nit}   |   ID Expediente: {s_radicado}", ln=1)
    pdf.ln(6)


    # 🗂️ ─── SECCIÓN 1: IDENTIFICACIÓN CORPORATIVA Y DE CONTACTO ───
    render_subseccion_moderna("1. Identificación de la Entidad Evaluada")

    # Parámetros de la grilla adaptada a 4 filas
    COL_IZQ_X   = 19
    COL_DER_X   = 109
    ANCHO_COL   = 82
    H_LABEL     = 3.0
    H_VALUE     = 4.2
    H_GAP       = 2.5
    PADDING_TOP = 3.5
    PADDING_BOT = 3.0

    # Pre-cálculo de alturas dinámicas
    pdf.set_font("Helvetica", "", 8.5)
    lineas_direccion = max(1, int(pdf.get_string_width(s_direccion) / ANCHO_COL) + 1)
    h_row1 = H_LABEL + (lineas_direccion * H_VALUE)
    h_row2 = H_LABEL + H_VALUE
    h_row3 = H_LABEL + H_VALUE
    h_row4 = H_LABEL + H_VALUE
    altura_bento_dinamica = PADDING_TOP + h_row1 + H_GAP + h_row2 + H_GAP + h_row3 + H_GAP + h_row4 + PADDING_BOT

    # 🛡️ CONTROL DE DESBORDE DE BENTO SECCIÓN 1
    if pdf.get_y() + altura_bento_dinamica > 262:
        pdf.add_page()

    start_y = pdf.get_y()

    # Contenedor Bento principal
    pdf.set_fill_color(*COLOR_BG_GRID)
    pdf.set_draw_color(*COLOR_LINE_TENUE)
    pdf.set_line_width(0.2)
    pdf.rect(15, start_y, 180, altura_bento_dinamica, style="FD")

    # Ejes Y calculados
    y_row1 = start_y + PADDING_TOP
    y_row2 = y_row1 + h_row1 + H_GAP
    y_row3 = y_row2 + h_row2 + H_GAP
    y_row4 = y_row3 + h_row3 + H_GAP

    # Divisores horizontales
    pdf.set_draw_color(*COLOR_LINE_TENUE)
    pdf.set_line_width(0.15)
    pdf.line(COL_IZQ_X, y_row2 - H_GAP / 2, 191, y_row2 - H_GAP / 2)
    pdf.line(COL_IZQ_X, y_row3 - H_GAP / 2, 191, y_row3 - H_GAP / 2)
    pdf.line(COL_IZQ_X, y_row4 - H_GAP / 2, 191, y_row4 - H_GAP / 2)

    # Fila 1
    pdf.set_xy(COL_IZQ_X, y_row1)
    pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(ANCHO_COL, H_LABEL, "DIRECCIÓN FISCAL", ln=1)
    pdf.set_x(COL_IZQ_X)
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.multi_cell(ANCHO_COL, H_VALUE, s_direccion)

    pdf.set_xy(COL_DER_X, y_row1)
    pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(ANCHO_COL, H_LABEL, "JURISDICCIÓN COMERCIAL", ln=1)
    pdf.set_xy(COL_DER_X, y_row1 + H_LABEL)
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.cell(ANCHO_COL, H_VALUE, _limitar_texto(s_jurisdic, max_caracteres=38))

    # Fila 2
    pdf.set_xy(COL_IZQ_X, y_row2)
    pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(ANCHO_COL, H_LABEL, "REPRESENTANTE LEGAL", ln=1)
    pdf.set_xy(COL_IZQ_X, y_row2 + H_LABEL)
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.cell(ANCHO_COL, H_VALUE, _limitar_texto(s_rep_nom, max_caracteres=38))

    pdf.set_xy(COL_DER_X, y_row2)
    pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(ANCHO_COL, H_LABEL, "SOCIO O ACCIONISTA PRINCIPAL", ln=1)
    pdf.set_xy(COL_DER_X, y_row2 + H_LABEL)
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.cell(ANCHO_COL, H_VALUE, _limitar_texto(s_acc_nom, max_caracteres=38))

    # Fila 3
    pdf.set_xy(COL_IZQ_X, y_row3)
    pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(ANCHO_COL, H_LABEL, "TELÉFONO DE CONTACTO", ln=1)
    pdf.set_xy(COL_IZQ_X, y_row3 + H_LABEL)
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.cell(ANCHO_COL, H_VALUE, s_telefono)

    pdf.set_xy(COL_DER_X, y_row3)
    pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(ANCHO_COL, H_LABEL, "CORREO ELECTRÓNICO DE CONTACTO", ln=1)
    pdf.set_xy(COL_DER_X, y_row3 + H_LABEL)
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.cell(ANCHO_COL, H_VALUE, _limitar_texto(s_correo, max_caracteres=38))

    # Fila 4
    pdf.set_xy(COL_IZQ_X, y_row4)
    pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(ANCHO_COL, H_LABEL, "CANAL DIGITAL / SITIO WEB", ln=1)
    pdf.set_xy(COL_IZQ_X, y_row4 + H_LABEL)
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.cell(ANCHO_COL, H_VALUE, _limitar_texto(s_web, max_caracteres=38))

    pdf.set_xy(COL_DER_X, y_row4)
    pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(ANCHO_COL, H_LABEL, "IDENTIFICADOR ÚNICO DE EXPEDIENTE", ln=1)
    pdf.set_xy(COL_DER_X, y_row4 + H_LABEL)
    pdf.set_font("Helvetica", "B", 8.5); pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(ANCHO_COL, H_VALUE, _limitar_texto(s_radicado, max_caracteres=38))

    pdf.set_y(start_y + altura_bento_dinamica)
    pdf.ln(6)


    # 🗂️ ─── SECCIÓN 2: TRAZABILIDAD Y SCREENING LAFT (VINCULADOS) ───
    render_subseccion_moderna("2. Análisis de Screening y Coincidencia en Listas de Control (LAFT)")
    
    render_infolaft_snippet("Empresa Principal")
    render_infolaft_snippet("Representante Legal")
    render_infolaft_snippet("Accionista / Beneficiario Final")
    pdf.ln(6)


    # 🗂️ ─── SECCIÓN 3: CONCEPTO TÉCNICO Y DECLARACIÓN DE CUMPLIMIENTO ───
    render_subseccion_moderna("3. Concepto Técnico de Cumplimiento")

    es_aprobado    = "APROBADO" in s_estado
    estado_str     = "APROBADO  SIN COINCIDENCIAS" if es_aprobado else "REVISIÓN ADICIONAL REQUERIDA"
    categoria_str  = "RIESGO BAJO" if es_aprobado else "RIESGO INTENSIFICADO"
    
    if es_aprobado:
        badge_bg = (240, 253, 244)
        badge_border = (187, 247, 208)
        badge_text = (21, 128, 61)
    else:
        badge_bg = (254, 243, 199)
        badge_border = (253, 230, 138)
        badge_text = (180, 83, 9)

    S3_IZQ   = 19
    S3_DER   = 109
    S3_W     = 82
    S3_H_LBL = 3.0
    S3_H_BDG = 6.0
    S3_GAP   = 5.5
    S3_PAD_T = 4.5
    S3_PAD_B = 4.5

    pdf.set_font("Helvetica", "I", 8)
    saltos_dict  = s_dictamen.count('\n')
    lineas_dict  = max(1, int(pdf.get_string_width(s_dictamen.replace('\n', ' ')) / 168) + 1) + saltos_dict
    h_dictamen   = lineas_dict * 4.2
    
    # Altura del Bento de Sección 3
    altura_bento_s3 = S3_PAD_T + S3_H_LBL + 1.2 + S3_H_BDG + S3_GAP + S3_H_LBL + 1.2 + h_dictamen + S3_PAD_B

    # 🛡️ CONTROL DE DESBORDE DE BENTO SECCIÓN 3
    if pdf.get_y() + altura_bento_s3 > 262:
        pdf.add_page()

    start_y = pdf.get_y()

    pdf.set_fill_color(*COLOR_BG_GRID)
    pdf.set_draw_color(*COLOR_LINE_TENUE)
    pdf.set_line_width(0.2)
    pdf.rect(15, start_y, 180, altura_bento_s3, style="FD")

    y_r1_lbl = start_y + S3_PAD_T
    y_r1_bdg = y_r1_lbl + S3_H_LBL + 1.2
    y_divisor = y_r1_bdg + S3_H_BDG + (S3_GAP / 2.0)
    y_r2_lbl = y_divisor + (S3_GAP / 2.0)
    y_r2_val = y_r2_lbl + S3_H_LBL + 1.2

    # Divisor horizontal
    pdf.set_draw_color(*COLOR_LINE_TENUE)
    pdf.set_line_width(0.15)
    pdf.line(S3_IZQ, y_divisor, 191, y_divisor)

    # Fila 1 - Badges
    pdf.set_xy(S3_IZQ, y_r1_lbl)
    pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(S3_W, S3_H_LBL, "RESULTADO FORMAL DE EVALUACIÓN LAFT")
    
    pdf.set_fill_color(*badge_bg)
    pdf.set_draw_color(*badge_border)
    pdf.rect(S3_IZQ, y_r1_bdg, 74, S3_H_BDG, style="FD")
    
    pdf.set_xy(S3_IZQ + 3, y_r1_bdg + 1.0)
    pdf.set_font("Helvetica", "B", 7.5); pdf.set_text_color(*badge_text)
    pdf.cell(68, 4.2, estado_str)

    pdf.set_xy(S3_DER, y_r1_lbl)
    pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(S3_W, S3_H_LBL, "CATEGORÍA DE RIESGO FINAL")
    
    pdf.set_fill_color(*badge_bg)
    pdf.set_draw_color(*badge_border)
    pdf.rect(S3_DER, y_r1_bdg, 74, S3_H_BDG, style="FD")
    
    pdf.set_xy(S3_DER + 3, y_r1_bdg + 1.0)
    pdf.set_font("Helvetica", "B", 7.5); pdf.set_text_color(*badge_text)
    pdf.cell(68, 4.2, categoria_str)

    # Fila 2 - Dictamen
    pdf.set_xy(S3_IZQ, y_r2_lbl)
    pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(172, S3_H_LBL, "SUSTENTO TÉCNICO DEL OFICIAL DE CUMPLIMIENTO", ln=1)
    
    pdf.set_xy(S3_IZQ, y_r2_val)
    pdf.set_font("Helvetica", "I", 8); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.multi_cell(172, 4.2, s_dictamen)

    pdf.set_y(start_y + altura_bento_s3)
    pdf.ln(6)


    # 🗂️ ─── SECCIÓN 4: ANÁLISIS DE FUENTES ABIERTAS COMPLEMENTARIO ───
    render_subseccion_moderna("4. Análisis de Contexto y Registro Público")

    contenido_rues = s_rues.strip() if s_rues.strip() else \
        "El análisis de screening y medios adversos concluyó sin hallazgos de referencias de prensa negativa, sanciones administrativas o anomalías mercantiles en las fuentes públicas consultadas."

    pdf.set_font("Helvetica", "", 8.5)
    saltos_rues  = contenido_rues.count('\n')
    lineas_rues  = max(1, int(pdf.get_string_width(contenido_rues.replace('\n', ' ')) / 172) + 1) + saltos_rues
    h_rues       = lineas_rues * 4.2
    
    altura_bento_rues = 4.5 + 3.0 + 1.5 + h_rues + 4.5

    # 🛡️ CONTROL DE DESBORDE DE BENTO SECCIÓN 4 (¡Evita el desborde de Image 2!)
    if pdf.get_y() + altura_bento_rues > 262:
        pdf.add_page()

    start_y = pdf.get_y()

    # Dibujo del contenedor Bento principal
    pdf.set_fill_color(*COLOR_BG_GRID)
    pdf.set_draw_color(*COLOR_LINE_TENUE)
    pdf.set_line_width(0.2)
    pdf.rect(15, start_y, 180, altura_bento_rues, style="FD")

    pdf.set_xy(19, start_y + 4.5)
    pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(172, 3.0, "ANÁLISIS DE ADVERSE MEDIA Y VALIDACIÓN EN REGISTRO MERCANTIL", ln=1)
    
    pdf.set_xy(19, start_y + 4.5 + 3.0 + 1.5)
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.multi_cell(172, 4.2, contenido_rues)

    pdf.set_y(start_y + altura_bento_rues)

    # Sello de seguridad
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(0, 3.5, f"Estampa de Tiempo de Evaluación: {s_fecha} COT", ln=1)
    pdf.cell(0, 3.5, f"Código de Verificación del Reporte: HBPO-COMPLIANCE-{s_nit.replace('-', '')}-{s_radicado.upper()}", ln=1)


    # 🗂️ ─── SECCIÓN DE ANEXOS: REGISTRO DE EVIDENCIAS DIGITALES (IMÁGENES) ───
    imagenes_evidencia = datos_master.get("evidencias_imagenes", [])
    
    if imagenes_evidencia:
        pdf.add_page()  # Abrir página limpia para el anexo
        
        pdf.set_text_color(*COLOR_PRIMARY)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "ANEXO: REGISTRO DE EVIDENCIAS DIGITALES", ln=1)
        
        pdf.set_draw_color(*COLOR_PRIMARY)
        pdf.set_line_width(0.4)
        pdf.line(15, pdf.get_y() + 1, 195, pdf.get_y() + 1)
        pdf.ln(6)
        
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*COLOR_TEXT_BODY)
        pdf.multi_cell(0, 4.2, "Como respaldo del proceso de debida diligencia y validación en fuentes abiertas, se adjuntan de manera íntegra las capturas de pantalla tomadas de los portales de verificación pública:")
        pdf.ln(4)

        import tempfile
        
        for idx, img_bytes in enumerate(imagenes_evidencia):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_img:
                temp_img.write(img_bytes)
                temp_path = temp_img.name
            
            try:
                # 🚀 LECTURA DINÁMICA DEL ASPECT RATIO DE LA IMAGEN (¡Para solucionar Image 1!)
                with PILImage.open(temp_path) as img:
                    img_w, img_h = img.size
                
                aspect = img_h / img_w  # Proporción de la imagen (alto / ancho)
                
                # Definir límites de la caja contenedora de la imagen
                max_width = 160.0
                max_height = 145.0  # Límite vertical estricto para evitar golpear el footer
                
                # Escalado proporcional de la imagen
                render_w = max_width
                render_h = max_width * aspect
                
                if render_h > max_height:
                    render_h = max_height
                    render_w = max_height / aspect
                
                # Centrado horizontal exacto dentro de los márgenes de 15mm y 195mm
                pos_x = 15.0 + (180.0 - render_w) / 2.0
                
                # 🛡️ CONTROL DE DESBORDE DE IMAGEN (Si no cabe verticalmente en la página actual, salta)
                espacio_disponible = 270.0 - pdf.get_y()  # Límite seguro antes del pie de página (270mm)
                if (render_h + 10) > espacio_disponible:
                    pdf.add_page()
                
                # Etiqueta de identificación
                pdf.set_font("Helvetica", "B", 8.0)
                pdf.set_text_color(*COLOR_TEXT_MUTED)
                pdf.cell(0, 5, f"EVIDENCIA DIGITAL NO. {idx + 1} - SOPORTE DE CONSULTA", ln=1)
                pdf.ln(2)
                
                # Renderizado simétrico escalado
                pdf.image(temp_path, x=pos_x, y=pdf.get_y(), w=render_w, h=render_h)
                
                # Cursor Y avanza exactamente lo que mide la imagen + separación
                pdf.set_y(pdf.get_y() + render_h + 8)
                
            except Exception as e:
                pdf.set_font("Helvetica", "I", 8.0)
                pdf.set_text_color(220, 38, 38)
                pdf.cell(0, 5, f"[Error al compilar la evidencia {idx + 1}: Formato no soportado]", ln=1)
                pdf.ln(4)
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

    # Retorno seguro
    out = pdf.output()
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    return str(out).encode('latin-1')


def compilar_expediente_completo(bytes_base: bytes, infolaft_bytes_list: list) -> bytes:
    """Fusiona el expediente de salida con las evidencias PDF de Infolaft."""
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