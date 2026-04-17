"""
db/seed_test_users.py
Inserta usuarios de prueba para validar la lógica RBAC de AdamoServices.

La contraseña de todos los usuarios es la misma que ADMIN_PASSWORD en .env
(la app acepta PLACEHOLDER_HASH en modo APP_ENV=development).

Uso:
    python db/seed_test_users.py
"""

import sys
from pathlib import Path

# Asegurar que la raíz del proyecto esté en el path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from db.database import get_session

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

# PLACEHOLDER_HASH es reconocido por authenticate() en modo development.
# La contraseña efectiva es el valor de ADMIN_PASSWORD en tu .env
_HASH = "PLACEHOLDER_HASH"


def seed_test_users() -> None:
    try:
        session_gen = get_session()
        session = next(session_gen)
    except Exception as exc:
        print(f"❌ No se pudo conectar a la base de datos: {exc}")
        print("   Asegúrate de que el contenedor Docker (adamo_postgres) esté corriendo:")
        print("   docker compose up -d postgres")
        sys.exit(1)

    try:
        created = 0
        for u in _TEST_USERS:
            # Verificar si el usuario ya existe
            existing = session.execute(
                text("SELECT id FROM usuarios WHERE username = :username"),
                {"username": u["username"]},
            ).fetchone()

            if existing:
                print(f"⚠️  Usuario '{u['username']}' ya existe — omitido.")
                continue

            session.execute(
                text("""
                    INSERT INTO usuarios
                        (username, nombre_completo, email, password_hash, rol, activo)
                    VALUES
                        (:username, :nombre_completo, :email, :password_hash, :rol, 1)
                """),
                {
                    "username":        u["username"],
                    "nombre_completo": u["nombre_completo"],
                    "email":           u["email"],
                    "password_hash":   _HASH,
                    "rol":             u["rol"],
                },
            )
            print(f"✅ Usuario '{u['username']}' creado con rol '{u['rol']}'.")
            created += 1

        session.commit()

        if created == 0:
            print("\nTodos los usuarios de prueba ya existían.")
        else:
            print(f"\n{created} usuario(s) insertado(s) correctamente.")

    except Exception as exc:
        session.rollback()
        print(f"❌ Error al insertar usuarios: {exc}")
        sys.exit(1)
    finally:
        session.close()

    print("\n─── Credenciales de prueba ───────────────────────────")
    print("  Usuario            │ Rol        │ Password")
    print("  ─────────────────────────────────────────────────")
    for u in _TEST_USERS:
        print(f"  {u['username']:<18} │ {u['rol']:<10} │ (tu ADMIN_PASSWORD del .env)")
    print("\n  Para probar: cierra sesión en la app y usa el username de prueba.")


if __name__ == "__main__":
    seed_test_users()
