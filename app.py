import streamlit as st
import mysql.connector
import pandas as pd
import google.generativeai as genai
from docx import Document
import io
import hashlib

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="EduPerú IA - Portal Docente", 
    layout="wide", 
    page_icon="✏️",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS PARA DISEÑO RESPONSIVO Y CENTRADO ---
st.markdown("""
    <style>
    /* Estilos para centrar la tarjeta de Login */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .auth-card {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.05);
        border: 1px solid #e0e0e0;
    }
    div[data-testid="stForm"] {
        border: none;
    }
    /* Adaptación móvil */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
    }
    </style>
""", unsafe_allow_html=True)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_db_connection():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=st.secrets["mysql"]["port"],
        database=st.secrets["mysql"]["database"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"]
    )

# --- INICIALIZACIÓN SEGURA DE LA BD ---
db_connected = False
try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            correo VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            region VARCHAR(50) DEFAULT 'Lima',
            colegio VARCHAR(100),
            nivel_educativo VARCHAR(30),
            rol VARCHAR(30) DEFAULT 'docente',
            creditos INT DEFAULT 50,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS planificaciones (
            id INT AUTO_INCREMENT PRIMARY KEY,
            usuario_id INT,
            tipo_documento VARCHAR(50),
            titulo VARCHAR(255) NOT NULL,
            contenido_texto LONGTEXT NOT NULL,
            normativa_usada VARCHAR(50) DEFAULT 'RM N.° 501-2025-MINEDU',
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()
    db_connected = True
except Exception as e:
    st.error(f"⚠️ Error de conexión a la Base de Datos: {e}")

genai.configure(api_key=st.secrets["gemini"]["api_key"])
model = genai.GenerativeModel('gemini-1.5-pro')

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_name = ""
    st.session_state.user_email = ""

# --- PANTALLA DE LOGIN / REGISTRO CENTRADA Y OPTIMIZADA ---
if not st.session_state.logged_in:
    # Columnas para centrar en pantallas grandes
    col_left, col_center, col_right = st.columns([1, 2, 1])
    
    with col_center:
        st.markdown("<h1 style='text-align: center;'>🔒 EduPerú IA</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>Plataforma Pedagógica Inteligente alineada al <b>CNEB y RM N.° 501-2025-MINEDU</b></p>", unsafe_allow_html=True)
        st.write("")
        
        tab_login, tab_register = st.tabs(["🔑 Iniciar Sesión", "📝 Registrarse"])
        
        with tab_login:
            with st.form("login_form"):
                st.subheader("Ingreso al Portal")
                email_login = st.text_input("Correo electrónico", key="l_email")
                pass_login = st.text_input("Contraseña", type="password", key="l_pass")
                submit_login = st.form_submit_button("Ingresar al Sistema", type="primary", use_container_width=True)
                
                if submit_login:
                    if email_login and pass_login:
                        try:
                            conn = get_db_connection()
                            cursor = conn.cursor(dictionary=True)
                            cursor.execute("SELECT * FROM usuarios WHERE correo = %s", (email_login,))
                            user = cursor.fetchone()
                            cursor.close()
                            conn.close()
                            
                            if user and user["password_hash"] == hash_password(pass_login):
                                st.session_state.logged_in = True
                                st.session_state.user_id = user["id"]
                                st.session_state.user_name = user["nombre"]
                                st.session_state.user_email = user["correo"]
                                st.success(f"¡Bienvenido, {user['nombre']}!")
                                st.rerun()
                            else:
                                st.error("Correo o contraseña incorrectos.")
                        except Exception as ex:
                            st.error(f"Error de acceso: {ex}")
                    else:
                        st.warning("Completa todos los campos.")
                    
        with tab_register:
            with st.form("register_form"):
                st.subheader("Crear Cuenta Nueva")
                nombre_reg = st.text_input("Nombre completo", key="r_nombre")
                email_reg = st.text_input("Correo electrónico", key="r_email")
                pass_reg = st.text_input("Contraseña", type="password", key="r_pass")
                nivel_reg = st.selectbox("Nivel en el que enseñas", ["Inicial", "Primaria", "Secundaria"], key="r_nivel")
                colegio_reg = st.text_input("Institución Educativa", key="r_colegio")
                submit_reg = st.form_submit_button("Registrarme", type="primary", use_container_width=True)
                
                if submit_reg:
                    if nombre_reg and email_reg and pass_reg:
                        try:
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            hashed_pw = hash_password(pass_reg)
                            cursor.execute(
                                "INSERT INTO usuarios (nombre, correo, password_hash, nivel_educativo, colegio) VALUES (%s, %s, %s, %s, %s)",
                                (nombre_reg, email_reg, hashed_pw, nivel_reg, colegio_reg)
                            )
                            conn.commit()
                            cursor.close()
                            conn.close()
                            st.success("¡Cuenta creada con éxito! Selecciona la pestaña 'Iniciar Sesión'.")
                        except mysql.connector.Error as err:
                            if err.errno == 1062:
                                st.error("Este correo ya está registrado.")
                            else:
                                st.error(f"Error al registrar: {err}")
                    else:
                        st.warning("Completa los campos obligatorios.")
    st.stop()

# --- PANEL PRINCIPAL (UNA VEZ AUTENTICADO) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3429/3429149.png", width=70)
    st.title("EduPerú IA 🇵🇪")
    st.write(f"👤 **{st.session_state.user_name}**")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
        
    st.divider()
    nivel = st.selectbox("Nivel Educativo", ["Inicial", "Primaria", "Secundaria"])
    grado = st.selectbox("Grado / Edad", ["1.° grado", "2.° grado", "3.° grado", "4.° grado", "5.° grado", "6.° grado"])
    area = st.selectbox("Área Curricular", ["Matemática", "Comunicación", "Ciencia y Tecnología", "Personal Social", "Tutoría"])
    region = st.selectbox("Región / Contexto", ["Lima", "Piura", "Cusco", "Loreto", "Puno", "Arequipa"])

st.title("🇵🇪 Asistente Pedagógico CNEB")
st.write("¡Bienvenido al sistema! Selecciona tus opciones en el menú lateral.")
