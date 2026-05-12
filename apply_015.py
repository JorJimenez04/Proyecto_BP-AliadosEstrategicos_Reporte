"""
apply_015.py — Aplicar migraciones 021 y 022 del módulo Cripto Compliance

  Migración 021: Campos SoF / UoF / Conclusión en crypto_monitoreo
  Migración 022: Campo weekly_delta + tabla crypto_monitoreo_historial

Uso:
    # Con URL desde variable de entorno (recomendado):
    $env:RAILWAY_URL = "postgresql://user:pass@host:port/db"
    python apply_015.py

    # O editar RAILWAY_URL directamente en este script (solo local, no commitear)
"""

import os
import sys

# ── Conexión ──────────────────────────────────────────────────────────────────
# Prioridad: variable de entorno > valor hardcodeado (dejar vacío en el repo)
RAILWAY_URL = os.environ.get("RAILWAY_URL", "")

if not RAILWAY_URL:
    print("ERROR: Variable RAILWAY_URL no definida.")
    print("  Ejecuta:  $env:RAILWAY_URL = 'postgresql://user:pass@host:port/db'")
    sys.exit(1)


# ── SQL: Migración 021 — SoF / UoF / Conclusión ───────────────────────────────
SQL_021 = [
    # Source of Funds
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS sof_tipo_riesgo     TEXT",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS sof_indicador       TEXT",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS sof_naturaleza      TEXT",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS sof_profundidad     INTEGER",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS sof_cont_directa    NUMERIC(8,4)",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS sof_cont_indirecta  NUMERIC(8,4)",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS sof_cont_total      NUMERIC(8,4)",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS sof_score           INTEGER",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS sof_nivel           TEXT",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS sof_monto           NUMERIC(20,2)",
    # Use of Funds
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS uof_indicador       TEXT",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS uof_naturaleza      TEXT",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS uof_profundidad     INTEGER",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS uof_cont_directa    NUMERIC(8,4)",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS uof_cont_indirecta  NUMERIC(8,4)",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS uof_cont_total      NUMERIC(8,4)",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS uof_score           INTEGER",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS uof_nivel           TEXT",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS uof_monto           NUMERIC(20,2)",
    # Conclusión
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS analyst_observations TEXT",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS monitoring_analyst   TEXT",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS final_risk_score     NUMERIC(6,2)",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS final_risk_level     TEXT",
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS wallet_status        TEXT DEFAULT 'Active'",
    # Índices
    "CREATE INDEX IF NOT EXISTS idx_crypto_mon_sof_nivel        ON crypto_monitoreo (sof_nivel)",
    "CREATE INDEX IF NOT EXISTS idx_crypto_mon_uof_nivel        ON crypto_monitoreo (uof_nivel)",
    "CREATE INDEX IF NOT EXISTS idx_crypto_mon_final_level      ON crypto_monitoreo (final_risk_level)",
    "CREATE INDEX IF NOT EXISTS idx_crypto_mon_monitoring_analyst ON crypto_monitoreo (monitoring_analyst)",
]

# ── SQL: Migración 022 — weekly_delta + historial ────────────────────────────
SQL_022 = [
    # Campo de resumen semanal en tabla activa
    "ALTER TABLE crypto_monitoreo ADD COLUMN IF NOT EXISTS weekly_delta TEXT",
    # Tabla de snapshots históricos
    """
    CREATE TABLE IF NOT EXISTS crypto_monitoreo_historial (
        id                   SERIAL PRIMARY KEY,
        original_id          INTEGER NOT NULL,
        snapshot_date        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        wallet_address       TEXT NOT NULL,
        gl_score             INTEGER,
        riesgo_nivel         TEXT,
        sof_indicador        TEXT,
        sof_cont_total       NUMERIC(10,4),
        sof_score            INTEGER,
        sof_nivel            TEXT,
        sof_monto            NUMERIC(18,2),
        uof_indicador        TEXT,
        uof_cont_total       NUMERIC(10,4),
        uof_score            INTEGER,
        uof_nivel            TEXT,
        uof_monto            NUMERIC(18,2),
        final_risk_score     NUMERIC(6,2),
        final_risk_level     TEXT,
        weekly_delta         TEXT,
        analyst_observations TEXT,
        monitoring_analyst   TEXT,
        registrado_por       TEXT,
        pdf_report_url       TEXT,
        total_exposure       NUMERIC(18,2),
        exposure_currency    TEXT
    )
    """,
    # Índices del historial
    "CREATE INDEX IF NOT EXISTS idx_crypto_hist_wallet   ON crypto_monitoreo_historial (wallet_address)",
    "CREATE INDEX IF NOT EXISTS idx_crypto_hist_original ON crypto_monitoreo_historial (original_id)",
    "CREATE INDEX IF NOT EXISTS idx_crypto_hist_date     ON crypto_monitoreo_historial (snapshot_date DESC)",
]


# ── Ejecutor ──────────────────────────────────────────────────────────────────
def run_migration(label: str, statements: list[str]) -> bool:
    """Ejecuta una lista de sentencias SQL en una transacción.
    Devuelve True si tuvo éxito, False si falló."""
    import psycopg2

    for sslmode in ("require", "prefer", "disable"):
        try:
            print(f"\n[{label}] Intentando sslmode={sslmode}...")
            conn = psycopg2.connect(RAILWAY_URL, sslmode=sslmode, connect_timeout=15)
            conn.autocommit = False
            cur = conn.cursor()

            for i, stmt in enumerate(statements, 1):
                clean = stmt.strip()
                if not clean:
                    continue
                preview = clean[:80].replace("\n", " ")
                print(f"  ({i}/{len(statements)}) {preview}...")
                cur.execute(clean)

            conn.commit()
            print(f"  ✅ [{label}] Aplicada correctamente (sslmode={sslmode})")
            conn.close()
            return True

        except psycopg2.OperationalError as exc:
            first_line = str(exc).splitlines()[0][:120]
            print(f"  ⚠  sslmode={sslmode} falló (OperationalError): {first_line}")
            continue
        except Exception as exc:
            import traceback
            traceback.print_exc()
            return False

    print(f"  ❌ [{label}] No se pudo conectar con ningún sslmode.")
    return False


def verify() -> None:
    """Verifica que las columnas clave existan después de las migraciones."""
    import psycopg2

    checks = [
        ("crypto_monitoreo",         "sof_score"),
        ("crypto_monitoreo",         "uof_score"),
        ("crypto_monitoreo",         "final_risk_level"),
        ("crypto_monitoreo",         "wallet_status"),
        ("crypto_monitoreo",         "weekly_delta"),
        ("crypto_monitoreo_historial", "snapshot_date"),
    ]

    for sslmode in ("require", "prefer", "disable"):
        try:
            conn = psycopg2.connect(RAILWAY_URL, sslmode=sslmode, connect_timeout=15)
            cur = conn.cursor()
            print("\n── Verificación post-migración ──────────────────────────")
            for table, column in checks:
                cur.execute(
                    "SELECT COUNT(*) FROM information_schema.columns "
                    "WHERE table_name = %s AND column_name = %s",
                    (table, column),
                )
                exists = cur.fetchone()[0] > 0
                status = "✅" if exists else "❌ FALTA"
                print(f"  {status}  {table}.{column}")
            conn.close()
            return
        except psycopg2.OperationalError:
            continue


if __name__ == "__main__":
    print("=" * 60)
    print("apply_015.py — Cripto Compliance: SoF/UoF + Historial semanal")
    print("=" * 60)

    ok_021 = run_migration("Migración 021 — SoF/UoF/Conclusión", SQL_021)
    ok_022 = run_migration("Migración 022 — weekly_delta + historial", SQL_022)

    verify()

    print("\n" + "=" * 60)
    if ok_021 and ok_022:
        print("✅ Ambas migraciones aplicadas exitosamente.")
    else:
        failed = []
        if not ok_021:
            failed.append("021")
        if not ok_022:
            failed.append("022")
        print(f"❌ Falló(n): {', '.join(failed)}. Revisa los errores arriba.")
        sys.exit(1)
