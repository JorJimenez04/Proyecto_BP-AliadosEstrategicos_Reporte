# app/utils/pdf_generator.py
import os
import io
import re
import pypdf
from fpdf import FPDF

# ─── PALETA DE COLORES EDITORIAL PREMIUM (FINTECH) ───
COLOR_PRIMARY = (15, 32, 67)       # Azul Marino Profundo (Confianza e Institucionalidad)
COLOR_ACCENT = (37, 99, 235)       # Azul Eléctrico (Enfoque Tecnológico Fintech)
COLOR_TEXT_MAIN = (15, 23, 42)     # Slate 900 (Lectura limpia de títulos)
COLOR_TEXT_BODY = (30, 41, 59)     # Slate 800 (Cuerpo técnico de alta legibilidad)
COLOR_TEXT_MUTED = (100, 116, 139) # Slate 500 (Etiquetas secundarias de control)
COLOR_BG_GRID = (248, 250, 252)    # Slate 50 (Fondo bento homogéneo de baja densidad)
COLOR_LINE_TENUE = (226, 232, 240) # Slate 200 (Bordes sutiles y limpios)


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
        
        # Logo Izquierdo (Adamo / Paycop) -> h=13mm, y=10mm (Midpoint = 16.5mm)
        if self.logo_adamo and os.path.exists(self.logo_adamo):
            self.image(self.logo_adamo, x=15, y=10, h=13)
            
        # Logo Derecho (Holdings BPO / HBPO) -> h=12mm, y=10.5mm (Midpoint = 16.5mm)
        if self.logo_holdings and os.path.exists(self.logo_holdings):
            self.image(self.logo_holdings, x=163, y=10.5, h=12)

        # Canal central de texto protegido (Y_mid = 16.5mm)
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
        self.cell(0, 8, f"Certificación de Cumplimiento - Confidencial - Página {self.page_no()}/{{nb}}", 0, 0, "C")


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
    path_adamo = resolver_ruta_logo("Logo Adamo general")
    path_holdings = resolver_ruta_logo("Logo Holdings")

    pdf = ComplianceMaestroPDF(logo_adamo=path_adamo, logo_holdings=path_holdings)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=18)

    # 🛡️ 1. DECLARACIÓN TEMPRANA DE FUNCIONES AUXILIARES
    def _limitar_texto(texto, max_caracteres=38):
        """Previene colisiones horizontales de grillas cortando strings largos."""
        if len(texto) > max_caracteres:
            return texto[:max_caracteres - 3] + "..."
        return texto

    def render_subseccion_moderna(titulo):
        """Genera un encabezado de módulo premium con indicador lateral."""
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
        """Row-by-Row Grid: labels 6.5pt bold muted + values 8.5pt, col izq/der sincronizadas."""
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

        pdf.ln(1.5)
        s_y = pdf.get_y()

        es_limpio  = ent.get('resultados', '0') == "0" and ent.get('intensificada', 'NO') == "NO"
        est_texto  = "SIN COINCIDENCIAS" if es_limpio else "REQUIERE AUDITORÍA INTERNA LAFT"
        est_color  = (22, 163, 74) if es_limpio else (220, 38, 38)

        # ── Constantes de la mini-grilla ──
        SNIP_IZQ = 23
        SNIP_DER = 109
        SNIP_W   = 78
        H_LBL    = 2.5
        H_VAL    = 4.2
        H_DET    = 3.2
        PAD_TOP  = 2.0
        PAD_BOT  = 1.5
        H_SNIP   = PAD_TOP + H_LBL + H_VAL + 1.5 + H_DET + PAD_BOT

        # Bento blanco
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(*COLOR_LINE_TENUE)
        pdf.set_line_width(0.15)
        pdf.rect(19, s_y, 172, H_SNIP, style="FD")

        y_lbl = s_y + PAD_TOP
        y_val = y_lbl + H_LBL
        y_div = y_val + H_VAL + 0.75
        y_det = y_val + H_VAL + 1.5

        # Divisor sutil entre fila principal y fila detalle
        pdf.set_draw_color(*COLOR_LINE_TENUE)
        pdf.set_line_width(0.15)
        pdf.line(SNIP_IZQ, y_div, 187, y_div)

        # Izq: ROL EVALUADO
        pdf.set_xy(SNIP_IZQ, y_lbl)
        pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
        pdf.cell(SNIP_W, H_LBL, "ROL EVALUADO")
        pdf.set_xy(SNIP_IZQ, y_val)
        pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
        pdf.cell(SNIP_W, H_VAL, _limitar_texto(entidad_rol, max_caracteres=34))

        # Der: ESTATUS LAFT
        pdf.set_xy(SNIP_DER, y_lbl)
        pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
        pdf.cell(SNIP_W, H_LBL, "ESTATUS LAFT")
        pdf.set_xy(SNIP_DER, y_val)
        pdf.set_font("Helvetica", "B", 8.5); pdf.set_text_color(*est_color)
        pdf.cell(SNIP_W, H_VAL, _limitar_texto(est_texto, max_caracteres=34))

        # Fila detalle (ancho completo): datos de registro
        pdf.set_xy(SNIP_IZQ, y_det)
        pdf.set_font("Helvetica", "", 7.0); pdf.set_text_color(*COLOR_TEXT_MUTED)
        pdf.cell(0, H_DET, f"No. Registro: {ent.get('radicado', 'N/A')}   |   Coincidencias: {ent.get('resultados', '0')}   |   Riesgo GAFI: {ent.get('intensificada', 'NO')}")

        pdf.set_y(s_y + H_SNIP)


    # ─── 2. SANITIZACIÓN ESTRUCTURAL DE DATOS ───
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

    # ─── 3. ENCABEZADO DE COMPAÑÍA ESTILO DASHBOARD ───
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 8, s_empresa.upper(), ln=1)

    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(0, 4, f"Identificación Comercial: {s_nit}   |   ID Expediente: {s_radicado}", ln=1)
    pdf.ln(6)


    # 🗂️ ─── SECCIÓN 1: IDENTIFICACIÓN CORPORATIVA Y DE CONTACTO ───
    render_subseccion_moderna("1. Identificación de la Entidad Evaluada")

    start_y = pdf.get_y()

    # ── Constantes de la grilla sincronizada ──
    COL_IZQ_X   = 19    # Margen interno izquierdo (4mm desde el borde del bento)
    COL_DER_X   = 109   # 19 + 82col + 8mm canaleta = 109 → termina en 191mm (4mm del borde derecho)
    ANCHO_COL   = 82    # Ambas columnas simétricas
    H_LABEL     = 3.0   # Altura etiqueta (Helvetica Bold 6.5pt)
    H_VALUE     = 4.2   # Altura valor (Helvetica 8.5pt)
    H_GAP       = 2.5   # Respiración entre filas
    PADDING_TOP = 3.5
    PADDING_BOT = 3.0

    # ── Pre-cálculo de h_row1 para que ambas columnas compartan el mismo eje Y ──
    pdf.set_font("Helvetica", "", 8.5)
    lineas_direccion = max(1, int(pdf.get_string_width(s_direccion) / ANCHO_COL) + 1)
    h_row1 = H_LABEL + (lineas_direccion * H_VALUE)
    h_row2 = H_LABEL + H_VALUE
    h_row3 = H_LABEL + H_VALUE
    altura_bento_dinamica = PADDING_TOP + h_row1 + H_GAP + h_row2 + H_GAP + h_row3 + PADDING_BOT

    # ── Contenedor Bento dinámico ──
    pdf.set_fill_color(*COLOR_BG_GRID)
    pdf.set_draw_color(*COLOR_LINE_TENUE)
    pdf.set_line_width(0.2)
    pdf.rect(15, start_y, 180, altura_bento_dinamica, style="FD")

    # ── Ejes Y fijos de cada fila (determinísticos, independientes del flujo) ──
    y_row1 = start_y + PADDING_TOP
    y_row2 = y_row1 + h_row1 + H_GAP
    y_row3 = y_row2 + h_row2 + H_GAP

    # ── Divisores horizontales sutiles entre filas ──
    pdf.set_draw_color(*COLOR_LINE_TENUE)
    pdf.set_line_width(0.15)
    pdf.line(COL_IZQ_X, y_row2 - H_GAP / 2, 191, y_row2 - H_GAP / 2)
    pdf.line(COL_IZQ_X, y_row3 - H_GAP / 2, 191, y_row3 - H_GAP / 2)

    # ═══════════════════════════════════════════════════════════════
    # FILA 1 — DIRECCIÓN FISCAL (izq)  |  JURISDICCIÓN COMERCIAL (der)
    # ═══════════════════════════════════════════════════════════════

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

    # ═══════════════════════════════════════════════════════════════
    # FILA 2 — REPRESENTANTE LEGAL (izq)  |  SOCIO/ACCIONISTA (der)
    # ═══════════════════════════════════════════════════════════════

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

    # ═══════════════════════════════════════════════════════════════
    # FILA 3 — TELÉFONO DE CONTACTO (izq)  |  CANAL DIGITAL (der)
    # ═══════════════════════════════════════════════════════════════

    pdf.set_xy(COL_IZQ_X, y_row3)
    pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(ANCHO_COL, H_LABEL, "TELÉFONO DE CONTACTO", ln=1)
    pdf.set_xy(COL_IZQ_X, y_row3 + H_LABEL)
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.cell(ANCHO_COL, H_VALUE, s_telefono)

    pdf.set_xy(COL_DER_X, y_row3)
    pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(ANCHO_COL, H_LABEL, "CANAL DIGITAL / SITIO WEB", ln=1)
    pdf.set_xy(COL_DER_X, y_row3 + H_LABEL)
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.cell(ANCHO_COL, H_VALUE, _limitar_texto(s_web, max_caracteres=38))

    # ── Restaurar cursor al final del bento para no solapar la siguiente sección ──
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

    start_y = pdf.get_y()

    es_aprobado    = "APROBADO" in s_estado
    estado_str     = "APROBADO  SIN COINCIDENCIAS" if es_aprobado else "REVISIÓN ADICIONAL REQUERIDA"
    categoria_str  = "RIESGO BAJO" if es_aprobado else "RIESGO INTENSIFICADO"
    
    # Colores semánticos
    if es_aprobado:
        badge_bg = (240, 253, 244)      # Emerald 50
        badge_border = (187, 247, 208)  # Emerald 200
        badge_text = (21, 128, 61)      # Emerald 700
    else:
        badge_bg = (254, 243, 199)      # Amber 50
        badge_border = (253, 230, 138)  # Amber 200
        badge_text = (180, 83, 9)       # Amber 700

    # Coordenadas y dimensiones de la grilla
    S3_IZQ   = 19
    S3_DER   = 109
    S3_W     = 82
    S3_H_LBL = 3.0      # Altura de las etiquetas grises
    S3_H_BDG = 6.0      # Altura del Badge (Incrementado para dar aire interno)
    S3_GAP   = 5.5      # Espacio de separación entre fila 1 y fila 2 (Incrementado)
    S3_PAD_T = 4.5      # Padding superior del Bento
    S3_PAD_B = 4.5      # Padding inferior del Bento

    # Pre-cálculo dinámico de líneas del dictamen (Sustento Técnico)
    pdf.set_font("Helvetica", "I", 8)
    saltos_dict  = s_dictamen.count('\n')
    lineas_dict  = max(1, int(pdf.get_string_width(s_dictamen.replace('\n', ' ')) / 168) + 1) + saltos_dict
    h_dictamen   = lineas_dict * 4.2

    # Distribución determinista de ejes Y para evitar colisiones
    y_r1_lbl = start_y + S3_PAD_T
    y_r1_bdg = y_r1_lbl + S3_H_LBL + 1.2
    
    # El divisor se ubica exactamente en la mitad del GAP de respiración
    y_divisor = y_r1_bdg + S3_H_BDG + (S3_GAP / 2.0)
    
    y_r2_lbl = y_divisor + (S3_GAP / 2.0)
    y_r2_val = y_r2_lbl + S3_H_LBL + 1.2

    # Altura total dinámica del Bento
    altura_bento_s3 = (y_r2_val + h_dictamen + S3_PAD_B) - start_y

    # Dibujo del contenedor Bento principal
    pdf.set_fill_color(*COLOR_BG_GRID)
    pdf.set_draw_color(*COLOR_LINE_TENUE)
    pdf.set_line_width(0.2)
    pdf.rect(15, start_y, 180, altura_bento_s3, style="FD")

    # Dibujo del divisor sutil horizontal
    pdf.set_draw_color(*COLOR_LINE_TENUE)
    pdf.set_line_width(0.15)
    pdf.line(S3_IZQ, y_divisor, 191, y_divisor)

    # ═══════════════════════════════════════════════════════════════
    # FILA 1 — Resultado (izq) | Categoría (der) con Status Badges
    # ═══════════════════════════════════════════════════════════════
    
    # ── Columna Izquierda: Resultado LAFT ──
    pdf.set_xy(S3_IZQ, y_r1_lbl)
    pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(S3_W, S3_H_LBL, "RESULTADO FORMAL DE EVALUACIÓN LAFT")
    
    # Placa física Badge Izquierdo
    pdf.set_fill_color(*badge_bg)
    pdf.set_draw_color(*badge_border)
    pdf.rect(S3_IZQ, y_r1_bdg, 74, S3_H_BDG, style="FD")
    
    # Texto centrado verticalmente dentro del Badge
    pdf.set_xy(S3_IZQ + 3, y_r1_bdg + 1.0)
    pdf.set_font("Helvetica", "B", 7.5); pdf.set_text_color(*badge_text)
    pdf.cell(68, 4.2, estado_str)

    # ── Columna Derecha: Categoría de Riesgo ──
    pdf.set_xy(S3_DER, y_r1_lbl)
    pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(S3_W, S3_H_LBL, "CATEGORÍA DE RIESGO FINAL")
    
    # Placa física Badge Derecho
    pdf.set_fill_color(*badge_bg)
    pdf.set_draw_color(*badge_border)
    pdf.rect(S3_DER, y_r1_bdg, 74, S3_H_BDG, style="FD")
    
    # Texto centrado verticalmente dentro del Badge
    pdf.set_xy(S3_DER + 3, y_r1_bdg + 1.0)
    pdf.set_font("Helvetica", "B", 7.5); pdf.set_text_color(*badge_text)
    pdf.cell(68, 4.2, categoria_str)

    # ═══════════════════════════════════════════════════════════════
    # FILA 2 — Sustento Técnico (Ancho Completo)
    # ═══════════════════════════════════════════════════════════════
    
    pdf.set_xy(S3_IZQ, y_r2_lbl)
    pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(172, S3_H_LBL, "SUSTENTO TÉCNICO DEL OFICIAL DE CUMPLIMIENTO", ln=1)
    
    pdf.set_xy(S3_IZQ, y_r2_val)
    pdf.set_font("Helvetica", "I", 8); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.multi_cell(172, 4.2, s_dictamen)

    # Restaurar cursor de salida
    pdf.set_y(start_y + altura_bento_s3)
    pdf.ln(6)


    # 🗂️ ─── SECCIÓN 4: ANÁLISIS DE FUENTES ABIERTAS COMPLEMENTARIO ───
    # Acortamos el título principal para evitar el desborde en el extremo derecho
    render_subseccion_moderna("4. Análisis de Contexto y Registro Público")

    start_y = pdf.get_y()

    contenido_rues = s_rues.strip() if s_rues.strip() else \
        "El análisis de screening y medios adversos concluyó sin hallazgos de referencias de prensa negativa, sanciones administrativas o anomalías mercantiles en las fuentes públicas consultadas."

    # Pre-cálculo dinámico de altura (Ancho seguro de columna: 172mm)
    pdf.set_font("Helvetica", "", 8.5)
    saltos_rues  = contenido_rues.count('\n')
    lineas_rues  = max(1, int(pdf.get_string_width(contenido_rues.replace('\n', ' ')) / 172) + 1) + saltos_rues
    h_rues       = lineas_rues * 4.2
    
    # Altura del Bento con márgenes internos holgados
    altura_bento_rues = 4.5 + 3.0 + 1.5 + h_rues + 4.5

    # Dibujo del contenedor Bento principal (Margen simétrico exacto de 15 a 195)
    pdf.set_fill_color(*COLOR_BG_GRID)
    pdf.set_draw_color(*COLOR_LINE_TENUE)
    pdf.set_line_width(0.2)
    pdf.rect(15, start_y, 180, altura_bento_rues, style="FD")

    # Posicionamiento con márgenes de seguridad alineados a X = 19
    pdf.set_xy(19, start_y + 4.5)
    pdf.set_font("Helvetica", "B", 6.5); pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(172, 3.0, "ANÁLISIS DE ADVERSE MEDIA Y VALIDACIÓN EN REGISTRO MERCANTIL", ln=1)
    
    # Espaciado y renderizado del cuerpo de texto
    pdf.set_xy(19, start_y + 4.5 + 3.0 + 1.5)
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.multi_cell(172, 4.2, contenido_rues)

    pdf.set_y(start_y + altura_bento_rues)

    # Sello de seguridad y autenticidad del sistema
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(0, 3.5, f"Estampa de Tiempo de Evaluación: {s_fecha} COT", ln=1)
    pdf.cell(0, 3.5, f"Código de Verificación del Reporte: HBPO-COMPLIANCE-{s_nit.replace('-', '')}-{s_radicado.upper()}", ln=1)

    # 🛡️ RETORNO SEGURO MULTI-VERSIÓN (Detecta dinámicamente si es bytes, bytearray o str)
    out = pdf.output()
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    return str(out).encode('latin-1')