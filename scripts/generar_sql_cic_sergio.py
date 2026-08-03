"""
scripts/generar_sql_cic_sergio.py
Genera el SQL completo (migración + alta de Sergio) listo para pegar en la
consola web de Railway, sin necesidad de conectarse a la base desde este equipo.

Calcula el hash bcrypt localmente — la contraseña en texto plano nunca sale
de tu máquina ni queda escrita en el SQL generado.

Uso:
    python scripts/generar_sql_cic_sergio.py
    python scripts/generar_sql_cic_sergio.py --password "OtraClaveSegura*"

El SQL se imprime en consola y se guarda en scripts/_cic_sergio_generado.sql
(ese archivo está ignorado por git: contiene un hash, no lo subas igualmente).
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import bcrypt

# ── Datos del usuario ────────────────────────────────────────
USERNAME        = "sergio.garcia"
NOMBRE_COMPLETO = "Sergio García"
EMAIL           = "sergio.garcia@holdingsbpo.com"
ROL             = "cic"
PASSWORD_DEFECTO = "AdamoCIC2026*"

SALIDA = RAIZ / "scripts" / "_cic_sergio_generado.sql"


def _leer_password(argv: list[str]) -> str:
    for i, arg in enumerate(argv):
        if arg == "--password" and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith("--password="):
            return arg.split("=", 1)[1]
    return PASSWORD_DEFECTO


def main() -> None:
    password = _leer_password(sys.argv[1:])

    hash_bcrypt = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    # Escape de comillas simples para literales SQL
    def q(valor: str) -> str:
        return "'" + valor.replace("'", "''") + "'"

    sql = f"""-- ═══════════════════════════════════════════════════════════
-- Rol CIC + alta de Sergio García
-- Generado por scripts/generar_sql_cic_sergio.py
-- Pegar en: Railway → servicio Postgres → pestaña Console
-- ═══════════════════════════════════════════════════════════

-- ── 1. Migración 034: ampliar el CHECK constraint con 'cic' ──
-- Cada sentencia en una sola línea: pégalas de una en una.
ALTER TABLE usuarios DROP CONSTRAINT IF EXISTS usuarios_rol_check;

ALTER TABLE usuarios ADD CONSTRAINT usuarios_rol_check CHECK (rol IN ('super_admin','compliance','manager_ops','manager_comercial','manager_legal','agente','cic','admin','comercial','agente_kyc','agente_operativo','consulta'));

-- ── 2. Alta del usuario (no duplica si ya existe) ────────────
-- Una sola línea: cópiala completa y pégala de una vez.
INSERT INTO usuarios (username, nombre_completo, email, password_hash, rol, activo) SELECT {q(USERNAME)}, {q(NOMBRE_COMPLETO)}, {q(EMAIL)}, {q(hash_bcrypt)}, {q(ROL)}, 1 WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE username = {q(USERNAME)} OR email = {q(EMAIL)});

-- ── 3. Verificación ──────────────────────────────────────────
SELECT id, username, email, rol, activo FROM usuarios WHERE username = {q(USERNAME)};

-- Debe devolver 1 fila con rol = 'cic' y activo = 1.
"""

    SALIDA.write_text(sql, encoding="utf-8")

    print(sql)
    print("─" * 62)
    print(f"💾 Guardado en: {SALIDA.relative_to(RAIZ)}")
    print(f"🔑 Contraseña : {password}")
    print("   (compártela con Sergio por canal seguro; no está en el SQL)")
    print("─" * 62)


if __name__ == "__main__":
    main()
