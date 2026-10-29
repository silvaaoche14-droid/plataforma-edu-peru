"""Inicio de sesión, registro y contraseñas."""
import hashlib
import bcrypt
import mysql.connector
import streamlit as st

from eduperu.core.db import fetch, execute
from eduperu.core.repo import mapa_colegios


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, stored_hash: str) -> bool:
    if stored_hash.startswith("$2"):
        try:
            return bcrypt.checkpw(password.encode(), stored_hash.encode())
        except ValueError:
            return False
    return hashlib.sha256(password.encode()).hexdigest() == stored_hash


def admin_correo() -> str:
    try:
        return str(st.secrets["admin"].get("correo", "")).strip().lower()
    except Exception:
        return ""


def pantalla_login():
    _, centro, _ = st.columns([1, 2, 1])
    with centro:
        st.markdown("<h1 style='text-align:center;'>✏️ EduPerú IA</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:#666;'>Tus documentos pedagógicos en minutos, alineados al "
                    "<b>CNEB y la RM N.° 501-2025-MINEDU</b></p>", unsafe_allow_html=True)
        tab_login, tab_reg = st.tabs(["🔑 Iniciar sesión", "📝 Crear cuenta"])

        with tab_login:
            with st.form("login_form"):
                correo = st.text_input("Correo electrónico", key="l_email")
                clave = st.text_input("Contraseña", type="password", key="l_pass")
                enviar = st.form_submit_button("Ingresar", type="primary", use_container_width=True)
            if enviar:
                if not (correo and clave):
                    st.warning("Completa todos los campos.")
                else:
                    try:
                        u = fetch("SELECT * FROM usuarios WHERE correo=%s", (correo.strip().lower(),), one=True)
                        if u and verify_password(clave, u["password_hash"]):
                            if u.get("activo") == 0:
                                st.error("Tu cuenta está desactivada. Contacta al administrador.")
                            else:
                                if not u["password_hash"].startswith("$2"):
                                    execute("UPDATE usuarios SET password_hash=%s WHERE id=%s",
                                            (hash_password(clave), u["id"]))
                                st.session_state.logged_in = True
                                st.session_state.user_id = u["id"]
                                st.rerun()
                        else:
                            st.error("Correo o contraseña incorrectos.")
                    except Exception:
                        st.error("No se pudo ingresar. Intenta de nuevo en unos minutos.")

        with tab_reg:
            colegios = mapa_colegios(solo_activos=True)
            with st.form("register_form"):
                nombre = st.text_input("Nombre completo", key="r_nombre")
                correo = st.text_input("Correo electrónico", key="r_email")
                clave = st.text_input("Contraseña (mínimo 8 caracteres)", type="password", key="r_pass")
                nivel = st.selectbox("Nivel en el que enseñas", ["Inicial", "Primaria", "Secundaria"], key="r_nivel")
                colegio = st.selectbox("Institución educativa", list(colegios.keys()),
                                       format_func=lambda k: colegios[k], key="r_colegio")
                enviar = st.form_submit_button("Crear mi cuenta", type="primary", use_container_width=True)
            if enviar:
                c = correo.strip().lower()
                if not (nombre and correo and clave):
                    st.warning("Completa los campos obligatorios.")
                elif len(clave) < 8:
                    st.warning("La contraseña debe tener al menos 8 caracteres.")
                elif c == admin_correo():
                    st.error("Este correo no está disponible.")
                else:
                    try:
                        execute("INSERT INTO usuarios (nombre, correo, password_hash, nivel_educativo, colegio, colegio_id) "
                                "VALUES (%s,%s,%s,%s,%s,%s)",
                                (nombre.strip(), c, hash_password(clave), nivel,
                                 colegios[colegio] if colegio else "Independiente", colegio or None))
                        st.success("¡Cuenta creada! Ve a la pestaña «Iniciar sesión».")
                    except mysql.connector.Error as err:
                        st.error("Este correo ya está registrado." if err.errno == 1062
                                 else "No se pudo crear la cuenta. Intenta de nuevo.")
