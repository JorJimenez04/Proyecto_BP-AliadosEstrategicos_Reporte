"""
db/seed_test_users.py
Inserta usuarios de prueba para validar la lógica RBAC de AdamoServices.

Modos de uso:
  Desarrollo local (PLACEHOLDER_HASH — contraseña = ADMIN_PASSWORD del .env):
      python db/seed_test_users.py

  Producción / Railway (hash bcrypt real):
      python db/seed_test_users.py --password "$ADMIN_PASSWORD"
      — o bien —
      DATABASE_URL=<url> python db/seed_test_users.py --password MiPassword

El script es idempotente: usa ON CONFLICT DO NOTHING, nunca falla si los
usuarios ya existen. Railway lo llama automáticamente en cada deploy desde
entrypoint.sh, pasando $ADMIN_PASSWORD como argumento.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from db.database import get_session

# ── Resolver contraseña ───────────────────────────────────────
# Prioridad: --password CLI > ADMIN_PASSWORD env > modo desarrollo
_real_password: str | None = None

if "--password" in sys.argv:
    idx = sys.argv.index("--password")
    if idx + 1 < len(sys.argv):
        _real_password = sys.argv[idx + 1].strip()
    else:
        print("❌ --password requiere un valor.")
        sys.exit(1)

if not _real_password:
    _real_password = os.getenv("ADMIN_PASSWORD", "").strip() or None

# ── Calcular hash ─────────────────────────────────────────────
_app_env = os.getenv("APP_ENV", "development")

if _real_password:
    import bcrypt as _bcrypt
    _HASH = _bcrypt.hashpw(_real_password.encode(), _bcrypt.gensalt()).decode()
    print("[seed] Usando hash bcrypt real.")
elif _app_env == "production":
    print("❌ En producción ADMIN_PASSWORD debe estar definida en Railway.")
    print("   Variables → ADMIN_PASSWORD=<tu-password>")
    sys.exit(1)
else:
    _HASH = "PLACEHOLDER_HASH"
    print("[seed] Modo desarrollo: PLACEHOLDER_HASH (contraseña = ADMIN_PASSWORD del .env).")

# ── Usuarios de prueba ────────────────────────────────────────
_TEST_USERS = [
    {
        "username":        "test_compliance",
        "nombre_completo": "Revisor de Cumplimiento",
        "email":           "test_compliance@adamoservices.co",
        "rol":             "compliance",
    },
    {
        "username":        "test_comercial",
        "nombre_completo": "Ejecutivo Comercial",
        "email":           "test_comercial@adamoservices.co",
        "rol":             "comercial",
    },
    {
        "username":        "test_consulta",
        "nombre_completo": "Auditor de Solo Lectura",
        "email":           "test_consulta@adamoservices.co",
        "rol":             "consulta",
    },
]


def seed_test_users() -> None:
    try:
        session_gen = get_session()
        session = next(session_gen)
    except Exception as exc:
        print(f"❌ No se pudo conectar a la base de datos: {exc}")
        sys.exit(1)

    try:
        created = 0
        for u in _TEST_USERS:
            result = session.execute(
                text("""
                    INSERT INTO usuarios
                        (username, nombre_completo, email, password_hash, rol, activo)
                    VALUES
                        (:username, :nombre_completo, :email, :password_hash, :rol, 1)
                    ON CONFLICT (username) DO NOTHING
                """),
                {
                    "username":        u["username"],
                    "nombre_completo": u["nombre_completo"],
                    "email":           u["email"],
                    "password_hash":   _HASH,
                    "rol":             u["rol"],
                },
            )
            if result.rowcount > 0:
                print(f"[seed] ✅ '{u['username']}' creado con rol '{u['rol']}'.")
                created += 1
            else:
                print(f"[seed] ⚠️  '{u['username']}' ya existe — omitido.")

        session.commit()
        print(f"[seed] {created} usuario(s) nuevos. {len(_TEST_USERS) - created} ya existían.")

    except Exception as exc:
        session.rollback()
        print(f"❌ Error en seed: {exc}")
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    seed_test_users()


if __name__ == "__main__":
    seed_test_users()
