import psycopg2, time
url = "postgresql://postgres:cBJTDNMbEBzCAncQuZUxlnkdoGJFfJsq@junction.proxy.rlwy.net:12345/railway"
for i in range(3):
    try:
        conn = psycopg2.connect(url, connect_timeout=20)
        cur = conn.cursor()
        cur.execute("SELECT carpeta, COUNT(*) as n FROM compliance_documentos GROUP BY carpeta ORDER BY carpeta")
        rows = cur.fetchall()
        print("=== Carpetas en Railway ===")
        for r in rows:
            print(f"  {r[0]}  ->  {r[1]} docs")
        conn.close()
        break
    except Exception as e:
        print(f"Intento {i+1}: {str(e)[:80]}")
        time.sleep(5)
