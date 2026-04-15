"""
app/auth/login.py
Sistema de autenticación de AdamoServices Partner Manager.

Flujo:
  1. Verifica ADMIN_USERNAME / ADMIN_PASSWORD (ENV) — acceso de administración inicial.
  2. Si no coincide, autentica contra la tabla `usuarios` con bcrypt.
  3. Rate-limiting básico: retraso progresivo + bloqueo temporal tras 5 fallos.
  4. Registro de cada intento (exitoso o fallido) en log_auditoria.
"""

import os
import base64
import time
from pathlib import Path
import streamlit as st
from datetime import datetime

# ── Rutas de logos (misma detección que main.py) ─────────────
_LOGOS_DIR   = Path(__file__).resolve().parent.parent / "static" / "img" / "logos"
_IMG_FORMATS = (".png", ".jpg", ".jpeg", ".webp", ".svg")


def _get_logos() -> tuple[bytes | None, bytes | None]:
    """
    Retorna (logo_principal_bytes, logo_secundario_bytes).
    Prioridad: nombres estándar → orden alfabético como fallback.
    """
    def _read(path: Path) -> bytes | None:
        try:
            return path.read_bytes()
        except Exception:
            return None

    # 1. Nombres estándar
    logo1 = logo2 = None
    for ext in _IMG_FORMATS:
        if not logo1 and (_LOGOS_DIR / f"logo_adamo_blanco{ext}").exists():
            logo1 = _read(_LOGOS_DIR / f"logo_adamo_blanco{ext}")
        if not logo2 and (_LOGOS_DIR / f"logo_adamo_color{ext}").exists():
            logo2 = _read(_LOGOS_DIR / f"logo_adamo_color{ext}")

    # 2. Fallback posicional
    if not logo1 and _LOGOS_DIR.exists():
        all_imgs = sorted(p for ext in _IMG_FORMATS for p in _LOGOS_DIR.glob(f"*{ext}"))
        if all_imgs:
            logo1 = _read(all_imgs[0])
        if len(all_imgs) >= 2:
            logo2 = _read(all_imgs[1])

    return logo1, logo2

# ── Constantes de rate-limiting ───────────────────────────────
_MAX_FAILS       = 5   # intentos consecutivos antes de bloqueo
_LOCKOUT_SECONDS = 60  # segundos de bloqueo temporal


# ── IP del cliente ────────────────────────────────────────────
def _get_client_ip() -> str:
    """Intenta obtener la IP real del cliente; retorna '127.0.0.1' como fallback."""
    try:
        headers = st.context.headers          # Streamlit ≥ 1.31
        ip = (
            headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or headers.get("X-Real-IP", "")
            or "127.0.0.1"
        )
        return ip or "127.0.0.1"
    except Exception:
        return "127.0.0.1"


# ── Registro de auditoría ─────────────────────────────────────
def _audit_login(
    success: bool,
    username: str,
    ip: str,
    usuario_id: int | None = None,
    motivo: str = "",
) -> None:
    """Registra el intento de login en log_auditoria (no bloquea la UI si falla)."""
    try:
        from db.database import get_session
        from db.repositories.audit_repo import AuditRepository

        session_gen = get_session()
        session = next(session_gen)
        try:
            AuditRepository(session).registrar(
                username=username,
                usuario_id=usuario_id,
                accion="LOGIN" if success else "LOGIN_FAIL",
                entidad="usuarios",
                entidad_id=usuario_id,
                descripcion=(
                    f"Inicio de sesión {'exitoso' if success else 'fallido'} · IP: {ip}"
                    + (f" · {motivo}" if motivo else "")
                ),
                ip_address=ip,
                resultado="exitoso" if success else "fallido",
            )
        finally:
            session.close()
    except Exception:
        pass  # auditoría nunca debe romper el flujo de autenticación


# ── Autenticación ─────────────────────────────────────────────
def authenticate(username: str, password: str) -> dict | None:
    """
    Autentica al usuario con la siguiente prioridad:

    1. Variables de entorno ADMIN_USERNAME / ADMIN_PASSWORD
       (acceso de administración inicial — salta la BD).
    2. Tabla `usuarios` con bcrypt (password_hash).
       Acepta PLACEHOLDER_HASH en modo desarrollo.

    Retorna el dict del usuario o None si las credenciales son incorrectas.
    """
    import bcrypt
    from db.database import get_session
    from sqlalchemy import text

    # ── 1. Autenticación por ENV (bootstrap admin) ────────────
    env_user = os.getenv("ADMIN_USERNAME", "admin")
    env_pass = os.getenv("ADMIN_PASSWORD", "")

    if env_pass and username == env_user and password == env_pass:
        return {
            "id":               0,
            "username":         env_user,
            "nombre_completo":  "Administrador del Sistema",
            "rol":              "admin",
            "email":            os.getenv("ADMIN_EMAIL", "compliance@adamoservices.co"),
        }

    # ── 2. Autenticación por BD ───────────────────────────────
    session_gen = get_session()
    session = next(session_gen)
    try:
        row = session.execute(
            text("SELECT * FROM usuarios WHERE username = :u AND activo = true"),
            {"u": username},
        ).mappings().first()

        if not row:
            return None

        stored_hash: str = row["password_hash"]

        # Modo desarrollo: acepta la password de ENV o la de fallback
        if stored_hash == "PLACEHOLDER_HASH":
            from config.settings import APP_ENV as _APP_ENV
            # PLACEHOLDER_HASH solo es válido en desarrollo — bloquear siempre en producción
            if _APP_ENV == "production":
                return None
            fallback = os.getenv("ADMIN_PASSWORD", "Admin@AdamoServices2025!")
            if password in (fallback, "admin"):
                return dict(row)
            return None

        # Verificación bcrypt
        if bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
            session.execute(
                text("UPDATE usuarios SET ultimo_acceso = :ts WHERE id = :id"),
                {"ts": datetime.now().isoformat(), "id": row["id"]},
            )
            session.commit()
            return dict(row)

        return None
    finally:
        session.close()


# ── Pantalla de login ─────────────────────────────────────────
def login_screen() -> None:
    """
    Renderiza el formulario de login con st.form.

    - Rate-limiting: retraso progresivo (1-3 s) + bloqueo temporal de 60 s
      tras 5 intentos consecutivos fallidos.
    - Registra cada intento (exitoso o fallido) en log_auditoria.
    - En caso de éxito establece:
        st.session_state["authenticated"] = True
        st.session_state["user"]          = <dict del usuario>
    """
    # Inicializar contadores en session_state
    st.session_state.setdefault("login_fails", 0)
    st.session_state.setdefault("login_locked_until", 0.0)

    ip = _get_client_ip()

    # Verificar bloqueo temporal
    remaining = st.session_state["login_locked_until"] - time.time()
    if remaining > 0:
        st.error(
            f"🔒 Acceso bloqueado temporalmente. "
            f"Intenta de nuevo en {int(remaining) + 1} segundo(s)."
        )
        st.stop()

    # ── CSS de la pantalla de login ───────────────────────────
    st.markdown("""
    <style>
    /* ── Globals ──────────────────────────────────────────── */
    [data-testid="stHeader"]  { background: transparent !important; border: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stAppViewContainer"] > .main { background: #0F1B2D !important; }
    [data-testid="stAppViewBlockContainer"] { padding-top: 2rem !important; }

    /* ── Fondo: degradado + malla de datos (dot grid) ─────── */
    [data-testid="stAppViewContainer"]::before {
        content: "";
        position: fixed;
        inset: 0;
        background-color: #0F1B2D;
        background-image:
            radial-gradient(ellipse 70% 55% at 15% 25%, rgba(95,233,208,0.07) 0%, transparent 65%),
            radial-gradient(ellipse 60% 50% at 85% 75%, rgba(95,233,208,0.05) 0%, transparent 60%),
            radial-gradient(circle, #1E293B 1px, transparent 1px);
        background-size: auto, auto, 28px 28px;
        pointer-events: none;
        z-index: 0;
    }

    /* ── Barra de logos ───────────────────────────────────── */
    .login-logos-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 20px 0 18px;
        background: transparent;
        margin-bottom: 0;
    }
    .login-logos-bar .logo-slot {
        display: flex;
        align-items: center;
        border-radius: 14px;
        padding: 14px 24px;
    }
    .login-logos-bar .logo-slot:first-child { justify-content: flex-start; }
    .login-logos-bar .logo-slot:last-child  { justify-content: flex-end; }

    /* Logo Adamo — invertido a blanco sobre fondo oscuro */
    .logo-slot:first-child {
        background: transparent;
        box-shadow: none;
    }
    .header-logo-adamo {
        max-height: 120px;
        max-width: 300px;
        object-fit: contain;
        filter: brightness(0) invert(1) drop-shadow(0 0 10px rgba(255,255,255,0.15));
        transition: opacity 0.25s, transform 0.25s;
    }
    .header-logo-adamo:hover { opacity: 0.85; transform: scale(1.03); }

    /* Logo Holdings BPO — colores originales, sin card */
    .logo-slot:last-child {
        background: transparent;
        box-shadow: none;
    }
    .header-logo-holdings {
        max-height: 120px;
        max-width: 300px;
        object-fit: contain;
        filter: brightness(0) invert(1) drop-shadow(0 0 10px rgba(255,255,255,0.15));
        transition: opacity 0.25s, transform 0.25s;
    }
    .header-logo-holdings:hover { opacity: 0.85; transform: scale(1.03); }

    /* ── Barra de título ──────────────────────────────────── */
    .login-title-bar {
        text-align: center;
        padding: 18px 0 10px;
        margin-bottom: 4px;
    }
    .login-title-bar .app-title {
        font-size: 1.15rem;
        font-weight: 800;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: #FFFFFF;
        -webkit-text-fill-color: #FFFFFF;
    }
    .login-title-bar .app-subtitle {
        font-size: 0.72rem;
        color: #9CA3AF;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-top: 6px;
    }

    /* ── Tarjeta contenedor (mate, sin blur) ──────────────── */
    [data-testid="stForm"] {
        background: #111827 !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
        border-radius: 8px !important;
        border: 1px solid #293056 !important;
        box-shadow: 0 4px 24px rgba(0,0,0,0.5) !important;
        padding: 36px 32px 28px !important;
    }

    /* ── Título dentro del card ───────────────────────────── */
    .login-card-title {
        text-align: center;
        font-size: 1.35rem;
        font-weight: 700;
        color: #FFFFFF;
        margin-bottom: 4px;
        letter-spacing: 0.5px;
    }
    .login-card-subtitle {
        text-align: center;
        font-size: 0.75rem;
        color: #9CA3AF;
        margin-bottom: 24px;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    /* ── Labels de inputs ─────────────────────────────────── */
    .stTextInput > label {
        color: #9CA3AF !important;
        font-weight: 600 !important;
        font-size: 0.78rem !important;
        letter-spacing: 0.8px !important;
        text-transform: uppercase !important;
    }

    /* ── Inputs: fondo oscuro, solo borde inferior activo ─── */
    .stTextInput input {
        background: #0F1B2D !important;
        border: none !important;
        border-bottom: 1.5px solid #293056 !important;
        border-radius: 4px 4px 0 0 !important;
        color: #E2E8F0 !important;
        padding: 11px 14px !important;
        font-size: 0.92rem !important;
        transition: border-color 0.2s, box-shadow 0.2s !important;
        box-shadow: none !important;
    }
    .stTextInput input::placeholder { color: #4B5563 !important; }
    .stTextInput input:focus {
        border-bottom-color: #5FE9D0 !important;
        box-shadow: 0 2px 0 0 rgba(95,233,208,0.45) !important;
        outline: none !important;
    }

    /* ── Ícono de ojo (toggle password) ───────────────────── */
    [data-testid="stTextInputRootElement"] button {
        color: #5FE9D0 !important;
        background: transparent !important;
        border: none !important;
        opacity: 0.7;
        transition: opacity 0.2s !important;
    }
    [data-testid="stTextInputRootElement"] button:hover { opacity: 1 !important; }

    /* ── Botón Ingresar: cyan sólido, hover blanco brillante  */
    .stFormSubmitButton > button {
        background: #5FE9D0 !important;
        color: #000000 !important;
        font-weight: 800 !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 13px !important;
        font-size: 0.95rem !important;
        letter-spacing: 1.5px !important;
        text-transform: uppercase !important;
        box-shadow: none !important;
        transition: background 0.18s, box-shadow 0.18s, transform 0.18s !important;
        width: 100% !important;
    }
    .stFormSubmitButton > button:hover {
        background: #FFFFFF !important;
        color: #000000 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 0 18px rgba(95,233,208,0.55), 0 4px 12px rgba(0,0,0,0.3) !important;
    }
    .stFormSubmitButton > button:active {
        transform: translateY(0px) !important;
    }

    /* ── Alertas ──────────────────────────────────────────── */
    [data-testid="stAlert"] {
        border-radius: 6px !important;
        border-left-width: 4px !important;
    }

    /* ── Separador ────────────────────────────────────────── */
    .login-divider {
        border: none;
        border-top: 1px solid #1E293B;
        margin: 6px 0 24px;
    }

    /* ── Footer ───────────────────────────────────────────── */
    .login-footer {
        text-align: center;
        font-size: 0.68rem;
        color: #4B5563;
        margin-top: 28px;
        letter-spacing: 0.5px;
    }
    .login-footer span {
        color: #5FE9D0 !important;
        -webkit-text-fill-color: #5FE9D0 !important;
    }

    /* ── Responsivo ───────────────────────────────────────── */
    @media (max-width: 640px) {
        [data-testid="stForm"] { padding: 24px 18px 20px !important; }
        .login-title-bar .app-title { font-size: 0.95rem; letter-spacing: 2px; }
        .header-logo { max-height: 80px; max-width: 200px; }
        .login-logos-bar .logo-slot { padding: 10px 14px; }
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Cabecera con logos ────────────────────────────────────
    logo1, logo2 = _get_logos()

    def _b64_img(data: bytes | None) -> str:
        if not data:
            return ""
        if data[:4] == b'\x89PNG':
            mime = "image/png"
        elif data[:2] == b'\xff\xd8':
            mime = "image/jpeg"
        elif b'<svg' in data[:200]:
            mime = "image/svg+xml"
        else:
            mime = "image/png"
        return f"data:{mime};base64,{base64.b64encode(data).decode()}"

    src1 = _b64_img(logo1)
    src2 = _b64_img(logo2)
    logo1_tag = f'<img src="{src1}" class="header-logo header-logo-adamo" alt="Adamo">' if src1 else ""
    logo2_tag = f'<img src="{src2}" class="header-logo header-logo-holdings" alt="Holdings BPO">' if src2 else ""

    st.markdown(f"""
    <div class="login-logos-bar">
        <div class="logo-slot">{logo1_tag}</div>
        <div class="logo-slot">{logo2_tag}</div>
    </div>
    <div class="login-title-bar">
        <div class="app-title">Partner Manager</div>
        <div class="app-subtitle">Compliance &amp; Technology</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        "<hr class='login-divider'>",
        unsafe_allow_html=True,
    )

    # ── Formulario centrado ───────────────────────────────────
    _, form_col, _ = st.columns([1, 2, 1])
    with form_col:
        st.markdown("""
        <div class='login-card-title'>Iniciar Sesión</div>
        <div class='login-card-subtitle'>Acceso restringido · ingresa tus credenciales</div>
        """, unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Usuario", placeholder="Ingresa tu usuario")
            password = st.text_input("Contraseña", type="password", placeholder="••••••••")
            submitted = st.form_submit_button(
                "Ingresar →", use_container_width=True, type="primary"
            )

        st.markdown("""
        <div class='login-footer'>
            🔒 Conexión segura · AdamoServices S.A.S · 2026
        </div>
        """, unsafe_allow_html=True)

    if submitted:
        if not username.strip() or not password:
            st.warning("⚠️ Ingresa usuario y contraseña.")
            return

        user = authenticate(username.strip(), password)

        if user:
            # ── Login exitoso ──────────────────────────────
            st.session_state["authenticated"]     = True
            st.session_state["user"]              = user
            st.session_state["login_fails"]       = 0
            st.session_state["login_locked_until"] = 0.0
            _audit_login(
                success=True,
                username=username.strip(),
                ip=ip,
                usuario_id=user.get("id"),
            )
            st.rerun()
        else:
            # ── Login fallido ──────────────────────────────
            st.session_state["login_fails"] += 1
            fails = st.session_state["login_fails"]

            # Retraso progresivo anti brute-force (1 s, 2 s, máx 3 s)
            time.sleep(min(fails, 3))

            if fails >= _MAX_FAILS:
                st.session_state["login_locked_until"] = time.time() + _LOCKOUT_SECONDS
                st.session_state["login_fails"] = 0
                _audit_login(
                    success=False,
                    username=username.strip(),
                    ip=ip,
                    motivo=(
                        f"Cuenta bloqueada temporalmente tras {_MAX_FAILS} "
                        "intentos fallidos consecutivos"
                    ),
                )
                st.error(
                    f"🔒 Demasiados intentos fallidos. "
                    f"Acceso bloqueado por {_LOCKOUT_SECONDS} segundos."
                )
            else:
                _audit_login(
                    success=False,
                    username=username.strip(),
                    ip=ip,
                    motivo=f"Credenciales incorrectas — intento #{fails}",
                )
                st.error(
                    f"❌ Credenciales incorrectas. "
                    f"Intento {fails} de {_MAX_FAILS}."
                )

        # Mensaje informativo debajo del form
        st.markdown(
            "<p style='text-align:center; color:#363f72; font-size:0.72rem; margin-top:14px;'>"
            "© 2026 AdamoServices S.A.S. · SARLAFT / GAFI Compliance Platform"
            "</p>",
            unsafe_allow_html=True,
        )


# ── Gate de autenticación ─────────────────────────────────────
def require_auth() -> dict:
    """
    Gate de autenticación para usar al inicio de main().

    Si el usuario no está autenticado, renderiza login_screen() y
    detiene la ejecución con st.stop() — nunca retorna en ese caso.

    Si está autenticado, retorna el dict del usuario.
    """
    if not st.session_state.get("authenticated") or "user" not in st.session_state:
        login_screen()
        st.stop()
    return st.session_state["user"]
