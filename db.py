"""Conexión a MySQL (Aiven) y creación / actualización automática del esquema."""
import streamlit as st
import mysql.connector
from mysql.connector import pooling


def _cfg():
    s = st.secrets["mysql"]
    return dict(
        host=s["host"], port=int(s["port"]), database=s["database"],
        user=s["user"], password=s["password"],
        ssl_disabled=False, connection_timeout=10,
    )


@st.cache_resource(show_spinner=False)
def _pool():
    return pooling.MySQLConnectionPool(pool_name="eduperu_pool", pool_size=5, pool_reset_session=True, **_cfg())


def conexion():
    """Conexión reutilizable (pool). Si el pool falla, abre una conexión directa."""
    try:
        conn = _pool().get_connection()
        conn.ping(reconnect=True, attempts=2, delay=1)
        return conn
    except Exception:
        return mysql.connector.connect(**_cfg())


def fetch(sql, params=(), one=False):
    conn = conexion()
    try:
        cur = conn.cursor(dictionary=True, buffered=True)
        cur.execute(sql, params)
        filas = cur.fetchone() if one else cur.fetchall()
        cur.close()
        return filas
    finally:
        conn.close()


def execute(sql, params=()):
    """Ejecuta INSERT/UPDATE/DELETE. Devuelve (último id, filas afectadas)."""
    conn = conexion()
    try:
        cur = conn.cursor(buffered=True)
        cur.execute(sql, params)
        conn.commit()
        res = (cur.lastrowid, cur.rowcount)
        cur.close()
        return res
    finally:
        conn.close()


def execute_many(sql, filas):
    if not filas:
        return
    conn = conexion()
    try:
        cur = conn.cursor(buffered=True)
        cur.executemany(sql, filas)
        conn.commit()
        cur.close()
    finally:
        conn.close()


def _asegurar_columna(cur, tabla, columna, ddl):
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (tabla, columna),
    )
    if cur.fetchone()[0] == 0:
        cur.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {ddl}")


def _asegurar_admin(conn):
    """Crea (o promueve) al administrador definido en Secrets [admin]."""
    if "admin" not in st.secrets:
        return
    from auth import hash_password, verify_password
    adm = st.secrets["admin"]
    correo = str(adm.get("correo", "")).strip().lower()
    pw = str(adm.get("password", ""))
    nombre = str(adm.get("nombre", "Administrador"))
    if not correo or not pw:
        return
    cur = conn.cursor(dictionary=True, buffered=True)
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


FUENTES_INICIALES = [
    ("Normas y resoluciones del MINEDU", "https://www.gob.pe/institucion/minedu/normas-legales", "pedagógico/normativo"),
    ("Currículo Nacional (CNEB)", "https://www.gob.pe/institucion/minedu/campa%C3%B1as/106784-curriculo-nacional-de-la-educacion-basica", "curricular"),
    ("Programas curriculares EBR", "https://www.gob.pe/es/90158-ministerio-de-educacion-programas-curriculares-de-la-educacion-basica-regular", "curricular"),
    ("Norma Técnica Año Escolar 2026 (RM 501-2025-MINEDU)", "https://www.gob.pe/institucion/minedu/normas-legales/7380466-501-2025-minedu", "administrativo"),
]

TABLAS = [
    """CREATE TABLE IF NOT EXISTS usuarios (
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
    )""",
    """CREATE TABLE IF NOT EXISTS planificaciones (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario_id INT,
        tipo_documento VARCHAR(50),
        titulo VARCHAR(255) NOT NULL,
        contenido_texto LONGTEXT NOT NULL,
        normativa_usada VARCHAR(255) DEFAULT 'RM N.° 501-2025-MINEDU',
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS colegios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nombre VARCHAR(150) NOT NULL,
        codigo_modular VARCHAR(20),
        region VARCHAR(50) DEFAULT 'Lima',
        ugel VARCHAR(80),
        activo TINYINT(1) DEFAULT 1,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS normativa_fuentes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nombre VARCHAR(200) NOT NULL,
        url VARCHAR(600) NOT NULL,
        tipo VARCHAR(40) DEFAULT 'pedagógico/normativo',
        activa TINYINT(1) DEFAULT 1,
        ultima_revision DATETIME NULL
    )""",
    """CREATE TABLE IF NOT EXISTS normativa_versiones (
        id INT AUTO_INCREMENT PRIMARY KEY,
        fuente_id INT NOT NULL,
        hash_contenido VARCHAR(64) NOT NULL,
        contenido LONGTEXT,
        resumen_cambios LONGTEXT,
        estado VARCHAR(20) DEFAULT 'pendiente',
        detectado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
        aprobado_por INT NULL,
        aprobado_en DATETIME NULL
    )""",
    """CREATE TABLE IF NOT EXISTS asignaciones (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario_id INT NOT NULL,
        ciclo_escolar INT DEFAULT 2026,
        institucion VARCHAR(150),
        director VARCHAR(120),
        docente VARCHAR(120),
        region VARCHAR(50) DEFAULT 'Lima',
        nivel VARCHAR(20) NOT NULL,
        grado VARCHAR(20) NOT NULL,
        area VARCHAR(80) NOT NULL,
        seccion VARCHAR(20),
        caracterizacion LONGTEXT,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_asig_usuario (usuario_id)
    )""",
    """CREATE TABLE IF NOT EXISTS documentos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario_id INT NOT NULL,
        asignacion_id INT NOT NULL,
        tipo VARCHAR(20) NOT NULL,
        padre_id INT NULL,
        numero INT DEFAULT 1,
        titulo VARCHAR(255),
        contenido LONGTEXT,
        color VARCHAR(7) DEFAULT '1F3B8F',
        normativa_usada VARCHAR(255),
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_doc_asig_tipo (asignacion_id, tipo)
    )""",
    """CREATE TABLE IF NOT EXISTS curriculo_competencias (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nivel VARCHAR(20) NOT NULL,
        area VARCHAR(80) NOT NULL,
        nombre VARCHAR(500) NOT NULL,
        orden INT DEFAULT 0,
        verificado TINYINT(1) DEFAULT 0,
        INDEX idx_comp_nivel_area (nivel, area)
    )""",
    """CREATE TABLE IF NOT EXISTS curriculo_capacidades (
        id INT AUTO_INCREMENT PRIMARY KEY,
        competencia_id INT NOT NULL,
        nombre VARCHAR(500) NOT NULL,
        orden INT DEFAULT 0,
        INDEX idx_cap_comp (competencia_id)
    )""",
    """CREATE TABLE IF NOT EXISTS curriculo_desempenos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        competencia_id INT NOT NULL,
        grado VARCHAR(20) NOT NULL,
        texto TEXT NOT NULL,
        orden INT DEFAULT 0,
        INDEX idx_des_comp_grado (competencia_id, grado)
    )""",
    """CREATE TABLE IF NOT EXISTS curriculo_transversal (
        id INT AUTO_INCREMENT PRIMARY KEY,
        tipo VARCHAR(20) NOT NULL,
        nombre VARCHAR(300) NOT NULL,
        detalle TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS config (
        clave VARCHAR(60) PRIMARY KEY,
        valor VARCHAR(255)
    )""",
]


@st.cache_resource(show_spinner=False)
def init_db():
    conn = conexion()
    try:
        cur = conn.cursor(buffered=True)
        for ddl in TABLAS:
            cur.execute(ddl)

        # Columnas que pueden faltar si las tablas se crearon con versiones anteriores
        for col, ddl in [("nombre", "VARCHAR(100)"), ("correo", "VARCHAR(100)"), ("password_hash", "VARCHAR(255)"),
                         ("region", "VARCHAR(50) DEFAULT 'Lima'"), ("colegio", "VARCHAR(100)"),
                         ("nivel_educativo", "VARCHAR(30)"), ("rol", "VARCHAR(30) DEFAULT 'docente'"),
                         ("creditos", "INT DEFAULT 50"), ("creado_en", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                         ("colegio_id", "INT NULL"), ("activo", "TINYINT(1) DEFAULT 1")]:
            _asegurar_columna(cur, "usuarios", col, ddl)
        for col, ddl in [("usuario_id", "INT"), ("tipo_documento", "VARCHAR(50)"), ("titulo", "VARCHAR(255)"),
                         ("contenido_texto", "LONGTEXT"),
                         ("normativa_usada", "VARCHAR(255) DEFAULT 'RM N.° 501-2025-MINEDU'"),
                         ("creado_en", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")]:
            _asegurar_columna(cur, "planificaciones", col, ddl)
        cur.execute("ALTER TABLE planificaciones MODIFY normativa_usada VARCHAR(255) DEFAULT 'RM N.° 501-2025-MINEDU'")

        cur.execute("SELECT COUNT(*) FROM normativa_fuentes")
        if cur.fetchone()[0] == 0:
            for nombre, url, tipo in FUENTES_INICIALES:
                cur.execute("INSERT INTO normativa_fuentes (nombre, url, tipo) VALUES (%s, %s, %s)", (nombre, url, tipo))
        conn.commit()
        cur.close()

        from curriculo import sembrar_curriculo
        sembrar_curriculo(conn)
        _asegurar_admin(conn)
    finally:
        conn.close()
    return True
