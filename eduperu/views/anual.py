"""Sílabo anual: datos, lineamientos del Estado, caracterización, competencias, unidades y temas (clases)."""
import streamlit as st

from eduperu.services.curriculo import buscar_competencia, ciclo_de, competencias_de, contexto_curricular, estado_area
from eduperu.core.ia import generar_texto, pedir_json, preambulo
from eduperu.services.lineamientos import desde_archivo, traer_oficial, usar_oficial
from eduperu.core.normativa import normativa_vigente
from eduperu.core.repo import actualizar_asignacion, cobrar, contenido, get_doc, guardar_doc
from eduperu.ui.components import (MIME_DOCX, PAG_TEMAS, campo_linea, descargar, campo_multi, campo_num, campo_texto, confirmar, exigir_area, flash, ir_a,
                siguiente_version, vista_previa_y_descarga)
from eduperu.core.util import a_lista, entero, norm, s


def _generar_caracterizacion(asig, notas):
    prompt = f"""{preambulo()}
Redacta un BOCETO de caracterización y contexto de los estudiantes (2 párrafos, máximo 150 palabras).
Datos: nivel {asig['nivel']}, grado {asig['grado']}, área {asig['area']}, región {asig['region']}, institución {asig['institucion'] or 'no indicada'}.
Notas del docente: {notas or 'ninguna'}.
Incluye: rasgos de desarrollo propios de la edad, intereses, contexto sociocultural probable de la región y necesidades de aprendizaje frecuentes.
No inventes cifras ni datos personales. Tono general; el docente lo ajustará. Devuelve solo el texto."""
    texto, _ = generar_texto(prompt)
    return s(texto)


def _normalizar_temas(lista, mapa, comp_unidad):
    temas = []
    for x in lista or []:
        if isinstance(x, str):
            x = {"titulo": x}
        if not isinstance(x, dict) or not s(x.get("titulo")):
            continue
        nombre = buscar_competencia(x.get("competencia"), mapa) or comp_unidad
        info = mapa.get(nombre)
        n = entero(x.get("desempeno"), 0)
        texto = info["des"][n - 1]["texto"] if info and 1 <= n <= len(info["des"]) else ""
        temas.append({"titulo": s(x.get("titulo")), "competencia": nombre, "desempeno_texto": texto})
    return temas


def _generar_unidades(asig, comps_sel, n, spw):
    nombres = [c["nombre"] for c in comps_sel]
    ctx, mapa = contexto_curricular(asig["nivel"], asig["area"], asig["grado"], nombres, asig["id"])
    prompt = f"""{preambulo()}
Elabora el SÍLABO ANUAL {asig['ciclo_escolar']} con {n} unidades de aprendizaje y los temas (clases) de cada una.
Datos: nivel {asig['nivel']}, grado {asig['grado']}, área {asig['area']}, región {asig['region']}, institución {asig['institucion'] or 'no indicada'}.
Caracterización de los estudiantes: {asig.get('caracterizacion') or 'no especificada'}

Lineamientos oficiales del curso (usa SOLO estos nombres de competencia, EXACTOS; D1, D2... son desempeños oficiales por competencia y NO se reescriben):
{ctx}

Para cada unidad entrega:
- "titulo": título corto y motivador.
- "problema": problema identificado del contexto (1 a 2 oraciones).
- "situacion": situación significativa contextualizada a {asig['region']} (4 a 6 oraciones) con un reto y preguntas retadoras.
- "valores": valores observables (2 a 3, separados por coma) de los enfoques transversales del CNEB.
- "competencias": 1 a 3 nombres EXACTOS de la lista. Entre todas las unidades deben cubrirse todas las competencias.
- "semanas": número entre 3 y 5.
- "temas": lista de clases de la unidad, EXACTAMENTE semanas × {spw} temas. Cada tema: {{"titulo": "tema concreto de la clase", "competencia": nombre EXACTO, "desempeno": número del D que desarrolla}}.
Los temas deben avanzar de lo simple a lo complejo y cubrir los desempeños de las competencias de la unidad.

Formato: {{"unidades":[{{"numero":1,"titulo":"...","problema":"...","situacion":"...","valores":"...","competencias":["..."],"semanas":4,"temas":[{{"titulo":"...","competencia":"...","desempeno":1}}]}}]}}"""
    datos, _ = pedir_json(prompt)
    lista = datos.get("unidades") if isinstance(datos, dict) else datos
    if not isinstance(lista, list) or not lista:
        raise RuntimeError("La IA no devolvió unidades. Intenta de nuevo.")
    por_nombre = {norm(c["nombre"]): c for c in comps_sel}
    unidades = []
    for i in range(1, n + 1):
        u = lista[i - 1] if i - 1 < len(lista) and isinstance(lista[i - 1], dict) else {}
        elegidas = []
        for x in u.get("competencias") or []:
            c = por_nombre.get(norm(x))
            if c and c["nombre"] not in elegidas:
                elegidas.append(c["nombre"])
        if not elegidas:
            elegidas = [comps_sel[(i - 1) % len(comps_sel)]["nombre"]]
        caps = [cap for c in comps_sel if c["nombre"] in elegidas for cap in c["capacidades"]]
        unidades.append({"numero": i, "titulo": s(u.get("titulo")) or f"Unidad {i}", "problema": s(u.get("problema")),
                         "situacion": s(u.get("situacion")), "valores": s(u.get("valores")),
                         "competencias": elegidas, "capacidades": caps, "semanas": entero(u.get("semanas"), 4, 1, 12),
                         "temas": _normalizar_temas(u.get("temas"), mapa, elegidas[0])})
    return unidades


def _vacia(i, comps_sel):
    c = comps_sel[(i - 1) % len(comps_sel)]
    return {"numero": i, "titulo": f"Unidad {i}", "problema": "", "situacion": "", "valores": "",
            "competencias": [c["nombre"]], "capacidades": list(c["capacidades"]), "semanas": 4, "temas": []}


# ------------------------------------------------------------------
def _paso_lineamientos(asig, ver_key):
    aid, uid = asig["id"], st.session_state.user_id
    propio = asig.get("lineamientos_fuente") or ""
    n_comp, n_ver, n_des = estado_area(asig["nivel"], asig["area"], asig["grado"], aid)
    st.caption("Son los textos oficiales del Estado; la IA no los inventa.")
    if propio:
        st.success(f"📌 Usas lineamientos propios: {propio}")
        if st.button("↩️ Volver a los del sistema", key=f"lin_oficial_{aid}"):
            usar_oficial(asig)
            flash("Listo: el curso usa los lineamientos del sistema.")
            st.rerun()
    elif n_ver == n_comp and n_des == n_comp:
        st.success("✅ Todo listo: no necesitas hacer nada aquí.")
    else:
        st.warning(f"⚠️ Faltan desempeños en este curso ({n_des} de {n_comp} competencias). "
                   "Elige abajo cómo completarlos.")

    opcion = st.radio("¿Cómo los obtenemos?", ["📘 Usar los del sistema", "🔎 Buscar en el MINEDU",
                                               "📤 Subir mi archivo"],
                      key=f"lin_op2_{aid}", horizontal=True)
    if opcion.startswith("🔎"):
        st.caption("Busca en los PDF oficiales del MINEDU y verifica cada texto. Puede tardar unos minutos la primera vez.")
        if confirmar("lineamientos", "Buscar en el MINEDU", f"lin_traer_{aid}"):
            barra = st.progress(0.0)
            try:
                res = traer_oficial(asig, lambda f, t: barra.progress(min(f, 1.0), text=t))
                cobrar(uid, "lineamientos")
                flash(f"Listo: {res['desempenos']} desempeño(s) y {res['estandares']} estándar(es) verificados contra el PDF oficial.")
                siguiente_version(ver_key)
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo: {e}")
    elif opcion.startswith("📤"):
        st.caption("Sube tu PDF o Word (por ejemplo, el Programa Curricular de tu nivel).")
        archivo = st.file_uploader("Archivo PDF o Word", type=["pdf", "docx", "txt"], key=f"lin_up_{aid}")
        if archivo is not None and confirmar("lineamientos", "Leer mi archivo", f"lin_leer_{aid}"):
            barra = st.progress(0.0)
            try:
                res = desde_archivo(asig, archivo.name, archivo.getvalue(), lambda f, t: barra.progress(min(f, 1.0), text=t))
                cobrar(uid, "lineamientos")
                flash(f"Listo: {res['desempenos']} desempeño(s) y {res['estandares']} estándar(es) leídos de tu archivo.")
                siguiente_version(ver_key)
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo leer: {e}")


def _pasos(hay_doc):
    """Barra de 3 pasos para orientar al docente."""
    pasos = [("1", "Tu curso", "done"), ("2", "Genera tu sílabo", "done" if hay_doc else "on"),
             ("3", "Revisa y descarga", "on" if hay_doc else "")]
    st.markdown("<div class='steps'>" + "".join(
        f"<div class='step {c}'><span class='step-n'>{'✓' if c == 'done' else n}</span><span class='step-t'>{tt}</span></div>"
        for n, tt, c in pasos) + "</div>", unsafe_allow_html=True)


def render():
    asig = exigir_area()
    uid, aid = st.session_state.user_id, asig["id"]
    st.title("📅 Sílabo anual")
    st.caption(f"{asig['area']} · {asig['grado']} · Sección {asig['seccion'] or '—'}")

    ver_key = f"ver_anual_{aid}"
    ver = st.session_state.get(ver_key, 0)
    doc = get_doc(aid, "anual")
    data = contenido(doc) if doc else {}
    _pasos(bool(doc))
    if doc:
        from eduperu.services.exportar import bloques_de
        from eduperu.services.render import a_docx
        bl, hor, archivo = bloques_de(doc)
        descargar("⬇️ Descargar mi sílabo en Word", a_docx(bl, doc.get("color"), doc.get("normativa_usada"), hor), archivo,
                  MIME_DOCX, f"dl_top_anual_{aid}", type="primary")

    st.markdown("##### Prepara tu curso <span class='opc'>(revisa solo lo que necesites)</span>", unsafe_allow_html=True)

    # DATOS
    with st.expander("👤 Mis datos: colegio, director, sección", expanded=not asig["director"]):
        c1, c2 = st.columns(2)
        inst = c1.text_input("Institución educativa", value=asig["institucion"] or "", key=f"d_inst_{aid}")
        director = c2.text_input("Director(a)", value=asig["director"] or "", key=f"d_dir_{aid}")
        docente = c1.text_input("Docente", value=asig["docente"] or "", key=f"d_doc_{aid}")
        seccion = c2.text_input("Sección", value=asig["seccion"] or "", key=f"d_sec_{aid}")
        st.caption(f"Nivel: {asig['nivel']} · Grado: {asig['grado']} · Área: {asig['area']} · "
                   f"Ciclo {ciclo_de(asig['nivel'], asig['grado'])} · Región: {asig['region']}")
        if st.button("💾 Guardar datos", key=f"d_save_{aid}"):
            actualizar_asignacion(aid, institucion=inst.strip(), director=director.strip(),
                                  docente=docente.strip(), seccion=seccion.strip())
            flash("Datos guardados ✅")
            st.rerun()

    # LINEAMIENTOS
    n_comp, n_ver, n_des = estado_area(asig["nivel"], asig["area"], asig["grado"], aid)
    lin_listo = bool(asig.get("lineamientos_fuente")) or (n_ver == n_comp and n_des == n_comp)
    with st.expander("📘 Competencias y desempeños del MINEDU  " + ("✅ Listo" if lin_listo else "⚠️ Revisar"),
                     expanded=not lin_listo):
        _paso_lineamientos(asig, ver_key)

    # CARACTERIZACIÓN
    with st.expander("🧑‍🎓 Mis estudiantes  " + ("✅" if asig.get("caracterizacion") else "(opcional, ayuda a la IA)")):
        st.caption("Cuéntanos cómo son tus estudiantes para que la IA adapte el sílabo. Si no sabes qué escribir, pide un boceto.")
        notas = st.text_input("Una idea breve (opcional)", key=f"car_notas_{aid}",
                              placeholder="Ej.: zona rural, les gusta el fútbol, varios trabajan con sus padres")
        if confirmar("caracterizacion", "✨ Escribir boceto con IA", f"car_{aid}"):
            try:
                with st.spinner("Escribiendo el boceto..."):
                    texto = _generar_caracterizacion(asig, notas)
                actualizar_asignacion(aid, caracterizacion=texto)
                cobrar(uid, "caracterizacion")
                siguiente_version(ver_key)
                flash("Boceto listo. Léelo y ajústalo a tu realidad.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo generar: {e}")
        car = campo_texto("Descripción de mis estudiantes", f"car_{aid}_{ver}", asig.get("caracterizacion") or "", 150)
        if st.button("💾 Guardar", key=f"car_save_{aid}"):
            actualizar_asignacion(aid, caracterizacion=car)
            flash("Guardado ✅")
            st.rerun()

    # COMPETENCIAS
    comps = competencias_de(asig["nivel"], asig["area"])
    if not comps:
        st.error("Este curso todavía no tiene competencias cargadas. Pide al administrador que las agregue en "
                 "Administración → Currículo.")
        st.stop()
    nombres = [c["nombre"] for c in comps]
    with st.expander("🎯 Competencias que trabajarás este año"):
        st.caption("Ya vienen todas marcadas. Quita las que no vayas a trabajar.")
        sel = campo_multi("Competencias del año", f"comp_{aid}_{ver}", nombres, data.get("competencias_area") or nombres)
        if sel:
            comps_ver = [c for c in comps if c["nombre"] in sel]
            for c in comps_ver:
                st.markdown(f"**{c['nombre']}**" + ("" if c["verificado"] else "  ⚠️ _pendiente de verificación_"))
                st.caption(" · ".join(c["capacidades"]))
    if not sel:
        st.warning("Elige al menos una competencia (en «🎯 Competencias que trabajarás este año»).")
        st.stop()
    comps_sel = [c for c in comps if c["nombre"] in sel]

    # UNIDADES Y TEMAS
    st.markdown("---")
    st.subheader("🚀 Tu sílabo" if unidades_hay(data) else "🚀 Genera tu sílabo")
    unidades = data.get("unidades") or []
    n = len(unidades)
    spw = 3
    if not unidades:
        st.caption("La IA propone las unidades del año, con su situación significativa y los temas de cada clase. "
                   "Después puedes editar todo.")
        c1, c2 = st.columns(2)
        n = int(c1.number_input("¿Cuántas unidades tendrá el año?", 1, 12, 6, key=f"nuni_{aid}"))
        spw = int(c2.number_input("Clases por semana", 1, 8, 3, key=f"spw_anual_{aid}"))
    if confirmar("anual", "✨ Generar sílabo con IA" if not unidades else "🔄 Volver a generar (reemplaza lo actual)",
                 f"anual_{aid}", asig=asig):
        try:
            with st.spinner("Creando tu sílabo... (puede tardar un minuto)"):
                nuevas = _generar_unidades(asig, comps_sel, n, spw)
            guardar_doc(uid, aid, "anual", 1, f"Sílabo anual {asig['area']} {asig['grado']}",
                        {"competencias_area": sel, "unidades": nuevas, "clases_por_semana": spw},
                        normativa=normativa_vigente()[1])
            cobrar(uid, "anual")
            siguiente_version(ver_key)
            flash("¡Listo! Revisa cada unidad y ajusta lo que quieras.")
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo generar: {e}")

    if unidades:
        st.caption("Abre cada unidad para revisarla. Lo principal está en la primera pestaña; lo demás, en «Más detalles».")
        for u in unidades:
            i = u["numero"]
            base = f"an_{aid}_{ver}_{i}"
            with st.expander(f"📚 Unidad {i}: {u['titulo']}  ·  {len(u.get('temas') or [])} clases", expanded=(i == 1)):
                tab_a, tab_b = st.tabs(["✍️ Lo principal", "⚙️ Más detalles"])
                with tab_a:
                    campo_linea("Título de la unidad", f"{base}_t", u["titulo"])
                    campo_texto("Situación significativa", f"{base}_s", u["situacion"], 160)
                    campo_texto("Clases de la unidad (una por línea)", f"{base}_tm",
                                "\n".join(t["titulo"] for t in u.get("temas") or []), 180,
                                "Estas clases son las que luego eliges en «Temas y clases» para crear sesiones, fichas y desafíos.")
                with tab_b:
                    campo_texto("Problema identificado", f"{base}_p", u["problema"], 80)
                    campo_linea("Valores observables", f"{base}_v", u["valores"])
                    cs = campo_multi("Competencias de esta unidad", f"{base}_c", sel, u["competencias"])
                    caps_op = [cap for c in comps if c["nombre"] in cs for cap in c["capacidades"]]
                    campo_multi("Capacidades a trabajar", f"{base}_k", caps_op, u["capacidades"])
                    campo_num("Semanas", f"{base}_w", 1, 12, u.get("semanas") or 4)

        def recoger():
            res = []
            for u in unidades:
                i = u["numero"]
                base = f"an_{aid}_{ver}_{i}"
                previos = {norm(t["titulo"]): t for t in u.get("temas") or []}
                cs = st.session_state.get(f"{base}_c", u["competencias"])
                temas = []
                for linea in a_lista(st.session_state.get(f"{base}_tm", "")):
                    t = previos.get(norm(linea)) or {"titulo": linea, "competencia": (cs or [""])[0], "desempeno_texto": ""}
                    temas.append({**t, "titulo": linea})
                res.append({"numero": i, "titulo": st.session_state.get(f"{base}_t", u["titulo"]),
                            "problema": st.session_state.get(f"{base}_p", ""),
                            "situacion": st.session_state.get(f"{base}_s", ""),
                            "valores": st.session_state.get(f"{base}_v", ""),
                            "competencias": cs, "capacidades": st.session_state.get(f"{base}_k", u["capacidades"]),
                            "semanas": entero(st.session_state.get(f"{base}_w"), 4, 1, 12), "temas": temas})
            return res

        def guardar(lista):
            guardar_doc(uid, aid, "anual", 1, f"Sílabo anual {asig['area']} {asig['grado']}",
                        {**data, "competencias_area": sel, "unidades": lista})

        b1, b2, b3 = st.columns(3)
        if b1.button("💾 Guardar sílabo", type="primary", key=f"an_save_{aid}", use_container_width=True):
            guardar(recoger())
            st.success("Sílabo guardado ✅")
        if b2.button("➕ Agregar unidad", key=f"an_add_{aid}", use_container_width=True):
            lista = recoger()
            lista.append(_vacia(len(lista) + 1, comps_sel))
            guardar(lista)
            siguiente_version(ver_key)
            st.rerun()
        if b3.button("➖ Quitar la última", key=f"an_del_{aid}", use_container_width=True) and len(unidades) > 1:
            guardar(recoger()[:-1])
            siguiente_version(ver_key)
            st.rerun()

    # DOCUMENTO
    if doc:
        st.subheader("📄 Vista previa de tu sílabo")
        vista_previa_y_descarga(doc["id"], f"anual_{aid}", abierta=False)
        st.button("Siguiente: elegir una clase y crear sus materiales →", on_click=ir_a, args=(PAG_TEMAS,), type="primary")


def unidades_hay(data):
    return bool(data.get("unidades"))
