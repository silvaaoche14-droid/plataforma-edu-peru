"""EduPerú IA — portal docente (VERSIÓN DE UN SOLO ARCHIVO).

Este archivo contiene TODO el sistema: arriba está el cargador y la aplicación principal, y al final
(bloques que empiezan con «#@@ MODULE») el código de cada módulo. No borres esos bloques.
"""
import linecache
import sys
import types

_ORDEN = ['util', 'db', 'curriculo', 'repo', 'render', 'exportar', 'ia', 'normativa', 'auth', 'ui', 'v_panel', 'v_anual', 'v_unidades', 'v_sesiones', 'v_biblioteca', 'v_admin']


def _cargar_modulos():
    with open(__file__, encoding="utf-8") as f:
        lineas = f.read().split("\n")
    bloques, actual = {}, None
    for linea in lineas:
        if linea.startswith("#@@ MODULE "):
            actual = linea[len("#@@ MODULE "):].strip()
            bloques[actual] = []
        elif linea.startswith("#@@ END"):
            actual = None
        elif actual is not None and linea.startswith("#|"):
            bloques[actual].append(linea[3:] if len(linea) > 2 else "")
    for nombre in _ORDEN:
        if nombre in sys.modules:
            continue
        codigo = "\n".join(bloques[nombre]) + "\n"
        archivo = f"<eduperu:{nombre}.py>"
        linecache.cache[archivo] = (len(codigo), None, codigo.splitlines(True), archivo)
        modulo = types.ModuleType(nombre)
        modulo.__file__ = archivo
        sys.modules[nombre] = modulo
        exec(compile(codigo, archivo, "exec"), modulo.__dict__)


_cargar_modulos()

# ======================= APLICACIÓN PRINCIPAL =======================

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


# ======================================================================
# MÓDULOS DEL SISTEMA (no borrar: el cargador de arriba los lee desde aquí)
# ======================================================================
#@@ MODULE util
#| """Funciones pequeñas de ayuda (sin dependencias de Streamlit)."""
#| import re
#| import unicodedata
#|
#|
#| def norm(texto) -> str:
#|     """Normaliza un texto para comparar nombres (sin tildes, minúsculas, sin signos)."""
#|     t = unicodedata.normalize("NFD", str(texto or ""))
#|     t = "".join(c for c in t if unicodedata.category(c) != "Mn")
#|     t = re.sub(r"[^a-z0-9 ]+", " ", t.lower())
#|     return re.sub(r"\s+", " ", t).strip()
#|
#|
#| def s(valor) -> str:
#|     """Convierte cualquier valor a texto limpio (las listas se unen por saltos de línea)."""
#|     if valor is None:
#|         return ""
#|     if isinstance(valor, (list, tuple)):
#|         return "\n".join(s(v) for v in valor if s(v))
#|     return str(valor).replace("**", "").strip()
#|
#|
#| def a_lista(valor) -> list:
#|     """Convierte texto con saltos de línea (o lista) en lista de textos no vacíos."""
#|     if valor is None:
#|         return []
#|     if isinstance(valor, (list, tuple)):
#|         items = [s(v) for v in valor]
#|     else:
#|         items = [x.strip() for x in str(valor).replace("**", "").split("\n")]
#|     limpios = []
#|     for x in items:
#|         x = re.sub(r"^[\-\*•·]\s*", "", x).strip()
#|         if x:
#|             limpios.append(x)
#|     return limpios
#|
#|
#| def a_texto(lista) -> str:
#|     return "\n".join(a_lista(lista))
#|
#|
#| def entero(valor, defecto=0, minimo=None, maximo=None) -> int:
#|     try:
#|         n = int(float(valor))
#|     except (TypeError, ValueError):
#|         n = defecto
#|     if minimo is not None:
#|         n = max(minimo, n)
#|     if maximo is not None:
#|         n = min(maximo, n)
#|     return n
#|
#|
#| def slug(texto) -> str:
#|     t = norm(texto).replace(" ", "_")
#|     return t[:60] or "documento"
#@@ END
#@@ MODULE db
#| """Conexión a MySQL (Aiven) y creación / actualización automática del esquema."""
#| import streamlit as st
#| import mysql.connector
#| from mysql.connector import pooling
#|
#|
#| def _cfg():
#|     s = st.secrets["mysql"]
#|     return dict(
#|         host=s["host"], port=int(s["port"]), database=s["database"],
#|         user=s["user"], password=s["password"],
#|         ssl_disabled=False, connection_timeout=10,
#|     )
#|
#|
#| @st.cache_resource(show_spinner=False)
#| def _pool():
#|     return pooling.MySQLConnectionPool(pool_name="eduperu_pool", pool_size=5, pool_reset_session=True, **_cfg())
#|
#|
#| def conexion():
#|     """Conexión reutilizable (pool). Si el pool falla, abre una conexión directa."""
#|     try:
#|         conn = _pool().get_connection()
#|         conn.ping(reconnect=True, attempts=2, delay=1)
#|         return conn
#|     except Exception:
#|         return mysql.connector.connect(**_cfg())
#|
#|
#| def fetch(sql, params=(), one=False):
#|     conn = conexion()
#|     try:
#|         cur = conn.cursor(dictionary=True, buffered=True)
#|         cur.execute(sql, params)
#|         filas = cur.fetchone() if one else cur.fetchall()
#|         cur.close()
#|         return filas
#|     finally:
#|         conn.close()
#|
#|
#| def execute(sql, params=()):
#|     """Ejecuta INSERT/UPDATE/DELETE. Devuelve (último id, filas afectadas)."""
#|     conn = conexion()
#|     try:
#|         cur = conn.cursor(buffered=True)
#|         cur.execute(sql, params)
#|         conn.commit()
#|         res = (cur.lastrowid, cur.rowcount)
#|         cur.close()
#|         return res
#|     finally:
#|         conn.close()
#|
#|
#| def execute_many(sql, filas):
#|     if not filas:
#|         return
#|     conn = conexion()
#|     try:
#|         cur = conn.cursor(buffered=True)
#|         cur.executemany(sql, filas)
#|         conn.commit()
#|         cur.close()
#|     finally:
#|         conn.close()
#|
#|
#| def _asegurar_columna(cur, tabla, columna, ddl):
#|     cur.execute(
#|         "SELECT COUNT(*) FROM information_schema.COLUMNS "
#|         "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
#|         (tabla, columna),
#|     )
#|     if cur.fetchone()[0] == 0:
#|         cur.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {ddl}")
#|
#|
#| def _asegurar_admin(conn):
#|     """Crea (o promueve) al administrador definido en Secrets [admin]."""
#|     if "admin" not in st.secrets:
#|         return
#|     from auth import hash_password, verify_password
#|     adm = st.secrets["admin"]
#|     correo = str(adm.get("correo", "")).strip().lower()
#|     pw = str(adm.get("password", ""))
#|     nombre = str(adm.get("nombre", "Administrador"))
#|     if not correo or not pw:
#|         return
#|     cur = conn.cursor(dictionary=True, buffered=True)
#|     cur.execute("SELECT id, password_hash FROM usuarios WHERE correo=%s", (correo,))
#|     row = cur.fetchone()
#|     if row is None:
#|         cur.execute(
#|             "INSERT INTO usuarios (nombre, correo, password_hash, rol, creditos, activo) "
#|             "VALUES (%s, %s, %s, 'admin', 9999, 1)",
#|             (nombre, correo, hash_password(pw)),
#|         )
#|     else:
#|         nuevo = row["password_hash"] if verify_password(pw, row["password_hash"]) else hash_password(pw)
#|         cur.execute("UPDATE usuarios SET rol='admin', activo=1, password_hash=%s WHERE id=%s", (nuevo, row["id"]))
#|     conn.commit()
#|     cur.close()
#|
#|
#| FUENTES_INICIALES = [
#|     ("Normas y resoluciones del MINEDU", "https://www.gob.pe/institucion/minedu/normas-legales", "pedagógico/normativo"),
#|     ("Currículo Nacional (CNEB)", "https://www.gob.pe/institucion/minedu/campa%C3%B1as/106784-curriculo-nacional-de-la-educacion-basica", "curricular"),
#|     ("Programas curriculares EBR", "https://www.gob.pe/es/90158-ministerio-de-educacion-programas-curriculares-de-la-educacion-basica-regular", "curricular"),
#|     ("Norma Técnica Año Escolar 2026 (RM 501-2025-MINEDU)", "https://www.gob.pe/institucion/minedu/normas-legales/7380466-501-2025-minedu", "administrativo"),
#| ]
#|
#| TABLAS = [
#|     """CREATE TABLE IF NOT EXISTS usuarios (
#|         id INT AUTO_INCREMENT PRIMARY KEY,
#|         nombre VARCHAR(100) NOT NULL,
#|         correo VARCHAR(100) UNIQUE NOT NULL,
#|         password_hash VARCHAR(255) NOT NULL,
#|         region VARCHAR(50) DEFAULT 'Lima',
#|         colegio VARCHAR(100),
#|         nivel_educativo VARCHAR(30),
#|         rol VARCHAR(30) DEFAULT 'docente',
#|         creditos INT DEFAULT 50,
#|         creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#|     )""",
#|     """CREATE TABLE IF NOT EXISTS planificaciones (
#|         id INT AUTO_INCREMENT PRIMARY KEY,
#|         usuario_id INT,
#|         tipo_documento VARCHAR(50),
#|         titulo VARCHAR(255) NOT NULL,
#|         contenido_texto LONGTEXT NOT NULL,
#|         normativa_usada VARCHAR(255) DEFAULT 'RM N.° 501-2025-MINEDU',
#|         creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#|     )""",
#|     """CREATE TABLE IF NOT EXISTS colegios (
#|         id INT AUTO_INCREMENT PRIMARY KEY,
#|         nombre VARCHAR(150) NOT NULL,
#|         codigo_modular VARCHAR(20),
#|         region VARCHAR(50) DEFAULT 'Lima',
#|         ugel VARCHAR(80),
#|         activo TINYINT(1) DEFAULT 1,
#|         creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#|     )""",
#|     """CREATE TABLE IF NOT EXISTS normativa_fuentes (
#|         id INT AUTO_INCREMENT PRIMARY KEY,
#|         nombre VARCHAR(200) NOT NULL,
#|         url VARCHAR(600) NOT NULL,
#|         tipo VARCHAR(40) DEFAULT 'pedagógico/normativo',
#|         activa TINYINT(1) DEFAULT 1,
#|         ultima_revision DATETIME NULL
#|     )""",
#|     """CREATE TABLE IF NOT EXISTS normativa_versiones (
#|         id INT AUTO_INCREMENT PRIMARY KEY,
#|         fuente_id INT NOT NULL,
#|         hash_contenido VARCHAR(64) NOT NULL,
#|         contenido LONGTEXT,
#|         resumen_cambios LONGTEXT,
#|         estado VARCHAR(20) DEFAULT 'pendiente',
#|         detectado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
#|         aprobado_por INT NULL,
#|         aprobado_en DATETIME NULL
#|     )""",
#|     """CREATE TABLE IF NOT EXISTS asignaciones (
#|         id INT AUTO_INCREMENT PRIMARY KEY,
#|         usuario_id INT NOT NULL,
#|         ciclo_escolar INT DEFAULT 2026,
#|         institucion VARCHAR(150),
#|         director VARCHAR(120),
#|         docente VARCHAR(120),
#|         region VARCHAR(50) DEFAULT 'Lima',
#|         nivel VARCHAR(20) NOT NULL,
#|         grado VARCHAR(20) NOT NULL,
#|         area VARCHAR(80) NOT NULL,
#|         seccion VARCHAR(20),
#|         caracterizacion LONGTEXT,
#|         creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#|         INDEX idx_asig_usuario (usuario_id)
#|     )""",
#|     """CREATE TABLE IF NOT EXISTS documentos (
#|         id INT AUTO_INCREMENT PRIMARY KEY,
#|         usuario_id INT NOT NULL,
#|         asignacion_id INT NOT NULL,
#|         tipo VARCHAR(20) NOT NULL,
#|         padre_id INT NULL,
#|         numero INT DEFAULT 1,
#|         titulo VARCHAR(255),
#|         contenido LONGTEXT,
#|         color VARCHAR(7) DEFAULT '1F3B8F',
#|         normativa_usada VARCHAR(255),
#|         creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#|         actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
#|         INDEX idx_doc_asig_tipo (asignacion_id, tipo)
#|     )""",
#|     """CREATE TABLE IF NOT EXISTS curriculo_competencias (
#|         id INT AUTO_INCREMENT PRIMARY KEY,
#|         nivel VARCHAR(20) NOT NULL,
#|         area VARCHAR(80) NOT NULL,
#|         nombre VARCHAR(500) NOT NULL,
#|         orden INT DEFAULT 0,
#|         verificado TINYINT(1) DEFAULT 0,
#|         INDEX idx_comp_nivel_area (nivel, area)
#|     )""",
#|     """CREATE TABLE IF NOT EXISTS curriculo_capacidades (
#|         id INT AUTO_INCREMENT PRIMARY KEY,
#|         competencia_id INT NOT NULL,
#|         nombre VARCHAR(500) NOT NULL,
#|         orden INT DEFAULT 0,
#|         INDEX idx_cap_comp (competencia_id)
#|     )""",
#|     """CREATE TABLE IF NOT EXISTS curriculo_desempenos (
#|         id INT AUTO_INCREMENT PRIMARY KEY,
#|         competencia_id INT NOT NULL,
#|         grado VARCHAR(20) NOT NULL,
#|         texto TEXT NOT NULL,
#|         orden INT DEFAULT 0,
#|         INDEX idx_des_comp_grado (competencia_id, grado)
#|     )""",
#|     """CREATE TABLE IF NOT EXISTS curriculo_transversal (
#|         id INT AUTO_INCREMENT PRIMARY KEY,
#|         tipo VARCHAR(20) NOT NULL,
#|         nombre VARCHAR(300) NOT NULL,
#|         detalle TEXT
#|     )""",
#|     """CREATE TABLE IF NOT EXISTS config (
#|         clave VARCHAR(60) PRIMARY KEY,
#|         valor VARCHAR(255)
#|     )""",
#| ]
#|
#|
#| @st.cache_resource(show_spinner=False)
#| def init_db():
#|     conn = conexion()
#|     try:
#|         cur = conn.cursor(buffered=True)
#|         for ddl in TABLAS:
#|             cur.execute(ddl)
#|
#|         # Columnas que pueden faltar si las tablas se crearon con versiones anteriores
#|         for col, ddl in [("nombre", "VARCHAR(100)"), ("correo", "VARCHAR(100)"), ("password_hash", "VARCHAR(255)"),
#|                          ("region", "VARCHAR(50) DEFAULT 'Lima'"), ("colegio", "VARCHAR(100)"),
#|                          ("nivel_educativo", "VARCHAR(30)"), ("rol", "VARCHAR(30) DEFAULT 'docente'"),
#|                          ("creditos", "INT DEFAULT 50"), ("creado_en", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
#|                          ("colegio_id", "INT NULL"), ("activo", "TINYINT(1) DEFAULT 1")]:
#|             _asegurar_columna(cur, "usuarios", col, ddl)
#|         for col, ddl in [("usuario_id", "INT"), ("tipo_documento", "VARCHAR(50)"), ("titulo", "VARCHAR(255)"),
#|                          ("contenido_texto", "LONGTEXT"),
#|                          ("normativa_usada", "VARCHAR(255) DEFAULT 'RM N.° 501-2025-MINEDU'"),
#|                          ("creado_en", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")]:
#|             _asegurar_columna(cur, "planificaciones", col, ddl)
#|         cur.execute("ALTER TABLE planificaciones MODIFY normativa_usada VARCHAR(255) DEFAULT 'RM N.° 501-2025-MINEDU'")
#|
#|         cur.execute("SELECT COUNT(*) FROM normativa_fuentes")
#|         if cur.fetchone()[0] == 0:
#|             for nombre, url, tipo in FUENTES_INICIALES:
#|                 cur.execute("INSERT INTO normativa_fuentes (nombre, url, tipo) VALUES (%s, %s, %s)", (nombre, url, tipo))
#|         conn.commit()
#|         cur.close()
#|
#|         from curriculo import sembrar_curriculo
#|         sembrar_curriculo(conn)
#|         _asegurar_admin(conn)
#|     finally:
#|         conn.close()
#|     return True
#@@ END
#@@ MODULE curriculo
#| """Base curricular verificada: competencias, capacidades, desempeños y transversales.
#|
#| Las competencias y capacidades base se cargan una sola vez (marcadas como "por verificar").
#| Los desempeños los carga el administrador (Excel/CSV) desde los Programas Curriculares oficiales.
#| La IA NUNCA inventa estos textos: solo elige entre los que están en esta base.
#| """
#| import streamlit as st
#| from db import fetch, execute
#| from util import norm
#|
#| NIVELES = ["Inicial", "Primaria", "Secundaria"]
#| GRADOS = {
#|     "Inicial": ["3 años", "4 años", "5 años"],
#|     "Primaria": ["1.° grado", "2.° grado", "3.° grado", "4.° grado", "5.° grado", "6.° grado"],
#|     "Secundaria": ["1.° grado", "2.° grado", "3.° grado", "4.° grado", "5.° grado"],
#| }
#| CICLOS = {
#|     "Inicial": {"3 años": "II", "4 años": "II", "5 años": "II"},
#|     "Primaria": {"1.° grado": "III", "2.° grado": "III", "3.° grado": "IV", "4.° grado": "IV",
#|                  "5.° grado": "V", "6.° grado": "V"},
#|     "Secundaria": {"1.° grado": "VI", "2.° grado": "VI", "3.° grado": "VII", "4.° grado": "VII", "5.° grado": "VII"},
#| }
#| REGIONES = ["Amazonas", "Áncash", "Apurímac", "Arequipa", "Ayacucho", "Cajamarca", "Callao", "Cusco",
#|             "Huancavelica", "Huánuco", "Ica", "Junín", "La Libertad", "Lambayeque", "Lima", "Loreto",
#|             "Madre de Dios", "Moquegua", "Pasco", "Piura", "Puno", "San Martín", "Tacna", "Tumbes", "Ucayali"]
#|
#|
#| def ciclo_de(nivel, grado):
#|     return CICLOS.get(nivel, {}).get(grado, "")
#|
#|
#| # ------------------------------------------------------------------
#| # DATOS BASE (CNEB)
#| # ------------------------------------------------------------------
#| _ORAL = ["Obtiene información del texto oral", "Infiere e interpreta información del texto oral",
#|          "Adecúa, organiza y desarrolla las ideas de forma coherente y cohesionada",
#|          "Utiliza recursos no verbales y paraverbales de forma estratégica",
#|          "Interactúa estratégicamente con distintos interlocutores",
#|          "Reflexiona y evalúa la forma, el contenido y contexto del texto oral"]
#| _LEE = ["Obtiene información del texto escrito", "Infiere e interpreta información del texto",
#|         "Reflexiona y evalúa la forma, el contenido y contexto del texto"]
#| _ESCRIBE = ["Adecúa el texto a la situación comunicativa",
#|             "Organiza y desarrolla las ideas de forma coherente y cohesionada",
#|             "Utiliza convenciones del lenguaje escrito de forma pertinente",
#|             "Reflexiona y evalúa la forma, el contenido y contexto del texto escrito"]
#| _CREA = ["Explora y experimenta los lenguajes del arte", "Aplica procesos creativos",
#|          "Evalúa y comunica sus procesos y proyectos"]
#|
#| COMPETENCIAS = {
#|     "cantidad": ("Resuelve problemas de cantidad",
#|                  ["Traduce cantidades a expresiones numéricas", "Comunica su comprensión sobre los números y las operaciones",
#|                   "Usa estrategias y procedimientos de estimación y cálculo",
#|                   "Argumenta afirmaciones sobre las relaciones numéricas y las operaciones"]),
#|     "regularidad": ("Resuelve problemas de regularidad, equivalencia y cambio",
#|                     ["Traduce datos y condiciones a expresiones algebraicas y gráficas",
#|                      "Comunica su comprensión sobre las relaciones algebraicas",
#|                      "Usa estrategias y procedimientos para encontrar equivalencias y reglas generales",
#|                      "Argumenta afirmaciones sobre relaciones de cambio y equivalencia"]),
#|     "forma": ("Resuelve problemas de forma, movimiento y localización",
#|               ["Modela objetos con formas geométricas y sus transformaciones",
#|                "Comunica su comprensión sobre las formas y relaciones geométricas",
#|                "Usa estrategias y procedimientos para orientarse en el espacio",
#|                "Argumenta afirmaciones sobre relaciones geométricas"]),
#|     "datos": ("Resuelve problemas de gestión de datos e incertidumbre",
#|               ["Representa datos con gráficos y medidas estadísticas o probabilísticas",
#|                "Comunica la comprensión de los conceptos estadísticos y probabilísticos",
#|                "Usa estrategias y procedimientos para recopilar y procesar datos",
#|                "Sustenta conclusiones o decisiones con base en la información obtenida"]),
#|     "oral": ("Se comunica oralmente en su lengua materna", _ORAL),
#|     "lee": ("Lee diversos tipos de textos escritos en su lengua materna", _LEE),
#|     "escribe": ("Escribe diversos tipos de textos en su lengua materna", _ESCRIBE),
#|     "crea": ("Crea proyectos desde los lenguajes artísticos", _CREA),
#|     "aprecia": ("Aprecia de manera crítica manifestaciones artístico-culturales",
#|                 ["Percibe manifestaciones artístico-culturales", "Contextualiza manifestaciones culturales",
#|                  "Reflexiona creativa y críticamente"]),
#|     "oral_en": ("Se comunica oralmente en inglés como lengua extranjera", _ORAL),
#|     "lee_en": ("Lee diversos tipos de textos escritos en inglés como lengua extranjera", _LEE),
#|     "escribe_en": ("Escribe diversos tipos de textos en inglés como lengua extranjera", _ESCRIBE),
#|     "indaga": ("Indaga mediante métodos científicos para construir sus conocimientos",
#|                ["Problematiza situaciones", "Diseña estrategias para hacer indagación",
#|                 "Genera y registra datos o información", "Analiza datos e información",
#|                 "Evalúa y comunica el proceso y resultados de su indagación"]),
#|     "explica": ("Explica el mundo físico basándose en conocimientos sobre los seres vivos, materia y energía, "
#|                 "biodiversidad, Tierra y universo",
#|                 ["Comprende y usa conocimientos sobre los seres vivos, materia y energía, biodiversidad, Tierra y universo",
#|                  "Evalúa las implicancias del saber y del quehacer científico y tecnológico"]),
#|     "disena": ("Diseña y construye soluciones tecnológicas para resolver problemas de su entorno",
#|                ["Determina una alternativa de solución tecnológica", "Diseña la alternativa de solución tecnológica",
#|                 "Implementa y valida la alternativa de solución tecnológica",
#|                 "Evalúa y comunica el funcionamiento y los impactos de su alternativa de solución tecnológica"]),
#|     "identidad": ("Construye su identidad",
#|                   ["Se valora a sí mismo", "Autorregula sus emociones", "Reflexiona y argumenta éticamente",
#|                    "Vive su sexualidad de manera integral y responsable de acuerdo a su etapa de desarrollo y madurez"]),
#|     "identidad_ini": ("Construye su identidad", ["Se valora a sí mismo", "Autorregula sus emociones"]),
#|     "convive": ("Convive y participa democráticamente en la búsqueda del bien común",
#|                 ["Interactúa con todas las personas", "Construye normas y asume acuerdos y leyes",
#|                  "Maneja conflictos de manera constructiva", "Delibera sobre asuntos públicos",
#|                  "Participa en acciones que promueven el bienestar común"]),
#|     "historia": ("Construye interpretaciones históricas",
#|                  ["Interpreta críticamente fuentes diversas", "Comprende el tiempo histórico",
#|                   "Elabora explicaciones sobre procesos históricos"]),
#|     "espacio": ("Gestiona responsablemente el espacio y el ambiente",
#|                 ["Comprende las relaciones entre los elementos naturales y sociales",
#|                  "Maneja fuentes de información para comprender el espacio geográfico y el ambiente",
#|                  "Genera acciones para conservar el ambiente local y global"]),
#|     "economia": ("Gestiona responsablemente los recursos económicos",
#|                  ["Comprende las relaciones entre los elementos del sistema económico y financiero",
#|                   "Toma decisiones económicas y financieras"]),
#|     "motricidad": ("Se desenvuelve de manera autónoma a través de su motricidad",
#|                    ["Comprende su cuerpo", "Se expresa corporalmente"]),
#|     "vida_saludable": ("Asume una vida saludable",
#|                        ["Comprende las relaciones entre la actividad física, alimentación, postura e higiene corporal y la salud",
#|                         "Incorpora prácticas que mejoran su calidad de vida"]),
#|     "sociomotrices": ("Interactúa a través de sus habilidades sociomotrices",
#|                       ["Se relaciona utilizando sus habilidades sociomotrices", "Crea y aplica estrategias y tácticas de juego"]),
#|     "rel_identidad": ("Construye su identidad como persona humana, amada por Dios, digna, libre y trascendente, "
#|                       "comprendiendo la doctrina de su propia religión, abierto al diálogo con las que le son cercanas",
#|                       ["Conoce a Dios y asume su identidad religiosa y espiritual como persona digna, libre y trascendente",
#|                        "Cultiva y valora las manifestaciones religiosas de su entorno argumentando su fe de manera comprensible y respetuosa"]),
#|     "rel_encuentro": ("Asume la experiencia del encuentro personal y comunitario con Dios en su proyecto de vida "
#|                       "en coherencia con su creencia religiosa",
#|                       ["Transforma su entorno desde el encuentro personal y comunitario con Dios y desde la fe que profesa",
#|                        "Actúa coherentemente en razón de su fe según los principios de su conciencia moral en situaciones concretas de la vida"]),
#|     "emprende": ("Gestiona proyectos de emprendimiento económico o social",
#|                  ["Crea propuestas de valor", "Aplica habilidades técnicas",
#|                   "Trabaja cooperativamente para lograr objetivos y metas",
#|                   "Evalúa los resultados del proyecto de emprendimiento"]),
#| }
#|
#| _REL = ["rel_identidad", "rel_encuentro"]
#| _MAT4 = ["cantidad", "regularidad", "forma", "datos"]
#| CATALOGO = {
#|     ("Inicial", "Personal Social"): ["identidad_ini", "convive"],
#|     ("Inicial", "Psicomotricidad"): ["motricidad"],
#|     ("Inicial", "Comunicación"): ["oral", "lee", "escribe", "crea"],
#|     ("Inicial", "Matemática"): ["cantidad", "forma"],
#|     ("Inicial", "Ciencia y Tecnología"): ["indaga"],
#|     ("Inicial", "Educación Religiosa"): _REL,
#|     ("Primaria", "Matemática"): _MAT4,
#|     ("Primaria", "Comunicación"): ["oral", "lee", "escribe"],
#|     ("Primaria", "Ciencia y Tecnología"): ["indaga", "explica", "disena"],
#|     ("Primaria", "Personal Social"): ["identidad", "convive", "historia", "espacio", "economia"],
#|     ("Primaria", "Arte y Cultura"): ["aprecia", "crea"],
#|     ("Primaria", "Educación Física"): ["motricidad", "vida_saludable", "sociomotrices"],
#|     ("Primaria", "Inglés"): ["oral_en", "lee_en", "escribe_en"],
#|     ("Primaria", "Educación Religiosa"): _REL,
#|     ("Secundaria", "Matemática"): _MAT4,
#|     ("Secundaria", "Comunicación"): ["oral", "lee", "escribe"],
#|     ("Secundaria", "Ciencia y Tecnología"): ["indaga", "explica", "disena"],
#|     ("Secundaria", "Ciencias Sociales"): ["historia", "espacio", "economia"],
#|     ("Secundaria", "Desarrollo Personal, Ciudadanía y Cívica"): ["identidad", "convive"],
#|     ("Secundaria", "Arte y Cultura"): ["aprecia", "crea"],
#|     ("Secundaria", "Educación Física"): ["motricidad", "vida_saludable", "sociomotrices"],
#|     ("Secundaria", "Inglés"): ["oral_en", "lee_en", "escribe_en"],
#|     ("Secundaria", "Educación para el Trabajo"): ["emprende"],
#|     ("Secundaria", "Educación Religiosa"): _REL,
#| }
#|
#| TRANSVERSALES = [
#|     ("competencia", "Se desenvuelve en entornos virtuales generados por las TIC",
#|      "Personaliza entornos virtuales\nGestiona información del entorno virtual\n"
#|      "Interactúa en entornos virtuales\nCrea objetos virtuales en diversos formatos"),
#|     ("competencia", "Gestiona su aprendizaje de manera autónoma",
#|      "Define metas de aprendizaje\nOrganiza acciones estratégicas para alcanzar sus metas de aprendizaje\n"
#|      "Monitorea y ajusta su desempeño durante el proceso de aprendizaje"),
#|     ("enfoque", "Enfoque de Derechos",
#|      "Conciencia de derechos\nLibertad y responsabilidad\nDiálogo y concertación"),
#|     ("enfoque", "Enfoque Inclusivo o de Atención a la diversidad",
#|      "Respeto por las diferencias\nEquidad en la enseñanza\nConfianza en la persona"),
#|     ("enfoque", "Enfoque Intercultural",
#|      "Respeto a la identidad cultural\nJusticia\nDiálogo intercultural"),
#|     ("enfoque", "Enfoque Igualdad de género", "Igualdad y Dignidad\nJusticia\nEmpatía"),
#|     ("enfoque", "Enfoque Ambiental",
#|      "Solidaridad planetaria y equidad intergeneracional\nJusticia y solidaridad\nRespeto a toda forma de vida"),
#|     ("enfoque", "Enfoque Orientación al bien común",
#|      "Equidad y justicia\nSolidaridad\nEmpatía\nResponsabilidad"),
#|     ("enfoque", "Enfoque Búsqueda de la Excelencia", "Flexibilidad y apertura\nSuperación personal"),
#| ]
#|
#|
#| def sembrar_curriculo(conn) -> int:
#|     """Agrega las competencias/capacidades base que falten. Devuelve cuántas competencias nuevas insertó."""
#|     cur = conn.cursor(buffered=True)
#|     nuevas = 0
#|     for (nivel, area), claves in CATALOGO.items():
#|         for orden, clave in enumerate(claves, 1):
#|             nombre, caps = COMPETENCIAS[clave]
#|             cur.execute("SELECT id FROM curriculo_competencias WHERE nivel=%s AND area=%s AND nombre=%s",
#|                         (nivel, area, nombre))
#|             if cur.fetchone():
#|                 continue
#|             cur.execute("INSERT INTO curriculo_competencias (nivel, area, nombre, orden, verificado) "
#|                         "VALUES (%s, %s, %s, %s, 0)", (nivel, area, nombre, orden))
#|             cid = cur.lastrowid
#|             for j, cap in enumerate(caps, 1):
#|                 cur.execute("INSERT INTO curriculo_capacidades (competencia_id, nombre, orden) VALUES (%s, %s, %s)",
#|                             (cid, cap, j))
#|             nuevas += 1
#|     for tipo, nombre, detalle in TRANSVERSALES:
#|         cur.execute("SELECT id FROM curriculo_transversal WHERE tipo=%s AND nombre=%s", (tipo, nombre))
#|         if not cur.fetchone():
#|             cur.execute("INSERT INTO curriculo_transversal (tipo, nombre, detalle) VALUES (%s, %s, %s)",
#|                         (tipo, nombre, detalle))
#|     conn.commit()
#|     cur.close()
#|     return nuevas
#|
#|
#| # ------------------------------------------------------------------
#| # CONSULTAS
#| # ------------------------------------------------------------------
#| def areas_de(nivel):
#|     filas = fetch("SELECT area, MIN(id) AS m FROM curriculo_competencias WHERE nivel=%s GROUP BY area ORDER BY m",
#|                   (nivel,))
#|     return [f["area"] for f in filas]
#|
#|
#| def competencias_de(nivel, area):
#|     filas = fetch("SELECT id, nombre, verificado FROM curriculo_competencias "
#|                   "WHERE nivel=%s AND area=%s ORDER BY orden, id", (nivel, area))
#|     if not filas:
#|         return []
#|     ids = [f["id"] for f in filas]
#|     marcas = ",".join(["%s"] * len(ids))
#|     caps = fetch(f"SELECT competencia_id, nombre FROM curriculo_capacidades "
#|                  f"WHERE competencia_id IN ({marcas}) ORDER BY orden, id", tuple(ids))
#|     por = {}
#|     for c in caps:
#|         por.setdefault(c["competencia_id"], []).append(c["nombre"])
#|     return [{"id": f["id"], "nombre": f["nombre"], "verificado": bool(f["verificado"]),
#|              "capacidades": por.get(f["id"], [])} for f in filas]
#|
#|
#| def desempenos_de(competencia_id, grado):
#|     return fetch("SELECT id, texto FROM curriculo_desempenos WHERE competencia_id=%s AND grado=%s ORDER BY orden, id",
#|                  (competencia_id, grado))
#|
#|
#| def estado_area(nivel, area, grado):
#|     """(n competencias, n verificadas, n con desempeños para el grado)."""
#|     comps = competencias_de(nivel, area)
#|     con_des = sum(1 for c in comps if desempenos_de(c["id"], grado))
#|     return len(comps), sum(1 for c in comps if c["verificado"]), con_des
#|
#|
#| @st.cache_data(ttl=120, show_spinner=False)
#| def transversales():
#|     """(competencias transversales, enfoques) → listas de dicts con 'nombre' y 'items'."""
#|     filas = fetch("SELECT tipo, nombre, detalle FROM curriculo_transversal ORDER BY id")
#|     comps, enf = [], []
#|     for f in filas:
#|         item = {"nombre": f["nombre"], "items": [x.strip() for x in (f["detalle"] or "").split("\n") if x.strip()]}
#|         (comps if f["tipo"] == "competencia" else enf).append(item)
#|     return comps, enf
#|
#|
#| def limpiar_cache():
#|     try:
#|         transversales.clear()
#|     except Exception:
#|         pass
#|
#|
#| def contexto_curricular(nivel, area, grado, nombres):
#|     """Texto para el prompt + mapa {nombre competencia: {'comp':..., 'des': [...]}} (desempeños numerados D1..Dn)."""
#|     objetivo = {norm(n) for n in nombres}
#|     lineas, mapa = [], {}
#|     for c in competencias_de(nivel, area):
#|         if norm(c["nombre"]) not in objetivo:
#|             continue
#|         ds = desempenos_de(c["id"], grado)
#|         mapa[c["nombre"]] = {"comp": c, "des": ds}
#|         lineas.append(f"COMPETENCIA: {c['nombre']}")
#|         lineas.append("  Capacidades: " + "; ".join(c["capacidades"]))
#|         if ds:
#|             for k, d in enumerate(ds, 1):
#|                 lineas.append(f"  D{k}: {d['texto']}")
#|         else:
#|             lineas.append("  (No hay desempeños cargados: propón 2 desempeños en 'desempenos_texto'.)")
#|     return "\n".join(lineas), mapa
#|
#|
#| def buscar_competencia(nombre, mapa):
#|     """Devuelve el nombre exacto de la competencia (de 'mapa') que coincide con 'nombre', o None."""
#|     n = norm(nombre)
#|     for real in mapa:
#|         if norm(real) == n:
#|             return real
#|     for real in mapa:  # coincidencia parcial
#|         if n and (n in norm(real) or norm(real) in n):
#|             return real
#|     return None
#@@ END
#@@ MODULE repo
#| """Acceso a datos: usuarios, créditos, asignaciones (áreas del docente) y documentos."""
#| import json
#| from db import fetch, execute
#|
#| ORDEN_NIVEL = {"Inicial": 0, "Primaria": 1, "Secundaria": 2}
#|
#| COSTOS_DEFAULT = {"caracterizacion": 0, "anual": 2, "unidad": 2, "sesion": 1,
#|                   "rubrica": 1, "ficha": 1, "examen": 1, "importar": 1, "revision": 1}
#| NOMBRES_COSTO = {
#|     "caracterizacion": "Boceto de caracterización del estudiante",
#|     "anual": "Situaciones significativas (planificación anual)",
#|     "unidad": "Unidad de aprendizaje",
#|     "sesion": "Sesión de aprendizaje",
#|     "rubrica": "Rúbrica de evaluación",
#|     "ficha": "Ficha de trabajo",
#|     "examen": "Examen",
#|     "importar": "Importar unidad desde Word",
#|     "revision": "Revisión de coherencia",
#| }
#|
#|
#| # ------------------------------------------------------------------
#| # Configuración y créditos
#| # ------------------------------------------------------------------
#| def config_get(clave, defecto=None):
#|     f = fetch("SELECT valor FROM config WHERE clave=%s", (clave,), one=True)
#|     return f["valor"] if f else defecto
#|
#|
#| def config_set(clave, valor):
#|     if fetch("SELECT clave FROM config WHERE clave=%s", (clave,), one=True):
#|         execute("UPDATE config SET valor=%s WHERE clave=%s", (str(valor), clave))
#|     else:
#|         execute("INSERT INTO config (clave, valor) VALUES (%s, %s)", (clave, str(valor)))
#|
#|
#| def costo_de(accion):
#|     v = config_get(f"costo_{accion}")
#|     try:
#|         return int(v) if v is not None else COSTOS_DEFAULT.get(accion, 1)
#|     except ValueError:
#|         return COSTOS_DEFAULT.get(accion, 1)
#|
#|
#| def get_usuario(uid):
#|     return fetch("SELECT id, nombre, correo, rol, creditos, activo, colegio, colegio_id, nivel_educativo "
#|                  "FROM usuarios WHERE id=%s", (uid,), one=True)
#|
#|
#| def cobrar(uid, accion, veces=1):
#|     """Descuenta créditos (el administrador no paga). Se llama DESPUÉS de que la IA respondió bien."""
#|     u = get_usuario(uid)
#|     if not u or u["rol"] == "admin":
#|         return
#|     costo = costo_de(accion) * veces
#|     if costo > 0:
#|         execute("UPDATE usuarios SET creditos = creditos - %s WHERE id=%s AND creditos >= %s", (costo, uid, costo))
#|
#|
#| def mapa_colegios(solo_activos=True):
#|     sql = "SELECT id, nombre FROM colegios" + (" WHERE activo=1" if solo_activos else "") + " ORDER BY nombre"
#|     mapa = {0: "— Docente independiente / sin colegio —"}
#|     mapa.update({c["id"]: c["nombre"] for c in fetch(sql)})
#|     return mapa
#|
#|
#| # ------------------------------------------------------------------
#| # Asignaciones (áreas del docente)
#| # ------------------------------------------------------------------
#| def listar_asignaciones(uid):
#|     filas = fetch("SELECT * FROM asignaciones WHERE usuario_id=%s", (uid,))
#|     return sorted(filas, key=lambda a: (ORDEN_NIVEL.get(a["nivel"], 9), a["grado"], a["area"], a["seccion"] or ""))
#|
#|
#| def get_asignacion(aid):
#|     return fetch("SELECT * FROM asignaciones WHERE id=%s", (aid,), one=True)
#|
#|
#| def crear_asignacion(uid, d):
#|     nuevo, _ = execute(
#|         "INSERT INTO asignaciones (usuario_id, ciclo_escolar, institucion, director, docente, region, nivel, grado, area, seccion) "
#|         "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
#|         (uid, d["ciclo_escolar"], d["institucion"], d["director"], d["docente"], d["region"],
#|          d["nivel"], d["grado"], d["area"], d["seccion"]))
#|     return nuevo
#|
#|
#| CAMPOS_ASIG = {"institucion", "director", "docente", "region", "seccion", "caracterizacion", "ciclo_escolar"}
#|
#|
#| def actualizar_asignacion(aid, **campos):
#|     campos = {k: v for k, v in campos.items() if k in CAMPOS_ASIG}
#|     if not campos:
#|         return
#|     sets = ", ".join(f"{k}=%s" for k in campos)
#|     execute(f"UPDATE asignaciones SET {sets} WHERE id=%s", tuple(campos.values()) + (aid,))
#|
#|
#| def borrar_asignacion(aid):
#|     execute("DELETE FROM documentos WHERE asignacion_id=%s", (aid,))
#|     execute("DELETE FROM asignaciones WHERE id=%s", (aid,))
#|
#|
#| def resumen_asignacion(aid):
#|     filas = fetch("SELECT tipo, COUNT(*) AS n FROM documentos WHERE asignacion_id=%s GROUP BY tipo", (aid,))
#|     return {f["tipo"]: f["n"] for f in filas}
#|
#|
#| # ------------------------------------------------------------------
#| # Documentos
#| # ------------------------------------------------------------------
#| def contenido(doc):
#|     if not doc or not doc.get("contenido"):
#|         return {}
#|     try:
#|         return json.loads(doc["contenido"])
#|     except (TypeError, ValueError):
#|         return {}
#|
#|
#| def get_doc_by_id(did):
#|     if not did:
#|         return None
#|     return fetch("SELECT * FROM documentos WHERE id=%s", (did,), one=True)
#|
#|
#| def get_doc(aid, tipo, numero=None, padre_id=None):
#|     sql = "SELECT * FROM documentos WHERE asignacion_id=%s AND tipo=%s"
#|     params = [aid, tipo]
#|     if numero is not None:
#|         sql += " AND numero=%s"
#|         params.append(numero)
#|     if padre_id is not None:
#|         sql += " AND padre_id=%s"
#|         params.append(padre_id)
#|     sql += " ORDER BY id DESC LIMIT 1"
#|     return fetch(sql, tuple(params), one=True)
#|
#|
#| def listar_docs(aid, tipo=None, padre_id=None):
#|     sql = "SELECT * FROM documentos WHERE asignacion_id=%s"
#|     params = [aid]
#|     if tipo:
#|         sql += " AND tipo=%s"
#|         params.append(tipo)
#|     if padre_id is not None:
#|         sql += " AND padre_id=%s"
#|         params.append(padre_id)
#|     sql += " ORDER BY numero, id"
#|     return fetch(sql, tuple(params))
#|
#|
#| def guardar_doc(uid, aid, tipo, numero, titulo, data, padre_id=None, color=None, normativa=None):
#|     """Crea o actualiza un documento. Devuelve su id."""
#|     clave_num = numero if tipo in ("unidad", "sesion") else None
#|     clave_pad = padre_id if tipo in ("sesion", "rubrica", "ficha", "examen") else None
#|     existente = get_doc(aid, tipo, clave_num, clave_pad)
#|     texto = json.dumps(data, ensure_ascii=False)
#|     titulo = (titulo or "")[:255]
#|     if existente:
#|         sets, params = ["titulo=%s", "contenido=%s", "numero=%s"], [titulo, texto, numero]
#|         if color:
#|             sets.append("color=%s")
#|             params.append(color)
#|         if normativa:
#|             sets.append("normativa_usada=%s")
#|             params.append(normativa[:255])
#|         if padre_id is not None:
#|             sets.append("padre_id=%s")
#|             params.append(padre_id)
#|         execute(f"UPDATE documentos SET {', '.join(sets)} WHERE id=%s", tuple(params) + (existente["id"],))
#|         return existente["id"]
#|     nuevo, _ = execute(
#|         "INSERT INTO documentos (usuario_id, asignacion_id, tipo, padre_id, numero, titulo, contenido, color, normativa_usada) "
#|         "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
#|         (uid, aid, tipo, padre_id, numero, titulo, texto, color or "1F3B8F", (normativa or "")[:255]))
#|     return nuevo
#|
#|
#| def cambiar_color(did, color):
#|     execute("UPDATE documentos SET color=%s WHERE id=%s", (color, did))
#|
#|
#| def borrar_doc(did):
#|     """Borra un documento y todo lo que depende de él."""
#|     for hijo in fetch("SELECT id FROM documentos WHERE padre_id=%s", (did,)):
#|         borrar_doc(hijo["id"])
#|     execute("DELETE FROM documentos WHERE id=%s", (did,))
#|
#|
#| def crear_sesiones_desde_secuencia(uid, asig, udoc):
#|     """Crea una sesión vacía por cada fila de la secuencia de la unidad. Devuelve cuántas creó."""
#|     d = contenido(udoc)
#|     creadas = 0
#|     for i, fila in enumerate(d.get("secuencia", []), 1):
#|         titulo = fila.get("titulo") or f"Sesión {i}"
#|         if get_doc(asig["id"], "sesion", numero=i, padre_id=udoc["id"]):
#|             continue
#|         guardar_doc(uid, asig["id"], "sesion", i, f"Sesión {i}: {titulo}",
#|                     {"numero": i, "titulo": titulo, "unidad_numero": udoc["numero"], "semana": fila.get("semana"),
#|                      "competencias_sugeridas": [fila["competencia"]] if fila.get("competencia") else []},
#|                     padre_id=udoc["id"])
#|         creadas += 1
#|     return creadas
#@@ END
#@@ MODULE render
#| """Documentos oficiales: se arman como "bloques" y se dibujan igual en Word y en la vista previa."""
#| import io
#| import html as _html
#| from typing import Optional
#|
#| from docx import Document
#| from docx.enum.section import WD_ORIENT
#| from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
#| from docx.oxml import OxmlElement
#| from docx.oxml.ns import qn
#| from docx.shared import Cm, Pt, RGBColor
#|
#| from util import s
#|
#| COLORES = {"Azul": "1F3B8F", "Morado": "6D28D9", "Verde": "15803D", "Rojo": "B91C1C",
#|            "Marrón": "7C4A2D", "Naranja": "C2410C", "Gris": "475569"}
#| ICONO_COLOR = {"Azul": "🔵", "Morado": "🟣", "Verde": "🟢", "Rojo": "🔴", "Marrón": "🟤", "Naranja": "🟠", "Gris": "⚪"}
#| COLOR_DEFECTO = "1F3B8F"
#|
#|
#| def _bul(items) -> str:
#|     """Lista → texto con viñetas (una por línea)."""
#|     if not items:
#|         return ""
#|     if isinstance(items, str):
#|         items = [x for x in items.split("\n") if x.strip()]
#|     return "\n".join("• " + s(x) for x in items if s(x))
#|
#|
#| def _aclarar(hex_color: str, factor: float = 0.88) -> str:
#|     r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
#|     r, g, b = (int(c + (255 - c) * factor) for c in (r, g, b))
#|     return f"{r:02X}{g:02X}{b:02X}"
#|
#|
#| # ------------------------------------------------------------------
#| # CONSTRUCTORES DE BLOQUES
#| # Bloques: ("h", titulo) ("sec", texto) ("kv", [(k, v)], ncols) ("tabla", encabezados, filas)
#| #          ("p", texto) ("sub", texto) ("ul", [items]) ("salto",)
#| # ------------------------------------------------------------------
#| def _kv_datos(asig, extra=None):
#|     pares = [("Institución educativa", asig.get("institucion")), ("Director(a)", asig.get("director")),
#|              ("Docente", asig.get("docente")), ("Región", asig.get("region")),
#|              ("Nivel", asig.get("nivel")), ("Grado / edad", asig.get("grado")),
#|              ("Área curricular", asig.get("area")), ("Sección", asig.get("seccion")),
#|              ("Ciclo escolar", asig.get("ciclo_escolar"))]
#|     return pares + list(extra or [])
#|
#|
#| def _bloques_transversales(trans, enfoques_sel=None):
#|     comps_t, enfoques_db = trans
#|     b = [("sec", "COMPETENCIAS TRANSVERSALES"),
#|          ("tabla", ["Competencia transversal", "Capacidades"],
#|           [[c["nombre"], _bul(c["items"])] for c in comps_t])]
#|     if enfoques_sel:
#|         b += [("sec", "ENFOQUES TRANSVERSALES"),
#|               ("tabla", ["Enfoque transversal", "Valores", "Acciones observables"],
#|                [[e.get("enfoque"), e.get("valores"), e.get("acciones")] for e in enfoques_sel])]
#|     else:
#|         b += [("sec", "ENFOQUES TRANSVERSALES"),
#|               ("tabla", ["Enfoque transversal", "Valores"],
#|                [[e["nombre"], _bul(e["items"])] for e in enfoques_db])]
#|     return b
#|
#|
#| def bloques_anual(asig, d, comps, trans):
#|     b = [("h", f"PLANIFICACIÓN ANUAL {asig.get('ciclo_escolar', '')} — {asig.get('area', '')}"),
#|          ("sec", "I. DATOS INFORMATIVOS"), ("kv", _kv_datos(asig), 2),
#|          ("sec", "II. CARACTERIZACIÓN Y CONTEXTO DEL ESTUDIANTE"), ("p", asig.get("caracterizacion") or ""),
#|          ("sec", "III. COMPETENCIAS Y CAPACIDADES DEL ÁREA"),
#|          ("tabla", ["Competencia", "Capacidades"], [[c["nombre"], _bul(c["capacidades"])] for c in comps]),
#|          ("sec", "IV. SITUACIONES SIGNIFICATIVAS Y UNIDADES DE APRENDIZAJE")]
#|     filas = [[f"Unidad {u.get('numero')}", u.get("titulo"), u.get("problema"), u.get("situacion"), u.get("valores"),
#|               _bul(u.get("competencias")), _bul(u.get("capacidades")), f"{u.get('semanas', '')} sem."]
#|              for u in d.get("unidades", [])]
#|     b.append(("tabla", ["Unidad", "Título", "Problema identificado", "Situación significativa",
#|                         "Valores observables", "Competencias", "Capacidades a trabajar", "Duración"], filas))
#|     return b + _bloques_transversales(trans)
#|
#|
#| def bloques_unidad(asig, d, trans):
#|     b = [("h", f"UNIDAD DE APRENDIZAJE N.° {d.get('numero', '')}: {d.get('titulo', '')}"),
#|          ("sec", "I. DATOS INFORMATIVOS"),
#|          ("kv", _kv_datos(asig, [("Unidad", d.get("numero")), ("Duración", f"{d.get('semanas', '')} semanas")]), 2),
#|          ("sec", "II. SITUACIÓN SIGNIFICATIVA"), ("p", d.get("situacion")),
#|          ("sec", "III. PRODUCTO DE APRENDIZAJE")]
#|     pr = d.get("producto") or {}
#|     b.append(("tabla", ["Evidencia", "Criterios de evaluación", "Relación con otras áreas"],
#|               [[pr.get("evidencia"), pr.get("criterios"), pr.get("relacion")]]))
#|     b.append(("sec", "IV. SECUENCIA DE LA UNIDAD"))
#|     b.append(("tabla", ["Semana", "Sesión", "Título / pregunta retadora", "Competencia"],
#|               [[f"Semana {f.get('semana')}", f"Sesión {i}", f.get("titulo"), f.get("competencia")]
#|                for i, f in enumerate(d.get("secuencia", []), 1)]))
#|     b.append(("sec", "V. PROPÓSITOS DE APRENDIZAJE"))
#|     filas = []
#|     for p in d.get("propositos", []):
#|         des = _bul(p.get("desempenos")) + ("\n(Desempeños por verificar con el Programa Curricular)" if p.get("por_verificar") else "")
#|         filas.append([p.get("competencia"), _bul(p.get("capacidades")), des, p.get("proposito"),
#|                       p.get("campo_tematico"), p.get("evidencia"), p.get("instrumento")])
#|     b.append(("tabla", ["Competencia", "Capacidades", "Desempeños", "Propósito", "Campo temático",
#|                         "Evidencia", "Instrumento"], filas))
#|     return b + _bloques_transversales(trans, d.get("enfoques") or None)
#|
#|
#| def bloques_sesion(asig, udata, d, trans):
#|     dur = sum(int(d.get(k, {}).get("minutos") or 0) for k in ("inicio", "desarrollo", "cierre"))
#|     b = [("h", f"SESIÓN DE APRENDIZAJE N.° {d.get('numero', '')}: {d.get('titulo', '')}"),
#|          ("sec", "I. DATOS INFORMATIVOS"),
#|          ("kv", _kv_datos(asig, [("Unidad", f"{udata.get('numero', '')}: {udata.get('titulo', '')}"),
#|                                  ("Duración", f"{d.get('duracion') or dur} minutos")]), 2),
#|          ("sec", "II. PROPÓSITO DE APRENDIZAJE"), ("p", d.get("proposito")),
#|          ("tabla", ["Competencia", "Capacidades", "Desempeños", "Criterios de evaluación"],
#|           [[c.get("competencia"), _bul(c.get("capacidades")),
#|             _bul(c.get("desempenos")) + ("\n(Por verificar)" if c.get("por_verificar") else ""),
#|             _bul(c.get("criterios"))] for c in d.get("competencias", [])]),
#|          ("sec", "III. EVALUACIÓN DE LOS APRENDIZAJES"),
#|          ("tabla", ["Competencia", "Evidencia de aprendizaje", "Instrumento de evaluación"],
#|           [[c.get("competencia"), c.get("evidencia"), c.get("instrumento")] for c in d.get("competencias", [])])]
#|     b += _bloques_transversales(trans, d.get("enfoques") or None)
#|     b.append(("sec", "IV. SECUENCIA DIDÁCTICA"))
#|     b.append(("tabla", ["Momento", "Actividades", "Tiempo"],
#|               [[nombre, (d.get(k) or {}).get("actividades"), f"{(d.get(k) or {}).get('minutos', '')} min"]
#|                for nombre, k in (("INICIO", "inicio"), ("DESARROLLO", "desarrollo"), ("CIERRE", "cierre"))]))
#|     b += [("sec", "V. MATERIALES Y RECURSOS"), ("ul", d.get("materiales") or []),
#|           ("sec", "VI. REFLEXIÓN SOBRE EL APRENDIZAJE"), ("ul", d.get("reflexion") or [])]
#|     return b
#|
#|
#| def bloques_rubrica(asig, sdata, d):
#|     return [("h", f"RÚBRICA DE EVALUACIÓN — {sdata.get('titulo', '')}"),
#|             ("kv", [("Institución educativa", asig.get("institucion")), ("Docente", asig.get("docente")),
#|                     ("Área", asig.get("area")), ("Grado y sección", f"{asig.get('grado', '')} {asig.get('seccion') or ''}"),
#|                     ("Competencia(s)", ", ".join(c.get("competencia", "") for c in sdata.get("competencias", [])))], 2),
#|             ("sec", "CRITERIOS Y NIVELES DE LOGRO"),
#|             ("tabla", ["Criterio", "AD · Logro destacado", "A · Logro esperado", "B · En proceso", "C · En inicio"],
#|              [[r.get("criterio"), r.get("AD"), r.get("A"), r.get("B"), r.get("C")] for r in d.get("criterios", [])])]
#|
#|
#| def bloques_ficha(asig, sdata, d):
#|     b = [("h", (d.get("titulo") or f"FICHA DE TRABAJO — {sdata.get('titulo', '')}").upper()),
#|          ("kv", [("Nombres y apellidos", ""), ("Fecha", ""), ("Grado y sección", f"{asig.get('grado', '')} {asig.get('seccion') or ''}"),
#|                  ("Área", asig.get("area"))], 2),
#|          ("sec", "INDICACIONES"), ("p", d.get("instrucciones")), ("sec", "ACTIVIDADES")]
#|     for a in d.get("actividades", []):
#|         b.append(("p", f"{a.get('numero')}. {s(a.get('consigna'))}"))
#|         b.append(("p", "Respuesta: ______________________________________________"))
#|     b += [("salto",), ("sec", "SOLUCIONARIO (SOLO PARA EL DOCENTE)"),
#|           ("tabla", ["N.°", "Respuesta esperada"], [[a.get("numero"), a.get("respuesta")] for a in d.get("actividades", [])])]
#|     return b
#|
#|
#| def bloques_examen(asig, sdata, d):
#|     def _num(v):
#|         try:
#|             return float(str(v).replace(",", "."))
#|         except ValueError:
#|             return 0.0
#|     total = sum(_num(p.get("puntaje")) for p in d.get("preguntas", []))
#|     b = [("h", (d.get("titulo") or f"EXAMEN — {sdata.get('titulo', '')}").upper()),
#|          ("kv", [("Nombres y apellidos", ""), ("Fecha", ""), ("Grado y sección", f"{asig.get('grado', '')} {asig.get('seccion') or ''}"),
#|                  ("Puntaje total", f"{total:g} puntos")], 2),
#|          ("sec", "INDICACIONES"), ("p", d.get("instrucciones")), ("sec", "PREGUNTAS")]
#|     for p in d.get("preguntas", []):
#|         b.append(("sub", f"{p.get('numero')}. {s(p.get('enunciado'))}  ({p.get('puntaje')} pts)"))
#|         ops = p.get("opciones") or []
#|         if ops:
#|             b.append(("ul", ops))
#|         elif p.get("tipo") == "desarrollo":
#|             b.append(("p", "______________________________________________________________"))
#|     b += [("salto",), ("sec", "CLAVES DE RESPUESTA (SOLO PARA EL DOCENTE)"),
#|           ("tabla", ["N.°", "Respuesta correcta", "Puntaje"],
#|            [[p.get("numero"), p.get("respuesta"), p.get("puntaje")] for p in d.get("preguntas", [])])]
#|     return b
#|
#|
#| # ------------------------------------------------------------------
#| # WORD
#| # ------------------------------------------------------------------
#| def _sombrear(celda, hex_color):
#|     tc_pr = celda._tc.get_or_add_tcPr()
#|     shd = OxmlElement("w:shd")
#|     shd.set(qn("w:val"), "clear")
#|     shd.set(qn("w:color"), "auto")
#|     shd.set(qn("w:fill"), hex_color)
#|     tc_pr.append(shd)
#|
#|
#| def _escribir(celda, texto, negrita=False, color_texto=None, tam=9, centrado=False):
#|     celda.text = ""
#|     p = celda.paragraphs[0]
#|     for i, linea in enumerate(s(texto).split("\n")):
#|         if i > 0:
#|             p = celda.add_paragraph()
#|         run = p.add_run(linea)
#|         run.bold = negrita
#|         run.font.size = Pt(tam)
#|         if color_texto:
#|             run.font.color.rgb = RGBColor.from_string(color_texto)
#|         p.paragraph_format.space_after = Pt(1)
#|         if centrado:
#|             p.alignment = WD_ALIGN_PARAGRAPH.CENTER
#|
#|
#| def a_docx(bloques, color=COLOR_DEFECTO, pie: Optional[str] = None, horizontal=False) -> bytes:
#|     color = (color or COLOR_DEFECTO).lstrip("#")
#|     claro = _aclarar(color)
#|     doc = Document()
#|     sec = doc.sections[0]
#|     sec.page_width, sec.page_height = Cm(21), Cm(29.7)
#|     if horizontal:
#|         sec.orientation = WD_ORIENT.LANDSCAPE
#|         sec.page_width, sec.page_height = sec.page_height, sec.page_width
#|     for lado in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
#|         setattr(sec, lado, Cm(1.6))
#|     normal = doc.styles["Normal"]
#|     normal.font.name = "Arial"
#|     normal.font.size = Pt(10)
#|
#|     for blq in bloques:
#|         tipo = blq[0]
#|         if tipo == "h":
#|             p = doc.add_paragraph()
#|             p.alignment = WD_ALIGN_PARAGRAPH.CENTER
#|             r = p.add_run(s(blq[1]))
#|             r.bold = True
#|             r.font.size = Pt(14)
#|             r.font.color.rgb = RGBColor.from_string(color)
#|         elif tipo == "sec":
#|             t = doc.add_table(rows=1, cols=1)
#|             t.style = "Table Grid"
#|             _sombrear(t.rows[0].cells[0], color)
#|             _escribir(t.rows[0].cells[0], blq[1], negrita=True, color_texto="FFFFFF", tam=10)
#|         elif tipo == "kv":
#|             pares, ncols = blq[1], blq[2]
#|             filas = (len(pares) + ncols - 1) // ncols
#|             t = doc.add_table(rows=filas, cols=ncols * 2)
#|             t.style = "Table Grid"
#|             for idx, (k, v) in enumerate(pares):
#|                 fila, col = divmod(idx, ncols)
#|                 ck, cv = t.rows[fila].cells[col * 2], t.rows[fila].cells[col * 2 + 1]
#|                 _sombrear(ck, claro)
#|                 _escribir(ck, k, negrita=True)
#|                 _escribir(cv, v)
#|         elif tipo == "tabla":
#|             enc, filas = blq[1], blq[2]
#|             t = doc.add_table(rows=1, cols=len(enc))
#|             t.style = "Table Grid"
#|             for i, h in enumerate(enc):
#|                 _sombrear(t.rows[0].cells[i], color)
#|                 _escribir(t.rows[0].cells[i], h, negrita=True, color_texto="FFFFFF", centrado=True)
#|             for fila in filas:
#|                 celdas = t.add_row().cells
#|                 for i in range(len(enc)):
#|                     _escribir(celdas[i], fila[i] if i < len(fila) else "")
#|         elif tipo == "p":
#|             if s(blq[1]):
#|                 doc.add_paragraph(s(blq[1]))
#|         elif tipo == "sub":
#|             p = doc.add_paragraph()
#|             p.add_run(s(blq[1])).bold = True
#|         elif tipo == "ul":
#|             for item in blq[1]:
#|                 if s(item):
#|                     doc.add_paragraph(s(item), style="List Bullet")
#|         elif tipo == "salto":
#|             doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
#|         if tipo in ("sec", "kv", "tabla"):
#|             doc.add_paragraph().paragraph_format.space_after = Pt(2)
#|
#|     p = doc.add_paragraph()
#|     r = p.add_run("Normativa utilizada: " + (pie or "RM N.° 501-2025-MINEDU") +
#|                   ". Documento generado con EduPerú IA; revísalo y ajústalo a tu realidad antes de usarlo.")
#|     r.italic = True
#|     r.font.size = Pt(8)
#|     buf = io.BytesIO()
#|     doc.save(buf)
#|     return buf.getvalue()
#|
#|
#| def texto_a_docx(titulo: str, contenido: str, pie: Optional[str] = None) -> bytes:
#|     """Word sencillo para documentos antiguos (texto con formato Markdown)."""
#|     doc = Document()
#|     doc.add_heading(titulo, level=0)
#|     for linea in contenido.splitlines():
#|         l = linea.strip().replace("**", "")
#|         if not l:
#|             continue
#|         if l.startswith("### "):
#|             doc.add_heading(l[4:], level=3)
#|         elif l.startswith("## "):
#|             doc.add_heading(l[3:], level=2)
#|         elif l.startswith("# "):
#|             doc.add_heading(l[2:], level=1)
#|         elif l.startswith(("- ", "* ")):
#|             doc.add_paragraph(l[2:], style="List Bullet")
#|         else:
#|             doc.add_paragraph(l)
#|     if pie:
#|         doc.add_paragraph().add_run(f"Normativa utilizada: {pie}").italic = True
#|     buf = io.BytesIO()
#|     doc.save(buf)
#|     return buf.getvalue()
#|
#|
#| # ------------------------------------------------------------------
#| # VISTA PREVIA (HTML)
#| # ------------------------------------------------------------------
#| _CSS = """<style>
#| body{font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#222;margin:0;padding:14px;background:#fff}
#| h1{text-align:center;font-size:17px;color:#__C__;margin:6px 0 14px}
#| .sec{background:#__C__;color:#fff;font-weight:bold;padding:6px 10px;margin:14px 0 6px;border-radius:3px;font-size:13px}
#| table{border-collapse:collapse;width:100%;margin-bottom:8px;table-layout:auto}
#| th{background:#__C__;color:#fff;padding:5px;border:1px solid #__C__;font-size:12px}
#| td{border:1px solid #bbb;padding:5px;vertical-align:top;font-size:12px}
#| td.k{background:#__L__;font-weight:bold;width:16%}
#| p{margin:4px 0;line-height:1.45} ul{margin:4px 0 8px 18px;padding:0}
#| .sub{font-weight:bold;margin:8px 0 2px}.salto{border-top:2px dashed #bbb;margin:16px 0}
#| .pie{font-size:11px;color:#666;font-style:italic;margin-top:14px}
#| </style>"""
#|
#|
#| def _h(texto) -> str:
#|     return _html.escape(s(texto)).replace("\n", "<br>")
#|
#|
#| def a_html(bloques, color=COLOR_DEFECTO, pie: Optional[str] = None) -> str:
#|     color = (color or COLOR_DEFECTO).lstrip("#")
#|     out = [_CSS.replace("__C__", color).replace("__L__", _aclarar(color))]
#|     for blq in bloques:
#|         tipo = blq[0]
#|         if tipo == "h":
#|             out.append(f"<h1>{_h(blq[1])}</h1>")
#|         elif tipo == "sec":
#|             out.append(f"<div class='sec'>{_h(blq[1])}</div>")
#|         elif tipo == "kv":
#|             pares, ncols = blq[1], blq[2]
#|             out.append("<table>")
#|             for i in range(0, len(pares), ncols):
#|                 out.append("<tr>")
#|                 for k, v in pares[i:i + ncols]:
#|                     out.append(f"<td class='k'>{_h(k)}</td><td>{_h(v)}</td>")
#|                 out.append("</tr>")
#|             out.append("</table>")
#|         elif tipo == "tabla":
#|             enc, filas = blq[1], blq[2]
#|             out.append("<table><tr>" + "".join(f"<th>{_h(e)}</th>" for e in enc) + "</tr>")
#|             for fila in filas:
#|                 out.append("<tr>" + "".join(f"<td>{_h(fila[i] if i < len(fila) else '')}</td>"
#|                                            for i in range(len(enc))) + "</tr>")
#|             out.append("</table>")
#|         elif tipo == "p":
#|             if s(blq[1]):
#|                 out.append(f"<p>{_h(blq[1])}</p>")
#|         elif tipo == "sub":
#|             out.append(f"<div class='sub'>{_h(blq[1])}</div>")
#|         elif tipo == "ul":
#|             out.append("<ul>" + "".join(f"<li>{_h(i)}</li>" for i in blq[1] if s(i)) + "</ul>")
#|         elif tipo == "salto":
#|             out.append("<div class='salto'></div>")
#|     out.append(f"<div class='pie'>Normativa utilizada: {_h(pie or 'RM N.° 501-2025-MINEDU')}</div>")
#|     return "".join(out)
#@@ END
#@@ MODULE exportar
#| """Convierte un documento guardado en bloques listos para vista previa y Word."""
#| from curriculo import competencias_de, transversales
#| from repo import contenido, get_asignacion, get_doc_by_id
#| from render import bloques_anual, bloques_unidad, bloques_sesion, bloques_rubrica, bloques_ficha, bloques_examen
#| from util import norm, slug
#|
#|
#| def bloques_de(doc):
#|     """Devuelve (bloques, horizontal, nombre_de_archivo)."""
#|     asig = get_asignacion(doc["asignacion_id"]) or {}
#|     d = contenido(doc)
#|     tipo = doc["tipo"]
#|     trans = transversales()
#|     base = slug(f"{asig.get('area', '')} {asig.get('grado', '')}")
#|     if tipo == "anual":
#|         elegidas = {norm(n) for n in d.get("competencias_area", [])}
#|         comps = [c for c in competencias_de(asig.get("nivel"), asig.get("area")) if norm(c["nombre"]) in elegidas]
#|         return bloques_anual(asig, d, comps, trans), True, f"planificacion_anual_{base}.docx"
#|     if tipo == "unidad":
#|         return bloques_unidad(asig, d, trans), True, f"unidad_{doc.get('numero', 1)}_{base}.docx"
#|     padre = get_doc_by_id(doc.get("padre_id")) or {}
#|     pdata = contenido(padre) if padre else {}
#|     if tipo == "sesion":
#|         return bloques_sesion(asig, pdata, d, trans), False, f"sesion_{doc.get('numero', 1)}_{base}.docx"
#|     if tipo == "rubrica":
#|         return bloques_rubrica(asig, pdata, d), True, f"rubrica_{base}.docx"
#|     if tipo == "ficha":
#|         return bloques_ficha(asig, pdata, d), False, f"ficha_{base}.docx"
#|     return bloques_examen(asig, pdata, d), False, f"examen_{base}.docx"
#@@ END
#@@ MODULE ia
#| """Proveedores de IA (OpenRouter primero, Gemini de respaldo) y utilidades para pedir JSON."""
#| import json
#| import re
#| import time
#| import requests
#| import streamlit as st
#|
#|
#| def _post(url, **kw):
#|     """POST con 3 intentos si el proveedor responde 429/503; el error incluye el mensaje real del proveedor."""
#|     r = None
#|     for intento in range(3):
#|         r = requests.post(url, **kw)
#|         if r.status_code in (429, 503) and intento < 2:
#|             time.sleep(4 * (intento + 1))
#|             continue
#|         break
#|     if r.status_code >= 400:
#|         try:
#|             detalle = r.json().get("error", {})
#|             detalle = detalle.get("message", r.text) if isinstance(detalle, dict) else str(detalle)
#|         except ValueError:
#|             detalle = r.text
#|         raise RuntimeError(f"{r.status_code}: {str(detalle)[:250]}")
#|     return r
#|
#|
#| def llamar_openrouter(prompt: str) -> str:
#|     cfg = st.secrets["openrouter"]
#|     r = _post("https://openrouter.ai/api/v1/chat/completions",
#|               headers={"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"},
#|               json={"model": cfg.get("model", "openai/gpt-4o-mini"),
#|                     "messages": [{"role": "user", "content": prompt}], "max_tokens": 6000},
#|               timeout=120)
#|     return r.json()["choices"][0]["message"]["content"]
#|
#|
#| def llamar_gemini(prompt: str) -> str:
#|     """Gemini por su API REST (no depende de ninguna librería). El modelo se puede cambiar en Secrets: [gemini] model."""
#|     cfg = st.secrets["gemini"]
#|     modelo = cfg.get("model", "gemini-3.8-flash")
#|     r = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
#|               params={"key": cfg["api_key"]},
#|               json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": 8000}},
#|               timeout=120)
#|     partes = r.json()["candidates"][0]["content"]["parts"]
#|     return "".join(p.get("text", "") for p in partes)
#|
#|
#| def generar_texto(prompt: str):
#|     """Devuelve (texto, proveedor). Lanza RuntimeError si fallan todos los proveedores."""
#|     errores = []
#|     if "openrouter" in st.secrets:
#|         try:
#|             return llamar_openrouter(prompt), "OpenRouter"
#|         except Exception as e:
#|             errores.append(f"OpenRouter: {e}")
#|     if "gemini" in st.secrets:
#|         try:
#|             return llamar_gemini(prompt), "Gemini"
#|         except Exception as e:
#|             errores.append(f"Gemini: {e}")
#|     raise RuntimeError(" | ".join(errores) or "No hay proveedores de IA configurados en Secrets.")
#|
#|
#| def parse_json(texto: str):
#|     """Extrae el primer objeto/arreglo JSON de un texto (tolera ``` y texto alrededor). None si no puede."""
#|     t = (texto or "").strip()
#|     t = re.sub(r"^```(?:json)?\s*", "", t)
#|     t = re.sub(r"\s*```$", "", t)
#|     candidatos = []
#|     for ini, fin in (("{", "}"), ("[", "]")):
#|         i, j = t.find(ini), t.rfind(fin)
#|         if i != -1 and j > i:
#|             candidatos.append((i, t[i:j + 1]))
#|     for _, trozo in sorted(candidatos):
#|         try:
#|             return json.loads(trozo)
#|         except json.JSONDecodeError:
#|             continue
#|     return None
#|
#|
#| SUFIJO_JSON = ("\n\nResponde ÚNICAMENTE con JSON válido (sin ```, sin comentarios, sin texto antes ni después). "
#|                "Usa comillas dobles y escribe los saltos de línea dentro de los textos como \\n.")
#|
#|
#| def pedir_json(prompt: str):
#|     """Devuelve (datos, proveedor). Reintenta una vez si la IA no devuelve JSON válido."""
#|     texto, prov = generar_texto(prompt + SUFIJO_JSON)
#|     datos = parse_json(texto)
#|     if datos is None:
#|         texto, prov = generar_texto(prompt + SUFIJO_JSON +
#|                                     "\n\nIMPORTANTE: tu respuesta anterior no era JSON válido. Devuelve solo el JSON completo.")
#|         datos = parse_json(texto)
#|     if datos is None:
#|         raise RuntimeError("La IA no devolvió un formato válido. Intenta de nuevo.")
#|     return datos, prov
#|
#|
#| def preambulo() -> str:
#|     """Instrucciones comunes + disposiciones normativas aprobadas por el administrador."""
#|     from normativa import normativa_vigente
#|     try:
#|         ctx, _ = normativa_vigente()
#|     except Exception:
#|         ctx = ""
#|     base = ("Eres un especialista en pedagogía y en el Currículo Nacional de la Educación Básica (CNEB) del Perú, "
#|             "y trabajas alineado a la RM N.° 501-2025-MINEDU. Escribes en español claro, práctico y contextualizado, "
#|             "para docentes peruanos. NO inventes competencias, capacidades ni desempeños oficiales: usa solo los que "
#|             "se te entregan, con su redacción exacta.")
#|     if ctx:
#|         base += ("\n\nDisposiciones normativas verificadas por el administrador (úsalas como referencia sin contradecir el CNEB):\n"
#|                  + ctx)
#|     return base
#@@ END
#@@ MODULE normativa
#| """Monitor normativo del MINEDU: detecta cambios en fuentes oficiales; el administrador aprueba."""
#| import hashlib
#| from typing import Optional
#| import requests
#| from bs4 import BeautifulSoup
#| from db import fetch as db_fetch, execute as db_execute
#| from ia import generar_texto
#|
#| UA = {"User-Agent": "Mozilla/5.0 (compatible; EduPeruIA-MonitorNormativo/1.0)"}
#|
#|
#| def html_a_texto(html: str) -> str:
#|     soup = BeautifulSoup(html, "html.parser")
#|     for t in soup(["script", "style", "noscript", "header", "footer", "nav", "form"]):
#|         t.decompose()
#|     return " ".join(soup.get_text(" ").split())
#|
#|
#| def resumir_cambios(nombre: str, nuevo: str, anterior: Optional[str]) -> str:
#|     if anterior:
#|         prompt = f"""Compara dos capturas de texto de la fuente oficial «{nombre}» (MINEDU, Perú).
#| Indica SOLO los cambios relevantes para docentes y colegios y clasifícalos en:
#| curricular / pedagógico-normativo / administrativo.
#| Si no hay cambios sustantivos (solo ruido de la página), responde exactamente: "Sin cambios sustantivos (posible ruido de la página)".
#| No inventes nada que no esté en los textos.
#|
#| === VERSIÓN ANTERIOR ===
#| {anterior[:12000]}
#|
#| === VERSIÓN NUEVA ===
#| {nuevo[:12000]}"""
#|     else:
#|         prompt = f"""Resume en español la fuente oficial «{nombre}» (MINEDU, Perú) a partir de este texto.
#| Indica: qué norma o documento es, vigencia y los puntos clave aplicables a la planificación docente.
#| No inventes nada que no esté en el texto.
#|
#| {nuevo[:15000]}"""
#|     try:
#|         texto, _ = generar_texto(prompt)
#|         return texto
#|     except Exception as e:
#|         return f"(No se pudo generar el resumen con IA: {e})"
#|
#|
#| def revisar_fuente(f: dict):
#|     """Devuelve (estado, mensaje): estado = nueva | sin_cambios | error."""
#|     try:
#|         r = requests.get(f["url"], headers=UA, timeout=30)
#|         r.raise_for_status()
#|         if "pdf" in r.headers.get("content-type", "").lower():
#|             return "error", "La fuente es un PDF (por ahora solo se leen páginas HTML)."
#|         texto = html_a_texto(r.text)[:200000]
#|         if len(texto) < 200:
#|             return "error", "La página devolvió muy poco texto (puede requerir JavaScript)."
#|     except Exception as e:
#|         return "error", f"No se pudo leer la fuente: {e}"
#|
#|     h = hashlib.sha256(texto.encode()).hexdigest()
#|     ultimo = db_fetch(
#|         "SELECT hash_contenido, contenido FROM normativa_versiones WHERE fuente_id=%s ORDER BY id DESC LIMIT 1",
#|         (f["id"],), one=True,
#|     )
#|     db_execute("UPDATE normativa_fuentes SET ultima_revision=NOW() WHERE id=%s", (f["id"],))
#|     if ultimo and ultimo["hash_contenido"] == h:
#|         return "sin_cambios", "Sin cambios desde la última captura."
#|
#|     resumen = resumir_cambios(f["nombre"], texto, ultimo["contenido"] if ultimo else None)
#|     db_execute(
#|         "INSERT INTO normativa_versiones (fuente_id, hash_contenido, contenido, resumen_cambios) VALUES (%s,%s,%s,%s)",
#|         (f["id"], h, texto, resumen),
#|     )
#|     return "nueva", "Nueva versión detectada, pendiente de aprobación."
#|
#|
#| def normativa_vigente():
#|     """(contexto para el prompt, etiqueta para el documento)."""
#|     filas = db_fetch(
#|         "SELECT f.nombre, v.resumen_cambios, v.aprobado_en FROM normativa_versiones v "
#|         "JOIN normativa_fuentes f ON f.id = v.fuente_id "
#|         "WHERE v.estado='aprobada' ORDER BY v.aprobado_en DESC LIMIT 5"
#|     )
#|     if not filas:
#|         return "", "RM N.° 501-2025-MINEDU"
#|     ctx = "\n\n".join(
#|         f"[{f['nombre']} · aprobada {f['aprobado_en']:%d/%m/%Y}]\n{f['resumen_cambios']}" for f in filas
#|     )[:4000]
#|     etiqueta = (f"RM N.° 501-2025-MINEDU + {len(filas)} actualización(es) verificada(s) "
#|                 f"(última {filas[0]['aprobado_en']:%d/%m/%Y})")
#|     return ctx, etiqueta[:255]
#@@ END
#@@ MODULE auth
#| """Inicio de sesión, registro y contraseñas."""
#| import hashlib
#| import bcrypt
#| import mysql.connector
#| import streamlit as st
#|
#| from db import fetch, execute
#| from repo import mapa_colegios
#|
#|
#| def hash_password(password: str) -> str:
#|     return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
#|
#|
#| def verify_password(password: str, stored_hash: str) -> bool:
#|     if stored_hash.startswith("$2"):
#|         try:
#|             return bcrypt.checkpw(password.encode(), stored_hash.encode())
#|         except ValueError:
#|             return False
#|     return hashlib.sha256(password.encode()).hexdigest() == stored_hash
#|
#|
#| def admin_correo() -> str:
#|     try:
#|         return str(st.secrets["admin"].get("correo", "")).strip().lower()
#|     except Exception:
#|         return ""
#|
#|
#| def pantalla_login():
#|     _, centro, _ = st.columns([1, 2, 1])
#|     with centro:
#|         st.markdown("<h1 style='text-align:center;'>✏️ EduPerú IA</h1>", unsafe_allow_html=True)
#|         st.markdown("<p style='text-align:center;color:#666;'>Tus documentos pedagógicos en minutos, alineados al "
#|                     "<b>CNEB y la RM N.° 501-2025-MINEDU</b></p>", unsafe_allow_html=True)
#|         tab_login, tab_reg = st.tabs(["🔑 Iniciar sesión", "📝 Crear cuenta"])
#|
#|         with tab_login:
#|             with st.form("login_form"):
#|                 correo = st.text_input("Correo electrónico", key="l_email")
#|                 clave = st.text_input("Contraseña", type="password", key="l_pass")
#|                 enviar = st.form_submit_button("Ingresar", type="primary", use_container_width=True)
#|             if enviar:
#|                 if not (correo and clave):
#|                     st.warning("Completa todos los campos.")
#|                 else:
#|                     try:
#|                         u = fetch("SELECT * FROM usuarios WHERE correo=%s", (correo.strip().lower(),), one=True)
#|                         if u and verify_password(clave, u["password_hash"]):
#|                             if u.get("activo") == 0:
#|                                 st.error("Tu cuenta está desactivada. Contacta al administrador.")
#|                             else:
#|                                 if not u["password_hash"].startswith("$2"):
#|                                     execute("UPDATE usuarios SET password_hash=%s WHERE id=%s",
#|                                             (hash_password(clave), u["id"]))
#|                                 st.session_state.logged_in = True
#|                                 st.session_state.user_id = u["id"]
#|                                 st.rerun()
#|                         else:
#|                             st.error("Correo o contraseña incorrectos.")
#|                     except Exception:
#|                         st.error("No se pudo ingresar. Intenta de nuevo en unos minutos.")
#|
#|         with tab_reg:
#|             colegios = mapa_colegios(solo_activos=True)
#|             with st.form("register_form"):
#|                 nombre = st.text_input("Nombre completo", key="r_nombre")
#|                 correo = st.text_input("Correo electrónico", key="r_email")
#|                 clave = st.text_input("Contraseña (mínimo 8 caracteres)", type="password", key="r_pass")
#|                 nivel = st.selectbox("Nivel en el que enseñas", ["Inicial", "Primaria", "Secundaria"], key="r_nivel")
#|                 colegio = st.selectbox("Institución educativa", list(colegios.keys()),
#|                                        format_func=lambda k: colegios[k], key="r_colegio")
#|                 enviar = st.form_submit_button("Crear mi cuenta", type="primary", use_container_width=True)
#|             if enviar:
#|                 c = correo.strip().lower()
#|                 if not (nombre and correo and clave):
#|                     st.warning("Completa los campos obligatorios.")
#|                 elif len(clave) < 8:
#|                     st.warning("La contraseña debe tener al menos 8 caracteres.")
#|                 elif c == admin_correo():
#|                     st.error("Este correo no está disponible.")
#|                 else:
#|                     try:
#|                         execute("INSERT INTO usuarios (nombre, correo, password_hash, nivel_educativo, colegio, colegio_id) "
#|                                 "VALUES (%s,%s,%s,%s,%s,%s)",
#|                                 (nombre.strip(), c, hash_password(clave), nivel,
#|                                  colegios[colegio] if colegio else "Independiente", colegio or None))
#|                         st.success("¡Cuenta creada! Ve a la pestaña «Iniciar sesión».")
#|                     except mysql.connector.Error as err:
#|                         st.error("Este correo ya está registrado." if err.errno == 1062
#|                                  else "No se pudo crear la cuenta. Intenta de nuevo.")
#@@ END
#@@ MODULE ui
#| """Piezas de interfaz compartidas: navegación, avisos, confirmación de costo, vista previa y descarga."""
#| import streamlit as st
#| import streamlit.components.v1 as components
#|
#| from repo import cambiar_color, costo_de, get_asignacion, get_doc_by_id, get_usuario, resumen_asignacion
#| from render import COLORES, COLOR_DEFECTO, ICONO_COLOR, a_docx, a_html
#| from exportar import bloques_de
#|
#| PAG_PANEL = "🏠 Mi Panel"
#| PAG_ANUAL = "📅 Planificación anual"
#| PAG_UNIDADES = "📚 Unidades"
#| PAG_SESIONES = "📝 Sesiones"
#| PAG_BIBLIO = "🗂️ Mi Biblioteca"
#| PAG_ADMIN = "⚙️ Administración"
#|
#| MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
#|
#|
#| # ------------------------------------------------------------------
#| # Navegación y mensajes
#| # ------------------------------------------------------------------
#| def ir_a(pagina):
#|     st.session_state["nav"] = pagina
#|
#|
#| def abrir_area(aid, pagina=None):
#|     st.session_state["area_id"] = aid
#|     if pagina:
#|         st.session_state["nav"] = pagina
#|
#|
#| def abrir_siguiente(aid):
#|     """Activa el área y te lleva al siguiente paso pendiente (anual → unidades → sesiones)."""
#|     r = resumen_asignacion(aid)
#|     pagina = PAG_ANUAL if not r.get("anual") else PAG_UNIDADES if not r.get("unidad") else PAG_SESIONES
#|     abrir_area(aid, pagina)
#|
#|
#| def flash(mensaje, tipo="success"):
#|     st.session_state["_flash"] = (tipo, mensaje)
#|
#|
#| def mostrar_flash():
#|     f = st.session_state.pop("_flash", None)
#|     if f:
#|         {"success": st.success, "info": st.info, "warning": st.warning, "error": st.error}.get(f[0], st.info)(f[1])
#|
#|
#| def ayuda(texto):
#|     st.info("💡 " + texto)
#|
#|
#| def area_activa():
#|     aid = st.session_state.get("area_id")
#|     return get_asignacion(aid) if aid else None
#|
#|
#| def exigir_area():
#|     asig = area_activa()
#|     if not asig:
#|         st.warning("👆 Primero elige o crea un **área** en *Mi Panel*. Ahí indicas tu grado, área y sección.")
#|         st.button("Ir a Mi Panel", on_click=ir_a, args=(PAG_PANEL,))
#|         st.stop()
#|     return asig
#|
#|
#| def exigir_cadena(mensaje, pagina_destino, etiqueta_boton):
#|     st.warning(mensaje)
#|     st.button(etiqueta_boton, on_click=ir_a, args=(pagina_destino,))
#|     st.stop()
#|
#|
#| # ------------------------------------------------------------------
#| # Campos con estado (evitan conflictos entre valor inicial y edición del usuario)
#| # ------------------------------------------------------------------
#| def campo_texto(etiqueta, clave, inicial="", alto=110, ayuda_txt=None):
#|     if clave not in st.session_state:
#|         st.session_state[clave] = inicial or ""
#|     return st.text_area(etiqueta, key=clave, height=alto, help=ayuda_txt)
#|
#|
#| def campo_linea(etiqueta, clave, inicial="", ayuda_txt=None):
#|     if clave not in st.session_state:
#|         st.session_state[clave] = inicial or ""
#|     return st.text_input(etiqueta, key=clave, help=ayuda_txt)
#|
#|
#| def campo_num(etiqueta, clave, minimo, maximo, inicial, paso=1):
#|     if clave not in st.session_state:
#|         st.session_state[clave] = max(minimo, min(maximo, int(inicial)))
#|     return st.number_input(etiqueta, min_value=minimo, max_value=maximo, step=paso, key=clave)
#|
#|
#| def campo_multi(etiqueta, clave, opciones, inicial):
#|     """Multiselección que nunca falla si cambian las opciones."""
#|     if clave not in st.session_state:
#|         st.session_state[clave] = [x for x in (inicial or []) if x in opciones]
#|     else:
#|         st.session_state[clave] = [x for x in st.session_state[clave] if x in opciones]
#|     return st.multiselect(etiqueta, opciones, key=clave)
#|
#|
#| def siguiente_version(clave_ver):
#|     st.session_state[clave_ver] = st.session_state.get(clave_ver, 0) + 1
#|
#|
#| # ------------------------------------------------------------------
#| # Costo en créditos con confirmación
#| # ------------------------------------------------------------------
#| def confirmar(accion, etiqueta, clave, veces=1):
#|     """Botón que pide confirmar el costo en créditos. Devuelve True cuando el usuario confirma."""
#|     u = get_usuario(st.session_state.user_id)
#|     costo = 0 if u["rol"] == "admin" else costo_de(accion) * veces
#|     if costo == 0:
#|         return st.button(etiqueta, key=f"b_{clave}", type="primary")
#|     flag = f"_conf_{clave}"
#|     if not st.session_state.get(flag):
#|         texto = f"{etiqueta} · {costo} crédito{'s' if costo != 1 else ''}"
#|         if st.button(texto, key=f"b_{clave}", type="primary"):
#|             if u["creditos"] < costo:
#|                 st.error(f"Necesitas {costo} créditos y tienes {u['creditos']}. Pide más créditos al administrador.")
#|                 return False
#|             st.session_state[flag] = True
#|             st.rerun()
#|         return False
#|     st.warning(f"Esta acción cuesta **{costo} crédito(s)**. Tienes **{u['creditos']}**. ¿Quieres continuar?")
#|     c1, c2 = st.columns(2)
#|     if c1.button("✅ Sí, continuar", key=f"y_{clave}", use_container_width=True):
#|         st.session_state[flag] = False
#|         return True
#|     if c2.button("✖ Cancelar", key=f"n_{clave}", use_container_width=True):
#|         st.session_state[flag] = False
#|         st.rerun()
#|     return False
#|
#|
#| # ------------------------------------------------------------------
#| # Vista previa, color y descarga
#| # ------------------------------------------------------------------
#| def vista_previa_y_descarga(doc_id, clave, abierta=True):
#|     doc = get_doc_by_id(doc_id)
#|     if not doc:
#|         return
#|     color_doc = (doc.get("color") or COLOR_DEFECTO).lstrip("#")
#|     nombre_actual = next((n for n, h in COLORES.items() if h == color_doc), "Azul")
#|     ckey = f"color_{clave}_{doc_id}"
#|     if ckey not in st.session_state:
#|         st.session_state[ckey] = nombre_actual
#|     elegido = st.radio("🎨 Color del documento", list(COLORES), key=ckey, horizontal=True,
#|                        format_func=lambda n: f"{ICONO_COLOR[n]} {n}")
#|     color = COLORES[elegido]
#|     if color != color_doc:
#|         cambiar_color(doc_id, color)
#|         doc["color"] = color
#|     bloques, horizontal, archivo = bloques_de(doc)
#|     with st.expander("👁️ Vista previa del documento (se actualiza al guardar)", expanded=abierta):
#|         components.html(a_html(bloques, color, doc.get("normativa_usada")), height=620, scrolling=True)
#|     st.download_button("⬇️ Descargar en Word", data=a_docx(bloques, color, doc.get("normativa_usada"), horizontal),
#|                        file_name=archivo, mime=MIME_DOCX, key=f"dl_{clave}_{doc_id}", type="primary")
#@@ END
#@@ MODULE v_panel
#| """Mi Panel: áreas asignadas del docente y guía rápida."""
#| import streamlit as st
#|
#| from curriculo import GRADOS, NIVELES, REGIONES, areas_de, estado_area
#| from repo import borrar_asignacion, crear_asignacion, get_usuario, listar_asignaciones, resumen_asignacion
#| from ui import PAG_ANUAL, abrir_area, abrir_siguiente, flash
#|
#|
#| def _pasos(aid):
#|     r = resumen_asignacion(aid)
#|     marca = lambda ok: "✅" if ok else "⬜"
#|     c1, c2, c3, c4 = st.columns(4)
#|     c1.markdown(f"**1. Tu área** ✅\n\nYa la creaste")
#|     c2.markdown(f"**2. Planificación anual** {marca(r.get('anual'))}\n\nSituaciones y unidades")
#|     c3.markdown(f"**3. Unidades** {marca(r.get('unidad'))}\n\n{r.get('unidad', 0)} creadas")
#|     c4.markdown(f"**4. Sesiones y materiales** {marca(r.get('sesion'))}\n\n{r.get('sesion', 0)} sesiones")
#|
#|
#| def _crear_area_cb(uid):
#|     """Se ejecuta ANTES de redibujar la página (así se puede cambiar el área activa sin errores)."""
#|     ss = st.session_state
#|     if not ss.get("na_area"):
#|         flash("No hay áreas para este nivel. Pide al administrador que cargue el currículo.", "error")
#|         return
#|     nuevo = crear_asignacion(uid, {"ciclo_escolar": int(ss.get("na_ciclo", 2026)),
#|                                    "institucion": (ss.get("na_inst") or "").strip(),
#|                                    "director": (ss.get("na_dir") or "").strip(),
#|                                    "docente": (ss.get("na_doc") or "").strip(), "region": ss.get("na_region", "Lima"),
#|                                    "nivel": ss["na_nivel"], "grado": ss["na_grado"], "area": ss["na_area"],
#|                                    "seccion": (ss.get("na_seccion") or "").strip()})
#|     ss["area_id"] = nuevo
#|     flash(f"¡Listo! Creaste {ss['na_area']} · {ss['na_grado']}. Sigue con la planificación anual.")
#|
#|
#| def _borrar_area_cb():
#|     ss = st.session_state
#|     if not ss.get("del_area_ok"):
#|         flash("Marca la casilla para confirmar que quieres eliminarla.", "warning")
#|         return
#|     elegida = ss.get("del_area_sel")
#|     borrar_asignacion(elegida)
#|     if ss.get("area_id") == elegida:
#|         ss["area_id"] = None
#|     ss["del_area_ok"] = False
#|     flash("Área eliminada.")
#|
#|
#| def render():
#|     uid = st.session_state.user_id
#|     u = get_usuario(uid)
#|     st.title(f"👋 ¡Hola, {u['nombre'].split()[0]}!")
#|     st.caption("Aquí empiezas. Crea tus áreas (el curso que enseñas) y sigue los pasos: Anual → Unidades → Sesiones.")
#|
#|     asigs = listar_asignaciones(uid)
#|
#|     if not asigs:
#|         st.info("💡 **Empieza aquí:** crea tu primera área abajo. Solo toma un minuto y luego todo se llena solo.")
#|     else:
#|         activa = st.session_state.get("area_id")
#|         if activa:
#|             actual = next((a for a in asigs if a["id"] == activa), None)
#|             if actual:
#|                 st.subheader(f"Tu ruta en: {actual['area']} · {actual['grado']}")
#|                 _pasos(actual["id"])
#|                 st.button("Continuar con la planificación anual →", on_click=abrir_area,
#|                           args=(actual["id"], PAG_ANUAL), type="primary")
#|                 st.divider()
#|
#|         st.subheader("📌 Mis áreas asignadas")
#|         for nivel in NIVELES:
#|             grupo = [a for a in asigs if a["nivel"] == nivel]
#|             if not grupo:
#|                 continue
#|             st.markdown(f"##### {nivel}")
#|             cols = st.columns(3)
#|             for i, a in enumerate(grupo):
#|                 with cols[i % 3]:
#|                     with st.container(border=True):
#|                         st.markdown(f"**{a['area']}**")
#|                         st.caption(f"{a['grado']} · Sección {a['seccion'] or '—'} · {a['ciclo_escolar']}")
#|                         r = resumen_asignacion(a["id"])
#|                         st.caption(f"📅 {'✅' if r.get('anual') else '⬜'}  📚 {r.get('unidad', 0)}  📝 {r.get('sesion', 0)}")
#|                         st.button("Abrir ▶", key=f"abrir_{a['id']}", on_click=abrir_siguiente, args=(a["id"],),
#|                                   use_container_width=True, type="primary")
#|
#|     with st.expander("➕ Nueva área", expanded=not asigs):
#|         st.caption("Estos datos aparecerán en todos tus documentos (los puedes cambiar después).")
#|         c1, c2 = st.columns(2)
#|         nivel = c1.selectbox("Nivel", NIVELES, index=1, key="na_nivel")
#|         grado = c2.selectbox("Grado / edad", GRADOS[nivel], key="na_grado")
#|         areas = areas_de(nivel)
#|         area = c1.selectbox("Área curricular", areas, key="na_area") if areas else None
#|         seccion = c2.text_input("Sección (ej.: A)", key="na_seccion")
#|         inst_def = u["colegio"] if u["colegio"] and u["colegio"] != "Independiente" else ""
#|         inst = c1.text_input("Institución educativa", value=inst_def, key="na_inst")
#|         director = c2.text_input("Nombre del director(a)", key="na_dir")
#|         docente = c1.text_input("Nombre del docente", value=u["nombre"], key="na_doc")
#|         region = c2.selectbox("Región", REGIONES, index=REGIONES.index("Lima"), key="na_region")
#|         ciclo = c1.number_input("Año escolar", 2024, 2035, 2026, key="na_ciclo")
#|         if area:
#|             n_comp, n_ver, n_des = estado_area(nivel, area, grado)
#|             if n_des == 0:
#|                 st.caption("ℹ️ Para este grado aún no hay desempeños cargados: la IA propondrá algunos "
#|                            "y los verás marcados como «por verificar».")
#|         st.button("✅ Crear área", type="primary", key="na_crear", on_click=_crear_area_cb, args=(uid,))
#|
#|     if asigs:
#|         with st.expander("🗑️ Eliminar un área"):
#|             st.caption("Se borran también todos los documentos de esa área.")
#|             ids = [a["id"] for a in asigs]
#|             elegida = st.selectbox("Área", ids, key="del_area_sel",
#|                                    format_func=lambda i: next(f"{a['area']} · {a['grado']} · {a['seccion'] or '—'}"
#|                                                               for a in asigs if a["id"] == i))
#|             st.checkbox("Sí, quiero eliminarla", key="del_area_ok")
#|             st.button("Eliminar área", key="del_area_btn", on_click=_borrar_area_cb)
#@@ END
#@@ MODULE v_anual
#| """Planificación anual: datos informativos, caracterización, competencias, situaciones significativas y unidades."""
#| import streamlit as st
#|
#| from curriculo import ciclo_de, competencias_de
#| from ia import generar_texto, pedir_json, preambulo
#| from normativa import normativa_vigente
#| from repo import actualizar_asignacion, contenido, cobrar, get_doc, guardar_doc
#| from ui import (PAG_UNIDADES, campo_linea, campo_multi, campo_num, campo_texto, confirmar, exigir_area, flash,
#|                 ir_a, siguiente_version, vista_previa_y_descarga)
#| from util import entero, norm, s
#|
#|
#| def _generar_caracterizacion(asig, notas):
#|     prompt = f"""{preambulo()}
#| Redacta un BOCETO de caracterización y contexto de los estudiantes (2 párrafos, máximo 150 palabras).
#| Datos: nivel {asig['nivel']}, grado {asig['grado']}, área {asig['area']}, región {asig['region']}, institución {asig['institucion'] or 'no indicada'}.
#| Notas del docente: {notas or 'ninguna'}.
#| Incluye: rasgos de desarrollo propios de la edad, intereses, contexto sociocultural probable de la región y necesidades de aprendizaje frecuentes.
#| No inventes cifras ni datos personales. Tono general; el docente lo ajustará. Devuelve solo el texto."""
#|     texto, _ = generar_texto(prompt)
#|     return s(texto)
#|
#|
#| def _generar_unidades(asig, comps_sel, n):
#|     ctx = "\n".join(f"- {c['nombre']} (capacidades: {'; '.join(c['capacidades'])})" for c in comps_sel)
#|     prompt = f"""{preambulo()}
#| Elabora las SITUACIONES SIGNIFICATIVAS de la PLANIFICACIÓN ANUAL {asig['ciclo_escolar']} con {n} unidades de aprendizaje.
#| Datos: nivel {asig['nivel']}, grado {asig['grado']}, área {asig['area']}, región {asig['region']}, institución {asig['institucion'] or 'no indicada'}.
#| Caracterización de los estudiantes: {asig.get('caracterizacion') or 'no especificada'}
#| Competencias del área (usa SOLO estos nombres, escritos EXACTAMENTE igual):
#| {ctx}
#|
#| Para cada unidad entrega:
#| - "titulo": título corto y motivador.
#| - "problema": problema identificado del contexto (1 a 2 oraciones).
#| - "situacion": situación significativa contextualizada a {asig['region']} (4 a 6 oraciones) que plantee un reto y termine con preguntas retadoras.
#| - "valores": valores observables (2 a 3, separados por coma) tomados de los enfoques transversales del CNEB.
#| - "competencias": lista de 1 a 3 nombres EXACTOS de la lista anterior. Entre todas las unidades deben quedar cubiertas todas las competencias.
#| - "semanas": número entre 3 y 5.
#|
#| Formato: {{"unidades":[{{"numero":1,"titulo":"...","problema":"...","situacion":"...","valores":"...","competencias":["..."],"semanas":4}}]}}"""
#|     datos, _ = pedir_json(prompt)
#|     lista = datos.get("unidades") if isinstance(datos, dict) else datos
#|     if not isinstance(lista, list) or not lista:
#|         raise RuntimeError("La IA no devolvió unidades. Intenta de nuevo.")
#|     por_nombre = {norm(c["nombre"]): c for c in comps_sel}
#|     unidades = []
#|     for i in range(1, n + 1):
#|         u = lista[i - 1] if i - 1 < len(lista) and isinstance(lista[i - 1], dict) else {}
#|         elegidas = []
#|         for x in u.get("competencias") or []:
#|             c = por_nombre.get(norm(x))
#|             if c and c["nombre"] not in elegidas:
#|                 elegidas.append(c["nombre"])
#|         if not elegidas:
#|             elegidas = [comps_sel[(i - 1) % len(comps_sel)]["nombre"]]
#|         caps = [cap for c in comps_sel if c["nombre"] in elegidas for cap in c["capacidades"]]
#|         unidades.append({"numero": i, "titulo": s(u.get("titulo")) or f"Unidad {i}", "problema": s(u.get("problema")),
#|                          "situacion": s(u.get("situacion")), "valores": s(u.get("valores")),
#|                          "competencias": elegidas, "capacidades": caps,
#|                          "semanas": entero(u.get("semanas"), 4, 1, 12)})
#|     return unidades
#|
#|
#| def _vacia(i, comps_sel):
#|     nombre = comps_sel[(i - 1) % len(comps_sel)]
#|     return {"numero": i, "titulo": f"Unidad {i}", "problema": "", "situacion": "", "valores": "",
#|             "competencias": [nombre["nombre"]], "capacidades": list(nombre["capacidades"]), "semanas": 4}
#|
#|
#| def render():
#|     asig = exigir_area()
#|     uid, aid = st.session_state.user_id, asig["id"]
#|     st.title("📅 Planificación anual")
#|     st.caption(f"{asig['area']} · {asig['grado']} · Sección {asig['seccion'] or '—'}  |  Alineada a RM N.° 501-2025-MINEDU")
#|     st.info("💡 Sigue los pasos de arriba hacia abajo. Todo lo que escribe la IA lo puedes editar antes de guardar.")
#|
#|     ver_key = f"ver_anual_{aid}"
#|     ver = st.session_state.get(ver_key, 0)
#|     doc = get_doc(aid, "anual")
#|     data = contenido(doc) if doc else {}
#|
#|     # ① DATOS INFORMATIVOS
#|     st.subheader("① Datos informativos")
#|     with st.expander("Ver y editar mis datos", expanded=not asig["director"]):
#|         c1, c2 = st.columns(2)
#|         inst = c1.text_input("Institución educativa", value=asig["institucion"] or "", key=f"d_inst_{aid}")
#|         director = c2.text_input("Director(a)", value=asig["director"] or "", key=f"d_dir_{aid}")
#|         docente = c1.text_input("Docente", value=asig["docente"] or "", key=f"d_doc_{aid}")
#|         seccion = c2.text_input("Sección", value=asig["seccion"] or "", key=f"d_sec_{aid}")
#|         st.caption(f"Nivel: {asig['nivel']} · Grado: {asig['grado']} · Área: {asig['area']} · "
#|                    f"Ciclo {ciclo_de(asig['nivel'], asig['grado'])} · Región: {asig['region']}")
#|         if st.button("💾 Guardar datos", key=f"d_save_{aid}"):
#|             actualizar_asignacion(aid, institucion=inst.strip(), director=director.strip(),
#|                                   docente=docente.strip(), seccion=seccion.strip())
#|             flash("Datos guardados ✅")
#|             st.rerun()
#|
#|     # ② CARACTERIZACIÓN
#|     st.subheader("② Caracterización y contexto de tus estudiantes")
#|     st.caption("Describe brevemente cómo son tus estudiantes. Si no sabes qué escribir, pide un boceto a la IA.")
#|     notas = st.text_input("Cuéntame algo de tus estudiantes (opcional)", key=f"car_notas_{aid}",
#|                           placeholder="Ej.: zona rural, les gusta el fútbol, varios trabajan con sus padres")
#|     if confirmar("caracterizacion", "✨ Escribir boceto con IA", f"car_{aid}"):
#|         try:
#|             with st.spinner("Escribiendo el boceto..."):
#|                 texto = _generar_caracterizacion(asig, notas)
#|             actualizar_asignacion(aid, caracterizacion=texto)
#|             cobrar(uid, "caracterizacion")
#|             siguiente_version(ver_key)
#|             flash("Boceto listo. Léelo y ajústalo a tu realidad.")
#|             st.rerun()
#|         except Exception as e:
#|             st.error(f"No se pudo generar: {e}")
#|     car = campo_texto("Caracterización del estudiante", f"car_{aid}_{ver}", asig.get("caracterizacion") or "", 150)
#|     if st.button("💾 Guardar caracterización", key=f"car_save_{aid}"):
#|         actualizar_asignacion(aid, caracterizacion=car)
#|         flash("Caracterización guardada ✅")
#|         st.rerun()
#|
#|     # ③ COMPETENCIAS
#|     st.subheader("③ Competencias que trabajarás este año")
#|     comps = competencias_de(asig["nivel"], asig["area"])
#|     if not comps:
#|         st.error("Esta área todavía no tiene competencias cargadas. Pide al administrador que las agregue "
#|                  "en Administración → Currículo.")
#|         st.stop()
#|     nombres = [c["nombre"] for c in comps]
#|     sel = campo_multi("Competencias del año", f"comp_{aid}_{ver}", nombres, data.get("competencias_area") or nombres)
#|     if not sel:
#|         st.warning("Elige al menos una competencia.")
#|         st.stop()
#|     comps_sel = [c for c in comps if c["nombre"] in sel]
#|     with st.expander("Ver capacidades de cada competencia"):
#|         for c in comps_sel:
#|             st.markdown(f"**{c['nombre']}**" + ("" if c["verificado"] else "  ⚠️ _pendiente de verificación_"))
#|             st.markdown("\n".join(f"- {x}" for x in c["capacidades"]))
#|
#|     # ④ SITUACIONES SIGNIFICATIVAS Y UNIDADES
#|     st.subheader("④ Situaciones significativas y unidades")
#|     unidades = data.get("unidades") or []
#|     n = len(unidades)
#|     if not unidades:
#|         n = int(st.number_input("¿Cuántas unidades tendrá el año?", 1, 12, 6, key=f"nuni_{aid}"))
#|     st.caption("La IA propone una situación significativa por unidad, con el problema del contexto, valores y competencias.")
#|     if confirmar("anual", "✨ Generar situaciones significativas con IA" if not unidades else
#|                  "🔄 Volver a generar (reemplaza lo actual)", f"anual_{aid}"):
#|         try:
#|             with st.spinner("Creando situaciones significativas... (puede tardar un minuto)"):
#|                 nuevas = _generar_unidades(asig, comps_sel, n)
#|             guardar_doc(uid, aid, "anual", 1, f"Planificación anual {asig['area']} {asig['grado']}",
#|                         {"competencias_area": sel, "unidades": nuevas}, normativa=normativa_vigente()[1])
#|             cobrar(uid, "anual")
#|             siguiente_version(ver_key)
#|             flash("¡Listo! Revisa cada unidad y ajusta lo que quieras.")
#|             st.rerun()
#|         except Exception as e:
#|             st.error(f"No se pudo generar: {e}")
#|
#|     if unidades:
#|         for u in unidades:
#|             i = u["numero"]
#|             base = f"an_{aid}_{ver}_{i}"
#|             with st.expander(f"Unidad {i}: {u['titulo']}", expanded=(i == 1)):
#|                 campo_linea("Título de la unidad", f"{base}_t", u["titulo"])
#|                 campo_texto("Problema identificado", f"{base}_p", u["problema"], 80)
#|                 campo_texto("Situación significativa", f"{base}_s", u["situacion"], 160)
#|                 campo_linea("Valores observables", f"{base}_v", u["valores"])
#|                 cs = campo_multi("Competencias de esta unidad", f"{base}_c", sel, u["competencias"])
#|                 caps_op = [cap for c in comps if c["nombre"] in cs for cap in c["capacidades"]]
#|                 campo_multi("Capacidades a trabajar", f"{base}_k", caps_op, u["capacidades"])
#|                 campo_num("Semanas", f"{base}_w", 1, 12, u.get("semanas") or 4)
#|
#|         def recoger():
#|             res = []
#|             for u in unidades:
#|                 i = u["numero"]
#|                 base = f"an_{aid}_{ver}_{i}"
#|                 res.append({"numero": i, "titulo": st.session_state.get(f"{base}_t", u["titulo"]),
#|                             "problema": st.session_state.get(f"{base}_p", ""),
#|                             "situacion": st.session_state.get(f"{base}_s", ""),
#|                             "valores": st.session_state.get(f"{base}_v", ""),
#|                             "competencias": st.session_state.get(f"{base}_c", u["competencias"]),
#|                             "capacidades": st.session_state.get(f"{base}_k", u["capacidades"]),
#|                             "semanas": entero(st.session_state.get(f"{base}_w"), 4, 1, 12)})
#|             return res
#|
#|         def guardar(lista):
#|             guardar_doc(uid, aid, "anual", 1, f"Planificación anual {asig['area']} {asig['grado']}",
#|                         {"competencias_area": sel, "unidades": lista})
#|
#|         b1, b2, b3 = st.columns(3)
#|         if b1.button("💾 Guardar planificación", type="primary", key=f"an_save_{aid}", use_container_width=True):
#|             guardar(recoger())
#|             st.success("Planificación guardada ✅")
#|         if b2.button("➕ Agregar unidad", key=f"an_add_{aid}", use_container_width=True):
#|             lista = recoger()
#|             lista.append(_vacia(len(lista) + 1, comps_sel))
#|             guardar(lista)
#|             siguiente_version(ver_key)
#|             st.rerun()
#|         if b3.button("➖ Quitar la última", key=f"an_del_{aid}", use_container_width=True) and len(unidades) > 1:
#|             guardar(recoger()[:-1])
#|             siguiente_version(ver_key)
#|             st.rerun()
#|
#|     # ⑤ VISTA PREVIA
#|     if doc:
#|         st.subheader("⑤ Tu documento")
#|         vista_previa_y_descarga(doc["id"], f"anual_{aid}")
#|         st.button("Siguiente: crear las unidades →", on_click=ir_a, args=(PAG_UNIDADES,), type="primary")
#@@ END
#@@ MODULE v_unidades
#| """Unidades de aprendizaje: producto, secuencia por semanas, propósitos, enfoques; importar y sincronizar."""
#| import pandas as pd
#| import streamlit as st
#|
#| from curriculo import buscar_competencia, contexto_curricular, transversales
#| from docx import Document
#| from ia import generar_texto, pedir_json, preambulo
#| from normativa import normativa_vigente
#| from repo import (cobrar, contenido, crear_sesiones_desde_secuencia, get_doc, get_doc_by_id, guardar_doc,
#|                   listar_docs)
#| from ui import (PAG_ANUAL, PAG_SESIONES, campo_linea, campo_multi, campo_texto, confirmar, exigir_area,
#|                 exigir_cadena, flash, ir_a, siguiente_version, vista_previa_y_descarga)
#| from util import a_lista, a_texto, entero, norm, s
#|
#|
#| # ------------------------------------------------------------------
#| # Normalización de lo que devuelve la IA (los textos oficiales vienen de la base curricular)
#| # ------------------------------------------------------------------
#| def _enfoques(ia_enfoques, enfoques_db):
#|     por_nombre = {norm(e["nombre"]): e for e in enfoques_db}
#|     res = []
#|     for x in ia_enfoques or []:
#|         if not isinstance(x, dict):
#|             continue
#|         e = por_nombre.get(norm(x.get("enfoque")))
#|         if e and not any(r["enfoque"] == e["nombre"] for r in res):
#|             res.append({"enfoque": e["nombre"], "valores": ", ".join(e["items"]), "acciones": s(x.get("acciones"))})
#|     return res
#|
#|
#| def normalizar_unidad(ia, mapa, ua, semanas, spw):
#|     """Convierte el JSON de la IA en la unidad final. Desempeños y capacidades salen de la base curricular."""
#|     prod = ia.get("producto") or {}
#|     producto = {"evidencia": s(prod.get("evidencia")), "criterios": a_texto(prod.get("criterios")),
#|                 "relacion": s(prod.get("relacion"))}
#|
#|     props = []
#|     for p in ia.get("propositos") or []:
#|         if not isinstance(p, dict):
#|             continue
#|         nombre = buscar_competencia(p.get("competencia"), mapa)
#|         raw = s(p.get("competencia"))
#|         info = mapa.get(nombre) if nombre else None
#|         if not info and not raw:
#|             continue
#|         caps, des, por_ver = [], [], False
#|         if info:
#|             caps = info["comp"]["capacidades"]
#|             for idx in p.get("desempenos") or []:
#|                 digitos = "".join(ch for ch in str(idx) if ch.isdigit())
#|                 if digitos and 1 <= int(digitos) <= len(info["des"]):
#|                     des.append(info["des"][int(digitos) - 1]["texto"])
#|             if not des and info["des"]:
#|                 des = [d["texto"] for d in info["des"][:3]]
#|         else:
#|             caps = a_lista(p.get("capacidades"))
#|         if not des:
#|             des, por_ver = a_lista(p.get("desempenos_texto")), True
#|         if nombre and any(x["competencia"] == nombre for x in props):
#|             continue
#|         props.append({"competencia": nombre or raw, "capacidades": caps, "desempenos": des, "por_verificar": por_ver,
#|                       "proposito": s(p.get("proposito")), "campo_tematico": s(p.get("campo_tematico")),
#|                       "evidencia": s(p.get("evidencia")), "instrumento": s(p.get("instrumento"))})
#|     for nombre, info in mapa.items():  # toda competencia de la unidad debe tener su fila
#|         if not any(x["competencia"] == nombre for x in props):
#|             ds = [d["texto"] for d in info["des"][:3]]
#|             props.append({"competencia": nombre, "capacidades": info["comp"]["capacidades"], "desempenos": ds,
#|                           "por_verificar": not ds, "proposito": "", "campo_tematico": "", "evidencia": "",
#|                           "instrumento": ""})
#|
#|     primera = next(iter(mapa), "")
#|     secuencia = []
#|     for f in ia.get("secuencia") or []:
#|         if isinstance(f, dict):
#|             secuencia.append({"semana": entero(f.get("semana"), 1, 1, 20), "titulo": s(f.get("titulo")),
#|                               "competencia": buscar_competencia(f.get("competencia"), mapa) or primera})
#|     if not secuencia:
#|         for sem in range(1, semanas + 1):
#|             for k in range(spw):
#|                 secuencia.append({"semana": sem, "titulo": f"Sesión {len(secuencia) + 1}", "competencia": primera})
#|
#|     enfoques = _enfoques(ia.get("enfoques"), transversales()[1])
#|     return {"numero": ua["numero"], "titulo": s(ia.get("titulo")) or ua["titulo"],
#|             "situacion": s(ia.get("situacion")) or ua["situacion"], "producto": producto,
#|             "secuencia": secuencia, "propositos": props, "enfoques": enfoques,
#|             "semanas": semanas, "sesiones_por_semana": spw}
#|
#|
#| def _generar_unidad(asig, ua, semanas, spw):
#|     ctx, mapa = contexto_curricular(asig["nivel"], asig["area"], asig["grado"], ua["competencias"])
#|     if not mapa:
#|         raise RuntimeError("La unidad no tiene competencias válidas. Revisa la planificación anual.")
#|     enfoques = transversales()[1]
#|     total = semanas * spw
#|     prompt = f"""{preambulo()}
#| Elabora una UNIDAD DE APRENDIZAJE.
#| Datos: nivel {asig['nivel']}, grado {asig['grado']}, área {asig['area']}, región {asig['region']}.
#| Unidad N.° {ua['numero']}: {ua['titulo']}
#| Problema identificado: {ua.get('problema') or '-'}
#| Situación significativa: {ua['situacion']}
#| Valores observables: {ua.get('valores') or '-'}
#| Duración: {semanas} semanas, {spw} sesiones por semana (total {total} sesiones).
#|
#| Competencias, capacidades y desempeños disponibles (D1, D2... son los desempeños; NO los reescribas, solo indica sus números):
#| {ctx}
#|
#| Enfoques transversales disponibles (usa nombres EXACTOS): {'; '.join(e['nombre'] for e in enfoques)}
#|
#| Entrega:
#| - "titulo": título de la unidad.
#| - "producto": {{"evidencia": producto o evidencia final de la unidad, "criterios": lista de 3 a 5 criterios de evaluación, "relacion": cómo se relaciona con otras áreas}}
#| - "secuencia": lista de EXACTAMENTE {total} sesiones, cada una {{"semana": n, "titulo": pregunta o reto en voz del estudiante (ej. "¿Cómo repartimos en partes iguales?"), "competencia": nombre EXACTO}}.
#| - "propositos": un objeto por competencia: {{"competencia": nombre EXACTO, "desempenos": [números de los D elegidos, p. ej. [1,3]], "desempenos_texto": [solo si no hay D disponibles, 2 desempeños propuestos], "proposito": propósito de aprendizaje, "campo_tematico": contenidos, "evidencia": evidencia, "instrumento": instrumento de evaluación}}
#| - "enfoques": 2 a 3 objetos {{"enfoque": nombre EXACTO, "acciones": acciones observables concretas para esta unidad}}."""
#|     ia, _ = pedir_json(prompt)
#|     if not isinstance(ia, dict):
#|         raise RuntimeError("La IA devolvió un formato inesperado. Intenta de nuevo.")
#|     return normalizar_unidad(ia, mapa, ua, semanas, spw)
#|
#|
#| def _texto_de_docx(archivo):
#|     doc = Document(archivo)
#|     partes = [p.text for p in doc.paragraphs if p.text.strip()]
#|     for t in doc.tables:
#|         for fila in t.rows:
#|             partes.append(" | ".join(c.text.strip() for c in fila.cells))
#|     return "\n".join(partes)[:15000]
#|
#|
#| def _importar_unidad(asig, ua, texto, semanas, spw):
#|     ctx, mapa = contexto_curricular(asig["nivel"], asig["area"], asig["grado"], ua["competencias"])
#|     prompt = f"""{preambulo()}
#| Tengo una unidad de aprendizaje escrita por un docente. Conviértela al formato indicado SIN inventar contenido nuevo (si falta algo, déjalo vacío).
#| Competencias de esta unidad: {', '.join(ua['competencias'])}
#|
#| TEXTO DEL DOCENTE:
#| {texto}
#|
#| Formato: {{"titulo": "...", "situacion": "...", "producto": {{"evidencia": "...", "criterios": ["..."], "relacion": "..."}},
#| "secuencia": [{{"semana": 1, "titulo": "...", "competencia": "..."}}],
#| "propositos": [{{"competencia": "...", "capacidades": ["..."], "desempenos_texto": ["..."], "proposito": "...", "campo_tematico": "...", "evidencia": "...", "instrumento": "..."}}],
#| "enfoques": [{{"enfoque": "...", "acciones": "..."}}]}}"""
#|     ia, _ = pedir_json(prompt)
#|     if not isinstance(ia, dict):
#|         raise RuntimeError("La IA devolvió un formato inesperado.")
#|     for p in ia.get("propositos") or []:  # lo importado se marca "por verificar"
#|         if isinstance(p, dict):
#|             p.pop("desempenos", None)
#|     return normalizar_unidad(ia, mapa, ua, semanas, spw)
#|
#|
#| # ------------------------------------------------------------------
#| # Pantalla
#| # ------------------------------------------------------------------
#| def render():
#|     asig = exigir_area()
#|     aid = asig["id"]
#|     st.title("📚 Unidades de aprendizaje")
#|     st.info("💡 Elige una unidad, pulsa **Generar** y revisa. Cada unidad nace de tu planificación anual.")
#|     anual = get_doc(aid, "anual")
#|     if not anual:
#|         exigir_cadena("Primero necesitas tu planificación anual (de ahí salen las unidades).", PAG_ANUAL,
#|                       "Ir a Planificación anual")
#|     unidades = contenido(anual).get("unidades") or []
#|     if not unidades:
#|         exigir_cadena("Tu planificación anual todavía no tiene unidades. Genera las situaciones significativas.",
#|                       PAG_ANUAL, "Ir a Planificación anual")
#|     existentes = {d["numero"] for d in listar_docs(aid, "unidad")}
#|     num = st.radio("Elige la unidad", [u["numero"] for u in unidades], horizontal=True, key=f"un_sel_{aid}",
#|                    format_func=lambda n: f"{'✅' if n in existentes else '⬜'} Unidad {n}")
#|     _unidad(asig, anual, next(u for u in unidades if u["numero"] == num))
#|
#|
#| def _unidad(asig, anual, ua):
#|     uid, aid, n = st.session_state.user_id, asig["id"], ua["numero"]
#|     doc = get_doc(aid, "unidad", numero=n)
#|     d = contenido(doc) if doc else {}
#|     ver_key = f"ver_unidad_{aid}_{n}"
#|     ver = st.session_state.get(ver_key, 0)
#|
#|     st.subheader(f"Unidad {n}: {ua['titulo']}")
#|     st.markdown(f"**Situación significativa:** {ua['situacion'] or '_(vacía: complétala en la planificación anual)_'}")
#|     st.caption("Competencias: " + ", ".join(ua["competencias"]))
#|
#|     # --- Generar / importar
#|     with st.container(border=True):
#|         c1, c2 = st.columns(2)
#|         semanas = c1.number_input("Semanas de la unidad", 1, 12, entero(d.get("semanas") or ua.get("semanas"), 4, 1, 12),
#|                                   key=f"sem_{aid}_{n}_{ver}")
#|         spw = c2.number_input("Sesiones por semana", 1, 8, entero(d.get("sesiones_por_semana"), 3, 1, 8),
#|                               key=f"spw_{aid}_{n}_{ver}")
#|         etiqueta = "✨ Generar unidad con IA" if not doc else "🔄 Volver a generar (reemplaza lo actual)"
#|         if confirmar("unidad", etiqueta, f"unidad_{aid}_{n}"):
#|             try:
#|                 with st.spinner("Armando la unidad... (puede tardar un minuto)"):
#|                     nueva = _generar_unidad(asig, ua, int(semanas), int(spw))
#|                 guardar_doc(uid, aid, "unidad", n, f"Unidad {n}: {nueva['titulo']}", nueva,
#|                             padre_id=anual["id"], normativa=normativa_vigente()[1])
#|                 cobrar(uid, "unidad")
#|                 siguiente_version(ver_key)
#|                 flash("¡Unidad lista! Revisa y ajusta lo que quieras.")
#|                 st.rerun()
#|             except Exception as e:
#|                 st.error(f"No se pudo generar: {e}")
#|
#|         with st.expander("📥 Cargar una unidad que ya tengo en Word"):
#|             st.caption("Sube tu unidad (.docx) y la IA la ordena en este formato. Lo importado queda marcado «por verificar».")
#|             archivo = st.file_uploader("Archivo Word", type=["docx"], key=f"up_{aid}_{n}_{ver}")
#|             if archivo is not None and confirmar("importar", "Convertir mi unidad", f"imp_{aid}_{n}"):
#|                 try:
#|                     with st.spinner("Leyendo y ordenando tu unidad..."):
#|                         nueva = _importar_unidad(asig, ua, _texto_de_docx(archivo), int(semanas), int(spw))
#|                     guardar_doc(uid, aid, "unidad", n, f"Unidad {n}: {nueva['titulo']}", nueva,
#|                                 padre_id=anual["id"], normativa=normativa_vigente()[1])
#|                     cobrar(uid, "importar")
#|                     siguiente_version(ver_key)
#|                     flash("Unidad importada. Revísala con calma.")
#|                     st.rerun()
#|                 except Exception as e:
#|                     st.error(f"No se pudo importar: {e}")
#|
#|     if not doc:
#|         st.caption("Aún no hay contenido para esta unidad.")
#|         return
#|
#|     # --- Edición
#|     base = f"u_{aid}_{n}_{ver}"
#|     st.markdown("### ✏️ Edita tu unidad")
#|     campo_linea("Título de la unidad", f"{base}_tit", d.get("titulo", ""))
#|     campo_texto("Situación significativa", f"{base}_sit", d.get("situacion", ""), 150)
#|
#|     st.markdown("**Producto de aprendizaje**")
#|     pr = d.get("producto") or {}
#|     campo_texto("Evidencia (producto final)", f"{base}_pe", pr.get("evidencia", ""), 80)
#|     campo_texto("Criterios de evaluación (uno por línea)", f"{base}_pc", pr.get("criterios", ""), 110)
#|     campo_texto("Relación con otras áreas", f"{base}_pr", pr.get("relacion", ""), 80)
#|
#|     st.markdown("**Secuencia de la unidad** (cada fila es una sesión; puedes agregar, borrar o cambiar títulos)")
#|     nombres_comp = [p["competencia"] for p in d.get("propositos", [])]
#|     filas = [{"semana": f.get("semana", 1), "titulo": f.get("titulo", ""),
#|               "competencia": f.get("competencia") if f.get("competencia") in nombres_comp else (nombres_comp[0] if nombres_comp else "")}
#|              for f in d.get("secuencia", [])]
#|     df = pd.DataFrame(filas, columns=["semana", "titulo", "competencia"])
#|     df["semana"] = pd.to_numeric(df["semana"], errors="coerce").fillna(1).astype(int)
#|     seq = st.data_editor(df, key=f"{base}_seq", num_rows="dynamic", hide_index=True, column_config={
#|         "semana": st.column_config.NumberColumn("Semana", min_value=1, max_value=20, step=1),
#|         "titulo": st.column_config.TextColumn("Título / pregunta retadora", width="large"),
#|         "competencia": st.column_config.SelectboxColumn("Competencia", options=nombres_comp or [""])})
#|
#|     st.markdown("**Propósitos de aprendizaje**")
#|     props = d.get("propositos", [])
#|     for j, p in enumerate(props):
#|         with st.expander(p["competencia"], expanded=(j == 0)):
#|             if p.get("por_verificar"):
#|                 st.caption("⚠️ Desempeños por verificar con el Programa Curricular oficial.")
#|             campo_texto("Capacidades (una por línea)", f"{base}_p{j}_cap", a_texto(p.get("capacidades")), 90)
#|             campo_texto("Desempeños (uno por línea)", f"{base}_p{j}_des", a_texto(p.get("desempenos")), 130)
#|             campo_texto("Propósito de aprendizaje", f"{base}_p{j}_pro", p.get("proposito", ""), 80)
#|             campo_linea("Campo temático", f"{base}_p{j}_ct", p.get("campo_tematico", ""))
#|             campo_texto("Evidencia", f"{base}_p{j}_ev", p.get("evidencia", ""), 70)
#|             campo_linea("Instrumento de evaluación", f"{base}_p{j}_in", p.get("instrumento", ""))
#|
#|     st.markdown("**Enfoques transversales**")
#|     enfoques_db = transversales()[1]
#|     nombres_enf = [e["nombre"] for e in enfoques_db]
#|     elegidos = campo_multi("Enfoques de esta unidad", f"{base}_enf", nombres_enf,
#|                            [e["enfoque"] for e in d.get("enfoques", [])])
#|     previos = {e["enfoque"]: e.get("acciones", "") for e in d.get("enfoques", [])}
#|     for k, nombre in enumerate(elegidos):
#|         campo_texto(f"Acciones observables — {nombre}", f"{base}_enf_{k}_{norm(nombre)[:12]}",
#|                     previos.get(nombre, ""), 70)
#|
#|     def recoger():
#|         st_ = st.session_state
#|         nueva_seq = []
#|         for _, f in seq.fillna("").iterrows():
#|             if s(f["titulo"]):
#|                 nueva_seq.append({"semana": entero(f["semana"], 1, 1, 20), "titulo": s(f["titulo"]),
#|                                   "competencia": s(f["competencia"])})
#|         nuevos_props = []
#|         for j, p in enumerate(props):
#|             nuevos_props.append({**p, "capacidades": a_lista(st_.get(f"{base}_p{j}_cap")),
#|                                  "desempenos": a_lista(st_.get(f"{base}_p{j}_des")),
#|                                  "proposito": st_.get(f"{base}_p{j}_pro", ""),
#|                                  "campo_tematico": st_.get(f"{base}_p{j}_ct", ""),
#|                                  "evidencia": st_.get(f"{base}_p{j}_ev", ""),
#|                                  "instrumento": st_.get(f"{base}_p{j}_in", "")})
#|         nuevos_enf = []
#|         for k, nombre in enumerate(st_.get(f"{base}_enf", [])):
#|             e = next((x for x in enfoques_db if x["nombre"] == nombre), None)
#|             nuevos_enf.append({"enfoque": nombre, "valores": ", ".join(e["items"]) if e else "",
#|                                "acciones": st_.get(f"{base}_enf_{k}_{norm(nombre)[:12]}", "")})
#|         return {**d, "titulo": st_.get(f"{base}_tit", d.get("titulo")), "situacion": st_.get(f"{base}_sit", ""),
#|                 "producto": {"evidencia": st_.get(f"{base}_pe", ""), "criterios": st_.get(f"{base}_pc", ""),
#|                              "relacion": st_.get(f"{base}_pr", "")},
#|                 "secuencia": nueva_seq, "propositos": nuevos_props, "enfoques": nuevos_enf}
#|
#|     b1, b2, b3 = st.columns(3)
#|     if b1.button("💾 Guardar unidad", type="primary", key=f"u_save_{aid}_{n}", use_container_width=True):
#|         nuevo = recoger()
#|         guardar_doc(uid, aid, "unidad", n, f"Unidad {n}: {nuevo['titulo']}", nuevo, padre_id=anual["id"])
#|         st.success("Unidad guardada ✅")
#|     if b2.button("🔄 Sincronizar con la anual", key=f"u_sync_{aid}_{n}", use_container_width=True,
#|                  help="Trae de la planificación anual la situación significativa y ajusta las competencias."):
#|         _sincronizar(asig, anual, ua, recoger(), ver_key)
#|     if b3.button("🧩 Crear sesiones de la secuencia", key=f"u_ses_{aid}_{n}", use_container_width=True,
#|                  help="Crea una sesión por cada fila de la secuencia, listas para generar."):
#|         nuevo = recoger()
#|         gid = guardar_doc(uid, aid, "unidad", n, f"Unidad {n}: {nuevo['titulo']}", nuevo, padre_id=anual["id"])
#|         creadas = crear_sesiones_desde_secuencia(uid, asig, get_doc_by_id(gid))
#|         flash(f"Se crearon {creadas} sesión(es). Ahora ve a la pestaña Sesiones.")
#|         st.rerun()
#|
#|     with st.expander("🔎 Revisar coherencia con la planificación anual"):
#|         if confirmar("revision", "Revisar con IA", f"rev_{aid}_{n}"):
#|             try:
#|                 with st.spinner("Revisando..."):
#|                     prompt = (f"{preambulo()}\nRevisa la coherencia de esta unidad con su situación en la planificación anual. "
#|                               f"Anual: título «{ua['titulo']}», competencias {ua['competencias']}, situación: {ua['situacion']}\n"
#|                               f"Unidad: {recoger()}\n"
#|                               "Devuelve hasta 8 observaciones breves en viñetas, empezando con ✅ si está bien o ⚠️ si hay que corregir, "
#|                               "y di cómo corregirlo. No reescribas la unidad.")
#|                     texto, _ = generar_texto(prompt)
#|                 cobrar(uid, "revision")
#|                 st.session_state[f"rev_txt_{aid}_{n}"] = texto
#|             except Exception as e:
#|                 st.error(f"No se pudo revisar: {e}")
#|         if st.session_state.get(f"rev_txt_{aid}_{n}"):
#|             st.markdown(st.session_state[f"rev_txt_{aid}_{n}"])
#|
#|     st.divider()
#|     vista_previa_y_descarga(doc["id"], f"unidad_{aid}_{n}", abierta=False)
#|     if listar_docs(aid, "sesion", padre_id=doc["id"]):
#|         st.button("Siguiente: generar las sesiones →", on_click=ir_a, args=(PAG_SESIONES,), type="primary",
#|                   key=f"u_next_{aid}_{n}")
#|
#|
#| def _sincronizar(asig, anual, ua, actual, ver_key):
#|     """Trae la situación de la anual y alinea las filas de propósitos con las competencias de la unidad anual."""
#|     uid, aid = st.session_state.user_id, asig["id"]
#|     _, mapa = contexto_curricular(asig["nivel"], asig["area"], asig["grado"], ua["competencias"])
#|     props = [p for p in actual.get("propositos", []) if p["competencia"] in mapa]
#|     for nombre, info in mapa.items():
#|         if not any(p["competencia"] == nombre for p in props):
#|             ds = [x["texto"] for x in info["des"][:3]]
#|             props.append({"competencia": nombre, "capacidades": info["comp"]["capacidades"], "desempenos": ds,
#|                           "por_verificar": not ds, "proposito": "", "campo_tematico": "", "evidencia": "",
#|                           "instrumento": ""})
#|     actual["propositos"] = props
#|     actual["situacion"] = ua["situacion"]
#|     guardar_doc(uid, aid, "unidad", ua["numero"], f"Unidad {ua['numero']}: {actual.get('titulo', ua['titulo'])}",
#|                 actual, padre_id=anual["id"])
#|     siguiente_version(ver_key)
#|     flash("Unidad sincronizada con la planificación anual ✅")
#|     st.rerun()
#@@ END
#@@ MODULE v_sesiones
#| """Sesiones de aprendizaje + rúbrica, ficha de trabajo y examen de cada sesión."""
#| import pandas as pd
#| import streamlit as st
#|
#| from ia import pedir_json, preambulo
#| from normativa import normativa_vigente
#| from repo import cobrar, contenido, crear_sesiones_desde_secuencia, get_doc, get_doc_by_id, guardar_doc, listar_docs
#| from ui import (PAG_ANUAL, PAG_UNIDADES, campo_linea, campo_multi, campo_num, campo_texto, confirmar, exigir_area,
#|                 exigir_cadena, flash, siguiente_version, vista_previa_y_descarga)
#| from util import a_lista, a_texto, entero, norm, s
#|
#|
#| # ------------------------------------------------------------------
#| # GENERACIÓN
#| # ------------------------------------------------------------------
#| def generar_sesion(asig, udata, sdata, duracion, comps_sel, notas=""):
#|     props = {p["competencia"]: p for p in udata.get("propositos", [])}
#|     comps_sel = [c for c in comps_sel if c in props] or list(props)[:1]
#|     if not comps_sel:
#|         raise RuntimeError("La unidad no tiene propósitos de aprendizaje. Genera o completa la unidad primero.")
#|     bloque = "\n".join(
#|         f"- {n}\n  Capacidades: {'; '.join(props[n].get('capacidades', []))}\n"
#|         f"  Desempeños: {' | '.join(props[n].get('desempenos', []))}\n  Propósito de la unidad: {props[n].get('proposito', '')}"
#|         for n in comps_sel)
#|     prompt = f"""{preambulo()}
#| Elabora una SESIÓN DE APRENDIZAJE.
#| Datos: nivel {asig['nivel']}, grado {asig['grado']}, área {asig['area']}, región {asig['region']}.
#| Unidad {udata.get('numero')}: {udata.get('titulo')}
#| Situación significativa: {udata.get('situacion')}
#| Título o reto de la sesión: {sdata.get('titulo')}
#| Duración: {duracion} minutos. Indicaciones del docente: {notas or 'ninguna'}
#|
#| Competencias que se trabajan (no cambies su redacción):
#| {bloque}
#|
#| Entrega:
#| - "titulo": título de la sesión (puedes mejorar el propuesto).
#| - "proposito": propósito en lenguaje del estudiante ("Hoy aprenderemos a...").
#| - "competencias": un objeto por competencia: {{"competencia": nombre EXACTO, "criterios": [2 a 3 criterios de evaluación observables], "evidencia": "...", "instrumento": "Lista de cotejo / Rúbrica / Escala de valoración"}}
#| - "inicio": {{"actividades": "motivación, saberes previos, conflicto cognitivo y propósito", "minutos": n}}
#| - "desarrollo": {{"actividades": "pasos detallados de la actividad principal", "minutos": n}}
#| - "cierre": {{"actividades": "síntesis y metacognición", "minutos": n}}
#| - "materiales": lista de materiales y recursos.
#| - "reflexion": 3 preguntas de metacognición.
#| Los minutos de inicio, desarrollo y cierre deben sumar {duracion}."""
#|     ia, _ = pedir_json(prompt)
#|     if not isinstance(ia, dict):
#|         raise RuntimeError("La IA devolvió un formato inesperado. Intenta de nuevo.")
#|     por_ia = {norm(x.get("competencia")): x for x in ia.get("competencias") or [] if isinstance(x, dict)}
#|     filas = []
#|     for nombre in comps_sel:
#|         p, x = props[nombre], por_ia.get(norm(nombre), {})
#|         filas.append({"competencia": nombre, "capacidades": p.get("capacidades", []),
#|                       "desempenos": p.get("desempenos", []), "por_verificar": bool(p.get("por_verificar")),
#|                       "criterios": a_lista(x.get("criterios")), "evidencia": s(x.get("evidencia")),
#|                       "instrumento": s(x.get("instrumento"))})
#|
#|     def momento(k, defecto):
#|         m = ia.get(k) if isinstance(ia.get(k), dict) else {}
#|         return {"actividades": s(m.get("actividades")), "minutos": entero(m.get("minutos"), defecto, 1, 240)}
#|
#|     return {**sdata, "titulo": s(ia.get("titulo")) or sdata.get("titulo", ""), "proposito": s(ia.get("proposito")),
#|             "duracion": int(duracion), "competencias": filas, "inicio": momento("inicio", round(duracion * 0.15)),
#|             "desarrollo": momento("desarrollo", round(duracion * 0.7)), "cierre": momento("cierre", round(duracion * 0.15)),
#|             "materiales": a_lista(ia.get("materiales")), "reflexion": a_lista(ia.get("reflexion")),
#|             "enfoques": udata.get("enfoques", []), "unidad_numero": udata.get("numero")}
#|
#|
#| def _resumen_competencias(sdata):
#|     return "\n".join(f"- {c['competencia']}: criterios {c.get('criterios')}; evidencia: {c.get('evidencia')}"
#|                      for c in sdata.get("competencias", []))
#|
#|
#| # ------------------------------------------------------------------
#| # PANTALLA
#| # ------------------------------------------------------------------
#| def render():
#|     asig = exigir_area()
#|     uid, aid = st.session_state.user_id, asig["id"]
#|     st.title("📝 Sesiones de aprendizaje")
#|     st.info("💡 Elige la unidad y la sesión. En cada sesión tienes 4 pestañas: contenido, rúbrica, ficha y examen.")
#|     if not get_doc(aid, "anual"):
#|         exigir_cadena("Primero crea tu planificación anual.", PAG_ANUAL, "Ir a Planificación anual")
#|     unidades = listar_docs(aid, "unidad")
#|     if not unidades:
#|         exigir_cadena("Primero crea al menos una unidad.", PAG_UNIDADES, "Ir a Unidades")
#|
#|     num = st.radio("Unidad", [u["numero"] for u in unidades], horizontal=True, key=f"se_unidad_{aid}",
#|                    format_func=lambda n: f"Unidad {n}")
#|     udoc = next(u for u in unidades if u["numero"] == num)
#|     udata = contenido(udoc)
#|     sesiones = listar_docs(aid, "sesion", padre_id=udoc["id"])
#|     if not sesiones:
#|         st.warning("Esta unidad todavía no tiene sesiones. Créalas desde la secuencia de la unidad.")
#|         if udata.get("secuencia") and st.button("🧩 Crear sesiones de la secuencia", type="primary", key=f"se_crear_{udoc['id']}"):
#|             creadas = crear_sesiones_desde_secuencia(uid, asig, udoc)
#|             flash(f"Se crearon {creadas} sesión(es).")
#|             st.rerun()
#|         st.stop()
#|
#|     def etiqueta(i):
#|         sd = contenido(sesiones[i])
#|         return f"{'✅' if sd.get('inicio') else '⬜'} Sesión {sesiones[i]['numero']}: {sd.get('titulo', '')}"
#|
#|     _masivo(asig, udoc, udata, sesiones)
#|
#|     idx = st.selectbox("Sesión", list(range(len(sesiones))), format_func=etiqueta, key=f"se_sel_{udoc['id']}")
#|     sdoc = sesiones[idx]
#|     t1, t2, t3, t4 = st.tabs(["📖 Contenido de sesión", "📊 Rúbrica", "📄 Ficha de trabajo", "📋 Examen"])
#|     with t1:
#|         _tab_contenido(asig, udoc, udata, sdoc)
#|     with t2:
#|         _tab_rubrica(asig, sdoc)
#|     with t3:
#|         _tab_ficha(asig, sdoc)
#|     with t4:
#|         _tab_examen(asig, sdoc)
#|
#|
#| def _masivo(asig, udoc, udata, sesiones):
#|     uid = st.session_state.user_id
#|     faltan = [x for x in sesiones if not contenido(x).get("inicio")]
#|     with st.expander(f"⚡ Generar todas las sesiones de la unidad ({len(faltan)} pendientes)"):
#|         if not faltan:
#|             st.success("Todas las sesiones de esta unidad ya tienen contenido.")
#|             return
#|         dur = st.number_input("Duración de cada sesión (minutos)", 20, 240, 90, step=5, key=f"mas_dur_{udoc['id']}")
#|         if confirmar("sesion", f"Generar las {len(faltan)} sesiones", f"mas_{udoc['id']}", veces=len(faltan)):
#|             barra = st.progress(0.0)
#|             hechas = 0
#|             for k, sdoc in enumerate(faltan, 1):
#|                 sd = contenido(sdoc)
#|                 try:
#|                     nuevo = generar_sesion(asig, udata, sd, int(dur), sd.get("competencias_sugeridas") or [])
#|                     guardar_doc(uid, asig["id"], "sesion", sdoc["numero"], f"Sesión {sdoc['numero']}: {nuevo['titulo']}",
#|                                 nuevo, padre_id=udoc["id"], normativa=normativa_vigente()[1])
#|                     cobrar(uid, "sesion")
#|                     hechas += 1
#|                 except Exception as e:
#|                     st.error(f"Se detuvo en la sesión {sdoc['numero']}: {e}")
#|                     break
#|                 barra.progress(k / len(faltan))
#|             flash(f"Se generaron {hechas} sesión(es) ✅")
#|             st.rerun()
#|
#|
#| # ------------------------------------------------------------------
#| # PESTAÑA 1: CONTENIDO
#| # ------------------------------------------------------------------
#| def _tab_contenido(asig, udoc, udata, sdoc):
#|     uid, aid = st.session_state.user_id, asig["id"]
#|     d = contenido(sdoc)
#|     ver_key = f"ver_ses_{sdoc['id']}"
#|     ver = st.session_state.get(ver_key, 0)
#|     props = [p["competencia"] for p in udata.get("propositos", [])]
#|
#|     c1, c2 = st.columns(2)
#|     duracion = c1.number_input("Duración (minutos)", 20, 240, entero(d.get("duracion"), 90, 20, 240), step=5,
#|                                key=f"ses_dur_{sdoc['id']}_{ver}")
#|     sel = c2.multiselect("Competencias de esta sesión", props,
#|                          default=[x for x in (d.get("competencias_sugeridas") or props[:1]) if x in props],
#|                          key=f"ses_comp_{sdoc['id']}_{ver}")
#|     notas = st.text_input("Indicaciones especiales (opcional)", key=f"ses_notas_{sdoc['id']}_{ver}",
#|                           placeholder="Ej.: aula multigrado, sin proyector, usar material reciclable")
#|     etiqueta = "✨ Generar sesión con IA" if not d.get("inicio") else "🔄 Volver a generar (reemplaza lo actual)"
#|     if confirmar("sesion", etiqueta, f"ses_{sdoc['id']}"):
#|         try:
#|             with st.spinner("Creando la sesión..."):
#|                 nuevo = generar_sesion(asig, udata, d, int(duracion), sel, notas)
#|             guardar_doc(uid, aid, "sesion", sdoc["numero"], f"Sesión {sdoc['numero']}: {nuevo['titulo']}", nuevo,
#|                         padre_id=udoc["id"], normativa=normativa_vigente()[1])
#|             cobrar(uid, "sesion")
#|             siguiente_version(ver_key)
#|             flash("¡Sesión lista! Revísala y ajústala.")
#|             st.rerun()
#|         except Exception as e:
#|             st.error(f"No se pudo generar: {e}")
#|
#|     if not d.get("inicio"):
#|         st.caption("Aún no hay contenido en esta sesión.")
#|         return
#|
#|     base = f"s_{sdoc['id']}_{ver}"
#|     campo_linea("Título de la sesión", f"{base}_tit", d.get("titulo", ""))
#|     campo_texto("Propósito de aprendizaje", f"{base}_pro", d.get("proposito", ""), 80)
#|     filas = d.get("competencias", [])
#|     for j, c in enumerate(filas):
#|         with st.expander(f"Competencia: {c['competencia']}", expanded=(j == 0)):
#|             if c.get("por_verificar"):
#|                 st.caption("⚠️ Desempeños por verificar con el Programa Curricular oficial.")
#|             campo_texto("Criterios de evaluación (uno por línea)", f"{base}_c{j}_cr", a_texto(c.get("criterios")), 100)
#|             campo_texto("Evidencia de aprendizaje", f"{base}_c{j}_ev", c.get("evidencia", ""), 70)
#|             campo_linea("Instrumento", f"{base}_c{j}_in", c.get("instrumento", ""))
#|     st.markdown("**Secuencia didáctica**")
#|     for k, nombre in (("inicio", "Inicio"), ("desarrollo", "Desarrollo"), ("cierre", "Cierre")):
#|         m = d.get(k) or {}
#|         campo_texto(f"{nombre}", f"{base}_{k}_a", m.get("actividades", ""), 140 if k == "desarrollo" else 100)
#|         campo_num(f"Minutos de {nombre.lower()}", f"{base}_{k}_m", 1, 240, entero(m.get("minutos"), 10))
#|     campo_texto("Materiales y recursos (uno por línea)", f"{base}_mat", a_texto(d.get("materiales")), 90)
#|     campo_texto("Reflexión sobre el aprendizaje (una pregunta por línea)", f"{base}_ref", a_texto(d.get("reflexion")), 90)
#|
#|     if st.button("💾 Guardar sesión", type="primary", key=f"s_save_{sdoc['id']}"):
#|         ss = st.session_state
#|         nuevas = [{**c, "criterios": a_lista(ss.get(f"{base}_c{j}_cr")), "evidencia": ss.get(f"{base}_c{j}_ev", ""),
#|                    "instrumento": ss.get(f"{base}_c{j}_in", "")} for j, c in enumerate(filas)]
#|         nuevo = {**d, "titulo": ss.get(f"{base}_tit", ""), "proposito": ss.get(f"{base}_pro", ""), "competencias": nuevas,
#|                  "materiales": a_lista(ss.get(f"{base}_mat")), "reflexion": a_lista(ss.get(f"{base}_ref"))}
#|         for k in ("inicio", "desarrollo", "cierre"):
#|             nuevo[k] = {"actividades": ss.get(f"{base}_{k}_a", ""), "minutos": entero(ss.get(f"{base}_{k}_m"), 10, 1, 240)}
#|         guardar_doc(uid, aid, "sesion", sdoc["numero"], f"Sesión {sdoc['numero']}: {nuevo['titulo']}", nuevo,
#|                     padre_id=udoc["id"])
#|         st.success("Sesión guardada ✅")
#|     st.divider()
#|     vista_previa_y_descarga(sdoc["id"], f"sesion_{sdoc['id']}", abierta=False)
#|
#|
#| # ------------------------------------------------------------------
#| # PESTAÑAS 2-4: MATERIALES (rúbrica, ficha, examen)
#| # ------------------------------------------------------------------
#| def _necesita_sesion(sdoc):
#|     sd = contenido(sdoc)
#|     if not sd.get("inicio"):
#|         st.info("Primero genera el **contenido de la sesión** (pestaña 1); de ahí salen los criterios y las evidencias.")
#|         return None
#|     return sd
#|
#|
#| def _tabla(filas, columnas, clave, config=None):
#|     df = pd.DataFrame(filas, columns=columnas)
#|     return st.data_editor(df, key=clave, num_rows="dynamic", hide_index=True, column_config=config or {}).fillna("")
#|
#|
#| def _tab_rubrica(asig, sdoc):
#|     sd = _necesita_sesion(sdoc)
#|     if not sd:
#|         return
#|     uid, aid = st.session_state.user_id, asig["id"]
#|     doc = get_doc(aid, "rubrica", padre_id=sdoc["id"])
#|     d = contenido(doc) if doc else {}
#|     ver_key = f"ver_rub_{sdoc['id']}"
#|     ver = st.session_state.get(ver_key, 0)
#|     if confirmar("rubrica", "✨ Generar rúbrica con IA" if not doc else "🔄 Volver a generar la rúbrica", f"rub_{sdoc['id']}"):
#|         try:
#|             prompt = f"""{preambulo()}
#| Elabora una RÚBRICA de evaluación para esta sesión (nivel {asig['nivel']}, grado {asig['grado']}, área {asig['area']}).
#| Sesión: {sd.get('titulo')}
#| Competencias, criterios y evidencias:
#| {_resumen_competencias(sd)}
#| Entrega entre 3 y 5 criterios (puedes partir de los criterios dados). Para cada uno describe lo observable en cuatro niveles: AD (logro destacado), A (logro esperado), B (en proceso), C (en inicio).
#| Formato: {{"criterios":[{{"criterio":"...","AD":"...","A":"...","B":"...","C":"..."}}]}}"""
#|             with st.spinner("Creando la rúbrica..."):
#|                 ia, _ = pedir_json(prompt)
#|             lista = ia.get("criterios") if isinstance(ia, dict) else ia
#|             filas = [{"criterio": s(r.get("criterio")), "AD": s(r.get("AD")), "A": s(r.get("A")), "B": s(r.get("B")),
#|                       "C": s(r.get("C"))} for r in (lista or []) if isinstance(r, dict)]
#|             if not filas:
#|                 raise RuntimeError("La IA no devolvió criterios. Intenta de nuevo.")
#|             guardar_doc(uid, aid, "rubrica", 1, f"Rúbrica: {sd.get('titulo')}", {"criterios": filas},
#|                         padre_id=sdoc["id"], normativa=normativa_vigente()[1])
#|             cobrar(uid, "rubrica")
#|             siguiente_version(ver_key)
#|             flash("Rúbrica lista ✅")
#|             st.rerun()
#|         except Exception as e:
#|             st.error(f"No se pudo generar: {e}")
#|     if not doc:
#|         return
#|     ed = _tabla(d.get("criterios", []), ["criterio", "AD", "A", "B", "C"], f"rub_ed_{sdoc['id']}_{ver}", {
#|         "criterio": st.column_config.TextColumn("Criterio", width="medium"),
#|         "AD": st.column_config.TextColumn("AD · Destacado", width="medium"),
#|         "A": st.column_config.TextColumn("A · Esperado", width="medium"),
#|         "B": st.column_config.TextColumn("B · En proceso", width="medium"),
#|         "C": st.column_config.TextColumn("C · En inicio", width="medium")})
#|     if st.button("💾 Guardar rúbrica", type="primary", key=f"rub_save_{sdoc['id']}"):
#|         filas = [{k: s(r[k]) for k in ("criterio", "AD", "A", "B", "C")} for _, r in ed.iterrows() if s(r["criterio"])]
#|         guardar_doc(uid, aid, "rubrica", 1, doc["titulo"], {"criterios": filas}, padre_id=sdoc["id"])
#|         st.success("Rúbrica guardada ✅")
#|     st.divider()
#|     vista_previa_y_descarga(doc["id"], f"rub_{sdoc['id']}", abierta=False)
#|
#|
#| def _tab_ficha(asig, sdoc):
#|     sd = _necesita_sesion(sdoc)
#|     if not sd:
#|         return
#|     uid, aid = st.session_state.user_id, asig["id"]
#|     doc = get_doc(aid, "ficha", padre_id=sdoc["id"])
#|     d = contenido(doc) if doc else {}
#|     ver_key = f"ver_fic_{sdoc['id']}"
#|     ver = st.session_state.get(ver_key, 0)
#|     n_act = st.number_input("Número de actividades", 3, 12, 6, key=f"fic_n_{sdoc['id']}")
#|     if confirmar("ficha", "✨ Generar ficha con IA" if not doc else "🔄 Volver a generar la ficha", f"fic_{sdoc['id']}"):
#|         try:
#|             prompt = f"""{preambulo()}
#| Elabora una FICHA DE TRABAJO para estudiantes de {asig['grado']} ({asig['nivel']}), área {asig['area']}, región {asig['region']}.
#| Sesión: {sd.get('titulo')}. Propósito: {sd.get('proposito')}
#| Competencias y criterios:
#| {_resumen_competencias(sd)}
#| Entrega {int(n_act)} actividades graduadas (de lo simple a lo complejo), con lenguaje adecuado a la edad y contexto cercano a la región. Cada actividad incluye la respuesta esperada para el docente.
#| Formato: {{"titulo":"...","instrucciones":"...","actividades":[{{"numero":1,"consigna":"...","respuesta":"..."}}]}}"""
#|             with st.spinner("Creando la ficha..."):
#|                 ia, _ = pedir_json(prompt)
#|             acts = [{"numero": i, "consigna": s(a.get("consigna")), "respuesta": s(a.get("respuesta"))}
#|                     for i, a in enumerate((ia.get("actividades") if isinstance(ia, dict) else []) or [], 1) if isinstance(a, dict)]
#|             if not acts:
#|                 raise RuntimeError("La IA no devolvió actividades. Intenta de nuevo.")
#|             guardar_doc(uid, aid, "ficha", 1, f"Ficha: {sd.get('titulo')}",
#|                         {"titulo": s(ia.get("titulo")), "instrucciones": s(ia.get("instrucciones")), "actividades": acts},
#|                         padre_id=sdoc["id"], normativa=normativa_vigente()[1])
#|             cobrar(uid, "ficha")
#|             siguiente_version(ver_key)
#|             flash("Ficha lista ✅")
#|             st.rerun()
#|         except Exception as e:
#|             st.error(f"No se pudo generar: {e}")
#|     if not doc:
#|         return
#|     base = f"fic_{sdoc['id']}_{ver}"
#|     campo_linea("Título de la ficha", f"{base}_t", d.get("titulo", ""))
#|     campo_texto("Indicaciones", f"{base}_i", d.get("instrucciones", ""), 80)
#|     ed = _tabla(d.get("actividades", []), ["numero", "consigna", "respuesta"], f"{base}_ed", {
#|         "numero": st.column_config.NumberColumn("N.°", step=1),
#|         "consigna": st.column_config.TextColumn("Consigna", width="large"),
#|         "respuesta": st.column_config.TextColumn("Respuesta esperada (docente)", width="medium")})
#|     if st.button("💾 Guardar ficha", type="primary", key=f"fic_save_{sdoc['id']}"):
#|         acts = [{"numero": k, "consigna": s(r["consigna"]), "respuesta": s(r["respuesta"])}
#|                 for k, (_, r) in enumerate(ed.iterrows(), 1) if s(r["consigna"])]
#|         guardar_doc(uid, aid, "ficha", 1, doc["titulo"],
#|                     {"titulo": st.session_state.get(f"{base}_t", ""), "instrucciones": st.session_state.get(f"{base}_i", ""),
#|                      "actividades": acts}, padre_id=sdoc["id"])
#|         st.success("Ficha guardada ✅")
#|     st.divider()
#|     vista_previa_y_descarga(doc["id"], f"fic_{sdoc['id']}", abierta=False)
#|
#|
#| def _tab_examen(asig, sdoc):
#|     sd = _necesita_sesion(sdoc)
#|     if not sd:
#|         return
#|     uid, aid = st.session_state.user_id, asig["id"]
#|     doc = get_doc(aid, "examen", padre_id=sdoc["id"])
#|     d = contenido(doc) if doc else {}
#|     ver_key = f"ver_exa_{sdoc['id']}"
#|     ver = st.session_state.get(ver_key, 0)
#|     c1, c2, c3 = st.columns(3)
#|     n_preg = c1.number_input("Número de preguntas", 3, 20, 8, key=f"exa_n_{sdoc['id']}")
#|     tipos = c2.selectbox("Tipo de preguntas", ["Mixto", "Solo opción múltiple", "Solo desarrollo"], key=f"exa_t_{sdoc['id']}")
#|     total = c3.number_input("Puntaje total", 5, 100, 20, key=f"exa_p_{sdoc['id']}")
#|     if confirmar("examen", "✨ Generar examen con IA" if not doc else "🔄 Volver a generar el examen", f"exa_{sdoc['id']}"):
#|         try:
#|             prompt = f"""{preambulo()}
#| Elabora un EXAMEN para estudiantes de {asig['grado']} ({asig['nivel']}), área {asig['area']}.
#| Sesión: {sd.get('titulo')}
#| Competencias y criterios:
#| {_resumen_competencias(sd)}
#| Número de preguntas: {int(n_preg)}. Tipo: {tipos}. Puntaje total: {int(total)} (los puntajes de las preguntas deben sumar exactamente {int(total)}).
#| Para "opcion_multiple": 4 opciones escritas como "a) ...", "b) ...", y "respuesta" con la letra correcta. Para "desarrollo": "opciones" vacía y "respuesta" con la respuesta esperada.
#| Formato: {{"titulo":"...","instrucciones":"...","preguntas":[{{"numero":1,"tipo":"opcion_multiple","enunciado":"...","opciones":["a) ...","b) ...","c) ...","d) ..."],"respuesta":"b","puntaje":2}}]}}"""
#|             with st.spinner("Creando el examen..."):
#|                 ia, _ = pedir_json(prompt)
#|             pregs = []
#|             for i, p in enumerate((ia.get("preguntas") if isinstance(ia, dict) else []) or [], 1):
#|                 if isinstance(p, dict):
#|                     pregs.append({"numero": i, "tipo": s(p.get("tipo")) or "desarrollo", "enunciado": s(p.get("enunciado")),
#|                                   "opciones": a_lista(p.get("opciones")), "respuesta": s(p.get("respuesta")),
#|                                   "puntaje": s(p.get("puntaje")) or "1"})
#|             if not pregs:
#|                 raise RuntimeError("La IA no devolvió preguntas. Intenta de nuevo.")
#|             guardar_doc(uid, aid, "examen", 1, f"Examen: {sd.get('titulo')}",
#|                         {"titulo": s(ia.get("titulo")), "instrucciones": s(ia.get("instrucciones")), "preguntas": pregs},
#|                         padre_id=sdoc["id"], normativa=normativa_vigente()[1])
#|             cobrar(uid, "examen")
#|             siguiente_version(ver_key)
#|             flash("Examen listo ✅")
#|             st.rerun()
#|         except Exception as e:
#|             st.error(f"No se pudo generar: {e}")
#|     if not doc:
#|         return
#|     base = f"exa_{sdoc['id']}_{ver}"
#|     campo_linea("Título del examen", f"{base}_t", d.get("titulo", ""))
#|     campo_texto("Indicaciones", f"{base}_i", d.get("instrucciones", ""), 80)
#|     filas = [{"numero": p.get("numero"), "tipo": p.get("tipo"), "enunciado": p.get("enunciado"),
#|               "opciones": " | ".join(p.get("opciones") or []), "respuesta": p.get("respuesta"), "puntaje": p.get("puntaje")}
#|              for p in d.get("preguntas", [])]
#|     ed = _tabla(filas, ["numero", "tipo", "enunciado", "opciones", "respuesta", "puntaje"], f"{base}_ed", {
#|         "numero": st.column_config.NumberColumn("N.°", step=1),
#|         "tipo": st.column_config.SelectboxColumn("Tipo", options=["opcion_multiple", "desarrollo", "verdadero_falso"]),
#|         "enunciado": st.column_config.TextColumn("Enunciado", width="large"),
#|         "opciones": st.column_config.TextColumn("Opciones (separadas por |)", width="large"),
#|         "respuesta": st.column_config.TextColumn("Respuesta"),
#|         "puntaje": st.column_config.TextColumn("Puntaje")})
#|     if st.button("💾 Guardar examen", type="primary", key=f"exa_save_{sdoc['id']}"):
#|         pregs = []
#|         for k, (_, r) in enumerate(ed.iterrows(), 1):
#|             if s(r["enunciado"]):
#|                 pregs.append({"numero": k, "tipo": s(r["tipo"]) or "desarrollo", "enunciado": s(r["enunciado"]),
#|                               "opciones": [x.strip() for x in s(r["opciones"]).split("|") if x.strip()],
#|                               "respuesta": s(r["respuesta"]), "puntaje": s(r["puntaje"]) or "1"})
#|         guardar_doc(uid, aid, "examen", 1, doc["titulo"],
#|                     {"titulo": st.session_state.get(f"{base}_t", ""), "instrucciones": st.session_state.get(f"{base}_i", ""),
#|                      "preguntas": pregs}, padre_id=sdoc["id"])
#|         st.success("Examen guardado ✅")
#|     st.divider()
#|     vista_previa_y_descarga(doc["id"], f"exa_{sdoc['id']}", abierta=False)
#@@ END
#@@ MODULE v_biblioteca
#| """Mi Biblioteca: todos tus documentos ordenados por área y grado."""
#| import streamlit as st
#|
#| from db import fetch
#| from exportar import bloques_de
#| from repo import borrar_doc, get_asignacion, listar_asignaciones, listar_docs
#| from render import COLOR_DEFECTO, a_docx, texto_a_docx
#| from ui import MIME_DOCX, PAG_ANUAL, PAG_SESIONES, PAG_UNIDADES, abrir_area, flash
#|
#| TIPOS = {"anual": ("📅", "Planificación anual", PAG_ANUAL), "unidad": ("📚", "Unidad", PAG_UNIDADES),
#|          "sesion": ("📝", "Sesión", PAG_SESIONES), "rubrica": ("📊", "Rúbrica", PAG_SESIONES),
#|          "ficha": ("📄", "Ficha", PAG_SESIONES), "examen": ("📋", "Examen", PAG_SESIONES)}
#| ORDEN = {"anual": 0, "unidad": 1, "sesion": 2, "rubrica": 3, "ficha": 4, "examen": 5}
#|
#|
#| def render():
#|     uid = st.session_state.user_id
#|     st.title("🗂️ Mi Biblioteca")
#|     st.caption("Todos tus documentos, organizados por área y grado. Descárgalos en Word cuando los necesites.")
#|     asigs = listar_asignaciones(uid)
#|     if not asigs:
#|         st.info("Cuando crees documentos aparecerán aquí.")
#|     filtro = st.selectbox("Mostrar", ["Todos los documentos"] + list(TIPOS), key="bib_filtro",
#|                           format_func=lambda k: k if k.startswith("Todos") else f"{TIPOS[k][0]} {TIPOS[k][1]}")
#|     for a in asigs:
#|         docs = listar_docs(a["id"], None if filtro.startswith("Todos") else filtro)
#|         docs.sort(key=lambda d: (ORDEN.get(d["tipo"], 9), d["numero"], d["id"]))
#|         titulo = f"{a['area']} · {a['grado']} · Sección {a['seccion'] or '—'}  ({len(docs)} documentos)"
#|         with st.expander(titulo, expanded=len(asigs) == 1):
#|             if not docs:
#|                 st.caption("Todavía no hay documentos en esta área.")
#|             for d in docs:
#|                 icono, nombre, pagina = TIPOS.get(d["tipo"], ("📄", d["tipo"], PAG_ANUAL))
#|                 c1, c2, c3, c4 = st.columns([5, 2, 2, 1])
#|                 c1.markdown(f"{icono} **{nombre}** — {d['titulo'] or ''}")
#|                 c1.caption(f"Actualizado: {d['actualizado_en']:%d/%m/%Y %H:%M}")
#|                 kb = f"bib_bytes_{d['id']}"
#|                 if c2.button("📄 Preparar Word", key=f"prep_{d['id']}"):
#|                     bloques, horizontal, archivo = bloques_de(d)
#|                     st.session_state[kb] = (a_docx(bloques, d.get("color") or COLOR_DEFECTO, d.get("normativa_usada"),
#|                                                    horizontal), archivo)
#|                 if kb in st.session_state:
#|                     datos, archivo = st.session_state[kb]
#|                     c2.download_button("⬇️ Descargar", data=datos, file_name=archivo, mime=MIME_DOCX, key=f"dlb_{d['id']}")
#|                 c3.button("Abrir área", key=f"op_{d['id']}", on_click=abrir_area, args=(a["id"], pagina))
#|                 if c4.button("🗑️", key=f"del_{d['id']}", help="Eliminar (también lo que depende de él)"):
#|                     st.session_state[f"_del_{d['id']}"] = True
#|                 if st.session_state.get(f"_del_{d['id']}"):
#|                     st.warning("¿Eliminar este documento y lo que depende de él? No se puede deshacer.")
#|                     y, n = st.columns(2)
#|                     if y.button("Sí, eliminar", key=f"dely_{d['id']}"):
#|                         borrar_doc(d["id"])
#|                         st.session_state.pop(f"_del_{d['id']}", None)
#|                         flash("Documento eliminado.")
#|                         st.rerun()
#|                     if n.button("Cancelar", key=f"deln_{d['id']}"):
#|                         st.session_state.pop(f"_del_{d['id']}", None)
#|                         st.rerun()
#|
#|     antiguos = fetch("SELECT id, titulo, contenido_texto, normativa_usada, creado_en FROM planificaciones "
#|                      "WHERE usuario_id=%s ORDER BY creado_en DESC LIMIT 30", (uid,))
#|     if antiguos:
#|         with st.expander(f"🕰️ Documentos del generador anterior ({len(antiguos)})"):
#|             for d in antiguos:
#|                 st.markdown(f"**{d['titulo']}** · {d['creado_en']:%d/%m/%Y}")
#|                 st.download_button("⬇️ Word", data=texto_a_docx(d["titulo"], d["contenido_texto"], d["normativa_usada"]),
#|                                    file_name=f"documento_{d['id']}.docx", mime=MIME_DOCX, key=f"old_{d['id']}")
#@@ END
#@@ MODULE v_admin
#| """Administración: resumen, usuarios, colegios, currículo, normativa MINEDU y costos."""
#| import io
#|
#| import mysql.connector
#| import pandas as pd
#| import streamlit as st
#|
#| from auth import hash_password
#| from curriculo import (CICLOS, GRADOS, NIVELES, areas_de, competencias_de, desempenos_de, limpiar_cache,
#|                        sembrar_curriculo, transversales)
#| from db import conexion, execute as db_execute, execute_many, fetch as db_fetch
#| from normativa import revisar_fuente
#| from repo import COSTOS_DEFAULT, NOMBRES_COSTO, config_get, config_set, costo_de, mapa_colegios
#| from util import a_lista, entero, norm, s
#|
#| ROLES = ["docente", "director", "admin"]
#| TIPOS_NORMA = ["curricular", "pedagógico/normativo", "administrativo"]
#|
#|
#| def render(admin_id):
#|     st.title("⚙️ Administración")
#|     t = st.tabs(["📊 Resumen", "👥 Usuarios", "🏫 Colegios", "🎓 Currículo", "📜 Normativa MINEDU", "🎟️ Costos"])
#|     with t[0]:
#|         panel_resumen()
#|     with t[1]:
#|         panel_usuarios(admin_id)
#|     with t[2]:
#|         panel_colegios()
#|     with t[3]:
#|         panel_curriculo()
#|     with t[4]:
#|         panel_normativa(admin_id)
#|     with t[5]:
#|         panel_costos()
#|
#|
#| # ------------------------------------------------------------------
#| def panel_resumen():
#|     st.subheader("Resumen")
#|     n = lambda sql: db_fetch(sql, one=True)["n"]
#|     c1, c2, c3, c4, c5 = st.columns(5)
#|     c1.metric("Usuarios", n("SELECT COUNT(*) AS n FROM usuarios"))
#|     c2.metric("Colegios", n("SELECT COUNT(*) AS n FROM colegios"))
#|     c3.metric("Documentos", n("SELECT COUNT(*) AS n FROM documentos"))
#|     c4.metric("Áreas asignadas", n("SELECT COUNT(*) AS n FROM asignaciones"))
#|     c5.metric("Normativa pendiente", n("SELECT COUNT(*) AS n FROM normativa_versiones WHERE estado='pendiente'"))
#|     st.markdown("#### Últimos documentos de todos los usuarios")
#|     docs = db_fetch("SELECT d.id, u.nombre AS usuario, d.tipo, d.titulo, d.normativa_usada AS normativa, d.actualizado_en "
#|                     "FROM documentos d LEFT JOIN usuarios u ON u.id = d.usuario_id ORDER BY d.actualizado_en DESC LIMIT 30")
#|     if docs:
#|         st.dataframe(pd.DataFrame(docs), hide_index=True)
#|     else:
#|         st.info("Todavía no hay documentos.")
#|
#|
#| # ------------------------------------------------------------------
#| def panel_usuarios(admin_id):
#|     st.subheader("Usuarios")
#|     filas = db_fetch(
#|         "SELECT u.id, u.nombre, u.correo, u.rol, u.colegio_id, c.nombre AS colegio, u.nivel_educativo AS nivel, "
#|         "u.creditos, u.activo, u.creado_en FROM usuarios u LEFT JOIN colegios c ON c.id = u.colegio_id ORDER BY u.id DESC")
#|     colegios = mapa_colegios(solo_activos=False)
#|     claves_col = list(colegios.keys())
#|     if filas:
#|         st.dataframe(pd.DataFrame(filas).drop(columns=["colegio_id"]), hide_index=True)
#|
#|     with st.expander("➕ Crear usuario"):
#|         with st.form("crear_usuario", clear_on_submit=True):
#|             c1, c2 = st.columns(2)
#|             nombre = c1.text_input("Nombre completo")
#|             correo = c2.text_input("Correo electrónico")
#|             pw = c1.text_input("Contraseña inicial (mínimo 8)", type="password")
#|             rol = c2.selectbox("Rol", ROLES)
#|             colegio = c1.selectbox("Colegio", claves_col, format_func=lambda k: colegios[k])
#|             nivel_u = c2.selectbox("Nivel", NIVELES)
#|             cred = c1.number_input("Créditos", min_value=0, max_value=100000, value=50)
#|             enviar = st.form_submit_button("Crear usuario", type="primary")
#|         if enviar:
#|             if not (nombre and correo and pw):
#|                 st.warning("Completa nombre, correo y contraseña.")
#|             elif len(pw) < 8:
#|                 st.warning("La contraseña debe tener al menos 8 caracteres.")
#|             else:
#|                 try:
#|                     db_execute("INSERT INTO usuarios (nombre, correo, password_hash, rol, colegio_id, colegio, nivel_educativo, creditos) "
#|                                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
#|                                (nombre.strip(), correo.strip().lower(), hash_password(pw), rol, colegio or None,
#|                                 colegios[colegio] if colegio else "Independiente", nivel_u, cred))
#|                     st.success("Usuario creado.")
#|                     st.rerun()
#|                 except mysql.connector.Error as err:
#|                     st.error("Ese correo ya existe." if err.errno == 1062 else "No se pudo crear el usuario.")
#|
#|     if filas:
#|         st.markdown("#### Editar o eliminar")
#|         opciones = {u["id"]: f"{u['id']} · {u['nombre']} · {u['correo']}" for u in filas}
#|         uid = st.selectbox("Usuario", list(opciones.keys()), format_func=lambda k: opciones[k], key="adm_user_sel")
#|         u = next(x for x in filas if x["id"] == uid)
#|         with st.form(f"edit_user_{uid}"):
#|             c1, c2 = st.columns(2)
#|             e_nombre = c1.text_input("Nombre", u["nombre"], key=f"en_{uid}")
#|             e_rol = c2.selectbox("Rol", ROLES, index=ROLES.index(u["rol"]) if u["rol"] in ROLES else 0, key=f"er_{uid}")
#|             actual = u["colegio_id"] or 0
#|             e_col = c1.selectbox("Colegio", claves_col, index=claves_col.index(actual) if actual in claves_col else 0,
#|                                  format_func=lambda k: colegios[k], key=f"ec_{uid}")
#|             e_cred = c2.number_input("Créditos", 0, 100000, int(u["creditos"] or 0), key=f"ecr_{uid}")
#|             e_activo = c1.checkbox("Cuenta activa", bool(u["activo"]), key=f"ea_{uid}")
#|             e_pw = c2.text_input("Nueva contraseña (opcional)", type="password", key=f"ep_{uid}")
#|             guardar = st.form_submit_button("Guardar cambios", type="primary")
#|         if guardar:
#|             if uid == admin_id and (e_rol != "admin" or not e_activo):
#|                 st.error("No puedes quitarte el rol de admin ni desactivarte a ti mismo.")
#|             elif e_pw and len(e_pw) < 8:
#|                 st.warning("La nueva contraseña debe tener al menos 8 caracteres.")
#|             else:
#|                 db_execute("UPDATE usuarios SET nombre=%s, rol=%s, colegio_id=%s, colegio=%s, creditos=%s, activo=%s WHERE id=%s",
#|                            (e_nombre.strip(), e_rol, e_col or None, colegios[e_col] if e_col else "Independiente",
#|                             e_cred, 1 if e_activo else 0, uid))
#|                 if e_pw:
#|                     db_execute("UPDATE usuarios SET password_hash=%s WHERE id=%s", (hash_password(e_pw), uid))
#|                 st.success("Cambios guardados.")
#|                 st.rerun()
#|         with st.expander("🗑️ Eliminar este usuario"):
#|             st.caption("También se eliminan sus áreas y documentos.")
#|             ok = st.checkbox("Confirmo que quiero eliminarlo", key=f"cd_{uid}")
#|             if st.button("Eliminar usuario", key=f"del_{uid}"):
#|                 if uid == admin_id:
#|                     st.error("No puedes eliminarte a ti mismo.")
#|                 elif not ok:
#|                     st.warning("Marca la confirmación primero.")
#|                 else:
#|                     db_execute("DELETE FROM documentos WHERE usuario_id=%s", (uid,))
#|                     db_execute("DELETE FROM asignaciones WHERE usuario_id=%s", (uid,))
#|                     db_execute("DELETE FROM planificaciones WHERE usuario_id=%s", (uid,))
#|                     db_execute("DELETE FROM usuarios WHERE id=%s", (uid,))
#|                     st.success("Usuario eliminado.")
#|                     st.rerun()
#|
#|
#| # ------------------------------------------------------------------
#| def panel_colegios():
#|     st.subheader("Colegios")
#|     from curriculo import REGIONES
#|     filas = db_fetch("SELECT c.id, c.nombre, c.codigo_modular, c.region, c.ugel, c.activo, "
#|                      "(SELECT COUNT(*) FROM usuarios u WHERE u.colegio_id = c.id) AS usuarios FROM colegios c ORDER BY c.nombre")
#|     if filas:
#|         st.dataframe(pd.DataFrame(filas), hide_index=True)
#|     else:
#|         st.info("Aún no hay colegios registrados.")
#|     with st.expander("➕ Crear colegio"):
#|         with st.form("crear_colegio", clear_on_submit=True):
#|             c1, c2 = st.columns(2)
#|             nombre = c1.text_input("Nombre de la institución")
#|             codigo = c2.text_input("Código modular (opcional)")
#|             reg = c1.selectbox("Región", REGIONES, index=REGIONES.index("Lima"))
#|             ugel = c2.text_input("UGEL (opcional)")
#|             enviar = st.form_submit_button("Crear colegio", type="primary")
#|         if enviar:
#|             if not nombre.strip():
#|                 st.warning("Escribe el nombre del colegio.")
#|             else:
#|                 db_execute("INSERT INTO colegios (nombre, codigo_modular, region, ugel) VALUES (%s,%s,%s,%s)",
#|                            (nombre.strip(), codigo.strip(), reg, ugel.strip()))
#|                 st.success("Colegio creado.")
#|                 st.rerun()
#|     if filas:
#|         st.markdown("#### Editar o eliminar")
#|         opciones = {c["id"]: f"{c['id']} · {c['nombre']}" for c in filas}
#|         cid = st.selectbox("Colegio", list(opciones.keys()), format_func=lambda k: opciones[k], key="adm_col_sel")
#|         c = next(x for x in filas if x["id"] == cid)
#|         with st.form(f"edit_col_{cid}"):
#|             c1, c2 = st.columns(2)
#|             e_nombre = c1.text_input("Nombre", c["nombre"], key=f"cn_{cid}")
#|             e_codigo = c2.text_input("Código modular", c["codigo_modular"] or "", key=f"cc_{cid}")
#|             e_reg = c1.selectbox("Región", REGIONES, index=REGIONES.index(c["region"]) if c["region"] in REGIONES
#|                                  else REGIONES.index("Lima"), key=f"cr_{cid}")
#|             e_ugel = c2.text_input("UGEL", c["ugel"] or "", key=f"cu_{cid}")
#|             e_activo = c1.checkbox("Activo", bool(c["activo"]), key=f"ca_{cid}")
#|             guardar = st.form_submit_button("Guardar cambios", type="primary")
#|         if guardar:
#|             db_execute("UPDATE colegios SET nombre=%s, codigo_modular=%s, region=%s, ugel=%s, activo=%s WHERE id=%s",
#|                        (e_nombre.strip(), e_codigo.strip(), e_reg, e_ugel.strip(), 1 if e_activo else 0, cid))
#|             db_execute("UPDATE usuarios SET colegio=%s WHERE colegio_id=%s", (e_nombre.strip(), cid))
#|             st.success("Cambios guardados.")
#|             st.rerun()
#|         with st.expander("🗑️ Eliminar este colegio"):
#|             if c["usuarios"] > 0:
#|                 st.warning(f"Tiene {c['usuarios']} usuario(s). Reasígnalos o desactívalo en lugar de eliminarlo.")
#|             else:
#|                 ok = st.checkbox("Confirmo que quiero eliminarlo", key=f"ccd_{cid}")
#|                 if st.button("Eliminar colegio", key=f"cdel_{cid}"):
#|                     if ok:
#|                         db_execute("DELETE FROM colegios WHERE id=%s", (cid,))
#|                         st.success("Colegio eliminado.")
#|                         st.rerun()
#|                     else:
#|                         st.warning("Marca la confirmación primero.")
#|
#|
#| # ------------------------------------------------------------------
#| # CURRÍCULO
#| # ------------------------------------------------------------------
#| def panel_curriculo():
#|     st.subheader("Base curricular verificada")
#|     st.caption("La IA solo usa los textos de esta base. Competencias y capacidades vienen precargadas (marcadas «por verificar»). "
#|                "Los **desempeños** los cargas tú desde los Programas Curriculares oficiales del MINEDU.")
#|     c1, c2 = st.columns(2)
#|     nivel = c1.selectbox("Nivel", NIVELES, key="cur_nivel")
#|     areas = areas_de(nivel)
#|     area = c2.selectbox("Área", areas, key="cur_area") if areas else None
#|     if st.button("♻️ Agregar competencias base que falten", key="cur_sembrar"):
#|         n = sembrar_curriculo(conexion())
#|         limpiar_cache()
#|         st.success(f"Se agregaron {n} competencia(s) base.")
#|         st.rerun()
#|     t1, t2, t3, t4 = st.tabs(["Competencias y capacidades", "Desempeños", "Importar Excel / CSV", "Transversales"])
#|     with t1:
#|         _cur_competencias(nivel, area)
#|     with t2:
#|         _cur_desempenos(nivel, area)
#|     with t3:
#|         _cur_importar()
#|     with t4:
#|         _cur_transversales()
#|
#|
#| def _cur_competencias(nivel, area):
#|     if not area:
#|         st.info("No hay áreas en este nivel.")
#|         return
#|     comps = competencias_de(nivel, area)
#|     for c in comps:
#|         with st.expander(("✅ " if c["verificado"] else "⚠️ ") + c["nombre"]):
#|             nombre = st.text_input("Competencia", c["nombre"], key=f"cn_{c['id']}")
#|             caps = st.text_area("Capacidades (una por línea)", "\n".join(c["capacidades"]), key=f"cp_{c['id']}", height=130)
#|             ver = st.checkbox("Verificada con el Programa Curricular oficial", c["verificado"], key=f"cv_{c['id']}")
#|             b1, b2 = st.columns(2)
#|             if b1.button("💾 Guardar", key=f"cs_{c['id']}"):
#|                 db_execute("UPDATE curriculo_competencias SET nombre=%s, verificado=%s WHERE id=%s",
#|                            (nombre.strip(), 1 if ver else 0, c["id"]))
#|                 db_execute("DELETE FROM curriculo_capacidades WHERE competencia_id=%s", (c["id"],))
#|                 execute_many("INSERT INTO curriculo_capacidades (competencia_id, nombre, orden) VALUES (%s,%s,%s)",
#|                              [(c["id"], x, i) for i, x in enumerate(a_lista(caps), 1)])
#|                 st.success("Guardado ✅")
#|             if b2.button("🗑️ Eliminar competencia", key=f"cx_{c['id']}"):
#|                 db_execute("DELETE FROM curriculo_desempenos WHERE competencia_id=%s", (c["id"],))
#|                 db_execute("DELETE FROM curriculo_capacidades WHERE competencia_id=%s", (c["id"],))
#|                 db_execute("DELETE FROM curriculo_competencias WHERE id=%s", (c["id"],))
#|                 st.rerun()
#|     with st.expander("➕ Agregar competencia a esta área"):
#|         n = st.text_input("Nombre de la competencia", key="nc_nombre")
#|         k = st.text_area("Capacidades (una por línea)", key="nc_caps", height=100)
#|         if st.button("Agregar", key="nc_add") and n.strip():
#|             nuevo, _ = db_execute("INSERT INTO curriculo_competencias (nivel, area, nombre, orden, verificado) "
#|                                   "VALUES (%s,%s,%s,%s,0)", (nivel, area, n.strip(), len(comps) + 1))
#|             execute_many("INSERT INTO curriculo_capacidades (competencia_id, nombre, orden) VALUES (%s,%s,%s)",
#|                          [(nuevo, x, i) for i, x in enumerate(a_lista(k), 1)])
#|             st.rerun()
#|     with st.expander("➕ Crear un área nueva en este nivel (ej.: Tutoría)"):
#|         na = st.text_input("Nombre del área", key="na_nombre")
#|         nc = st.text_input("Primera competencia del área", key="na_comp")
#|         if st.button("Crear área", key="na_add") and na.strip() and nc.strip():
#|             db_execute("INSERT INTO curriculo_competencias (nivel, area, nombre, orden, verificado) VALUES (%s,%s,%s,1,0)",
#|                        (nivel, na.strip(), nc.strip()))
#|             st.rerun()
#|
#|
#| def _cur_desempenos(nivel, area):
#|     if not area:
#|         return
#|     comps = competencias_de(nivel, area)
#|     if not comps:
#|         st.info("Esta área no tiene competencias.")
#|         return
#|     resumen = [{"competencia": c["nombre"][:60], **{g: len(desempenos_de(c["id"], g)) for g in GRADOS[nivel]}} for c in comps]
#|     st.caption("Cantidad de desempeños cargados por grado:")
#|     st.dataframe(pd.DataFrame(resumen), hide_index=True)
#|     cid = st.selectbox("Competencia", [c["id"] for c in comps], key="des_comp",
#|                        format_func=lambda i: next(c["nombre"] for c in comps if c["id"] == i)[:90])
#|     grado = st.selectbox("Grado", GRADOS[nivel], key="des_grado")
#|     actuales = desempenos_de(cid, grado)
#|     df = pd.DataFrame([{"desempeño": d["texto"]} for d in actuales], columns=["desempeño"])
#|     ed = st.data_editor(df, key=f"des_ed_{cid}_{grado}", num_rows="dynamic", hide_index=True,
#|                         column_config={"desempeño": st.column_config.TextColumn("Desempeño (texto oficial)", width="large")})
#|     if st.button("💾 Guardar desempeños", type="primary", key=f"des_save_{cid}_{grado}"):
#|         db_execute("DELETE FROM curriculo_desempenos WHERE competencia_id=%s AND grado=%s", (cid, grado))
#|         filas = [(cid, grado, s(t), i) for i, t in enumerate(ed["desempeño"].fillna(""), 1) if s(t)]
#|         execute_many("INSERT INTO curriculo_desempenos (competencia_id, grado, texto, orden) VALUES (%s,%s,%s,%s)", filas)
#|         st.success(f"{len(filas)} desempeño(s) guardados ✅")
#|
#|
#| def _cur_importar():
#|     st.caption("Sube un Excel o CSV con las columnas: **nivel, area, competencia, grado, desempeno**. "
#|                "Si la competencia no existe, se crea (sin verificar).")
#|     plantilla = pd.DataFrame([{"nivel": "Primaria", "area": "Matemática", "competencia": "Resuelve problemas de cantidad",
#|                                "grado": "3.° grado", "desempeno": "Escribe aquí el desempeño oficial..."}])
#|     st.download_button("⬇️ Descargar plantilla (CSV)", plantilla.to_csv(index=False).encode("utf-8-sig"),
#|                        file_name="plantilla_desempenos.csv", mime="text/csv", key="cur_plantilla")
#|     archivo = st.file_uploader("Archivo", type=["csv", "xlsx"], key="cur_archivo")
#|     reemplazar = st.checkbox("Reemplazar los desempeños existentes de cada competencia/grado del archivo", value=False)
#|     if archivo is not None and st.button("📥 Importar", type="primary", key="cur_importar_btn"):
#|         try:
#|             df = pd.read_csv(archivo) if archivo.name.lower().endswith(".csv") else pd.read_excel(archivo)
#|             df.columns = [norm(c).replace(" ", "") for c in df.columns]
#|             falta = {"nivel", "area", "competencia", "grado", "desempeno"} - set(df.columns)
#|             if falta:
#|                 st.error(f"Faltan columnas: {', '.join(sorted(falta))}")
#|                 return
#|             insertados, creadas, limpiados = 0, 0, set()
#|             for _, r in df.fillna("").iterrows():
#|                 nivel, area, comp, grado, texto = (s(r[k]) for k in ("nivel", "area", "competencia", "grado", "desempeno"))
#|                 if not (nivel and area and comp and grado and texto):
#|                     continue
#|                 cid = None
#|                 for c in competencias_de(nivel, area):
#|                     if norm(c["nombre"]) == norm(comp):
#|                         cid = c["id"]
#|                 if cid is None:
#|                     cid, _ = db_execute("INSERT INTO curriculo_competencias (nivel, area, nombre, orden, verificado) "
#|                                         "VALUES (%s,%s,%s,99,0)", (nivel, area, comp))
#|                     creadas += 1
#|                 if reemplazar and (cid, grado) not in limpiados:
#|                     db_execute("DELETE FROM curriculo_desempenos WHERE competencia_id=%s AND grado=%s", (cid, grado))
#|                     limpiados.add((cid, grado))
#|                 db_execute("INSERT INTO curriculo_desempenos (competencia_id, grado, texto, orden) VALUES (%s,%s,%s,%s)",
#|                            (cid, grado, texto, insertados + 1))
#|                 insertados += 1
#|             st.success(f"Importados {insertados} desempeño(s). Competencias nuevas: {creadas}.")
#|         except Exception as e:
#|             st.error(f"No se pudo importar: {e}")
#|
#|
#| def _cur_transversales():
#|     filas = db_fetch("SELECT id, tipo, nombre, detalle FROM curriculo_transversal ORDER BY id")
#|     for tipo, titulo in (("competencia", "Competencias transversales"), ("enfoque", "Enfoques transversales")):
#|         st.markdown(f"**{titulo}** (en «detalle» escribe una capacidad o valor por línea)")
#|         df = pd.DataFrame([{"nombre": f["nombre"], "detalle": f["detalle"] or ""} for f in filas if f["tipo"] == tipo],
#|                           columns=["nombre", "detalle"])
#|         ed = st.data_editor(df, key=f"trans_{tipo}", num_rows="dynamic", hide_index=True,
#|                             column_config={"detalle": st.column_config.TextColumn("detalle", width="large")})
#|         if st.button(f"💾 Guardar {titulo.lower()}", key=f"trans_save_{tipo}"):
#|             db_execute("DELETE FROM curriculo_transversal WHERE tipo=%s", (tipo,))
#|             execute_many("INSERT INTO curriculo_transversal (tipo, nombre, detalle) VALUES (%s,%s,%s)",
#|                          [(tipo, s(r["nombre"]), s(r["detalle"])) for _, r in ed.fillna("").iterrows() if s(r["nombre"])])
#|             limpiar_cache()
#|             st.success("Guardado ✅")
#|
#|
#| # ------------------------------------------------------------------
#| # NORMATIVA
#| # ------------------------------------------------------------------
#| def panel_normativa(admin_id):
#|     st.subheader("Actualización normativa MINEDU")
#|     st.caption("La IA detecta cambios y los resume; nada se usa en los documentos hasta que lo apruebes. "
#|                "La IA no modifica el currículo oficial.")
#|     fuentes = db_fetch("SELECT * FROM normativa_fuentes ORDER BY id")
#|     if st.button("🔄 Revisar todas las fuentes activas ahora", type="primary", key="norm_revisar"):
#|         with st.spinner("Consultando fuentes oficiales y analizando cambios..."):
#|             for f in fuentes:
#|                 if f["activa"]:
#|                     estado, msg = revisar_fuente(f)
#|                     st.write(f"{ {'nueva': '🆕', 'sin_cambios': '✅', 'error': '⚠️'}[estado] } **{f['nombre']}** — {msg}")
#|     st.markdown("#### Pendientes de revisión")
#|     pend = db_fetch("SELECT v.id, f.nombre, f.tipo, v.resumen_cambios, v.detectado_en FROM normativa_versiones v "
#|                     "JOIN normativa_fuentes f ON f.id = v.fuente_id WHERE v.estado='pendiente' ORDER BY v.id DESC")
#|     if not pend:
#|         st.success("No hay cambios pendientes.")
#|     for p in pend:
#|         with st.expander(f"🆕 {p['nombre']} · {p['tipo']} · {p['detectado_en']:%d/%m/%Y %H:%M}"):
#|             st.markdown(p["resumen_cambios"] or "_Sin resumen_")
#|             b1, b2, _ = st.columns([1, 1, 3])
#|             if b1.button("✅ Aprobar", key=f"ap_{p['id']}"):
#|                 db_execute("UPDATE normativa_versiones SET estado='aprobada', aprobado_por=%s, aprobado_en=NOW() WHERE id=%s",
#|                            (admin_id, p["id"]))
#|                 st.rerun()
#|             if b2.button("❌ Rechazar", key=f"rj_{p['id']}"):
#|                 db_execute("UPDATE normativa_versiones SET estado='rechazada', aprobado_por=%s, aprobado_en=NOW() WHERE id=%s",
#|                            (admin_id, p["id"]))
#|                 st.rerun()
#|     st.markdown("#### Fuentes monitoreadas")
#|     if fuentes:
#|         st.dataframe(pd.DataFrame(fuentes).drop(columns=["url"]), hide_index=True)
#|         opciones = {f["id"]: f"{f['id']} · {f['nombre']}" for f in fuentes}
#|         fid = st.selectbox("Fuente", list(opciones.keys()), format_func=lambda k: opciones[k], key="adm_fuente_sel")
#|         f = next(x for x in fuentes if x["id"] == fid)
#|         c1, c2 = st.columns(2)
#|         if c1.button("⏯️ Activar / desactivar", key=f"tg_{fid}"):
#|             db_execute("UPDATE normativa_fuentes SET activa=%s WHERE id=%s", (0 if f["activa"] else 1, fid))
#|             st.rerun()
#|         if c2.button("🗑️ Eliminar fuente y su historial", key=f"fd_{fid}"):
#|             db_execute("DELETE FROM normativa_versiones WHERE fuente_id=%s", (fid,))
#|             db_execute("DELETE FROM normativa_fuentes WHERE id=%s", (fid,))
#|             st.rerun()
#|     with st.expander("➕ Agregar fuente (MINEDU, DRE o UGEL)"):
#|         with st.form("nueva_fuente", clear_on_submit=True):
#|             n_nombre = st.text_input("Nombre")
#|             n_url = st.text_input("URL (página web HTML)")
#|             n_tipo = st.selectbox("Tipo de cambio que suele traer", TIPOS_NORMA)
#|             enviar = st.form_submit_button("Agregar", type="primary")
#|         if enviar:
#|             if n_nombre.strip() and n_url.strip().startswith(("http://", "https://")):
#|                 db_execute("INSERT INTO normativa_fuentes (nombre, url, tipo) VALUES (%s,%s,%s)",
#|                            (n_nombre.strip(), n_url.strip(), n_tipo))
#|                 st.success("Fuente agregada.")
#|                 st.rerun()
#|             else:
#|                 st.warning("Escribe un nombre y una URL que empiece con http:// o https://")
#|     st.markdown("#### Historial de versiones")
#|     hist = db_fetch("SELECT v.id, f.nombre AS fuente, v.estado, v.detectado_en, v.aprobado_en FROM normativa_versiones v "
#|                     "JOIN normativa_fuentes f ON f.id = v.fuente_id ORDER BY v.id DESC LIMIT 30")
#|     if hist:
#|         st.dataframe(pd.DataFrame(hist), hide_index=True)
#|
#|
#| # ------------------------------------------------------------------
#| def panel_costos():
#|     st.subheader("Costo en créditos por acción")
#|     st.caption("Lo que paga un docente cada vez que la IA genera algo (0 = gratis). El administrador nunca paga.")
#|     valores = {}
#|     cols = st.columns(3)
#|     for i, (clave, nombre) in enumerate(NOMBRES_COSTO.items()):
#|         valores[clave] = cols[i % 3].number_input(nombre, 0, 100, costo_de(clave), key=f"costo_{clave}")
#|     if st.button("💾 Guardar costos", type="primary", key="costos_save"):
#|         for clave, v in valores.items():
#|             config_set(f"costo_{clave}", int(v))
#|         st.success("Costos guardados ✅")
#@@ END
