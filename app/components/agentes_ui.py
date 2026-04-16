"""
app/components/agentes_ui.py
Módulo de Equipos Operativos — AdamoServices Partner Manager.

Módulo INFORMATIVO para gerencia y líderes de equipo.
Los agentes son colaboradores registrados en el catálogo —
no acceden al sistema. Las métricas se derivan de los
aliados asignados a cada agente.
"""

from __future__ import annotations
import base64
import logging
import streamlit as st
import plotly.graph_objects as go
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Paleta corporativa
# ─────────────────────────────────────────────────────────────
_C_CYAN   = "#5fe9d0"
_C_VIOLET = "#7839ee"
_C_AMBER  = "#f59e0b"
_C_RED    = "#ef4444"
_C_GREEN  = "#22c55e"
_C_GRAY   = "#9ca3af"
_C_BG     = "#1f2937"
_C_BG2    = "#0b0f1a"
_C_BORDER = "#293056"

_EQUIPOS_COLORES: dict[str, str] = {
    "Cumplimiento": _C_CYAN,
    "Pagos":        _C_VIOLET,
    "Soporte":      _C_AMBER,
}
_EQUIPOS_ICONOS: dict[str, str] = {
    "Cumplimiento": "\U0001f6e1\ufe0f",
    "Pagos":        "\U0001f4b8",
    "Soporte":      "\U0001f3a7",
}
_COLORES_RIESGO: dict[str, str] = {
    "Bajo":     _C_CYAN,
    "Medio":    _C_AMBER,
    "Alto":     "#f97316",
    "Muy Alto": _C_RED,
}

# Cargos especializados por equipo
_CARGOS_POR_EQUIPO: dict[str, list[str]] = {
    "Cumplimiento": [
        "Analista SARLAFT",
        "Oficial de Compliance",
        "Analista AML",
        "Analista de Debida Diligencia",
        "Coordinador de Cumplimiento",
    ],
    "Pagos": [
        "Analista de Pagos",
        "Gestor de Dispersi\u00f3n",
        "Especialista de Conciliaci\u00f3n",
        "Analista de Riesgo Transaccional",
    ],
    "Soporte": [
        "Agente de Soporte",
        "T\u00e9cnico Onboarding",
        "Especialista de Atenci\u00f3n al Cliente",
        "Coordinador de Operaciones",
    ],
}
_CARGO_OTRO = "Otro"

# ─────────────────────────────────────────────────────────────
# Catálogo estático — fallback si la tabla agentes está vacía
# ─────────────────────────────────────────────────────────────
EQUIPOS: dict[str, dict] = {
    "\U0001f6e1\ufe0f Cumplimiento": {
        "color": _C_CYAN,
        "agentes": [
            {"username": "samuel_mora",   "nombre": "Samuel Mora",   "cargo": "Analista SARLAFT"},
            {"username": "laura_cano",    "nombre": "Laura Cano",    "cargo": "Oficial de Compliance"},
            {"username": "daniel_reyes",  "nombre": "Daniel Reyes",  "cargo": "Analista AML"},
        ],
    },
    "\U0001f4b8 Pagos": {
        "color": _C_VIOLET,
        "agentes": [
            {"username": "andrea_ospina", "nombre": "Andrea Ospina", "cargo": "Analista de Pagos"},
            {"username": "carlos_mendez", "nombre": "Carlos M\u00e9ndez", "cargo": "Gestor de Dispersi\u00f3n"},
        ],
    },
    "\U0001f3a7 Soporte": {
        "color": _C_AMBER,
        "agentes": [
            {"username": "sofia_villa",   "nombre": "Sof\u00eda Villa",   "cargo": "Agente de Soporte"},
            {"username": "miguel_torres", "nombre": "Miguel Torres", "cargo": "T\u00e9cnico Onboarding"},
        ],
    },
}

_USERNAME_TO_EQUIPO: dict[str, str] = {
    a["username"]: eq
    for eq, info in EQUIPOS.items()
    for a in info["agentes"]
}

# ─────────────────────────────────────────────────────────────
# Fotos locales
# ─────────────────────────────────────────────────────────────
_AGENTES_DIR = Path(__file__).resolve().parent.parent / "static" / "img" / "agentes"
_IMG_FORMATS = (".jpg", ".jpeg", ".png", ".webp")


def _foto_base64(username: str) -> str | None:
    for ext in _IMG_FORMATS:
        path = _AGENTES_DIR / f"{username}{ext}"
        if path.exists():
            mime = "image/jpeg" if ext in (".jpg", ".jpeg") else f"image/{ext.lstrip('.')}"
            return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"
    return None


# ─────────────────────────────────────────────────────────────
# Sidebar — carga desde tabla agentes
# ─────────────────────────────────────────────────────────────

def get_agentes_sidebar() -> dict:
    """
    Carga agentes desde la tabla `agentes`.
    Fallback al catálogo estático si la tabla está vacía.
    """
    try:
        from db.database import get_session
        from sqlalchemy import text
        with next(get_session()) as session:
            rows = session.execute(text("""
                SELECT username, nombre_completo, cargo, equipo
                FROM agentes
                WHERE activo = TRUE
                ORDER BY equipo, nombre_completo
            """)).mappings().all()

            if not rows:
                return EQUIPOS

            result: dict = {}
            for row in rows:
                eq_raw = row["equipo"]
                icono  = _EQUIPOS_ICONOS.get(eq_raw, "\U0001f464")
                key    = f"{icono} {eq_raw}"
                color  = _EQUIPOS_COLORES.get(eq_raw, _C_GRAY)
                if key not in result:
                    result[key] = {"color": color, "agentes": []}
                result[key]["agentes"].append({
                    "username": row["username"],
                    "nombre":   row["nombre_completo"],
                    "cargo":    row["cargo"] or "Colaborador",
                })
            return result if result else EQUIPOS
    except Exception:
        return EQUIPOS


# ─────────────────────────────────────────────────────────────
# Helpers de UI
# ─────────────────────────────────────────────────────────────

def _kpi_card(label: str, value: object, color: str = _C_CYAN, sublabel: str = "") -> None:
    sub = (
        f"<div style='color:{_C_GRAY};font-size:0.70rem;margin-top:4px;'>{sublabel}</div>"
        if sublabel else ""
    )
    st.markdown(
        f"""
        <div style='background:{_C_BG};border-radius:10px;padding:14px 18px;
                    border-left:3px solid {color};'>
            <div style='color:{_C_GRAY};font-size:0.70rem;text-transform:uppercase;
                        letter-spacing:1px;font-weight:600;'>{label}</div>
            <div style='color:#f9fafb;font-size:1.8rem;font-weight:800;
                        margin-top:4px;line-height:1;'>{value}</div>
            {sub}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _section_title(text_val: str) -> None:
    st.markdown(
        f"<p style='color:{_C_GRAY};font-size:0.72rem;text-transform:uppercase;"
        f"letter-spacing:1px;font-weight:600;border-bottom:1px solid {_C_BORDER};"
        f"padding-bottom:6px;margin:20px 0 14px;'>{text_val}</p>",
        unsafe_allow_html=True,
    )


def _render_header_agente(
    username: str,
    nombre: str,
    cargo: str,
    equipo_label: str,
    equipo_color: str,
    email: str = "",
    telefono: str = "",
) -> None:
    foto = _foto_base64(username)
    if foto:
        avatar = (
            f"<img src='{foto}' style='width:72px;height:72px;border-radius:50%;"
            f"object-fit:cover;border:2px solid {equipo_color};flex-shrink:0;'>"
        )
    else:
        inicial = nombre[0].upper()
        avatar = (
            f"<div style='width:72px;height:72px;border-radius:50%;flex-shrink:0;"
            f"background:{equipo_color}22;border:2px solid {equipo_color};"
            f"display:flex;align-items:center;justify-content:center;"
            f"color:{equipo_color};font-size:1.8rem;font-weight:800;'>{inicial}</div>"
        )

    contacto_html = ""
    if email:
        contacto_html += (
            f"<span style='color:{_C_GRAY};font-size:0.75rem;margin-right:16px;'>"
            f"\u2709\ufe0f {email}</span>"
        )
    if telefono:
        contacto_html += (
            f"<span style='color:{_C_GRAY};font-size:0.75rem;'>"
            f"\U0001f4de {telefono}</span>"
        )

    st.markdown(
        f"""
        <div style='background:{_C_BG};border-radius:14px;padding:24px 28px;
                    border-top:3px solid {equipo_color};border:1px solid {_C_BORDER};
                    margin-bottom:24px;'>
            <div style='display:flex;align-items:center;gap:18px;'>
                {avatar}
                <div>
                    <div style='color:#f9fafb;font-size:1.35rem;font-weight:700;
                                margin-bottom:4px;'>{nombre}</div>
                    <div style='color:{_C_GRAY};font-size:0.82rem;margin-bottom:8px;'>{cargo}</div>
                    <span style='background:{equipo_color}22;color:{equipo_color};
                                 border:1px solid {equipo_color}44;border-radius:9999px;
                                 padding:2px 12px;font-size:10px;font-weight:700;'>
                        {equipo_label}
                    </span>
                    {"<div style='margin-top:10px;'>" + contacto_html + "</div>" if contacto_html else ""}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────
# Registro Diario de Gestiones (Bitácora)
# ─────────────────────────────────────────────────────────────

def _form_registro_diario(agente_db: dict, user: Optional[dict]) -> None:
    """
    Expansor dentro del perfil del agente para registrar la gestión del día.

    Solo visible para administradores.  Si ya existe un registro para hoy lo
    precarga en los campos para permitir edición.  Al guardar hace UPSERT en
    agente_kpi_diario (con auditoría) y st.rerun().
    """
    from config.settings import Roles
    if not (user and user.get("rol") == Roles.ADMIN):
        return

    from datetime import date
    from db.database import get_session
    from db.repositories.agente_repo import AgenteRepository

    agente_id  = agente_db.get("id")
    hoy        = date.today()
    hoy_label  = hoy.strftime("%A %d de %B, %Y")

    # Cargar registro existente de hoy (si lo hay)
    hoy_data: dict = {}
    try:
        with next(get_session()) as session:
            row = AgenteRepository(session).get_kpi_diario(agente_id)
            if row:
                hoy_data = row
    except Exception:
        pass

    with st.expander(
        f"\U0001f4dd Registrar Gesti\u00f3n de Hoy  \u2014  {hoy_label}",
        expanded=bool(hoy_data),
    ):
        # Banner informativo si ya hay datos de hoy
        if hoy_data:
            upd = hoy_data.get("updated_at")
            upd_str = upd.strftime("%H:%M") if hasattr(upd, "strftime") else str(upd)[:5]
            st.markdown(
                f"<div style='background:{_C_BG2};border:1px solid {_C_BORDER};"
                f"border-left:3px solid {_C_CYAN};border-radius:8px;"
                f"padding:8px 14px;font-size:0.80rem;color:{_C_GRAY};"
                f"margin-bottom:10px;'>"
                f"\u2705 Ya tienes datos registrados hoy (última actualización: "
                f"<b style='color:{_C_CYAN};'>{upd_str}</b>). "
                f"Edita los valores y vuelve a guardar.</div>",
                unsafe_allow_html=True,
            )

        with st.form(f"form_diario_{agente_id}_{hoy.isoformat()}"):
            c1, c2 = st.columns(2)
            with c1:
                docs_p = st.number_input(
                    "\U0001f4c4 Docs Personales",
                    min_value=0, step=1,
                    value=int(hoy_data.get("docs_personales") or 0),
                    key=f"dp_{agente_id}",
                )
                sanc   = st.number_input(
                    "\U0001f6e1\ufe0f Sanciones Revisadas",
                    min_value=0, step=1,
                    value=int(hoy_data.get("sanciones") or 0),
                    key=f"sa_{agente_id}",
                )
            with c2:
                docs_c = st.number_input(
                    "\U0001f4c4 Docs Comerciales",
                    min_value=0, step=1,
                    value=int(hoy_data.get("docs_comerciales") or 0),
                    key=f"dc_{agente_id}",
                )
                hs     = st.number_input(
                    "\U0001f6a8 Alertas Hardstop",
                    min_value=0, step=1,
                    value=int(hoy_data.get("hardstop") or 0),
                    key=f"hs_{agente_id}",
                )
            tx = st.number_input(
                "\U0001f504 TX Ongoing",
                min_value=0, step=1,
                value=int(hoy_data.get("tx_ongoing") or 0),
                key=f"tx_{agente_id}",
            )

            st.markdown(
                f"<div style='color:{_C_GRAY};font-size:0.72rem;text-transform:uppercase;"
                f"letter-spacing:0.8px;margin:14px 0 4px;border-top:1px solid {_C_BORDER};"
                f"padding-top:12px;'>\U0001f464 Cuentas Personales</div>",
                unsafe_allow_html=True,
            )
            cp1, cp2, cp3 = st.columns(3)
            with cp1:
                form_pers_aprobadas = st.number_input(
                    "\u2705 Aprobadas",
                    min_value=0, step=1,
                    value=int(agente_db.get("kpi_cuentas_pers_aprobadas") or 0),
                    key=f"cpa_{agente_id}",
                )
            with cp2:
                form_pers_rechazadas = st.number_input(
                    "\u274c Rechazadas",
                    min_value=0, step=1,
                    value=int(agente_db.get("kpi_cuentas_pers_rechazadas") or 0),
                    key=f"cpr_{agente_id}",
                )
            with cp3:
                form_pers_investigacion = st.number_input(
                    "\U0001f50d Investigaci\u00f3n",
                    min_value=0, step=1,
                    value=int(agente_db.get("kpi_cuentas_pers_investigacion") or 0),
                    key=f"cpi_{agente_id}",
                )

            st.markdown(
                f"<div style='color:{_C_GRAY};font-size:0.72rem;text-transform:uppercase;"
                f"letter-spacing:0.8px;margin:10px 0 4px;'>\U0001f3e2 Cuentas Comerciales</div>",
                unsafe_allow_html=True,
            )
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                form_com_aprobadas = st.number_input(
                    "\u2705 Aprobadas",
                    min_value=0, step=1,
                    value=int(agente_db.get("kpi_cuentas_com_aprobadas") or 0),
                    key=f"cca_{agente_id}",
                )
            with cc2:
                form_com_rechazadas = st.number_input(
                    "\u274c Rechazadas",
                    min_value=0, step=1,
                    value=int(agente_db.get("kpi_cuentas_com_rechazadas") or 0),
                    key=f"ccr_{agente_id}",
                )
            with cc3:
                form_com_investigacion = st.number_input(
                    "\U0001f50d Investigaci\u00f3n",
                    min_value=0, step=1,
                    value=int(agente_db.get("kpi_cuentas_com_investigacion") or 0),
                    key=f"cci_{agente_id}",
                )

            guardado = st.form_submit_button(
                "\U0001f4be Guardar Gesti\u00f3n",
                type="primary",
                use_container_width=True,
            )

        if guardado:
            try:
                with next(get_session()) as session:
                    repo = AgenteRepository(session)
                    repo.registrar_gestion_diaria(
                        agente_id,
                        {
                            "docs_personales":  docs_p,
                            "docs_comerciales": docs_c,
                            "sanciones":        sanc,
                            "hardstop":         hs,
                            "tx_ongoing":       tx,
                        },
                        admin_user=user,
                    )
                    repo.update(agente_id, {
                        "kpi_cuentas_pers_aprobadas":     int(form_pers_aprobadas),
                        "kpi_cuentas_pers_rechazadas":    int(form_pers_rechazadas),
                        "kpi_cuentas_pers_investigacion": int(form_pers_investigacion),
                        "kpi_cuentas_com_aprobadas":      int(form_com_aprobadas),
                        "kpi_cuentas_com_rechazadas":     int(form_com_rechazadas),
                        "kpi_cuentas_com_investigacion":  int(form_com_investigacion),
                    })
                st.success("\u2705 Gesti\u00f3n del d\u00eda guardada correctamente.")
                st.rerun()
            except Exception as exc:
                st.error(f"Error al guardar: {exc}")


# ─────────────────────────────────────────────────────────────
# KPIs especializados — Equipo Cumplimiento
# ─────────────────────────────────────────────────────────────

def _render_compliance_kpis(agente_db: dict, meta: int) -> None:
    """Cuadrícula de KPIs de rendimiento técnico para el equipo Cumplimiento.

    Muestra totales históricos acumulados de agente_kpi_diario y un banner
    con el resumen del día actual.  El formulario de registro se inyecta
    encima desde _tab_kpis.
    """
    from datetime import date
    from db.database import get_session
    from db.repositories.agente_repo import AgenteRepository

    agente_id = agente_db.get("id")

    # ── Cargar totales globales desde bitácora ────────────
    totales: dict = {
        "docs_personales_total": 0, "docs_comerciales_total": 0,
        "sanciones_total": 0, "hardstop_total": 0, "tx_ongoing_total": 0,
        "dias_registrados": 0,
    }
    hoy_data: dict = {}
    if agente_id:
        try:
            with next(get_session()) as session:
                stats    = AgenteRepository(session).get_stats_agente(agente_id)
                totales  = stats["totales"]
                hoy_data = stats["hoy"]
        except Exception as exc:
            st.warning(f"No se pudieron cargar los totales históricos: {exc}")

    # ── Banner de resumen de hoy ──────────────────────────
    hoy_str = date.today().strftime("%d/%m/%Y")
    if hoy_data:
        resumen_hoy = (
            f"\U0001f4c4 {int(hoy_data.get('docs_personales') or 0)} Docs Pers. &nbsp;&nbsp;"
            f"\U0001f4c4 {int(hoy_data.get('docs_comerciales') or 0)} Docs Com. &nbsp;&nbsp;"
            f"\U0001f6e1\ufe0f {int(hoy_data.get('sanciones') or 0)} Sanciones &nbsp;&nbsp;"
            f"\U0001f6a8 {int(hoy_data.get('hardstop') or 0)} Hardstop &nbsp;&nbsp;"
            f"\U0001f504 {int(hoy_data.get('tx_ongoing') or 0)} TX Ongoing"
        )
        st.markdown(
            f"<div style='background:{_C_BG2};border:1px solid {_C_BORDER};"
            f"border-left:3px solid {_C_CYAN};border-radius:8px;"
            f"padding:8px 16px;font-size:0.80rem;margin-bottom:14px;'>"
            f"<span style='color:{_C_GRAY};font-size:0.72rem;'>"
            f"Resumen de hoy ({hoy_str}):</span><br>"
            f"<span style='color:#f9fafb;'>{resumen_hoy}</span></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='background:{_C_BG2};border:1px dashed {_C_BORDER};"
            f"border-radius:8px;padding:8px 16px;font-size:0.80rem;"
            f"color:{_C_GRAY};margin-bottom:14px;'>"
            f"\u26a0\ufe0f Sin registro de hoy ({hoy_str}). Usa el formulario de arriba para registrar la gestión.</div>",
            unsafe_allow_html=True,
        )

    dias = totales["dias_registrados"]
    dias_suffix = (
        f" — {dias} d\u00eda{'s' if dias != 1 else ''} registrado{'s' if dias != 1 else ''}"
        if dias > 0 else ""
    )
    _section_title(f"\U0001f4ca Totales Hist\u00f3ricos Acumulados{dias_suffix}")

    def _kv(key: str) -> int:
        return int(agente_db.get(key) or 0)

    pers_aprobadas     = _kv("kpi_cuentas_pers_aprobadas")
    pers_rechazadas    = _kv("kpi_cuentas_pers_rechazadas")
    pers_investigacion = _kv("kpi_cuentas_pers_investigacion")
    com_aprobadas      = _kv("kpi_cuentas_com_aprobadas")
    com_rechazadas     = _kv("kpi_cuentas_com_rechazadas")
    com_investigacion  = _kv("kpi_cuentas_com_investigacion")
    total_activos = pers_aprobadas + com_aprobadas

    # ── Fila 1: Documentación ─────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        _kpi_card("Docs Personales", totales["docs_personales_total"], _C_CYAN,
                  "Total histórico — contratos tipo personal")
    with c2:
        _kpi_card("Docs Comerciales", totales["docs_comerciales_total"], _C_VIOLET,
                  "Total histórico — contratos tipo comercial")

    # ── Fila 2: Seguridad + TX Ongoing ────────────────────
    c3, c4 = st.columns(2)
    with c3:
        col_san = _C_CYAN if totales["sanciones_total"] > 0 else _C_GRAY
        _kpi_card("Sanciones Revisadas", totales["sanciones_total"], col_san,
                  "Total histórico — listas de sanciones verificadas")
    with c4:
        col_hs = _C_CYAN if totales["hardstop_total"] > 0 else _C_GRAY
        _kpi_card("Alertas Hardstop", totales["hardstop_total"], col_hs,
                  "Total histórico — alertas SARLAFT cerradas")

    # ── Fila 3: TX Ongoing + Partners Activos ─────────────
    c5, c6 = st.columns(2)
    with c5:
        _kpi_card("TX Ongoing Total", totales["tx_ongoing_total"], _C_CYAN,
                  "Total histórico — transacciones con due-diligence completado")
    with c6:
        col_tot = _C_GREEN if total_activos > 0 else _C_GRAY
        _kpi_card("Partners Aprobados", total_activos, col_tot,
                  "Cuentas aprobadas personal + comercial")

    # ── Progreso de meta ──────────────────────────────────
    progreso = min(total_activos / meta, 1.0) if meta > 0 else 0.0
    _section_title("\u26a1 Progreso de Meta — Partners Activos")
    st.markdown(
        f"<div style='color:{_C_GRAY};font-size:0.75rem;margin-bottom:6px;'>"
        f"<b style='color:#f9fafb;'>{total_activos}</b> aprobados (personal + comercial) "
        f"de una meta de <b style='color:#f9fafb;'>{meta}</b></div>",
        unsafe_allow_html=True,
    )
    st.progress(progreso)

    # ── Segmentación de Cuentas ────────────────────────────
    _section_title("\U0001f4b3 Segmentaci\u00f3n de Cuentas")
    seg_cols = st.columns(3)
    _SEG = [
        ("\u2705 Aprobadas",          pers_aprobadas,     com_aprobadas,     _C_GREEN),
        ("\u274c Rechazadas",         pers_rechazadas,    com_rechazadas,    _C_RED),
        ("\U0001f50d Investigaci\u00f3n", pers_investigacion, com_investigacion, _C_AMBER),
    ]
    for col, (label, pv, cv, color) in zip(seg_cols, _SEG):
        with col:
            st.markdown(
                f"<div style='background:{_C_BG};border:1px solid {_C_BORDER};"
                f"border-left:3px solid {color};border-radius:8px;"
                f"padding:10px 14px;'>"
                f"<div style='color:{color};font-size:0.70rem;font-weight:700;"
                f"text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px;'>{label}</div>"
                f"<div style='display:flex;justify-content:space-around;'>"
                f"<div style='text-align:center;'>"
                f"<div style='color:#f9fafb;font-size:1.4rem;font-weight:700;'>{pv}</div>"
                f"<div style='color:{_C_GRAY};font-size:0.68rem;margin-top:2px;'>Personal</div>"
                f"</div>"
                f"<div style='width:1px;background:{_C_BORDER};'></div>"
                f"<div style='text-align:center;'>"
                f"<div style='color:#f9fafb;font-size:1.4rem;font-weight:700;'>{cv}</div>"
                f"<div style='color:{_C_GRAY};font-size:0.68rem;margin-top:2px;'>Comercial</div>"
                f"</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────
# Tab: KPIs de Gestión
# ─────────────────────────────────────────────────────────────

def _render_kpis_cartera(agente_id: int, meta: int, equipo_color: str) -> None:
    """KPIs generales de cartera (pie charts + 4 tarjetas + barra de meta)."""
    metrics: dict = {
        "total_partners": 0, "partners_activos": 0, "partners_riesgo_alto": 0,
        "tasa_activacion_pct": 0.0, "distribucion_riesgo": {}, "distribucion_estado": {},
        "meta_mensual": meta,
    }

    if agente_id:
        try:
            from db.database import get_session
            from db.repositories.agente_repo import AgenteRepository
            with next(get_session()) as session:
                metrics = AgenteRepository(session).get_metrics(agente_id)
        except Exception as exc:
            st.error(f"Error cargando m\u00e9tricas: {exc}")
            return

    total   = metrics["total_partners"]
    activos = metrics["partners_activos"]
    alto    = metrics["partners_riesgo_alto"]
    tasa    = metrics["tasa_activacion_pct"]

    _section_title("\U0001f4ca Resumen de Cartera")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        _kpi_card("Partners Asignados", total, equipo_color)
    with k2:
        _kpi_card("Partners Activos", activos, _C_GREEN if activos > 0 else _C_GRAY)
    with k3:
        _kpi_card("Riesgo Alto / Muy Alto", alto, _C_RED if alto > 0 else _C_GREEN)
    with k4:
        c_tasa = _C_GREEN if tasa >= 70 else _C_AMBER if tasa >= 40 else _C_RED
        _kpi_card("Tasa de Activaci\u00f3n", f"{tasa}%", c_tasa, "Partners activos / total")

    if total == 0:
        st.markdown(
            f"<div style='color:{_C_GRAY};font-style:italic;font-size:0.85rem;"
            f"padding:24px 0;text-align:center;'>"
            "Sin partners asignados a este colaborador a\u00fan.<br>"
            "Asigna partners desde el m\u00f3dulo <b>\U0001f91d Partners</b> "
            "usando el campo <b>Agente Gestor</b>.</div>",
            unsafe_allow_html=True,
        )
        return

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    col_pie1, col_pie2 = st.columns(2)

    with col_pie1:
        _section_title("\U0001f50d Foco de Riesgo")
        dist_riesgo = metrics["distribucion_riesgo"]
        if dist_riesgo:
            labels = list(dist_riesgo.keys())
            values = list(dist_riesgo.values())
            colors = [_COLORES_RIESGO.get(lbl, _C_GRAY) for lbl in labels]
            fig = go.Figure(data=[go.Pie(
                labels=labels, values=values,
                marker=dict(colors=colors, line=dict(color=_C_BG2, width=2)),
                hole=0.55, textfont=dict(size=11, color="#f9fafb"),
                hovertemplate="<b>%{label}</b><br>%{value} (%{percent})<extra></extra>",
            )])
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=10, b=0), height=220,
                legend=dict(font=dict(color=_C_GRAY, size=11), bgcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_pie2:
        _section_title("\U0001f4cb Estado del Pipeline")
        dist_estado = metrics["distribucion_estado"]
        if dist_estado:
            _COL_PIPELINE = {
                "Prospecto":      "#6b7280",
                "En Calificaci\u00f3n": _C_AMBER,
                "Onboarding":     _C_VIOLET,
                "Activo":         _C_GREEN,
                "Suspendido":     _C_RED,
                "Terminado":      "#374151",
            }
            labels = list(dist_estado.keys())
            values = list(dist_estado.values())
            colors = [_COL_PIPELINE.get(lbl, _C_GRAY) for lbl in labels]
            fig2 = go.Figure(data=[go.Pie(
                labels=labels, values=values,
                marker=dict(colors=colors, line=dict(color=_C_BG2, width=2)),
                hole=0.55, textfont=dict(size=11, color="#f9fafb"),
                hovertemplate="<b>%{label}</b><br>%{value} (%{percent})<extra></extra>",
            )])
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=10, b=0), height=220,
                legend=dict(font=dict(color=_C_GRAY, size=11), bgcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    _section_title("\u26a1 Progreso de Meta \u2014 Partners Activos")
    progreso = min(activos / meta, 1.0) if meta > 0 else 0.0
    st.markdown(
        f"<div style='color:{_C_GRAY};font-size:0.75rem;margin-bottom:6px;'>"
        f"<b style='color:#f9fafb;'>{activos}</b> partners activos "
        f"de una meta de <b style='color:#f9fafb;'>{meta}</b></div>",
        unsafe_allow_html=True,
    )
    st.progress(progreso)


def _tab_kpis(agente_db: Optional[dict], equipo_color: str, user: Optional[dict] = None) -> None:
    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    if not agente_db:
        st.info(
            "Este colaborador no está registrado en la base de datos. "
            "Usa **\U0001f465 Gesti\u00f3n de Agentes** para agregarlo."
        )
        return

    agente_id = agente_db.get("id")
    meta      = int(agente_db.get("meta_mensual_gestiones") or 50)
    equipo    = agente_db.get("equipo", "")

    if equipo == "Cumplimiento":
        # Formulario de registro diario (siempre visible arriba)
        _form_registro_diario(agente_db, user)
        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

        tab_dash, tab_cartera = st.tabs([
            "\U0001f4c8 Dashboard de Rendimiento",
            "\U0001f4ca Cartera General",
        ])
        with tab_dash:
            _render_compliance_kpis(agente_db, meta)
        with tab_cartera:
            _render_kpis_cartera(agente_id, meta, equipo_color)
    else:
        _render_kpis_cartera(agente_id, meta, equipo_color)


# ─────────────────────────────────────────────────────────────
# Tab: Información del Collaborador
# ─────────────────────────────────────────────────────────────

def _tab_info(agente_db: Optional[dict], user: Optional[dict]) -> None:
    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    if not agente_db:
        st.info("Colaborador sin registro en la base de datos.")
        return

    es_admin = bool(user and user.get("rol") == "admin")

    _section_title("\U0001f4cb Ficha de Contacto")
    _email_val    = agente_db.get("email")    or "\u2014"
    _telefono_val = agente_db.get("telefono") or "\u2014"
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"<div style='color:{_C_GRAY};font-size:0.72rem;text-transform:uppercase;"
            f"letter-spacing:0.8px;margin-bottom:4px;'>Email</div>"
            f"<div style='color:#f9fafb;font-size:0.92rem;'>{_email_val}</div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"<div style='color:{_C_GRAY};font-size:0.72rem;text-transform:uppercase;"
            f"letter-spacing:0.8px;margin-bottom:4px;'>Tel\u00e9fono</div>"
            f"<div style='color:#f9fafb;font-size:0.92rem;'>{_telefono_val}</div>",
            unsafe_allow_html=True,
        )

    notas = agente_db.get("notas")
    if notas:
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        _section_title("\U0001f4dd Observaciones Internas")
        st.markdown(
            f"<div style='background:{_C_BG2};border-radius:8px;padding:14px 16px;"
            f"border-left:3px solid {_C_BORDER};color:#d1d5db;font-size:0.85rem;"
            f"line-height:1.6;'>{notas}</div>",
            unsafe_allow_html=True,
        )

    if not es_admin:
        return

    _section_title("\u270f\ufe0f Editar Informaci\u00f3n")
    from db.database import get_session
    from db.repositories.agente_repo import AgenteRepository
    from db.repositories.audit_repo import AuditRepository

    with st.form(f"form_info_{agente_db['id']}"):
        f1, f2 = st.columns(2)
        with f1:
            email_e = st.text_input("Email",    value=agente_db.get("email") or "")
            cargo_e = st.text_input("Cargo",    value=agente_db.get("cargo") or "")
        with f2:
            tel_e   = st.text_input("Tel\u00e9fono", value=agente_db.get("telefono") or "")
            meta_e  = st.number_input(
                "Meta de Partners Activos",
                min_value=1, max_value=500,
                value=int(agente_db.get("meta_mensual_gestiones") or 50),
            )
        notas_e  = st.text_area("Observaciones Internas", value=agente_db.get("notas") or "")
        activo_e = st.toggle("Colaborador activo", value=bool(agente_db.get("activo", True)))

        if st.form_submit_button("\U0001f4be Guardar", type="primary"):
            fields = {
                "email":                  email_e.strip() or None,
                "cargo":                  cargo_e.strip() or None,
                "telefono":               tel_e.strip() or None,
                "meta_mensual_gestiones": int(meta_e),
                "notas":                  notas_e.strip() or None,
                "activo":                 activo_e,
            }
            try:
                with next(get_session()) as session:
                    AgenteRepository(session).update(agente_db["id"], fields)
                    AuditRepository(session).registrar(
                        username=user["username"],
                        usuario_id=user["id"],
                        accion="UPDATE",
                        entidad="agentes",
                        entidad_id=agente_db["id"],
                        descripcion=f"Perfil actualizado: {agente_db['username']}",
                        valores_anteriores={k: agente_db.get(k) for k in fields},
                        valores_nuevos=fields,
                    )
                st.success("Informaci\u00f3n guardada correctamente.")
                st.rerun()
            except Exception as exc:
                st.error(f"Error al guardar: {exc}")


# ─────────────────────────────────────────────────────────────
# Tab: Timeline de Actividad del Catálogo
# ─────────────────────────────────────────────────────────────

def _tab_actividad(agente_db: Optional[dict]) -> None:
    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    if not agente_db:
        st.info("Colaborador sin registro en la base de datos.")
        return

    _ACCIONES_COLOR: dict[str, str] = {
        "CREATE":       _C_GREEN,
        "UPDATE":       _C_CYAN,
        "DELETE":       _C_RED,
        "LOGIN":        _C_VIOLET,
        "EXPORT":       _C_AMBER,
        "ESTADO_CHANGE": "#f97316",
    }

    try:
        from db.database import get_session
        from db.repositories.audit_repo import AuditRepository
        with next(get_session()) as session:
            entradas = AuditRepository(session).get_actividad_agente(agente_db["id"], limit=5)
    except Exception as exc:
        st.error(f"Error cargando actividad: {exc}")
        return

    _section_title("\U0001f4c5 \u00daltimas Acciones del Sistema")

    if not entradas:
        st.markdown(
            f"<div style='color:{_C_GRAY};font-style:italic;font-size:0.85rem;"
            f"padding:16px 0;text-align:center;'>Sin actividad registrada a\u00fan.</div>",
            unsafe_allow_html=True,
        )
        return

    for entrada in entradas:
        accion = entrada.get("accion", "UPDATE")
        color  = _ACCIONES_COLOR.get(accion, _C_GRAY)
        ts     = entrada.get("created_at")
        fecha  = ts.strftime("%d/%m/%Y %H:%M") if hasattr(ts, "strftime") else str(ts)[:16]
        desc   = entrada.get("descripcion") or "\u2014"
        usr    = entrada.get("username") or "\u2014"
        resultado = entrada.get("resultado", "exitoso")
        res_color = _C_GREEN if resultado == "exitoso" else _C_RED
        st.markdown(
            f"<div style='background:{_C_BG};border-radius:8px;padding:10px 14px;"
            f"border-left:3px solid {color};margin-bottom:8px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<span style='background:{color}22;color:{color};border-radius:9999px;"
            f"padding:1px 10px;font-size:10px;font-weight:700;'>{accion}</span>"
            f"<span style='color:{_C_GRAY};font-size:0.72rem;'>{fecha}</span>"
            f"</div>"
            f"<div style='color:#f9fafb;font-size:0.82rem;margin-top:6px;line-height:1.4;'>{desc}</div>"
            f"<div style='display:flex;justify-content:space-between;margin-top:4px;'>"
            f"<span style='color:{_C_GRAY};font-size:0.72rem;'>por {usr}</span>"
            f"<span style='color:{res_color};font-size:0.70rem;font-weight:600;'>\u25cf {resultado}</span>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────
# Vista del Perfil
# ─────────────────────────────────────────────────────────────

def render_perfil_agente(username: str, user: Optional[dict] = None) -> None:
    """Vista informativa del colaborador: KPIs de cartera y ficha de contacto."""
    from db.database import get_session
    from db.repositories.agente_repo import AgenteRepository

    agente_db: Optional[dict] = None
    try:
        with next(get_session()) as session:
            agente_db = AgenteRepository(session).get_by_username(username)
    except Exception as exc:
        st.warning(f"No se pudo conectar con la base de datos: {exc}")

    if agente_db:
        eq_raw       = agente_db.get("equipo", "")
        equipo_label = f"{_EQUIPOS_ICONOS.get(eq_raw, chr(0x1f464))} {eq_raw}"
        equipo_color = _EQUIPOS_COLORES.get(eq_raw, _C_GRAY)
        nombre   = agente_db["nombre_completo"]
        cargo    = agente_db.get("cargo") or "Colaborador"
        email    = agente_db.get("email") or ""
        telefono = agente_db.get("telefono") or ""
    else:
        equipo_label = _USERNAME_TO_EQUIPO.get(username, "Sin equipo")
        equipo_color = EQUIPOS.get(equipo_label, {}).get("color", _C_GRAY)
        fallback = next(
            (a for info in EQUIPOS.values() for a in info["agentes"] if a["username"] == username),
            None,
        )
        nombre   = fallback["nombre"] if fallback else username
        cargo    = fallback["cargo"]  if fallback else "Colaborador"
        email    = ""
        telefono = ""

    _render_header_agente(username, nombre, cargo, equipo_label, equipo_color, email, telefono)

    tab_kpis, tab_info, tab_hist = st.tabs([
        "\U0001f4c8 KPIs de Gesti\u00f3n",
        "\U0001f4cb Informaci\u00f3n",
        "\U0001f4c5 Actividad",
    ])
    with tab_kpis:
        _tab_kpis(agente_db, equipo_color, user)
    with tab_info:
        _tab_info(agente_db, user)
    with tab_hist:
        _tab_actividad(agente_db)


# ─────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────
# Editor de KPIs Inline — Gestión de Rendimiento
# ─────────────────────────────────────────────────────────────

# Etiquetas de columna para el st.data_editor
_KPI_LABELS: dict[str, str] = {
    "kpi_docs_personales":  "Docs Personales",
    "kpi_docs_comerciales": "Docs Comerciales",
    "kpi_sanciones_revisadas": "Sanciones Revisadas",
    "kpi_alertas_hardstop": "Hardstop Resueltos",
    "kpi_tx_ongoing":       "TX Ongoing",
}


def _panel_rendimiento(user: dict) -> None:
    """
    Editor de tabla inline para actualizar los KPIs manuales de los agentes.

    - Admin: ve todos los equipos.
    - Compliance: ve únicamente el equipo Cumplimiento.
    """
    from config.settings import Roles

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    rol       = user.get("rol", "")
    es_admin  = rol == Roles.ADMIN
    equipo_filtro: Optional[str] = None if es_admin else "Cumplimiento"

    # ── Cargar tabla desde BD ─────────────────────────────
    import pandas as pd
    from db.database import get_session
    from db.repositories.agente_repo import AgenteRepository

    try:
        with next(get_session()) as session:
            df_original = AgenteRepository(session).get_kpi_table(equipo=equipo_filtro)
    except Exception as exc:
        st.error(f"Error al cargar la tabla de rendimiento: {exc}")
        return

    if df_original.empty:
        st.info("No hay colaboradores activos para el equipo seleccionado.")
        return

    # ── Instrucción contextual ────────────────────────────
    scope_label = "todos los equipos" if es_admin else "equipo **Cumplimiento**"
    st.markdown(
        f"<div style='color:{_C_GRAY};font-size:0.82rem;margin-bottom:12px;'>"
        f"Edita los KPIs directamente en la tabla ({scope_label}). "
        f"Solo se guardan las filas que hayan cambiado. "
        f"Cada modificación queda registrada en el log de auditoría.</div>",
        unsafe_allow_html=True,
    )

    # ── Configuración del editor ──────────────────────────
    col_cfg = {
        "id":             None,                         # oculto — clave interna
        "username":       st.column_config.TextColumn(
                              "Username", disabled=True, width="medium"),
        "nombre_completo": st.column_config.TextColumn(
                              "Nombre", disabled=True, width="large"),
        "equipo":         st.column_config.TextColumn(
                              "Equipo", disabled=True, width="small"),
        "cargo":          st.column_config.TextColumn(
                              "Cargo", disabled=True, width="medium"),
    }
    for col, label in _KPI_LABELS.items():
        col_cfg[col] = st.column_config.NumberColumn(
            label,
            min_value=0,
            step=1,
            format="%d",
            width="small",
        )

    df_editado = st.data_editor(
        df_original,
        column_config=col_cfg,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="editor_kpis_rendimiento",
    )

    # ── Botón de sincronización ───────────────────────────
    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
    if st.button(
        "\U0001f4be Sincronizar Cambios",
        type="primary",
        key="btn_sync_kpis",
    ):
        try:
            with next(get_session()) as session:
                resultado = AgenteRepository(session).update_kpis_from_editor(
                    df_editado, usuario=user
                )
            n = resultado["actualizados"]
            if n > 0:
                st.success(
                    f"\u2705 **{n}** colaborador{'es' if n != 1 else ''} "
                    f"actualizado{'s' if n != 1 else ''} correctamente."
                )
            else:
                st.info("No se detectaron cambios respecto a los valores actuales.")
            st.rerun()
        except ValueError as exc:
            st.error(f"\u274c Error de datos: {exc}")
        except Exception as exc:
            st.error(f"\u274c Error inesperado: {exc}")


# ─────────────────────────────────────────────────────────────
# Panel de Gestión del Catálogo (ADMIN + COMPLIANCE)
# ─────────────────────────────────────────────────────────────

def render_gestion_agentes(user: dict) -> None:
    from config.settings import Roles

    st.markdown("<h1>\U0001f465 Gesti\u00f3n de Equipos</h1>", unsafe_allow_html=True)
    st.markdown(
        f"<p style='color:{_C_GRAY};font-size:0.88rem;margin-top:-8px;margin-bottom:16px;'>"
        "Administra el cat\u00e1logo de colaboradores por equipo. "
        "Los agentes <b>no acceden al sistema</b> \u2014 m\u00f3dulo de uso exclusivo para gerencia.</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr style='border-color:#293056;'>", unsafe_allow_html=True)

    rol      = user.get("rol", "")
    es_admin = rol == Roles.ADMIN
    puede_ver_rendimiento = rol in (Roles.ADMIN, Roles.COMPLIANCE)

    if not puede_ver_rendimiento:
        st.error("Acceso restringido. Solo administradores y el equipo de Compliance pueden acceder.")
        return

    if es_admin:
        tab_vista, tab_nuevo, tab_editar, tab_rend = st.tabs([
            "\U0001f3e2 Vista por Equipo",
            "\u2795 Nuevo Colaborador",
            "\u270f\ufe0f Editar Colaborador",
            "\U0001f4ca Gesti\u00f3n de Rendimiento",
        ])
        with tab_vista:
            _panel_vista_equipos()
        with tab_nuevo:
            _form_nuevo_agente(user)
        with tab_editar:
            _form_editar_agente(user)
        with tab_rend:
            _panel_rendimiento(user)
    else:
        # Rol Compliance: solo acceso al editor de KPIs
        (tab_rend,) = st.tabs(["\U0001f4ca Gesti\u00f3n de Rendimiento"])
        with tab_rend:
            _panel_rendimiento(user)


def _panel_vista_equipos() -> None:
    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
    try:
        from db.database import get_session
        from db.repositories.agente_repo import AgenteRepository
        with next(get_session()) as session:
            agentes = AgenteRepository(session).get_all()
    except Exception as exc:
        st.error(f"Error al cargar cat\u00e1logo: {exc}")
        return

    if not agentes:
        st.info(
            "El cat\u00e1logo est\u00e1 vac\u00edo. "
            "Usa la pesta\u00f1a **\u2795 Nuevo Colaborador** para registrar miembros del equipo."
        )
        return

    por_equipo: dict[str, list] = {}
    for ag in agentes:
        eq = ag.get("equipo", "Otro")
        por_equipo.setdefault(eq, []).append(ag)

    for equipo, miembros in por_equipo.items():
        color        = _EQUIPOS_COLORES.get(equipo, _C_GRAY)
        icono        = _EQUIPOS_ICONOS.get(equipo, "\U0001f464")
        activos_eq   = sum(1 for m in miembros if m.get("activo"))

        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;margin:20px 0 12px;'>"
            f"<span style='font-size:1.1rem;'>{icono}</span>"
            f"<span style='color:{color};font-size:0.80rem;font-weight:700;"
            f"text-transform:uppercase;letter-spacing:1px;'>{equipo}</span>"
            f"<span style='color:{_C_GRAY};font-size:0.75rem;'>"
            f"\u2014 {activos_eq} activo{'s' if activos_eq != 1 else ''}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        cols = st.columns(min(len(miembros), 3))
        for i, ag in enumerate(miembros):
            with cols[i % 3]:
                foto   = _foto_base64(ag["username"])
                activo = ag.get("activo", True)
                alpha  = "ff" if activo else "44"
                if foto:
                    av = (
                        f"<img src='{foto}' style='width:44px;height:44px;border-radius:50%;"
                        f"object-fit:cover;border:2px solid {color}{alpha};flex-shrink:0;"
                        f"opacity:{'1' if activo else '0.5'};'>"
                    )
                else:
                    inicial = ag["nombre_completo"][0].upper()
                    av = (
                        f"<div style='width:44px;height:44px;border-radius:50%;flex-shrink:0;"
                        f"background:{color}22;border:2px solid {color}{alpha};"
                        f"display:flex;align-items:center;justify-content:center;"
                        f"color:{color};font-size:1.1rem;font-weight:800;"
                        f"opacity:{'1' if activo else '0.5'};'>{inicial}</div>"
                    )
                estado_badge = (
                    f"<span style='color:{_C_GREEN};font-size:9px;font-weight:700;'>\u25cf ACTIVO</span>"
                    if activo else
                    f"<span style='color:{_C_GRAY};font-size:9px;font-weight:700;'>\u25cf INACTIVO</span>"
                )
                _nombre_ag = ag["nombre_completo"]
                _cargo_ag  = ag.get("cargo") or "\u2014"
                _opac_ag   = "opacity:.5;" if not activo else ""
                st.markdown(
                    f"""
                    <div style='background:{_C_BG};border-radius:10px;padding:12px 14px;
                                border:1px solid {_C_BORDER};margin-bottom:8px;'>
                        <div style='display:flex;align-items:center;gap:10px;'>
                            {av}
                            <div>
                                <div style='color:#f9fafb;font-size:0.85rem;font-weight:600;
                                            {_opac_ag}'
                                >{_nombre_ag}</div>
                                <div style='color:{_C_GRAY};font-size:0.72rem;'>
                                    {_cargo_ag}</div>
                                <div style='margin-top:3px;'>{estado_badge}</div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def _form_nuevo_agente(user: dict) -> None:
    from db.database import get_session
    from db.repositories.agente_repo import AgenteRepository
    from db.repositories.audit_repo import AuditRepository

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    with st.form("form_nuevo_agente", clear_on_submit=True):
        st.markdown('<p class="section-title">Datos del Nuevo Colaborador</p>',
                    unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            nombre   = st.text_input("Nombre Completo *")
            username = st.text_input(
                "Identificador *",
                placeholder="ej: maria_garcia",
                help="Solo min\u00fasculas, n\u00fameros y guion bajo. Ej: maria_garcia, juan01. Sin espacios ni acentos.",
            )
            email    = st.text_input("Email corporativo")
        with c2:
            equipo   = st.selectbox("Equipo *", ["Cumplimiento", "Pagos", "Soporte"], key="nuevo_equipo")
            _cargos_opts = _CARGOS_POR_EQUIPO.get(equipo, []) + [_CARGO_OTRO]
            cargo    = st.selectbox("Cargo *", _cargos_opts, key="nuevo_cargo")
            telefono = st.text_input("Tel\u00e9fono")
        meta  = st.number_input(
            "Meta de Partners Activos (mensual)", min_value=1, max_value=500, value=50
        )
        notas = st.text_area(
            "Observaciones internas (opcional)",
            placeholder="Ej: Especialista en clientes fintech de alto riesgo...",
        )
        if st.form_submit_button("\u2705 Registrar Colaborador", type="primary"):
            from db.models import AgenteCreate
            from pydantic import ValidationError
            # ── Pydantic validation ───────────────────────────
            # Sanitizar username: minúsculas, espacios→_, quitar caracteres no permitidos
            import re as _re
            username_clean = _re.sub(r"[^a-z0-9_]", "", username.strip().lower().replace(" ", "_").replace("-", "_"))
            try:
                datos = AgenteCreate(
                    username=username_clean,
                    nombre_completo=nombre.strip(),
                    equipo=equipo,
                    cargo=cargo.strip() or None,
                    email=email.strip() or None,
                    telefono=telefono.strip() or None,
                    meta_mensual_gestiones=int(meta),
                    notas=notas.strip() or None,
                )
            except ValidationError as ve:
                for err in ve.errors():
                    campo = str(err["loc"][0]) if err["loc"] else "campo"
                    msg = err["msg"]
                    if campo == "username" and "pattern" in msg:
                        msg = f"Solo se permiten min\u00fasculas, n\u00fameros y guion bajo. Valor recibido: '{username_clean}'"
                    st.error(f"\u274c **{campo}**: {msg}")
                return
            # ── Persistencia ─────────────────────────────────
            try:
                with next(get_session()) as session:
                    repo  = AgenteRepository(session)
                    audit = AuditRepository(session)
                    if repo.username_exists(datos.username):
                        st.error(f"El identificador '**{datos.username}**' ya est\u00e1 en uso.")
                        return
                    nuevo_id = repo.create(
                        username=datos.username,
                        nombre_completo=datos.nombre_completo,
                        equipo=datos.equipo,
                        cargo=datos.cargo,
                        email=datos.email,
                        telefono=datos.telefono,
                        meta_mensual_gestiones=datos.meta_mensual_gestiones,
                        notas=datos.notas,
                    )
                    audit.registrar(
                        username=user["username"],
                        usuario_id=user["id"],
                        accion="CREATE",
                        entidad="agentes",
                        entidad_id=nuevo_id,
                        descripcion=(
                            f"Colaborador registrado: {datos.nombre_completo} ({datos.equipo})"
                        ),
                        valores_nuevos=datos.model_dump(exclude_none=True),
                    )
                st.success(
                    f"\u2705 **{datos.nombre_completo}** registrado en "
                    f"**{datos.equipo}** (ID #{nuevo_id})."
                )
            except Exception as exc:
                st.error(f"Error al registrar: {exc}")


def _form_editar_agente(user: dict) -> None:
    from db.database import get_session
    from db.repositories.agente_repo import AgenteRepository
    from db.repositories.audit_repo import AuditRepository

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    try:
        with next(get_session()) as session:
            agentes = AgenteRepository(session).get_all()
    except Exception as exc:
        st.error(f"Error cargando cat\u00e1logo: {exc}")
        return

    if not agentes:
        st.info("No hay colaboradores registrados a\u00fan.")
        return

    opciones = {
        f"{a['nombre_completo']} \u2014 {a['equipo']} ({'activo' if a.get('activo') else 'inactivo'})": a
        for a in agentes
    }
    sel    = st.selectbox(
        "Seleccionar colaborador", list(opciones.keys()), key="sel_editar_agente"
    )
    agente = opciones[sel]
    eq_opts = ["Cumplimiento", "Pagos", "Soporte"]
    eq_idx  = eq_opts.index(agente["equipo"]) if agente["equipo"] in eq_opts else 0

    with st.form(f"form_edit_{agente['username']}"):
        st.markdown('<p class="section-title">Editar Datos del Colaborador</p>',
                    unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            nombre_e = st.text_input("Nombre Completo", value=agente.get("nombre_completo") or "")
            email_e  = st.text_input("Email",           value=agente.get("email") or "")
            _cargos_e = _CARGOS_POR_EQUIPO.get(agente.get("equipo", ""), []) + [_CARGO_OTRO]
            _cargo_actual = agente.get("cargo") or ""
            _cargo_idx = _cargos_e.index(_cargo_actual) if _cargo_actual in _cargos_e else 0
            cargo_e  = st.selectbox("Cargo", _cargos_e, index=_cargo_idx,
                                    key=f"edit_cargo_{agente['id']}")
        with c2:
            equipo_e = st.selectbox("Equipo", eq_opts, index=eq_idx)
            tel_e    = st.text_input("Tel\u00e9fono",   value=agente.get("telefono") or "")
            meta_e   = st.number_input(
                "Meta de Partners Activos",
                min_value=1, max_value=500,
                value=int(agente.get("meta_mensual_gestiones") or 50),
            )
        notas_e  = st.text_area("Observaciones internas", value=agente.get("notas") or "")
        activo_e = st.toggle("Colaborador activo", value=bool(agente.get("activo", True)))

        if st.form_submit_button("\U0001f4be Guardar Cambios", type="primary"):
            fields = {
                "nombre_completo":        nombre_e.strip(),
                "equipo":                 equipo_e,
                "cargo":                  cargo_e.strip() or None,
                "email":                  email_e.strip() or None,
                "telefono":               tel_e.strip() or None,
                "meta_mensual_gestiones": int(meta_e),
                "notas":                  notas_e.strip() or None,
                "activo":                 activo_e,
            }
            try:
                with next(get_session()) as session:
                    AgenteRepository(session).update(agente["id"], fields)
                    AuditRepository(session).registrar(
                        username=user["username"],
                        usuario_id=user["id"],
                        accion="UPDATE",
                        entidad="agentes",
                        entidad_id=agente["id"],
                        descripcion=f"Colaborador actualizado: {agente['username']}",
                        valores_anteriores={k: agente.get(k) for k in fields},
                        valores_nuevos=fields,
                    )
                st.success(f"\u2705 **{agente['nombre_completo']}** actualizado correctamente.")
                st.rerun()
            except Exception as exc:
                st.error(f"Error al guardar: {exc}")
