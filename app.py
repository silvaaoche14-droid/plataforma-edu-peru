import io
import hashlib

import bcrypt
import requests
import streamlit as st
import mysql.connector
import google.generativeai as genai
from docx import Document

# ------------------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ------------------------------------------------------------------
st.set_page_config(
    page_title="EduPerú IA - Portal Docente",
    layout="wide",
    page_icon="✏️",
    initial_sidebar_state="collapsed",
)

st.markdown("""
    <style>
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    div[data-testid="stForm"] { border: none; }
    @media (max-width: 768px) {
        .main .block-container { padding-left: 1rem; padding-right: 1rem; }
    }
    </style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# SEGURIDAD: CONTRASEÑAS (bcrypt, con compatibilidad para SHA-256 antiguo)
# ------------------------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, stored_hash: str) -> bool:
    if stored_hash.startswith("$2"):
        try:
            return bcrypt.checkpw(password.encode(), stored_hash.encode())
        except ValueError:
            return False
    # Hash antiguo (SHA-256) de usuarios creados antes del cambio
    return hashlib.sha256(password.encode()).hexdigest() == stored_hash


# ------------------------------------------------------------------
# BASE DE DATOS
# ------------------------------------------------------------------
def get_db_connection():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=int(st.secrets["mysql"]["port"]),
        database=st.secrets["mysql"]["database"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        ssl_disabled=False,  # Aiven requiere SSL
        connection_timeout=10,
    )


@st.cache_resource(show_spinner=False)
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
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
    cur.execute("""
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
    cur.close()
    conn.close()
    return True


try:
    db_connected = init_db()
except Exception as e:
    db_connected = False
    st.error(f"⚠️ {type(e).__name__}: {e}")
    st.stop()


def db_fetch(sql, params=(), one=False):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    rows = cur.fetchone() if one else cur.fetchall()
    cur.close()
    conn.close()
    return rows


def db_execute(sql, params=()):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    affected = cur.rowcount
    cur.close()
    conn.close()
    return last_id, affected


# ------------------------------------------------------------------
# IA: OPENROUTER PRIMERO, GEMINI DE RESPALDO
# ------------------------------------------------------------------
def llamar_openrouter(prompt: str) -> str:
    cfg = st.secrets["openrouter"]
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {cfg['api_key']}",
            "Content-Type": "application/json",
        },
        json={
            "model": cfg.get("model", "openai/gpt-4o-mini"),
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def llamar_gemini(prompt: str) -> str:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    modelo = genai.GenerativeModel("gemini-2.5-flash")
    return modelo.generate_content(prompt).text


def generar_texto(prompt: str):
    """Devuelve (texto, proveedor). Lanza excepción si fallan ambos."""
    errores = []
    if "openrouter" in st.secrets:
        try:
            return llamar_openrouter(prompt), "OpenRouter"
        except Exception as e:
            errores.append(f"OpenRouter: {e}")
    if "gemini" in st.secrets:
        try:
            return llamar_gemini(prompt), "Gemini"
        except Exception as e:
            errores.append(f"Gemini: {e}")
    raise RuntimeError(" | ".join(errores) or "No hay proveedores de IA configurados.")


# ------------------------------------------------------------------
# EXPORTAR A WORD
# ------------------------------------------------------------------
def texto_a_docx(titulo: str, contenido: str) -> bytes:
    doc = Document()
    doc.add_heading(titulo, level=0)
    for linea in contenido.splitlines():
        l = linea.strip().replace("**", "")
        if not l:
            continue
        if l.startswith("### "):
            doc.add_heading(l[4:], level=3)
        elif l.startswith("## "):
            doc.add_heading(l[3:], level=2)
        elif l.startswith("# "):
            doc.add_heading(l[2:], level=1)
        elif l.startswith(("- ", "* ")):
            doc.add_paragraph(l[2:], style="List Bullet")
        else:
            doc.add_paragraph(l)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ------------------------------------------------------------------
# ESTADO DE SESIÓN
# ------------------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_name = ""
    st.session_state.user_email = ""

# ------------------------------------------------------------------
# LOGIN / REGISTRO
# ------------------------------------------------------------------
if not st.session_state.logged_in:
    _, col_center, _ = st.columns([1, 2, 1])

    with col_center:
        st.markdown("<h1 style='text-align: center;'>🔒 EduPerú IA</h1>", unsafe_allow_html=True)
        st.markdown(
            "<p style='text-align: center; color: #666;'>Plataforma Pedagógica Inteligente alineada al "
            "<b>CNEB y RM N.° 501-2025-MINEDU</b></p>",
            unsafe_allow_html=True,
        )
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
                        user = db_fetch("SELECT * FROM usuarios WHERE correo = %s", (email_login.strip().lower(),), one=True)
                        if user and verify_password(pass_login, user["password_hash"]):
                            # Migrar hash antiguo a bcrypt
                            if not user["password_hash"].startswith("$2"):
                                db_execute("UPDATE usuarios SET password_hash=%s WHERE id=%s",
                                           (hash_password(pass_login), user["id"]))
                            st.session_state.logged_in = True
                            st.session_state.user_id = user["id"]
                            st.session_state.user_name = user["nombre"]
                            st.session_state.user_email = user["correo"]
                            st.rerun()
                        else:
                            st.error("Correo o contraseña incorrectos.")
                    except Exception:
                        st.error("Error de acceso. Intenta de nuevo en unos minutos.")
                else:
                    st.warning("Completa todos los campos.")

        with tab_register:
            with st.form("register_form"):
                st.subheader("Crear Cuenta Nueva")
                nombre_reg = st.text_input("Nombre completo", key="r_nombre")
                email_reg = st.text_input("Correo electrónico", key="r_email")
                pass_reg = st.text_input("Contraseña (mínimo 8 caracteres)", type="password", key="r_pass")
                nivel_reg = st.selectbox("Nivel en el que enseñas", ["Inicial", "Primaria", "Secundaria"], key="r_nivel")
                colegio_reg = st.text_input("Institución Educativa", key="r_colegio")
                submit_reg = st.form_submit_button("Registrarme", type="primary", use_container_width=True)

            if submit_reg:
                if not (nombre_reg and email_reg and pass_reg):
                    st.warning("Completa los campos obligatorios.")
                elif len(pass_reg) < 8:
                    st.warning("La contraseña debe tener al menos 8 caracteres.")
                else:
                    try:
                        db_execute(
                            "INSERT INTO usuarios (nombre, correo, password_hash, nivel_educativo, colegio) "
                            "VALUES (%s, %s, %s, %s, %s)",
                            (nombre_reg.strip(), email_reg.strip().lower(), hash_password(pass_reg),
                             nivel_reg, colegio_reg.strip()),
                        )
                        st.success("¡Cuenta creada con éxito! Ve a la pestaña 'Iniciar Sesión'.")
                    except mysql.connector.Error as err:
                        if err.errno == 1062:
                            st.error("Este correo ya está registrado.")
                        else:
                            st.error("Error al registrar. Intenta de nuevo.")
    st.stop()

# ------------------------------------------------------------------
# SIDEBAR (USUARIO AUTENTICADO)
# ------------------------------------------------------------------
GRADOS = {
    "Inicial": ["3 años", "4 años", "5 años"],
    "Primaria": ["1.° grado", "2.° grado", "3.° grado", "4.° grado", "5.° grado", "6.° grado"],
    "Secundaria": ["1.° grado", "2.° grado", "3.° grado", "4.° grado", "5.° grado"],
}
AREAS = {
    "Inicial": ["Personal Social", "Psicomotricidad", "Comunicación", "Matemática", "Ciencia y Tecnología"],
    "Primaria": ["Matemática", "Comunicación", "Ciencia y Tecnología", "Personal Social",
                 "Arte y Cultura", "Educación Física", "Inglés", "Educación Religiosa", "Tutoría"],
    "Secundaria": ["Matemática", "Comunicación", "Ciencia y Tecnología", "Desarrollo Personal, Ciudadanía y Cívica",
                   "Ciencias Sociales", "Arte y Cultura", "Educación Física", "Inglés", "Educación para el Trabajo",
                   "Educación Religiosa", "Tutoría"],
}

usuario = db_fetch("SELECT creditos FROM usuarios WHERE id=%s", (st.session_state.user_id,), one=True)
creditos = usuario["creditos"] if usuario else 0

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3429/3429149.png", width=70)
    st.title("EduPerú IA 🇵🇪")
    st.write(f"👤 **{st.session_state.user_name}**")
    st.write(f"🎟️ Créditos: **{creditos}**")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    st.divider()
    nivel = st.selectbox("Nivel Educativo", list(GRADOS.keys()), index=1)
    grado = st.selectbox("Grado / Edad", GRADOS[nivel])
    area = st.selectbox("Área Curricular", AREAS[nivel])
    region = st.selectbox("Región / Contexto", ["Lima", "Piura", "Cusco", "Loreto", "Puno", "Arequipa", "Otra"])

# ------------------------------------------------------------------
# PANEL PRINCIPAL
# ------------------------------------------------------------------
st.title("🇵🇪 Asistente Pedagógico CNEB")
st.caption(f"{nivel} · {grado} · {area} · {region}")

tab_gen, tab_hist = st.tabs(["✨ Generar documento", "📁 Mis documentos"])

with tab_gen:
    tipo = st.selectbox("Tipo de documento", [
        "Sesión de aprendizaje", "Unidad de aprendizaje", "Programación anual",
        "Ficha de trabajo", "Rúbrica de evaluación", "Examen",
    ])
    tema = st.text_input("Tema o propósito (ej.: Sumas con llevada)")
    c1, c2 = st.columns(2)
    duracion = c1.number_input("Duración de la sesión (minutos)", min_value=15, max_value=240, value=90, step=5)
    contexto = c2.text_input("Contexto del aula (opcional)", placeholder="Ej.: aula multigrado rural, 25 estudiantes")

    if st.button("Generar con IA (1 crédito)", type="primary", use_container_width=True):
        if not tema.strip():
            st.warning("Escribe el tema o propósito.")
        elif creditos <= 0:
            st.error("No tienes créditos disponibles.")
        else:
            prompt = f"""Eres un especialista pedagógico peruano. Elabora un(a) {tipo} para:
- Nivel: {nivel} | Grado/Edad: {grado} | Área: {area}
- Región/contexto: {region}. Contexto adicional: {contexto or 'no especificado'}
- Tema: {tema}
- Duración: {duracion} minutos

Reglas:
- Alinéalo al Currículo Nacional de la Educación Básica (CNEB) y a la RM N.° 501-2025-MINEDU.
- Incluye: título, propósito de aprendizaje, competencia y capacidades, criterios de evaluación,
  evidencias, secuencia didáctica (inicio, desarrollo, cierre con tiempos), recursos e instrumento de evaluación.
- No inventes códigos ni textos oficiales; si no estás seguro de un desempeño exacto, indica
  "verificar en el Programa Curricular oficial".
- Contextualiza a la región indicada.
- Responde en español, con formato Markdown (títulos con # y listas con -)."""
            try:
                with st.spinner("Generando documento..."):
                    texto, proveedor = generar_texto(prompt)
                _, afectadas = db_execute(
                    "UPDATE usuarios SET creditos = creditos - 1 WHERE id=%s AND creditos > 0",
                    (st.session_state.user_id,),
                )
                st.session_state["resultado"] = {
                    "tipo": tipo, "titulo": f"{tipo}: {tema.strip()}",
                    "texto": texto, "proveedor": proveedor,
                }
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo generar el documento: {e}")

    res = st.session_state.get("resultado")
    if res:
        st.success(f"Documento generado con {res['proveedor']}")
        st.markdown(res["texto"])
        d1, d2 = st.columns(2)
        d1.download_button(
            "⬇️ Descargar Word",
            data=texto_a_docx(res["titulo"], res["texto"]),
            file_name="documento_eduperu.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
        if d2.button("💾 Guardar en mis documentos", use_container_width=True):
            db_execute(
                "INSERT INTO planificaciones (usuario_id, tipo_documento, titulo, contenido_texto) "
                "VALUES (%s, %s, %s, %s)",
                (st.session_state.user_id, res["tipo"], res["titulo"][:255], res["texto"]),
            )
            st.success("Guardado.")

with tab_hist:
    docs = db_fetch(
        "SELECT id, tipo_documento, titulo, contenido_texto, creado_en FROM planificaciones "
        "WHERE usuario_id=%s ORDER BY creado_en DESC LIMIT 20",
        (st.session_state.user_id,),
    )
    if not docs:
        st.info("Aún no has guardado documentos.")
    for d in docs:
        with st.expander(f"{d['titulo']} · {d['creado_en']:%d/%m/%Y}"):
            st.markdown(d["contenido_texto"])
            st.download_button(
                "⬇️ Word",
                data=texto_a_docx(d["titulo"], d["contenido_texto"]),
                file_name=f"documento_{d['id']}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key=f"dl_{d['id']}",
            )
