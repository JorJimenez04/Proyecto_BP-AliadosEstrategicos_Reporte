# test_pdf.py
import os
import sys

# Aseguramos que Python encuentre la carpeta 'app' desde la raíz
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.components.screening_ui import generar_pdf_base

def correr_render_pro():
    print("🚀 Iniciando renderizado PRO aislado...")

    datos_mock = {
        "empresa_principal": "JMNZ S.A.S.",
        "nit_principal": "901.002.210-3",
        "radicado_caso": "EXP-JMNZ-2026-005",
        "direccion": "AV CIRCUNVALAR 12-51 100",
        "jurisdiccion": "Pereira, Risaralda",
        "telefono": "3117293807",
        "sitio_web": "WWW.JMNZ.CO",
        "rep_legal_nom": "JORGE LEONARDO JIMÉNEZ R.",
        "rep_legal_id": "1029384",
        "accionista_nom": "JORGE LEONARDO JIMÉNEZ R.",
        "accionista_id": "1029384",
        "estado_global": "REQUIERE REVISIÓN INTENSIFICADA",
        "dictamen_motivo": "El análisis exhaustivo de listas restrictivas arrojó concordancia limpia para la firma principal. No obstante, se requiere auditoría sobre las personas naturales vinculadas.",
        "rues_noticias_raw": "Consulta RUES: Matrícula mercantil activa y al día. Prensa: Sin noticias adversas.",
        "fecha": "2026-07-14 10:20:00",
        "entidades_processed": [
            {
                "nombre": "JMNZ S.A.S.",
                "identificacion": "901.002.210-3",
                "rol_interno": "Empresa Principal",
                "radicado": "109283741",
                "resultados": "0",
                "intensificada": "NO"
            },
            {
                "nombre": "JORGE LEONARDO JIMÉNEZ R.",
                "identificacion": "1029384",
                "rol_interno": "Representante Legal",
                "radicado": "109283742",
                "resultados": "1",
                "intensificada": "SI"
            },
            # Dejamos este string de prueba para certificar que el blindaje anti-strings responde sin caerse
            "AUDITORÍA ADICIONAL DE RESPALDO"
        ]
    }

    # Ejecución del renderizador
    pdf_bytes = generar_pdf_base(datos_mock)

    archivo_salida = "review_screening.pdf"
    with open(archivo_salida, "wb") as f:
        f.write(pdf_bytes)
    
    print(f"✨ PDF generado con éxito en: './{archivo_salida}'")

if __name__ == "__main__":
    correr_render_pro()