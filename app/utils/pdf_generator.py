# app/utils/pdf_generator.py
#
# Requiere: fpdf2 >= 2.7.6, pypdf >= 3.9, pillow
#
# ─────────────────────────────────────────────────────────────────────────
# CHANGELOG DE ESTA REVISIÓN
#   [FIX-01] render_infolaft_snippet tenía el cuerpo sin indentar -> el
#            módulo no compilaba (IndentationError). Reescrita completa.
#   [FIX-02] Regex GAFI sin frontera de palabra marcaba "SIN COINCIDENCIAS"
#            como GAFI=SI -> alerta LAFT falsa. Ahora exige \b(SI|NO)\b.
#   [FIX-03] La tarjeta de la Sección 2 ignoraba error_lectura /
#            requiere_revision_manual y pintaba verde un PDF ilegible,
#            contradiciendo el dictamen de la Sección 3. Clasificación
#            unificada en _clasificar_entidad() — única fuente de verdad.
#   [FIX-04] El código de verificación usaba el NIT también en Persona
#            Natural, produciendo "HBPO-COMPLIANCE-N/D-...".
#   [FIX-05] La Sección 4 afirmaba "sin hallazgos" cuando simplemente no
#            había análisis registrado. Ausencia de dato != ausencia de
#            hallazgo.
#   [FIX-06] _s(0) devolvía "" y la puntuación tipográfica (— “ ” ’) se
#            perdía. Ahora translitera antes de descartar.
#   [FIX-07] Alturas de los contenedores Bento calculadas por ancho de
#            cadena (ignora el corte por palabra) -> desbordes. Ahora se
#            usa el medidor real de fpdf2 (dry_run).
#   [FIX-08] datos_master accedido con [] en 8 claves -> KeyError mataba
#            toda la generación. Todo pasa por .get() con default.
#   [FIX-09] Las capturas de evidencia (datos KYC) se escribían a %TEMP%.
#            Ahora se renderizan en memoria.
#   [FIX-10] except Exception mudos -> logging.exception con trazabilidad.
#   [FIX-11] Evidencias PDF que fallaban al fusionar desaparecían del
#            expediente sin dejar rastro. Ahora se reportan.
#   [UX-01]  Sección 2 rediseñada: jerarquía rol/nombre, grilla de
#            metadatos, motivo explícito de la alerta, archivo fuente y
#            barra resumen del screening.
# ─────────────────────────────────────────────────────────────────────────

import io
import os
import re
import logging
import unicodedata
from pathlib import Path

import pypdf
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from PIL import Image as PILImage

logger = logging.getLogger(__name__)

# ─── PALETA DE COLORES EDITORIAL PREMIUM (FINTECH) ───
COLOR_PRIMARY = (15, 32, 67)       # Azul Marino Profundo
COLOR_ACCENT = (37, 99, 235)       # Azul Eléctrico
COLOR_TEXT_MAIN = (15, 23, 42)     # Slate 900
COLOR_TEXT_BODY = (30, 41, 59)     # Slate 800
COLOR_TEXT_MUTED = (100, 116, 139) # Slate 500
COLOR_BG_GRID = (248, 250, 252)    # Slate 50
COLOR_BG_CARD = (253, 253, 254)
COLOR_LINE_TENUE = (226, 232, 240) # Slate 200

# ─── SEMÁFORO ÚNICO DE CUMPLIMIENTO ───
# Estas tres paletas se usan TANTO en la tarjeta de la Sección 2 como en
# los badges de la Sección 3. Un mismo caso no puede verse verde en una
# sección y ámbar en la otra porque ambas leen de aquí.
SEMAFORO = {
    "limpio":     {"bg": (212, 237, 218), "borde": (195, 230, 203), "texto": (21, 87, 36),   "franja": (40, 167, 69)},
    "revision":   {"bg": (255, 243, 205), "borde": (255, 238, 186), "texto": (133, 100, 4),  "franja": (255, 193, 7)},
    "alerta":     {"bg": (248, 215, 218), "borde": (245, 198, 203), "texto": (114, 28, 36),  "franja": (220, 53, 69)},
    "preliminar": {"bg": (224, 242, 254), "borde": (186, 230, 253), "texto": (3, 105, 161),  "franja": (14, 165, 233)},
}

# ─── GEOMETRÍA DE PÁGINA ───
PAGE_X0 = 15.0            # margen izquierdo
PAGE_X1 = 195.0           # margen derecho
PAGE_W = PAGE_X1 - PAGE_X0
MARGEN_INFERIOR = 18.0
LIMITE_Y = 297.0 - MARGEN_INFERIOR - 4.0   # y máximo utilizable = 275 mm
SIN_DATO = "-"

# ─── TIPOS DE ENTIDAD EVALUADA ───
# Única fuente de verdad para el valor de "tipo_persona" que circula entre
# screening_ui.py y este módulo — evita que un typo en un literal de cadena
# rompa silenciosamente la segmentación Jurídica / Natural.
TIPO_PERSONA_JURIDICA = "Persona Jurídica"
TIPO_PERSONA_NATURAL = "Persona Natural"

# Valores que NUNCA son un nombre real de vinculado: son etiquetas del
# propio certificado que se colaron en el parseo.
_NOMBRES_BASURA = {
    "", "LISTAS", "LISTAS CONSULTADAS", "LISTA DE COINCIDENCIAS",
    "NO DETECTADO", "REPORTE DE BUSQUEDA", "REPORTE DE BÚSQUEDA",
    "DATOS CONSULTADOS", "RESUMEN DE RESULTADOS", "NOTA LEGAL",
    "COINCIDENCIAS", "RESULTADOS", "N/D", "N/A",
}


# ══════════════════════════════════════════════════════════════════════
# SANITIZACIÓN DE TEXTO
# ══════════════════════════════════════════════════════════════════════

# fpdf2 con fuentes core (Helvetica) solo soporta latin-1: un guion largo
# "—" o una comilla tipográfica rompen la generación con
# FPDFUnicodeEncodingException. En vez de descartar esos caracteres (que
# dejaba huecos: 'ACME — "Global"' -> 'ACME  Global'), se transliteran.
_TRANSLITERACION = {
    "—": "-", "–": "-", "‒": "-", "−": "-",   # — – ‒ −
    "‘": "'", "’": "'", "‚": ",", "‛": "'",
    "“": '"', "”": '"', "„": '"',
    "…": "...", "•": "-", "·": "-", "‑": "-",
    " ": " ", " ": " ", " ": " ", "​": "",
    "€": "EUR", "™": "(TM)", "←": "<-", "→": "->",
    "¿": "",
}


def _s(texto) -> str:
    """Deja el texto seguro para las fuentes core latin-1 de fpdf2.

    A diferencia de la versión anterior: el 0 y el False numérico ya no se
    convierten en cadena vacía, y la puntuación tipográfica se translitera
    en lugar de desaparecer.
    """
    if texto is None:
        return ""
    txt = str(texto)
    if not txt:
        return ""
    for origen, destino in _TRANSLITERACION.items():
        if origen in txt:
            txt = txt.replace(origen, destino)
    # Último recurso: descompone acentos exóticos no cubiertos por latin-1
    # (ej. ẞ, ā) en su letra base en lugar de borrarlos.
    if any(ord(c) > 255 for c in txt):
        txt = "".join(
            c if ord(c) < 256 else unicodedata.normalize("NFKD", c).encode("ascii", "ignore").decode("ascii")
            for c in txt
        )
    return txt.encode("latin-1", "ignore").decode("latin-1")


def _norm(texto) -> str:
    """Normaliza para comparar: sin acentos, mayúsculas, sin espacios dobles."""
    if texto is None:
        return ""
    txt = unicodedata.normalize("NFKD", str(texto))
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return " ".join(txt.upper().split())


def _fmt(valor, vacio: str = SIN_DATO) -> str:
    """Convierte 'No detectado' / None / '' en un guion discreto.

    Repetir "No detectado" cuatro veces en una tarjeta no comunica nada;
    un guion deja claro que el campo está vacío sin gritar.
    """
    txt = _s(valor).strip()
    if not txt or _norm(txt) in {"NO DETECTADO", "N/D", "N/A", "NONE", "NULL"}:
        return vacio
    return txt


# ══════════════════════════════════════════════════════════════════════
# DOCUMENTO BASE
# ══════════════════════════════════════════════════════════════════════

class ComplianceMaestroPDF(FPDF):
    """Estructura de diseño institucional con doble logo simétrico para HBPO-Adamo-Paycop."""

    TOP_MARGIN = 42.0

    def __init__(self, logo_adamo=None, logo_holdings=None, tipo_persona=TIPO_PERSONA_JURIDICA):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.logo_adamo = logo_adamo
        self.logo_holdings = logo_holdings
        self.tipo_persona = tipo_persona
        self.set_margins(left=PAGE_X0, top=self.TOP_MARGIN, right=PAGE_X0)
        self.set_auto_page_break(auto=True, margin=MARGEN_INFERIOR)

    # ── utilidades de medición ────────────────────────────────────────
    def contar_lineas(self, ancho: float, texto: str) -> int:
        """Número REAL de líneas que ocupará multi_cell.

        El cálculo anterior (ancho_de_cadena / ancho_columna) ignoraba que
        las palabras no se parten, así que subestimaba y el texto se salía
        del contenedor Bento. fpdf2 sabe la respuesta exacta.
        """
        texto = texto or ""
        try:
            lineas = self.multi_cell(ancho, 4.2, texto, dry_run=True, output="LINES")
            return max(1, len(lineas))
        except Exception:  # fpdf2 antiguo sin dry_run
            saltos = texto.count("\n")
            ancho_txt = self.get_string_width(texto.replace("\n", " "))
            return max(1, int(ancho_txt / ancho) + 1 + saltos)

    def recortar(self, texto: str, ancho_max: float, sufijo: str = "...") -> str:
        """Recorta por ANCHO REAL, no por número de caracteres.

        38 caracteres en mayúsculas ocupan mucho más que 38 en minúsculas;
        el corte por longitud dejaba unos valores cortados de más y otros
        desbordados.
        """
        texto = _s(texto)
        if not texto or self.get_string_width(texto) <= ancho_max:
            return texto
        ancho_sufijo = self.get_string_width(sufijo)
        recorte = texto
        while recorte and self.get_string_width(recorte) + ancho_sufijo > ancho_max:
            recorte = recorte[:-1]
        return recorte.rstrip() + sufijo

    def espacio_restante(self) -> float:
        return LIMITE_Y - self.get_y()

    def asegurar_espacio(self, alto: float) -> None:
        """Abre página nueva si el bloque completo no cabe."""
        if self.get_y() + alto > LIMITE_Y:
            self.add_page()

    # ── plantilla ─────────────────────────────────────────────────────
    def header(self):
        if self.logo_adamo and os.path.exists(self.logo_adamo):
            self.image(self.logo_adamo, x=15, y=10, h=13)

        if self.logo_holdings and os.path.exists(self.logo_holdings):
            self.image(self.logo_holdings, x=163, y=10.5, h=12)

        titulo_doc = (
            "EXPEDIENTE DE DEBIDA DILIGENCIA INDIVIDUAL - PERSONA NATURAL / UBO"
            if self.tipo_persona == TIPO_PERSONA_NATURAL
            else "EXPEDIENTE DE DEBIDA DILIGENCIA CORPORATIVA - PERSONA JURÍDICA"
        )
        self.set_xy(45, 11.5)
        self.set_text_color(*COLOR_PRIMARY)
        # El canal central mide 115 mm entre los dos logos: si el título no
        # cabe se reduce el cuerpo en lugar de invadir el logo de Holdings.
        for cuerpo in (9.0, 8.5, 8.0, 7.5):
            self.set_font("Helvetica", "B", cuerpo)
            if self.get_string_width(titulo_doc) <= 114:
                break
        self.cell(115, 4.5, titulo_doc, align="C")

        self.set_xy(45, 16.5)
        self.set_font("Helvetica", "", 6.5)
        self.set_text_color(*COLOR_TEXT_MUTED)
        self.cell(115, 4, "VERIFICACIÓN DE ANTECEDENTES, LISTAS DE CONTROL Y VALIDACIÓN DE SEGURIDAD OPERATIVA", align="C")

        self.set_draw_color(*COLOR_PRIMARY)
        self.set_line_width(0.6)
        self.line(PAGE_X0, 30, PAGE_X1, 30)

        self.set_xy(self.l_margin, self.TOP_MARGIN)

    def footer(self):
        self.set_y(-18)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*COLOR_TEXT_MUTED)
        self.set_draw_color(*COLOR_LINE_TENUE)
        self.set_line_width(0.2)
        self.line(PAGE_X0, self.get_y() - 2, PAGE_X1, self.get_y() - 2)
        self.cell(
            0, 8,
            f"Certificación de Cumplimiento - Confidencial Interno/Externo - Página {self.page_no()}/{{nb}}",
            border=0, align="C",
        )


# ══════════════════════════════════════════════════════════════════════
# PARSEO DEL CERTIFICADO INFOLAFT
# ══════════════════════════════════════════════════════════════════════

_KEYWORDS_SISTEMA = (
    "REPORTE DE BUSQUEDA", "DATOS CONSULTADOS", "SU CONSULTA FUE",
    "DOCUMENTO DE IDENTIDAD", "RESUMEN DE RESULTADOS", "LISTAS CONSULTADAS",
    "LISTA DE COINCIDENCIAS", "NOTA LEGAL", "PAGINA", "CONSULTADO POR",
    "FECHA Y HORA", "NUMERO DE CONSULTA", "NO SE OBTUVIERON RESULTADOS",
    "PARA LA BUSQUEDA REALIZADA", "REQUIERE DEBIDA DILIGENCIA",
    "TIPO DE DOCUMENTO", "INFOLAFT", "WWW.", "HTTP",
)

# ─── ANCLAJES REALES DEL REPORTE INFOLAFT ─────────────────────────────
# Extraídos de reportes de produccion ("...-SearchByNameAndId.pdf"). El
# layout del PDF intercala las etiquetas, así que el texto plano queda
# pegado de formas poco intuitivas:
#
#   RESUMEN DE RESULTADOS:
#   LISTAS
#   CONSULTADAS:
#   316No se obtuvieron resultados
#   para la busqueda realizada.DATOS CONSULTADOS
#   DOCUMENTO DE IDENTIDAD:
#   0901787129SU CONSULTA FUE: ARIMETRIX SAS
#   ¿REQUIERE DEBIDA DILIGENCIA INTENSIFICADA POR CONCEPTO PEP O JURISDICCION DE RIESGO GAFI?: NO
#   ...
#   PAGINA  1 /2 389617601 NUMERO DE CONSULTA:
#   CONSULTADO POR: Adrian  Cardona  FECHA Y HORA DE CONSULTA: 10/09/2026 15:22:03
#
# Detalles que importan y que rompían la extraccion anterior:
#   - "316" es el numero de LISTAS CONSULTADAS, NO el de coincidencias.
#     Jamas debe leerse como resultado del screening.
#   - El numero de consulta va ANTES de su etiqueta, no despues.
#   - El documento viene con un cero de relleno al frente (0901787129).
#   - El nombre vive en "SU CONSULTA FUE:", no en "DATOS CONSULTADOS".
# ──────────────────────────────────────────────────────────────────────

# Etiquetas que preceden al nombre del vinculado, en orden de fiabilidad.
_RE_NOMBRE_ETIQUETADO = (
    re.compile(r"SU CONSULTA FUE\s*[:\-]\s*([^\n¿|]{3,90})", re.IGNORECASE),
    re.compile(r"(?:RAZ[OÓ]N SOCIAL|NOMBRE COMPLETO|NOMBRE)\s*[:\-]\s*([^\n¿|]{3,90})", re.IGNORECASE),
    re.compile(r"DATOS CONSULTADOS\s*[:\-]?\s*\n\s*([^\n¿|]{3,90})", re.IGNORECASE),
)

# Documento de identidad / NIT. InfoLAFT antepone un cero de relleno.
_RE_DOCUMENTO = re.compile(r"DOCUMENTO DE IDENTIDAD\s*[:\-]?\s*([\d\.\-]{6,20})", re.IGNORECASE)

# Veredicto explícito de "sin coincidencias". Es la ÚNICA frase que
# autoriza a dar por confirmado un screening limpio en este formato.
_RE_SIN_RESULTADOS = re.compile(
    r"NO SE OBTUVIERON RESULTADOS\s+PARA LA B[UÚ]SQUEDA REALIZADA", re.IGNORECASE
)
# Cantidad de listas de control consultadas (316 en los reportes actuales).
_RE_LISTAS_CONSULTADAS = re.compile(r"LISTAS\s*CONSULTADAS\s*[:\-]?\s*(\d{1,5})", re.IGNORECASE)
# Analista que ejecutó la consulta — trazabilidad de quién screeneó.
_RE_CONSULTADO_POR = re.compile(r"CONSULTADO POR\s*[:\-]?\s*(.{3,60}?)\s*FECHA Y HORA", re.IGNORECASE)
# El radicado precede a su etiqueta: "PAGINA 1 /2 389617601 NUMERO DE CONSULTA:"
_RE_RADICADO_ANTEPUESTO = re.compile(r"\b(\d{8,10})\s*N[UÚ]MERO DE CONSULTA", re.IGNORECASE)


def _es_nombre_valido(candidato: str) -> bool:
    """Un nombre capturado por etiqueta no puede ser a su vez una etiqueta.

    Sin esta validacion, el patron de "DATOS CONSULTADOS" devolvia la
    línea siguiente tal cual — que en estos reportes es "DOCUMENTO DE
    IDENTIDAD:" — y ese texto terminaba impreso como razón social.
    """
    cand = _norm(candidato).rstrip(":").strip()
    if len(cand) < 3 or cand in _NOMBRES_BASURA:
        return False
    if any(kw in cand for kw in _KEYWORDS_SISTEMA):
        return False
    return any(c.isalpha() for c in cand)


def parsear_texto_infolaft(texto: str) -> dict:
    """
    Analiza el texto plano del PDF de Infolaft y extrae la información de manera universal
    mediante filtrado de palabras clave del sistema y patrones de expresiones regulares.
    """
    res = {
        "nombre": "No detectado",
        "identificacion": "No detectado",
        "radicado": "No detectado",
        "fecha_consulta": "No detectado",
        "resultados": "0",
        "intensificada": "NO",
        # Trazan si el valor vino realmente del PDF o es el default silencioso.
        # Sin esto, un patrón que no calza se lee igual que "sin coincidencias".
        "resultados_detectado": False,
        "intensificada_detectado": False,
        "motivo_revision": "",
        # Datos de trazabilidad que el reporte sí trae y antes se perdían.
        "listas_consultadas": "",
        "consultado_por": "",
    }

    texto = texto or ""
    texto_plano = " ".join(texto.split())

    # 1. Radicado / Número de Consulta.
    #    En InfoLAFT el número va ANTES de la etiqueta ("... 389617601
    #    NÚMERO DE CONSULTA:"), por eso se intenta ese orden primero.
    rad_match = (
        _RE_RADICADO_ANTEPUESTO.search(texto_plano)
        or re.search(r"N[UÚ]MERO DE CONSULTA\D{0,40}?\b(\d{8,10})\b", texto_plano, re.IGNORECASE)
        or re.search(r"\b(3\d{8}|1\d{8})\b", texto_plano)
    )
    if rad_match:
        res["radicado"] = rad_match.group(1)

    # 2. Fecha y Hora de Consulta
    fecha_match = re.search(r"FECHA Y HORA DE CONSULTA[:\s]*([\d/\-]+ [\d:]+)", texto_plano, re.IGNORECASE)
    if fecha_match:
        res["fecha_consulta"] = fecha_match.group(1).strip()

    # 2.b Trazabilidad: cuántas listas se barrieron y quién ejecutó la consulta.
    listas_match = _RE_LISTAS_CONSULTADAS.search(texto_plano)
    if listas_match:
        res["listas_consultadas"] = listas_match.group(1)
    analista_match = _RE_CONSULTADO_POR.search(texto_plano)
    if analista_match:
        res["consultado_por"] = " ".join(analista_match.group(1).split())

    # 3. Coincidencias en listas.
    #    El orden es deliberado: primero la frase explícita de veredicto.
    #    El número que sigue a "RESUMEN DE RESULTADOS" en este layout es el
    #    de LISTAS CONSULTADAS (316), no el de coincidencias — leerlo como
    #    resultado convertiría un certificado limpio en "316 coincidencias".
    if _RE_SIN_RESULTADOS.search(texto_plano):
        res["resultados"] = "0"
        res["resultados_detectado"] = True
    else:
        res_match = re.search(
            r"RESUMEN DE RESULTADOS\s*[:\-]?\s*(\d{1,4})\b", texto_plano, re.IGNORECASE
        )
        if res_match and res_match.group(1) != res["listas_consultadas"]:
            res["resultados"] = res_match.group(1)
            res["resultados_detectado"] = True
        else:
            coinc_match = re.search(
                r"LISTA DE COINCIDENCIAS\s*[:\-]?\s*(\d{1,4})\b", texto_plano, re.IGNORECASE
            )
            if coinc_match:
                res["resultados"] = coinc_match.group(1)
                res["resultados_detectado"] = True

    # 4. Monitoreo Intensificado / GAFI / PEP
    #    [FIX-02] \b obligatorio: sin él, "GAFI: SIN COINCIDENCIAS" capturaba
    #    el "SI" de "SIN" y disparaba una alerta LAFT inexistente.
    gafi_match = re.search(r"GAFI\??\s*[:\-]?\s*\b(SI|S[IÍ]|NO)\b", texto_plano, re.IGNORECASE)
    if gafi_match:
        valor = _norm(gafi_match.group(1))
        res["intensificada"] = "SI" if valor.startswith("S") else "NO"
        res["intensificada_detectado"] = True
    else:
        # Algunos certificados no responden SI/NO sino con una frase. Sin
        # esto, exigir \b dejaría en ámbar a todos los certificados limpios
        # redactados de esa forma.
        gafi_frase = re.search(
            r"GAFI[^.\n]{0,90}?\b(SIN COINCIDENCIAS|NO SE OBTUVIERON|NO REGISTRA|NO APARECE|NO PRESENTA)\b",
            texto_plano, re.IGNORECASE,
        )
        if gafi_frase:
            res["intensificada"] = "NO"
            res["intensificada_detectado"] = True

    # 5. Identificación / Tax ID / NIT / Cédula.
    #    La etiqueta del reporte manda; el cero de relleno que antepone
    #    InfoLAFT ("0901787129") se descarta para que el NIT impreso
    #    coincida con el del formulario.
    doc_match = _RE_DOCUMENTO.search(texto)
    if doc_match:
        crudo = doc_match.group(1).strip().strip(".-")
        limpio = re.sub(r"^0+(?=\d)", "", crudo)
        if limpio and limpio != res["radicado"]:
            res["identificacion"] = limpio
    if res["identificacion"] == "No detectado":
        id_match = re.search(r"\b(\d{2,3}-\d{6,8}|\d{7,10}-\d)\b", texto_plano)
        if id_match:
            res["identificacion"] = id_match.group(1).strip()

    # 6. Nombre del Vinculado
    #    6.a Primero por etiqueta explícita (fiable). En InfoLAFT es
    #    "SU CONSULTA FUE:", que devuelve el término exacto consultado.
    for patron in _RE_NOMBRE_ETIQUETADO:
        m = patron.search(texto)
        if m and _es_nombre_valido(m.group(1)):
            res["nombre"] = _norm(m.group(1)).rstrip(":").strip()
            break

    #    6.b Si no hay etiqueta, se recurre a la heurística por exclusión.
    if res["nombre"] == "No detectado":
        for line in (l.strip() for l in texto.split("\n") if l.strip()):
            line_up = _norm(line)
            if any(kw in line_up for kw in _KEYWORDS_SISTEMA):
                continue
            if re.match(r"^[\d\.\s\-/:]+$", line):       # solo números, ID o fechas
                continue
            if len(line_up) < 3 or line_up in _NOMBRES_BASURA:
                continue
            # Una línea que es una sola palabra genérica del certificado
            # ("LISTAS", "RESULTADOS") no es una razón social.
            if len(line_up.split()) == 1 and len(line_up) <= 8:
                continue
            res["nombre"] = line_up
            break

    # ── Marca de confianza del parseo ─────────────────────────────────
    # Un partner "limpio" en el certificado final debe significar que SÍ se
    # verificaron resultados y monitoreo GAFI, no que el regex no encontró nada.
    res["requiere_revision_manual"] = not (
        res["resultados_detectado"] and res["intensificada_detectado"]
    )
    if res["requiere_revision_manual"]:
        res["motivo_revision"] = (
            "No fue posible confirmar en el texto del certificado el número de "
            "coincidencias y/o el monitoreo intensificado GAFI."
        )
    res["error_lectura"] = False

    return res


def _resultado_no_confiable(motivo: str) -> dict:
    """
    Resultado placeholder para cuando el PDF existe pero no se pudo leer
    (escaneo sin texto, archivo corrupto, formato no reconocido).

    Antes esto devolvía None y la entidad simplemente desaparecía del
    expediente sin dejar rastro — el certificado final podía salir
    "APROBADO S/ANOMALÍAS" sin que ese vinculado hubiera sido evaluado.
    """
    return {
        "nombre": motivo,           # se conserva por compatibilidad con screening_ui
        "identificacion": "No detectado",
        "radicado": "No detectado",
        "fecha_consulta": "No detectado",
        "resultados": "0",
        "intensificada": "NO",
        "resultados_detectado": False,
        "intensificada_detectado": False,
        "requiere_revision_manual": True,
        "error_lectura": True,
        "motivo_revision": motivo,
    }


_RE_CERTIFICADO_NOMBRE = re.compile(r"Certificado_(\d+)", re.IGNORECASE)

# InfoLAFT exporta con el patrón "<radicado>-<NOMBRE>___<documento>-SearchByNameAndId.pdf"
# (ej. "389617601-ARIMETRIX_SAS___901787129-SearchByNameAndId.pdf"). El nombre
# del archivo es entonces una fuente de respaldo legítima para los tres
# campos, útil cuando el texto del PDF no se pudo leer del todo.
_RE_EXPORT_INFOLAFT = re.compile(
    r"^(\d{8,10})[-_](.+?)_{2,}(\d{6,15})[-_]", re.IGNORECASE
)


def _datos_desde_nombre_archivo(nombre_archivo: str) -> dict:
    """Radicado, nombre y documento deducibles del nombre del archivo."""
    datos = {}
    nombre_archivo = nombre_archivo or ""
    m = _RE_EXPORT_INFOLAFT.search(nombre_archivo)
    if m:
        datos["radicado"] = m.group(1)
        datos["nombre"] = _norm(m.group(2).replace("_", " "))
        datos["identificacion"] = re.sub(r"^0+(?=\d)", "", m.group(3))
        return datos
    m = _RE_CERTIFICADO_NOMBRE.search(nombre_archivo)
    if m:
        datos["radicado"] = m.group(1)
    elif re.match(r"^(\d{8,10})[-_]", nombre_archivo):
        datos["radicado"] = re.match(r"^(\d{8,10})[-_]", nombre_archivo).group(1)
    return datos


def _aplicar_fallback_nombre_archivo(res: dict, nombre_archivo: str) -> dict:
    """
    Punto único donde se fija el veredicto final de confianza de un
    documento (res['requiere_revision_manual']). Se ejecuta siempre — se
    haya podido leer el texto o no — para que el nombre del archivo (ej.
    "Certificado_1053866845.pdf") sirva de señal adicional:

      - Si el radicado no se pudo leer del texto, se recupera del nombre
        del archivo (evita el falso "No. Registro Consulta: No detectado"
        cuando el certificado sí existe y sí se procesó).
      - Un documento cuyo TEXTO reportó "0 coincidencias" de forma
        confiable (resultados_detectado=True) se confirma como CONFORME
        aunque el radicado no se haya podido extraer del cuerpo del PDF.
      - Un PDF sin texto extraíble (OCR fallido / escaneo) NUNCA se marca
        como limpio solo por el nombre del archivo.
      - Una coincidencia real (resultados > 0) o GAFI=SI siempre gana y
        marca alerta, sin importar el nombre del archivo.

    NOTA: requiere_revision_manual=False en el caso de coincidencia real
    NO significa "conforme": significa "no hay nada que releer, el dato se
    leyó bien". El veredicto de riesgo lo produce _clasificar_entidad(),
    donde una coincidencia real siempre pinta alerta roja.
    """
    res.setdefault("motivo_revision", "")
    res["fuente_archivo"] = nombre_archivo or ""

    del_archivo = _datos_desde_nombre_archivo(nombre_archivo)
    res["certificado_nombre_valido"] = bool(del_archivo.get("radicado"))

    def _vacio(clave):
        return res.get(clave) in (None, "", "No detectado")

    if _vacio("radicado") and del_archivo.get("radicado"):
        res["radicado"] = del_archivo["radicado"]
        res["radicado_via_nombre_archivo"] = True
    # El nombre y el documento del archivo solo rellenan huecos: nunca
    # pisan lo que sí se pudo leer del texto del certificado.
    if _vacio("identificacion") and del_archivo.get("identificacion"):
        res["identificacion"] = del_archivo["identificacion"]
        res["identificacion_via_nombre_archivo"] = True
    if _vacio("nombre") and del_archivo.get("nombre"):
        res["nombre"] = del_archivo["nombre"]
        res["nombre_via_nombre_archivo"] = True

    coincidencias_reales = str(res.get("resultados", "0")).strip() not in ("0", "")
    gafi_alerta = _norm(res.get("intensificada", "NO")) == "SI"
    resultados_confirmados = res.get("resultados_detectado", False) and str(res.get("resultados", "0")).strip() == "0"
    no_registro_detectado = res.get("radicado", "No detectado") not in (None, "", "No detectado")

    if coincidencias_reales or gafi_alerta:
        res["requiere_revision_manual"] = False
    elif resultados_confirmados and (no_registro_detectado or res["certificado_nombre_valido"]):
        res["requiere_revision_manual"] = False
        res["motivo_revision"] = ""
    else:
        res["requiere_revision_manual"] = True
        if not res.get("motivo_revision"):
            res["motivo_revision"] = (
                "El certificado no permitió confirmar el resultado del screening. "
                "Validar manualmente contra el documento original."
            )

    return res


def procesar_archivo_pdf(uploaded_file) -> dict:
    if uploaded_file is None:
        return None

    nombre_archivo = getattr(uploaded_file, "name", "") or ""

    try:
        # 🚀 RESETEAR EL CURSOR DE LECTURA DEL BUFFER (BytesIO)
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)

        reader = pypdf.PdfReader(uploaded_file)

        # Muchos certificados llegan con cifrado vacío (solo permisos). Sin
        # esto pypdf lanza y el documento se perdía como "corrupto".
        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt("")
            except Exception:
                logger.warning("PDF cifrado no descifrable: %s", nombre_archivo)

        full_text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                full_text += t + "\n"

        if not full_text.strip():
            # PDF sin texto extraíble (típico de un escaneo/imagen). No hay
            # base para afirmar "sin coincidencias" — se marca sin confianza.
            logger.warning("PDF sin texto extraible: %s", nombre_archivo)
            resultado = _resultado_no_confiable(
                "PDF sin texto extraíble (documento escaneado o imagen). Requiere lectura manual."
            )
        else:
            resultado = parsear_texto_infolaft(full_text)
    except Exception:
        logger.exception("Fallo al procesar el PDF '%s'", nombre_archivo)
        resultado = _resultado_no_confiable(
            "El archivo no pudo abrirse o está dañado. Requiere lectura manual."
        )

    return _aplicar_fallback_nombre_archivo(resultado, nombre_archivo)


# ══════════════════════════════════════════════════════════════════════
# CLASIFICACIÓN ÚNICA DE RIESGO  [FIX-03]
# ══════════════════════════════════════════════════════════════════════

def _clasificar_entidad(ent: dict, es_prospecto: bool = False) -> dict:
    """Decide el estatus visual de UNA entidad evaluada.

    Es la única función autorizada a decidir el color de una entidad; la
    Sección 2 y la barra resumen la consultan. El orden de las ramas es
    deliberado: una coincidencia real gana siempre, y una lectura fallida
    nunca puede caer en la rama verde.
    """
    resultados = str(ent.get("resultados", "0")).strip() or "0"
    intensificada = "SI" if _norm(ent.get("intensificada", "NO")) == "SI" else "NO"
    error_lectura = bool(ent.get("error_lectura"))
    revision = bool(ent.get("requiere_revision_manual"))
    radicado = _fmt(ent.get("radicado"), "")

    coincidencias = resultados not in ("0", "")
    # Entidades Pagadoras Cross-Border (Modo Express): screening_ui las
    # inyecta con radicado "N/A - Sin Consulta InfoLAFT". Son declarativas,
    # nunca consultadas: no pueden verse como un vinculado más.
    sin_consulta = "SIN CONSULTA" in _norm(radicado)

    if coincidencias or intensificada == "SI":
        clave, etiqueta = "alerta", "COINCIDENCIA EN LISTAS - AUDITORÍA LAFT"
        motivo = "Se hallaron coincidencias o monitoreo intensificado GAFI. Escalar al Oficial de Cumplimiento."
    elif sin_consulta:
        clave, etiqueta = "revision", "DECLARADA - SIN CONSULTA EN LISTAS"
        motivo = ("Entidad declarada por el area comercial sin consulta InfoLAFT en esta etapa. "
                  "Debe screenearse en el Onboarding Formal SARLAFT.")
    elif error_lectura:
        clave, etiqueta = "revision", "LECTURA NO CONFIABLE - VALIDAR MANUALMENTE"
        motivo = ent.get("motivo_revision") or (
            "El certificado no entregó texto legible; el resultado no pudo verificarse."
        )
    elif revision:
        clave, etiqueta = "revision", "DATOS INCOMPLETOS - VALIDAR MANUALMENTE"
        motivo = ent.get("motivo_revision") or (
            "No se pudo confirmar el número de coincidencias ni el monitoreo GAFI."
        )
    elif es_prospecto and (not radicado or "BDM" in radicado.upper() or "EXP" in radicado.upper()):
        clave, etiqueta = "preliminar", "VERIFICACIÓN PRELIMINAR (EXPRESS)"
        motivo = "Verificación comercial preliminar: no reemplaza el screening formal SARLAFT."
    else:
        clave, etiqueta = "limpio", "SIN COINCIDENCIAS"
        motivo = ""

    paleta = SEMAFORO[clave]
    return {
        "clave": clave,
        "etiqueta": etiqueta,
        "motivo": motivo,
        "coincidencias": coincidencias,
        "pendiente": clave == "revision",
        **paleta,
    }


def _nombre_de_respaldo(ent: dict, datos_master: dict) -> str:
    """Nombre a mostrar cuando el certificado no permitió extraerlo.

    Antes la tarjeta imprimía literalmente "REPRESENTANTE LEGAL: LISTAS"
    (una etiqueta del PDF confundida con el nombre). Ahora se recurre al
    dato que el usuario ya capturó en el formulario, por rol.
    """
    rol = _norm(ent.get("rol_interno", ""))
    if "REPRESENTANTE" in rol or "REP. LEGAL" in rol:
        candidato = datos_master.get("rep_legal_nom", "")
    elif "ACCIONISTA" in rol or "BENEFICIARIO" in rol or "SOCIO" in rol or "UBO" in rol:
        candidato = datos_master.get("accionista_nom", "")
    else:
        candidato = datos_master.get("empresa_principal") or datos_master.get("nombre_completo", "")

    candidato = _fmt(candidato, "")
    if not candidato:
        candidato = _fmt(datos_master.get("empresa_principal") or datos_master.get("nombre_completo"), "")
    return candidato.upper() if candidato else "VINCULADO NO IDENTIFICADO"


def _resolver_nombre_entidad(ent: dict, datos_master: dict) -> tuple:
    """Devuelve (nombre_a_mostrar, viene_del_formulario)."""
    if ent.get("error_lectura"):
        return _nombre_de_respaldo(ent, datos_master), True

    nombre = _norm(ent.get("nombre", ""))
    if not nombre or nombre in _NOMBRES_BASURA or len(nombre) < 3:
        return _nombre_de_respaldo(ent, datos_master), True
    return nombre, False


# ══════════════════════════════════════════════════════════════════════
# LOGOS
# ══════════════════════════════════════════════════════════════════════

def resolver_ruta_logo(nombre_base: str) -> str:
    """Busca el logo relativo al módulo (no al cwd) y de forma determinista."""
    base_modulo = Path(__file__).resolve()
    candidatos = []
    for parent in base_modulo.parents[:4]:
        candidatos.append(parent / "app" / "static" / "img" / "logos")
        candidatos.append(parent / "static" / "img" / "logos")
    candidatos.append(Path("app") / "static" / "img" / "logos")
    candidatos.append(Path("static") / "img" / "logos")

    prefijos = {
        nombre_base.lower(),
        nombre_base.lower().replace(" ", "_"),
        nombre_base.lower().replace(" ", "-"),
    }

    for carpeta in candidatos:
        if not carpeta.is_dir():
            continue
        # sorted() -> el mismo logo siempre; os.listdir no garantiza orden.
        for archivo in sorted(p.name for p in carpeta.iterdir() if p.is_file()):
            if any(archivo.lower().startswith(p) for p in prefijos):
                return str(carpeta / archivo)
    return None


# ══════════════════════════════════════════════════════════════════════
# GENERACIÓN DEL EXPEDIENTE
# ══════════════════════════════════════════════════════════════════════

def generar_pdf_base(datos_master: dict) -> bytes:
    datos_master = datos_master or {}
    tipo_persona = datos_master.get("tipo_persona", TIPO_PERSONA_JURIDICA)
    es_juridica = tipo_persona == TIPO_PERSONA_JURIDICA
    # Modo Screening Express (Clientes Prospectos / BDM): VoBo comercial
    # preliminar con datos mínimos, mientras aún no existe la estructura
    # completa de administración exigida en el Onboarding Formal SARLAFT.
    es_prospecto = bool(datos_master.get("modo_prospecto", False))

    path_adamo = resolver_ruta_logo("Logo Adamo general")
    path_holdings = resolver_ruta_logo("Logo Holdings")

    pdf = ComplianceMaestroPDF(logo_adamo=path_adamo, logo_holdings=path_holdings, tipo_persona=tipo_persona)

    # Metadatos: cadena de custodia mínima del documento probatorio.
    pdf.set_title(f"Expediente de Debida Diligencia - {datos_master.get('radicado_caso', 'S/N')}")
    pdf.set_author("HBPO Compliance Hub")
    pdf.set_creator("PayShield & Compliance Hub")
    pdf.set_subject("Verificación SARLAFT / Screening en listas de control")

    pdf.alias_nb_pages()
    pdf.add_page()

    # ══════════════════════════════════════════════════════════════════
    # HELPERS DE RENDER
    # ══════════════════════════════════════════════════════════════════

    def render_subseccion_moderna(titulo):
        pdf.asegurar_espacio(14)
        pdf.set_text_color(*COLOR_PRIMARY)
        pdf.set_font("Helvetica", "B", 10)
        current_y = pdf.get_y()
        pdf.set_draw_color(*COLOR_ACCENT)
        pdf.set_line_width(0.7)
        pdf.line(PAGE_X0, current_y + 1.2, PAGE_X0, current_y + 5.2)
        pdf.cell(4, 6, "")
        pdf.cell(0, 6, _s(titulo).upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

    def render_banner_prospecto():
        """
        Barra de advertencia comercial para el Modo Screening Express. Un
        VoBo de prospecto (datos mínimos, sin Rep. Legal/Accionista
        verificados) nunca debe poder confundirse visualmente con el
        Onboarding Formal SARLAFT completo.
        """
        texto_banner = "CERTIFICADO PRELIMINAR COMERCIAL (MODO PROSPECTO) - NO REEMPLAZA EL ONBOARDING SARLAFT DEFINITIVO"
        banner_h = 8.0
        y0 = pdf.get_y()
        pal = SEMAFORO["revision"]
        pdf.set_fill_color(*pal["bg"])
        pdf.set_draw_color(255, 193, 7)
        pdf.set_line_width(0.4)
        pdf.rect(PAGE_X0, y0, PAGE_W, banner_h, style="FD")
        pdf.set_xy(PAGE_X0, y0 + 1.8)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(*pal["texto"])
        pdf.cell(PAGE_W, 4.5, texto_banner, align="C")
        pdf.set_y(y0 + banner_h + 4)

    def render_resumen_screening(entidades):
        """Barra de totales: qué se evaluó y qué queda pendiente, de un vistazo.

        Sin esto el lector tenía que contar tarjetas para saber si el
        expediente estaba completo.
        """
        total = len(entidades)
        con_coincidencia = sum(1 for e in entidades if _clasificar_entidad(e, es_prospecto)["coincidencias"])
        pendientes = sum(1 for e in entidades if _clasificar_entidad(e, es_prospecto)["pendiente"])

        h = 10.0
        pdf.asegurar_espacio(h + 4)
        y0 = pdf.get_y()
        pdf.set_fill_color(*COLOR_BG_GRID)
        pdf.set_draw_color(*COLOR_LINE_TENUE)
        pdf.set_line_width(0.2)
        pdf.rect(PAGE_X0, y0, PAGE_W, h, style="FD")

        bloques = [
            ("VINCULADOS EVALUADOS", str(total), COLOR_PRIMARY),
            ("CON COINCIDENCIAS EN LISTAS", str(con_coincidencia),
             SEMAFORO["alerta"]["texto"] if con_coincidencia else COLOR_TEXT_BODY),
            ("PENDIENTES DE VALIDACIÓN", str(pendientes),
             SEMAFORO["revision"]["texto"] if pendientes else COLOR_TEXT_BODY),
        ]
        ancho_bloque = PAGE_W / 3.0
        for i, (etiqueta, valor, color) in enumerate(bloques):
            x = PAGE_X0 + i * ancho_bloque
            if i:
                pdf.set_draw_color(*COLOR_LINE_TENUE)
                pdf.set_line_width(0.15)
                pdf.line(x, y0 + 2.0, x, y0 + h - 2.0)
            pdf.set_xy(x + 4, y0 + 2.2)
            pdf.set_font("Helvetica", "B", 6.0)
            pdf.set_text_color(*COLOR_TEXT_MUTED)
            pdf.cell(ancho_bloque - 8, 2.8, etiqueta, new_x=XPos.LEFT, new_y=YPos.NEXT)
            pdf.set_xy(x + 4, y0 + 5.2)
            pdf.set_font("Helvetica", "B", 9.5)
            pdf.set_text_color(*color)
            pdf.cell(ancho_bloque - 8, 4.2, valor)

        pdf.set_y(y0 + h + 4)

    def render_infolaft_snippet(ent: dict, datos_master: dict):
        """Microtarjeta de UNA entidad evaluada.

        Jerarquía de lectura: (1) franja de color + badge = veredicto,
        (2) rol y nombre = a quién se evaluó, (3) grilla = con qué datos
        se sustenta, (4) pie = de qué archivo salió y, si algo falló, por
        qué. Antes la tarjeta solo repetía "No detectado" tres veces sin
        explicar nada.
        """
        estado = _clasificar_entidad(ent, es_prospecto)
        rol = _norm(ent.get("rol_interno", "")) or "VINCULADO EVALUADO"
        nombre, nombre_del_formulario = _resolver_nombre_entidad(ent, datos_master)

        identificacion = _fmt(ent.get("identificacion"))
        radicado = _fmt(ent.get("radicado"))
        if "SIN CONSULTA" in _norm(radicado):
            radicado = SIN_DATO   # el motivo del pie ya lo explica
        fecha_consulta = _fmt(ent.get("fecha_consulta"))
        # Fallback de fecha si el objeto no la trae individualmente. Se
        # aplica solo a entidades que SI fueron consultadas: una entidad
        # declarada sin consulta, o un PDF ilegible, no pueden exhibir una
        # fecha de consulta que nunca existio.
        hubo_consulta = radicado != SIN_DATO and not ent.get("error_lectura")
        if fecha_consulta == SIN_DATO and hubo_consulta and datos_master.get("fecha"):
            fecha_consulta = str(datos_master.get("fecha"))[:10]
        resultados = str(ent.get("resultados", "0")).strip() or "0"
        intensificada = "SI" if _norm(ent.get("intensificada", "NO")) == "SI" else "NO"
        listas_consultadas = _fmt(ent.get("listas_consultadas"))
        analista = _fmt(ent.get("consultado_por"), "")
        fuente = _fmt(ent.get("fuente_archivo"), "")

        # Notas del pie: motivo de la alerta + trazabilidad del nombre.
        notas = []
        if estado.get("motivo"):
            notas.append(str(estado["motivo"]).rstrip(" :"))
        if nombre_del_formulario:
            notas.append("Nombre tomado del formulario: el certificado no permitió extraerlo.")
        if ent.get("radicado_via_nombre_archivo"):
            notas.append("No. de consulta recuperado del nombre del archivo.")

        H_CABECERA = 13.6
        H_GRILLA = 9.6
        H_PIE = 4.0
        H_NOTA = 3.6
        alto = H_CABECERA + H_GRILLA + H_PIE + (len(notas) * H_NOTA) + 3.0

        pdf.asegurar_espacio(alto + 3)
        y0 = pdf.get_y()

        # Cuerpo de la tarjeta
        pdf.set_fill_color(*COLOR_BG_CARD)
        pdf.set_draw_color(*COLOR_LINE_TENUE)
        pdf.set_line_width(0.2)
        pdf.rect(PAGE_X0, y0, PAGE_W, alto, style="FD")

        # Franja lateral de estado: permite escanear la página entera sin leer
        pdf.set_fill_color(*estado["franja"])
        pdf.set_draw_color(*estado["franja"])
        pdf.rect(PAGE_X0, y0, 1.8, alto, style="FD")

        # ── Badge (derecha, ancho ajustado al texto) ──
        pdf.set_font("Helvetica", "B", 6.8)
        badge_w = min(78.0, max(42.0, pdf.get_string_width(estado["etiqueta"]) + 7))
        badge_x = PAGE_X1 - 3.5 - badge_w
        pdf.set_fill_color(*estado["bg"])
        pdf.set_draw_color(*estado["borde"])
        pdf.set_line_width(0.2)
        pdf.rect(badge_x, y0 + 3.4, badge_w, 6.0, style="FD")
        pdf.set_xy(badge_x, y0 + 4.6)
        pdf.set_text_color(*estado["texto"])
        pdf.cell(badge_w, 3.6, estado["etiqueta"], align="C")

        # ── Rol + nombre (izquierda) ──
        ancho_nombre = badge_x - (PAGE_X0 + 5.5) - 4
        pdf.set_xy(PAGE_X0 + 5.5, y0 + 3.2)
        pdf.set_font("Helvetica", "B", 6.2)
        pdf.set_text_color(*COLOR_TEXT_MUTED)
        pdf.cell(ancho_nombre, 2.8, pdf.recortar(rol, ancho_nombre), new_x=XPos.LEFT, new_y=YPos.NEXT)

        pdf.set_xy(PAGE_X0 + 5.5, y0 + 6.4)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*COLOR_TEXT_MAIN)
        pdf.cell(ancho_nombre, 5.0, pdf.recortar(nombre, ancho_nombre))

        # ── Divisor ──
        pdf.set_draw_color(*COLOR_LINE_TENUE)
        pdf.set_line_width(0.15)
        pdf.line(PAGE_X0 + 5.5, y0 + H_CABECERA, PAGE_X1 - 3.5, y0 + H_CABECERA)

        # ── Grilla de metadatos ──
        columnas = [
            ("IDENTIFICACIÓN", identificacion, COLOR_TEXT_BODY, "B" if identificacion != SIN_DATO else ""),
            ("No. DE CONSULTA", radicado, COLOR_TEXT_BODY, "B" if radicado != SIN_DATO else ""),
            ("FECHA DE CONSULTA", fecha_consulta, COLOR_TEXT_BODY, ""),
            # Cuántas listas de control barrió el proveedor: es la medida
            # del alcance del screening y el reporte sí la trae (316).
            ("LISTAS CONSULTADAS", listas_consultadas, COLOR_TEXT_BODY, ""),
            ("COINCIDENCIAS", resultados,
             SEMAFORO["alerta"]["texto"] if estado.get("coincidencias") else COLOR_TEXT_BODY, "B"),
            ("MONITOREO GAFI", intensificada,
             SEMAFORO["alerta"]["texto"] if intensificada == "SI" else COLOR_TEXT_BODY, "B"),
        ]
        # Radicados cross-border ("BDM-ARIMETRIX-2026-EXT1", 39.1mm a 8.2pt
        # Bold) seguian truncando en el ancho anterior (36.0). No. DE
        # CONSULTA sube a 44.0; el resto se reparte por su peor caso real
        # (ver medicion de anchos) para que la fila siga sumando 171mm.
        anchos = [26.0, 44.0, 32.0, 27.0, 20.0, 22.0]   # suma 171 = ancho interior
        x = PAGE_X0 + 5.5
        y_lbl = y0 + H_CABECERA + 2.4
        for (etiqueta, valor, color, estilo), w in zip(columnas, anchos):
            pdf.set_xy(x, y_lbl)
            pdf.set_font("Helvetica", "B", 5.8)
            pdf.set_text_color(*COLOR_TEXT_MUTED)
            pdf.cell(w, 2.6, pdf.recortar(etiqueta, w - 1.5), new_x=XPos.LEFT, new_y=YPos.NEXT)
            pdf.set_xy(x, y_lbl + 3.0)
            pdf.set_font("Helvetica", estilo, 8.2)
            pdf.set_text_color(*color)
            pdf.cell(w, 3.8, pdf.recortar(valor, w - 1.5))
            x += w

        # ── Pie: archivo fuente y notas ──
        y_pie = y0 + H_CABECERA + H_GRILLA + 1.4
        pdf.set_xy(PAGE_X0 + 5.5, y_pie)
        pdf.set_font("Helvetica", "I", 6.4)
        pdf.set_text_color(*COLOR_TEXT_MUTED)
        texto_fuente = f"Fuente documental: {fuente}" if fuente else "Fuente documental: no registrada"
        if analista:
            texto_fuente += f"   |   Consulta ejecutada por: {analista}"
        pdf.cell(PAGE_W - 10, 3.2, pdf.recortar(texto_fuente, PAGE_W - 12))

        for i, nota in enumerate(notas):
            pdf.set_xy(PAGE_X0 + 5.5, y_pie + 3.4 + i * H_NOTA)
            pdf.set_font("Helvetica", "I", 6.4)
            pdf.set_text_color(*estado["texto"])
            pdf.cell(PAGE_W - 10, 3.2, pdf.recortar(_s(nota), PAGE_W - 12))

        pdf.set_y(y0 + alto + 3.0)

    # ─── SANITIZACIÓN ESTRUCTURAL DE DATOS ───
    # [FIX-08] Todo por .get(): una clave faltante ya no aborta el expediente.
    s_radicado  = _s(datos_master.get('radicado_caso', 'N/D'))
    s_direccion = _s(datos_master.get('direccion', 'No Registrada'))
    s_telefono  = _s(datos_master.get('telefono', 'No Registrado'))
    s_correo    = _s(datos_master.get('correo_contacto', 'No Registrado'))
    s_estado    = _s(datos_master.get('estado_global', 'REQUIERE REVISIÓN MANUAL'))
    s_dictamen  = _s(datos_master.get('dictamen_motivo', ''))
    s_rues      = _s(datos_master.get('rues_noticias_raw', ''))
    s_fecha     = _s(datos_master.get('fecha', ''))

    # Campos exclusivos de Persona Jurídica.
    s_empresa   = _s(datos_master.get('empresa_principal', ''))
    s_nit       = _s(datos_master.get('nit_principal', 'N/D'))
    s_jurisdic  = _s(datos_master.get('jurisdiccion', 'N/D'))
    s_web       = _s(datos_master.get('sitio_web', 'N/D'))
    s_rep_nom   = _s(datos_master.get('rep_legal_nom', 'N/D'))
    s_acc_nom   = _s(datos_master.get('accionista_nom', 'N/D'))

    # Campos exclusivos de Persona Natural.
    s_nombre_completo = _s(datos_master.get('nombre_completo', ''))
    s_num_doc         = _s(datos_master.get('numero_documento', 'N/D'))
    s_rol_relacion    = _s(datos_master.get('rol_relacion', 'N/D'))
    s_pais_residencia = _s(datos_master.get('pais_residencia', 'N/D'))

    # ─── BANNER DE MODO PROSPECTO (si aplica) ───
    if es_prospecto:
        render_banner_prospecto()

    # ─── ENCABEZADO ESTILO DASHBOARD ───
    nombre_principal = s_empresa if es_juridica else s_nombre_completo
    if not nombre_principal.strip():
        nombre_principal = "ENTIDAD NO IDENTIFICADA"
    if es_juridica:
        linea_identificacion = f"Identificación Comercial: {s_nit}   |   ID Expediente: {s_radicado}"
    else:
        linea_identificacion = f"Documento: {s_num_doc}   |   Calidad: {s_rol_relacion}   |   ID Expediente: {s_radicado}"

    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 8, pdf.recortar(nombre_principal.upper(), PAGE_W), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(0, 4, linea_identificacion, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)

    # 🗂️ ─── SECCIÓN 1: IDENTIFICACIÓN CORPORATIVA Y DE CONTACTO ───
    render_subseccion_moderna("1. Identificación de la Entidad Evaluada")

    if es_juridica:
        placeholder_no_exigido = "No Requerido en Prospecto"
        rep_legal_val = s_rep_nom if (s_rep_nom.strip() and s_rep_nom != "N/D") else (placeholder_no_exigido if es_prospecto else s_rep_nom)
        accionista_val = s_acc_nom if (s_acc_nom.strip() and s_acc_nom != "N/D") else (placeholder_no_exigido if es_prospecto else s_acc_nom)

        row1_der_label, row1_der_val = "JURISDICCIÓN COMERCIAL", s_jurisdic
        row2_izq_label, row2_izq_val = "REPRESENTANTE LEGAL", rep_legal_val
        row2_der_label, row2_der_val = "SOCIO O ACCIONISTA PRINCIPAL", accionista_val
        row4_izq_label, row4_izq_val = "CANAL DIGITAL / SITIO WEB", s_web
    else:
        row1_der_label, row1_der_val = "PAÍS DE RESIDENCIA / NACIONALIDAD", s_pais_residencia
        row2_izq_label, row2_izq_val = "NÚMERO DE DOCUMENTO", s_num_doc
        row2_der_label, row2_der_val = "CALIDAD / ROL EVALUADO", s_rol_relacion
        row4_izq_label, row4_izq_val = "TIPO DE EXPEDIENTE", "INDIVIDUAL - PERSONA NATURAL"

    COL_IZQ_X   = 19
    COL_DER_X   = 109
    ANCHO_COL   = 82
    H_LABEL     = 3.0
    H_VALUE     = 4.2
    H_GAP       = 2.5
    PADDING_TOP = 3.5
    PADDING_BOT = 3.0

    # [FIX-07] Conteo real de líneas (respeta el corte por palabra).
    pdf.set_font("Helvetica", "", 8.5)
    lineas_direccion = pdf.contar_lineas(ANCHO_COL, s_direccion)
    h_row1 = H_LABEL + (lineas_direccion * H_VALUE)
    h_row2 = h_row3 = h_row4 = H_LABEL + H_VALUE
    altura_bento_dinamica = PADDING_TOP + h_row1 + H_GAP + h_row2 + H_GAP + h_row3 + H_GAP + h_row4 + PADDING_BOT

    pdf.asegurar_espacio(altura_bento_dinamica)
    start_y = pdf.get_y()

    pdf.set_fill_color(*COLOR_BG_GRID)
    pdf.set_draw_color(*COLOR_LINE_TENUE)
    pdf.set_line_width(0.2)
    pdf.rect(PAGE_X0, start_y, PAGE_W, altura_bento_dinamica, style="FD")

    y_row1 = start_y + PADDING_TOP
    y_row2 = y_row1 + h_row1 + H_GAP
    y_row3 = y_row2 + h_row2 + H_GAP
    y_row4 = y_row3 + h_row3 + H_GAP

    pdf.set_draw_color(*COLOR_LINE_TENUE)
    pdf.set_line_width(0.15)
    for y_div in (y_row2, y_row3, y_row4):
        pdf.line(COL_IZQ_X, y_div - H_GAP / 2, 191, y_div - H_GAP / 2)

    def _celda(x, y, etiqueta, valor, negrita_valor=False, color_valor=COLOR_TEXT_BODY):
        pdf.set_xy(x, y)
        pdf.set_font("Helvetica", "B", 6.5)
        pdf.set_text_color(*COLOR_TEXT_MUTED)
        pdf.cell(ANCHO_COL, H_LABEL, etiqueta, new_x=XPos.LEFT, new_y=YPos.NEXT)
        pdf.set_xy(x, y + H_LABEL)
        pdf.set_font("Helvetica", "B" if negrita_valor else "", 8.5)
        pdf.set_text_color(*color_valor)
        pdf.cell(ANCHO_COL, H_VALUE, pdf.recortar(valor, ANCHO_COL))

    # Fila 1
    pdf.set_xy(COL_IZQ_X, y_row1)
    pdf.set_font("Helvetica", "B", 6.5)
    pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(ANCHO_COL, H_LABEL, "DIRECCIÓN FISCAL", new_x=XPos.LEFT, new_y=YPos.NEXT)
    pdf.set_x(COL_IZQ_X)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.multi_cell(ANCHO_COL, H_VALUE, s_direccion)
    _celda(COL_DER_X, y_row1, row1_der_label, row1_der_val)

    # Filas 2 a 4
    _celda(COL_IZQ_X, y_row2, row2_izq_label, row2_izq_val)
    _celda(COL_DER_X, y_row2, row2_der_label, row2_der_val)
    _celda(COL_IZQ_X, y_row3, "TELÉFONO DE CONTACTO", s_telefono)
    _celda(COL_DER_X, y_row3, "CORREO ELECTRÓNICO DE CONTACTO", s_correo)
    _celda(COL_IZQ_X, y_row4, row4_izq_label, row4_izq_val)
    _celda(COL_DER_X, y_row4, "IDENTIFICADOR ÚNICO DE EXPEDIENTE", s_radicado,
           negrita_valor=True, color_valor=COLOR_PRIMARY)

    pdf.set_y(start_y + altura_bento_dinamica)
    pdf.ln(6)

    # 🗂️ ─── SECCIÓN 2: EVIDENCIAS ANALIZADAS Y SCREENING LAFT ───
    render_subseccion_moderna("2. Evidencias Analizadas y Screening LAFT")

    entidades_evidencia = [
        e for e in datos_master.get('entidades_processed', datos_master.get('entidades_procesadas', []) or [])
        if isinstance(e, dict)
    ]

    if entidades_evidencia:
        render_resumen_screening(entidades_evidencia)
        for ent in entidades_evidencia:
            render_infolaft_snippet(ent, datos_master)
    else:
        # Antes la sección quedaba simplemente vacía, indistinguible de un
        # error de render. Ahora deja constancia explícita.
        pdf.asegurar_espacio(14)
        y0 = pdf.get_y()
        pal = SEMAFORO["revision"]
        pdf.set_fill_color(*pal["bg"])
        pdf.set_draw_color(*pal["borde"])
        pdf.set_line_width(0.2)
        pdf.rect(PAGE_X0, y0, PAGE_W, 11, style="FD")
        pdf.set_xy(PAGE_X0 + 4, y0 + 3.4)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*pal["texto"])
        pdf.cell(PAGE_W - 8, 4.2,
                 "NO SE ADJUNTARON CERTIFICADOS DE SCREENING PARA ESTE EXPEDIENTE.",
                 new_x=XPos.LEFT, new_y=YPos.NEXT)
        pdf.set_x(PAGE_X0 + 4)
        pdf.set_font("Helvetica", "I", 7)
        pdf.cell(PAGE_W - 8, 3.4, "El expediente no puede considerarse completo sin la consulta en listas de control.")
        pdf.set_y(y0 + 11 + 3)

    # ── Anexos de Soporte Adjuntos (SIN badge de evaluación LAFT) ──────
    anexos_soporte = datos_master.get('anexos_soporte', []) or []
    if anexos_soporte:
        pdf.asegurar_espacio(16)
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 7.0)
        pdf.set_text_color(*COLOR_TEXT_MUTED)
        pdf.cell(0, 4.5, "ANEXOS DE SOPORTE ADJUNTOS", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "I", 6.4)
        pdf.cell(0, 3.4,
                 "Evidencia documental de respaldo. No constituye consulta en listas de control ni sustituye el screening.",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*COLOR_TEXT_BODY)
        for anexo in anexos_soporte:
            pdf.asegurar_espacio(6)
            linea = f"- {anexo.get('nombre', 'N/D')} (adjuntado: {anexo.get('fecha', 'N/D')})"
            pdf.cell(0, 4.2, pdf.recortar(_s(linea), PAGE_W), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(6)

    # 🗂️ ─── SECCIÓN 3: CONCEPTO TÉCNICO Y DECLARACIÓN DE CUMPLIMIENTO ───
    render_subseccion_moderna("3. Concepto Técnico de Cumplimiento")

    # Tres veredictos posibles — ver estado_global en screening_ui.py:
    #   "APROBADO S/ANOMALÍAS"            -> screening completo, sin coincidencias
    #   "REQUIERE REVISIÓN MANUAL"        -> uno o más PDF no se pudieron leer
    #   "REQUIERE REVISIÓN INTENSIFICADA" -> coincidencia real en listas / GAFI
    estado_norm = _norm(s_estado)
    es_aprobado = "APROBADO" in estado_norm
    es_revision_manual = "MANUAL" in estado_norm

    # Coherencia dura: si alguna tarjeta de la Sección 2 quedó en ámbar o
    # rojo, el dictamen NO puede imprimirse como aprobado aunque
    # estado_global llegue mal calculado desde la UI.
    clasificaciones = [_clasificar_entidad(e, es_prospecto) for e in entidades_evidencia]
    hay_alerta = any(c["clave"] == "alerta" for c in clasificaciones)
    hay_pendiente = any(c["pendiente"] for c in clasificaciones)
    if hay_alerta:
        es_aprobado, es_revision_manual = False, False
    elif hay_pendiente and es_aprobado:
        es_aprobado, es_revision_manual = False, True

    if es_aprobado:
        estado_str, categoria_str, pal = "CONFORME - SIN COINCIDENCIAS", "RIESGO BAJO", SEMAFORO["limpio"]
    elif es_revision_manual:
        estado_str, categoria_str, pal = "PENDIENTE - LECTURA NO CONFIABLE", "REQUIERE VALIDACIÓN MANUAL", SEMAFORO["revision"]
    else:
        estado_str, categoria_str, pal = "NO CONFORME - ALERTA LAFT", "RIESGO ALTO", SEMAFORO["alerta"]

    badge_bg, badge_border, badge_text = pal["bg"], pal["borde"], pal["texto"]

    S3_IZQ, S3_DER, S3_W = 19, 109, 82
    S3_H_LBL, S3_H_BDG, S3_GAP, S3_PAD_T, S3_PAD_B = 3.0, 6.0, 5.5, 4.5, 4.5

    if not s_dictamen.strip():
        s_dictamen = ("No se registró sustento técnico del Oficial de Cumplimiento para este expediente.")

    pdf.set_font("Helvetica", "I", 8)
    h_dictamen = pdf.contar_lineas(172, s_dictamen) * 4.2
    altura_bento_s3 = S3_PAD_T + S3_H_LBL + 1.2 + S3_H_BDG + S3_GAP + S3_H_LBL + 1.2 + h_dictamen + S3_PAD_B

    pdf.asegurar_espacio(altura_bento_s3)
    start_y = pdf.get_y()

    pdf.set_fill_color(*COLOR_BG_GRID)
    pdf.set_draw_color(*COLOR_LINE_TENUE)
    pdf.set_line_width(0.2)
    pdf.rect(PAGE_X0, start_y, PAGE_W, altura_bento_s3, style="FD")

    y_r1_lbl = start_y + S3_PAD_T
    y_r1_bdg = y_r1_lbl + S3_H_LBL + 1.2
    y_divisor = y_r1_bdg + S3_H_BDG + (S3_GAP / 2.0)
    y_r2_lbl = y_divisor + (S3_GAP / 2.0)
    y_r2_val = y_r2_lbl + S3_H_LBL + 1.2

    pdf.set_draw_color(*COLOR_LINE_TENUE)
    pdf.set_line_width(0.15)
    pdf.line(S3_IZQ, y_divisor, 191, y_divisor)

    for x_col, etiqueta, valor in (
        (S3_IZQ, "RESULTADO FORMAL DE EVALUACIÓN LAFT", estado_str),
        (S3_DER, "CATEGORÍA DE RIESGO FINAL", categoria_str),
    ):
        pdf.set_xy(x_col, y_r1_lbl)
        pdf.set_font("Helvetica", "B", 6.5)
        pdf.set_text_color(*COLOR_TEXT_MUTED)
        pdf.cell(S3_W, S3_H_LBL, etiqueta)

        pdf.set_fill_color(*badge_bg)
        pdf.set_draw_color(*badge_border)
        pdf.set_line_width(0.2)
        pdf.rect(x_col, y_r1_bdg, 74, S3_H_BDG, style="FD")

        pdf.set_xy(x_col + 3, y_r1_bdg + 1.0)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(*badge_text)
        pdf.cell(68, 4.2, valor)

    pdf.set_xy(S3_IZQ, y_r2_lbl)
    pdf.set_font("Helvetica", "B", 6.5)
    pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(172, S3_H_LBL, "SUSTENTO TÉCNICO DEL OFICIAL DE CUMPLIMIENTO",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_xy(S3_IZQ, y_r2_val)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*COLOR_TEXT_BODY)
    pdf.multi_cell(172, 4.2, s_dictamen)

    pdf.set_y(start_y + altura_bento_s3)
    pdf.ln(6)

    # 🗂️ ─── SECCIÓN 4: ANÁLISIS DE FUENTES ABIERTAS COMPLEMENTARIO ───
    render_subseccion_moderna("4. Análisis de Contexto y Registro Público")

    # [FIX-05] Sin datos NO es lo mismo que sin hallazgos.
    hay_analisis_rues = bool(s_rues.strip())
    contenido_rues = s_rues.strip() if hay_analisis_rues else (
        "No se registró análisis de fuentes abiertas ni de registro mercantil para este expediente. "
        "La ausencia de información en esta sección no debe interpretarse como ausencia de hallazgos."
    )

    pdf.set_font("Helvetica", "", 8.5)
    h_rues = pdf.contar_lineas(172, contenido_rues) * 4.2
    altura_bento_rues = 4.5 + 3.0 + 1.5 + h_rues + 4.5

    pdf.asegurar_espacio(altura_bento_rues)
    start_y = pdf.get_y()

    pdf.set_fill_color(*COLOR_BG_GRID)
    pdf.set_draw_color(*COLOR_LINE_TENUE)
    pdf.set_line_width(0.2)
    pdf.rect(PAGE_X0, start_y, PAGE_W, altura_bento_rues, style="FD")

    pdf.set_xy(19, start_y + 4.5)
    pdf.set_font("Helvetica", "B", 6.5)
    pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(172, 3.0, "ANÁLISIS DE ADVERSE MEDIA Y VALIDACIÓN EN REGISTRO MERCANTIL",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_xy(19, start_y + 4.5 + 3.0 + 1.5)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*COLOR_TEXT_BODY if hay_analisis_rues else COLOR_TEXT_MUTED)
    pdf.multi_cell(172, 4.2, contenido_rues)

    pdf.set_y(start_y + altura_bento_rues)

    # Sello de seguridad
    # [FIX-04] En Persona Natural el identificador es el documento, no el NIT.
    identificador_sello = s_nit if es_juridica else s_num_doc
    identificador_sello = re.sub(r"\W", "", identificador_sello) or "SIN-ID"
    pdf.asegurar_espacio(12)
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*COLOR_TEXT_MUTED)
    sello_fecha = f"{s_fecha} COT" if s_fecha.strip() else "No registrada"
    pdf.cell(0, 3.5, f"Estampa de Tiempo de Evaluación: {sello_fecha}",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 3.5,
             f"Código de Verificación del Reporte: HBPO-COMPLIANCE-{identificador_sello}-{s_radicado.upper()}",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # 🗂️ ─── ANEXO: REGISTRO DE EVIDENCIAS DIGITALES (IMÁGENES) ───
    imagenes_evidencia = datos_master.get("evidencias_imagenes", []) or []

    if imagenes_evidencia:
        pdf.add_page()

        pdf.set_text_color(*COLOR_PRIMARY)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "ANEXO: REGISTRO DE EVIDENCIAS DIGITALES",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_draw_color(*COLOR_PRIMARY)
        pdf.set_line_width(0.4)
        pdf.line(PAGE_X0, pdf.get_y() + 1, PAGE_X1, pdf.get_y() + 1)
        pdf.ln(6)

        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*COLOR_TEXT_BODY)
        pdf.multi_cell(0, 4.2,
                       "Como respaldo del proceso de debida diligencia y validación en fuentes abiertas, "
                       "se adjuntan de manera íntegra las capturas de pantalla tomadas de los portales de "
                       "verificación pública:")
        pdf.ln(4)

        for idx, img_bytes in enumerate(imagenes_evidencia):
            # Defensa en profundidad: esta lista debería traer solo imágenes
            # (los PDF de soporte se desvían al pipeline de screening en
            # callback_ejecutar_compilacion). Si llega un PDF, se informa.
            if not img_bytes:
                continue
            if bytes(img_bytes[:4]) == b"%PDF":
                pdf.set_font("Helvetica", "I", 8.0)
                pdf.set_text_color(*COLOR_TEXT_MUTED)
                pdf.cell(0, 5, _s(f"[Evidencia {idx + 1}: documento PDF adjunto - analizado en la Sección 2, "
                                  f"no se renderiza como imagen]"),
                         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(4)
                continue

            try:
                # [FIX-09] En memoria: las capturas contienen datos KYC y ya
                # no quedan escritas en el %TEMP% del servidor.
                with PILImage.open(io.BytesIO(img_bytes)) as img:
                    img.load()
                    img_w, img_h = img.size
                    if img.mode not in ("RGB", "RGBA", "L", "P"):
                        img = img.convert("RGB")

                    aspect = (img_h / img_w) if img_w else 1.0

                    max_width = 160.0
                    max_height = 145.0

                    render_w = max_width
                    render_h = max_width * aspect
                    if render_h > max_height:
                        render_h = max_height
                        render_w = max_height / aspect
                    # Una captura muy vertical se reducía a una tira ilegible:
                    # se respeta un ancho mínimo legible y se deja crecer el
                    # alto hasta el máximo de página.
                    if render_w < 70.0:
                        render_w = 70.0
                        render_h = min(max_height, render_w * aspect)

                    pos_x = PAGE_X0 + (PAGE_W - render_w) / 2.0

                    if pdf.get_y() + render_h + 12 > LIMITE_Y:
                        pdf.add_page()

                    pdf.set_font("Helvetica", "B", 8.0)
                    pdf.set_text_color(*COLOR_TEXT_MUTED)
                    pdf.cell(0, 5, f"EVIDENCIA DIGITAL NO. {idx + 1} - SOPORTE DE CONSULTA",
                             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    pdf.ln(2)

                    pdf.image(img, x=pos_x, y=pdf.get_y(), w=render_w, h=render_h)
                    pdf.set_y(pdf.get_y() + render_h + 8)

            except Exception:
                logger.exception("No se pudo renderizar la evidencia %s", idx + 1)
                pdf.set_font("Helvetica", "I", 8.0)
                pdf.set_text_color(*SEMAFORO["alerta"]["texto"])
                pdf.cell(0, 5, f"[Evidencia {idx + 1} no renderizable: formato de imagen no soportado. "
                               f"El archivo original se conserva adjunto al expediente.]",
                         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(4)

    # Retorno seguro
    out = pdf.output()
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    return str(out).encode("latin-1", "ignore")


# ══════════════════════════════════════════════════════════════════════
# FUSIÓN DEL EXPEDIENTE
# ══════════════════════════════════════════════════════════════════════

def compilar_expediente_completo(bytes_base: bytes, infolaft_bytes_list: list, nombres: list = None) -> bytes:
    """Fusiona el expediente de salida con las evidencias PDF de Infolaft.

    [FIX-11] Una evidencia que falla al fusionar ya no desaparece en
    silencio: se registra en el log con su nombre para que el Oficial de
    Cumplimiento pueda reclamarla. `nombres` es opcional y solo se usa para
    esa traza.
    """
    writer = pypdf.PdfWriter()
    fallidos = []

    reader_base = pypdf.PdfReader(io.BytesIO(bytes_base))
    for page in reader_base.pages:
        writer.add_page(page)

    for i, b in enumerate(infolaft_bytes_list or []):
        etiqueta = (nombres[i] if nombres and i < len(nombres) else f"evidencia_{i + 1}")
        if not b:
            fallidos.append(etiqueta)
            continue
        try:
            reader_evi = pypdf.PdfReader(io.BytesIO(b))
            if getattr(reader_evi, "is_encrypted", False):
                reader_evi.decrypt("")
            for page in reader_evi.pages:
                writer.add_page(page)
        except Exception:
            logger.exception("No se pudo anexar la evidencia '%s' al expediente", etiqueta)
            fallidos.append(etiqueta)
            continue

    if fallidos:
        logger.warning(
            "Expediente compilado SIN %d evidencia(s): %s", len(fallidos), ", ".join(fallidos)
        )

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
