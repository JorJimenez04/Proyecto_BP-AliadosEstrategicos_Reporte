import os
import sys

# Inyectar la raíz del proyecto en el PYTHONPATH
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.utils.pdf_generator import generar_pdf_base

# Payload mock para probar el Modo Express
payload_test = {
    "empresa_principal": "ARIMETRIX S.A.S.",
    "nit_principal": "901.787.129-0",
    "radicado_caso": "BDM-ARIMETRIX-2026",
    "dictamen_motivo": "Tras efectuar la debida diligencia en listas vinculantes, no vinculantes y fuentes abiertas, no se identifican hallazgos ni alertas de riesgo que afecten la idoneidad de la contraparte.",
    "estado_global": "PRE-APROBADO S/ANOMALÍAS (MODO PROSPECTO)",
    "modo_prospecto": True,
    "entidades_processed": [
        {
            "nombre": "ARIMETRIX S.A.S.",
            "identificacion": "901.787.129-0",
            "radicado": "BDM-ARIMETRIX-2026",
            "resultados": "0",
            "intensificada": "NO",
            "rol_interno": "Empresa Principal (Colombia)"
        },
        {
            "nombre": "BUSINESS AND DIGITAL LAB LLC",
            "identificacion": "35-2938958",
            "radicado": "BDM-ARIMETRIX-2026-EXT1",
            "resultados": "0",
            "intensificada": "NO",
            "rol_interno": "Entidad Pagadora (EE. UU. / Exterior)"
        }
    ],
    "direccion": "Calle 100 # 15-20, Bogotá",
    "telefono": "3101234567",
    "jurisdiccion": "Colombia - Bogotá",
    "sitio_web": "www.arimetrix.co",
    "rep_legal_nom": "No Requerido en Prospecto",
    "rep_legal_id": "N/A",
    "accionista_nom": "No Requerido en Prospecto",
    "accionista_id": "N/A",
    "rues_noticias_raw": "Empresa legalmente constituida. Matrícula mercantil activa en Cámara de Comercio.",
    "evidencias_imagenes": [],
    "fecha": "2026-09-14 19:30:00",
    "analista": "jorge.jimenez"
}

print("⚡ Generando PDF de prueba desde la carpeta Tests...")
pdf_bytes = generar_pdf_base(payload_test)

# Guardar en la raíz para fácil acceso
output_file = os.path.join(ROOT_DIR, "test_output.pdf")
with open(output_file, "wb") as f:
    f.write(pdf_bytes)

print(f"✅ PDF generado exitosamente en: {output_file}")

# Abrir el PDF de manera automática
os.startfile(output_file)