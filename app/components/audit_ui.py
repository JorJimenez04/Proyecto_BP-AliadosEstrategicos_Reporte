"""
app/components/audit_ui.py
Vista del Log de Auditoría — AdamoServices Partner Manager.
Solo accesible para roles admin y compliance.
"""

import streamlit as st
from db.database import get_session
from db.repositories.audit_repo import AuditRepository
from config.settings import Roles


_COLOR_ACCION = {
    "CREATE":        "#5fe9d0",
    "UPDATE":        "#60a5fa",
    "DELETE":        "#ef4444",
    "LOGIN":         "#9ca3af",
    "EXPORT":        "#f59e0b",
    "ESTADO_CHANGE": "#7839ee",
}


def page_auditoria(user: dict):
    if user["rol"] not in (Roles.ADMIN, Roles.COMPLIANCE):
        st.error("⛔ Acceso restringido — Solo administradores y compliance.")
        return

    st.markdown("<h1>📋 Log de Auditoría</h1>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#293056;'>", unsafe_allow_html=True)

    # ── Filtros ───────────────────────────────────────────────────────────────
    with st.expander("🔍 Filtros", expanded=False):
        fa1, fa2, fa3, fa4 = st.columns(4)
        with fa1:
            filtro_accion = st.selectbox(
                "Acción",
                ["Todas", "CREATE", "UPDATE", "DELETE", "LOGIN", "EXPORT", "ESTADO_CHANGE"],
            )
        with fa2:
            filtro_entidad = st.selectbox(
                "Entidad", ["Todas", "aliados", "usuarios", "revisiones_sarlaft"]
            )
        with fa3:
            filtro_desde = st.date_input("Desde", value=None)
        with fa4:
            filtro_hasta = st.date_input("Hasta", value=None)

    with next(get_session()) as session:
        audit = AuditRepository(session)
        registros = audit.list_log(
            accion=None if filtro_accion == "Todas" else filtro_accion,
            entidad=None if filtro_entidad == "Todas" else filtro_entidad,
            fecha_desde=str(filtro_desde) if filtro_desde else None,
            fecha_hasta=str(filtro_hasta) if filtro_hasta else None,
            limit=300,
        )

    if not registros:
        st.info("Sin registros de auditoría con los filtros seleccionados.")
        return

    st.markdown(f"**{len(registros)}** registro(s)")

    for r in registros:
        color = _COLOR_ACCION.get(r.get("accion", ""), "#9ca3af")
        resultado_color = "#5fe9d0" if r.get("resultado") == "exitoso" else "#ef4444"
        st.markdown(
            f"""
            <div style='background:#1f2937;border-radius:8px;padding:12px 16px;
                        margin-bottom:6px;border-left:3px solid {color};'>
                <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <span style='color:{color};font-weight:700;font-size:0.85rem;'>{r.get("accion","")}</span>
                    <span style='color:#9ca3af;font-size:0.75rem;'>{r.get("created_at","")}</span>
                </div>
                <div style='color:#f9fafb;font-size:0.88rem;margin:4px 0;'>{r.get("descripcion","")}</div>
                <div style='color:#9ca3af;font-size:0.75rem;'>
                    👤 {r.get("username","")} &nbsp;|&nbsp;
                    📁 {r.get("entidad","")} #{r.get("entidad_id","—")} &nbsp;|&nbsp;
                    <span style='color:{resultado_color};'>{r.get("resultado","")}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
