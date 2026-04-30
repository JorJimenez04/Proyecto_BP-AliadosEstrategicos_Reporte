import psycopg2

RAILWAY_URL = "postgresql://postgres:cBJTDNMbEBzCAncQuZUxlnkdoGJFfJsq@junction.proxy.rlwy.net:12345/railway"

SQL_STATEMENTS = [
    "UPDATE compliance_documentos SET carpeta = 'Procesos y Procedimientos' WHERE carpeta = 'Etica'",
    "ALTER TABLE compliance_documentos DROP CONSTRAINT IF EXISTS compliance_documentos_carpeta_check",
    "ALTER TABLE compliance_documentos ADD CONSTRAINT compliance_documentos_carpeta_check CHECK (carpeta IN ('Politicas','Manuales','Onboarding','Procesos y Procedimientos','Riesgos','Empresariales','Capacitacion'))",
]

for sslmode in ("disable", "require", "prefer"):
    try:
        print("Intentando sslmode=" + sslmode + "...")
        conn = psycopg2.connect(RAILWAY_URL, sslmode=sslmode, connect_timeout=15)
        conn.autocommit = False
        cur = conn.cursor()
        for stmt in SQL_STATEMENTS:
            cur.execute(stmt)
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM compliance_documentos WHERE carpeta = 'Procesos y Procedimientos'")
        new_count = cur.fetchone()[0]
        print("OK - Migracion aplicada (sslmode=" + sslmode + ")")
        print("Filas en 'Procesos y Procedimientos': " + str(new_count))
        conn.close()
        break
    except psycopg2.OperationalError as exc:
        print("  fallo sslmode=" + sslmode + ": " + str(exc).splitlines()[0][:100])
    except Exception as exc:
        import traceback; traceback.print_exc()
        break
