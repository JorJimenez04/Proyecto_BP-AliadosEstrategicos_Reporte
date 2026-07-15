# test_pdf.py
from app.utils.pdf_generator import generar_pdf_base
from datetime import datetime

# Simulación de datos realistas para la prueba de diseño
datos_de_prueba = {
    "empresa_principal": "CM GRUPO TECNO SAS",
    "nit_principal": "901419688-5",
    "radicado_caso": "EXP-CMGRUPOTEC-001",
    "direccion": "CARRERA 31 # 51 - 74 OFICINA 501 BIS EDIFICIO TORRE MARDEL",
    "telefono": "3167405808",
    "jurisdiccion": "BUCARAMANGA, SANTANDER",
    "sitio_web": "WWW.WPAGOS.COM",
    "rep_legal_nom": "JUAN CAMILO MANTILLA MANTILLA",
    "rep_legal_id": "55266333555251",
    "accionista_nom": "JUAN CAMILO MANTILLA MANTILLA",
    "accionista_id": "55266333555251",
    "estado_global": "APROBADO S/ANOMALÍAS",
    "dictamen_motivo": "Se realiza análisis de riesgos LAFT sobre los vinculados. Se evidencia coincidencia negativa en listas restrictivas locales e internacionales. El cliente presenta un modelo operativo transaccional robusto y trazable.",
    "rues_noticias_raw": "Verifique el contenido y confiabilidad de este certificado, ingresando a WWW.CAMARADIRECTA.COM y digite el respectivo código, para que visualice la imagen generada al momento de su expedición.",
    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "entidades_processed": [
        {
            "rol_interno": "Empresa Principal",
            "nombre": "CM GRUPO TECNO SAS",
            "identificacion": "901419688-5",
            "radicado": "100259837",
            "resultados": "0",
            "intensificada": "NO"
        },
        {
            "rol_interno": "Representante Legal",
            "nombre": "JUAN CAMILO MANTILLA MANTILLA",
            "identificacion": "55266333555251",
            "radicado": "100259838",
            "resultados": "0",
            "intensificada": "NO"
        }
    ]
}

if __name__ == "__main__":
    print("⚡ Generando PDF de pruebas bajo la arquitectura desacoplada...")
    try:
        pdf_bytes = generar_pdf_base(datos_de_prueba)
        with open("review_screening.pdf", "wb") as f:
            f.write(pdf_bytes)
        print("✓ ¡Éxito! El PDF de prueba ha sido guardado como 'review_screening.pdf'.")
    except Exception as e:
        print(f"❌ Error en la compilación del PDF: {str(e)}")