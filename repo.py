"""Acceso a datos: usuarios, créditos, asignaciones (áreas del docente) y documentos."""
import json
from db import fetch, execute

ORDEN_NIVEL = {"Inicial": 0, "Primaria": 1, "Secundaria": 2}

COSTOS_DEFAULT = {"caracterizacion": 0, "anual": 2, "unidad": 2, "sesion": 1,
                  "rubrica": 1, "ficha": 1, "examen": 1, "importar": 1, "revision": 1}
NOMBRES_COSTO = {
    "caracterizacion": "Boceto de caracterización del estudiante",
    "anual": "Situaciones significativas (planificación anual)",
    "unidad": "Unidad de aprendizaje",
    "sesion": "Sesión de aprendizaje",
    "rubrica": "Rúbrica de evaluación",
    "ficha": "Ficha de trabajo",
    "examen": "Examen",
    "importar": "Importar unidad desde Word",
    "revision": "Revisión de coherencia",
}


# ------------------------------------------------------------------
# Configuración y créditos
# ------------------------------------------------------------------
def config_get(clave, defecto=None):
    f = fetch("SELECT valor FROM config WHERE clave=%s", (clave,), one=True)
    return f["valor"] if f else defecto


def config_set(clave, valor):
    if fetch("SELECT clave FROM config WHERE clave=%s", (clave,), one=True):
        execute("UPDATE config SET valor=%s WHERE clave=%s", (str(valor), clave))
    else:
        execute("INSERT INTO config (clave, valor) VALUES (%s, %s)", (clave, str(valor)))


def costo_de(accion):
    v = config_get(f"costo_{accion}")
    try:
        return int(v) if v is not None else COSTOS_DEFAULT.get(accion, 1)
    except ValueError:
        return COSTOS_DEFAULT.get(accion, 1)


def get_usuario(uid):
    return fetch("SELECT id, nombre, correo, rol, creditos, activo, colegio, colegio_id, nivel_educativo "
                 "FROM usuarios WHERE id=%s", (uid,), one=True)


def cobrar(uid, accion, veces=1):
    """Descuenta créditos (el administrador no paga). Se llama DESPUÉS de que la IA respondió bien."""
    u = get_usuario(uid)
    if not u or u["rol"] == "admin":
        return
    costo = costo_de(accion) * veces
    if costo > 0:
        execute("UPDATE usuarios SET creditos = creditos - %s WHERE id=%s AND creditos >= %s", (costo, uid, costo))


def mapa_colegios(solo_activos=True):
    sql = "SELECT id, nombre FROM colegios" + (" WHERE activo=1" if solo_activos else "") + " ORDER BY nombre"
    mapa = {0: "— Docente independiente / sin colegio —"}
    mapa.update({c["id"]: c["nombre"] for c in fetch(sql)})
    return mapa


# ------------------------------------------------------------------
# Asignaciones (áreas del docente)
# ------------------------------------------------------------------
def listar_asignaciones(uid):
    filas = fetch("SELECT * FROM asignaciones WHERE usuario_id=%s", (uid,))
    return sorted(filas, key=lambda a: (ORDEN_NIVEL.get(a["nivel"], 9), a["grado"], a["area"], a["seccion"] or ""))


def get_asignacion(aid):
    return fetch("SELECT * FROM asignaciones WHERE id=%s", (aid,), one=True)


def crear_asignacion(uid, d):
    nuevo, _ = execute(
        "INSERT INTO asignaciones (usuario_id, ciclo_escolar, institucion, director, docente, region, nivel, grado, area, seccion) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (uid, d["ciclo_escolar"], d["institucion"], d["director"], d["docente"], d["region"],
         d["nivel"], d["grado"], d["area"], d["seccion"]))
    return nuevo


CAMPOS_ASIG = {"institucion", "director", "docente", "region", "seccion", "caracterizacion", "ciclo_escolar"}


def actualizar_asignacion(aid, **campos):
    campos = {k: v for k, v in campos.items() if k in CAMPOS_ASIG}
    if not campos:
        return
    sets = ", ".join(f"{k}=%s" for k in campos)
    execute(f"UPDATE asignaciones SET {sets} WHERE id=%s", tuple(campos.values()) + (aid,))


def borrar_asignacion(aid):
    execute("DELETE FROM documentos WHERE asignacion_id=%s", (aid,))
    execute("DELETE FROM asignaciones WHERE id=%s", (aid,))


def resumen_asignacion(aid):
    filas = fetch("SELECT tipo, COUNT(*) AS n FROM documentos WHERE asignacion_id=%s GROUP BY tipo", (aid,))
    return {f["tipo"]: f["n"] for f in filas}


# ------------------------------------------------------------------
# Documentos
# ------------------------------------------------------------------
def contenido(doc):
    if not doc or not doc.get("contenido"):
        return {}
    try:
        return json.loads(doc["contenido"])
    except (TypeError, ValueError):
        return {}


def get_doc_by_id(did):
    if not did:
        return None
    return fetch("SELECT * FROM documentos WHERE id=%s", (did,), one=True)


def get_doc(aid, tipo, numero=None, padre_id=None):
    sql = "SELECT * FROM documentos WHERE asignacion_id=%s AND tipo=%s"
    params = [aid, tipo]
    if numero is not None:
        sql += " AND numero=%s"
        params.append(numero)
    if padre_id is not None:
        sql += " AND padre_id=%s"
        params.append(padre_id)
    sql += " ORDER BY id DESC LIMIT 1"
    return fetch(sql, tuple(params), one=True)


def listar_docs(aid, tipo=None, padre_id=None):
    sql = "SELECT * FROM documentos WHERE asignacion_id=%s"
    params = [aid]
    if tipo:
        sql += " AND tipo=%s"
        params.append(tipo)
    if padre_id is not None:
        sql += " AND padre_id=%s"
        params.append(padre_id)
    sql += " ORDER BY numero, id"
    return fetch(sql, tuple(params))


def guardar_doc(uid, aid, tipo, numero, titulo, data, padre_id=None, color=None, normativa=None):
    """Crea o actualiza un documento. Devuelve su id."""
    clave_num = numero if tipo in ("unidad", "sesion") else None
    clave_pad = padre_id if tipo in ("sesion", "rubrica", "ficha", "examen") else None
    existente = get_doc(aid, tipo, clave_num, clave_pad)
    texto = json.dumps(data, ensure_ascii=False)
    titulo = (titulo or "")[:255]
    if existente:
        sets, params = ["titulo=%s", "contenido=%s", "numero=%s"], [titulo, texto, numero]
        if color:
            sets.append("color=%s")
            params.append(color)
        if normativa:
            sets.append("normativa_usada=%s")
            params.append(normativa[:255])
        if padre_id is not None:
            sets.append("padre_id=%s")
            params.append(padre_id)
        execute(f"UPDATE documentos SET {', '.join(sets)} WHERE id=%s", tuple(params) + (existente["id"],))
        return existente["id"]
    nuevo, _ = execute(
        "INSERT INTO documentos (usuario_id, asignacion_id, tipo, padre_id, numero, titulo, contenido, color, normativa_usada) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (uid, aid, tipo, padre_id, numero, titulo, texto, color or "1F3B8F", (normativa or "")[:255]))
    return nuevo


def cambiar_color(did, color):
    execute("UPDATE documentos SET color=%s WHERE id=%s", (color, did))


def borrar_doc(did):
    """Borra un documento y todo lo que depende de él."""
    for hijo in fetch("SELECT id FROM documentos WHERE padre_id=%s", (did,)):
        borrar_doc(hijo["id"])
    execute("DELETE FROM documentos WHERE id=%s", (did,))


def crear_sesiones_desde_secuencia(uid, asig, udoc):
    """Crea una sesión vacía por cada fila de la secuencia de la unidad. Devuelve cuántas creó."""
    d = contenido(udoc)
    creadas = 0
    for i, fila in enumerate(d.get("secuencia", []), 1):
        titulo = fila.get("titulo") or f"Sesión {i}"
        if get_doc(asig["id"], "sesion", numero=i, padre_id=udoc["id"]):
            continue
        guardar_doc(uid, asig["id"], "sesion", i, f"Sesión {i}: {titulo}",
                    {"numero": i, "titulo": titulo, "unidad_numero": udoc["numero"], "semana": fila.get("semana"),
                     "competencias_sugeridas": [fila["competencia"]] if fila.get("competencia") else []},
                    padre_id=udoc["id"])
        creadas += 1
    return creadas
