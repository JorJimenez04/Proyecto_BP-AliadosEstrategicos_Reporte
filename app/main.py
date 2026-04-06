"""
app/main.py
Entry point principal de AdamoServices Partner Manager.
Actualizado con métricas de gestión corporativa y operativa.
"""

import streamlit as st
from datetime import date, datetime
import sys
from pathlib import Path
import os
import db.repositories.partner_repo as pr

# Asegurar que la raíz del proyecto esté en el path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import (
    APP_NAME, APP_ENV, EstadosAliado, TiposAliado, NivelesRiesgo,
    EstadosSARLAFT, Roles, SECRET_KEY_IS_DEFAULT
)
from db.database import get_session
from db.repositories.partner_repo import PartnerRepository
from db.repositories.audit_repo import AuditRepository
from db.models import AliadoCreate

# ── Rutas de assets ──────────────────────────────────────────
_STATIC_DIR   = Path(__file__).resolve().parent / "static"
_LOGOS_DIR    = _STATIC_DIR / "img" / "logos"
_IMG_FORMATS  = (".png", ".jpg", ".jpeg", ".webp", ".svg")

def _get_logos() -> tuple[Path | None, Path | None]:
    logo_sidebar = logo_icono = None
    for ext in _IMG_FORMATS:
        if not logo_sidebar and (_LOGOS_DIR / f"logo_adamo_blanco{ext}").exists():
            logo_sidebar = _LOGOS_DIR / f"logo_adamo_blanco{ext}"
        if not logo_icono and (_LOGOS_DIR / f"logo_adamo_color{ext}").exists():
            logo_icono = _LOGOS_DIR / f"logo_adamo_color{ext}"
    if not logo_sidebar and _LOGOS_DIR.exists():
        all_imgs: list[Path] = sorted(p for ext in _IMG_FORMATS for p in _LOGOS_DIR.glob(f"*{ext}"))
        if all_imgs: logo_sidebar = all_imgs[0]
        if len(all_imgs) >= 2: logo_icono = all_imgs[1]
    return logo_sidebar, logo_icono

# ── Configuración de página ───────────────────────────────────
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🔹",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS corporativo AdamoServices (Tu diseño original) ───────
st.markdown("""
<style>
    .stApp { color: #111827; }
    .stApp p, .stApp span, .stApp div { color: #d1d5db; }
    .stApp label { color: #d1d5db !important; font-size: 0.85rem !important; }
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: #f9fafb !important; }
    [data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #293056; }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #5fe9d0 0%, #7839ee 100%);
        color: #101323 !important; font-weight: 700; border: none; border-radius: 8px;
    }
    .section-title {
        font-size: 0.75rem; font-weight: 700; color: #5fe9d0;
        text-transform: uppercase; letter-spacing: 1.2px;
        border-bottom: 1px solid #293056; padding-bottom: 6px; margin-bottom: 14px;
    }
    .badge { display:inline-block; padding:3px 12px; border-radius:20px; font-size:0.75rem; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar Navegación ────────────────────────────────────────
def sidebar(user: dict):
    _logo_sidebar, _logo_icono = _get_logos()
    if _logo_icono:
        try:
            _icon_bytes = _logo_icono.read_bytes()
            st.logo(_logo_sidebar.read_bytes() if _logo_sidebar else _icon_bytes, icon_image=_icon_bytes, size="large")
        except: pass
    with st.sidebar:
        if _logo_sidebar:
            try: st.image(_logo_sidebar.read_bytes(), width=220)
            except: pass
        st.markdown(f"<span style='color:#9ca3af; font-size:0.82rem;'>👤 {user['nombre_completo']}</span>", unsafe_allow_html=True)
        page = st.radio("Navegación", options=["📊 Dashboard", "🤝 Partners", "➕ Nuevo Partner", "📋 Log de Auditoría"], label_visibility="collapsed")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            for _k in ("user", "authenticated"): st.session_state.pop(_k, None)
            st.rerun()
    return page

# ── Página Nuevo Partner (Formulario Reestructurado) ──────────
def page_nuevo_partner(user: dict):
    if user["rol"] not in (Roles.ADMIN, Roles.COMPLIANCE, Roles.COMERCIAL):
        st.error("No tienes permisos para crear partners.")
        return

    st.markdown("<h1>➕ Registrar Nuevo Partner</h1>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#293056;'>", unsafe_allow_html=True)

    with st.form("form_nuevo_partner", clear_on_submit=True):
        # --- SECCIÓN 1: IDENTIFICACIÓN ---
        st.markdown('<p class="section-title">Información Básica e Identificación</p>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            nombre = st.text_input("Razón Social *", placeholder="Ej: Cobre / Davivienda")
            nit = st.text_input("NIT * (900123456-1)", placeholder="900123456-1")
        with c2:
            tipo = st.selectbox("Tipo de Aliado *", TiposAliado.ALL)
            fecha_vinc = st.date_input("Fecha Vinculación *", value=date.today())
        with c3:
            ciudad = st.text_input("Ciudad")
            depto = st.text_input("Departamento")

        # --- SECCIÓN 2: GESTIÓN CORPORATIVA (HOLDINGS/ADAMO/PAYCOP) ---
        st.markdown('<p class="section-title">🏢 Relación con el Grupo Corporativo (Relationship Status)</p>', unsafe_allow_html=True)
        cg1, cg2, cg3 = st.columns(3)
        with cg1:
            est_hbpo = st.selectbox("Estado en HoldingsBPO", ["Activo", "Inactivo", "Sin relación"], index=2)
        with cg2:
            est_adamo = st.selectbox("Estado en Adamo", ["Activo", "Inactivo", "Sin relación"], index=2)
        with cg3:
            est_paycop = st.selectbox("Estado en Paycop", ["Activo", "Inactivo", "Sin relación"], index=2)

        # --- SECCIÓN 3: PERFIL OPERATIVO (BANKING CAPABILITIES) ---
        st.markdown('<p class="section-title">💳 Perfil Operativo y Capacidades</p>', unsafe_allow_html=True)
        co1, co2 = st.columns(2)
        with co1:
            crypto = st.checkbox("¿Es Crypto Friendly?")
            adult = st.checkbox("¿Es Adult Friendly?")
            monetizacion = st.checkbox("Permite Monetización")
            dispersion = st.checkbox("Permite Dispersión")
        with co2:
            monedas = st.text_input("Monedas Soportadas", placeholder="COP-USD-MXN-BRL")
            volumen = st.text_input("Volumen Real Estimado", placeholder="Ej: 10-11M mensuales")
        
        clientes = st.text_area("Clientes Vinculados", placeholder="Ej: Paxum, Scientia, CM Group...")
        
        cf1, cf2 = st.columns(2)
        with cf1:
            fecha_ini_rel = st.date_input("Fecha Inicio Relación Grupo", value=None)
        with cf2:
            fecha_fin_rel = st.date_input("Fecha Fin Relación (si aplica)", value=None)

        # --- SECCIÓN 4: COMPLIANCE ---
        st.markdown('<p class="section-title">⚖️ Cumplimiento y Riesgo</p>', unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        with cc1:
            riesgo = st.selectbox("Nivel de Riesgo Inicial", NivelesRiesgo.ALL, index=1)
            pep = st.checkbox("¿Es Persona Expuesta Políticamente (PEP)?")
        with cc2:
            freq = st.selectbox("Frecuencia Revisión", ["Anual", "Semestral", "Trimestral", "Mensual"])
            motivo_inact = st.text_area("Si está Inactivo, ¿por qué? (Motivo)")

        obs = st.text_area("Observaciones Adicionales de Compliance")

        submitted = st.form_submit_button("💾 Registrar Partner", type="primary")

    if submitted:
        if not nombre or not nit:
            st.error("Razón Social y NIT son obligatorios.")
            return
        
        try:
            # Construcción del modelo Pydantic
            nuevo = AliadoCreate(
                nombre_razon_social=nombre, nit=nit, tipo_aliado=tipo, fecha_vinculacion=fecha_vinc,
                ciudad=ciudad, departamento_geo=depto, nivel_riesgo=riesgo, es_pep=pep,
                frecuencia_revision=freq, observaciones_compliance=obs,
                # Métricas de gestión nuevas
                estado_hbpocorp=est_hbpo, estado_adamo=est_adamo, estado_paycop=est_paycop,
                crypto_friendly=crypto, adult_friendly=adult, permite_monetizacion=monetizacion,
                permite_dispersion=dispersion, monedas_soportadas=monedas,
                clientes_vinculados=clientes, volumen_real_mensual=volumen,
                fecha_inicio_relacion=fecha_ini_rel, fecha_fin_relacion=fecha_fin_rel,
                motivo_inactividad=motivo_inact
            )
            
            with next(get_session()) as session:
                repo = PartnerRepository(session)
                audit = AuditRepository(session)
                # El repo.create ya maneja el ajuste de ID 1 si el usuario es 0
                nuevo_id = repo.create(nuevo, creado_por=user["id"])
                
                # Registrar en auditoría
                audit.registrar(
                    username=user["username"], usuario_id=user["id"], accion="CREATE", 
                    entidad="aliados", entidad_id=nuevo_id, 
                    descripcion=f"Nuevo partner registrado: {nombre} (NIT: {nit})",
                    valores_nuevos=nuevo.model_dump(mode="json")
                )
                st.success(f"✅ Partner **{nombre}** registrado exitosamente con ID #{nuevo_id}")
        except Exception as e:
            st.error(f"Error al registrar: {e}")

# ── Router Principal ──────────────────────────────────────────
def main():
    from app.auth.login import require_auth
    user = require_auth()
    
    # Invocación de sidebar y navegación
    page = sidebar(user)

    if page == "📊 Dashboard":
        from app.components.dashboard_ui import page_dashboard # Asumiendo que moviste la lógica allí
        page_dashboard(user) 
    elif page == "🤝 Partners":
        from app.components.partners_ui import page_partners
        page_partners(user)
    elif page == "➕ Nuevo Partner":
        page_nuevo_partner(user)
    elif page == "📋 Log de Auditoría":
        from app.components.audit_ui import page_auditoria
        page_auditoria(user)

if __name__ == "__main__":
    main()