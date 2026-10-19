import io
import hashlib

import bcrypt
import pandas as pd
import requests
import streamlit as st
import mysql.connector
import google.generativeai as genai
from bs4 import BeautifulSoup
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

REGIONES = ["Amazonas", "Áncash", "Apurímac", "Arequipa", "Ayacucho", "Cajamarca", "Callao", "Cusco",
            "Huancavelica", "Huánuco", "Ica", "Junín", "La Libertad", "Lambayeque", "Lima", "Loreto",
            "Madre de Dios", "Moquegua", "Pasco", "Piura", "Puno", "San Martín", "Tacna", "Tumbes", "Ucayali"]
ROLES = ["docente", "director", "admin"]
TIPOS_NORMA = ["curricular", "pedagógico/normativo", "administrativo"]

FUENTES_INICIALES = [
    ("Normas y resoluciones del MINEDU", "https://www.gob.pe/institucion/minedu/normas-legales", "pedagógico/normativo"),
    ("Currículo Nacional (CNEB)", "https://www.gob.pe/institucion/minedu/campa%C3%B1as/106784-curriculo-nacional-de-la-educacion-basica", "curricular"),
    ("Programas curriculares EBR", "https://www.gob.pe/es/90158-ministerio-de-educacion-programas-curriculares-de-la-educacion-basica-regular", "curricular"),
    ("Norma Técnica Año Escolar 2026 (RM 501-2025-MINEDU)", "https://www.gob.pe/institucion/minedu/normas-legales/7380466-501-2025-minedu", "administrativo"),
]

# ------------------------------------------------------------------
# SEGURIDAD: CONTRASEÑAS
# ------------------------------------------------------------------
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
        ssl_disabled=False,
        connection_timeout=10,
    )


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


def _asegurar_columna(cur, tabla, columna, ddl):
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (tabla, columna),
    )
    if cur.fetchone()[0] == 0:
        cur.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {ddl}")


def _asegurar_admin(conn):
    if "admin" not in st.secrets:
        return
    adm = st.secrets["admin"]
    correo = str(adm.get("correo", "")).strip().lower()
    pw = str(adm.get("password", ""))
    nombre = str(adm.get("nombre", "Administrador"))
    if not correo or not pw:
        return
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, password_hash FROM usuarios WHERE correo=%s", (correo,))
    row = cur.fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO usuarios (nombre, correo, password_hash, rol, creditos, activo) "
            "VALUES (%s, %s, %s, 'admin', 9999, 1)",
            (nombre, correo, hash_password(pw)),
        )
    else:
        nuevo = row["password_hash"] if verify_password(pw, row["password_hash"]) else hash_password(pw)
        cur.execute("UPDATE usuarios SET rol='admin', activo=1, password_hash=%s WHERE id=%s", (nuevo, row["id"]))
    conn.commit()
    cur.close()


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
            normativa_usada VARCHAR(255) DEFAULT 'RM N.° 501-2025-MINEDU',
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS colegios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(150) NOT NULL,
            codigo_modular VARCHAR(20),
            region VARCHAR(50) DEFAULT 'Lima',
            ugel VARCHAR(80),
            activo TINYINT(1) DEFAULT 1,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS normativa_fuentes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(200) NOT NULL,
            url VARCHAR(600) NOT NULL,
            tipo VARCHAR(40) DEFAULT 'pedagógico/normativo',
            activa TINYINT(1) DEFAULT 1,
            ultima_revision DATETIME NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS normativa_versiones (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fuente_id INT NOT NULL,
            hash_contenido VARCHAR(64) NOT NULL,
            contenido LONGTEXT,
            resumen_cambios LONGTEXT,
            estado VARCHAR(20) DEFAULT 'pendiente',
            detectado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
            aprobado_por INT NULL,
            aprobado_en DATETIME NULL
        );
    """)
    _asegurar_columna(cur, "usuarios", "colegio_id", "INT NULL")
    _asegurar_columna(cur, "usuarios", "activo", "TINYINT(1) DEFAULT 1")
    cur.execute("ALTER TABLE planificaciones MODIFY normativa_usada VARCHAR(255) DEFAULT 'RM N.° 501-2025-MINEDU'")

    cur.execute("SELECT COUNT(*) FROM normativa_fuentes")
    if cur.fetchone()[0] == 0:
        for nombre, url, tipo in FUENTES_INICIALES:
            cur.execute("INSERT INTO normativa_fuentes (nombre, url, tipo) VALUES (%s, %s, %s)", (nombre, url, tipo))
    conn.commit()
    cur.close()
    _asegurar_admin(conn)
    conn.close()
    return True


try:
    db_connected = init_db()
except Exception as e:
    db_connected = False
    st.error(f"⚠️ No se pudo conectar a la base de datos: {type(e).__name__}")
    st.stop()


def mapa_colegios(solo_activos=True):
    sql = "SELECT id, nombre FROM colegios" + (" WHERE activo=1" if solo_activos else "") + " ORDER BY nombre"
    filas = db_fetch(sql)
    mapa = {0: "— Docente independiente / sin colegio —"}
    mapa.update({c["id"]: c["nombre"] for c in filas})
    return mapa


# ------------------------------------------------------------------
# IA: OPENROUTER PRIMERO, GEMINI DE RESPALDO
# ------------------------------------------------------------------
def llamar_openrouter(prompt: str) -> str:
    cfg = st.secrets["openrouter"]
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"},
        json={"model": cfg.get("model", "openai/gpt-4o-mini"),
              "messages": [{"role": "user", "content": prompt}]},
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def llamar_gemini(prompt: str) -> str:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    return genai.GenerativeModel("gemini-2.5-flash").generate_content(prompt).text


def generar_texto(prompt: str):
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
# MONITOR NORMATIVO MINEDU
# ------------------------------------------------------------------
UA = {"User-Agent": "Mozilla/5.0 (compatible; EduPeruIA-MonitorNormativo/1.0)"}


def html_a_texto(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "header", "footer", "nav", "form"]):
        t.decompose()
    return " ".join(soup.get_text(" ").split())


def resumir_cambios(nombre: str, nuevo: str, anterior: str | None) -> str:
    if anterior:
        prompt = f"""Compara dos capturas de texto de la fuente oficial «{nombre}» (MINEDU, Perú).
Indica SOLO los cambios relevantes para docentes y colegios y clasifícalos en:
curricular / pedagógico-normativo / administrativo.
Si no hay cambios sustantivos (solo ruido de la página), responde exactamente: "Sin cambios sustantivos (posible ruido de la página)".
No inventes nada que no esté en los textos.

=== VERSIÓN ANTERIOR ===
{anterior[:12000]}

=== VERSIÓN NUEVA ===
{nuevo[:12000]}"""
    else:
        prompt = f"""Resume en español la fuente oficial «{nombre}» (MINEDU, Perú) a partir de este texto.
Indica: qué norma o documento es, vigencia y los puntos clave aplicables a la planificación docente.
No inventes nada que no esté en el texto.

{nuevo[:15000]}"""
    try:
        texto, _ = generar_texto(prompt)
        return texto
    except Exception as e:
        return f"(No se pudo generar el resumen con IA: {e})"


def revisar_fuente(f: dict):
    """Devuelve (estado, mensaje): estado = nueva | sin_cambios | error."""
    try:
        r = requests.get(f["url"], headers=UA, timeout=30)
        r.raise_for_status()
        if "pdf" in r.headers.get("content-type", "").lower():
            return "error", "La fuente es un PDF (por ahora solo se leen páginas HTML)."
        texto = html_a_texto(r.text)[:200000]
        if len(texto) < 200:
            return "error", "La página devolvió muy poco texto (puede requerir JavaScript)."
    except Exception as e:
        return "error", f"No se pudo leer la fuente: {e}"

    h = hashlib.sha256(texto.encode()).hexdigest()
    ultimo = db_fetch(
        "SELECT hash_contenido, contenido FROM normativa_versiones WHERE fuente_id=%s ORDER BY id DESC LIMIT 1",
        (f["id"],), one=True,
    )
    db_execute("UPDATE normativa_fuentes SET ultima_revision=NOW() WHERE id=%s", (f["id"],))
    if ultimo and ultimo["hash_contenido"] == h:
        return "sin_cambios", "Sin cambios desde la última captura."

    resumen = resumir_cambios(f["nombre"], texto, ultimo["contenido"] if ultimo else None)
    db_execute(
        "INSERT INTO normativa_versiones (fuente_id, hash_contenido, contenido, resumen_cambios) VALUES (%s,%s,%s,%s)",
        (f["id"], h, texto, resumen),
    )
    return "nueva", "Nueva versión detectada, pendiente de aprobación."


def normativa_vigente():
    """(contexto para el prompt, etiqueta para el documento)."""
    filas = db_fetch(
        "SELECT f.nombre, v.resumen_cambios, v.aprobado_en FROM normativa_versiones v "
        "JOIN normativa_fuentes f ON f.id = v.fuente_id "
        "WHERE v.estado='approved' OR v.estado='aprobada' ORDER BY v.aprobado_en DESC LIMIT 5"
    )
    if not filas:
        return "", "RM N.° 501-2025-MINEDU"
    ctx = "\n\n".join(
        f"[{f['nombre']} · aprobada {f['aprobado_en']:%d/%m/%Y}]\n{f['resumen_cambios']}" for f in filas
    )[:4000]
    etiqueta = (f"RM N.° 501-2025-MINEDU + {len(filas)} actualización(es) verificada(s) "
                f"(última {filas[0]['aprobado_en']:%d/%m/%Y})")
    return ctx, etiqueta[:255]


# ------------------------------------------------------------------
# EXPORTAR A WORD
# ------------------------------------------------------------------
def texto_a_docx(titulo: str, contenido: str, pie: str | None = None) -> bytes:
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
    if pie:
        p = doc.add_paragraph()
        p.add_run(f"Normativa utilizada: {pie}").italic = True
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
                        user = db_fetch("SELECT * FROM usuarios WHERE correo = %s",
                                        (email_login.strip().lower(),), one=True)
                        if user and verify_password(pass_login, user["password_hash"]):
                            if user.get("activo") == 0:
                                st.error("Tu cuenta está desactivada. Contacta al administrador.")
                            else:
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
            colegios_reg = mapa_colegios(solo_activos=True)
            with st.form("register_form"):
                st.subheader("Crear Cuenta Nueva")
                nombre_reg = st.text_input("Nombre completo", key="r_nombre")
                email_reg = st.text_input("Correo electrónico", key="r_email")
                pass_reg = st.text_input("Contraseña (mínimo 8 caracteres)", type="password", key="r_pass")
                nivel_reg = st.selectbox("Nivel en el que enseñas", ["Inicial", "Primaria", "Secundaria"], key="r_nivel")
                colegio_reg = st.selectbox("Institución Educativa", list(colegios_reg.keys()),
                                           format_func=lambda k: colegios_reg[k], key="r_colegio")
                submit_reg = st.form_submit_button("Registrarme", type="primary", use_container_width=True)

            if submit_reg:
                correo_norm = email_reg.strip().lower()
                if not (nombre_reg and email_reg and pass_reg):
                    st.warning("Completa los campos obligatorios.")
                elif len(pass_reg) < 8:
                    st.warning("La contraseña debe tener al menos 8 caracteres.")
                elif correo_norm == admin_correo():
                    st.error("Este correo no está disponible.")
                else:
                    try:
                        db_execute(
                            "INSERT INTO usuarios (nombre, correo, password_hash, nivel_educativo, colegio, colegio_id) "
                            "VALUES (%s, %s, %s, %s, %s, %s)",
                            (nombre_reg.strip(), correo_norm, hash_password(pass_reg), nivel_reg,
                             colegios_reg[colegio_reg] if colegio_reg else "Independiente",
                             colegio_reg or None),
                        )
                        st.success("¡Cuenta creada con éxito! Ve a la pestaña 'Iniciar Sesión'.")
                    except mysql.connector.Error as err:
                        if err.errno == 1062:
                            st.error("Este correo ya está registrado.")
                        else:
                            st.error("Error al registrar. Intenta de nuevo.")
    st.stop()

# ------------------------------------------------------------------
# USUARIO AUTENTICADO: SE LEE SIEMPRE DE LA BD (rol, estado, créditos)
# ------------------------------------------------------------------
usuario = db_fetch(
    "SELECT id, nombre, rol, creditos, activo FROM usuarios WHERE id=%s",
    (st.session_state.user_id,), one=True,
)
if not usuario or usuario["activo"] == 0:
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

es_admin = usuario["rol"] == "admin"
creditos = usuario["creditos"]
ctx_norma, etiqueta_norma = normativa_vigente()

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

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3429/3429149.png", width=70)
    st.title("EduPerú IA 🇵🇪")
    st.write(f"👤 **{usuario['nombre']}**" + (" · 🛡️ Admin" if es_admin else ""))
    st.write("🎟️ Créditos: **ilimitados**" if es_admin else f"🎟️ Créditos: **{creditos}**")
    if es_admin:
        pend = db_fetch("SELECT COUNT(*) AS n FROM normativa_versiones WHERE estado='pendiente'", one=True)["n"]
        if pend:
            st.warning(f"📜 {pend} cambio(s) normativo(s) por revisar")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    st.divider()
    nivel = st.selectbox("Nivel Educativo", list(GRADOS.keys()), index=1)
    grado = st.selectbox("Grado / Edad", GRADOS[nivel])
    area = st.selectbox("Área Curricular", AREAS[nivel])
    region = st.selectbox("Región / Contexto", REGIONES, index=REGIONES.index("Lima"))

st.title("🇵🇪 Asistente Pedagógico CNEB")
st.caption(f"{nivel} · {grado} · {area} · {region}  |  📌 Normativa: {etiqueta_norma}")


# ------------------------------------------------------------------
# PANELES DE ADMINISTRACIÓN
# ------------------------------------------------------------------
def panel_resumen():
    st.subheader("Resumen")
    n_users = db_fetch("SELECT COUNT(*) AS n FROM usuarios", one=True)["n"]
    n_cols = db_fetch("SELECT COUNT(*) AS n FROM colegios", one=True)["n"]
    n_docs = db_fetch("SELECT COUNT(*) AS n FROM planificaciones", one=True)["n"]
    n_pend = db_fetch("SELECT COUNT(*) AS n FROM normativa_versiones WHERE estado='pendiente'", one=True)["n"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Usuarios", n_users)
    c2.metric("Colegios", n_cols)
    c3.metric("Documentos guardados", n_docs)
    c4.metric("Cambios normativos pendientes", n_pend)

    st.markdown("#### Últimos documentos de todos los usuarios")
    docs = db_fetch(
        "SELECT p.id, u.nombre AS usuario, p.tipo_documento AS tipo, p.titulo, p.normativa_usada AS normativa, p.creado_en "
        "FROM planificaciones p LEFT JOIN usuarios u ON u.id = p.usuario_id ORDER BY p.creado_en DESC LIMIT 30"
    )
    if docs:
        st.dataframe(pd.DataFrame(docs), use_container_width=True, hide_index=True)
    else:
        st.info("Todavía no hay documentos guardados.")


def panel_usuarios(admin_id: int):
    st.subheader("Usuarios")
    filas = db_fetch(
        "SELECT u.id, u.nombre, u.correo, u.rol, u.colegio_id, c.nombre AS colegio, "
        "u.nivel_educativo AS nivel, u.creditos, u.activo, u.creado_en "
        "FROM usuarios u LEFT JOIN colegios c ON c.id = u.colegio_id ORDER BY u.id DESC"
    )
    colegios = mapa_colegios(solo_activos=False)
    claves_col = list(colegios.keys())

    if filas:
        st.dataframe(pd.DataFrame(filas).drop(columns=["colegio_id"]), use_container_width=True, hide_index=True)

    with st.expander("➕ Crear usuario"):
        with st.form("crear_usuario", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre completo")
            correo = c2.text_input("Correo electrónico")
            pw = c1.text_input("Contraseña inicial (mínimo 8)", type="password")
            rol = c2.selectbox("Rol", ROLES)
            colegio = c1.selectbox("Colegio", claves_col, format_func=lambda k: colegios[k])
            nivel_u = c2.selectbox("Nivel", ["Inicial", "Primaria", "Secundaria"])
            cred = c1.number_input("Créditos", min_value=0, max_value=100000, value=50)
            enviar = st.form_submit_button("Crear usuario", type="primary")
        if enviar:
            if not (nombre and correo and pw):
                st.warning("Completa nombre, correo y contraseña.")
            elif len(pw) < 8:
                st.warning("La contraseña debe tener al menos 8 caracteres.")
            else:
                try:
                    db_execute(
                        "INSERT INTO usuarios (nombre, correo, password_hash, rol, colegio_id, colegio, nivel_educativo, creditos) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                        (nombre.strip(), correo.strip().lower(), hash_password(pw), rol,
                         colegio or None, colegios[colegio] if colegio else "Independiente", nivel_u, cred),
                    )
                    st.success("Usuario creado.")
                    st.rerun()
                except mysql.connector.Error as err:
                    st.error("Ese correo ya existe." if err.errno == 1062 else "No se pudo crear el usuario.")

    if filas:
        st.markdown("#### Editar o eliminar")
        opciones = {u["id"]: f"{u['id']} · {u['nombre']} · {u['correo']}" for u in filas}
        uid = st.selectbox("Usuario", list(opciones.keys()), format_func=lambda k: opciones[k], key="adm_user_sel")
        u = next(x for x in filas if x["id"] == uid)

        with st.form(f"edit_user_{uid}"):
            c1, c2 = st.columns(2)
            e_nombre = c1.text_input("Nombre", u["nombre"], key=f"en_{uid}")
            e_rol = c2.selectbox("Rol", ROLES, index=ROLES.index(u["rol"]) if u["rol"] in ROLES else 0, key=f"er_{uid}")
            actual = u["colegio_id"] or 0
            e_col = c1.selectbox("Colegio", claves_col, index=claves_col.index(actual) if actual in claves_col else 0,
                                 format_func=lambda k: colegios[k], key=f"ec_{uid}")
            e_cred = c2.number_input("Créditos", 0, 100000, int(u["creditos"]), key=f"ecr_{uid}")
            e_activo = c1.checkbox("Cuenta activa", bool(u["activo"]), key=f"ea_{uid}")
            e_pw = c2.text_input("Nueva contraseña (opcional)", type="password", key=f"ep_{uid}")
            guardar = st.form_submit_button("Guardar cambios", type="primary")
        if guardar:
            if uid == admin_id and (e_rol != "admin" or not e_activo):
                st.error("No puedes quitarte el rol de admin ni desactivarte a ti mismo.")
            elif e_pw and len(e_pw) < 8:
                st.warning("La nueva contraseña debe tener al menos 8 caracteres.")
            else:
                db_execute(
                    "UPDATE usuarios SET nombre=%s, rol=%s, colegio_id=%s, colegio=%s, creditos=%s, activo=%s WHERE id=%s",
                    (e_nombre.strip(), e_rol, e_col or None, colegios[e_col] if e_col else "Independiente",
                     e_cred, 1 if e_activo else 0, uid),
                )
                if e_pw:
                    db_execute("UPDATE usuarios SET password_hash=%s WHERE id=%s", (hash_password(e_pw), uid))
                st.success("Cambios guardados.")
                st.rerun()

        with st.expander("🗑️ Eliminar este usuario"):
            st.caption("También se eliminan los documentos que guardó.")
            confirmar = st.checkbox("Confirmo que quiero eliminarlo", key=f"cd_{uid}")
            if st.button("Eliminar usuario", key=f"del_{uid}"):
                if uid == admin_id:
                    st.error("No puedes eliminarte a ti mismo.")
                elif not confirmar:
                    st.warning("Marca la confirmación primero.")
                else:
                    db_execute("DELETE FROM planificaciones WHERE usuario_id=%s", (uid,))
                    db_execute("DELETE FROM usuarios WHERE id=%s", (uid,))
                    st.success("Usuario eliminado.")
                    st.rerun()


def panel_colegios():
    st.subheader("Colegios")
    filas = db_fetch(
        "SELECT c.id, c.nombre, c.codigo_modular, c.region, c.ugel, c.activo, "
        "(SELECT COUNT(*) FROM usuarios u WHERE u.colegio_id = c.id) AS usuarios "
        "FROM colegios c ORDER BY c.nombre"
    )
    if filas:
        st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay colegios registrados.")

    with st.expander("➕ Crear colegio"):
        with st.form("crear_colegio", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre de la institución")
            codigo = c2.text_input("Código modular (opcional)")
            reg = c1.selectbox("Región", REGIONES, index=REGIONES.index("Lima"))
            ugel = c2.text_input("UGEL (opcional)")
            enviar = st.form_submit_button("Crear colegio", type="primary")
        if enviar:
            if not nombre.strip():
                st.warning("Escribe el nombre del colegio.")
            else:
                db_execute("INSERT INTO colegios (nombre, codigo_modular, region, ugel) VALUES (%s,%s,%s,%s)",
                           (nombre.strip(), codigo.strip(), reg, ugel.strip()))
                st.success("Colegio creado.")
                st.rerun()

    if filas:
        st.markdown("#### Editar o eliminar")
        opciones = {c["id"]: f"{c['id']} · {c['nombre']}" for c in filas}
        cid = st.selectbox("Colegio", list(opciones.keys()), format_func=lambda k: opciones[k], key="adm_col_sel")
        c = next(x for x in filas if x["id"] == cid)
        with st.form(f"edit_col_{cid}"):
            c1, c2 = st.columns(2)
            e_nombre = c1.text_input("Nombre", c["nombre"], key=f"cn_{cid}")
            e_codigo = c2.text_input("Código modular", c["codigo_modular"] or "", key=f"cc_{cid}")
            e_reg = c1.selectbox("Región", REGIONES,
                                 index=REGIONES.index(c["region"]) if c["region"] in REGIONES else REGIONES.index("Lima"),
                                 key=f"cr_{cid}")
            e_ugel = c2.text_input("UGEL", c["ugel"] or "", key=f"cu_{cid}")
            e_activo = c1.checkbox("Activo", bool(c["activo"]), key=f"ca_{cid}")
            guardar = st.form_submit_button("Guardar cambios", type="primary")
        if guardar:
            db_execute("UPDATE colegios SET nombre=%s, codigo_modular=%s, region=%s, ugel=%s, activo=%s WHERE id=%s",
                       (e_nombre.strip(), e_codigo.strip(), e_reg, e_ugel.strip(), 1 if e_activo else 0, cid))
            db_execute("UPDATE usuarios SET colegio=%s WHERE colegio_id=%s", (e_nombre.strip(), cid))
            st.success("Cambios guardados.")
            st.rerun()

        with st.expander("🗑️ Eliminar este colegio"):
            if c["usuarios"] > 0:
                st.warning(f"Tiene {c['usuarios']} usuario(s) asignado(s). Reasígnalos o desactívalo en lugar de eliminarlo.")
            else:
                confirmar = st.checkbox("Confirmo que quiero eliminarlo", key=f"ccd_{cid}")
                if st.button("Eliminar colegio", key=f"cdel_{cid}"):
                    if confirmar:
                        db_execute("DELETE FROM colegios WHERE id=%s", (cid,))
                        st.success("Colegio eliminado.")
                        st.rerun()
                    else:
                        st.warning("Marca la confirmación primero.")


def panel_normativa(admin_id: int):
    st.subheader("Actualización normativa MINEDU")
    st.caption("La IA detecta cambios y los resume; nada se usa en los documentos hasta que lo apruebes. "
               "La IA no modifica el currículo oficial.")

    fuentes = db_fetch("SELECT * FROM normativa_fuentes ORDER BY id")

    if st.button("🔄 Revisar todas las fuentes activas ahora", type="primary"):
        with st.spinner("Consultando fuentes oficiales y analizando cambios..."):
            for f in fuentes:
                if f["activa"]:
                    estado, msg = revisar_fuente(f)
                    icono = {"nueva": "🆕", "sin_cambios": "✅", "error": "⚠️"}[estado]
                    st.write(f"{icono} **{f['nombre']}** — {msg}")

    st.markdown("#### Pendientes de revisión")
    pendientes = db_fetch(
        "SELECT v.id, f.nombre, f.tipo, v.resumen_cambios, v.detectado_en FROM normativa_versiones v "
        "JOIN normativa_fuentes f ON f.id = v.fuente_id WHERE v.estado='pendiente' ORDER BY v.id DESC"
    )
    if not pendientes:
        st.success("No hay cambios pendientes.")
    for p in pendientes:
        with st.expander(f"🆕 {p['nombre']} · {p['tipo']} · {p['detectado_en']:%d/%m/%Y %H:%M}"):
            st.markdown(p["resumen_cambios"] or "_Sin resumen_")
            b1, b2, _ = st.columns([1, 1, 3])
            if b1.button("✅ Aprobar", key=f"ap_{p['id']}"):
                db_execute("UPDATE normativa_versiones SET estado='aprobada', aprobado_por=%s, aprobado_en=NOW() WHERE id=%s",
                           (admin_id, p["id"]))
                st.rerun()
            if b2.button("❌ Rechazar", key=f"rj_{p['id']}"):
                db_execute("UPDATE normativa_versiones SET estado='rechazada', aprobado_por=%s, aprobado_en=NOW() WHERE id=%s",
                           (admin_id, p["id"]))
                st.rerun()

    st.markdown("#### Fuentes monitoreadas")
    if fuentes:
        st.dataframe(pd.DataFrame(fuentes), use_container_width=True, hide_index=True)
        opciones = {f["id"]: f"{f['id']} · {f['nombre']}" for f in fuentes}
        fid = st.selectbox("Fuente", list(opciones.keys()), format_func=lambda k: opciones[k], key="adm_fuente_sel")
        f = next(x for x in fuentes if x["id"] == fid)
        c1, c2 = st.columns(2)
        if c1.button("⏯️ Activar / desactivar", key=f"tg_{fid}"):
            db_execute("UPDATE normativa_fuentes SET activa=%s WHERE id=%s", (0 if f["activa"] else 1, fid))
            st.rerun()
        if c2.button("🗑️ Eliminar fuente y su historial", key=f"fd_{fid}"):
            db_execute("DELETE FROM normativa_versiones WHERE fuente_id=%s", (fid,))
            db_execute("DELETE FROM normativa_fuentes WHERE id=%s", (fid,))
            st.rerun()

    with st.expander("➕ Agregar fuente (MINEDU, DRE o UGEL)"):
        with st.form("nueva_fuente", clear_on_submit=True):
            n_nombre = st.text_input("Nombre")
            n_url = st.text_input("URL (página web HTML)")
            n_tipo = st.selectbox("Tipo de cambio que suele traer", TIPOS_NORMA)
            enviar = st.form_submit_button("Agregar", type="primary")
        if enviar:
            if n_nombre.strip() and n_url.strip().startswith(("http://", "https://")):
                db_execute("INSERT INTO normativa_fuentes (nombre, url, tipo) VALUES (%s,%s,%s)",
                           (n_nombre.strip(), n_url.strip(), n_tipo))
                st.success("Fuente agregada.")
                st.rerun()
            else:
                st.warning("Escribe un nombre y una URL que empiece con http:// o https://")

    st.markdown("#### Historial de versiones")
    hist = db_fetch(
        "SELECT v.id, f.nombre AS fuente, v.estado, v.detectado_en, v.aprobado_en FROM normativa_versiones v "
        "JOIN normativa_fuentes f ON f.id = v.fuente_id ORDER BY v.id DESC LIMIT 30"
    )
    if hist:
        st.dataframe(pd.DataFrame(hist), use_container_width=True, hide_index=True)


# ------------------------------------------------------------------
# PANEL PRINCIPAL
# ------------------------------------------------------------------
nombres_tabs = ["✨ Generar documento", "📁 Mis documentos"] + (["⚙️ Administración"] if es_admin else [])
tabs = st.tabs(nombres_tabs)
tab_gen, tab_hist = tabs[0], tabs[1]

with tab_gen:
    tipo = st.selectbox("Tipo de documento", [
        "Sesión de aprendizaje", "Unidad de aprendizaje", "Programación anual",
        "Ficha de trabajo", "Rúbrica de evaluación", "Examen",
    ])
    tema = st.text_input("Tema o propósito (ej.: Sumas con llevada)")
    c1, c2 = st.columns(2)
    duracion = c1.number_input("Duración de la sesión (minutos)", min_value=15, max_value=240, value=90, step=5)
    contexto = c2.text_input("Contexto del aula (opcional)", placeholder="Ej.: aula multigrado rural, 25 estudiantes")

    if st.button("Generar con IA" + ("" if es_admin else " (1 crédito)"), type="primary", use_container_width=True):
        if not tema.strip():
            st.warning("Escribe el tema o propósito.")
        elif (not es_admin) and creditos <= 0:
            st.error("No tienes créditos disponibles.")
        else:
            bloque_norma = (
                "- Disposiciones verificadas por el administrador (úsalas como referencia, sin contradecir el CNEB):\n"
                + ctx_norma
            ) if ctx_norma else ""
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
- Responde en español, con formato Markdown (títulos con # y listas con -).
{bloque_norma}"""
            try:
                with st.spinner("Generando documento..."):
                    texto, proveedor = generar_texto(prompt)
                if not es_admin:
                    db_execute("UPDATE usuarios SET creditos = creditos - 1 WHERE id=%s AND creditos > 0",
                               (usuario["id"],))
                st.session_state["resultado"] = {
                    "tipo": tipo, "titulo": f"{tipo}: {tema.strip()}", "texto": texto,
                    "proveedor": proveedor, "normativa": etiqueta_norma,
                }
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo generar el documento: {e}")

    res = st.session_state.get("resultado")
    if res:
        st.success(f"Documento generado con {res['proveedor']}")
        st.markdown(res["texto"])
        st.caption(f"Normativa utilizada: {res['normativa']}")
        d1, d2 = st.columns(2)
        d1.download_button(
            "⬇️ Descargar Word",
            data=texto_a_docx(res["titulo"], res["texto"], res["normativa"]),
            file_name="documento_eduperu.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
        if d2.button("💾 Guardar en mis documentos", use_container_width=True):
            db_execute(
                "INSERT INTO planificaciones (usuario_id, tipo_documento, titulo, contenido_texto, normativa_usada) "
                "VALUES (%s, %s, %s, %s, %s)",
                (usuario["id"], res["tipo"], res["titulo"][:255], res["texto"], res["normativa"]),
            )
            st.success("Guardado.")

with tab_hist:
    docs = db_fetch(
        "SELECT id, tipo_documento, titulo, contenido_texto, normativa_usada, creado_en FROM planificaciones "
        "WHERE usuario_id=%s ORDER BY creado_en DESC LIMIT 20",
        (usuario["id"],),
    )
    if not docs:
        st.info("Aún no has guardado documentos.")
    for d in docs:
        with st.expander(f"{d['titulo']} · {d['creado_en']:%d/%m/%Y}"):
            st.markdown(d["contenido_texto"])
            st.caption(f"Normativa utilizada: {d['normativa_usada']}")
            st.download_button(
                "⬇️ Word",
                data=texto_a_docx(d["titulo"], d["contenido_texto"], d["normativa_usada"]),
                file_name=f"documento_{d['id']}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key=f"dl_{d['id']}",
            )

if es_admin:
    with tabs[2]:
        sub_res, sub_usr, sub_col, sub_norm = st.tabs(
            ["📊 Resumen", "👥 Usuarios", "🏫 Colegios", "📜 Normativa MINEDU"]
        )
        with sub_res:
            panel_resumen()
        with sub_usr:
            panel_usuarios(usuario["id"])
        with sub_col:
            panel_colegios()
        with sub_norm:
            panel_normativa(usuario["id"])
