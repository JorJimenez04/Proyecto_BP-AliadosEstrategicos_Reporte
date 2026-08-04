"""
scripts/verify_cic_parity.py
Verifica que 'cic' siga la línea base del rol 'comercial', salvo en las
divergencias declaradas abajo.

'cic' nació como clon exacto de 'comercial'. Cada vez que los dos se separan,
la diferencia se registra en DIVERGENCIAS con su motivo. El script falla en
dos casos: si divergen donde no deberían, y si una divergencia declarada ya
no existe (para que la lista no acumule entradas obsoletas).

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
EXCLUIR = {"CARPETAS_COMERCIAL", "CARPETAS_LEGAL", "CARPETAS_OPS", "CARPETAS_CIC"}

# Divergencias deliberadas: conjunto -> motivo.
# Añadir aquí cualquier separación intencionada entre 'cic' y 'comercial'.
DIVERGENCIAS: dict[str, str] = {
    "CAN_VIEW_AGENTES":
        "cic ve los equipos en solo lectura; 'comercial' no. "
        "No se le dio CAN_EDIT_AGENTES.",
}


def main() -> None:
    conjuntos = {
        nombre: valor
        for nombre, valor in vars(Roles).items()
        if isinstance(valor, frozenset) and nombre not in EXCLUIR
    }

    if not conjuntos:
        print("❌ No se encontraron conjuntos de permiso en Roles.")
        sys.exit(1)

    inesperadas: list[str] = []
    declaradas_sin_efecto: list[str] = []

    print(f"\n{'Conjunto':<26} {REF_ROL:^12} {NEW_ROL:^8}  ")
    print("─" * 62)

    for nombre in sorted(conjuntos):
        conjunto = conjuntos[nombre]
        ref = REF_ROL in conjunto
        new = NEW_ROL in conjunto
        iguales = ref == new
        declarada = nombre in DIVERGENCIAS

        if iguales and not declarada:
            marca = "✅"
        elif not iguales and declarada:
            marca = "➜  divergencia declarada"
        elif not iguales:
            marca = "❌ DIVERGE sin declarar"
            inesperadas.append(nombre)
        else:
            marca = "⚠️  declarada pero ya no diverge"
            declaradas_sin_efecto.append(nombre)

        print(f"{nombre:<26} {'✔' if ref else '·':^12} {'✔' if new else '·':^8}  {marca}")

    print("─" * 62)

    for nombre, motivo in sorted(DIVERGENCIAS.items()):
        print(f"  ➜ {nombre}: {motivo}")
    if DIVERGENCIAS:
        print("─" * 62)

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
        raiz / "app" / "components" / "compliance_ui.py",
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

    # 'cic' debe tener su propio conjunto de carpetas, no caer en el 'else'
    if not getattr(Roles, "CARPETAS_CIC", None):
        print("❌ Falta Roles.CARPETAS_CIC — 'cic' vería todas las carpetas.")
        extras_ok = False

    # ── Resultado ─────────────────────────────────────────────
    if inesperadas or declaradas_sin_efecto or not extras_ok:
        if inesperadas:
            print(f"\n❌ Divergencias sin declarar: {', '.join(inesperadas)}")
            print("   Si son intencionadas, añádelas a DIVERGENCIAS con su motivo.")
        if declaradas_sin_efecto:
            print(f"\n⚠️  Declaradas pero ya sin efecto: {', '.join(declaradas_sin_efecto)}")
            print("   Retíralas de DIVERGENCIAS.")
        print("\n❌ VERIFICACIÓN FALLIDA\n")
        sys.exit(1)

    print(f"\n✅ OK — '{NEW_ROL}' sigue la línea base de '{REF_ROL}' "
          f"en los {len(conjuntos)} conjuntos de permiso.\n")


if __name__ == "__main__":
    main()
