"""EduPerú IA — portal docente (VERSIÓN DE UN SOLO ARCHIVO).

Este archivo contiene TODO el sistema: arriba está el cargador y la aplicación principal, y al final
(bloques que empiezan con «#@@ MODULE») el código de cada módulo. No borres esos bloques.
"""
import hashlib
import linecache
import sys
import types

import streamlit as st

_ORDEN = ['util', 'db', 'repo', 'curriculo', 'render', 'exportar', 'ia', 'normativa', 'programas', 'lineamientos', 'calendario', 'auth', 'ui', 'examen_unidad', 'v_curriculo', 'v_programas', 'v_calendario', 'v_panel', 'v_anual', 'v_unidades', 'v_sesiones', 'v_biblioteca', 'v_admin']


def _cargar_modulos():
    """Carga los módulos del final de este archivo.
    - Si cambiaste app.py, recarga todo (no quedan módulos viejos en memoria).
    - Si un módulo falla, descarta lo cargado a medias y dice cuál falló y por qué."""
    with open(__file__, encoding="utf-8") as f:
        texto = f.read()
    version = hashlib.md5(texto.encode("utf-8")).hexdigest()[:12]
    bloques, actual = {}, None
    for linea in texto.split("\n"):
        if linea.startswith("#@@ MODULE "):
            actual = linea[len("#@@ MODULE "):].strip()
            bloques[actual] = []
        elif linea.startswith("#@@ END"):
            actual = None
        elif actual is not None and linea.startswith("#|"):
            bloques[actual].append(linea[3:] if len(linea) > 2 else "")
    nuevos, nombre = [], ""
    try:
        for nombre in _ORDEN:
            existente = sys.modules.get(nombre)
            if existente is not None and getattr(existente, "__eduperu__", None) == version:
                continue
            codigo = "\n".join(bloques[nombre]) + "\n"
            archivo = f"<eduperu:{nombre}.py>"
            linecache.cache[archivo] = (len(codigo), None, codigo.splitlines(True), archivo)
            modulo = types.ModuleType(nombre)
            modulo.__file__ = archivo
            modulo.__eduperu__ = version
            sys.modules[nombre] = modulo
            nuevos.append(nombre)
            exec(compile(codigo, archivo, "exec"), modulo.__dict__)
    except BaseException as e:
        for n in nuevos:
            sys.modules.pop(n, None)
        raise ImportError(f"No se pudo cargar el módulo «{nombre}»: {type(e).__name__}: {e}") from e


try:
    _cargar_modulos()
except ImportError as _e:
    st.error(f"⚠️ {_e}")
    st.stop()

# ======================= APLICACIÓN PRINCIPAL =======================

import html

import streamlit as st

st.set_page_config(page_title="EduPerú IA - Portal Docente", layout="wide", page_icon="✏️",
                   initial_sidebar_state="expanded")

# Cada ejecución empieza con la memoria de consultas vacía (así los datos nunca quedan viejos)
st.session_state["_memo"] = {}

st.markdown("""
<style>
:root { --p1:#7c3aed; --p2:#c026d3; --acc:#f59e0b; --ink:#1f2937; --suave:#6b7280; }
.main .block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 1100px; }
h1, h2, h3 { letter-spacing: -0.01em; }
h2, h3 { margin-top: .6rem; }
div[data-testid="stVerticalBlock"] { gap: 1rem; }
div[data-testid="stForm"] { border: none; }

/* sin el "muñequito" de carga ni la atenuación de la pantalla */
[data-testid="stStatusWidget"] { display: none !important; }
[data-stale="true"], .stApp [data-stale="true"] { opacity: 1 !important; transition: none !important; }

/* ---------- barra lateral ---------- */
[data-testid="stSidebar"] { background: linear-gradient(180deg, #f8f2ff 0%, #ffffff 65%); border-right: 1px solid #eee3fb; }
[data-testid="stSidebar"] > div:first-child { padding: 1.2rem 1rem 1rem; }
.brand { font-size: 1.5rem; font-weight: 800; background: linear-gradient(90deg, var(--p1), var(--p2));
         -webkit-background-clip: text; background-clip: text; color: transparent; margin: .2rem 0 1rem .3rem; }
.usercard { display: flex; align-items: center; gap: .75rem; background: #fff; border: 1px solid #efe7fb; border-radius: 18px;
            padding: .8rem .9rem; margin-bottom: 1.2rem; box-shadow: 0 2px 10px rgba(124,58,237,.08); }
.avatar { flex: 0 0 auto; width: 42px; height: 42px; border-radius: 50%; color: #fff; font-weight: 800; font-size: 1.1rem;
          display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, var(--p1), var(--p2)); }
.usercard .nombre { font-weight: 700; color: var(--ink); line-height: 1.2; }
.usercard .rol { font-size: .74rem; color: var(--suave); }
.chip { display: inline-block; border-radius: 999px; padding: .15rem .7rem; font-size: .8rem; margin-top: .25rem;
        background: #f3e8ff; color: #6d28d9; font-weight: 600; }
.menu-t { font-size: .72rem; letter-spacing: .14em; color: #a78bda; font-weight: 700; margin: .4rem 0 .5rem .5rem; }

/* menú lateral: más aire, bordes suaves y el elegido resaltado */
[data-testid="stSidebar"] div[role="radiogroup"] { gap: 6px; }
[data-testid="stSidebar"] div[role="radiogroup"] > label { padding: .78rem 1rem; border-radius: 14px; width: 100%; cursor: pointer;
                                                           transition: background .15s; }
[data-testid="stSidebar"] div[role="radiogroup"] > label p { font-size: 1rem; margin: 0; }
[data-testid="stSidebar"] div[role="radiogroup"] > label:hover { background: #f3e8ff; }
[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child { display: none; }
[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
    background: linear-gradient(90deg, var(--p1), var(--p2)); box-shadow: 0 6px 16px rgba(124,58,237,.25); }
[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) * { color: #fff !important; font-weight: 600; }
.pie-lateral { font-size: .74rem; color: #9ca3af; margin-top: .8rem; text-align: center; }

/* ---------- banda de bienvenida (el botón va DENTRO) ---------- */
.st-key-hero { background: linear-gradient(120deg, #7c3aed 0%, #c026d3 60%, #f59e0b 135%); border-radius: 24px;
               padding: 1.8rem 2rem 1.5rem; box-shadow: 0 12px 30px rgba(124,58,237,.30); }
.hero-t { font-size: 1.95rem; font-weight: 800; color: #fff; }
.hero-s { color: #fff; opacity: .96; max-width: 720px; margin: .35rem 0 .7rem; line-height: 1.5; }
.st-key-hero .chip { background: rgba(255,255,255,.22); color: #fff; }
.st-key-hero button { background: #ffffff; border: 0; border-radius: 14px; font-weight: 700; padding: .55rem 1rem; }
.st-key-hero button p, .st-key-hero button div { color: #6d28d9 !important; }
.st-key-hero button:hover { filter: brightness(.96); }

/* ---------- tarjetas ---------- */
[class*="st-key-card_"], [class*="st-key-curso_"], .st-key-continuar, .st-key-form_crear {
    padding: 1.25rem 1.35rem !important; border-radius: 20px !important; background: #fff;
    box-shadow: 0 2px 12px rgba(17,24,39,.06); transition: box-shadow .2s, transform .2s; }
[class*="st-key-card_"]:hover, [class*="st-key-curso_"]:hover { box-shadow: 0 10px 26px rgba(124,58,237,.16); transform: translateY(-2px); }
.tool-i { font-size: 2.2rem; line-height: 1; margin-bottom: .2rem; }
.tool-t { font-weight: 700; font-size: 1.05rem; margin-top: .35rem; color: var(--ink); }
.tool-d { color: var(--suave); font-size: .86rem; min-height: 2.6rem; margin: .2rem 0 .6rem; line-height: 1.4; }
.curso-t { font-weight: 700; font-size: 1.08rem; color: var(--ink); }
.curso-s { color: var(--suave); font-size: .86rem; margin: .15rem 0 .5rem; }
.curso-p { font-size: .85rem; color: #4b5563; margin: .2rem 0 .8rem; }

/* ---------- botones de las tarjetas de curso (no se cortan ni se apilan en celular) ---------- */
[class*="st-key-curso_"] { overflow: visible; min-width: 0; }
[class*="st-key-curso_"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .5rem; }
[class*="st-key-curso_"] [data-testid="stColumn"] { min-width: 0 !important; }
[class*="st-key-curso_"] button { padding-left: .5rem; padding-right: .5rem; white-space: nowrap; }

/* ---------- botones ---------- */
button[kind="primary"], button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(90deg, var(--p1), var(--p2)); border: 0; color: #fff; border-radius: 12px; font-weight: 600; }
button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover { filter: brightness(1.08); }
button[kind="secondary"], button[data-testid="stBaseButton-secondary"] { border-radius: 12px; }
@media (max-width: 768px) { .main .block-container { padding-left: 1rem; padding-right: 1rem; } .hero-t { font-size: 1.4rem; } }
</style>
""", unsafe_allow_html=True)

from db import init_db  # noqa: E402

try:
    init_db()
except Exception as e:
    st.error(f"⚠️ No se pudo preparar la base de datos: {type(e).__name__}: {e}")
    st.stop()

from auth import pantalla_login  # noqa: E402
from repo import get_usuario  # noqa: E402
from ui import (PAG_ADMIN, PAG_ANUAL, PAG_BIBLIO, PAG_CALENDARIO, PAG_CURRICULO, PAG_CURSOS,  # noqa: E402
                PAG_PANEL, PAG_TEMAS, mostrar_flash)
import v_admin, v_anual, v_biblioteca, v_calendario, v_curriculo, v_panel, v_sesiones  # noqa: E402,E401


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

paginas = [PAG_PANEL, PAG_CURSOS, PAG_ANUAL, PAG_TEMAS, PAG_CALENDARIO, PAG_CURRICULO, PAG_BIBLIO] + ([PAG_ADMIN] if es_admin else [])
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
    v_panel.render()
elif pagina == PAG_CURSOS:
    v_panel.render_cursos()
elif pagina == PAG_ANUAL:
    v_anual.render()
elif pagina == PAG_TEMAS:
    v_sesiones.render()
elif pagina == PAG_CALENDARIO:
    v_calendario.render()
elif pagina == PAG_CURRICULO:
    v_curriculo.render()
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
#| import copy
#| import queue
#| import threading
#| import time
#|
#| import streamlit as st
#| import mysql.connector
#|
#|
#| def _cfg():
#|     s = st.secrets["mysql"]
#|     return dict(
#|         host=s["host"], port=int(s["port"]), database=s["database"],
#|         user=s["user"], password=s["password"],
#|         ssl_disabled=False, connection_timeout=10, autocommit=True,
#|     )
#|
#|
#| class _Reserva:
#|     """Pequeña reserva de conexiones abiertas. Cada consulta cuesta UNA sola ida y vuelta a la base
#|     (sin «ping» ni «reset» en cada uso, que era lo que hacía lenta la página)."""
#|
#|     def __init__(self, tamano=4):
#|         self.libres = queue.Queue()
#|         self.tamano = tamano
#|         self.abiertas = 0
#|         self.candado = threading.Lock()
#|
#|     def _nueva(self):
#|         c = mysql.connector.connect(**_cfg())
#|         c._eduperu_uso = time.time()
#|         return c
#|
#|     def tomar(self):
#|         try:
#|             c = self.libres.get_nowait()
#|         except queue.Empty:
#|             with self.candado:
#|                 crear = self.abiertas < self.tamano
#|                 if crear:
#|                     self.abiertas += 1
#|             if not crear:
#|                 c = self.libres.get(timeout=30)
#|             else:
#|                 try:
#|                     return self._nueva()
#|                 except Exception:
#|                     with self.candado:
#|                         self.abiertas -= 1
#|                     raise
#|         # solo si estuvo ociosa un buen rato se comprueba que siga viva
#|         if time.time() - getattr(c, "_eduperu_uso", 0) > 120:
#|             try:
#|                 c.ping(reconnect=True, attempts=2, delay=1)
#|             except Exception:
#|                 self.descartar(c)
#|                 return self.tomar()
#|         return c
#|
#|     def devolver(self, c):
#|         c._eduperu_uso = time.time()
#|         self.libres.put(c)
#|
#|     def descartar(self, c):
#|         try:
#|             c.close()
#|         except Exception:
#|             pass
#|         with self.candado:
#|             self.abiertas = max(0, self.abiertas - 1)
#|
#|
#| @st.cache_resource(show_spinner=False)
#| def _reserva():
#|     return _Reserva()
#|
#|
#| _ERRORES_CONEXION = (2006, 2013, 2055, 2003, 2027, 2014)
#|
#|
#| def _con_reintento(operacion):
#|     """Ejecuta operacion(conexion). Si la conexión estaba caída, abre otra y reintenta una vez."""
#|     reserva = _reserva()
#|     for intento in (1, 2):
#|         c = reserva.tomar()
#|         try:
#|             res = operacion(c)
#|             reserva.devolver(c)
#|             return res
#|         except mysql.connector.Error as e:
#|             if getattr(e, "errno", None) in _ERRORES_CONEXION or isinstance(e, mysql.connector.InterfaceError):
#|                 reserva.descartar(c)
#|                 if intento == 1:
#|                     continue
#|             else:
#|                 reserva.devolver(c)
#|             raise
#|         except Exception:
#|             reserva.devolver(c)
#|             raise
#|
#|
#| def conexion():
#|     """Conexión suelta (se usa solo al crear las tablas)."""
#|     return mysql.connector.connect(**_cfg())
#|
#|
#| def _memo():
#|     """Memoria de consultas de UNA ejecución de la página (se vacía en cada ejecución y en cada escritura)."""
#|     try:
#|         return st.session_state.setdefault("_memo", {})
#|     except Exception:
#|         return {}
#|
#|
#| def fetch(sql, params=(), one=False):
#|     memo = _memo()
#|     try:
#|         clave = (sql, tuple(params), one)
#|         if clave in memo:
#|             return copy.deepcopy(memo[clave])
#|     except TypeError:
#|         clave = None
#|     def op(conn):
#|         cur = conn.cursor(dictionary=True, buffered=True)
#|         cur.execute(sql, params)
#|         filas = cur.fetchone() if one else cur.fetchall()
#|         cur.close()
#|         return filas
#|
#|     filas = _con_reintento(op)
#|     if clave is not None:
#|         memo[clave] = copy.deepcopy(filas)
#|     return filas
#|
#|
#| def _tras_escribir(sql):
#|     """Después de escribir: se vacía la memoria de la página y, si cambió el currículo/configuración, la caché."""
#|     try:
#|         st.session_state["_memo"] = {}
#|     except Exception:
#|         pass
#|     bajo = sql.lower()
#|     if any(x in bajo for x in ("curriculo_", " config", "normativa_")):
#|         try:
#|             st.cache_data.clear()
#|         except Exception:
#|             pass
#|
#|
#| def execute(sql, params=()):
#|     """Ejecuta INSERT/UPDATE/DELETE. Devuelve (último id, filas afectadas)."""
#|     def op(conn):
#|         cur = conn.cursor(buffered=True)
#|         cur.execute(sql, params)
#|         res = (cur.lastrowid, cur.rowcount)
#|         cur.close()
#|         return res
#|
#|     res = _con_reintento(op)
#|     _tras_escribir(sql)
#|     return res
#|
#|
#| def execute_many(sql, filas):
#|     if not filas:
#|         return
#|     def op(conn):
#|         cur = conn.cursor(buffered=True)
#|         cur.executemany(sql, filas)
#|         cur.close()
#|
#|     _con_reintento(op)
#|     _tras_escribir(sql)
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
#|         lineamientos_fuente VARCHAR(300),
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
#|         fuente VARCHAR(600),
#|         verificado_en DATETIME NULL,
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
#|         asignacion_id INT NULL,
#|         INDEX idx_des_comp_grado (competencia_id, grado)
#|     )""",
#|     """CREATE TABLE IF NOT EXISTS curriculo_transversal (
#|         id INT AUTO_INCREMENT PRIMARY KEY,
#|         tipo VARCHAR(20) NOT NULL,
#|         nombre VARCHAR(300) NOT NULL,
#|         detalle TEXT
#|     )""",
#|     """CREATE TABLE IF NOT EXISTS curriculo_estandares (
#|         id INT AUTO_INCREMENT PRIMARY KEY,
#|         competencia_id INT NOT NULL,
#|         ciclo VARCHAR(10) NOT NULL,
#|         texto TEXT NOT NULL,
#|         asignacion_id INT NULL,
#|         INDEX idx_est_comp (competencia_id, ciclo)
#|     )""",
#|     """CREATE TABLE IF NOT EXISTS curriculo_pdf (
#|         id INT AUTO_INCREMENT PRIMARY KEY,
#|         url VARCHAR(600) NOT NULL,
#|         titulo VARCHAR(300),
#|         nivel VARCHAR(20),
#|         origen VARCHAR(600),
#|         firma VARCHAR(300),
#|         hash_contenido VARCHAR(64),
#|         paginas INT DEFAULT 0,
#|         estado VARCHAR(20) DEFAULT 'nuevo',
#|         detectado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
#|         leido_en DATETIME NULL
#|     )""",
#|     """CREATE TABLE IF NOT EXISTS curriculo_pdf_paginas (
#|         id INT AUTO_INCREMENT PRIMARY KEY,
#|         pdf_id INT NOT NULL,
#|         pagina INT NOT NULL,
#|         texto LONGTEXT,
#|         INDEX idx_pag_pdf (pdf_id, pagina)
#|     )""",
#|     """CREATE TABLE IF NOT EXISTS curriculo_importado (
#|         id INT AUTO_INCREMENT PRIMARY KEY,
#|         pdf_id INT NOT NULL,
#|         competencia_id INT NOT NULL,
#|         tipo VARCHAR(12) NOT NULL,
#|         grado VARCHAR(20) NOT NULL,
#|         texto TEXT NOT NULL,
#|         pagina INT DEFAULT 0,
#|         estado VARCHAR(12) DEFAULT 'pendiente',
#|         creado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
#|         INDEX idx_imp_pdf (pdf_id, estado)
#|     )""",
#|     """CREATE TABLE IF NOT EXISTS eventos (
#|         id INT AUTO_INCREMENT PRIMARY KEY,
#|         usuario_id INT NOT NULL,
#|         asignacion_id INT NULL,
#|         fecha DATE NOT NULL,
#|         tipo VARCHAR(20) DEFAULT 'actividad',
#|         titulo VARCHAR(255) NOT NULL,
#|         detalle TEXT,
#|         doc_id INT NULL,
#|         creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#|         INDEX idx_ev_usuario_fecha (usuario_id, fecha)
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
#|         for col, ddl in [("fuente", "VARCHAR(600)"), ("verificado_en", "DATETIME NULL")]:
#|             _asegurar_columna(cur, "curriculo_competencias", col, ddl)
#|         _asegurar_columna(cur, "curriculo_desempenos", "asignacion_id", "INT NULL")
#|         _asegurar_columna(cur, "curriculo_estandares", "asignacion_id", "INT NULL")
#|         _asegurar_columna(cur, "asignaciones", "lineamientos_fuente", "VARCHAR(300)")
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
#|
#|
#| def medir_latencia(veces=5):
#|     """Milisegundos que tarda una consulta mínima a la base (promedio)."""
#|     inicio = time.time()
#|     for _ in range(veces):
#|         _con_reintento(lambda c: (lambda cur: (cur.execute("SELECT 1"), cur.fetchall(), cur.close()))(c.cursor()))
#|     return (time.time() - inicio) * 1000 / veces
#@@ END
#@@ MODULE repo
#| """Acceso a datos: usuarios, créditos, asignaciones (áreas del docente) y documentos."""
#| import json
#|
#| import streamlit as st
#|
#| from db import fetch, execute
#|
#| ORDEN_NIVEL = {"Inicial": 0, "Primaria": 1, "Secundaria": 2}
#|
#| COSTOS_DEFAULT = {"caracterizacion": 0, "anual": 2, "unidad": 2, "sesion": 1,
#|                   "rubrica": 1, "ficha": 1, "examen": 1, "examen_unidad": 2, "importar": 1, "revision": 1,
#|                   "desafio": 1, "lineamientos": 1, "calendario_ia": 1}
#| NOMBRES_COSTO = {
#|     "caracterizacion": "Boceto de caracterización del estudiante",
#|     "anual": "Situaciones significativas (planificación anual)",
#|     "unidad": "Unidad de aprendizaje",
#|     "sesion": "Sesión de aprendizaje",
#|     "rubrica": "Rúbrica de evaluación",
#|     "ficha": "Ficha de trabajo",
#|     "examen": "Examen de la sesión",
#|     "examen_unidad": "Examen de unidad / bimestre",
#|     "importar": "Importar unidad desde Word",
#|     "revision": "Revisión de coherencia",
#|     "desafio": "Desafíos de aprendizaje",
#|     "lineamientos": "Traer o leer lineamientos con IA",
#|     "calendario_ia": "Sugerencias del calendario con IA",
#| }
#|
#|
#| # ------------------------------------------------------------------
#| # Configuración y créditos
#| # ------------------------------------------------------------------
#| @st.cache_data(ttl=300, show_spinner=False)
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
#| CAMPOS_ASIG = {"institucion", "director", "docente", "region", "seccion", "caracterizacion", "ciclo_escolar",
#|                "lineamientos_fuente"}
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
#|     execute("DELETE FROM eventos WHERE asignacion_id=%s", (aid,))
#|     execute("DELETE FROM curriculo_desempenos WHERE asignacion_id=%s", (aid,))
#|     execute("DELETE FROM curriculo_estandares WHERE asignacion_id=%s", (aid,))
#|     execute("DELETE FROM asignaciones WHERE id=%s", (aid,))
#|
#|
#| def borrar_todas_asignaciones(uid):
#|     for a in fetch("SELECT id FROM asignaciones WHERE usuario_id=%s", (uid,)):
#|         borrar_asignacion(a["id"])
#|
#|
#| def resumen_todas(uid):
#|     """{asignacion_id: {tipo: cantidad}} para todos los cursos del usuario, en UNA sola consulta."""
#|     res = {}
#|     for f in fetch("SELECT asignacion_id, tipo, COUNT(*) AS n FROM documentos WHERE usuario_id=%s "
#|                    "GROUP BY asignacion_id, tipo", (uid,)):
#|         res.setdefault(f["asignacion_id"], {})[f["tipo"]] = f["n"]
#|     return res
#|
#|
#| def docs_del_usuario(uid):
#|     """Lista liviana (sin el contenido) de todos los documentos del usuario."""
#|     return fetch("SELECT id, asignacion_id, tipo, padre_id, numero, titulo, color, normativa_usada, actualizado_en "
#|                  "FROM documentos WHERE usuario_id=%s ORDER BY asignacion_id, numero, id", (uid,))
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
#|     clave_num = numero if tipo in ("unidad", "sesion", "examen_unidad") else None
#|     clave_pad = padre_id if tipo in ("sesion", "rubrica", "ficha", "examen", "desafio") else None
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
#@@ MODULE curriculo
#| """Base curricular verificada: competencias, capacidades, desempeños y transversales.
#|
#| Las competencias y capacidades base se cargan una sola vez (marcadas como "por verificar").
#| Los desempeños los carga el administrador (Excel/CSV) desde los Programas Curriculares oficiales.
#| La IA NUNCA inventa estos textos: solo elige entre los que están en esta base.
#| """
#| import streamlit as st
#| from db import fetch, execute
#| from repo import config_get
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
#| @st.cache_data(ttl=300, show_spinner=False)
#| def areas_de(nivel):
#|     filas = fetch("SELECT area, MIN(id) AS m FROM curriculo_competencias WHERE nivel=%s GROUP BY area ORDER BY m",
#|                   (nivel,))
#|     return [f["area"] for f in filas]
#|
#|
#| @st.cache_data(ttl=300, show_spinner=False)
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
#| @st.cache_data(ttl=300, show_spinner=False)
#| def desempenos_de(competencia_id, grado, aid=None):
#|     """Desempeños de una competencia y grado. Si el curso (aid) cargó lineamientos propios, se usan esos."""
#|     if aid:
#|         propios = fetch("SELECT id, texto FROM curriculo_desempenos WHERE competencia_id=%s AND grado=%s "
#|                         "AND asignacion_id=%s ORDER BY orden, id", (competencia_id, grado, aid))
#|         if propios:
#|             return propios
#|     return fetch("SELECT id, texto FROM curriculo_desempenos WHERE competencia_id=%s AND grado=%s "
#|                  "AND asignacion_id IS NULL ORDER BY orden, id", (competencia_id, grado))
#|
#|
#| @st.cache_data(ttl=300, show_spinner=False)
#| def estandar_de(competencia_id, ciclo, aid=None):
#|     if aid:
#|         f = fetch("SELECT texto FROM curriculo_estandares WHERE competencia_id=%s AND ciclo=%s AND asignacion_id=%s "
#|                   "ORDER BY id LIMIT 1", (competencia_id, ciclo, aid), one=True)
#|         if f:
#|             return f["texto"]
#|     f = fetch("SELECT texto FROM curriculo_estandares WHERE competencia_id=%s AND ciclo=%s AND asignacion_id IS NULL "
#|               "ORDER BY id LIMIT 1", (competencia_id, ciclo), one=True)
#|     return f["texto"] if f else ""
#|
#|
#| def detalle_competencia(competencia_id):
#|     return fetch("SELECT fuente, verificado_en FROM curriculo_competencias WHERE id=%s", (competencia_id,), one=True) or {}
#|
#|
#| def bloqueo_curricular(asig):
#|     """Si el administrador activó «exigir currículo verificado», devuelve el motivo del bloqueo (o None)."""
#|     if config_get("exigir_verificado", "0") != "1":
#|         return None
#|     comps = competencias_de(asig["nivel"], asig["area"])
#|     if not comps:
#|         return "Esta área no tiene competencias cargadas en la base curricular oficial."
#|     sin_ver = [c["nombre"] for c in comps if not c["verificado"]]
#|     sin_des = [c["nombre"] for c in comps if not desempenos_de(c["id"], asig["grado"], asig.get("id"))]
#|     if sin_ver or sin_des:
#|         return ("El administrador aún no verificó el currículo oficial de esta área para este grado "
#|                 f"({len(sin_ver)} competencia(s) sin verificar, {len(sin_des)} sin desempeños). "
#|                 "Cuando lo verifique podrás generar documentos.")
#|     return None
#|
#|
#| def estado_area(nivel, area, grado, aid=None):
#|     """(n competencias, n verificadas, n con desempeños para el grado)."""
#|     comps = competencias_de(nivel, area)
#|     con_des = sum(1 for c in comps if desempenos_de(c["id"], grado, aid))
#|     return len(comps), sum(1 for c in comps if c["verificado"]), con_des
#|
#|
#| @st.cache_data(ttl=300, show_spinner=False)
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
#| def contexto_curricular(nivel, area, grado, nombres, aid=None):
#|     """Texto para el prompt + mapa {nombre competencia: {'comp':..., 'des': [...]}} (desempeños numerados D1..Dn)."""
#|     objetivo = {norm(n) for n in nombres}
#|     lineas, mapa = [], {}
#|     for c in competencias_de(nivel, area):
#|         if norm(c["nombre"]) not in objetivo:
#|             continue
#|         ds = desempenos_de(c["id"], grado, aid)
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
#|     if any(u.get("temas") for u in d.get("unidades", [])):
#|         b.append(("sec", "V. TEMAS POR UNIDAD (CLASES)"))
#|         temas = []
#|         for u in d.get("unidades", []):
#|             for i, tm in enumerate(u.get("temas") or [], 1):
#|                 temas.append([f"Unidad {u.get('numero')}", f"Clase {i}", tm.get("titulo"), tm.get("competencia"),
#|                               tm.get("desempeno_texto")])
#|         b.append(("tabla", ["Unidad", "Clase", "Tema", "Competencia", "Desempeño que desarrolla"], temas))
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
#| def bloques_desafio(asig, pdata, d):
#|     b = [("h", (d.get("titulo") or f"DESAFÍOS DE APRENDIZAJE — {pdata.get('titulo', '')}").upper()),
#|          ("kv", [("Institución educativa", asig.get("institucion")), ("Docente", asig.get("docente")),
#|                  ("Área", asig.get("area")), ("Grado y sección", f"{asig.get('grado', '')} {asig.get('seccion') or ''}"),
#|                  ("Tema o unidad", pdata.get("titulo")), ("Modalidad", d.get("modalidad"))], 2),
#|          ("sec", "PRESENTACIÓN"), ("p", d.get("introduccion")), ("sec", "DESAFÍOS")]
#|     for x in d.get("desafios", []):
#|         b.append(("sub", f"Desafío {x.get('numero')}: {s(x.get('nombre'))}  ({x.get('nivel') or ''} · {x.get('puntos') or ''} pts)"))
#|         b.append(("p", x.get("reto")))
#|         if x.get("pasos"):
#|             b.append(("ul", x.get("pasos")))
#|         b.append(("p", "Producto: " + s(x.get("producto"))))
#|         if x.get("criterios"):
#|             b.append(("p", "Lo lograrás si:"))
#|             b.append(("ul", x.get("criterios")))
#|     b += [("salto",), ("sec", "HOJA DE SEGUIMIENTO (SOLO PARA EL DOCENTE)"),
#|           ("tabla", ["Estudiante"] + [f"D{x.get('numero')}" for x in d.get("desafios", [])] + ["Total"],
#|            [[""] * (len(d.get("desafios", [])) + 2) for _ in range(10)])]
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
#|             b.append(("opciones", ops))
#|         elif p.get("tipo") == "desarrollo":
#|             b.append(("p", "______________________________________________________________"))
#|     b += [("salto",), ("sec", "CLAVES DE RESPUESTA (SOLO PARA EL DOCENTE)"),
#|           ("tabla", ["N.°", "Respuesta correcta", "Puntaje"],
#|            [[p.get("numero"), p.get("respuesta"), p.get("puntaje")] for p in d.get("preguntas", [])])]
#|     if any(p.get("desempeno_texto") for p in d.get("preguntas", [])):
#|         b += [("sec", "MATRIZ DE EVALUACIÓN (SOLO PARA EL DOCENTE)"),
#|               ("tabla", ["N.°", "Competencia", "Desempeño evaluado", "Puntaje"],
#|                [[p.get("numero"), p.get("competencia"), p.get("desempeno_texto"), p.get("puntaje")]
#|                 for p in d.get("preguntas", [])])]
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
#|         elif tipo == "opciones":
#|             for item in blq[1]:
#|                 if s(item):
#|                     p = doc.add_paragraph(s(item))
#|                     p.paragraph_format.left_indent = Cm(1)
#|                     p.paragraph_format.space_after = Pt(1)
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
#|         elif tipo == "opciones":
#|             out.append("<div style='margin:2px 0 8px 22px'>" + "".join(f"<div>{_h(i)}</div>" for i in blq[1] if s(i)) + "</div>")
#|         elif tipo == "salto":
#|             out.append("<div class='salto'></div>")
#|     out.append(f"<div class='pie'>Normativa utilizada: {_h(pie or 'RM N.° 501-2025-MINEDU')}</div>")
#|     return "".join(out)
#@@ END
#@@ MODULE exportar
#| """Convierte un documento guardado en bloques listos para vista previa y Word."""
#| from curriculo import competencias_de, transversales
#| from repo import contenido, get_asignacion, get_doc_by_id
#| from render import (bloques_anual, bloques_desafio, bloques_examen, bloques_ficha, bloques_rubrica,
#|                     bloques_sesion, bloques_unidad)
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
#|     if tipo == "desafio":
#|         return bloques_desafio(asig, pdata, d), False, f"desafios_{base}.docx"
#|     if tipo == "examen_unidad":
#|         return bloques_examen(asig, pdata, d), False, f"examen_unidad_{doc.get('numero', 1)}_{base}.docx"
#|     if tipo == "rubrica":
#|         return bloques_rubrica(asig, pdata, d), True, f"rubrica_{base}.docx"
#|     if tipo == "ficha":
#|         return bloques_ficha(asig, pdata, d), False, f"ficha_{base}.docx"
#|     return bloques_examen(asig, pdata, d), False, f"examen_{base}.docx"
#@@ END
#@@ MODULE ia
#| """IA: OpenRouter primero y Gemini de respaldo, de forma automática.
#| Las claves se leen primero del panel de Administración (base de datos) y, si no hay, de Secrets.
#| Nunca se muestran ni se guardan en los registros."""
#| import json
#| import re
#| import time
#|
#| import requests
#| import streamlit as st
#|
#| TIMEOUT = (10, 90)  # (segundos para conectar, segundos para esperar la respuesta)
#| ORDEN = ["openrouter", "gemini"]
#| PROVEEDORES = {
#|     "openrouter": {"nombre": "OpenRouter", "modelo": "openai/gpt-4o-mini"},
#|     "gemini": {"nombre": "Gemini", "modelo": "gemini-3.8-flash"},
#| }
#|
#|
#| class ErrorIA(RuntimeError):
#|     def __init__(self, status, detalle):
#|         super().__init__(f"{status}: {detalle}" if status else str(detalle))
#|         self.status = status
#|
#|
#| # ------------------------------------------------------------------
#| # Claves y modelos (panel de Administración primero, Secrets después)
#| # ------------------------------------------------------------------
#| def _db(clave):
#|     try:
#|         from db import fetch
#|         f = fetch("SELECT valor FROM config WHERE clave=%s", (clave,), one=True)
#|         return (f["valor"] or "").strip() if f else ""
#|     except Exception:
#|         return ""
#|
#|
#| def _secret(seccion, campo):
#|     try:
#|         return str(st.secrets[seccion].get(campo, "") or "").strip()
#|     except Exception:
#|         return ""
#|
#|
#| def clave_de(prov):
#|     return _db(f"ia_{prov}_key") or _secret(prov, "api_key")
#|
#|
#| def origen_clave(prov):
#|     if _db(f"ia_{prov}_key"):
#|         return "panel"
#|     return "secrets" if _secret(prov, "api_key") else ""
#|
#|
#| def modelo_de(prov):
#|     return _db(f"ia_{prov}_model") or _secret(prov, "model") or PROVEEDORES[prov]["modelo"]
#|
#|
#| def _limpiar(texto):
#|     """Quita cualquier clave del texto antes de mostrarlo o guardarlo."""
#|     t = str(texto)
#|     for p in PROVEEDORES:
#|         k = clave_de(p)
#|         if k and len(k) > 6:
#|             t = t.replace(k, "***")
#|     t = re.sub(r"(sk-[A-Za-z0-9_\-]{8,}|AIza[A-Za-z0-9_\-]{10,})", "***", t)
#|     return t[:300]
#|
#|
#| # ------------------------------------------------------------------
#| # Registro técnico seguro (tabla nueva ia_registro; no toca nada existente)
#| # ------------------------------------------------------------------
#| @st.cache_resource(show_spinner=False)
#| def _tabla_registro():
#|     from db import conexion
#|     c = conexion()
#|     try:
#|         cur = c.cursor()
#|         cur.execute("""CREATE TABLE IF NOT EXISTS ia_registro (
#|             id INT AUTO_INCREMENT PRIMARY KEY,
#|             creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#|             proveedor VARCHAR(20),
#|             modelo VARCHAR(120),
#|             ok TINYINT(1),
#|             ms INT,
#|             motivo VARCHAR(120),
#|             detalle VARCHAR(400)
#|         )""")
#|         c.commit()
#|         cur.close()
#|     finally:
#|         c.close()
#|     return True
#|
#|
#| def _registrar(prov, ok, ms, motivo, detalle=""):
#|     try:
#|         _tabla_registro()
#|         from db import execute
#|         execute("INSERT INTO ia_registro (proveedor, modelo, ok, ms, motivo, detalle) VALUES (%s,%s,%s,%s,%s,%s)",
#|                 (prov, modelo_de(prov)[:120], 1 if ok else 0, int(ms), motivo[:120], _limpiar(detalle)[:400]))
#|     except Exception:
#|         pass  # el registro nunca debe romper la generación
#|
#|
#| def registros_recientes(n=20):
#|     try:
#|         _tabla_registro()
#|         from db import fetch
#|         return fetch("SELECT creado_en, proveedor, modelo, ok, ms, motivo, detalle FROM ia_registro "
#|                      "ORDER BY id DESC LIMIT %s", (int(n),))
#|     except Exception:
#|         return []
#|
#|
#| # ------------------------------------------------------------------
#| # Llamadas a cada proveedor (una sola vez, sin reintentos)
#| # ------------------------------------------------------------------
#| def _post(url, **kw):
#|     r = requests.post(url, timeout=TIMEOUT, **kw)
#|     if r.status_code >= 400:
#|         try:
#|             det = r.json().get("error", {})
#|             det = det.get("message", r.text) if isinstance(det, dict) else str(det)
#|         except ValueError:
#|             det = r.text
#|         raise ErrorIA(r.status_code, _limpiar(det))
#|     return r
#|
#|
#| def llamar_openrouter(prompt: str) -> str:
#|     k = clave_de("openrouter")
#|     if not k:
#|         raise ErrorIA(None, "sin clave")
#|     r = _post("https://openrouter.ai/api/v1/chat/completions",
#|               headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json", "X-Title": "EduPeru IA"},
#|               json={"model": modelo_de("openrouter"), "messages": [{"role": "user", "content": prompt}],
#|                     "max_tokens": 6000})
#|     datos = r.json()
#|     if isinstance(datos, dict) and datos.get("error"):
#|         e = datos["error"]
#|         raise ErrorIA(e.get("code") if isinstance(e, dict) else None,
#|                       _limpiar(e.get("message") if isinstance(e, dict) else e))
#|     try:
#|         return datos["choices"][0]["message"]["content"] or ""
#|     except (KeyError, IndexError, TypeError):
#|         raise ErrorIA(None, "respuesta con formato inesperado")
#|
#|
#| def llamar_gemini(prompt: str) -> str:
#|     k = clave_de("gemini")
#|     if not k:
#|         raise ErrorIA(None, "sin clave")
#|     r = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{modelo_de('gemini')}:generateContent",
#|               headers={"x-goog-api-key": k, "Content-Type": "application/json"},  # la clave NO va en la URL
#|               json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": 8000}})
#|     cand = r.json().get("candidates") or []
#|     if not cand:
#|         raise ErrorIA(None, "Gemini no devolvió texto (posible bloqueo de contenido)")
#|     partes = (cand[0].get("content") or {}).get("parts") or []
#|     return "".join(p.get("text", "") for p in partes)
#|
#|
#| _LLAMAR = {"openrouter": llamar_openrouter, "gemini": llamar_gemini}
#|
#|
#| def _motivo(e):
#|     """Explicación corta y sin datos sensibles, en lenguaje claro."""
#|     if isinstance(e, requests.exceptions.Timeout):
#|         return "tardó demasiado en responder"
#|     if isinstance(e, requests.exceptions.ConnectionError):
#|         return "no hubo conexión con el servicio"
#|     st_ = getattr(e, "status", None)
#|     txt = str(e).lower()
#|     if st_ in (401, 403) or ("api key" in txt and "valid" in txt):
#|         return "clave rechazada (inválida, vencida o sin permiso)"
#|     if st_ == 402:
#|         return "sin saldo o créditos en la cuenta del proveedor"
#|     if st_ == 404:
#|         return "modelo no encontrado (revisa el nombre del modelo)"
#|     if st_ == 429:
#|         return "límite de uso alcanzado"
#|     if isinstance(st_, int) and st_ >= 500:
#|         return "el servicio tiene fallas temporales"
#|     if "sin clave" in txt:
#|         return "sin clave configurada"
#|     return "respondió con un error"
#|
#|
#| def generar_texto(prompt: str):
#|     """Devuelve (texto, proveedor). Siempre prueba OpenRouter primero; si falla, pasa a Gemini.
#|     Si el primero respondió bien, NO se llama al segundo (no se duplica el contenido)."""
#|     fallos = []
#|     for prov in ORDEN:
#|         nombre = PROVEEDORES[prov]["nombre"]
#|         if not clave_de(prov):
#|             fallos.append((nombre, "sin clave configurada"))
#|             continue
#|         t0 = time.time()
#|         try:
#|             texto = _LLAMAR[prov](prompt)
#|             if not (texto or "").strip():
#|                 raise ErrorIA(None, "respuesta vacía")
#|         except Exception as e:
#|             motivo = _motivo(e)
#|             _registrar(prov, False, (time.time() - t0) * 1000, motivo, str(e))
#|             fallos.append((nombre, motivo))
#|             continue
#|         _registrar(prov, True, (time.time() - t0) * 1000, "ok")
#|         return texto, nombre
#|     detalle = "; ".join(f"{n}: {m}" for n, m in fallos)
#|     raise RuntimeError(f"La IA no está disponible en este momento ({detalle}). No se descontaron créditos. "
#|                        "Intenta de nuevo en unos minutos; si continúa, avisa al administrador.")
#|
#|
#| def probar_proveedor(prov):
#|     """Para el panel de Administración: (ok, mensaje, milisegundos). No usa el otro proveedor."""
#|     if not clave_de(prov):
#|         return False, "No hay clave configurada.", 0
#|     t0 = time.time()
#|     try:
#|         res = _LLAMAR[prov]("Responde solo con la palabra: ok")
#|         ms = (time.time() - t0) * 1000
#|         _registrar(prov, True, ms, "prueba ok")
#|         return True, f"Respondió: {res.strip()[:40]}", ms
#|     except Exception as e:
#|         ms = (time.time() - t0) * 1000
#|         _registrar(prov, False, ms, _motivo(e), str(e))
#|         return False, f"{_motivo(e)} · {_limpiar(e)}", ms
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
#|     """Devuelve (datos, proveedor). Reintenta una vez SOLO si la IA respondió pero no con JSON válido."""
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
#@@ MODULE programas
#| """Programas Curriculares oficiales (PDF de gob.pe): buscar, leer, extraer desempeños y verificarlos.
#|
#| Reglas de oro:
#| - La IA NO busca en internet ni inventa: el sistema descarga las páginas oficiales y la IA solo ordena texto.
#| - Todo desempeño/estándar que la IA devuelva debe aparecer en el PDF (comparación tolerante a saltos de línea
#|   y signos); si no aparece, se descarta.
#| - Lo extraído entra como «pendiente» y solo el administrador lo aprueba.
#| """
#| import hashlib
#| import io
#| import re
#| from urllib.parse import urljoin
#|
#| import requests
#| from bs4 import BeautifulSoup
#|
#| from curriculo import GRADOS, areas_de, competencias_de
#| from db import execute, execute_many, fetch
#| from ia import pedir_json
#| from util import norm, s
#|
#| UA = {"User-Agent": "Mozilla/5.0 (compatible; EduPeruIA-Programas/1.0)"}
#| PORTALES = [
#|     "https://www.gob.pe/es/90158-ministerio-de-educacion-programas-curriculares-de-la-educacion-basica-regular",
#|     "https://www.gob.pe/institucion/minedu/campa%C3%B1as/106784-curriculo-nacional-de-la-educacion-basica",
#| ]
#| MAX_MB = 120
#| CICLOS_VALIDOS = ["II", "III", "IV", "V", "VI", "VII"]
#|
#|
#| def nivel_probable(texto):
#|     t = norm(texto)
#|     for n in ("inicial", "primaria", "secundaria"):
#|         if n in t:
#|             return n.capitalize()
#|     return ""
#|
#|
#| # ------------------------------------------------------------------
#| # 1) BUSCAR en las páginas oficiales
#| # ------------------------------------------------------------------
#| def _titulo_pagina(soup):
#|     h = soup.find("h1") or soup.title
#|     return h.get_text(" ", strip=True) if h else ""
#|
#|
#| def _firma_remota(url):
#|     try:
#|         h = requests.head(url, headers=UA, timeout=20, allow_redirects=True)
#|         return "|".join(h.headers.get(k, "") for k in ("ETag", "Last-Modified", "Content-Length"))[:300]
#|     except Exception:
#|         return ""
#|
#|
#| def buscar_programas():
#|     """Recorre las páginas oficiales y registra los PDF de Programas Curriculares.
#|     Devuelve (lista de PDF registrados, lista de avisos/errores)."""
#|     avisos, hallados, vistos = [], {}, set()
#|     por_visitar = list(PORTALES)
#|     for paso in range(2):
#|         siguientes = []
#|         for url in por_visitar:
#|             if url in vistos:
#|                 continue
#|             vistos.add(url)
#|             try:
#|                 r = requests.get(url, headers=UA, timeout=40)
#|                 r.raise_for_status()
#|             except Exception as e:
#|                 avisos.append(f"No se pudo abrir {url}: {e}")
#|                 continue
#|             soup = BeautifulSoup(r.text, "html.parser")
#|             titulo_pag = _titulo_pagina(soup)
#|             for a in soup.find_all("a", href=True):
#|                 href = urljoin(url, a["href"]).split("#")[0]
#|                 texto = a.get_text(" ", strip=True)
#|                 if href.lower().split("?")[0].endswith(".pdf"):
#|                     # Si el enlace dice solo «Descargar», se usa el título de la página; si dice otra cosa, se usa su texto
#|                     generico = norm(texto) in ("", "descargar", "ver", "descargar pdf", "pdf", "descargar archivo")
#|                     titulo = titulo_pag if generico else texto
#|                     contexto = norm(f"{titulo} {href}")
#|                     if "curricul" in contexto or "programa" in contexto:
#|                         hallados.setdefault(href, {"url": href, "titulo": titulo[:300], "origen": url})
#|                 elif paso == 0 and "gob.pe" in href and (
#|                         "programa-curricular" in href.lower() or "programa curricular" in norm(texto)):
#|                     siguientes.append(href)
#|         por_visitar = siguientes[:20]
#|     if not hallados:
#|         avisos.append("No se encontraron PDF en las páginas oficiales (puede que gob.pe cargue su contenido con "
#|                       "JavaScript o bloquee el acceso). Usa «Pegar URL» o «Subir PDF».")
#|
#|     nuevos = []
#|     for url, h in hallados.items():
#|         ex = fetch("SELECT id, firma, estado FROM curriculo_pdf WHERE url=%s", (url,), one=True)
#|         if ex is None:
#|             nid, _ = execute("INSERT INTO curriculo_pdf (url, titulo, nivel, origen, firma, estado) "
#|                              "VALUES (%s,%s,%s,%s,%s,'nuevo')",
#|                              (url, h["titulo"], nivel_probable(f"{h['titulo']} {url} {h['origen']}"), h["origen"],
#|                               _firma_remota(url)))
#|             nuevos.append(nid)
#|         elif ex["estado"] == "leido":
#|             firma = _firma_remota(url)
#|             if firma and ex["firma"] and firma != ex["firma"]:
#|                 execute("UPDATE curriculo_pdf SET estado='actualizado', firma=%s WHERE id=%s", (firma, ex["id"]))
#|     _clasificar_con_ia(nuevos)
#|     return fetch("SELECT * FROM curriculo_pdf ORDER BY id DESC"), avisos
#|
#|
#| def _clasificar_con_ia(ids):
#|     """La IA solo ayuda a decidir el nivel de los PDF cuyo título no lo dice (no navega por internet)."""
#|     pend = [f for f in (fetch("SELECT id, titulo, url, nivel FROM curriculo_pdf WHERE id=%s", (i,), one=True) for i in ids)
#|             if f and not f["nivel"]]
#|     if not pend:
#|         return
#|     lista = "\n".join(f"{i}. título: {f['titulo']} | url: {f['url']}" for i, f in enumerate(pend))
#|     try:
#|         datos, _ = pedir_json(
#|             "Clasifica estos documentos publicados por el MINEDU (Perú). Para cada uno indica a qué nivel de la "
#|             "Educación Básica Regular corresponde (Inicial, Primaria, Secundaria) o 'Otro', y si es un Programa "
#|             f"Curricular oficial (true/false).\n{lista}\n"
#|             'Formato: {"clasificacion":[{"i":0,"nivel":"Primaria","es_programa":true}]}')
#|         for x in datos.get("clasificacion", []):
#|             f = pend[int(x["i"])]
#|             nivel = x.get("nivel") if x.get("nivel") in ("Inicial", "Primaria", "Secundaria") else ""
#|             estado = "nuevo" if x.get("es_programa", True) else "descartado"
#|             execute("UPDATE curriculo_pdf SET nivel=%s, estado=%s WHERE id=%s", (nivel, estado, f["id"]))
#|     except Exception:
#|         pass  # el administrador puede elegir el nivel a mano
#|
#|
#| # ------------------------------------------------------------------
#| # 2) DESCARGAR y LEER el PDF (se guarda el texto por página)
#| # ------------------------------------------------------------------
#| def registrar_url(url, titulo="", nivel=""):
#|     ex = fetch("SELECT id FROM curriculo_pdf WHERE url=%s", (url,), one=True)
#|     if ex:
#|         return ex["id"]
#|     nid, _ = execute("INSERT INTO curriculo_pdf (url, titulo, nivel, origen, estado) VALUES (%s,%s,%s,%s,'nuevo')",
#|                      (url, titulo or url[-80:], nivel or nivel_probable(f"{titulo} {url}"), "manual"))
#|     return nid
#|
#|
#| def _guardar_paginas(pdf_id, datos: bytes, firma=""):
#|     from pypdf import PdfReader
#|     lector = PdfReader(io.BytesIO(datos))
#|     execute("DELETE FROM curriculo_pdf_paginas WHERE pdf_id=%s", (pdf_id,))
#|     filas = []
#|     for n, pagina in enumerate(lector.pages, 1):
#|         try:
#|             texto = pagina.extract_text() or ""
#|         except Exception:
#|             texto = ""
#|         filas.append((pdf_id, n, texto))
#|         if len(filas) >= 40:
#|             execute_many("INSERT INTO curriculo_pdf_paginas (pdf_id, pagina, texto) VALUES (%s,%s,%s)", filas)
#|             filas = []
#|     execute_many("INSERT INTO curriculo_pdf_paginas (pdf_id, pagina, texto) VALUES (%s,%s,%s)", filas)
#|     execute("UPDATE curriculo_pdf SET paginas=%s, hash_contenido=%s, firma=%s, estado='leido', leido_en=NOW() WHERE id=%s",
#|             (len(lector.pages), hashlib.sha256(datos).hexdigest(), firma or "", pdf_id))
#|     return len(lector.pages)
#|
#|
#| def descargar_y_leer(pdf_id):
#|     f = fetch("SELECT url FROM curriculo_pdf WHERE id=%s", (pdf_id,), one=True)
#|     r = requests.get(f["url"], headers=UA, timeout=180, stream=True)
#|     r.raise_for_status()
#|     datos = b""
#|     for trozo in r.iter_content(1024 * 512):
#|         datos += trozo
#|         if len(datos) > MAX_MB * 1024 * 1024:
#|             raise RuntimeError(f"El PDF pesa más de {MAX_MB} MB.")
#|     if not datos.startswith(b"%PDF"):
#|         raise RuntimeError("El enlace no devolvió un PDF (puede requerir abrirse desde el navegador).")
#|     firma = "|".join(r.headers.get(k, "") for k in ("ETag", "Last-Modified", "Content-Length"))[:300]
#|     return _guardar_paginas(pdf_id, datos, firma)
#|
#|
#| def leer_subido(nombre, datos: bytes, nivel=""):
#|     if not datos.startswith(b"%PDF"):
#|         raise RuntimeError("El archivo no es un PDF.")
#|     pdf_id = registrar_url(f"subido:{nombre}", nombre, nivel)
#|     return pdf_id, _guardar_paginas(pdf_id, datos)
#|
#|
#| # ------------------------------------------------------------------
#| # 3) EXTRAER con IA y VERIFICAR contra el texto del PDF
#| # ------------------------------------------------------------------
#| def mapear_grado(valor, nivel):
#|     m = re.search(r"\d", str(valor or ""))
#|     if not m:
#|         return None
#|     n = m.group(0)
#|     for g in GRADOS[nivel]:
#|         if g.startswith(n):
#|             return g
#|     return None
#|
#|
#| def mapear_ciclo(valor):
#|     v = str(valor or "").upper().replace("CICLO", "").strip()
#|     return v if v in CICLOS_VALIDOS else None
#|
#|
#| def _pagina_de(texto_norm, paginas):
#|     for numero, _, pn in paginas:
#|         if texto_norm in pn:
#|             return numero
#|     return 0
#|
#|
#| def extraer_items(paginas, nivel, trabajos, progreso=None):
#|     """Núcleo de la extracción: devuelve (items, resumen).
#|     paginas = [(n, texto, texto_normalizado)], trabajos = [(area, competencia)].
#|     item = (competencia_id, tipo, grado_o_ciclo, texto_verificado, pagina)."""
#|     resumen = {"verificados": 0, "descartados": 0, "sin_paginas": []}
#|     items = []
#|     for k, (area, c) in enumerate(trabajos, 1):
#|         if progreso:
#|             progreso(k / len(trabajos), f"{area} · {c['nombre'][:60]}")
#|         clave = norm(c["nombre"])[:70]
#|         cand = [p for p in paginas if clave in p[2] and ("desempe" in p[2] or "estandar" in p[2])][:8]
#|         if not cand:
#|             resumen["sin_paginas"].append(f"{area}: {c['nombre']}")
#|             continue
#|         plano = " ".join(p[2] for p in cand)
#|         texto = "\n".join(f"[Página {p[0]}]\n{p[1]}" for p in cand)[:24000]
#|         try:
#|             datos, _ = pedir_json(f"""Del siguiente texto de un Programa Curricular (lineamientos oficiales, Perú), nivel {nivel}, extrae para la competencia «{c['nombre']}»:
#| - "desempenos": los desempeños de cada grado ({', '.join(GRADOS[nivel])}). Cada uno con "grado" y "texto".
#| - "estandares": el estándar de aprendizaje de cada ciclo. Cada uno con "ciclo" (II, III, IV, V, VI o VII) y "texto".
#| COPIA cada texto EXACTAMENTE como aparece en el documento, sin cambiar, resumir ni agregar palabras. Si no encuentras algo, no lo incluyas. No inventes.
#| Formato: {{"desempenos":[{{"grado":"3.° grado","texto":"..."}}],"estandares":[{{"ciclo":"IV","texto":"..."}}]}}
#|
#| TEXTO:
#| {texto}""")
#|         except Exception:
#|             resumen["sin_paginas"].append(f"{area}: {c['nombre']} (la IA no respondió)")
#|             continue
#|         for tipo, lista, mapear in (("desempeno", datos.get("desempenos") or [], lambda x: mapear_grado(x.get("grado"), nivel)),
#|                                     ("estandar", datos.get("estandares") or [], lambda x: mapear_ciclo(x.get("ciclo")))):
#|             for x in lista:
#|                 if not isinstance(x, dict):
#|                     continue
#|                 clave_g, t = mapear(x), s(x.get("texto"))
#|                 tn = norm(t)
#|                 if clave_g and len(tn) > 25 and tn in plano:
#|                     items.append((c["id"], tipo, clave_g, t, _pagina_de(tn, cand)))
#|                     resumen["verificados"] += 1
#|                 else:
#|                     resumen["descartados"] += 1
#|     return items, resumen
#|
#|
#| def paginas_guardadas(pdf_id):
#|     filas = fetch("SELECT pagina, texto FROM curriculo_pdf_paginas WHERE pdf_id=%s ORDER BY pagina", (pdf_id,))
#|     if not filas:
#|         raise RuntimeError("Primero hay que descargar y leer el PDF.")
#|     return [(f["pagina"], f["texto"], norm(f["texto"])) for f in filas]
#|
#|
#| def poner_en_cola(pdf_id, items):
#|     """Deja los textos extraídos como «pendientes» para que el administrador los apruebe."""
#|     for cid in {i[0] for i in items}:
#|         execute("DELETE FROM curriculo_importado WHERE pdf_id=%s AND competencia_id=%s AND estado='pendiente'",
#|                 (pdf_id, cid))
#|     execute_many("INSERT INTO curriculo_importado (pdf_id, competencia_id, tipo, grado, texto, pagina) "
#|                  "VALUES (%s,%s,%s,%s,%s,%s)", [(pdf_id,) + i for i in items])
#|
#|
#| def extraer(pdf_id, nivel, areas=None, progreso=None):
#|     """Extrae desempeños y estándares del PDF ya leído y los deja pendientes de aprobación."""
#|     paginas = paginas_guardadas(pdf_id)
#|     trabajos = [(a, c) for a in (areas or areas_de(nivel)) for c in competencias_de(nivel, a)]
#|     items, resumen = extraer_items(paginas, nivel, trabajos, progreso)
#|     poner_en_cola(pdf_id, items)
#|     return resumen
#|
#|
#| # ------------------------------------------------------------------
#| # 4) REVISIÓN: aprobar / rechazar
#| # ------------------------------------------------------------------
#| def pendientes(pdf_id):
#|     return fetch("SELECT i.id, i.competencia_id, c.area, c.nombre AS competencia, i.tipo, i.grado, i.texto, i.pagina "
#|                  "FROM curriculo_importado i JOIN curriculo_competencias c ON c.id = i.competencia_id "
#|                  "WHERE i.pdf_id=%s AND i.estado='pendiente' ORDER BY c.area, c.id, i.tipo, i.grado, i.id", (pdf_id,))
#|
#|
#| def aprobar(ids, marcar_verificada=True, fuente=""):
#|     """Pasa lo aprobado a la base curricular (reemplaza lo anterior de esa competencia y grado/ciclo)."""
#|     if not ids:
#|         return 0
#|     marcas = ",".join(["%s"] * len(ids))
#|     filas = fetch(f"SELECT * FROM curriculo_importado WHERE id IN ({marcas}) ORDER BY id", tuple(ids))
#|     grupos = {}
#|     for f in filas:
#|         grupos.setdefault((f["competencia_id"], f["tipo"], f["grado"]), []).append(f)
#|     for (cid, tipo, clave), items in grupos.items():
#|         if tipo == "desempeno":
#|             execute("DELETE FROM curriculo_desempenos WHERE competencia_id=%s AND grado=%s AND asignacion_id IS NULL", (cid, clave))
#|             execute_many("INSERT INTO curriculo_desempenos (competencia_id, grado, texto, orden) VALUES (%s,%s,%s,%s)",
#|                          [(cid, clave, x["texto"], i) for i, x in enumerate(items, 1)])
#|         else:
#|             execute("DELETE FROM curriculo_estandares WHERE competencia_id=%s AND ciclo=%s AND asignacion_id IS NULL", (cid, clave))
#|             execute("INSERT INTO curriculo_estandares (competencia_id, ciclo, texto) VALUES (%s,%s,%s)",
#|                     (cid, clave, items[0]["texto"]))
#|     if marcar_verificada:
#|         for cid in {f["competencia_id"] for f in filas}:
#|             execute("UPDATE curriculo_competencias SET verificado=1, verificado_en=NOW(), fuente=%s WHERE id=%s",
#|                     (fuente[:600], cid))
#|     execute(f"UPDATE curriculo_importado SET estado='aprobado' WHERE id IN ({marcas})", tuple(ids))
#|     return len(filas)
#|
#|
#| def rechazar(ids):
#|     if ids:
#|         marcas = ",".join(["%s"] * len(ids))
#|         execute(f"UPDATE curriculo_importado SET estado='rechazado' WHERE id IN ({marcas})", tuple(ids))
#@@ END
#@@ MODULE lineamientos
#| """Lineamientos por curso: traerlos del MINEDU (con IA) o leer los que sube el docente (PDF / Word).
#| Se guardan SOLO para ese curso (no cambian el currículo de los demás) y siempre se verifican contra el texto."""
#| import io
#| import re
#|
#| from curriculo import competencias_de
#| from db import execute, execute_many, fetch
#| from programas import (buscar_programas, descargar_y_leer, extraer_items, nivel_probable, paginas_guardadas,
#|                        poner_en_cola)
#| from repo import actualizar_asignacion
#| from util import norm
#|
#|
#| def paginas_de_archivo(nombre, datos: bytes):
#|     """Convierte un PDF, Word o TXT en páginas [(n, texto, normalizado)]."""
#|     bajo = nombre.lower()
#|     if bajo.endswith(".pdf"):
#|         from pypdf import PdfReader
#|         lector = PdfReader(io.BytesIO(datos))
#|         textos = [(p.extract_text() or "") for p in lector.pages]
#|     elif bajo.endswith(".docx"):
#|         from docx import Document
#|         d = Document(io.BytesIO(datos))
#|         lineas = [p.text for p in d.paragraphs if p.text.strip()]
#|         for t in d.tables:
#|             for fila in t.rows:
#|                 lineas.append(" | ".join(c.text.strip() for c in fila.cells))
#|         textos, actual = [], ""
#|         for l in lineas:                         # páginas artificiales de ~3000 caracteres
#|             if len(actual) + len(l) > 3000:
#|                 textos.append(actual)
#|                 actual = ""
#|             actual += l + "\n"
#|         textos.append(actual)
#|     elif bajo.endswith(".txt"):
#|         crudo = datos.decode("utf-8", errors="ignore")
#|         textos = [crudo[i:i + 3000] for i in range(0, len(crudo), 3000)] or [""]
#|     else:
#|         raise RuntimeError("Solo se pueden leer archivos PDF, Word (.docx) o TXT.")
#|     return [(i, t, norm(t)) for i, t in enumerate(textos, 1)]
#|
#|
#| def _guardar_propios(asig, items, fuente):
#|     """Guarda lo extraído como lineamientos propios del curso (reemplaza lo propio anterior de esas competencias)."""
#|     aid = asig["id"]
#|     for cid in {i[0] for i in items}:
#|         execute("DELETE FROM curriculo_desempenos WHERE competencia_id=%s AND asignacion_id=%s", (cid, aid))
#|         execute("DELETE FROM curriculo_estandares WHERE competencia_id=%s AND asignacion_id=%s", (cid, aid))
#|     des = [(i[0], i[2], i[3], k, aid) for k, i in enumerate((x for x in items if x[1] == "desempeno"), 1)]
#|     est = [(i[0], i[2], i[3], aid) for i in items if i[1] == "estandar"]
#|     execute_many("INSERT INTO curriculo_desempenos (competencia_id, grado, texto, orden, asignacion_id) VALUES (%s,%s,%s,%s,%s)", des)
#|     execute_many("INSERT INTO curriculo_estandares (competencia_id, ciclo, texto, asignacion_id) VALUES (%s,%s,%s,%s)", est)
#|     actualizar_asignacion(aid, lineamientos_fuente=fuente[:300])
#|     return len(des), len(est)
#|
#|
#| def _trabajos(asig):
#|     return [(asig["area"], c) for c in competencias_de(asig["nivel"], asig["area"])]
#|
#|
#| def desde_archivo(asig, nombre, datos, progreso=None):
#|     """El docente sube sus lineamientos: se lee, se extrae con IA y se verifica contra su propio archivo."""
#|     paginas = paginas_de_archivo(nombre, datos)
#|     items, resumen = extraer_items(paginas, asig["nivel"], _trabajos(asig), progreso)
#|     if not items:
#|         raise RuntimeError("No se encontraron desempeños en tu archivo para las competencias de este curso. "
#|                            "Revisa que el archivo contenga los desempeños por grado.")
#|     resumen["desempenos"], resumen["estandares"] = _guardar_propios(asig, items, f"Archivo propio: {nombre}")
#|     return resumen
#|
#|
#| def _pdf_del_nivel(nivel):
#|     filas = fetch("SELECT * FROM curriculo_pdf WHERE estado IN ('leido','actualizado') AND paginas>0 "
#|                   "AND nivel=%s ORDER BY (estado='leido') DESC, id DESC", (nivel,))
#|     return filas[0] if filas else None
#|
#|
#| def traer_oficial(asig, progreso=None):
#|     """Busca el Programa Curricular oficial del nivel (si no está leído lo descarga) y trae los lineamientos del curso."""
#|     pdf = _pdf_del_nivel(asig["nivel"])
#|     if pdf is None:
#|         if progreso:
#|             progreso(0.05, "Buscando el Programa Curricular en gob.pe…")
#|         lista, _ = buscar_programas()
#|         cand = [p for p in lista if p["nivel"] == asig["nivel"] and p["estado"] != "descartado"]
#|         if not cand:
#|             raise RuntimeError("No encontré el Programa Curricular de tu nivel en las páginas oficiales. "
#|                                "Pídele al administrador que lo cargue, o sube tus lineamientos en PDF o Word.")
#|         if progreso:
#|             progreso(0.1, "Descargando el PDF oficial (puede tardar)…")
#|         pdf = cand[0]
#|         descargar_y_leer(pdf["id"])
#|     paginas = paginas_guardadas(pdf["id"])
#|     items, resumen = extraer_items(paginas, asig["nivel"], _trabajos(asig),
#|                                    (lambda f, t: progreso(0.2 + 0.8 * f, t)) if progreso else None)
#|     if not items:
#|         raise RuntimeError("No pude verificar desempeños de este curso en el PDF oficial. "
#|                            "Puedes subir tus lineamientos en PDF o Word.")
#|     poner_en_cola(pdf["id"], items)        # el administrador podrá aprobarlos para todos
#|     resumen["desempenos"], resumen["estandares"] = _guardar_propios(asig, items, f"MINEDU (PDF oficial): {pdf['titulo'] or pdf['url']}")
#|     return resumen
#|
#|
#| def usar_oficial(asig):
#|     """Vuelve a usar el currículo oficial del sistema (borra los lineamientos propios del curso)."""
#|     execute("DELETE FROM curriculo_desempenos WHERE asignacion_id=%s", (asig["id"],))
#|     execute("DELETE FROM curriculo_estandares WHERE asignacion_id=%s", (asig["id"],))
#|     actualizar_asignacion(asig["id"], lineamientos_fuente="")
#@@ END
#@@ MODULE calendario
#| """Calendario docente: eventos, programación automática de clases y sugerencias con IA."""
#| import calendar
#| import datetime as dt
#| import re
#|
#| from db import execute, fetch
#| from ia import pedir_json, preambulo
#| from repo import contenido, get_doc, listar_docs
#| from util import s
#|
#| TIPOS = {"clase": ("📖", "Clase"), "examen": ("📝", "Examen"), "actividad": ("🎯", "Actividad"),
#|          "reunion": ("👥", "Reunión"), "otro": ("📌", "Otro")}
#| DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
#| MESES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Setiembre", "Octubre",
#|          "Noviembre", "Diciembre"]
#| AUTO = "[auto]"
#|
#|
#| def eventos_mes(uid, año, mes, aid=None):
#|     ini = dt.date(año, mes, 1)
#|     fin = dt.date(año, mes, calendar.monthrange(año, mes)[1])
#|     sql = "SELECT * FROM eventos WHERE usuario_id=%s AND fecha>=%s AND fecha<=%s"
#|     params = [uid, ini, fin]
#|     if aid:
#|         sql += " AND (asignacion_id=%s OR asignacion_id IS NULL)"
#|         params.append(aid)
#|     return fetch(sql + " ORDER BY fecha, id", tuple(params))
#|
#|
#| def agregar(uid, aid, fecha, tipo, titulo, detalle="", doc_id=None):
#|     nuevo, _ = execute("INSERT INTO eventos (usuario_id, asignacion_id, fecha, tipo, titulo, detalle, doc_id) "
#|                        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
#|                        (uid, aid, fecha, tipo if tipo in TIPOS else "otro", titulo[:255], detalle, doc_id))
#|     return nuevo
#|
#|
#| def borrar(evento_id, uid):
#|     execute("DELETE FROM eventos WHERE id=%s AND usuario_id=%s", (evento_id, uid))
#|
#|
#| def parsear_fechas(texto):
#|     """Lee fechas dd/mm/aaaa separadas por comas, espacios o saltos de línea. Devuelve (set de fechas, inválidas)."""
#|     validas, invalidas = set(), []
#|     for trozo in re.split(r"[,\n;]+", texto or ""):
#|         trozo = trozo.strip()
#|         if not trozo:
#|             continue
#|         try:
#|             validas.add(dt.datetime.strptime(trozo, "%d/%m/%Y").date())
#|         except ValueError:
#|             invalidas.append(trozo)
#|     return validas, invalidas
#|
#|
#| def programar_clases(uid, asig, inicio, dias_semana, sin_clase=frozenset(), con_examen=True):
#|     """Reparte las clases del sílabo (y un examen al final de cada unidad) en las fechas elegidas.
#|     Reemplaza lo que se programó antes automáticamente para este curso. Devuelve cuántos eventos creó."""
#|     if not dias_semana:
#|         raise ValueError("Elige al menos un día de clase.")
#|     aid = asig["id"]
#|     anual = get_doc(aid, "anual")
#|     unidades = (contenido(anual).get("unidades") if anual else None) or []
#|     if not unidades:
#|         raise ValueError("Primero crea tu sílabo anual.")
#|     execute("DELETE FROM eventos WHERE usuario_id=%s AND asignacion_id=%s AND detalle LIKE %s", (uid, aid, AUTO + "%"))
#|
#|     fecha = [inicio]
#|
#|     def siguiente():
#|         for _ in range(800):
#|             d = fecha[0]
#|             fecha[0] = d + dt.timedelta(days=1)
#|             if d.weekday() in dias_semana and d not in sin_clase:
#|                 return d
#|         raise ValueError("No hay fechas disponibles con esos días.")
#|
#|     creados = 0
#|     for ua in unidades:
#|         udoc = get_doc(aid, "unidad", numero=ua["numero"])
#|         sesiones = listar_docs(aid, "sesion", padre_id=udoc["id"]) if udoc else []
#|         if sesiones:
#|             clases = [(contenido(x).get("titulo") or x["titulo"], x["id"]) for x in sesiones]
#|         else:
#|             clases = [(t["titulo"], None) for t in ua.get("temas") or []]
#|         for i, (titulo, doc_id) in enumerate(clases, 1):
#|             agregar(uid, aid, siguiente(), "clase", f"U{ua['numero']} · Clase {i}: {titulo}", AUTO, doc_id)
#|             creados += 1
#|         if con_examen and clases:
#|             agregar(uid, aid, siguiente(), "examen", f"Examen de la Unidad {ua['numero']}: {ua['titulo']}", AUTO)
#|             creados += 1
#|     return creados
#|
#|
#| def sugerir_con_ia(asig, año, mes):
#|     """La IA propone actividades pedagógicas del mes (no inventa feriados ni fechas oficiales)."""
#|     ultimo = calendar.monthrange(año, mes)[1]
#|     datos, _ = pedir_json(f"""{preambulo()}
#| Propón entre 5 y 8 actividades pedagógicas para el mes de {MESES[mes]} de {año} de un docente de {asig['area']} ({asig['grado']}, {asig['nivel']}):
#| evaluaciones, retroalimentación, proyectos, ferias, reuniones con familias, etc.
#| NO inventes feriados, vacaciones ni fechas oficiales del Ministerio. Usa solo días de lunes a viernes del mes (del 1 al {ultimo}).
#| Formato: {{"eventos":[{{"fecha":"{año}-{mes:02d}-10","tipo":"actividad","titulo":"...","detalle":"..."}}]}}
#| Tipos permitidos: actividad, examen, reunion.""")
#|     res = []
#|     for x in (datos.get("eventos") if isinstance(datos, dict) else datos) or []:
#|         try:
#|             f = dt.datetime.strptime(s(x.get("fecha")), "%Y-%m-%d").date()
#|         except (ValueError, AttributeError):
#|             continue
#|         if f.year == año and f.month == mes and s(x.get("titulo")):
#|             res.append({"fecha": f, "tipo": x.get("tipo") if x.get("tipo") in TIPOS else "actividad",
#|                         "titulo": s(x.get("titulo")), "detalle": s(x.get("detalle"))})
#|     return res
#|
#|
#| def a_ics(eventos):
#|     """Archivo .ics para importar a Google Calendar u Outlook."""
#|     esc = lambda t: s(t).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
#|     lineas = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//EduPeru IA//ES"]
#|     for e in eventos:
#|         f = e["fecha"]
#|         lineas += ["BEGIN:VEVENT", f"UID:eduperu-{e['id']}@eduperu", f"DTSTART;VALUE=DATE:{f:%Y%m%d}",
#|                    f"SUMMARY:{esc(e['titulo'])}", f"DESCRIPTION:{esc((e.get('detalle') or '').replace(AUTO, '').strip())}",
#|                    "END:VEVENT"]
#|     lineas.append("END:VCALENDAR")
#|     return ("\r\n".join(lineas) + "\r\n").encode("utf-8")
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
#| """Piezas de interfaz compartidas: navegación, selector de curso, avisos, costos, vista previa y editores."""
#| import streamlit as st
#| import streamlit.components.v1 as components
#|
#| from curriculo import bloqueo_curricular
#| from exportar import bloques_de
#| from repo import (cambiar_color, costo_de, get_asignacion, get_doc_by_id, get_usuario, listar_asignaciones,
#|                   resumen_asignacion)
#| from render import COLORES, COLOR_DEFECTO, ICONO_COLOR, a_docx, a_html
#| from util import a_lista, a_texto, s
#|
#| PAG_PANEL = "🏠 Inicio"
#| PAG_CURSOS = "📚 Mis cursos"
#| PAG_ANUAL = "📅 Sílabo anual"
#| PAG_TEMAS = "🎯 Temas y clases"
#| PAG_CALENDARIO = "🗓️ Calendario"
#| PAG_CURRICULO = "📖 Currículo oficial"
#| PAG_BIBLIO = "🗂️ Mi biblioteca"
#| PAG_ADMIN = "⚙️ Administración"
#| PAG_UNIDADES = PAG_SESIONES = PAG_TEMAS   # nombres antiguos: ahora todo vive en «Temas y clases»
#|
#| MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
#|
#|
#| # ------------------------------------------------------------------
#| # Navegación y mensajes
#| # ------------------------------------------------------------------
#| def caja(clave, borde=False):
#|     """Contenedor con nombre propio (para darle estilo con CSS). Si tu Streamlit es antiguo, usa uno normal."""
#|     try:
#|         return st.container(border=borde, key=clave)
#|     except TypeError:
#|         return st.container(border=borde)
#|
#|
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
#|     """Activa el curso y te lleva al siguiente paso pendiente (sílabo anual → temas y clases)."""
#|     r = resumen_asignacion(aid)
#|     abrir_area(aid, PAG_ANUAL if not r.get("anual") else PAG_TEMAS)
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
#| def _etiqueta_curso(a):
#|     return f"{a['area']} · {a['grado']} · Sección {a['seccion'] or '—'}"
#|
#|
#| def area_activa():
#|     """Curso activo del usuario (sale de la lista de sus cursos: no hace otra consulta)."""
#|     aid = st.session_state.get("area_id")
#|     if not aid:
#|         return None
#|     return next((a for a in listar_asignaciones(st.session_state.user_id) if a["id"] == aid), None)
#|
#|
#| def selector_curso(titulo="📌 ¿Para qué curso?"):
#|     """Selector de curso al comienzo de la pantalla. Devuelve el curso elegido (o None si no hay cursos)."""
#|     asigs = listar_asignaciones(st.session_state.user_id)
#|     if not asigs:
#|         return None
#|     ids = [a["id"] for a in asigs]
#|     actual = st.session_state.get("area_id")
#|     with st.container(border=True):
#|         elegido = st.selectbox(titulo, ids, index=ids.index(actual) if actual in ids else 0,
#|                                key=f"selcurso_{st.session_state.get('nav', '')}",
#|                                format_func=lambda i: _etiqueta_curso(next(a for a in asigs if a["id"] == i)))
#|     st.session_state["area_id"] = elegido
#|     return next(a for a in asigs if a["id"] == elegido)
#|
#|
#| def exigir_area():
#|     """Muestra el selector de curso arriba; si no hay cursos, invita a crear uno."""
#|     asig = selector_curso()
#|     if not asig:
#|         st.warning("👆 Primero crea un **curso** en *Inicio*. Ahí indicas tu grado, área y sección.")
#|         st.button("Ir a Inicio", on_click=ir_a, args=(PAG_PANEL,))
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
#| def seccion(opciones, clave):
#|     """Selector de secciones (reemplaza a las pestañas): solo se dibuja lo que eliges, así la página va más rápido."""
#|     return st.radio("Sección", opciones, horizontal=True, key=clave, label_visibility="collapsed")
#|
#|
#| def descargar(etiqueta, data, nombre, mime, key, **kw):
#|     """Botón de descarga que NO vuelve a calcular la página (más rápido) cuando Streamlit lo permite."""
#|     try:
#|         return st.download_button(etiqueta, data=data, file_name=nombre, mime=mime, key=key, on_click="ignore", **kw)
#|     except TypeError:
#|         return st.download_button(etiqueta, data=data, file_name=nombre, mime=mime, key=key, **kw)
#|
#|
#| # ------------------------------------------------------------------
#| # Costo en créditos con confirmación
#| # ------------------------------------------------------------------
#| def confirmar(accion, etiqueta, clave, veces=1, asig=None):
#|     """Botón que pide confirmar el costo en créditos. Devuelve True cuando el usuario confirma.
#|     Si se pasa 'asig' y el administrador exige currículo verificado, bloquea los cursos sin verificar."""
#|     if asig is not None:
#|         motivo = bloqueo_curricular(asig)
#|         if motivo:
#|             st.error("🔒 " + motivo)
#|             st.button("Ver el currículo oficial", key=f"cv_{clave}", on_click=ir_a, args=(PAG_CURRICULO,))
#|             return False
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
#| # Vista previa, color y descarga (la descarga va PRIMERO)
#| # ------------------------------------------------------------------
#| def vista_previa_y_descarga(doc_id, clave, abierta=True):
#|     doc = get_doc_by_id(doc_id)
#|     if not doc:
#|         return
#|     color_doc = (doc.get("color") or COLOR_DEFECTO).lstrip("#")
#|     nombres = list(COLORES)
#|     actual = next((n for n, h in COLORES.items() if h == color_doc), "Azul")
#|     c_desc, c_color = st.columns([3, 2])
#|     ckey = f"color_{clave}_{doc_id}"
#|     elegido = c_color.selectbox("🎨 Color del documento", nombres, index=nombres.index(actual), key=ckey,
#|                                 format_func=lambda n: f"{ICONO_COLOR[n]} {n}")
#|     color = COLORES[elegido]
#|     if color != color_doc:
#|         cambiar_color(doc_id, color)
#|         doc["color"] = color
#|     bloques, horizontal, archivo = bloques_de(doc)
#|     with c_desc:
#|         st.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
#|         descargar("⬇️ Descargar en Word", a_docx(bloques, color, doc.get("normativa_usada"), horizontal), archivo,
#|                   MIME_DOCX, f"dl_{clave}_{doc_id}", type="primary", use_container_width=True)
#|     with st.expander("👁️ Vista previa del documento (se actualiza al guardar)", expanded=abierta):
#|         components.html(a_html(bloques, color, doc.get("normativa_usada")), height=560, scrolling=True)
#|
#|
#| # ------------------------------------------------------------------
#| # Editores por elemento (reemplazan a las tablas anchas: se ven ordenados también en el celular)
#| # campos = [{"k": "enunciado", "label": "Enunciado", "tipo": "linea|area|lineas|select|lectura", "alto": 90, "opciones": [...]}]
#| # ------------------------------------------------------------------
#| def editor_items(clave, items, campos, titulo_fn, abiertos=1):
#|     for i, it in enumerate(items):
#|         with st.expander(titulo_fn(i, it), expanded=(i < abiertos)):
#|             for c in campos:
#|                 k, tipo = f"{clave}_{i}_{c['k']}", c.get("tipo", "linea")
#|                 valor = it.get(c["k"])
#|                 if tipo == "area":
#|                     campo_texto(c["label"], k, s(valor), c.get("alto", 90))
#|                 elif tipo == "lineas":
#|                     campo_texto(c["label"], k, a_texto(valor), c.get("alto", 90), c.get("ayuda"))
#|                 elif tipo == "select":
#|                     ops = list(c["opciones"])
#|                     if s(valor) and s(valor) not in ops:
#|                         ops.insert(0, s(valor))
#|                     if k not in st.session_state or st.session_state[k] not in ops:
#|                         st.session_state[k] = s(valor) if s(valor) in ops else ops[0]
#|                     st.selectbox(c["label"], ops, key=k)
#|                 elif tipo == "lectura":
#|                     if s(valor):
#|                         st.caption(f"{c['label']}: {s(valor)}")
#|                 else:
#|                     campo_linea(c["label"], k, s(valor))
#|
#|
#| def recoger_items(clave, items, campos):
#|     res = []
#|     for i, it in enumerate(items):
#|         d = dict(it)
#|         for c in campos:
#|             tipo = c.get("tipo", "linea")
#|             if tipo == "lectura":
#|                 continue
#|             v = st.session_state.get(f"{clave}_{i}_{c['k']}")
#|             if v is not None:
#|                 d[c["k"]] = a_lista(v) if tipo == "lineas" else s(v)
#|         d["numero"] = i + 1
#|         res.append(d)
#|     return res
#|
#|
#| def barra_edicion(clave, items, campos, vacio, guardar, ver_key):
#|     """Botones Guardar / Agregar / Quitar el último para un editor_items. guardar(lista) persiste los cambios."""
#|     c1, c2, c3 = st.columns(3)
#|     if c1.button("💾 Guardar cambios", type="primary", key=f"{clave}_save", use_container_width=True):
#|         guardar(recoger_items(clave, items, campos))
#|         st.success("Guardado ✅")
#|     if c2.button("➕ Agregar", key=f"{clave}_add", use_container_width=True):
#|         lista = recoger_items(clave, items, campos)
#|         lista.append(vacio(len(lista) + 1))
#|         guardar(lista)
#|         siguiente_version(ver_key)
#|         st.rerun()
#|     if c3.button("➖ Quitar el último", key=f"{clave}_rm", use_container_width=True) and len(items) > 1:
#|         guardar(recoger_items(clave, items, campos)[:-1])
#|         siguiente_version(ver_key)
#|         st.rerun()
#@@ END
#@@ MODULE examen_unidad
#| """Examen de unidad o bimestral: se arma con los desempeños (de la base oficial) y los temas de las unidades."""
#| import streamlit as st
#|
#| from ia import pedir_json, preambulo
#| from normativa import normativa_vigente
#| from repo import cobrar, contenido, get_doc, guardar_doc, listar_docs
#| from ui import (barra_edicion, campo_linea, campo_texto, confirmar, editor_items, siguiente_version,
#|                 vista_previa_y_descarga)
#| from util import a_lista, entero, norm, s
#|
#|
#| def _contexto(unidades):
#|     """Texto para la IA + lista numerada de desempeños verificados {n, competencia, texto}."""
#|     des, lineas = [], []
#|     for ud in unidades:
#|         d = contenido(ud)
#|         temas = "; ".join(f.get("titulo", "") for f in d.get("secuencia", []))
#|         lineas.append(f"UNIDAD {d.get('numero')}: {d.get('titulo')}\n  Situación: {d.get('situacion', '')}\n  Temas de las sesiones: {temas}")
#|         for p in d.get("propositos", []):
#|             lineas.append(f"  Competencia: {p['competencia']} | Campo temático: {p.get('campo_tematico', '')}")
#|             for texto in p.get("desempenos", []):
#|                 des.append({"n": len(des) + 1, "competencia": p["competencia"], "texto": texto})
#|                 lineas.append(f"    D{len(des)}: {texto}")
#|     return "\n".join(lineas), des
#|
#|
#| def generar(asig, unidades, n_preg, tipos, total):
#|     ctx, des = _contexto(unidades)
#|     if not des:
#|         raise RuntimeError("Las unidades elegidas no tienen desempeños. Completa los propósitos de aprendizaje primero.")
#|     nums = ", ".join(str(ud["numero"]) for ud in unidades)
#|     prompt = f"""{preambulo()}
#| Elabora un EXAMEN {'de la unidad' if len(unidades) == 1 else 'bimestral'} para estudiantes de {asig['grado']} ({asig['nivel']}), área {asig['area']}.
#| Unidades incluidas: {nums}. Número de preguntas: {n_preg}. Tipo: {tipos}. Puntaje total: {total} (los puntajes deben sumar exactamente {total}).
#|
#| Contenido de las unidades (los desempeños D1, D2... son oficiales; NO los reescribas):
#| {ctx}
#|
#| Reglas:
#| - Cada pregunta evalúa UN desempeño: indica su número en "desempeno" (ej. 3) y el nombre exacto de su competencia en "competencia".
#| - Reparte las preguntas entre los desempeños y los temas de las unidades.
#| - "opcion_multiple": 4 opciones "a) ...", "b) ...", y "respuesta" con la letra. "desarrollo": "opciones" vacía y "respuesta" con la respuesta esperada.
#| - Lenguaje adecuado a la edad y contexto cercano a la región {asig['region']}.
#| Formato: {{"titulo":"...","instrucciones":"...","preguntas":[{{"numero":1,"tipo":"opcion_multiple","enunciado":"...","opciones":["a) ...","b) ...","c) ...","d) ..."],"respuesta":"b","puntaje":2,"competencia":"...","desempeno":3}}]}}"""
#|     ia, _ = pedir_json(prompt)
#|     if not isinstance(ia, dict):
#|         raise RuntimeError("La IA devolvió un formato inesperado. Intenta de nuevo.")
#|     por_n = {x["n"]: x for x in des}
#|     preguntas = []
#|     for i, p in enumerate(ia.get("preguntas") or [], 1):
#|         if not isinstance(p, dict):
#|             continue
#|         x = por_n.get(entero(p.get("desempeno"), 0))
#|         preguntas.append({"numero": i, "tipo": s(p.get("tipo")) or "desarrollo", "enunciado": s(p.get("enunciado")),
#|                           "opciones": a_lista(p.get("opciones")), "respuesta": s(p.get("respuesta")),
#|                           "puntaje": s(p.get("puntaje")) or "1",
#|                           "competencia": x["competencia"] if x else s(p.get("competencia")),
#|                           "desempeno_texto": x["texto"] if x else ""})
#|     if not preguntas:
#|         raise RuntimeError("La IA no devolvió preguntas. Intenta de nuevo.")
#|     titulo = s(ia.get("titulo")) or (f"Examen de la Unidad {nums}" if len(unidades) == 1 else f"Examen bimestral (Unidades {nums})")
#|     return {"titulo": titulo, "instrucciones": s(ia.get("instrucciones")), "unidades": [ud["numero"] for ud in unidades],
#|             "preguntas": preguntas}
#|
#|
#| CAMPOS = [{"k": "tipo", "label": "Tipo de pregunta", "tipo": "select",
#|            "opciones": ["opcion_multiple", "desarrollo", "verdadero_falso"]},
#|           {"k": "enunciado", "label": "Pregunta", "tipo": "area", "alto": 80},
#|           {"k": "opciones", "label": "Alternativas (una por línea, ej.: a) …)", "tipo": "lineas", "alto": 100},
#|           {"k": "respuesta", "label": "Respuesta correcta", "tipo": "linea"},
#|           {"k": "puntaje", "label": "Puntaje", "tipo": "linea"},
#|           {"k": "competencia", "label": "Competencia", "tipo": "lectura"},
#|           {"k": "desempeno_texto", "label": "Desempeño que evalúa", "tipo": "lectura"}]
#|
#|
#| def render(asig, udoc):
#|     uid, aid = st.session_state.user_id, asig["id"]
#|     st.caption("Se arma con los temas y los desempeños oficiales de las unidades que elijas. Incluye una matriz que "
#|                "muestra qué desempeño evalúa cada pregunta.")
#|     todas = listar_docs(aid, "unidad")
#|     numeros = [u["numero"] for u in todas]
#|     doc = get_doc(aid, "examen_unidad", numero=udoc["numero"])
#|     d = contenido(doc) if doc else {}
#|     ver_key = f"ver_exu_{udoc['id']}"
#|     ver = st.session_state.get(ver_key, 0)
#|
#|     with st.expander("⚙️ Generar con IA", expanded=not doc):
#|         sel = st.multiselect("Unidades que incluye (para un examen bimestral elige varias)", numeros,
#|                              default=[x for x in d.get("unidades", [udoc["numero"]]) if x in numeros] or [udoc["numero"]],
#|                              key=f"exu_sel_{udoc['id']}_{ver}", format_func=lambda n: f"Unidad {n}")
#|         c1, c2, c3 = st.columns(3)
#|         n_preg = c1.number_input("Número de preguntas", 5, 40, 12, key=f"exu_n_{udoc['id']}")
#|         tipos = c2.selectbox("Tipo de preguntas", ["Mixto", "Solo opción múltiple", "Solo desarrollo"], key=f"exu_t_{udoc['id']}")
#|         total = c3.number_input("Puntaje total", 5, 100, 20, key=f"exu_p_{udoc['id']}")
#|         etiqueta = "✨ Generar examen" if not doc else "🔄 Volver a generar el examen"
#|         if confirmar("examen_unidad", etiqueta, f"exu_{udoc['id']}", asig=asig):
#|             try:
#|                 elegidas = [u for u in todas if u["numero"] in sel] or [udoc]
#|                 with st.spinner("Armando el examen con los desempeños de las unidades..."):
#|                     nuevo = generar(asig, elegidas, int(n_preg), tipos, int(total))
#|                 guardar_doc(uid, aid, "examen_unidad", udoc["numero"], nuevo["titulo"], nuevo, padre_id=udoc["id"],
#|                             normativa=normativa_vigente()[1])
#|                 cobrar(uid, "examen_unidad")
#|                 siguiente_version(ver_key)
#|                 st.rerun()
#|             except Exception as e:
#|                 st.error(f"No se pudo generar: {e}")
#|     if not doc:
#|         return
#|
#|     vista_previa_y_descarga(doc["id"], f"exu_{udoc['id']}")
#|     with st.expander("✏️ Editar el examen"):
#|         clave = f"exu_{udoc['id']}_{ver}"
#|         campo_linea("Título del examen", f"{clave}_t", d.get("titulo", ""))
#|         campo_texto("Indicaciones", f"{clave}_i", d.get("instrucciones", ""), 80)
#|         items = d.get("preguntas", [])
#|         editor_items(clave, items, CAMPOS, lambda i, x: f"Pregunta {i + 1}: {s(x.get('enunciado'))[:60]}")
#|         barra_edicion(clave, items, CAMPOS,
#|                       lambda n: {"numero": n, "tipo": "desarrollo", "enunciado": "", "opciones": [], "respuesta": "",
#|                                  "puntaje": "1", "competencia": "", "desempeno_texto": ""},
#|                       lambda lista: guardar_doc(uid, aid, "examen_unidad", udoc["numero"],
#|                                                 st.session_state.get(f"{clave}_t", "") or doc["titulo"],
#|                                                 {**d, "titulo": st.session_state.get(f"{clave}_t", ""),
#|                                                  "instrucciones": st.session_state.get(f"{clave}_i", ""),
#|                                                  "preguntas": lista}, padre_id=udoc["id"]), ver_key)
#@@ END
#@@ MODULE v_curriculo
#| """Currículo oficial: los lineamientos del MINEDU por curso (solo lectura; la IA no toca este contenido)."""
#| import streamlit as st
#|
#| from curriculo import (GRADOS, NIVELES, areas_de, ciclo_de, competencias_de, desempenos_de, detalle_competencia,
#|                        estandar_de)
#| from db import fetch
#| from ui import area_activa
#|
#|
#| def render():
#|     st.title("📖 Currículo oficial")
#|     st.info("💡 Aquí ves los lineamientos oficiales del MINEDU por curso. Son los textos que usa el sistema: "
#|             "la IA **no** los escribe ni los modifica; solo prepara actividades y materiales a partir de ellos.")
#|
#|     act = area_activa()
#|     c1, c2, c3 = st.columns(3)
#|     niveles = NIVELES
#|     nivel = c1.selectbox("Nivel", niveles, index=niveles.index(act["nivel"]) if act else 1, key="cur_ver_nivel")
#|     areas = areas_de(nivel)
#|     if not areas:
#|         st.warning("Este nivel todavía no tiene áreas cargadas.")
#|         return
#|     area = c2.selectbox("Área", areas, index=areas.index(act["area"]) if act and act["nivel"] == nivel
#|                         and act["area"] in areas else 0, key="cur_ver_area")
#|     grados = GRADOS[nivel]
#|     grado = c3.selectbox("Grado", grados, index=grados.index(act["grado"]) if act and act["nivel"] == nivel
#|                          and act["grado"] in grados else 0, key="cur_ver_grado")
#|     ciclo = ciclo_de(nivel, grado)
#|
#|     comps = competencias_de(nivel, area)
#|     if not comps:
#|         st.warning("Esta área todavía no tiene competencias cargadas.")
#|         return
#|     verificadas = sum(1 for c in comps if c["verificado"])
#|     con_des = sum(1 for c in comps if desempenos_de(c["id"], grado))
#|     if verificadas == len(comps) and con_des == len(comps):
#|         st.success(f"✅ Currículo verificado para {area} · {grado} (ciclo {ciclo}).")
#|     else:
#|         st.warning(f"⚠️ Pendiente de verificación: {verificadas} de {len(comps)} competencias verificadas; "
#|                    f"{con_des} de {len(comps)} con desempeños cargados para {grado}.")
#|
#|     for c in comps:
#|         det = detalle_competencia(c["id"])
#|         with st.expander(("✅ " if c["verificado"] else "⚠️ ") + c["nombre"]):
#|             st.markdown("**Capacidades**")
#|             st.markdown("\n".join(f"- {x}" for x in c["capacidades"]) or "_Sin capacidades cargadas._")
#|             est = estandar_de(c["id"], ciclo)
#|             st.markdown(f"**Estándar de aprendizaje (ciclo {ciclo})**")
#|             st.write(est or "_Aún no cargado._")
#|             des = desempenos_de(c["id"], grado)
#|             st.markdown(f"**Desempeños de {grado}**")
#|             if des:
#|                 st.markdown("\n".join(f"{i}. {d['texto']}" for i, d in enumerate(des, 1)))
#|             else:
#|                 st.caption("Aún no cargados por el administrador.")
#|             if det.get("fuente"):
#|                 fecha = f" · verificado el {det['verificado_en']:%d/%m/%Y}" if det.get("verificado_en") else ""
#|                 st.caption(f"Fuente: {det['fuente']}{fecha}")
#|
#|     with st.expander("📜 Normativa vigente aprobada (MINEDU)"):
#|         st.caption("Base: RM N.° 501-2025-MINEDU. Estas son las actualizaciones que el administrador revisó y aprobó.")
#|         filas = fetch("SELECT f.nombre, f.url, v.resumen_cambios, v.aprobado_en FROM normativa_versiones v "
#|                       "JOIN normativa_fuentes f ON f.id = v.fuente_id WHERE v.estado='aprobada' "
#|                       "ORDER BY v.aprobado_en DESC LIMIT 10")
#|         if not filas:
#|             st.write("Todavía no hay actualizaciones aprobadas; se aplica la RM N.° 501-2025-MINEDU.")
#|         for f in filas:
#|             st.markdown(f"**{f['nombre']}** · aprobada el {f['aprobado_en']:%d/%m/%Y}")
#|             st.caption(f["url"])
#|             st.write(f["resumen_cambios"])
#@@ END
#@@ MODULE v_programas
#| """Administración: buscar, leer y cargar los Programas Curriculares oficiales (PDF) con verificación."""
#| import pandas as pd
#| import streamlit as st
#|
#| from curriculo import NIVELES, areas_de
#| from db import execute, fetch
#| from programas import (aprobar, buscar_programas, descargar_y_leer, extraer, leer_subido, pendientes, registrar_url,
#|                        rechazar)
#|
#| ESTADOS = {"nuevo": "🆕 Nuevo", "leido": "📖 Leído", "actualizado": "🔄 Actualizado en gob.pe", "descartado": "🚫 Descartado"}
#|
#|
#| def render():
#|     st.caption("El sistema revisa las páginas oficiales del MINEDU en gob.pe y trae los PDF de los Programas Curriculares. "
#|                "La IA **no navega por internet**: solo ayuda a clasificar y a ordenar el texto, y todo lo que extrae "
#|                "se comprueba contra el PDF. Nada pasa a los docentes sin tu aprobación.")
#|
#|     # ---------------- 1. Buscar
#|     st.markdown("### ① Buscar en el MINEDU")
#|     if st.button("🔎 Buscar Programas Curriculares en gob.pe", type="primary", key="prog_buscar"):
#|         with st.spinner("Revisando las páginas oficiales..."):
#|             try:
#|                 lista, avisos = buscar_programas()
#|                 for a in avisos:
#|                     st.warning(a)
#|                 st.success(f"Listo. Hay {len(lista)} documento(s) registrados.")
#|             except Exception as e:
#|                 st.error(f"No se pudo buscar: {e}")
#|     with st.expander("Otras formas de traer un PDF (pegar enlace o subir archivo)"):
#|         c1, c2 = st.columns(2)
#|         url = c1.text_input("Enlace directo al PDF", key="prog_url", placeholder="https://cdn.www.gob.pe/uploads/...pdf")
#|         nivel_url = c1.selectbox("Nivel del documento", [""] + NIVELES, key="prog_url_nivel")
#|         if c1.button("➕ Agregar enlace", key="prog_url_btn") and url.startswith("http"):
#|             registrar_url(url.strip(), nivel=nivel_url)
#|             st.rerun()
#|         archivo = c2.file_uploader("…o sube el PDF", type=["pdf"], key="prog_subir")
#|         nivel_sub = c2.selectbox("Nivel del documento", [""] + NIVELES, key="prog_sub_nivel")
#|         if archivo is not None and c2.button("📥 Leer este PDF", key="prog_sub_btn"):
#|             try:
#|                 with st.spinner("Leyendo el PDF (puede tardar)..."):
#|                     _, n = leer_subido(archivo.name, archivo.getvalue(), nivel_sub)
#|                 st.success(f"PDF leído: {n} páginas.")
#|                 st.rerun()
#|             except Exception as e:
#|                 st.error(f"No se pudo leer: {e}")
#|
#|     docs = fetch("SELECT * FROM curriculo_pdf WHERE estado<>'descartado' ORDER BY id DESC")
#|     if not docs:
#|         st.info("Aún no hay documentos. Pulsa «Buscar» o agrega un enlace.")
#|         return
#|     st.dataframe(pd.DataFrame([{"id": d["id"], "estado": ESTADOS.get(d["estado"], d["estado"]), "nivel": d["nivel"],
#|                                 "título": d["titulo"], "páginas": d["paginas"], "leído": d["leido_en"]} for d in docs]),
#|                  hide_index=True)
#|
#|     # ---------------- 2. Leer
#|     st.markdown("### ② Descargar y leer el PDF")
#|     ids = [d["id"] for d in docs]
#|     pid = st.selectbox("Documento", ids, key="prog_sel", format_func=lambda i: next(
#|         f"{d['id']} · {d['nivel'] or '¿nivel?'} · {(d['titulo'] or d['url'])[:70]}" for d in docs if d["id"] == i))
#|     doc = next(d for d in docs if d["id"] == pid)
#|     if doc["estado"] == "actualizado":
#|         st.warning("Este PDF cambió en gob.pe desde la última lectura. Vuelve a leerlo y a extraer.")
#|     if not doc["url"].startswith("subido:"):
#|         if st.button("⬇️ Descargar y leer", key=f"prog_leer_{pid}"):
#|             try:
#|                 with st.spinner("Descargando y leyendo el PDF..."):
#|                     n = descargar_y_leer(pid)
#|                 st.success(f"Leído: {n} páginas.")
#|                 st.rerun()
#|             except Exception as e:
#|                 st.error(f"No se pudo leer: {e}")
#|     if doc["estado"] not in ("leido", "actualizado") or not doc["paginas"]:
#|         st.caption("Cuando el PDF esté leído podrás extraer los desempeños.")
#|         return
#|
#|     # ---------------- 3. Extraer
#|     st.markdown("### ③ Extraer desempeños y estándares (IA + verificación contra el PDF)")
#|     nivel = st.selectbox("Nivel a extraer", NIVELES, key="prog_nivel",
#|                          index=NIVELES.index(doc["nivel"]) if doc["nivel"] in NIVELES else 1)
#|     areas = areas_de(nivel)
#|     sel = st.multiselect("Áreas (vacío = todas)", areas, key=f"prog_areas_{nivel}")
#|     if st.button("🤖 Extraer y verificar", type="primary", key=f"prog_ext_{pid}"):
#|         barra = st.progress(0.0)
#|         try:
#|             res = extraer(pid, nivel, sel or None, lambda f, t: barra.progress(min(f, 1.0), text=t))
#|             st.success(f"Verificados contra el PDF: {res['verificados']} · descartados por no aparecer en el PDF: "
#|                        f"{res['descartados']}")
#|             if res["sin_paginas"]:
#|                 with st.expander(f"No se encontraron páginas para {len(res['sin_paginas'])} competencia(s)"):
#|                     st.write("\n".join(f"- {x}" for x in res["sin_paginas"]))
#|         except Exception as e:
#|             st.error(f"No se pudo extraer: {e}")
#|
#|     # ---------------- 4. Revisar y aprobar
#|     st.markdown("### ④ Revisar y aprobar")
#|     pend = pendientes(pid)
#|     if not pend:
#|         st.success("No hay textos pendientes de revisión en este documento.")
#|         return
#|     st.caption(f"{len(pend)} texto(s) pendientes. Marca «aprobar» solo los que coinciden con el documento oficial. "
#|                "Puedes corregir el texto antes de aprobar.")
#|     df = pd.DataFrame([{"aprobar": True, "id": p["id"], "área": p["area"], "competencia": p["competencia"][:50],
#|                         "tipo": p["tipo"], "grado/ciclo": p["grado"], "página": p["pagina"], "texto": p["texto"]}
#|                        for p in pend])
#|     ed = st.data_editor(df, key=f"prog_rev_{pid}_{len(pend)}", hide_index=True, disabled=["id", "área", "competencia",
#|                         "tipo", "grado/ciclo", "página"])
#|     marcar = st.checkbox("Marcar como «verificadas» las competencias aprobadas", value=True, key=f"prog_ver_{pid}")
#|     c1, c2 = st.columns(2)
#|     if c1.button("✅ Aprobar los marcados", type="primary", key=f"prog_apr_{pid}"):
#|         for _, r in ed.iterrows():
#|             if r["aprobar"]:
#|                 execute("UPDATE curriculo_importado SET texto=%s WHERE id=%s", (str(r["texto"]).strip(), int(r["id"])))
#|         n = aprobar([int(r["id"]) for _, r in ed.iterrows() if r["aprobar"]], marcar,
#|                     doc["titulo"] or doc["url"])
#|         st.success(f"Se aprobaron {n} texto(s) y ya están disponibles para los docentes.")
#|         st.rerun()
#|     if c2.button("🗑️ Rechazar los desmarcados", key=f"prog_rec_{pid}"):
#|         rechazar([int(r["id"]) for _, r in ed.iterrows() if not r["aprobar"]])
#|         st.rerun()
#@@ END
#@@ MODULE v_calendario
#| """Calendario: vista mensual, eventos, programación automática y sugerencias con IA."""
#| import calendar
#| import datetime as dt
#| import html
#|
#| import streamlit as st
#|
#| from calendario import (AUTO, DIAS, MESES, TIPOS, a_ics, agregar, borrar, eventos_mes, parsear_fechas,
#|                         programar_clases, sugerir_con_ia)
#| from repo import cobrar
#| from ui import confirmar, descargar, flash, selector_curso
#|
#|
#| def _mover(delta):
#|     y, m = st.session_state["cal_y"], st.session_state["cal_m"] + delta
#|     if m < 1:
#|         y, m = y - 1, 12
#|     elif m > 12:
#|         y, m = y + 1, 1
#|     st.session_state["cal_y"], st.session_state["cal_m"] = y, m
#|
#|
#| def _hoy_cb():
#|     hoy = dt.date.today()
#|     st.session_state["cal_y"], st.session_state["cal_m"] = hoy.year, hoy.month
#|
#|
#| def render():
#|     uid = st.session_state.user_id
#|     hoy = dt.date.today()
#|     st.session_state.setdefault("cal_y", hoy.year)
#|     st.session_state.setdefault("cal_m", hoy.month)
#|     y, m = st.session_state["cal_y"], st.session_state["cal_m"]
#|
#|     st.title("🗓️ Calendario")
#|     st.info("💡 Programa tus clases, exámenes y actividades. Puedes repartir automáticamente las clases de tu sílabo "
#|             "y pedir sugerencias a la IA.")
#|
#|     asig = selector_curso("📌 ¿Para qué curso programas?")
#|     c1, c2, c3, c4 = st.columns([1, 3, 1, 2])
#|     c1.button("◀ Anterior", on_click=_mover, args=(-1,), key="cal_prev", use_container_width=True)
#|     c2.markdown(f"<h3 style='text-align:center;margin:0'>{MESES[m]} {y}</h3>", unsafe_allow_html=True)
#|     c3.button("Siguiente ▶", on_click=_mover, args=(1,), key="cal_next", use_container_width=True)
#|     c4.button("Ir a hoy", on_click=_hoy_cb, key="cal_hoy", use_container_width=True)
#|
#|     solo_curso = False
#|     if asig:
#|         solo_curso = st.radio("Mostrar", ["Todos mis cursos", f"Solo {asig['area']} · {asig['grado']}"], horizontal=True,
#|                               key="cal_filtro", label_visibility="collapsed").startswith("Solo")
#|     eventos = eventos_mes(uid, y, m, asig["id"] if solo_curso and asig else None)
#|     por_dia = {}
#|     for e in eventos:
#|         por_dia.setdefault(e["fecha"].day, []).append(e)
#|
#|     cab = st.columns(7)
#|     for i, nombre in enumerate(DIAS):
#|         cab[i].markdown(f"<div style='text-align:center;font-weight:600;color:#6D28D9'>{nombre[:3]}</div>",
#|                         unsafe_allow_html=True)
#|     for semana in calendar.Calendar(firstweekday=0).monthdayscalendar(y, m):
#|         cols = st.columns(7)
#|         for i, dia in enumerate(semana):
#|             if dia == 0:
#|                 continue
#|             es_hoy = dt.date(y, m, dia) == hoy
#|             borde = "#7c3aed" if es_hoy else "#eee"
#|             fondo = "#faf5ff" if es_hoy else "#fff"
#|             items = "".join(
#|                 f"<div style='font-size:11px;line-height:1.25;margin-top:2px'>{TIPOS.get(e['tipo'], TIPOS['otro'])[0]} "
#|                 f"{html.escape((e['titulo'] or '')[:28])}</div>" for e in por_dia.get(dia, [])[:3])
#|             mas = len(por_dia.get(dia, [])) - 3
#|             if mas > 0:
#|                 items += f"<div style='font-size:11px;color:#888'>+{mas} más</div>"
#|             cols[i].markdown(f"<div style='min-height:82px;border:1px solid {borde};background:{fondo};"
#|                              f"border-radius:10px;padding:4px 6px'><b>{dia}</b>{items}</div>", unsafe_allow_html=True)
#|
#|     st.markdown("#### 📋 Eventos de este mes")
#|     if not eventos:
#|         st.caption("No hay eventos este mes.")
#|     for e in eventos:
#|         a, b = st.columns([8, 1])
#|         emoji, nombre = TIPOS.get(e["tipo"], TIPOS["otro"])
#|         a.markdown(f"**{e['fecha']:%d/%m}** · {emoji} {e['titulo']}")
#|         if e.get("detalle") and not e["detalle"].startswith(AUTO):
#|             a.caption(e["detalle"])
#|         if b.button("✕", key=f"ev_del_{e['id']}", help="Eliminar este evento"):
#|             borrar(e["id"], uid)
#|             st.rerun()
#|     if eventos:
#|         descargar("⬇️ Descargar calendario (.ics)", a_ics(eventos), f"calendario_{y}_{m:02d}.ics", "text/calendar", "cal_ics")
#|
#|     with st.expander("➕ Agregar un evento"):
#|         with st.form("cal_nuevo", clear_on_submit=True):
#|             f1, f2 = st.columns(2)
#|             fecha = f1.date_input("Fecha", value=dt.date(y, m, 1) if (y, m) != (hoy.year, hoy.month) else hoy)
#|             tipo = f2.selectbox("Tipo", list(TIPOS), format_func=lambda k: f"{TIPOS[k][0]} {TIPOS[k][1]}")
#|             titulo = st.text_input("Título")
#|             detalle = st.text_area("Detalle (opcional)", height=70)
#|             vincular = st.checkbox("Asociarlo al curso activo", value=bool(asig), disabled=not asig)
#|             ok = st.form_submit_button("Agregar", type="primary")
#|         if ok:
#|             if not titulo.strip():
#|                 st.warning("Escribe un título.")
#|             else:
#|                 agregar(uid, asig["id"] if asig and vincular else None, fecha, tipo, titulo.strip(), detalle.strip())
#|                 flash("Evento agregado ✅")
#|                 st.rerun()
#|
#|     with st.expander("⚡ Programar mis clases automáticamente"):
#|         if not asig:
#|             st.info("Primero elige un curso en el menú lateral.")
#|         else:
#|             st.caption("Reparte las clases de tu sílabo en los días que elijas y pone un examen al final de cada unidad. "
#|                        "Lo programado antes automáticamente para este curso se reemplaza.")
#|             d1, d2 = st.columns(2)
#|             inicio = d1.date_input("Primer día de clases", value=hoy, key="cal_inicio")
#|             dias = d2.multiselect("Días de clase", DIAS, default=["Lunes", "Miércoles", "Viernes"], key="cal_dias")
#|             sin = st.text_area("Días sin clases (opcional): fechas dd/mm/aaaa separadas por comas", height=70, key="cal_sin",
#|                                help="Feriados, vacaciones, semana de gestión… según el calendario de tu institución.")
#|             con_ex = st.checkbox("Incluir un examen al final de cada unidad", value=True, key="cal_conex")
#|             if st.button("📆 Programar clases", type="primary", key="cal_programar"):
#|                 fechas, malas = parsear_fechas(sin)
#|                 if malas:
#|                     st.warning("No entendí estas fechas (úsalas como dd/mm/aaaa): " + ", ".join(malas))
#|                 try:
#|                     n = programar_clases(uid, asig, inicio, [DIAS.index(x) for x in dias], fechas, con_ex)
#|                     flash(f"Se programaron {n} eventos. Revisa los meses siguientes ✅")
#|                     st.session_state["cal_y"], st.session_state["cal_m"] = inicio.year, inicio.month
#|                     st.rerun()
#|                 except ValueError as e:
#|                     st.error(str(e))
#|
#|     with st.expander("🤖 Sugerencias de actividades con IA"):
#|         if not asig:
#|             st.info("Primero elige un curso en el menú lateral.")
#|         else:
#|             st.caption(f"La IA propone actividades pedagógicas para {MESES[m]} {y}. No conoce los feriados ni fechas oficiales: "
#|                        "verifica siempre con el calendario de tu institución (RM N.° 501-2025-MINEDU).")
#|             if confirmar("calendario_ia", f"✨ Sugerir actividades de {MESES[m]}", "cal_ia", asig=None):
#|                 try:
#|                     with st.spinner("Pensando actividades..."):
#|                         st.session_state["cal_sug"] = sugerir_con_ia(asig, y, m)
#|                     cobrar(uid, "calendario_ia")
#|                 except Exception as e:
#|                     st.error(f"No se pudo: {e}")
#|             sug = st.session_state.get("cal_sug") or []
#|             marcados = []
#|             for i, x in enumerate(sug):
#|                 if st.checkbox(f"{x['fecha']:%d/%m} · {TIPOS[x['tipo']][0]} {x['titulo']}", value=True, key=f"cal_s_{i}"):
#|                     marcados.append(x)
#|                 if x["detalle"]:
#|                     st.caption(x["detalle"])
#|             if sug and st.button("➕ Agregar los marcados", key="cal_sug_add"):
#|                 for x in marcados:
#|                     agregar(uid, asig["id"], x["fecha"], x["tipo"], x["titulo"], x["detalle"])
#|                 st.session_state["cal_sug"] = []
#|                 flash(f"Se agregaron {len(marcados)} actividades ✅")
#|                 st.rerun()
#@@ END
#@@ MODULE v_panel
#| """Inicio (bienvenida y herramientas) y Mis cursos (crear, abrir y eliminar cursos)."""
#| import html
#|
#| import streamlit as st
#|
#| from curriculo import GRADOS, NIVELES, REGIONES, areas_de, estado_area
#| from repo import (borrar_asignacion, borrar_todas_asignaciones, crear_asignacion, get_usuario, listar_asignaciones,
#|                   resumen_todas)
#| from ui import PAG_ANUAL, PAG_CURSOS, PAG_TEMAS, abrir_siguiente, caja, flash
#|
#| CLASE, UNIDAD = "📖 Una clase (un tema)", "📚 Toda la unidad"
#| # (icono, título, descripción, pestaña de la clase o None, ámbito)
#| HERRAMIENTAS = [
#|     ("🎒", "Mis cursos", "Todos tus cursos en un solo lugar: crea, abre o elimina.", "CURSOS", None, None),
#|     ("📚", "Unidad de aprendizaje", "Diseña una unidad completa con su secuencia.", PAG_TEMAS, UNIDAD, "📚 Unidad de aprendizaje"),
#|     ("📝", "Sesión de aprendizaje", "Elige un tema y crea su sesión.", PAG_TEMAS, CLASE, "📖 Sesión de aprendizaje"),
#|     ("🏆", "Fichas y desafíos", "Desglosa un tema en fichas de trabajo y retos.", PAG_TEMAS, CLASE, "📄 Ficha de trabajo"),
#|     ("📊", "Rúbricas", "Evalúa con criterios claros y niveles de logro.", PAG_TEMAS, CLASE, "📊 Rúbrica"),
#|     ("📋", "Exámenes", "Por clase, por unidad o bimestral.", PAG_TEMAS, CLASE, "📋 Examen"),
#| ]
#| ICONO_AREA = {"Matemática": "🔢", "Comunicación": "📖", "Ciencia y Tecnología": "🔬", "Personal Social": "🧑‍🤝‍🧑",
#|               "Ciencias Sociales": "🌎", "Desarrollo Personal, Ciudadanía y Cívica": "🤝", "Arte y Cultura": "🎨",
#|               "Educación Física": "⚽", "Inglés": "🔤", "Educación Religiosa": "🕊️", "Educación para el Trabajo": "🛠️",
#|               "Psicomotricidad": "🤸"}
#|
#|
#| # ---------------- callbacks (se ejecutan antes de redibujar: así pueden cambiar el curso activo) ----------------
#| def _crear_curso_cb(uid):
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
#|     ss["crear_abierto"] = False
#|     flash(f"¡Listo! Creaste {ss['na_area']} · {ss['na_grado']}. Ahora ábrelo y empieza por el sílabo anual.")
#|
#|
#| def _ir_crear():
#|     st.session_state["nav"] = PAG_CURSOS
#|     st.session_state["crear_abierto"] = True
#|
#|
#| def _alternar_crear():
#|     st.session_state["crear_abierto"] = not st.session_state.get("crear_abierto", False)
#|
#|
#| def _pedir_borrar(aid):
#|     st.session_state[f"_del_{aid}"] = True
#|
#|
#| def _cancelar_borrar(aid):
#|     st.session_state.pop(f"_del_{aid}", None)
#|
#|
#| def _borrar_curso_cb(aid):
#|     borrar_asignacion(aid)
#|     st.session_state.pop(f"_del_{aid}", None)
#|     if st.session_state.get("area_id") == aid:
#|         st.session_state["area_id"] = None
#|     flash("Curso eliminado.")
#|
#|
#| def _pedir_borrar_todos():
#|     st.session_state["_del_todos"] = True
#|
#|
#| def _cancelar_borrar_todos():
#|     st.session_state.pop("_del_todos", None)
#|
#|
#| def _borrar_todos_cb(uid):
#|     borrar_todas_asignaciones(uid)
#|     st.session_state.pop("_del_todos", None)
#|     st.session_state["area_id"] = None
#|     flash("Se eliminaron todos tus cursos.")
#|
#|
#| def _ir_herramienta(pagina, ambito, seccion):
#|     ss = st.session_state
#|     if pagina == "CURSOS":
#|         ss["nav"] = PAG_CURSOS
#|         return
#|     ss["nav"] = pagina
#|     if ambito:
#|         ss["tc_ambito"] = ambito
#|         ss["tc_sec_unidad" if ambito == UNIDAD else "tc_sec_clase"] = seccion
#|
#|
#| # ---------------- INICIO ----------------
#| def render():
#|     uid = st.session_state.user_id
#|     u = get_usuario(uid)
#|     asigs = listar_asignaciones(uid)
#|     nombre = html.escape(u["nombre"].split()[0])
#|     creditos = "ilimitados" if u["rol"] == "admin" else u["creditos"]
#|
#|     with caja("hero"):
#|         st.markdown(f"<div class='hero-t'>¡Hola, {nombre}! 👋</div>"
#|                     "<div class='hero-s'>Crea tu sílabo, tus clases, fichas, desafíos y exámenes en minutos, "
#|                     "alineados al CNEB y a la RM N.° 501-2025-MINEDU.</div>"
#|                     f"<span class='chip'>🎟️ Créditos: {creditos}</span>", unsafe_allow_html=True)
#|         b1, b2, _ = st.columns([1.4, 1.4, 3])
#|         b1.button("➕ Crear curso", key="hero_crear", on_click=_ir_crear, use_container_width=True)
#|         b2.button("📚 Mis cursos", key="hero_cursos", on_click=lambda: st.session_state.update(nav=PAG_CURSOS),
#|                   use_container_width=True)
#|
#|     st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
#|     if not asigs:
#|         st.info("💡 **Empieza aquí:** pulsa **➕ Crear curso** (solo toma un minuto) y luego sigue con el sílabo anual.")
#|     else:
#|         activa = next((a for a in asigs if a["id"] == st.session_state.get("area_id")), asigs[0])
#|         r = resumen_todas(uid).get(activa["id"], {})
#|         with caja("continuar", borde=True):
#|             c1, c2 = st.columns([4, 1.3])
#|             c1.markdown(f"**▶ Sigue donde te quedaste:** {ICONO_AREA.get(activa['area'], '📘')} {activa['area']} · {activa['grado']} · "
#|                         f"Sección {activa['seccion'] or '—'}")
#|             c1.caption(f"Sílabo {'✅' if r.get('anual') else '⬜'}   ·   Unidades {r.get('unidad', 0)}   ·   "
#|                        f"Clases {r.get('sesion', 0)}   ·   Documentos {sum(r.values()) if r else 0}")
#|             c2.button("Continuar ▶", key="continuar_btn", on_click=abrir_siguiente, args=(activa["id"],),
#|                       type="primary", use_container_width=True)
#|
#|     st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
#|     st.subheader("🛠️ ¿Qué quieres crear hoy?")
#|     st.caption("Elige una herramienta. En la siguiente pantalla te preguntaré para qué curso.")
#|     for fila in range(0, len(HERRAMIENTAS), 3):
#|         cols = st.columns(3, gap="medium")
#|         for col, (icono, titulo, desc, pagina, ambito, seccion) in zip(cols, HERRAMIENTAS[fila:fila + 3]):
#|             with col:
#|                 with caja(f"card_{titulo.replace(' ', '_')}", borde=True):
#|                     st.markdown(f"<div class='tool-i'>{icono}</div><div class='tool-t'>{titulo}</div>"
#|                                 f"<div class='tool-d'>{desc}</div>", unsafe_allow_html=True)
#|                     st.button("Abrir", key=f"tool_{titulo}", on_click=_ir_herramienta, args=(pagina, ambito, seccion),
#|                               use_container_width=True, type="primary" if pagina == "CURSOS" else "secondary")
#|     st.caption("Los pasos también están en el menú de la izquierda: Sílabo anual, Calendario, Currículo oficial y Mi biblioteca.")
#|
#|
#| # ---------------- MIS CURSOS ----------------
#| def _formulario_crear(uid, u):
#|     with caja("form_crear", borde=True):
#|         st.markdown("#### ➕ Nuevo curso")
#|         st.caption("Estos datos aparecerán en todos tus documentos (los puedes cambiar después).")
#|         c1, c2 = st.columns(2, gap="medium")
#|         nivel = c1.selectbox("Nivel", NIVELES, index=1, key="na_nivel")
#|         grado = c2.selectbox("Grado / edad", GRADOS[nivel], key="na_grado")
#|         areas = areas_de(nivel)
#|         area = c1.selectbox("Área curricular", areas, key="na_area") if areas else None
#|         c2.text_input("Sección (ej.: A)", key="na_seccion")
#|         inst_def = u["colegio"] if u["colegio"] and u["colegio"] != "Independiente" else ""
#|         c1.text_input("Institución educativa", value=inst_def, key="na_inst")
#|         c2.text_input("Nombre del director(a)", key="na_dir")
#|         c1.text_input("Nombre del docente", value=u["nombre"], key="na_doc")
#|         c2.selectbox("Región", REGIONES, index=REGIONES.index("Lima"), key="na_region")
#|         c1.number_input("Año escolar", 2024, 2035, 2026, key="na_ciclo")
#|         if area:
#|             _, _, n_des = estado_area(nivel, area, grado)
#|             if n_des == 0:
#|                 st.caption("ℹ️ Para este grado aún no hay desempeños oficiales cargados. Después podrás traerlos del MINEDU "
#|                            "con IA o subir tus propios lineamientos en el paso «Lineamientos» del sílabo.")
#|         b1, b2, _ = st.columns([1.3, 1, 3])
#|         b1.button("✅ Crear curso", type="primary", key="na_crear", on_click=_crear_curso_cb, args=(uid,),
#|                   use_container_width=True)
#|         b2.button("Cancelar", key="na_cancelar", on_click=_alternar_crear, use_container_width=True)
#|
#|
#| def render_cursos():
#|     uid = st.session_state.user_id
#|     u = get_usuario(uid)
#|     asigs = listar_asignaciones(uid)
#|     st.title("📚 Mis cursos")
#|     st.caption("Aquí están todos tus cursos. Abre uno para seguir trabajando.")
#|
#|     b1, b2, b3 = st.columns([1.4, 3.6, 0.6])
#|     abierto = st.session_state.get("crear_abierto", False) or not asigs
#|     if not abierto:
#|         b1.button("➕ Crear curso", key="cursos_crear", on_click=_alternar_crear, type="primary", use_container_width=True)
#|     if asigs:
#|         b3.button("🗑️", key="del_todos_btn", on_click=_pedir_borrar_todos, help="Eliminar TODOS mis cursos")
#|     if st.session_state.get("_del_todos"):
#|         st.warning("⚠️ ¿Eliminar **todos** tus cursos y todos sus documentos? No se puede deshacer.")
#|         y, n, _ = st.columns([2, 1, 3])
#|         y.button("Sí, eliminar todos", key="del_todos_si", on_click=_borrar_todos_cb, args=(uid,), type="primary")
#|         n.button("No", key="del_todos_no", on_click=_cancelar_borrar_todos)
#|     if abierto:
#|         _formulario_crear(uid, u)
#|     if not asigs:
#|         st.info("💡 Aún no tienes cursos. Completa los datos de arriba y pulsa **Crear curso**.")
#|         return
#|
#|     st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
#|     activa = st.session_state.get("area_id")
#|     resumen = resumen_todas(uid)
#|     for nivel in NIVELES:
#|         grupo = [a for a in asigs if a["nivel"] == nivel]
#|         if not grupo:
#|             continue
#|         st.markdown(f"### {nivel}")
#|         for fila in range(0, len(grupo), 3):
#|             cols = st.columns(3, gap="medium")
#|             for col, a in zip(cols, grupo[fila:fila + 3]):
#|                 with col:
#|                     with caja(f"curso_{a['id']}", borde=True):
#|                         st.markdown(f"<div class='curso-t'>{ICONO_AREA.get(a['area'], '📘')} {html.escape(a['area'])}</div>",
#|                                     unsafe_allow_html=True)
#|                         st.markdown(f"<div class='curso-s'>{a['grado']} · Sección {html.escape(a['seccion'] or '—')} · "
#|                                     f"{a['ciclo_escolar']}" + ("  ·  <b style='color:#7c3aed'>● activo</b>" if a["id"] == activa else "")
#|                                     + "</div>", unsafe_allow_html=True)
#|                         if st.session_state.get(f"_del_{a['id']}"):
#|                             st.warning(f"¿Eliminar «{a['area']}»? Se borran sus documentos.")
#|                             y, n = st.columns(2)
#|                             y.button("Sí", key=f"xy_{a['id']}", on_click=_borrar_curso_cb, args=(a["id"],), type="primary",
#|                                      use_container_width=True)
#|                             n.button("No", key=f"xn_{a['id']}", on_click=_cancelar_borrar, args=(a["id"],),
#|                                      use_container_width=True)
#|                         else:
#|                             r = resumen.get(a["id"], {})
#|                             st.markdown(f"<div class='curso-p'>📅 Sílabo {'✅' if r.get('anual') else '⬜'} &nbsp;·&nbsp; "
#|                                         f"📚 {r.get('unidad', 0)} unidades &nbsp;·&nbsp; 📝 {r.get('sesion', 0)} clases</div>",
#|                                         unsafe_allow_html=True)
#|                             b1, b2 = st.columns([4, 1.3])
#|                             b1.button("Abrir ▶", key=f"abrir_{a['id']}", on_click=abrir_siguiente, args=(a["id"],),
#|                                       use_container_width=True, type="primary")
#|                             b2.button("🗑️", key=f"x_{a['id']}", on_click=_pedir_borrar, args=(a["id"],),
#|                                       help="Eliminar este curso", use_container_width=True)
#@@ END
#@@ MODULE v_anual
#| """Sílabo anual: datos, lineamientos del Estado, caracterización, competencias, unidades y temas (clases)."""
#| import streamlit as st
#|
#| from curriculo import buscar_competencia, ciclo_de, competencias_de, contexto_curricular, estado_area
#| from ia import generar_texto, pedir_json, preambulo
#| from lineamientos import desde_archivo, traer_oficial, usar_oficial
#| from normativa import normativa_vigente
#| from repo import actualizar_asignacion, cobrar, contenido, get_doc, guardar_doc
#| from ui import (MIME_DOCX, PAG_TEMAS, campo_linea, descargar, campo_multi, campo_num, campo_texto, confirmar, exigir_area, flash, ir_a,
#|                 siguiente_version, vista_previa_y_descarga)
#| from util import a_lista, entero, norm, s
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
#| def _normalizar_temas(lista, mapa, comp_unidad):
#|     temas = []
#|     for x in lista or []:
#|         if isinstance(x, str):
#|             x = {"titulo": x}
#|         if not isinstance(x, dict) or not s(x.get("titulo")):
#|             continue
#|         nombre = buscar_competencia(x.get("competencia"), mapa) or comp_unidad
#|         info = mapa.get(nombre)
#|         n = entero(x.get("desempeno"), 0)
#|         texto = info["des"][n - 1]["texto"] if info and 1 <= n <= len(info["des"]) else ""
#|         temas.append({"titulo": s(x.get("titulo")), "competencia": nombre, "desempeno_texto": texto})
#|     return temas
#|
#|
#| def _generar_unidades(asig, comps_sel, n, spw):
#|     nombres = [c["nombre"] for c in comps_sel]
#|     ctx, mapa = contexto_curricular(asig["nivel"], asig["area"], asig["grado"], nombres, asig["id"])
#|     prompt = f"""{preambulo()}
#| Elabora el SÍLABO ANUAL {asig['ciclo_escolar']} con {n} unidades de aprendizaje y los temas (clases) de cada una.
#| Datos: nivel {asig['nivel']}, grado {asig['grado']}, área {asig['area']}, región {asig['region']}, institución {asig['institucion'] or 'no indicada'}.
#| Caracterización de los estudiantes: {asig.get('caracterizacion') or 'no especificada'}
#|
#| Lineamientos oficiales del curso (usa SOLO estos nombres de competencia, EXACTOS; D1, D2... son desempeños oficiales por competencia y NO se reescriben):
#| {ctx}
#|
#| Para cada unidad entrega:
#| - "titulo": título corto y motivador.
#| - "problema": problema identificado del contexto (1 a 2 oraciones).
#| - "situacion": situación significativa contextualizada a {asig['region']} (4 a 6 oraciones) con un reto y preguntas retadoras.
#| - "valores": valores observables (2 a 3, separados por coma) de los enfoques transversales del CNEB.
#| - "competencias": 1 a 3 nombres EXACTOS de la lista. Entre todas las unidades deben cubrirse todas las competencias.
#| - "semanas": número entre 3 y 5.
#| - "temas": lista de clases de la unidad, EXACTAMENTE semanas × {spw} temas. Cada tema: {{"titulo": "tema concreto de la clase", "competencia": nombre EXACTO, "desempeno": número del D que desarrolla}}.
#| Los temas deben avanzar de lo simple a lo complejo y cubrir los desempeños de las competencias de la unidad.
#|
#| Formato: {{"unidades":[{{"numero":1,"titulo":"...","problema":"...","situacion":"...","valores":"...","competencias":["..."],"semanas":4,"temas":[{{"titulo":"...","competencia":"...","desempeno":1}}]}}]}}"""
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
#|                          "competencias": elegidas, "capacidades": caps, "semanas": entero(u.get("semanas"), 4, 1, 12),
#|                          "temas": _normalizar_temas(u.get("temas"), mapa, elegidas[0])})
#|     return unidades
#|
#|
#| def _vacia(i, comps_sel):
#|     c = comps_sel[(i - 1) % len(comps_sel)]
#|     return {"numero": i, "titulo": f"Unidad {i}", "problema": "", "situacion": "", "valores": "",
#|             "competencias": [c["nombre"]], "capacidades": list(c["capacidades"]), "semanas": 4, "temas": []}
#|
#|
#| # ------------------------------------------------------------------
#| def _paso_lineamientos(asig, ver_key):
#|     aid, uid = asig["id"], st.session_state.user_id
#|     propio = asig.get("lineamientos_fuente") or ""
#|     n_comp, n_ver, n_des = estado_area(asig["nivel"], asig["area"], asig["grado"], aid)
#|     st.markdown("**¿Con qué lineamientos armamos tu sílabo?**  Siempre son textos del Estado, nunca inventados por la IA.")
#|     if propio:
#|         st.success(f"📌 Estás usando lineamientos propios de este curso: {propio}")
#|         if st.button("↩️ Volver a usar el currículo oficial del sistema", key=f"lin_oficial_{aid}"):
#|             usar_oficial(asig)
#|             flash("Ahora el curso usa el currículo oficial del sistema.")
#|             st.rerun()
#|     elif n_ver == n_comp and n_des == n_comp:
#|         st.success(f"✅ El currículo oficial de {asig['area']} · {asig['grado']} está verificado y listo.")
#|     else:
#|         st.warning(f"⚠️ El currículo oficial de este curso aún no está completo ({n_des} de {n_comp} competencias con "
#|                    "desempeños). Puedes traerlo del MINEDU con IA o subir tus propios lineamientos.")
#|
#|     opcion = st.radio("Origen de los lineamientos", ["📘 Currículo oficial del sistema", "🔎 Consultar el MINEDU con IA",
#|                                                       "📤 Subir mis lineamientos (PDF o Word)"],
#|                       key=f"lin_op_{aid}", horizontal=True, label_visibility="collapsed")
#|     if opcion.startswith("🔎"):
#|         st.caption("El sistema revisa los PDF oficiales del MINEDU en gob.pe, busca los desempeños de este curso y los "
#|                    "comprueba palabra por palabra contra el documento. Puede tardar unos minutos la primera vez.")
#|         if confirmar("lineamientos", "Traer lineamientos del MINEDU", f"lin_traer_{aid}"):
#|             barra = st.progress(0.0)
#|             try:
#|                 res = traer_oficial(asig, lambda f, t: barra.progress(min(f, 1.0), text=t))
#|                 cobrar(uid, "lineamientos")
#|                 flash(f"Listo: {res['desempenos']} desempeño(s) y {res['estandares']} estándar(es) verificados contra el PDF oficial.")
#|                 siguiente_version(ver_key)
#|                 st.rerun()
#|             except Exception as e:
#|                 st.error(f"No se pudo: {e}")
#|     elif opcion.startswith("📤"):
#|         st.caption("Sube el documento con tus lineamientos (por ejemplo, el Programa Curricular de tu nivel). "
#|                    "Solo se usarán los desempeños que aparezcan en tu archivo.")
#|         archivo = st.file_uploader("Archivo PDF o Word", type=["pdf", "docx", "txt"], key=f"lin_up_{aid}")
#|         if archivo is not None and confirmar("lineamientos", "Leer mis lineamientos", f"lin_leer_{aid}"):
#|             barra = st.progress(0.0)
#|             try:
#|                 res = desde_archivo(asig, archivo.name, archivo.getvalue(), lambda f, t: barra.progress(min(f, 1.0), text=t))
#|                 cobrar(uid, "lineamientos")
#|                 flash(f"Listo: {res['desempenos']} desempeño(s) y {res['estandares']} estándar(es) leídos de tu archivo.")
#|                 siguiente_version(ver_key)
#|                 st.rerun()
#|             except Exception as e:
#|                 st.error(f"No se pudo leer: {e}")
#|
#|
#| def render():
#|     asig = exigir_area()
#|     uid, aid = st.session_state.user_id, asig["id"]
#|     st.title("📅 Sílabo anual")
#|     st.caption(f"{asig['area']} · {asig['grado']} · Sección {asig['seccion'] or '—'}  |  Alineado a CNEB y RM N.° 501-2025-MINEDU")
#|     st.info("💡 Sigue los pasos de arriba hacia abajo. Lo que escribe la IA siempre lo puedes editar antes de guardar.")
#|
#|     ver_key = f"ver_anual_{aid}"
#|     ver = st.session_state.get(ver_key, 0)
#|     doc = get_doc(aid, "anual")
#|     data = contenido(doc) if doc else {}
#|     if doc:
#|         from exportar import bloques_de
#|         from render import a_docx
#|         bl, hor, archivo = bloques_de(doc)
#|         descargar("⬇️ Descargar mi sílabo en Word", a_docx(bl, doc.get("color"), doc.get("normativa_usada"), hor), archivo,
#|                   MIME_DOCX, f"dl_top_anual_{aid}", type="primary")
#|
#|     # ① DATOS
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
#|     # ② LINEAMIENTOS
#|     st.subheader("② Lineamientos del Estado")
#|     _paso_lineamientos(asig, ver_key)
#|
#|     # ③ CARACTERIZACIÓN
#|     st.subheader("③ Caracterización de tus estudiantes")
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
#|     # ④ COMPETENCIAS
#|     st.subheader("④ Competencias que trabajarás este año")
#|     comps = competencias_de(asig["nivel"], asig["area"])
#|     if not comps:
#|         st.error("Este curso todavía no tiene competencias cargadas. Pide al administrador que las agregue en "
#|                  "Administración → Currículo.")
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
#|     # ⑤ UNIDADES Y TEMAS
#|     st.subheader("⑤ Unidades, situaciones significativas y temas")
#|     unidades = data.get("unidades") or []
#|     n = len(unidades)
#|     spw = 3
#|     if not unidades:
#|         c1, c2 = st.columns(2)
#|         n = int(c1.number_input("¿Cuántas unidades tendrá el año?", 1, 12, 6, key=f"nuni_{aid}"))
#|         spw = int(c2.number_input("Clases por semana", 1, 8, 3, key=f"spw_anual_{aid}"))
#|     st.caption("La IA propone, con los lineamientos de arriba, una situación significativa por unidad y los temas "
#|                "(clases) de cada una.")
#|     if confirmar("anual", "✨ Generar sílabo con IA" if not unidades else "🔄 Volver a generar (reemplaza lo actual)",
#|                  f"anual_{aid}", asig=asig):
#|         try:
#|             with st.spinner("Creando tu sílabo... (puede tardar un minuto)"):
#|                 nuevas = _generar_unidades(asig, comps_sel, n, spw)
#|             guardar_doc(uid, aid, "anual", 1, f"Sílabo anual {asig['area']} {asig['grado']}",
#|                         {"competencias_area": sel, "unidades": nuevas, "clases_por_semana": spw},
#|                         normativa=normativa_vigente()[1])
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
#|             with st.expander(f"Unidad {i}: {u['titulo']}  ·  {len(u.get('temas') or [])} temas", expanded=(i == 1)):
#|                 campo_linea("Título de la unidad", f"{base}_t", u["titulo"])
#|                 campo_texto("Problema identificado", f"{base}_p", u["problema"], 80)
#|                 campo_texto("Situación significativa", f"{base}_s", u["situacion"], 160)
#|                 campo_linea("Valores observables", f"{base}_v", u["valores"])
#|                 cs = campo_multi("Competencias de esta unidad", f"{base}_c", sel, u["competencias"])
#|                 caps_op = [cap for c in comps if c["nombre"] in cs for cap in c["capacidades"]]
#|                 campo_multi("Capacidades a trabajar", f"{base}_k", caps_op, u["capacidades"])
#|                 campo_num("Semanas", f"{base}_w", 1, 12, u.get("semanas") or 4)
#|                 campo_texto("Temas / clases de la unidad (uno por línea)", f"{base}_tm",
#|                             "\n".join(t["titulo"] for t in u.get("temas") or []), 180,
#|                             "Estos temas son los que luego eliges en «Temas y clases» para crear sesiones, fichas y desafíos.")
#|
#|         def recoger():
#|             res = []
#|             for u in unidades:
#|                 i = u["numero"]
#|                 base = f"an_{aid}_{ver}_{i}"
#|                 previos = {norm(t["titulo"]): t for t in u.get("temas") or []}
#|                 cs = st.session_state.get(f"{base}_c", u["competencias"])
#|                 temas = []
#|                 for linea in a_lista(st.session_state.get(f"{base}_tm", "")):
#|                     t = previos.get(norm(linea)) or {"titulo": linea, "competencia": (cs or [""])[0], "desempeno_texto": ""}
#|                     temas.append({**t, "titulo": linea})
#|                 res.append({"numero": i, "titulo": st.session_state.get(f"{base}_t", u["titulo"]),
#|                             "problema": st.session_state.get(f"{base}_p", ""),
#|                             "situacion": st.session_state.get(f"{base}_s", ""),
#|                             "valores": st.session_state.get(f"{base}_v", ""),
#|                             "competencias": cs, "capacidades": st.session_state.get(f"{base}_k", u["capacidades"]),
#|                             "semanas": entero(st.session_state.get(f"{base}_w"), 4, 1, 12), "temas": temas})
#|             return res
#|
#|         def guardar(lista):
#|             guardar_doc(uid, aid, "anual", 1, f"Sílabo anual {asig['area']} {asig['grado']}",
#|                         {**data, "competencias_area": sel, "unidades": lista})
#|
#|         b1, b2, b3 = st.columns(3)
#|         if b1.button("💾 Guardar sílabo", type="primary", key=f"an_save_{aid}", use_container_width=True):
#|             guardar(recoger())
#|             st.success("Sílabo guardado ✅")
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
#|     # ⑥ DOCUMENTO
#|     if doc:
#|         st.subheader("⑥ Tu documento")
#|         vista_previa_y_descarga(doc["id"], f"anual_{aid}")
#|         st.button("Siguiente: elegir un tema y crear sus materiales →", on_click=ir_a, args=(PAG_TEMAS,), type="primary")
#@@ END
#@@ MODULE v_unidades
#| """Unidades de aprendizaje: producto, secuencia por semanas, propósitos, enfoques; importar y sincronizar."""
#| import pandas as pd
#| import streamlit as st
#|
#| from curriculo import buscar_competencia, contexto_curricular, transversales
#| from docx import Document
#| from ia import generar_texto, pedir_json, preambulo
#| from examen_unidad import render as render_examen_unidad
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
#|     spw_ = max(1, int(spw))
#|     for i, tm in enumerate(ua.get("temas") or []):           # los temas del sílabo anual mandan
#|         secuencia.append({"semana": i // spw_ + 1, "titulo": tm["titulo"],
#|                           "competencia": buscar_competencia(tm.get("competencia"), mapa) or primera})
#|     for f in ([] if secuencia else ia.get("secuencia") or []):
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
#|     ctx, mapa = contexto_curricular(asig["nivel"], asig["area"], asig["grado"], ua["competencias"], asig["id"])
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
#| - "secuencia": {'(ya viene dada por los temas del sílabo; igual devuélvela)' if ua.get('temas') else ''} lista de EXACTAMENTE {total} sesiones, cada una {{"semana": n, "titulo": pregunta o reto en voz del estudiante (ej. "¿Cómo repartimos en partes iguales?"), "competencia": nombre EXACTO}}.
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
#|     ctx, mapa = contexto_curricular(asig["nivel"], asig["area"], asig["grado"], ua["competencias"], asig["id"])
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
#|         if confirmar("unidad", etiqueta, f"unidad_{aid}_{n}", asig=asig):
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
#|             if archivo is not None and confirmar("importar", "Convertir mi unidad", f"imp_{aid}_{n}", asig=asig):
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
#|     vista_previa_y_descarga(doc["id"], f"unidad_{aid}_{n}")
#|     with st.expander("✏️ Editar la unidad"):
#|         # --- Edición
#|         base = f"u_{aid}_{n}_{ver}"
#|         st.markdown("### ✏️ Edita tu unidad")
#|         campo_linea("Título de la unidad", f"{base}_tit", d.get("titulo", ""))
#|         campo_texto("Situación significativa", f"{base}_sit", d.get("situacion", ""), 150)
#|
#|         st.markdown("**Producto de aprendizaje**")
#|         pr = d.get("producto") or {}
#|         campo_texto("Evidencia (producto final)", f"{base}_pe", pr.get("evidencia", ""), 80)
#|         campo_texto("Criterios de evaluación (uno por línea)", f"{base}_pc", pr.get("criterios", ""), 110)
#|         campo_texto("Relación con otras áreas", f"{base}_pr", pr.get("relacion", ""), 80)
#|
#|         st.markdown("**Secuencia de la unidad** (cada fila es una sesión; puedes agregar, borrar o cambiar títulos)")
#|         nombres_comp = [p["competencia"] for p in d.get("propositos", [])]
#|         filas = [{"semana": f.get("semana", 1), "titulo": f.get("titulo", ""),
#|                   "competencia": f.get("competencia") if f.get("competencia") in nombres_comp else (nombres_comp[0] if nombres_comp else "")}
#|                  for f in d.get("secuencia", [])]
#|         df = pd.DataFrame(filas, columns=["semana", "titulo", "competencia"])
#|         df["semana"] = pd.to_numeric(df["semana"], errors="coerce").fillna(1).astype(int)
#|         seq = st.data_editor(df, key=f"{base}_seq", num_rows="dynamic", hide_index=True, column_config={
#|             "semana": st.column_config.NumberColumn("Semana", min_value=1, max_value=20, step=1),
#|             "titulo": st.column_config.TextColumn("Título / pregunta retadora", width="large"),
#|             "competencia": st.column_config.SelectboxColumn("Competencia", options=nombres_comp or [""])})
#|
#|         st.markdown("**Propósitos de aprendizaje**")
#|         props = d.get("propositos", [])
#|         for j, p in enumerate(props):
#|             with st.expander(p["competencia"], expanded=(j == 0)):
#|                 if p.get("por_verificar"):
#|                     st.caption("⚠️ Desempeños por verificar con el Programa Curricular oficial.")
#|                 campo_texto("Capacidades (una por línea)", f"{base}_p{j}_cap", a_texto(p.get("capacidades")), 90)
#|                 campo_texto("Desempeños (uno por línea)", f"{base}_p{j}_des", a_texto(p.get("desempenos")), 130)
#|                 campo_texto("Propósito de aprendizaje", f"{base}_p{j}_pro", p.get("proposito", ""), 80)
#|                 campo_linea("Campo temático", f"{base}_p{j}_ct", p.get("campo_tematico", ""))
#|                 campo_texto("Evidencia", f"{base}_p{j}_ev", p.get("evidencia", ""), 70)
#|                 campo_linea("Instrumento de evaluación", f"{base}_p{j}_in", p.get("instrumento", ""))
#|
#|         st.markdown("**Enfoques transversales**")
#|         enfoques_db = transversales()[1]
#|         nombres_enf = [e["nombre"] for e in enfoques_db]
#|         elegidos = campo_multi("Enfoques de esta unidad", f"{base}_enf", nombres_enf,
#|                                [e["enfoque"] for e in d.get("enfoques", [])])
#|         previos = {e["enfoque"]: e.get("acciones", "") for e in d.get("enfoques", [])}
#|         for k, nombre in enumerate(elegidos):
#|             campo_texto(f"Acciones observables — {nombre}", f"{base}_enf_{k}_{norm(nombre)[:12]}",
#|                         previos.get(nombre, ""), 70)
#|
#|         def recoger():
#|             st_ = st.session_state
#|             nueva_seq = []
#|             for _, f in seq.fillna("").iterrows():
#|                 if s(f["titulo"]):
#|                     nueva_seq.append({"semana": entero(f["semana"], 1, 1, 20), "titulo": s(f["titulo"]),
#|                                       "competencia": s(f["competencia"])})
#|             nuevos_props = []
#|             for j, p in enumerate(props):
#|                 nuevos_props.append({**p, "capacidades": a_lista(st_.get(f"{base}_p{j}_cap")),
#|                                      "desempenos": a_lista(st_.get(f"{base}_p{j}_des")),
#|                                      "proposito": st_.get(f"{base}_p{j}_pro", ""),
#|                                      "campo_tematico": st_.get(f"{base}_p{j}_ct", ""),
#|                                      "evidencia": st_.get(f"{base}_p{j}_ev", ""),
#|                                      "instrumento": st_.get(f"{base}_p{j}_in", "")})
#|             nuevos_enf = []
#|             for k, nombre in enumerate(st_.get(f"{base}_enf", [])):
#|                 e = next((x for x in enfoques_db if x["nombre"] == nombre), None)
#|                 nuevos_enf.append({"enfoque": nombre, "valores": ", ".join(e["items"]) if e else "",
#|                                    "acciones": st_.get(f"{base}_enf_{k}_{norm(nombre)[:12]}", "")})
#|             return {**d, "titulo": st_.get(f"{base}_tit", d.get("titulo")), "situacion": st_.get(f"{base}_sit", ""),
#|                     "producto": {"evidencia": st_.get(f"{base}_pe", ""), "criterios": st_.get(f"{base}_pc", ""),
#|                                  "relacion": st_.get(f"{base}_pr", "")},
#|                     "secuencia": nueva_seq, "propositos": nuevos_props, "enfoques": nuevos_enf}
#|
#|         b1, b2, b3 = st.columns(3)
#|         if b1.button("💾 Guardar unidad", type="primary", key=f"u_save_{aid}_{n}", use_container_width=True):
#|             nuevo = recoger()
#|             guardar_doc(uid, aid, "unidad", n, f"Unidad {n}: {nuevo['titulo']}", nuevo, padre_id=anual["id"])
#|             st.success("Unidad guardada ✅")
#|         if b2.button("🔄 Sincronizar con la anual", key=f"u_sync_{aid}_{n}", use_container_width=True,
#|                      help="Trae de la planificación anual la situación significativa y ajusta las competencias."):
#|             _sincronizar(asig, anual, ua, recoger(), ver_key)
#|         if b3.button("🧩 Crear sesiones de la secuencia", key=f"u_ses_{aid}_{n}", use_container_width=True,
#|                      help="Crea una sesión por cada fila de la secuencia, listas para generar."):
#|             nuevo = recoger()
#|             gid = guardar_doc(uid, aid, "unidad", n, f"Unidad {n}: {nuevo['titulo']}", nuevo, padre_id=anual["id"])
#|             creadas = crear_sesiones_desde_secuencia(uid, asig, get_doc_by_id(gid))
#|             flash(f"Se crearon {creadas} sesión(es). Ahora ve a la pestaña Sesiones.")
#|             st.rerun()
#|
#|     with st.expander("🔎 Revisar coherencia con la planificación anual"):
#|         if confirmar("revision", "Revisar con IA", f"rev_{aid}_{n}", asig=asig):
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
#|
#|     if listar_docs(aid, "sesion", padre_id=doc["id"]):
#|         st.button("Siguiente: generar las sesiones →", on_click=ir_a, args=(PAG_SESIONES,), type="primary",
#|                   key=f"u_next_{aid}_{n}")
#|
#|
#| def _sincronizar(asig, anual, ua, actual, ver_key):
#|     """Trae la situación de la anual y alinea las filas de propósitos con las competencias de la unidad anual."""
#|     uid, aid = st.session_state.user_id, asig["id"]
#|     _, mapa = contexto_curricular(asig["nivel"], asig["area"], asig["grado"], ua["competencias"], asig["id"])
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
#|
#|
#| def asegurar_unidad(asig, anual, ua):
#|     """Devuelve el documento de la unidad; si no existe lo arma SIN IA a partir del sílabo (temas y currículo)."""
#|     uid, aid = st.session_state.user_id, asig["id"]
#|     doc = get_doc(aid, "unidad", numero=ua["numero"])
#|     if doc:
#|         return doc
#|     _, mapa = contexto_curricular(asig["nivel"], asig["area"], asig["grado"], ua["competencias"], aid)
#|     props = []
#|     for nombre, info in mapa.items():
#|         ds = [x["texto"] for x in info["des"][:3]]
#|         props.append({"competencia": nombre, "capacidades": info["comp"]["capacidades"], "desempenos": ds,
#|                       "por_verificar": not ds, "proposito": "", "campo_tematico": "", "evidencia": "", "instrumento": ""})
#|     primera = next(iter(mapa), "")
#|     spw = int(anual and contenido(anual).get("clases_por_semana") or 3)
#|     secuencia = [{"semana": i // spw + 1, "titulo": tm["titulo"],
#|                   "competencia": buscar_competencia(tm.get("competencia"), mapa) or primera}
#|                  for i, tm in enumerate(ua.get("temas") or [])]
#|     data = {"numero": ua["numero"], "titulo": ua["titulo"], "situacion": ua["situacion"],
#|             "producto": {"evidencia": "", "criterios": "", "relacion": ""}, "secuencia": secuencia,
#|             "propositos": props, "enfoques": [], "semanas": ua.get("semanas") or 4, "sesiones_por_semana": spw}
#|     gid = guardar_doc(uid, aid, "unidad", ua["numero"], f"Unidad {ua['numero']}: {ua['titulo']}", data,
#|                       padre_id=anual["id"], normativa=normativa_vigente()[1])
#|     return get_doc_by_id(gid)
#@@ END
#@@ MODULE v_sesiones
#| """Temas y clases: sesión, ficha, rúbrica, desafíos y examen de cada tema; unidad, desafíos y examen de la unidad."""
#| import streamlit as st
#|
#| from examen_unidad import render as render_examen_unidad
#| from ia import pedir_json, preambulo
#| from normativa import normativa_vigente
#| from repo import cobrar, contenido, crear_sesiones_desde_secuencia, get_doc, guardar_doc, listar_docs
#| from ui import (PAG_ANUAL, barra_edicion, campo_linea, campo_num, campo_texto, confirmar, editor_items, exigir_area,
#|                 exigir_cadena, flash, ir_a, recoger_items, seccion, siguiente_version, vista_previa_y_descarga)
#| from v_unidades import _unidad, asegurar_unidad
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
#| # PANTALLA: TEMAS Y CLASES
#| # ------------------------------------------------------------------
#| def render():
#|     asig = exigir_area()
#|     uid, aid = st.session_state.user_id, asig["id"]
#|     st.title("🎯 Temas y clases")
#|     st.info("💡 Elige un tema de tu sílabo (una clase) o una unidad completa y crea con IA sus sesiones, fichas, "
#|             "desafíos, rúbricas y exámenes.")
#|     anual = get_doc(aid, "anual")
#|     if not anual:
#|         exigir_cadena("Primero crea tu sílabo anual: de ahí salen las unidades y los temas.", PAG_ANUAL,
#|                       "Ir al Sílabo anual")
#|     unidades = contenido(anual).get("unidades") or []
#|     if not unidades:
#|         exigir_cadena("Tu sílabo anual todavía no tiene unidades. Genera el sílabo primero.", PAG_ANUAL,
#|                       "Ir al Sílabo anual")
#|
#|     num = st.radio("Unidad", [u["numero"] for u in unidades], horizontal=True, key=f"tc_unidad_{aid}",
#|                    format_func=lambda n: f"Unidad {n}")
#|     ua = next(u for u in unidades if u["numero"] == num)
#|     st.caption(f"**{ua['titulo']}** · {len(ua.get('temas') or [])} temas")
#|     udoc = asegurar_unidad(asig, anual, ua)
#|     udata = contenido(udoc)
#|
#|     ambito = st.radio("¿Qué quieres trabajar?", ["📖 Una clase (un tema)", "📚 Toda la unidad"], horizontal=True,
#|                       key="tc_ambito")
#|     if ambito.startswith("📚"):
#|         sec = seccion(["📚 Unidad de aprendizaje", "🏆 Desafíos de la unidad", "📋 Examen de la unidad"], "tc_sec_unidad")
#|         if sec.startswith("📚"):
#|             _unidad(asig, anual, ua)
#|         elif sec.startswith("🏆"):
#|             _tab_desafios(asig, udoc, udata, "unidad")
#|         else:
#|             render_examen_unidad(asig, udoc)
#|         return
#|
#|     sesiones = listar_docs(aid, "sesion", padre_id=udoc["id"])
#|     if not sesiones and udata.get("secuencia"):
#|         crear_sesiones_desde_secuencia(uid, asig, udoc)
#|         sesiones = listar_docs(aid, "sesion", padre_id=udoc["id"])
#|     if not sesiones:
#|         st.warning("Esta unidad todavía no tiene temas. Agrégalos en el **Sílabo anual** (campo «Temas / clases») "
#|                    "o elige «Toda la unidad» para generar la unidad con IA.")
#|         st.button("Ir al Sílabo anual", on_click=ir_a, args=(PAG_ANUAL,))
#|         st.stop()
#|
#|     def etiqueta(i):
#|         sd = contenido(sesiones[i])
#|         return f"{'✅' if sd.get('inicio') else '⬜'} Clase {sesiones[i]['numero']}: {sd.get('titulo', '')}"
#|
#|     _masivo(asig, udoc, udata, sesiones)
#|     idx = st.selectbox("Elige el tema (clase)", list(range(len(sesiones))), format_func=etiqueta,
#|                        key=f"se_sel_{udoc['id']}")
#|     sdoc = sesiones[idx]
#|     sec = seccion(["📖 Sesión de aprendizaje", "📄 Ficha de trabajo", "📊 Rúbrica", "🏆 Desafíos", "📋 Examen"],
#|                   "tc_sec_clase")
#|     if sec.startswith("📖"):
#|         _tab_contenido(asig, udoc, udata, sdoc)
#|     elif sec.startswith("📄"):
#|         _tab_ficha(asig, sdoc)
#|     elif sec.startswith("📊"):
#|         _tab_rubrica(asig, sdoc)
#|     elif sec.startswith("🏆"):
#|         _tab_desafios(asig, sdoc, udata, "clase")
#|     else:
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
#|         if confirmar("sesion", f"Generar las {len(faltan)} sesiones", f"mas_{udoc['id']}", veces=len(faltan), asig=asig):
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
#| # SESIÓN
#| # ------------------------------------------------------------------
#| def _tab_contenido(asig, udoc, udata, sdoc):
#|     uid, aid = st.session_state.user_id, asig["id"]
#|     d = contenido(sdoc)
#|     ver_key = f"ver_ses_{sdoc['id']}"
#|     ver = st.session_state.get(ver_key, 0)
#|     props = [p["competencia"] for p in udata.get("propositos", [])]
#|     hecho = bool(d.get("inicio"))
#|
#|     with st.expander("⚙️ Opciones y generación con IA", expanded=not hecho):
#|         c1, c2 = st.columns(2)
#|         duracion = c1.number_input("Duración (minutos)", 20, 240, entero(d.get("duracion"), 90, 20, 240), step=5,
#|                                    key=f"ses_dur_{sdoc['id']}_{ver}")
#|         sel = c2.multiselect("Competencias de esta sesión", props,
#|                              default=[x for x in (d.get("competencias_sugeridas") or props[:1]) if x in props],
#|                              key=f"ses_comp_{sdoc['id']}_{ver}")
#|         notas = st.text_input("Indicaciones especiales (opcional)", key=f"ses_notas_{sdoc['id']}_{ver}",
#|                               placeholder="Ej.: aula multigrado, sin proyector, usar material reciclable")
#|         etiqueta = "✨ Generar sesión con IA" if not hecho else "🔄 Volver a generar (reemplaza lo actual)"
#|         if confirmar("sesion", etiqueta, f"ses_{sdoc['id']}", asig=asig):
#|             try:
#|                 with st.spinner("Creando la sesión..."):
#|                     nuevo = generar_sesion(asig, udata, d, int(duracion), sel, notas)
#|                 guardar_doc(uid, aid, "sesion", sdoc["numero"], f"Sesión {sdoc['numero']}: {nuevo['titulo']}", nuevo,
#|                             padre_id=udoc["id"], normativa=normativa_vigente()[1])
#|                 cobrar(uid, "sesion")
#|                 siguiente_version(ver_key)
#|                 flash("¡Sesión lista! Descárgala en Word o edítala.")
#|                 st.rerun()
#|             except Exception as e:
#|                 st.error(f"No se pudo generar: {e}")
#|     if not hecho:
#|         st.caption("Aún no hay contenido en esta sesión.")
#|         return
#|
#|     vista_previa_y_descarga(sdoc["id"], f"sesion_{sdoc['id']}")
#|     with st.expander("✏️ Editar la sesión"):
#|         base = f"s_{sdoc['id']}_{ver}"
#|         campo_linea("Título de la sesión", f"{base}_tit", d.get("titulo", ""))
#|         campo_texto("Propósito de aprendizaje", f"{base}_pro", d.get("proposito", ""), 80)
#|         filas = d.get("competencias", [])
#|         for j, c in enumerate(filas):
#|             st.markdown(f"**Competencia:** {c['competencia']}" + ("  ⚠️ _desempeños por verificar_" if c.get("por_verificar") else ""))
#|             campo_texto("Criterios de evaluación (uno por línea)", f"{base}_c{j}_cr", a_texto(c.get("criterios")), 100)
#|             campo_texto("Evidencia de aprendizaje", f"{base}_c{j}_ev", c.get("evidencia", ""), 70)
#|             campo_linea("Instrumento", f"{base}_c{j}_in", c.get("instrumento", ""))
#|         st.markdown("**Secuencia didáctica**")
#|         for k, nombre in (("inicio", "Inicio"), ("desarrollo", "Desarrollo"), ("cierre", "Cierre")):
#|             m = d.get(k) or {}
#|             campo_texto(nombre, f"{base}_{k}_a", m.get("actividades", ""), 140 if k == "desarrollo" else 100)
#|             campo_num(f"Minutos de {nombre.lower()}", f"{base}_{k}_m", 1, 240, entero(m.get("minutos"), 10))
#|         campo_texto("Materiales y recursos (uno por línea)", f"{base}_mat", a_texto(d.get("materiales")), 90)
#|         campo_texto("Reflexión sobre el aprendizaje (una pregunta por línea)", f"{base}_ref", a_texto(d.get("reflexion")), 90)
#|         if st.button("💾 Guardar sesión", type="primary", key=f"s_save_{sdoc['id']}"):
#|             ss = st.session_state
#|             nuevas = [{**c, "criterios": a_lista(ss.get(f"{base}_c{j}_cr")), "evidencia": ss.get(f"{base}_c{j}_ev", ""),
#|                        "instrumento": ss.get(f"{base}_c{j}_in", "")} for j, c in enumerate(filas)]
#|             nuevo = {**d, "titulo": ss.get(f"{base}_tit", ""), "proposito": ss.get(f"{base}_pro", ""), "competencias": nuevas,
#|                      "materiales": a_lista(ss.get(f"{base}_mat")), "reflexion": a_lista(ss.get(f"{base}_ref"))}
#|             for k in ("inicio", "desarrollo", "cierre"):
#|                 nuevo[k] = {"actividades": ss.get(f"{base}_{k}_a", ""), "minutos": entero(ss.get(f"{base}_{k}_m"), 10, 1, 240)}
#|             guardar_doc(uid, aid, "sesion", sdoc["numero"], f"Sesión {sdoc['numero']}: {nuevo['titulo']}", nuevo,
#|                         padre_id=udoc["id"])
#|             st.success("Sesión guardada ✅ (la vista previa se actualiza al volver a abrir esta sección)")
#|
#|
#| def _necesita_sesion(sdoc):
#|     sd = contenido(sdoc)
#|     if not sd.get("inicio"):
#|         st.info("Primero genera la **sesión de aprendizaje** (sección «📖 Sesión de aprendizaje»): de ahí salen los "
#|                 "criterios y las evidencias.")
#|         return None
#|     return sd
#|
#|
#| # ------------------------------------------------------------------
#| # RÚBRICA
#| # ------------------------------------------------------------------
#| CAMPOS_RUBRICA = [{"k": "criterio", "label": "Criterio", "tipo": "linea"},
#|                   {"k": "AD", "label": "AD · Logro destacado", "tipo": "area", "alto": 70},
#|                   {"k": "A", "label": "A · Logro esperado", "tipo": "area", "alto": 70},
#|                   {"k": "B", "label": "B · En proceso", "tipo": "area", "alto": 70},
#|                   {"k": "C", "label": "C · En inicio", "tipo": "area", "alto": 70}]
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
#|     with st.expander("⚙️ Generar con IA", expanded=not doc):
#|         if confirmar("rubrica", "✨ Generar rúbrica con IA" if not doc else "🔄 Volver a generar la rúbrica",
#|                      f"rub_{sdoc['id']}", asig=asig):
#|             try:
#|                 prompt = f"""{preambulo()}
#| Elabora una RÚBRICA de evaluación para esta sesión (nivel {asig['nivel']}, grado {asig['grado']}, área {asig['area']}).
#| Sesión: {sd.get('titulo')}
#| Competencias, criterios y evidencias:
#| {_resumen_competencias(sd)}
#| Entrega entre 3 y 5 criterios (puedes partir de los criterios dados). Para cada uno describe lo observable en cuatro niveles: AD (logro destacado), A (logro esperado), B (en proceso), C (en inicio).
#| Formato: {{"criterios":[{{"criterio":"...","AD":"...","A":"...","B":"...","C":"..."}}]}}"""
#|                 with st.spinner("Creando la rúbrica..."):
#|                     ia, _ = pedir_json(prompt)
#|                 lista = ia.get("criterios") if isinstance(ia, dict) else ia
#|                 filas = [{"numero": i, "criterio": s(r.get("criterio")), "AD": s(r.get("AD")), "A": s(r.get("A")),
#|                           "B": s(r.get("B")), "C": s(r.get("C"))} for i, r in enumerate(lista or [], 1) if isinstance(r, dict)]
#|                 if not filas:
#|                     raise RuntimeError("La IA no devolvió criterios. Intenta de nuevo.")
#|                 guardar_doc(uid, aid, "rubrica", 1, f"Rúbrica: {sd.get('titulo')}", {"criterios": filas},
#|                             padre_id=sdoc["id"], normativa=normativa_vigente()[1])
#|                 cobrar(uid, "rubrica")
#|                 siguiente_version(ver_key)
#|                 flash("Rúbrica lista ✅")
#|                 st.rerun()
#|             except Exception as e:
#|                 st.error(f"No se pudo generar: {e}")
#|     if not doc:
#|         return
#|     vista_previa_y_descarga(doc["id"], f"rub_{sdoc['id']}")
#|     with st.expander("✏️ Editar la rúbrica"):
#|         clave = f"rub_{sdoc['id']}_{ver}"
#|         items = d.get("criterios", [])
#|         editor_items(clave, items, CAMPOS_RUBRICA, lambda i, x: f"Criterio {i + 1}: {s(x.get('criterio'))[:60]}")
#|         barra_edicion(clave, items, CAMPOS_RUBRICA,
#|                       lambda n: {"numero": n, "criterio": "", "AD": "", "A": "", "B": "", "C": ""},
#|                       lambda lista: guardar_doc(uid, aid, "rubrica", 1, doc["titulo"], {"criterios": lista}, padre_id=sdoc["id"]),
#|                       ver_key)
#|
#|
#| # ------------------------------------------------------------------
#| # FICHA DE TRABAJO
#| # ------------------------------------------------------------------
#| CAMPOS_FICHA = [{"k": "consigna", "label": "Consigna", "tipo": "area", "alto": 90},
#|                 {"k": "respuesta", "label": "Respuesta esperada (solo para el docente)", "tipo": "linea"}]
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
#|     with st.expander("⚙️ Generar con IA", expanded=not doc):
#|         n_act = st.number_input("Número de actividades", 3, 12, 6, key=f"fic_n_{sdoc['id']}")
#|         if confirmar("ficha", "✨ Generar ficha con IA" if not doc else "🔄 Volver a generar la ficha",
#|                      f"fic_{sdoc['id']}", asig=asig):
#|             try:
#|                 prompt = f"""{preambulo()}
#| Elabora una FICHA DE TRABAJO para estudiantes de {asig['grado']} ({asig['nivel']}), área {asig['area']}, región {asig['region']}.
#| Sesión: {sd.get('titulo')}. Propósito: {sd.get('proposito')}
#| Competencias y criterios:
#| {_resumen_competencias(sd)}
#| Entrega {int(n_act)} actividades graduadas (de lo simple a lo complejo), con lenguaje adecuado a la edad y contexto cercano a la región. Cada actividad incluye la respuesta esperada para el docente.
#| Formato: {{"titulo":"...","instrucciones":"...","actividades":[{{"numero":1,"consigna":"...","respuesta":"..."}}]}}"""
#|                 with st.spinner("Creando la ficha..."):
#|                     ia, _ = pedir_json(prompt)
#|                 acts = [{"numero": i, "consigna": s(a.get("consigna")), "respuesta": s(a.get("respuesta"))}
#|                         for i, a in enumerate((ia.get("actividades") if isinstance(ia, dict) else []) or [], 1) if isinstance(a, dict)]
#|                 if not acts:
#|                     raise RuntimeError("La IA no devolvió actividades. Intenta de nuevo.")
#|                 guardar_doc(uid, aid, "ficha", 1, f"Ficha: {sd.get('titulo')}",
#|                             {"titulo": s(ia.get("titulo")), "instrucciones": s(ia.get("instrucciones")), "actividades": acts},
#|                             padre_id=sdoc["id"], normativa=normativa_vigente()[1])
#|                 cobrar(uid, "ficha")
#|                 siguiente_version(ver_key)
#|                 flash("Ficha lista ✅")
#|                 st.rerun()
#|             except Exception as e:
#|                 st.error(f"No se pudo generar: {e}")
#|     if not doc:
#|         return
#|     vista_previa_y_descarga(doc["id"], f"fic_{sdoc['id']}")
#|     with st.expander("✏️ Editar la ficha"):
#|         clave = f"fic_{sdoc['id']}_{ver}"
#|         campo_linea("Título de la ficha", f"{clave}_t", d.get("titulo", ""))
#|         campo_texto("Indicaciones", f"{clave}_i", d.get("instrucciones", ""), 80)
#|         items = d.get("actividades", [])
#|         editor_items(clave, items, CAMPOS_FICHA, lambda i, x: f"Actividad {i + 1}: {s(x.get('consigna'))[:60]}")
#|         barra_edicion(clave, items, CAMPOS_FICHA, lambda n: {"numero": n, "consigna": "", "respuesta": ""},
#|                       lambda lista: guardar_doc(uid, aid, "ficha", 1, doc["titulo"],
#|                                                 {"titulo": st.session_state.get(f"{clave}_t", ""),
#|                                                  "instrucciones": st.session_state.get(f"{clave}_i", ""),
#|                                                  "actividades": lista}, padre_id=sdoc["id"]), ver_key)
#|
#|
#| # ------------------------------------------------------------------
#| # EXAMEN DE LA SESIÓN
#| # ------------------------------------------------------------------
#| CAMPOS_EXAMEN = [{"k": "tipo", "label": "Tipo de pregunta", "tipo": "select",
#|                   "opciones": ["opcion_multiple", "desarrollo", "verdadero_falso"]},
#|                  {"k": "enunciado", "label": "Pregunta", "tipo": "area", "alto": 80},
#|                  {"k": "opciones", "label": "Alternativas (una por línea, ej.: a) …)", "tipo": "lineas", "alto": 100},
#|                  {"k": "respuesta", "label": "Respuesta correcta", "tipo": "linea"},
#|                  {"k": "puntaje", "label": "Puntaje", "tipo": "linea"}]
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
#|     with st.expander("⚙️ Generar con IA", expanded=not doc):
#|         c1, c2, c3 = st.columns(3)
#|         n_preg = c1.number_input("Número de preguntas", 3, 20, 8, key=f"exa_n_{sdoc['id']}")
#|         tipos = c2.selectbox("Tipo de preguntas", ["Mixto", "Solo opción múltiple", "Solo desarrollo"], key=f"exa_t_{sdoc['id']}")
#|         total = c3.number_input("Puntaje total", 5, 100, 20, key=f"exa_p_{sdoc['id']}")
#|         if confirmar("examen", "✨ Generar examen con IA" if not doc else "🔄 Volver a generar el examen",
#|                      f"exa_{sdoc['id']}", asig=asig):
#|             try:
#|                 prompt = f"""{preambulo()}
#| Elabora un EXAMEN para estudiantes de {asig['grado']} ({asig['nivel']}), área {asig['area']}.
#| Sesión: {sd.get('titulo')}
#| Competencias y criterios:
#| {_resumen_competencias(sd)}
#| Número de preguntas: {int(n_preg)}. Tipo: {tipos}. Puntaje total: {int(total)} (los puntajes de las preguntas deben sumar exactamente {int(total)}).
#| Para "opcion_multiple": 4 opciones escritas como "a) ...", "b) ...", y "respuesta" con la letra correcta. Para "desarrollo": "opciones" vacía y "respuesta" con la respuesta esperada.
#| Formato: {{"titulo":"...","instrucciones":"...","preguntas":[{{"numero":1,"tipo":"opcion_multiple","enunciado":"...","opciones":["a) ...","b) ...","c) ...","d) ..."],"respuesta":"b","puntaje":2}}]}}"""
#|                 with st.spinner("Creando el examen..."):
#|                     ia, _ = pedir_json(prompt)
#|                 pregs = []
#|                 for i, p in enumerate((ia.get("preguntas") if isinstance(ia, dict) else []) or [], 1):
#|                     if isinstance(p, dict):
#|                         pregs.append({"numero": i, "tipo": s(p.get("tipo")) or "desarrollo", "enunciado": s(p.get("enunciado")),
#|                                       "opciones": a_lista(p.get("opciones")), "respuesta": s(p.get("respuesta")),
#|                                       "puntaje": s(p.get("puntaje")) or "1"})
#|                 if not pregs:
#|                     raise RuntimeError("La IA no devolvió preguntas. Intenta de nuevo.")
#|                 guardar_doc(uid, aid, "examen", 1, f"Examen: {sd.get('titulo')}",
#|                             {"titulo": s(ia.get("titulo")), "instrucciones": s(ia.get("instrucciones")), "preguntas": pregs},
#|                             padre_id=sdoc["id"], normativa=normativa_vigente()[1])
#|                 cobrar(uid, "examen")
#|                 siguiente_version(ver_key)
#|                 flash("Examen listo ✅")
#|                 st.rerun()
#|             except Exception as e:
#|                 st.error(f"No se pudo generar: {e}")
#|     if not doc:
#|         return
#|     vista_previa_y_descarga(doc["id"], f"exa_{sdoc['id']}")
#|     with st.expander("✏️ Editar el examen"):
#|         clave = f"exa_{sdoc['id']}_{ver}"
#|         campo_linea("Título del examen", f"{clave}_t", d.get("titulo", ""))
#|         campo_texto("Indicaciones", f"{clave}_i", d.get("instrucciones", ""), 80)
#|         items = d.get("preguntas", [])
#|         editor_items(clave, items, CAMPOS_EXAMEN, lambda i, x: f"Pregunta {i + 1}: {s(x.get('enunciado'))[:60]}")
#|         barra_edicion(clave, items, CAMPOS_EXAMEN,
#|                       lambda n: {"numero": n, "tipo": "desarrollo", "enunciado": "", "opciones": [], "respuesta": "", "puntaje": "1"},
#|                       lambda lista: guardar_doc(uid, aid, "examen", 1, doc["titulo"],
#|                                                 {"titulo": st.session_state.get(f"{clave}_t", ""),
#|                                                  "instrucciones": st.session_state.get(f"{clave}_i", ""),
#|                                                  "preguntas": lista}, padre_id=sdoc["id"]), ver_key)
#|
#|
#| # ------------------------------------------------------------------
#| # DESAFÍOS DE APRENDIZAJE (por clase o por unidad)
#| # ------------------------------------------------------------------
#| CAMPOS_DESAFIO = [{"k": "nombre", "label": "Nombre del desafío", "tipo": "linea"},
#|                   {"k": "nivel", "label": "Nivel", "tipo": "select", "opciones": ["Básico", "Intermedio", "Avanzado"]},
#|                   {"k": "puntos", "label": "Puntos", "tipo": "linea"},
#|                   {"k": "reto", "label": "El reto", "tipo": "area", "alto": 90},
#|                   {"k": "pasos", "label": "Pasos (uno por línea)", "tipo": "lineas", "alto": 90},
#|                   {"k": "producto", "label": "Producto que presentarán", "tipo": "linea"},
#|                   {"k": "criterios", "label": "Lo lograrás si… (uno por línea)", "tipo": "lineas", "alto": 80}]
#|
#|
#| def _contexto_desafio(padre, udata, ambito):
#|     d = contenido(padre)
#|     if ambito == "unidad":
#|         temas = "; ".join(f.get("titulo", "") for f in d.get("secuencia", []))
#|         comps = d.get("propositos", [])
#|         cab = f"UNIDAD: {d.get('titulo')}\nSituación significativa: {d.get('situacion')}\nTemas de la unidad: {temas}"
#|     else:
#|         sug = d.get("competencias_sugeridas") or []
#|         comps = [c for c in (d.get("competencias") or [])] or [p for p in udata.get("propositos", [])
#|                                                                 if not sug or p["competencia"] in sug]
#|         cab = f"TEMA (CLASE): {d.get('titulo')}\nPropósito: {d.get('proposito', '')}\nUnidad: {udata.get('titulo')}"
#|     des = "\n".join(f"- {c.get('competencia')}: " + " | ".join((c.get("desempenos") or [])[:3]) for c in comps)
#|     return cab + "\nDesempeños oficiales que se desarrollan:\n" + des
#|
#|
#| def _tab_desafios(asig, padre, udata, ambito):
#|     uid, aid = st.session_state.user_id, asig["id"]
#|     doc = get_doc(aid, "desafio", padre_id=padre["id"])
#|     d = contenido(doc) if doc else {}
#|     ver_key = f"ver_des_{padre['id']}"
#|     ver = st.session_state.get(ver_key, 0)
#|     st.caption("Retos motivadores para tus estudiantes, basados en el tema y en los desempeños oficiales. "
#|                "Incluyen pasos, producto, criterios de logro y una hoja de seguimiento.")
#|     with st.expander("⚙️ Generar con IA", expanded=not doc):
#|         c1, c2 = st.columns(2)
#|         n = c1.number_input("Número de desafíos", 3, 10, 5, key=f"des_n_{padre['id']}")
#|         modalidad = c2.selectbox("Modalidad", ["Mixto", "Individual", "En equipos"], key=f"des_m_{padre['id']}")
#|         if confirmar("desafio", "✨ Crear desafíos con IA" if not doc else "🔄 Volver a crear los desafíos",
#|                      f"des_{padre['id']}", asig=asig):
#|             try:
#|                 prompt = f"""{preambulo()}
#| Crea DESAFÍOS DE APRENDIZAJE para estudiantes de {asig['grado']} ({asig['nivel']}), área {asig['area']}, región {asig['region']}.
#| {_contexto_desafio(padre, udata, ambito)}
#| Número de desafíos: {int(n)}. Modalidad: {modalidad}.
#| Cada desafío es un reto motivador y contextualizado que hace que el estudiante use lo aprendido, con dificultad creciente (Básico, Intermedio, Avanzado).
#| Formato: {{"titulo":"...","introduccion":"mensaje motivador para los estudiantes","desafios":[{{"numero":1,"nombre":"...","reto":"...","pasos":["..."],"producto":"...","criterios":["..."],"nivel":"Básico","puntos":5}}]}}"""
#|                 with st.spinner("Creando los desafíos..."):
#|                     ia, _ = pedir_json(prompt)
#|                 lista = [x for x in (ia.get("desafios") if isinstance(ia, dict) else []) or [] if isinstance(x, dict)]
#|                 if not lista:
#|                     raise RuntimeError("La IA no devolvió desafíos. Intenta de nuevo.")
#|                 desafios = [{"numero": i, "nombre": s(x.get("nombre")), "reto": s(x.get("reto")), "pasos": a_lista(x.get("pasos")),
#|                              "producto": s(x.get("producto")), "criterios": a_lista(x.get("criterios")),
#|                              "nivel": s(x.get("nivel")), "puntos": s(x.get("puntos"))} for i, x in enumerate(lista, 1)]
#|                 guardar_doc(uid, aid, "desafio", 1, s(ia.get("titulo")) or f"Desafíos: {contenido(padre).get('titulo')}",
#|                             {"titulo": s(ia.get("titulo")), "introduccion": s(ia.get("introduccion")),
#|                              "modalidad": modalidad, "desafios": desafios}, padre_id=padre["id"],
#|                             normativa=normativa_vigente()[1])
#|                 cobrar(uid, "desafio")
#|                 siguiente_version(ver_key)
#|                 flash("¡Desafíos listos! Descárgalos en Word o edítalos.")
#|                 st.rerun()
#|             except Exception as e:
#|                 st.error(f"No se pudo generar: {e}")
#|     if not doc:
#|         return
#|     vista_previa_y_descarga(doc["id"], f"des_{padre['id']}")
#|     with st.expander("✏️ Editar los desafíos"):
#|         clave = f"des_{padre['id']}_{ver}"
#|         campo_linea("Título", f"{clave}_t", d.get("titulo", ""))
#|         campo_texto("Mensaje para los estudiantes", f"{clave}_i", d.get("introduccion", ""), 80)
#|         items = d.get("desafios", [])
#|         editor_items(clave, items, CAMPOS_DESAFIO, lambda i, x: f"Desafío {i + 1}: {s(x.get('nombre'))[:50]}")
#|         barra_edicion(clave, items, CAMPOS_DESAFIO,
#|                       lambda n: {"numero": n, "nombre": "", "reto": "", "pasos": [], "producto": "", "criterios": [],
#|                                  "nivel": "Básico", "puntos": "5"},
#|                       lambda lista: guardar_doc(uid, aid, "desafio", 1, st.session_state.get(f"{clave}_t", "") or doc["titulo"],
#|                                                 {**d, "titulo": st.session_state.get(f"{clave}_t", ""),
#|                                                  "introduccion": st.session_state.get(f"{clave}_i", ""),
#|                                                  "desafios": lista}, padre_id=padre["id"]), ver_key)
#@@ END
#@@ MODULE v_biblioteca
#| """Mi Biblioteca: todos tus documentos ordenados por área y grado."""
#| import streamlit as st
#|
#| from db import fetch
#| from exportar import bloques_de
#| from repo import borrar_doc, docs_del_usuario, get_doc_by_id, listar_asignaciones
#| from render import COLOR_DEFECTO, a_docx, texto_a_docx
#| from ui import MIME_DOCX, PAG_ANUAL, PAG_SESIONES, PAG_UNIDADES, abrir_area, descargar, flash
#|
#| TIPOS = {"anual": ("📅", "Planificación anual", PAG_ANUAL), "unidad": ("📚", "Unidad", PAG_UNIDADES),
#|          "sesion": ("📝", "Sesión", PAG_SESIONES), "rubrica": ("📊", "Rúbrica", PAG_SESIONES),
#|          "ficha": ("📄", "Ficha", PAG_SESIONES), "examen": ("📋", "Examen de sesión", PAG_SESIONES),
#|          "examen_unidad": ("🧪", "Examen de unidad", PAG_UNIDADES),
#|          "desafio": ("🏆", "Desafíos", PAG_SESIONES)}
#| ORDEN = {"anual": 0, "unidad": 1, "sesion": 2, "rubrica": 3, "ficha": 4, "examen": 5, "examen_unidad": 6, "desafio": 7}
#|
#|
#| def render():
#|     uid = st.session_state.user_id
#|     st.title("🗂️ Mi biblioteca")
#|     st.caption("Todos tus documentos, organizados por área y grado. Descárgalos en Word cuando los necesites.")
#|     asigs = listar_asignaciones(uid)
#|     if not asigs:
#|         st.info("Cuando crees documentos aparecerán aquí.")
#|     filtro = st.selectbox("Mostrar", ["Todos los documentos"] + list(TIPOS), key="bib_filtro",
#|                           format_func=lambda k: k if k.startswith("Todos") else f"{TIPOS[k][0]} {TIPOS[k][1]}")
#|     todos = docs_del_usuario(uid)
#|     for a in asigs:
#|         docs = [d for d in todos if d["asignacion_id"] == a["id"] and (filtro.startswith("Todos") or d["tipo"] == filtro)]
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
#|                     completo = get_doc_by_id(d["id"])
#|                     bloques, horizontal, archivo = bloques_de(completo)
#|                     st.session_state[kb] = (a_docx(bloques, d.get("color") or COLOR_DEFECTO, d.get("normativa_usada"),
#|                                                    horizontal), archivo)
#|                 if kb in st.session_state:
#|                     datos, archivo = st.session_state[kb]
#|                     descargar("⬇️ Descargar", datos, archivo, MIME_DOCX, f"dlb_{d['id']}")
#|                 c3.button("Abrir curso", key=f"op_{d['id']}", on_click=abrir_area, args=(a["id"], pagina))
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
#|                 descargar("⬇️ Word", texto_a_docx(d["titulo"], d["contenido_texto"], d["normativa_usada"]),
#|                           f"documento_{d['id']}.docx", MIME_DOCX, f"old_{d['id']}")
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
#| import time
#|
#| import requests
#|
#| import v_programas
#| from db import medir_latencia
#| from ia import (PROVEEDORES, clave_de, llamar_gemini, llamar_openrouter, modelo_de, origen_clave,
#|                 probar_proveedor, registros_recientes)
#| from programas import PORTALES
#| from ui import descargar, flash
#|
#| ROLES = ["docente", "director", "admin"]
#| TIPOS_NORMA = ["curricular", "pedagógico/normativo", "administrativo"]
#|
#|
#| def render(admin_id):
#|     st.title("⚙️ Administración")
#|     t = st.tabs(["📊 Resumen", "👥 Usuarios", "🏫 Colegios", "🎓 Currículo", "📜 Normativa MINEDU", "🎟️ Costos",
#|                  "🩺 Diagnóstico", "🤖 IA"])
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
#|     with t[6]:
#|         panel_diagnostico()
#|     with t[7]:
#|         panel_ia()
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
#|     exigir = st.checkbox("🔒 Bloquear la generación en las áreas cuyo currículo aún no esté verificado "
#|                          "(los docentes solo podrán generar cuando todas las competencias estén verificadas y tengan desempeños)",
#|                          value=config_get("exigir_verificado", "0") == "1", key="cur_exigir")
#|     if exigir != (config_get("exigir_verificado", "0") == "1"):
#|         config_set("exigir_verificado", "1" if exigir else "0")
#|         st.success("Configuración guardada.")
#|     t0, t_resto = st.tabs(["📥 Programas oficiales (PDF)", "✏️ Editar currículo"])
#|     with t0:
#|         v_programas.render()
#|     with t_resto:
#|         _panel_curriculo_editor()
#|
#|
#| def _panel_curriculo_editor():
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
#|         db_execute("DELETE FROM curriculo_desempenos WHERE competencia_id=%s AND grado=%s AND asignacion_id IS NULL", (cid, grado))
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
#|     descargar("⬇️ Descargar plantilla (CSV)", plantilla.to_csv(index=False).encode("utf-8-sig"),
#|               "plantilla_desempenos.csv", "text/csv", "cur_plantilla")
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
#|                     db_execute("DELETE FROM curriculo_desempenos WHERE competencia_id=%s AND grado=%s AND asignacion_id IS NULL", (cid, grado))
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
#| # IA: claves y modelos (se aplican al instante, sin reiniciar)
#| # ------------------------------------------------------------------
#| def _guardar_ia(prov):
#|     ss = st.session_state
#|     nueva = (ss.get(f"ia_k_{prov}") or "").strip()
#|     modelo = (ss.get(f"ia_m_{prov}") or "").strip()
#|     if nueva and (" " in nueva or len(nueva) > 250):
#|         flash("Esa clave no parece válida (tiene espacios o es demasiado larga). No se guardó nada.", "error")
#|         return
#|     if nueva:
#|         config_set(f"ia_{prov}_key", nueva)
#|     config_set(f"ia_{prov}_model", modelo)
#|     ss[f"ia_k_{prov}"] = ""  # se borra el campo para que la clave no quede en pantalla
#|     flash(f"{PROVEEDORES[prov]['nombre']}: guardado ✅ Ya lo usa todo el sistema. Pulsa «Probar» para comprobarlo.")
#|
#|
#| def _quitar_ia(prov):
#|     config_set(f"ia_{prov}_key", "")
#|     flash(f"Se quitó la clave del panel para {PROVEEDORES[prov]['nombre']}. "
#|           "Si hay una en Secrets, se usará esa.", "info")
#|
#|
#| def panel_ia():
#|     st.subheader("Proveedores de IA")
#|     st.caption("Orden automático: **OpenRouter** primero; si falla, **Gemini**. Las claves que guardes aquí tienen "
#|                "prioridad sobre las de Secrets. Nunca se muestran completas.")
#|     for prov, etiqueta in (("openrouter", "OpenRouter · principal"), ("gemini", "Gemini · respaldo")):
#|         with st.container(border=True):
#|             st.markdown(f"**{etiqueta}**")
#|             k, origen = clave_de(prov), origen_clave(prov)
#|             if not k:
#|                 st.error("Sin clave configurada.")
#|             else:
#|                 donde = "panel de Administración" if origen == "panel" else "Secrets de Streamlit"
#|                 st.success(f"Clave configurada (termina en …{k[-4:]}) · origen: {donde}")
#|             st.text_input("Pegar una clave nueva (déjalo vacío para no cambiarla)", type="password", key=f"ia_k_{prov}")
#|             st.text_input("Modelo", value=modelo_de(prov), key=f"ia_m_{prov}",
#|                           help="Ejemplos: openai/gpt-4o-mini en OpenRouter. En Gemini usa el nombre exacto que vea tu cuenta.")
#|             c1, c2, c3 = st.columns(3)
#|             c1.button("💾 Guardar", key=f"ia_g_{prov}", type="primary", on_click=_guardar_ia, args=(prov,),
#|                       use_container_width=True)
#|             if c2.button("🧪 Probar", key=f"ia_t_{prov}", use_container_width=True):
#|                 with st.spinner("Probando..."):
#|                     ok, msg, ms = probar_proveedor(prov)
#|                 (st.success if ok else st.error)(f"{'✅' if ok else '❌'} {msg} ({ms:.0f} ms)")
#|             c3.button("🗑️ Quitar del panel", key=f"ia_q_{prov}", on_click=_quitar_ia, args=(prov,),
#|                       use_container_width=True, disabled=origen != "panel")
#|     st.markdown("#### Últimos intentos (sin claves)")
#|     reg = registros_recientes(20)
#|     if reg:
#|         st.dataframe(pd.DataFrame(reg), hide_index=True)
#|     else:
#|         st.caption("Todavía no hay registros.")
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
#|
#|
#| # ------------------------------------------------------------------
#| def panel_diagnostico():
#|     st.subheader("Diagnóstico del sistema")
#|     st.caption("Comprueba en un clic la velocidad de la base de datos, las claves de IA, las tablas y el acceso al MINEDU.")
#|     if not st.button("▶️ Ejecutar pruebas", type="primary", key="diag_run"):
#|         return
#|     filas = []
#|
#|     def probar(nombre, fn):
#|         t0 = time.time()
#|         try:
#|             estado, detalle = fn()
#|         except Exception as e:
#|             estado, detalle = "❌", f"{type(e).__name__}: {e}"
#|         filas.append((estado, nombre, detalle, f"{(time.time() - t0) * 1000:.0f} ms"))
#|
#|     def _bd():
#|         ms = medir_latencia(5)
#|         if ms < 120:
#|             return "✅", f"{ms:.0f} ms por consulta: buena velocidad."
#|         return "⚠️", (f"{ms:.0f} ms por consulta: es lento. Tu base de Aiven probablemente está lejos de Streamlit Cloud; "
#|                      "crea el servicio de Aiven en una región de EE. UU. (la misma zona de Google Cloud) para ganar velocidad.")
#|
#|     def _tablas():
#|         existentes = {f["TABLE_NAME"] if "TABLE_NAME" in f else list(f.values())[0]
#|                       for f in db_fetch("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()")}
#|         necesarias = {"usuarios", "asignaciones", "documentos", "curriculo_competencias", "curriculo_desempenos",
#|                       "eventos", "config", "normativa_versiones"}
#|         faltan = necesarias - {x.lower() for x in existentes}
#|         return ("✅", "Todas las tablas existen.") if not faltan else ("❌", "Faltan tablas: " + ", ".join(sorted(faltan)))
#|
#|     def _secrets():
#|         faltan = [PROVEEDORES[p]["nombre"] for p in ("openrouter", "gemini") if not clave_de(p)]
#|         for x in ("mysql", "admin"):
#|             if x not in st.secrets:
#|                 faltan.append(f"Secrets [{x}]")
#|         return ("✅", "Claves y Secrets completos.") if not faltan else ("⚠️", "Falta configurar: " + ", ".join(faltan))
#|
#|     def _or():
#|         if not clave_de("openrouter"):
#|             return "⚠️", "No hay clave de OpenRouter (panel IA o Secrets)."
#|         return "✅", "Respondió: " + llamar_openrouter("Responde solo con la palabra: ok")[:40]
#|
#|     def _gem():
#|         if not clave_de("gemini"):
#|             return "⚠️", "No hay clave de Gemini (panel IA o Secrets)."
#|         return "✅", "Respondió: " + llamar_gemini("Responde solo con la palabra: ok")[:40]
#|
#|     def _minedu():
#|         r = requests.get(PORTALES[0], timeout=25, headers={"User-Agent": "Mozilla/5.0"})
#|         return ("✅", f"gob.pe respondió ({r.status_code}).") if r.status_code < 400 else ("⚠️", f"gob.pe respondió {r.status_code}.")
#|
#|     def _libs():
#|         import docx, pypdf  # noqa: F401
#|         return "✅", "python-docx y pypdf instalados."
#|
#|     probar("Velocidad de la base de datos", _bd)
#|     probar("Tablas de la base de datos", _tablas)
#|     probar("Secrets (claves)", _secrets)
#|     probar("IA principal: OpenRouter", _or)
#|     probar("IA de respaldo: Gemini", _gem)
#|     probar("Acceso a gob.pe (MINEDU)", _minedu)
#|     probar("Librerías de Word y PDF", _libs)
#|     for estado, nombre, detalle, tiempo in filas:
#|         st.markdown(f"{estado} **{nombre}** · {tiempo}  \n{detalle}")
#@@ END
