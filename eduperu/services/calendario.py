"""Calendario docente: eventos, programación automática de clases y sugerencias con IA."""
import calendar
import datetime as dt
import re

from eduperu.core.db import execute, fetch
from eduperu.core.ia import pedir_json, preambulo
from eduperu.core.repo import contenido, get_doc, listar_docs
from eduperu.core.util import s

TIPOS = {"clase": ("📖", "Clase"), "examen": ("📝", "Examen"), "actividad": ("🎯", "Actividad"),
         "reunion": ("👥", "Reunión"), "otro": ("📌", "Otro")}
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Setiembre", "Octubre",
         "Noviembre", "Diciembre"]
AUTO = "[auto]"


def eventos_mes(uid, año, mes, aid=None):
    ini = dt.date(año, mes, 1)
    fin = dt.date(año, mes, calendar.monthrange(año, mes)[1])
    sql = "SELECT * FROM eventos WHERE usuario_id=%s AND fecha>=%s AND fecha<=%s"
    params = [uid, ini, fin]
    if aid:
        sql += " AND (asignacion_id=%s OR asignacion_id IS NULL)"
        params.append(aid)
    return fetch(sql + " ORDER BY fecha, id", tuple(params))


def agregar(uid, aid, fecha, tipo, titulo, detalle="", doc_id=None):
    nuevo, _ = execute("INSERT INTO eventos (usuario_id, asignacion_id, fecha, tipo, titulo, detalle, doc_id) "
                       "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                       (uid, aid, fecha, tipo if tipo in TIPOS else "otro", titulo[:255], detalle, doc_id))
    return nuevo


def borrar(evento_id, uid):
    execute("DELETE FROM eventos WHERE id=%s AND usuario_id=%s", (evento_id, uid))


def parsear_fechas(texto):
    """Lee fechas dd/mm/aaaa separadas por comas, espacios o saltos de línea. Devuelve (set de fechas, inválidas)."""
    validas, invalidas = set(), []
    for trozo in re.split(r"[,\n;]+", texto or ""):
        trozo = trozo.strip()
        if not trozo:
            continue
        try:
            validas.add(dt.datetime.strptime(trozo, "%d/%m/%Y").date())
        except ValueError:
            invalidas.append(trozo)
    return validas, invalidas


def programar_clases(uid, asig, inicio, dias_semana, sin_clase=frozenset(), con_examen=True):
    """Reparte las clases del sílabo (y un examen al final de cada unidad) en las fechas elegidas.
    Reemplaza lo que se programó antes automáticamente para este curso. Devuelve cuántos eventos creó."""
    if not dias_semana:
        raise ValueError("Elige al menos un día de clase.")
    aid = asig["id"]
    anual = get_doc(aid, "anual")
    unidades = (contenido(anual).get("unidades") if anual else None) or []
    if not unidades:
        raise ValueError("Primero crea tu sílabo anual.")
    execute("DELETE FROM eventos WHERE usuario_id=%s AND asignacion_id=%s AND detalle LIKE %s", (uid, aid, AUTO + "%"))

    fecha = [inicio]

    def siguiente():
        for _ in range(800):
            d = fecha[0]
            fecha[0] = d + dt.timedelta(days=1)
            if d.weekday() in dias_semana and d not in sin_clase:
                return d
        raise ValueError("No hay fechas disponibles con esos días.")

    creados = 0
    for ua in unidades:
        udoc = get_doc(aid, "unidad", numero=ua["numero"])
        sesiones = listar_docs(aid, "sesion", padre_id=udoc["id"]) if udoc else []
        if sesiones:
            clases = [(contenido(x).get("titulo") or x["titulo"], x["id"]) for x in sesiones]
        else:
            clases = [(t["titulo"], None) for t in ua.get("temas") or []]
        for i, (titulo, doc_id) in enumerate(clases, 1):
            agregar(uid, aid, siguiente(), "clase", f"U{ua['numero']} · Clase {i}: {titulo}", AUTO, doc_id)
            creados += 1
        if con_examen and clases:
            agregar(uid, aid, siguiente(), "examen", f"Examen de la Unidad {ua['numero']}: {ua['titulo']}", AUTO)
            creados += 1
    return creados


def sugerir_con_ia(asig, año, mes):
    """La IA propone actividades pedagógicas del mes (no inventa feriados ni fechas oficiales)."""
    ultimo = calendar.monthrange(año, mes)[1]
    datos, _ = pedir_json(f"""{preambulo()}
Propón entre 5 y 8 actividades pedagógicas para el mes de {MESES[mes]} de {año} de un docente de {asig['area']} ({asig['grado']}, {asig['nivel']}):
evaluaciones, retroalimentación, proyectos, ferias, reuniones con familias, etc.
NO inventes feriados, vacaciones ni fechas oficiales del Ministerio. Usa solo días de lunes a viernes del mes (del 1 al {ultimo}).
Formato: {{"eventos":[{{"fecha":"{año}-{mes:02d}-10","tipo":"actividad","titulo":"...","detalle":"..."}}]}}
Tipos permitidos: actividad, examen, reunion.""")
    res = []
    for x in (datos.get("eventos") if isinstance(datos, dict) else datos) or []:
        try:
            f = dt.datetime.strptime(s(x.get("fecha")), "%Y-%m-%d").date()
        except (ValueError, AttributeError):
            continue
        if f.year == año and f.month == mes and s(x.get("titulo")):
            res.append({"fecha": f, "tipo": x.get("tipo") if x.get("tipo") in TIPOS else "actividad",
                        "titulo": s(x.get("titulo")), "detalle": s(x.get("detalle"))})
    return res


def a_ics(eventos):
    """Archivo .ics para importar a Google Calendar u Outlook."""
    esc = lambda t: s(t).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    lineas = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//EduPeru IA//ES"]
    for e in eventos:
        f = e["fecha"]
        lineas += ["BEGIN:VEVENT", f"UID:eduperu-{e['id']}@eduperu", f"DTSTART;VALUE=DATE:{f:%Y%m%d}",
                   f"SUMMARY:{esc(e['titulo'])}", f"DESCRIPTION:{esc((e.get('detalle') or '').replace(AUTO, '').strip())}",
                   "END:VEVENT"]
    lineas.append("END:VCALENDAR")
    return ("\r\n".join(lineas) + "\r\n").encode("utf-8")
