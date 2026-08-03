"""
scripts/verify_cic_parity.py
Verifica que el rol 'cic' tenga exactamente los mismos permisos que el rol 'comercial'.

Recorre por introspección todos los frozenset de config.settings.Roles y compara
la pertenencia de ambos roles. Sale con código 1 si detecta divergencia.

Uso:
    python scripts/verify_cic_parity.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import Roles

REF_ROL = "comercial"
NEW_ROL = "cic"

# Conjuntos que NO son de permiso por rol (carpetas del Centro Documental)
EXCLUIR = {"CARPETAS_COMERCIAL", "CARPETAS_LEGAL", "CARPETAS_OPS"}


def main() -> None:
    conjuntos = {
        nombre: valor
        for nombre, valor in vars(Roles).items()
        if isinstance(valor, frozenset) and nombre not in EXCLUIR
    }

    if not conjuntos:
        print("❌ No se encontraron conjuntos de permiso en Roles.")
        sys.exit(1)

    divergencias: list[str] = []

    print(f"\n{'Conjunto':<26} {REF_ROL:^12} {NEW_ROL:^8}  ")
    print("─" * 56)

    for nombre in sorted(conjuntos):
        conjunto = conjuntos[nombre]
        ref = REF_ROL in conjunto
        new = NEW_ROL in conjunto
        ok = ref == new
        marca = "✅" if ok else "❌ DIVERGE"
        print(f"{nombre:<26} {'✔' if ref else '·':^12} {'✔' if new else '·':^8}  {marca}")
        if not ok:
            divergencias.append(nombre)

    print("─" * 56)

    # ── Comprobaciones adicionales ────────────────────────────
    extras_ok = True

    if NEW_ROL not in Roles.ALL:
        print(f"❌ '{NEW_ROL}' no está en Roles.ALL (no aparecerá en selectores de UI).")
        extras_ok = False

    if getattr(Roles, "CIC", None) != NEW_ROL:
        print(f"❌ Roles.CIC no está definido o no vale '{NEW_ROL}'.")
        extras_ok = False

    # Hardcodeos conocidos fuera de los frozensets
    raiz = Path(__file__).resolve().parent.parent
    hardcodeos = [
        raiz / "app" / "main.py",
        raiz / "app" / "components" / "clientes_ui.py",
        raiz / "app" / "components" / "partners_ui.py",
        raiz / "db" / "migrations" / "034_rol_cic.sql",
    ]
    for archivo in hardcodeos:
        if not archivo.exists():
            print(f"⚠️  No encontrado: {archivo.relative_to(raiz)}")
            extras_ok = False
            continue
        texto = archivo.read_text(encoding="utf-8", errors="replace")
        if NEW_ROL not in texto.lower():
            print(f"❌ '{NEW_ROL}' no aparece en {archivo.relative_to(raiz)}")
            extras_ok = False

    # ── Resultado ─────────────────────────────────────────────
    if divergencias or not extras_ok:
        if divergencias:
            print(f"\n❌ {len(divergencias)} divergencia(s): {', '.join(divergencias)}")
        print("\n❌ PARIDAD NO VERIFICADA\n")
        sys.exit(1)

    print(f"\n✅ PARIDAD OK — '{NEW_ROL}' replica a '{REF_ROL}' "
          f"en los {len(conjuntos)} conjuntos de permiso.\n")


if __name__ == "__main__":
    main()
