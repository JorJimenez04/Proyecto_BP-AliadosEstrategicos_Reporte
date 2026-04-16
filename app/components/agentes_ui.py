"""
app/components/agentes_ui.py
Módulo de Equipos Operativos — AdamoServices Partner Manager.

Visualiza el perfil de desempeño de cada agente: KPIs de actividad,
última conexión, partners asignados y timeline de las últimas acciones.
"""

from __future__ import annotations
import base64
import streamlit as st
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# Paleta corporativa (idéntica a dashboard_ui / main.py)
# ─────────────────────────────────────────────────────────────
_C_CYAN   = "#5fe9d0"
_C_VIOLET = "#7839ee"
_C_AMBER  = "#f59e0b"
_C_RED    = "#ef4444"
_C_GRAY   = "#9ca3af"
_C_BG     = "#1f2937"
_C_BG2    = "#111827"
_C_BORDER = "#293056"

# ─────────────────────────────────────────────────────────────
# Catálogo de Equipos y Agentes
# Cada agente lleva: id de usuario en `usuarios`, equipo, cargo e ícono.
# ─────────────────────────────────────────────────────────────
EQUIPOS: dict[str, dict] = {
    "🛡️ Cumplimiento": {
        "color": _C_CYAN,
        "agentes": [
            {"username": "samuel_mora",    "nombre": "Samuel Mora",    "cargo": "Analista SARLAFT"},
            {"username": "laura_cano",     "nombre": "Laura Cano",     "cargo": "Oficial de Compliance"},
            {"username": "daniel_reyes",   "nombre": "Daniel Reyes",   "cargo": "Analista AML"},
        ],
    },
    "💸 Pagos": {
        "color": _C_VIOLET,
        "agentes": [
            {"username": "andrea_ospina",  "nombre": "Andrea Ospina",  "cargo": "Analista de Pagos"},
            {"username": "carlos_mendez",  "nombre": "Carlos Méndez",  "cargo": "Gestor de Dispersión"},
        ],
    },
    "🎧 Soporte": {
        "color": _C_AMBER,
        "agentes": [
            {"username": "sofia_villa",    "nombre": "Sofía Villa",    "cargo": "Agente de Soporte"},
            {"username": "miguel_torres",  "nombre": "Miguel Torres",  "cargo": "Técnico Onboarding"},
        ],
    },
}

# Mapa rápido username → equipo (se construye una sola vez al cargar el módulo)
_USERNAME_TO_EQUIPO: dict[str, str] = {
    agente["username"]: equipo_nombre
    for equipo_nombre, info in EQUIPOS.items()
    for agente in info["agentes"]
}

# Directorio de fotos de agentes
# Convención: app/static/img/agentes/<username>.(jpg|jpeg|png|webp)
_AGENTES_DIR = Path(__file__).resolve().parent.parent / "static" / "img" / "agentes"
_IMG_FORMATS = (".jpg", ".jpeg", ".png", ".webp")


def _foto_base64(username: str) -> str | None:
    """Retorna la foto del agente como data-URI base64, o None si no existe."""
    for ext in _IMG_FORMATS:
        path = _AGENTES_DIR / f"{username}{ext}"
        if path.exists():
            mime = "image/jpeg" if ext in (".jpg", ".jpeg") else f"image/{ext.lstrip('.')}"
            return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"
    return None


# ─────────────────────────────────────────────────────────────
# Helpers de UI
# ─────────────────────────────────────────────────────────────

def _kpi(label: str, value: object, color: str = _C_CYAN) -> None:
    st.markdown(
        f"""
        <div style='background:{_C_BG};border-radius:10px;padding:14px 18px;
                    border-left:3px solid {color};'>
            <div style='color:{_C_GRAY};font-size:0.70rem;text-transform:uppercase;
                        letter-spacing:1px;font-weight:600;'>{label}</div>
            <div style='color:#f9fafb;font-size:1.8rem;font-weight:800;
                        margin-top:4px;line-height:1;'>{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _accion_badge(accion: str) -> str:
    colores = {
        "CREATE":        (_C_CYAN,   "CREAR"),
        "UPDATE":        (_C_VIOLET, "EDITAR"),
        "DELETE":        (_C_RED,    "ELIMINAR"),
        "LOGIN":         ("#22c55e", "LOGIN"),
        "LOGIN_FAIL":    (_C_RED,    "LOGIN FAIL"),
        "EXPORT":        (_C_AMBER,  "EXPORTAR"),
        "ESTADO_CHANGE": (_C_AMBER,  "ESTADO"),
    }
    color, label = colores.get(accion.upper(), (_C_GRAY, accion))
    return (
        f'<span style="background:{color}22;color:{color};border:1px solid {color}44;'
        f'border-radius:9999px;padding:2px 9px;font-size:10px;font-weight:700;'
        f'white-space:nowrap">{label}</span>'
    )


# ─────────────────────────────────────────────────────────────
# Función principal de perfil
# ─────────────────────────────────────────────────────────────

def render_perfil_agente(username: str) -> None:
    """
    Renderiza el perfil de desempeño de un agente identificado por su username.

    Secciones:
      1. Header (nombre, equipo, cargo)
      2. KPIs: gestiones totales, última conexión, partners asignados
      3. Timeline: últimas 5 acciones en log_auditoria
    """
    from db.database import get_session
    from db.repositories.audit_repo import AuditRepository
    from sqlalchemy import text

    # ── Resolver equipo y datos del agente ───────────────────
    equipo_nombre = _USERNAME_TO_EQUIPO.get(username)
    agente_info: dict | None = None
    equipo_color = _C_GRAY

    if equipo_nombre:
        equipo_color = EQUIPOS[equipo_nombre]["color"]
        agente_info = next(
            (a for a in EQUIPOS[equipo_nombre]["agentes"] if a["username"] == username),
            None,
        )

    nombre_display = agente_info["nombre"] if agente_info else username
    cargo_display  = agente_info["cargo"]  if agente_info else "Agente"

    # ── Consulta a BD ─────────────────────────────────────────
    usuario_id: int | None = None
    gestiones_total: int   = 0
    ultimo_acceso: str     = "—"
    partners_asignados: int = 0
    timeline: list[dict]   = []

    try:
        with next(get_session()) as session:
            # Resolver ID de usuario por username
            row_user = session.execute(
                text("SELECT id, ultimo_acceso FROM usuarios WHERE username = :u"),
                {"u": username},
            ).mappings().first()

            if row_user:
                usuario_id    = row_user["id"]
                ua = row_user["ultimo_acceso"]
                if ua:
                    try:
                        from datetime import datetime
                        if isinstance(ua, str):
                            ua = datetime.fromisoformat(ua)
                        ultimo_acceso = ua.strftime("%d/%m/%Y %H:%M")
                    except Exception:
                        ultimo_acceso = str(ua)

            if usuario_id:
                # Total de gestiones en log
                gestiones_total = session.execute(
                    text("SELECT COUNT(*) FROM log_auditoria WHERE usuario_id = :id"),
                    {"id": usuario_id},
                ).scalar() or 0

                # Partners asignados (ejecutivo_cuenta_id)
                partners_asignados = session.execute(
                    text("SELECT COUNT(*) FROM aliados WHERE ejecutivo_cuenta_id = :id"),
                    {"id": usuario_id},
                ).scalar() or 0

                # Timeline: últimas 5 acciones
                audit_repo = AuditRepository(session)
                timeline = audit_repo.get_actividad_usuario(usuario_id, limit=5)

    except Exception as exc:
        st.error(f"Error al cargar el perfil del agente: {exc}")
        return

    # ─────────────────────────────────────────────────────────
    # RENDER
    # ─────────────────────────────────────────────────────────

    # ── Header ────────────────────────────────────────────────
    foto = _foto_base64(username)
    if foto:
        avatar_html = (
            f"<img src='{foto}' style='width:56px;height:56px;border-radius:50%;"
            f"object-fit:cover;border:2px solid {equipo_color};flex-shrink:0;'>"
        )
    else:
        inicial = nombre_display[0].upper()
        avatar_html = (
            f"<div style='width:56px;height:56px;border-radius:50%;flex-shrink:0;"
            f"background:{equipo_color}22;border:2px solid {equipo_color};"
            f"display:flex;align-items:center;justify-content:center;"
            f"color:{equipo_color};font-size:1.5rem;font-weight:800;'>{inicial}</div>"
        )

    st.markdown(
        f"""
        <div style='background:{_C_BG};border-radius:14px;padding:20px 24px;
                    border-top:3px solid {equipo_color};border:1px solid {_C_BORDER};
                    margin-bottom:20px;'>
            <div style='display:flex;align-items:center;gap:14px;'>
                {avatar_html}
                <div>
                    <div style='color:#f9fafb;font-size:1.2rem;font-weight:700;
                                margin-bottom:2px;'>{nombre_display}</div>
                    <div style='color:{_C_GRAY};font-size:0.78rem;'>{cargo_display}</div>
                    <div style='margin-top:4px;'>
                        <span style='background:{equipo_color}22;color:{equipo_color};
                                     border:1px solid {equipo_color}44;border-radius:9999px;
                                     padding:2px 10px;font-size:10px;font-weight:700;'>
                            {equipo_nombre or "Sin equipo"}
                        </span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── KPIs ──────────────────────────────────────────────────
    st.markdown(
        f"<p style='color:{_C_GRAY};font-size:0.72rem;text-transform:uppercase;"
        f"letter-spacing:1px;font-weight:600;border-bottom:1px solid {_C_BORDER};"
        f"padding-bottom:6px;margin-bottom:14px;'>Métricas de Desempeño</p>",
        unsafe_allow_html=True,
    )
    k1, k2, k3 = st.columns(3)
    with k1:
        _kpi("Gestiones Totales", gestiones_total, equipo_color)
    with k2:
        _kpi("Última Conexión", ultimo_acceso, _C_VIOLET)
    with k3:
        _kpi("Partners Asignados", partners_asignados, _C_AMBER)

    st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)

    # ── Timeline ──────────────────────────────────────────────
    st.markdown(
        f"<p style='color:{_C_GRAY};font-size:0.72rem;text-transform:uppercase;"
        f"letter-spacing:1px;font-weight:600;border-bottom:1px solid {_C_BORDER};"
        f"padding-bottom:6px;margin-bottom:14px;'>Últimas 5 Acciones</p>",
        unsafe_allow_html=True,
    )

    if not timeline:
        st.markdown(
            f"<div style='color:#4b5563;font-size:0.85rem;font-style:italic;"
            f"padding:12px 0;'>Sin actividad registrada para este agente.</div>",
            unsafe_allow_html=True,
        )
        return

    # Cabecera de tabla
    st.markdown(
        f"""
        <div style='display:grid;grid-template-columns:130px 90px 1fr 90px;
                    gap:8px;padding:6px 12px;background:{_C_BG2};
                    border-radius:8px 8px 0 0;border:1px solid {_C_BORDER};
                    border-bottom:none;'>
            <span style='color:{_C_GRAY};font-size:0.68rem;font-weight:700;
                         text-transform:uppercase;letter-spacing:0.8px;'>Fecha</span>
            <span style='color:{_C_GRAY};font-size:0.68rem;font-weight:700;
                         text-transform:uppercase;letter-spacing:0.8px;'>Acción</span>
            <span style='color:{_C_GRAY};font-size:0.68rem;font-weight:700;
                         text-transform:uppercase;letter-spacing:0.8px;'>Descripción</span>
            <span style='color:{_C_GRAY};font-size:0.68rem;font-weight:700;
                         text-transform:uppercase;letter-spacing:0.8px;'>Resultado</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for i, evento in enumerate(timeline):
        # Formatear fecha
        ts = evento.get("created_at")
        try:
            from datetime import datetime
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            fecha_fmt = ts.strftime("%d/%m/%Y %H:%M") if ts else "—"
        except Exception:
            fecha_fmt = str(ts) if ts else "—"

        accion     = str(evento.get("accion", ""))
        descripcion = str(evento.get("descripcion", "—"))
        resultado  = str(evento.get("resultado", ""))

        res_color = _C_CYAN if resultado == "exitoso" else _C_RED
        border_b  = f"border-bottom:1px solid {_C_BORDER};" if i < len(timeline) - 1 else ""
        row_bg    = _C_BG if i % 2 == 0 else _C_BG2

        st.markdown(
            f"""
            <div style='display:grid;grid-template-columns:130px 90px 1fr 90px;
                        gap:8px;padding:9px 12px;background:{row_bg};
                        border-left:1px solid {_C_BORDER};border-right:1px solid {_C_BORDER};
                        {border_b}'>
                <span style='color:#e5e7eb;font-size:0.78rem;'>{fecha_fmt}</span>
                <span>{_accion_badge(accion)}</span>
                <span style='color:#d1d5db;font-size:0.78rem;
                             white-space:nowrap;overflow:hidden;
                             text-overflow:ellipsis;'>{descripcion}</span>
                <span style='color:{res_color};font-size:0.75rem;
                             font-weight:600;text-transform:capitalize;'>{resultado}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<div style='border:1px solid {_C_BORDER};border-top:none;"
        f"border-radius:0 0 8px 8px;height:4px;'></div>",
        unsafe_allow_html=True,
    )
