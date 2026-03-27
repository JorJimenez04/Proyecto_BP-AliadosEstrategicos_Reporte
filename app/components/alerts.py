"""
app/components/alerts.py
Centro de Notificaciones de Compliance — AdamoServices Partner Manager.

Renderiza el panel de alertas SARLAFT vencidas con botones de Acción Rápida
para iniciar la re-calificación directamente desde el Dashboard.
"""

import streamlit as st
from config.settings import EstadosAliado


def _riesgo_color(nivel: str) -> str:
    return {
        "Bajo": "#5fe9d0", "Medio": "#f59e0b",
        "Alto": "#fb923c", "Muy Alto": "#ef4444",
    }.get(nivel, "#9ca3af")


def render_centro_notificaciones(repo, session, user: dict) -> None:
    """
    Centro de Notificaciones de Compliance.

    Muestra:
    - Banner de criticidad cuando hay revisiones SARLAFT vencidas.
    - Cards de aliados con SARLAFT vencido + botón 'Acción Rápida' para
      iniciar la re-calificación (Monitoreo Intensificado — GAFI R.1).
    - Cards de próximas revisiones dentro de 30 días.

    Parámetros:
        repo    — instancia de PartnerRepository ya abierta.
        session — SQLAlchemy Session activa (para AuditRepository).
        user    — dict con id, username, rol del usuario en sesión.
    """
    from db.repositories.audit_repo import AuditRepository

    vencidas = repo.get_sarlaft_vencidas()
    proximas  = repo.get_revisiones_proximas(dias=30)
    n_v = len(vencidas)
    n_p = len(proximas)

    if not n_v and not n_p:
        st.success(
            "✅ Sin alertas de cumplimiento activas. "
            "Portafolio al día conforme SARLAFT Colombia."
        )
        return

    # ── Banner crítico ────────────────────────────────────────────────────────
    if n_v:
        st.markdown(f"""
        <div style='
            background: linear-gradient(90deg, rgba(239,68,68,0.14), rgba(239,68,68,0.04));
            border: 1px solid #ef4444;
            border-left: 5px solid #ef4444;
            border-radius: 10px;
            padding: 14px 20px;
            margin-bottom: 20px;'>
            <div style='display:flex; align-items:center; gap:14px;'>
                <span style='font-size:1.6rem; line-height:1;'>🚨</span>
                <div>
                    <div style='color:#ef4444; font-size:0.95rem; font-weight:800;
                        letter-spacing:0.3px; text-transform:uppercase;'>
                        Alerta Crítica — Revisiones SARLAFT Vencidas
                    </div>
                    <div style='color:#fca5a5; font-size:0.82rem; margin-top:3px;'>
                        <strong>{n_v}</strong> aliado(s) con revisión vencida ·
                        Riesgo de incumplimiento normativo ·
                        CSBF / Circular 027 de 2020 · GAFI Recomendación 1
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Cards: SARLAFT Vencidas + Acción Rápida ───────────────────────────────
    if n_v:
        st.markdown(
            "<div class='section-title'>"
            "⛔ Monitoreo Intensificado — SARLAFT Vencido"
            "</div>",
            unsafe_allow_html=True,
        )
        cols = st.columns(min(n_v, 3))
        for idx, p in enumerate(vencidas):
            nc           = _riesgo_color(p.get("nivel_riesgo", ""))
            risk         = p.get("nivel_riesgo", "—")
            pep_tag      = " · ⚠️ PEP" if p.get("es_pep") else ""
            fecha        = p.get("fecha_proxima_revision", "N/D")
            score        = int(p.get("puntaje_riesgo") or 0)
            estado_actual = p.get("estado_pipeline", "")
            can_recalify = "En Calificación" in EstadosAliado.TRANSICIONES.get(estado_actual, [])

            with cols[idx % len(cols)]:
                # Tarjeta visual
                st.markdown(f"""
                <div style='
                    background:#111927;
                    border:1px solid #ef4444;
                    border-top:4px solid {nc};
                    border-radius:10px;
                    padding:14px 16px;
                    margin-bottom:6px;'>
                    <div style='color:#f9fafb; font-weight:700; font-size:0.9rem;
                        line-height:1.3; margin-bottom:4px;'>
                        {p["nombre_razon_social"]}
                    </div>
                    <div style='color:#9ca3af; font-size:0.73rem;'>
                        NIT {p["nit"]} · {p.get("ciudad", "—")}{pep_tag}
                    </div>
                    <div style='display:flex; align-items:center; gap:10px; margin:8px 0 4px;'>
                        <span style='color:{nc}; font-weight:700; font-size:0.8rem;'>
                            ● {risk}
                        </span>
                        <span style='color:#6b7280; font-size:0.75rem;'>Score {score}/100</span>
                    </div>
                    <div style='
                        color:#ef4444; font-size:0.73rem; font-weight:600;
                        border-top:1px solid rgba(239,68,68,0.2);
                        padding-top:6px; margin-top:4px;'>
                        Vencida: {fecha}
                    </div>
                    <div style='color:#9ca3af; font-size:0.7rem; margin-top:4px;'>
                        Pipeline: <span style="color:#d1d5db;">{estado_actual}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Botón de Acción Rápida
                if can_recalify:
                    if st.button(
                        "⚡ Acción Rápida — Iniciar Re-calificación",
                        key=f"recalif_{p['id']}_{idx}",
                        use_container_width=True,
                        type="primary",
                    ):
                        try:
                            repo.cambiar_estado(
                                p["id"],
                                "En Calificación",
                                cambiado_por=user["id"],
                                motivo=(
                                    "Acción Rápida — Centro de Notificaciones: "
                                    "Re-calificación iniciada por SARLAFT vencido. "
                                    "Aplica Debida Diligencia Intensificada (GAFI R.1 / R.12)."
                                ),
                            )
                            AuditRepository(session).registrar(
                                username=user["username"],
                                usuario_id=user["id"],
                                accion="ESTADO_CHANGE",
                                entidad="aliados",
                                entidad_id=p["id"],
                                descripcion=(
                                    f"Acción Rápida · SARLAFT Vencido → Re-calificación. "
                                    f"Partner: {p['nombre_razon_social']} "
                                    f"(NIT {p['nit']}). "
                                    f"Transición: {estado_actual} → En Calificación."
                                ),
                            )
                            st.success(
                                f"✅ Re-calificación iniciada: "
                                f"**{p['nombre_razon_social']}**"
                            )
                            st.rerun()
                        except ValueError as exc:
                            st.warning(f"⚠️ Transición bloqueada: {exc}")
                else:
                    st.caption(
                        f"Estado actual: `{estado_actual}` — "
                        "Re-calificación no disponible desde este estado."
                    )

        st.markdown("<br>", unsafe_allow_html=True)

    # ── Cards: Próximas Revisiones (30 días) ─────────────────────────────────
    if n_p:
        st.markdown(
            f"<div class='section-title'>"
            f"⏰ Próximas Revisiones — Ventana de 30 días ({n_p})"
            f"</div>",
            unsafe_allow_html=True,
        )
        cols2 = st.columns(min(n_p, 4))
        for idx, p in enumerate(proximas):
            nc    = _riesgo_color(p.get("nivel_riesgo", ""))
            fecha = p.get("fecha_proxima_revision", "N/D")
            score = int(p.get("puntaje_riesgo") or 0)
            pep_t = " · ⚠️ PEP" if p.get("es_pep") else ""
            with cols2[idx % len(cols2)]:
                st.markdown(f"""
                <div style='
                    background:#111927;
                    border:1px solid #293056;
                    border-top:3px solid {nc};
                    border-radius:10px;
                    padding:12px 14px;
                    margin-bottom:8px;'>
                    <div style='color:#f9fafb; font-weight:600; font-size:0.83rem;
                        white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>
                        {p["nombre_razon_social"]}
                    </div>
                    <div style='color:#9ca3af; font-size:0.7rem; margin-top:2px;'>
                        NIT {p["nit"]}{pep_t}
                    </div>
                    <div style='margin-top:5px;'>
                        <span style='color:{nc}; font-size:0.75rem; font-weight:700;'>
                            ● {p.get("nivel_riesgo", "—")}
                        </span>
                        <span style='color:#6b7280; font-size:0.72rem; margin-left:8px;'>
                            Score {score}/100
                        </span>
                    </div>
                    <div style='color:#f59e0b; font-size:0.73rem; font-weight:600; margin-top:7px;'>
                        📅 {fecha}
                    </div>
                </div>
                """, unsafe_allow_html=True)
