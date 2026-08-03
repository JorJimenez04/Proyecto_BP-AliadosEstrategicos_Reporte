"""
scripts/_db_target.py
Resolución de la base de datos destino para los scripts de mantenimiento.

Permite apuntar a Railway (u otra instancia) sin tocar el .env local.

Orden de precedencia:
    1. Argumento CLI  --database-url <url>
    2. Variable de entorno  DATABASE_PUBLIC_URL
    3. DATABASE_URL de config.settings (lo que haya en .env)

No incrusta credenciales en el código: la URL se pasa en tiempo de ejecución.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from sqlalchemy import create_engine, text as _text
from sqlalchemy.engine import Engine


def _extraer_arg(argv: list[str]) -> str | None:
    """Lee --database-url <url> o --database-url=<url> de argv."""
    for i, arg in enumerate(argv):
        if arg == "--database-url" and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith("--database-url="):
            return arg.split("=", 1)[1]
    return None


def resolver_url(argv: list[str] | None = None) -> tuple[str, str]:
    """Devuelve (url, origen) de la base de datos destino."""
    argv = argv if argv is not None else sys.argv[1:]

    url = _extraer_arg(argv)
    if url:
        return url, "--database-url"

    url = os.getenv("DATABASE_PUBLIC_URL", "").strip()
    if url:
        return url, "DATABASE_PUBLIC_URL"

    from config.settings import DATABASE_URL
    return DATABASE_URL, ".env (DATABASE_URL)"


def describir(url: str) -> str:
    """Representación segura de la URL — nunca imprime la contraseña."""
    try:
        p = urlparse(url.replace("postgres://", "postgresql://", 1))
        usuario = f"{p.username}@" if p.username else ""
        puerto = f":{p.port}" if p.port else ""
        base = p.path.lstrip("/") or "?"
        return f"{usuario}{p.hostname}{puerto}/{base}"
    except Exception:
        return "(URL no interpretable)"


def crear_engine(argv: list[str] | None = None) -> tuple[Engine, str]:
    """Crea un Engine hacia la base destino. Devuelve (engine, descripción)."""
    url, origen = resolver_url(argv)

    if not url:
        print("❌ No hay URL de base de datos.")
        print("   Pasa  --database-url postgresql://... , define DATABASE_PUBLIC_URL,")
        print("   o configura DATABASE_URL en .env")
        sys.exit(1)

    url = url.replace("postgres://", "postgresql://", 1)
    destino = f"{describir(url)}  [origen: {origen}]"

    # Railway a veces rechaza el handshake según el modo SSL negociado.
    # Probamos variantes hasta que una conecte de verdad (SELECT 1).
    errores: list[str] = []
    for sslmode in ("require", "prefer", "allow", "disable"):
        engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 20, "sslmode": sslmode},
        )
        try:
            with engine.connect() as conn:
                conn.execute(_text("SELECT 1"))
            if sslmode != "require":
                print(f"ℹ️  Conectado con sslmode={sslmode}")
            return engine, f"{destino}  [sslmode: {sslmode}]"
        except Exception as exc:
            engine.dispose()
            errores.append(f"  sslmode={sslmode:<8} → {str(exc).splitlines()[0][:110]}")

    print("❌ No se pudo conectar con ningún modo SSL:\n")
    print("\n".join(errores))
    print(f"\n🎯 Destino intentado: {describir(url)}")
    print("""
Qué revisar, en orden:

  1. Host y puerto. El proxy de Railway cambia al recrear el servicio.
     Ve al servicio *Postgres* → Variables → DATABASE_PUBLIC_URL
     y compara el host y el puerto con los de arriba.

  2. Que sea la URL pública. El host debe terminar en .proxy.rlwy.net
     (no .railway.internal, que solo funciona dentro de Railway).

  3. Que el servicio esté despierto. Si el proyecto estaba dormido o
     redesplegando, el proxy acepta el TCP pero corta la sesión.
     Abre la pestaña Data del servicio Postgres: si carga, está vivo.

  4. La contraseña, si la copiaste a mano. En PowerShell la URL debe ir
     entre comillas dobles.
""")
    sys.exit(1)
