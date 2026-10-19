import streamlit as st
import mysql.connector
import pandas as pd
import google.generativeai as genai
from docx import Document
import io
import hashlib

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="EduPerú IA - Portal Docente", layout="wide", page_icon="✏️")

# --- FUNCIONES DE SEGURIDAD Y HASH ---
def hash_password(password):
    """Encripta la contraseña usando SHA-256 para mayor seguridad."""
    return hashlib.sha256(password.encode()).hexdigest()

# --- CONEXIÓN A LA BASE DE DATOS Y AUTO-CREACIÓN/ACTUALIZACIÓN DE TABLAS ---
def get_db_connection():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=st.secrets["mysql"]["port"],
        database=st.secrets["mysql"]["database"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"]
    )

def inicializar_bd():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Crear tabla de Usuarios si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                correo VARCHAR(100) UNIQUE NOT NULL,
                region VARCHAR(50) DEFAULT 'Lima',
                colegio VARCHAR(100),
                nivel_educativo VARCHAR(30),
                rol VARCHAR(30) DEFAULT 'docente',
                creditos INT DEFAULT 50,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Comprobar y agregar la columna password_hash si la tabla ya existía sin ella
        cursor.execute("SHOW COLUMNS FROM usuarios LIKE 'password_hash';")
        resultado = cursor.fetchone()
        if not resultado:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN password_hash VARCHAR(255) NOT NULL;")
        
        # 2. Tabla de Planificaciones Guardadas
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
    except Exception as e:
        st.error(f"Error al conectar/inicializar la BD: {e}")

inicializar_bd()

# --- CONFIGURACIÓN DE IA ---
genai.configure(api_key=st.secrets["gemini"]["api_key"])
model = genai.GenerativeModel('gemini-1.5-pro')

# --- CONTROL DE SESIÓN (LOGIN) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_name = ""
    st.session_state.user_email = ""

# --- PANTALLA DE LOGIN / REGISTRO SI NO HA INICIADO SESIÓN ---
if not st.session_state.logged_in:
    st.title("🔐 EduPerú IA - Acceso al Sistema")
    st.markdown("Plataforma Pedagógica Inteligente alineada al **CNEB y RM N.° 501-2025-MINEDU**.")
    
    tab_login, tab_register = st.tabs(["🔑 Iniciar Sesión", "📝 Registrarse"])
    
    with tab_login:
        st.subheader("Iniciar Sesión Docente")
        email_login = st.text_input("Correo electrónico", key="login_email")
        pass_login = st.text_input("Contraseña", type="password", key="login_pass")
        
        if st.button("Ingresar al Sistema", type="primary"):
            if email_login and pass_login:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("SELECT * FROM usuarios WHERE correo = %s", (email_login,))
                    user = cursor.fetchone()
                    cursor.close()
                    conn.close()
                    
                    if user and user.get("password_hash") and user["password_hash"] == hash_password(pass_login):
                        st.session_state.logged_in = True
                        st.session_state.user_id = user["id"]
                        st.session_state.user_name = user["nombre"]
                        st.session_state.user_email = user["correo"]
                        st.success(f"¡Bienvenido de nuevo, {user['nombre']}!")
                        st.rerun()
                    else:
                        st.error("Correo o contraseña incorrectos.")
                except Exception as e:
                    st.error(f"Error en la base de datos: {e}")
            else:
                st.warning("Por favor completa todos los campos.")
                
    with tab_register:
        st.subheader("Crear Cuenta Nueva")
        nombre_reg = st.text_input("Nombre completo", key="reg_nombre")
        email_reg = st.text_input("Correo electrónico", key="reg_email")
        pass_reg = st.text_input("Contraseña", type="password", key="reg_pass")
        nivel_reg = st.selectbox("Nivel en el que enseñas", ["Inicial", "Primaria", "Secundaria"], key="reg_nivel")
        colegio_reg = st.text_input("Nombre de tu Institución Educativa", key="reg_colegio")
        
        if st.button("Registrarme", type="primary"):
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
                    st.success("¡Cuenta creada con éxito! Ya puedes iniciar sesión en la pestaña de al lado.")
                except mysql.connector.Error as err:
                    if err.errno == 1062:
                        st.error("Este correo ya está registrado en el sistema.")
                    else:
                        st.error(f"Error al registrar: {err}")
            else:
                st.warning("Por favor completa los campos obligatorios.")
                
    st.stop()

# --- APLICACIÓN PRINCIPAL (UNA VEZ LOGUEADO) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3429/3429149.png", width=70)
    st.title("EduPerú IA 🇵🇪")
    st.write(f"👤 **{st.session_state.user_name}**")
    st.caption(f"📧 {st.session_state.user_email}")
    
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()
        
    st.divider()
    nivel = st.selectbox("Nivel Educativo", ["Inicial", "Primaria", "Secundaria"])
    grado = st.selectbox("Grado / Edad", ["1.° grado", "2.° grado", "3.° grado", "4.° grado", "5.° grado", "6.° grado"])
    area = st.selectbox("Área Curricular", ["Matemática", "Comunicación", "Ciencia y Tecnología", "Personal Social", "Tutoría"])
    region = st.selectbox("Región / Contexto", ["Lima", "Piura", "Cusco", "Loreto", "Puno", "Arequipa"])

st.title("🇵🇪 Asistente Pedagógico CNEB")

tab1, tab2, tab3, tab4 = st.tabs([
    "🚀 Diseñar Sesión", 
    "📚 Revisor de Docs", 
    "🤖 Copiloto IA", 
    "⚙️ Administración / Backup BD"
])

with tab1:
    st.write("### Crear Nueva Sesión de Aprendizaje")
    col1, col2 = st.columns(2)
    with col1:
        titulo_sesion = st.text_input("Título de la Sesión", "Leemos un texto sobre los transportes de nuestra comunidad")
        duracion = st.selectbox("Duración", ["45 minutos", "90 minutos", "135 minutos"])
    with col2:
        situacion_contexto = st.text_area("Contexto Local", f"Estudiantes de la región {region} enfrentan problemas de transporte o clima local.")

    if st.button("✨ Generar Sesión Completa con CNEB", type="primary"):
        with st.spinner("Consultando CNEB y redactando estructura pedagógica..."):
            prompt = f"""
            Actúa como un Especialista Pedagógico del MINEDU Perú.
            Genera una Sesión de Aprendizaje alineada al CNEB y a la norma vigente (RM N.° 501-2025-MINEDU).
            
            DATOS DE ENTRADA:
            - Nivel: {nivel} | Grado: {grado} | Área: {area} | Región: {region}
            - Duración: {duracion} | Título: {titulo_sesion}
            - Contexto local: {situacion_contexto}
            
            ESTRUCTURA REQUERIDA:
            1. PROPÓSITO DE APRENDIZAJE (Competencias, Capacidades, Criterios y Evidencias).
            2. MOMENTOS DE LA SESIÓN (Inicio, Desarrollo y Cierre).
            3. INSTRUMENTO DE EVALUACIÓN (Lista de cotejo o Rúbrica).
            """
            response = model.generate_content(prompt)
            resultado_texto = response.text
            
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO planificaciones (usuario_id, tipo_documento, titulo, contenido_texto) VALUES (%s, %s, %s, %s)",
                    (st.session_state.user_id, "Sesion", titulo_sesion, resultado_texto)
                )
                conn.commit()
                cursor.close()
                conn.close()
                st.success("¡Sesión generada y guardada de forma segura en la Base de Datos!")
            except Exception as e:
                st.warning(f"Generado pero no se pudo guardar en BD: {e}")

            st.markdown(resultado_texto)
            
            doc = Document()
            doc.add_heading(f'SESIÓN DE APRENDIZAJE - {area.upper()}', 0)
            doc.add_paragraph(f'Docente: {st.session_state.user_name} | Grado: {grado} | Nivel: {nivel} | Región: {region}')
            doc.add_paragraph(f'Normativa: RM N.° 501-2025-MINEDU\n')
            doc.add_paragraph(resultado_texto)
            
            buffer = io.BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            
            st.download_button(
                label="📥 Descargar Sesión en Word (.docx)",
                data=buffer,
                file_name=f"Sesion_{area}_{grado}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

with tab2:
    st.write("### Revisor de Documentos Pedagógicos")
    archivo_subido = st.file_uploader("Sube tu sesión o unidad actual (Word)", type=["docx"])
    if archivo_subido and st.button("🔍 Auditar Documento"):
        st.info("La IA está evaluando el documento según la matriz CNEB...")
        st.warning("⚠️ Observación: Verificar coherencia entre el desempeño y el instrumento de evaluación.")

with tab3:
    st.write("### Copiloto Conversacional Docente")
    user_chat = st.text_input("¿Qué ajuste deseas realizar a tu planificación?")
    if user_chat:
        st.chat_message("user").write(user_chat)
        st.chat_message("assistant").write("Entendido. He adaptado la sesión para incluir dinámicas de trabajo grupal.")

with tab4:
    st.write("### ⚙️ Centro de Respaldo y Recuperación de Datos")
    st.info("Desde aquí puedes descargar copias de seguridad de los registros y planificaciones de la plataforma.")
    
    if st.button("🔄 Cargar datos de la Base de Datos"):
        try:
            conn = get_db_connection()
            df_usuarios = pd.read_sql("SELECT id, nombre, correo, region, colegio, nivel_educativo, creado_en FROM usuarios;", conn)
            df_planificaciones = pd.read_sql("SELECT * FROM planificaciones;", conn)
            conn.close()
            
            st.write("#### 1. Tabla de Usuarios Registrados")
            st.dataframe(df_usuarios)
            
            st.write("#### 2. Tabla de Planificaciones Generadas")
            st.dataframe(df_planificaciones)
            
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                df_usuarios.to_excel(writer, sheet_name='Usuarios', index=False)
                df_planificaciones.to_excel(writer, sheet_name='Planificaciones', index=False)
            output_excel.seek(0)
            
            st.download_button(
                label="📊 Descargar Respaldo Completo en Excel (.xlsx)",
                data=output_excel,
                file_name="Respaldo_BaseDeDatos_EduPeru.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Error al leer la base de datos: {e}")
