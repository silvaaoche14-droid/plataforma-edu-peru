"""EduPerú IA — portal docente. Archivo principal (ejecuta: streamlit run app.py)."""
import streamlit as st

st.set_page_config(page_title="EduPerú IA - Portal Docente", layout="wide", page_icon="✏️",
                   initial_sidebar_state="auto")

st.markdown("""
<style>
.main .block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1200px; }
div[data-testid="stForm"] { border: none; }
div[role="radiogroup"] { gap: .35rem; }
@media (max-width: 768px) { .main .block-container { padding-left: 1rem; padding-right: 1rem; } }
</style>
""", unsafe_allow_html=True)

from db import init_db  # noqa: E402

try:
    init_db()
except Exception as e:
    st.error(f"⚠️ No se pudo preparar la base de datos: {type(e).__name__}: {e}")
    st.stop()

from auth import pantalla_login  # noqa: E402
from repo import get_usuario, listar_asignaciones  # noqa: E402
from ui import (PAG_ADMIN, PAG_ANUAL, PAG_BIBLIO, PAG_PANEL, PAG_SESIONES, PAG_UNIDADES,  # noqa: E402
                mostrar_flash)
import v_admin, v_anual, v_biblioteca, v_panel, v_sesiones, v_unidades  # noqa: E402,E401

if not st.session_state.get("logged_in"):
    pantalla_login()
    st.stop()

usuario = get_usuario(st.session_state.get("user_id"))
if not usuario or usuario["activo"] == 0:
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()
es_admin = usuario["rol"] == "admin"

# --- Barra lateral: perfil, créditos y salir
with st.sidebar:
    st.title("✏️ EduPerú IA")
    st.write(f"👤 **{usuario['nombre']}**" + (" · 🛡️ Admin" if es_admin else ""))
    st.write("🎟️ Créditos: **ilimitados**" if es_admin else f"🎟️ Créditos: **{usuario['creditos']}**")
    st.caption("Alineado a CNEB y RM N.° 501-2025-MINEDU")
    if st.button("🚪 Cerrar sesión", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# --- Navegación (arriba, visible también en el celular)
paginas = [PAG_PANEL, PAG_ANUAL, PAG_UNIDADES, PAG_SESIONES, PAG_BIBLIO] + ([PAG_ADMIN] if es_admin else [])
if st.session_state.get("nav") not in paginas:
    st.session_state["nav"] = PAG_PANEL
pagina = st.radio("Menú", paginas, key="nav", horizontal=True, label_visibility="collapsed")

# --- Área activa
asigs = listar_asignaciones(usuario["id"])
ids = [a["id"] for a in asigs]
if ids:
    if st.session_state.get("area_id") not in ids:
        st.session_state["area_id"] = ids[0]
    st.selectbox("📌 Trabajando en:", ids, key="area_id",
                 format_func=lambda i: next(f"{a['area']} · {a['grado']} · Sección {a['seccion'] or '—'}"
                                            for a in asigs if a["id"] == i))
else:
    st.session_state["area_id"] = None
st.divider()
mostrar_flash()

if pagina == PAG_PANEL:
    v_panel.render()
elif pagina == PAG_ANUAL:
    v_anual.render()
elif pagina == PAG_UNIDADES:
    v_unidades.render()
elif pagina == PAG_SESIONES:
    v_sesiones.render()
elif pagina == PAG_BIBLIO:
    v_biblioteca.render()
elif pagina == PAG_ADMIN and es_admin:
    v_admin.render(usuario["id"])
