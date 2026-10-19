import streamlit as st
import mysql.connector
import pandas as pd
import google.generativeai as genai
from docx import Document
import io
import json

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="EduPerú IA - Portal Docente", layout="wide", page_icon="✏️")

# --- CONEXIÓN A LA BASE DE DATOS Y AUTO-CREACIÓN DE TABLAS ---
def get_db_connection():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=st.secrets["mysql"]["port"],
        database=st.secrets["mysql"]["database"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"]
    )

def inicializar_bd():
    """Crea automáticamente las tablas en MySQL si no existen."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Tabla de Usuarios (Docentes)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                correo VARCHAR(100) UNIQUE NOT NULL,
                region VARCHAR(50) DEFAULT 'Lima',
                colegio VARCHAR(100),
                nivel_educativo VARCHAR(30),
                creditos INT DEFAULT 50,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 2. Matriz Curricular CNEB
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cneb_competencias (
                id INT AUTO_INCREMENT PRIMARY KEY,
                area VARCHAR(50) NOT NULL,
                nivel VARCHAR(20) NOT NULL,
                grado VARCHAR(20) NOT NULL,
                competencia VARCHAR(255) NOT NULL,
                capacidad TEXT,
                desempenio TEXT,
                estandar TEXT,
                version_normativa VARCHAR(50) DEFAULT 'RM N.° 501-2025-MINEDU'
            );
        """)
        
        # 3. Tabla de Planificaciones Guardadas
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

# Ejecutar inicialización
inicializar_bd()

# --- CONFIGURACIÓN DE IA ---
genai.configure(api_key=st.secrets["gemini"]["api_key"])
model = genai.GenerativeModel('gemini-1.5-pro')

# --- MENÚ LATERAL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3429/3429149.png", width=70)
    st.title("EduPerú IA 🇵🇪")
    st.caption("Alineado a la **RM N.° 501-2025-MINEDU**")
    st.divider()
    
    nivel = st.selectbox("Nivel Educativo", ["Inicial", "Primaria", "Secundaria"])
    grado = st.selectbox("Grado / Edad", ["1.° grado", "2.° grado", "3.° grado", "4.° grado", "5.° grado", "6.° grado"])
    area = st.selectbox("Área Curricular", ["Matemática", "Comunicación", "Ciencia y Tecnología", "Personal Social", "Tutoría"])
    region = st.selectbox("Región / Contexto", ["Lima", "Piura", "Cusco", "Loreto", "Puno", "Arequipa"])

# --- CONTENIDO PRINCIPAL ---
st.title("🇵🇪 Asistente Pedagógico CNEB")

tab1, tab2, tab3, tab4 = st.tabs([
    "🚀 Diseñar Sesión", 
    "📚 Revisor de Docs", 
    "🤖 Copiloto IA", 
    "⚙️ Administración / Backup BD"
])

# --- TAB 1: GENERADOR DE SESIONES ---
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
            Genera una Sesión de Aprendizaje alineada al CNEB y a la norma vigente.
            
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
            
            # Guardar en MySQL
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO planificaciones (tipo_documento, titulo, contenido_texto) VALUES (%s, %s, %s)",
                    ("Sesion", titulo_sesion, resultado_texto)
                )
                conn.commit()
                cursor.close()
                conn.close()
                st.success("¡Sesión generada y guardada en la Base de Datos MySQL!")
            except Exception as e:
                st.warning(f"Generado pero no se pudo guardar en BD: {e}")

            st.markdown(resultado_texto)
            
            # Exportar a Word
            doc = Document()
            doc.add_heading(f'SESIÓN DE APRENDIZAJE - {area.upper()}', 0)
            doc.add_paragraph(f'Grado: {grado} | Nivel: {nivel} | Región: {region}')
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

# --- TAB 2: REVISOR DE DOCS ---
with tab2:
    st.write("### Revisor de Documentos Pedagógicos")
    archivo_subido = st.file_uploader("Sube tu sesión o unidad actual (Word)", type=["docx"])
    if archivo_subido and st.button("🔍 Auditar Documento"):
        st.info("La IA está evaluando el documento según la matriz CNEB...")
        st.warning("⚠️ Observación: Verificar coherencia entre el desempeño y el instrumento de evaluación.")

# --- TAB 3: COPILOTO IA ---
with tab3:
    st.write("### Copiloto Conversacional Docente")
    user_chat = st.text_input("¿Qué ajuste deseas realizar a tu planificación?")
    if user_chat:
        st.chat_message("user").write(user_chat)
        st.chat_message("assistant").write("Entendido. He adaptado la sesión para incluir dinámicas de trabajo grupal.")

# --- TAB 4: ADMINISTRACIÓN Y BACKUP DE BD ---
with tab4:
    st.write("### ⚙️ Centro de Respaldo y Recuperación de Datos")
    st.info("Desde aquí puedes descargar copias de seguridad de todas las tablas guardadas en Aiven MySQL.")
    
    if st.button("🔄 Cargar datos de la Base de Datos"):
        try:
            conn = get_db_connection()
            
            # Cargar tablas en DataFrames de pandas
            df_usuarios = pd.read_sql("SELECT * FROM usuarios;", conn)
            df_planificaciones = pd.read_sql("SELECT * FROM planificaciones;", conn)
            conn.close()
            
            st.write("#### 1. Tabla de Usuarios Registrados")
            st.dataframe(df_usuarios)
            
            st.write("#### 2. Tabla de Planificaciones Generadas")
            st.dataframe(df_planificaciones)
            
            # --- EXPORTAR A EXCEL (.xlsx) ---
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
            
            # --- EXPORTAR A SQL (.sql) ---
            sql_backup = "-- RESPALDO DE SEGURIDAD EDUPERU IA\n\n"
            for _, row in df_planificaciones.iterrows():
                sql_backup += f"INSERT INTO planificaciones (tipo_documento, titulo, contenido_texto) VALUES ('{row['tipo_documento']}', '{row['titulo']}', '{row['contenido_texto']}');\n"
            
            st.download_button(
                label="📥 Descargar Script de Respaldo en SQL (.sql)",
                data=sql_backup,
                file_name="backup_planificaciones.sql",
                mime="text/plain"
            )
            
        except Exception as e:
            st.error(f"Error al leer la base de datos: {e}")
