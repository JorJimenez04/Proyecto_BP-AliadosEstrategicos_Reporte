"""
db/sync_db.py
─────────────────────────────────────────────────────────────
Script de sincronización de base de datos — AdamoServices.

Aplica las migraciones pendientes en orden numérico y valida
que las relaciones críticas existan al finalizar.

Uso:
    python db/sync_db.py                        # aplica todas
    python db/sync_db.py --only 005 006 007     # aplica solo las indicadas
    python db/sync_db.py --check                # solo valida tablas
"""

import sys
import argparse
import pathlib
import logging
import time

# ── Ajustar path para imports relativos al proyecto ───────────
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from db.database import engine

logging.basicConfig(level=logging.WARNING)

# ─────────────────────────────────────────────────────────────
# Migraciones a aplicar — orden explícito y obligatorio
# ─────────────────────────────────────────────────────────────
MIGRATIONS_DIR = pathlib.Path(__file__).parent / "migrations"

ALL_MIGRATIONS: list[str] = [
    "001_initial_schema_pg.sql",
    "002_add_corporate_metrics.sql",
    "003_fix_constraints_and_corporate_metrics.sql",
    "004_agentes_perfil.sql",
    "005_tabla_agentes.sql",
    "006_kpi_fields.sql",
    "007_kpi_history.sql",
    "008_cuentas_segmentadas.sql",
    "009_rbac_roles.sql",
    "010_kpi_diario_observaciones.sql",
    "011_compliance_documentos.sql",
    "012_compliance_empresa.sql",
    "013_cleanup_seed_documentos.sql",
    "014_rename_carpeta_etica.sql",
    "015_rename_carpeta_riesgos.sql",
]

# Tablas / columnas a validar tras las migraciones
VALIDATION_QUERIES: list[tuple[str, str]] = [
    ("agentes",           "SELECT COUNT(*) FROM agentes"),
    ("agente_kpi_diario", "SELECT COUNT(*) FROM agente_kpi_diario"),
    ("kpi_docs_personales (col)",
     "SELECT kpi_docs_personales FROM agentes LIMIT 1"),
]


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _print(emoji: str, msg: str) -> None:
    print(f"  {emoji}  {msg}")


def _run_migration(filepath: pathlib.Path, retries: int = 3, delay: float = 3.0) -> bool:
    """
    Ejecuta un archivo SQL completo dentro de una transacción.
    Reintenta hasta `retries` veces ante errores de conexión (útil en Railway).
    Retorna True si fue exitoso, False si todos los intentos fallaron.
    """
    sql = filepath.read_text(encoding="utf-8")
    for attempt in range(1, retries + 1):
        try:
            with engine.begin() as conn:
                conn.execute(text(sql))
            return True
        except Exception as exc:
            short = str(exc).splitlines()[0][:120]
            if attempt < retries:
                _print("⏳", f"Reintento {attempt}/{retries - 1} para {filepath.name}: {short}")
                time.sleep(delay)
            else:
                _print("⚠️ ", f"Advertencia en {filepath.name}: {short}")
    return False


def run_migrations(only: list[str] | None = None) -> dict[str, bool]:
    """Ejecuta las migraciones y retorna {nombre: éxito}."""
    targets = only if only else ALL_MIGRATIONS
    results: dict[str, bool] = {}

    print("\n🚀  Iniciando sincronización de base de datos...\n")

    for name in targets:
        # Soporte para prefijo numérico corto, ej: "005"
        if not name.endswith(".sql"):
            matched = [m for m in ALL_MIGRATIONS if m.startswith(name)]
            if not matched:
                _print("❌", f"Migración no encontrada: {name!r}")
                results[name] = False
                continue
            name = matched[0]

        filepath = MIGRATIONS_DIR / name
        if not filepath.exists():
            _print("❌", f"Archivo no encontrado: {filepath}")
            results[name] = False
            continue

        print(f"  ▶  {name}")
        ok = _run_migration(filepath)
        results[name] = ok
        if ok:
            _print("✅", "Aplicada correctamente.\n")
        else:
            _print("↩️ ", "Se continuó con la siguiente.\n")

    return results


def validate_schema() -> bool:
    """Verifica que las relaciones críticas existen."""
    print("─" * 55)
    print("🔍  Validando integridad del esquema...\n")
    all_ok = True

    with engine.connect() as conn:
        for label, query in VALIDATION_QUERIES:
            try:
                conn.execute(text(query))
                _print("✅", f"{label} — OK")
            except Exception as exc:
                short = str(exc).splitlines()[0][:100]
                _print("❌", f"{label} — FALLO: {short}")
                all_ok = False

    return all_ok


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sincroniza el esquema de BD con las migraciones del proyecto."
    )
    parser.add_argument(
        "--only", nargs="+", metavar="ID",
        help="Aplicar solo las migraciones indicadas (ej: --only 005 006 007)"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Solo validar que las tablas existen, sin ejecutar migraciones."
    )
    args = parser.parse_args()

    if args.check:
        ok = validate_schema()
        sys.exit(0 if ok else 1)

    migration_results = run_migrations(only=args.only)
    schema_ok = validate_schema()

    # Resumen final
    total     = len(migration_results)
    exitosas  = sum(1 for v in migration_results.values() if v)
    fallidas  = total - exitosas

    print("\n" + "═" * 55)
    print(f"  📋  Resumen: {exitosas}/{total} migraciones aplicadas")
    if fallidas:
        print(f"  ⚠️   {fallidas} con advertencias (ver arriba — pueden ser idempotentes)")
    if schema_ok:
        print("  ✅  Esquema validado correctamente.")
    else:
        print("  ❌  Algunas relaciones críticas no existen. Revisa los errores.")
    print("═" * 55 + "\n")

    sys.exit(0 if schema_ok else 1)


if __name__ == "__main__":
    main()
