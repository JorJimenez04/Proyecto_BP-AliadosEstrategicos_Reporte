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
import hmac
import hashlib
import json
from pathlib import Path
import streamlit as st
from datetime import datetime, timedelta, timezone
import extra_streamlit_components as stx

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


# ── Cookie de sesión ──────────────────────────────────────────
_SESSION_COOKIE = "adamo_session_token"
_SESSION_TTL_H  = 8   # horas de validez


def _get_cookie_manager() -> stx.CookieManager:
    """Retrieves the CookieManager rendered once per run by require_auth()."""
    if "_cookie_manager" not in st.session_state:
        # Fallback: render it now if accessed before require_auth initialises it
        st.session_state["_cookie_manager"] = stx.CookieManager(key="adamo_cm_fallback")
    return st.session_state["_cookie_manager"]


def _read_session_cookie_sync() -> str | None:
    """
    Lee la cookie de sesión de forma síncrona desde los headers HTTP
    (Streamlit ≥ 1.33 expone st.context.cookies).
    Retorna el valor crudo o None si no está disponible.
    """
    try:
        return st.context.cookies.get(_SESSION_COOKIE)  # type: ignore[attr-defined]
    except AttributeError:
        return None


def _render_splash() -> None:
    """
    Pantalla minimalista de espera mientras stx.CookieManager
    lee la sesión del navegador via JavaScript (primer ciclo de Streamlit).
    Dura ~1 run (~200 ms) — oculta el formulario de login antes de que
    el CookieManager dispare el rerun automático con el valor real.
    """
    logo1, _ = _get_logos()
    logo_html = ""
    if logo1:
        if logo1[:4] == b'\x89PNG':
            mime = "image/png"
        elif logo1[:2] == b'\xff\xd8':
            mime = "image/jpeg"
        elif b'<svg' in logo1[:200]:
            mime = "image/svg+xml"
        else:
            mime = "image/png"
        src = f"data:{mime};base64,{base64.b64encode(logo1).decode()}"
        logo_html = (
            f'<img src="{src}" style="max-height:80px;max-width:240px;'
            f'object-fit:contain;filter:brightness(0) invert(1);opacity:0.85;">'
        )
    st.markdown(f"""
    <style>
    [data-testid="stHeader"],[data-testid="stToolbar"],
    [data-testid="stSidebar"]{{display:none!important;}}
    [data-testid="stAppViewContainer"]>.main{{background:#0A1628!important;}}
    [data-testid="stAppViewBlockContainer"]{{padding-top:0!important;}}
    @keyframes splashPulse{{0%,100%{{opacity:0.4;}}50%{{opacity:1;}}}}
    @keyframes splashFade{{from{{opacity:0;transform:translateY(10px);}}
                          to{{opacity:1;transform:translateY(0);}}}}
    .splash-wrap{{
        display:flex;flex-direction:column;align-items:center;
        justify-content:center;min-height:85vh;
        animation:splashFade 0.45s ease-out;
    }}
    .splash-logo{{margin-bottom:36px;}}
    .splash-msg{{
        color:#5fe9d0;font-size:0.78rem;letter-spacing:2.5px;
        text-transform:uppercase;font-weight:600;
        animation:splashPulse 1.7s ease-in-out infinite;
        font-family:'Inter','Segoe UI',sans-serif;
    }}
    </style>
    <div class="splash-wrap">
        <div class="splash-logo">{logo_html}</div>
        <div class="splash-msg">🔐 &nbsp;Estableciendo conexión segura...</div>
    </div>
    """, unsafe_allow_html=True)


def _sign_token(payload: dict) -> str:
    """Firma el payload con HMAC-SHA256 y retorna el token codificado en base64."""
    secret = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production").encode()
    body   = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    sig    = hmac.new(secret, body.encode(), hashlib.sha256).hexdigest()
    return base64.b64encode(json.dumps({"p": body, "s": sig}).encode()).decode()


def _verify_token(token: str) -> dict | None:
    """Verifica firma HMAC y TTL. Retorna el payload o None si es inválido/expirado."""
    try:
        outer    = json.loads(base64.b64decode(token.encode()).decode())
        body     = outer["p"]
        sig      = outer["s"]
        secret   = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production").encode()
        expected = hmac.new(secret, body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(body)
        if datetime.now(timezone.utc).timestamp() > payload.get("exp", 0):
            return None
        return payload
    except Exception:
        return None


def save_session_cookie(user: dict) -> None:
    """Crea y almacena la cookie de sesión firmada (TTL 8 h)."""
    exp = datetime.now(timezone.utc) + timedelta(hours=_SESSION_TTL_H)
    payload = {
        "username":        user["username"],
        "user_id":         user["id"],
        "rol":             user.get("rol", "consulta"),
        "nombre_completo": user.get("nombre_completo", ""),
        "email":           user.get("email", ""),
        "exp":             exp.timestamp(),
    }
    _get_cookie_manager().set(_SESSION_COOKIE, _sign_token(payload), expires_at=exp)


def check_active_session() -> bool:
    """
    Intenta re-hidratar la sesión desde la cookie firmada.

    - Lee la cookie y verifica firma HMAC + TTL.
    - Para usuarios de BD: re-consulta para confirmar que siguen activos.
    - Invalida la cookie automáticamente si la validación falla.
    - Retorna True si la sesión fue restaurada correctamente.
    """
    if st.session_state.get("authenticated"):
        return True

    if st.session_state.get("_logged_out"):
        return False

    token = _read_session_cookie_sync() or _get_cookie_manager().get(_SESSION_COOKIE)
    if not token:
        return False

    payload = _verify_token(token)
    if not payload:
        cm = _get_cookie_manager()
        if cm.get(_SESSION_COOKIE):
            try:
                cm.delete(_SESSION_COOKIE)
            except KeyError:
                pass
        return False

    user_id  = payload.get("user_id")
    username = payload.get("username")

    # Administrador de ENV (id=0) — no existe en la BD
    if user_id == 0:
        st.session_state["authenticated"] = True
        st.session_state["user"] = {
            "id":              0,
            "username":        username,
            "nombre_completo": "Administrador del Sistema",
            "rol":             "admin",
            "email":           os.getenv("ADMIN_EMAIL", "compliance@adamoservices.co"),
        }
        return True

    # Usuario de BD — verificación ligera: solo id + activo = 1
    # El payload completo ya fue verificado con HMAC — no necesitamos SELECT *
    try:
        from db.database import get_session as _get_db_session
        from sqlalchemy import text as _text

        _gen     = _get_db_session()
        _session = next(_gen)
        try:
            exists = _session.execute(
                _text("SELECT id FROM usuarios WHERE id = :id AND activo = 1"),
                {"id": user_id},
            ).first()
        finally:
            _session.close()

        if not exists:
            cm = _get_cookie_manager()
            if cm.get(_SESSION_COOKIE):
                try:
                    cm.delete(_SESSION_COOKIE)
                except KeyError:
                    pass
            return False

        # Restaurar sesión desde el payload firmado (HMAC ya verificado arriba)
        st.session_state["authenticated"] = True
        st.session_state["user"] = {
            "id":              user_id,
            "username":        payload.get("username", username),
            "nombre_completo": payload.get("nombre_completo", ""),
            "rol":             payload.get("rol", "consulta"),
            "email":           payload.get("email", ""),
        }
        return True
    except Exception:
        return False


def logout() -> None:
    """Elimina la cookie de sesión y limpia el estado de la aplicación."""
    try:
        _get_cookie_manager().delete(_SESSION_COOKIE)
    except Exception:
        pass
    for _k in ("user", "authenticated", "nav_agente", "login_fails", "login_locked_until"):
        st.session_state.pop(_k, None)
    st.session_state["_logged_out"] = True
    st.rerun()


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
            text("SELECT * FROM usuarios WHERE username = :u AND activo = 1"),
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

    /* ── Animaciones globales ─────────────────────────────── */
    @keyframes meshFloat {
        0%   { background-position: 0 0, 0 0, 0 0, 0 0; }
        25%  { background-position: 30px 15px, -20px 25px, 0 0, 14px 14px; }
        50%  { background-position: 60px -15px, 40px -30px, 0 0, 28px 28px; }
        75%  { background-position: -30px 40px, -40px 15px, 0 0, 14px 0px; }
        100% { background-position: 0 0, 0 0, 0 0, 0 0; }
    }
    @keyframes inputGlow {
        0%   { box-shadow: 0 2px 0 0 rgba(95,233,208,0.4); }
        50%  { box-shadow: 0 2px 6px 0 rgba(95,233,208,0.65); }
        100% { box-shadow: 0 2px 0 0 rgba(95,233,208,0.4); }
    }
    @keyframes fadeInLogin {
        from { opacity: 0; transform: translateY(12px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    /* ── Fade-in del contenido de login ──────────────────────── */
    [data-testid="stForm"],
    .login-logos-bar,
    .login-title-bar {
        animation: fadeInLogin 0.65s ease-out both;
    }

    /* ── Fondo: malla de partículas animada ──────────────────── */
    [data-testid="stAppViewContainer"]::before {
        content: "";
        position: fixed;
        inset: 0;
        background-color: #0A1628;
        background-image:
            radial-gradient(ellipse 70% 55% at 15% 25%, rgba(95,233,208,0.07) 0%, transparent 65%),
            radial-gradient(ellipse 60% 50% at 85% 75%, rgba(95,233,208,0.05) 0%, transparent 60%),
            radial-gradient(circle, rgba(95,233,208,0.07) 1px, transparent 1px),
            radial-gradient(circle, rgba(95,233,208,0.03) 1px, transparent 1px);
        background-size: 100% 100%, 100% 100%, 28px 28px, 14px 14px;
        animation: meshFloat 22s ease-in-out infinite;
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
        font-family: 'Inter', 'Roboto', 'Segoe UI', sans-serif;
        font-size: 1.25rem;
        font-weight: 800;
        letter-spacing: 2px;
        text-transform: uppercase;
        background: linear-gradient(135deg, #FFFFFF 0%, #5FE9D0 38%, #FFFFFF 58%, #A8F0E8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        filter: drop-shadow(0 1px 6px rgba(95,233,208,0.35));
    }
    .login-title-bar .app-subtitle {
        font-family: 'Inter', 'Roboto', 'Segoe UI', sans-serif;
        font-size: 0.75rem;
        color: #E5E7EB;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-top: 8px;
    }

    /* ── Tarjeta contenedor (glassmorphism) ─────────────────── */
    [data-testid="stForm"] {
        background: rgba(15, 27, 45, 0.55) !important;
        backdrop-filter: blur(20px) saturate(150%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(150%) !important;
        border-radius: 16px !important;
        border: 1px solid rgba(95, 233, 208, 0.22) !important;
        box-shadow:
            0 8px 32px rgba(0, 0, 0, 0.45),
            inset 0 1px 0 rgba(95, 233, 208, 0.12),
            inset 0 -1px 0 rgba(0, 0, 0, 0.2) !important;
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
        background: rgba(10, 22, 40, 0.7) !important;
        border: none !important;
        border-bottom: 1.5px solid rgba(95,233,208,0.25) !important;
        border-radius: 6px 6px 0 0 !important;
        color: #E2E8F0 !important;
        padding: 11px 14px !important;
        font-size: 0.92rem !important;
        transition: border-color 0.25s ease, box-shadow 0.25s ease, background 0.25s ease !important;
        box-shadow: none !important;
    }
    .stTextInput input::placeholder { color: #4B5563 !important; }
    .stTextInput input:hover {
        border-bottom-color: rgba(95,233,208,0.5) !important;
        background: rgba(10, 22, 40, 0.85) !important;
    }
    .stTextInput input:focus {
        border-bottom-color: #5FE9D0 !important;
        background: rgba(10, 22, 40, 0.9) !important;
        outline: none !important;
        animation: inputGlow 2s ease-in-out infinite !important;
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
        <div class="app-title">Centro de Inteligencia Corporativa</div>
        <div class="app-subtitle">Compliance, Data &amp; Technology Intelligent Hub</div>
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
            🔒 Conexión segura · Intelligence Hub - Operaciones Globales · AdamoServices S.A.S · 2026
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
            st.session_state.pop("_logged_out", None)
            save_session_cookie(user)
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


# ── Verificación de permisos ──────────────────────────────────
def check_permission(required_roles: list[str], user: dict | None = None) -> bool:
    """
    Verifica si el usuario activo tiene al menos uno de los roles requeridos.

    Parámetros:
        required_roles: Lista de strings de rol que tienen acceso.
        user:           Dict del usuario; si None, se obtiene de session_state.

    Retorna True si el usuario tiene permiso; False si no.

    Uso típico en UI:
        if not check_permission([Roles.ADMIN, Roles.AGENTE_KYC]):
            st.error("Acceso denegado.")
            st.stop()
    """
    if user is None:
        user = st.session_state.get("user", {})
    return user.get("rol", "") in required_roles


def access_denied(message: str = "No tienes permisos para acceder a esta sección.") -> None:
    """Muestra un banner de acceso denegado y detiene la ejecución de la página."""
    st.error(f"🔒 {message}")
    st.stop()


# ── Gate de autenticación ─────────────────────────────────────
def require_auth() -> dict:
    """
    Gate de autenticación para usar al inicio de main().

    Flujo de arranque anti-parpadeo:
      Run 1 — stx.CookieManager se renderiza pero la cookie aún no está
               disponible (JS no ha comunicado el valor). Se muestra el
               splash screen para ocultar el formulario de login.
               El componente dispara un rerun automático al leer las cookies.
      Run 2 — cookie disponible → check_active_session() puede validar.
               Si la sesión es válida, retorna el usuario directamente.
               Si no hay sesión, muestra login_screen() con fade-in suave.

    Nunca retorna si el usuario no está autenticado (llama st.stop()).
    """
    # CookieManager se renderiza siempre para que set/delete funcionen
    # (logout necesita que el componente esté en el DOM)
    st.session_state["_cookie_manager"] = stx.CookieManager(key="adamo_cm")

    # ── Fast path: sesión activa en este run ──────────────────
    # El splash NO puede aparecer si el usuario ya está autenticado.
    # Cubre navegación normal y reruns del propio CookieManager.
    if st.session_state.get("authenticated") and "user" in st.session_state:
        return st.session_state["user"]

    # ── Logout explícito: ir al login sin splash ──────────────
    if st.session_state.get("_logged_out"):
        login_screen()
        st.stop()

    # ── Lectura síncrona de cookie (Streamlit ≥ 1.33) ─────────
    # Si la cookie existe en los headers HTTP ya la tenemos sin JS.
    # En este caso saltamos el splash por completo.
    _sync_token = _read_session_cookie_sync()

    # ── Splash solo si no hay cookie síncrona y es primer boot ─
    if not st.session_state.get("_boot_done") and _sync_token is None:
        st.session_state["_boot_done"] = True
        _render_splash()
        st.stop()

    # Marcar boot completado para runs siguientes
    st.session_state["_boot_done"] = True

    check_active_session()
    if not st.session_state.get("authenticated") or "user" not in st.session_state:
        login_screen()
        st.stop()
    return st.session_state["user"]
