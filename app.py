"""EduPerú IA — portal docente. Punto de entrada de Streamlit.

Ejecutar:  streamlit run app.py
La lógica vive en el paquete `eduperu/` (core, services, ui, views). Aquí solo se arma la página:
configuración, tema, sesión, barra lateral y enrutamiento entre vistas.
"""
import html

import streamlit as st

st.set_page_config(page_title="EduPerú IA - Portal Docente", layout="wide", page_icon="✏️",
                   initial_sidebar_state="expanded")

from eduperu.ui.theme import inyectar_tema  # noqa: E402

# Cada ejecución empieza con la memoria de consultas vacía (así los datos nunca quedan viejos)
st.session_state["_memo"] = {}
inyectar_tema()

from eduperu.core.db import init_db  # noqa: E402

try:
    init_db()
except Exception as e:
    st.error(f"⚠️ No se pudo preparar la base de datos: {type(e).__name__}: {e}")
    st.stop()

from eduperu.core.auth import pantalla_login  # noqa: E402
from eduperu.core.repo import get_usuario  # noqa: E402
from eduperu.ui.components import (PAG_ADMIN, PAG_ANUAL, PAG_BIBLIO, PAG_CALENDARIO, PAG_CURRICULO,  # noqa: E402
                                   PAG_CURSOS, PAG_PANEL, PAG_TEMAS, mostrar_flash)
from eduperu.views import (admin, anual, biblioteca, calendario, curriculo_oficial, panel,  # noqa: E402
                           sesiones)


def _volver(destino):
    st.session_state.update(nav=destino, _nav_prev=PAG_PANEL, _nav_actual=destino)


if not st.session_state.get("logged_in"):
    pantalla_login()
    st.stop()

usuario = get_usuario(st.session_state.get("user_id"))
if not usuario or usuario["activo"] == 0:
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()
es_admin = usuario["rol"] == "admin"

paginas = [PAG_PANEL, PAG_CURSOS, PAG_ANUAL, PAG_TEMAS, PAG_CALENDARIO, PAG_CURRICULO, PAG_BIBLIO] + (
    [PAG_ADMIN] if es_admin else [])
if st.session_state.get("nav") not in paginas:
    st.session_state["nav"] = PAG_PANEL

# --- Barra lateral: marca, perfil, menú y salir
with st.sidebar:
    st.markdown("<div class='brand'>✏️ EduPerú IA</div>", unsafe_allow_html=True)
    creditos = "ilimitados" if es_admin else usuario["creditos"]
    inicial = (usuario["nombre"] or "?").strip()[:1].upper()
    st.markdown(f"<div class='usercard'><div class='avatar'>{inicial}</div><div><div class='nombre'>{html.escape(usuario['nombre'])}</div>"
                f"<div class='rol'>{'Administrador' if es_admin else 'Docente'}</div>"
                f"<span class='chip'>🎟️ {creditos} créditos</span></div></div>", unsafe_allow_html=True)
    st.markdown("<div class='menu-t'>MENÚ</div>", unsafe_allow_html=True)
    pagina = st.radio("Menú", paginas, key="nav", label_visibility="collapsed")
    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    st.divider()
    if st.button("🚪 Cerrar sesión", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
    st.markdown("<div class='pie-lateral'>Alineado a CNEB y<br>RM N.° 501-2025-MINEDU</div>", unsafe_allow_html=True)

mostrar_flash()
_ant = st.session_state.get("_nav_actual")
if _ant != pagina:
    if _ant:
        st.session_state["_nav_prev"] = _ant
    st.session_state["_nav_actual"] = pagina
if pagina != PAG_PANEL:
    _prev = st.session_state.get("_nav_prev")
    if _prev not in paginas or _prev == pagina:
        _prev = PAG_PANEL
    st.button("← Volver", key="btn_volver", on_click=_volver, args=(_prev,))

if pagina == PAG_PANEL:
    panel.render()
elif pagina == PAG_CURSOS:
    panel.render_cursos()
elif pagina == PAG_ANUAL:
    anual.render()
elif pagina == PAG_TEMAS:
    sesiones.render()
elif pagina == PAG_CALENDARIO:
    calendario.render()
elif pagina == PAG_CURRICULO:
    curriculo_oficial.render()
elif pagina == PAG_BIBLIO:
    biblioteca.render()
elif pagina == PAG_ADMIN and es_admin:
    admin.render(usuario["id"])
