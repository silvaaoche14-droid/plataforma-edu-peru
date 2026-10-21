"""Planificación anual: datos informativos, caracterización, competencias, situaciones significativas y unidades."""
import streamlit as st

from curriculo import ciclo_de, competencias_de
from ia import generar_texto, pedir_json, preambulo
from normativa import normativa_vigente
from repo import actualizar_asignacion, contenido, cobrar, get_doc, guardar_doc
from ui import (PAG_UNIDADES, campo_linea, campo_multi, campo_num, campo_texto, confirmar, exigir_area, flash,
                ir_a, siguiente_version, vista_previa_y_descarga)
from util import entero, norm, s


def _generar_caracterizacion(asig, notas):
    prompt = f"""{preambulo()}
Redacta un BOCETO de caracterización y contexto de los estudiantes (2 párrafos, máximo 150 palabras).
Datos: nivel {asig['nivel']}, grado {asig['grado']}, área {asig['area']}, región {asig['region']}, institución {asig['institucion'] or 'no indicada'}.
Notas del docente: {notas or 'ninguna'}.
Incluye: rasgos de desarrollo propios de la edad, intereses, contexto sociocultural probable de la región y necesidades de aprendizaje frecuentes.
No inventes cifras ni datos personales. Tono general; el docente lo ajustará. Devuelve solo el texto."""
    texto, _ = generar_texto(prompt)
    return s(texto)


def _generar_unidades(asig, comps_sel, n):
    ctx = "\n".join(f"- {c['nombre']} (capacidades: {'; '.join(c['capacidades'])})" for c in comps_sel)
    prompt = f"""{preambulo()}
Elabora las SITUACIONES SIGNIFICATIVAS de la PLANIFICACIÓN ANUAL {asig['ciclo_escolar']} con {n} unidades de aprendizaje.
Datos: nivel {asig['nivel']}, grado {asig['grado']}, área {asig['area']}, región {asig['region']}, institución {asig['institucion'] or 'no indicada'}.
Caracterización de los estudiantes: {asig.get('caracterizacion') or 'no especificada'}
Competencias del área (usa SOLO estos nombres, escritos EXACTAMENTE igual):
{ctx}

Para cada unidad entrega:
- "titulo": título corto y motivador.
- "problema": problema identificado del contexto (1 a 2 oraciones).
- "situacion": situación significativa contextualizada a {asig['region']} (4 a 6 oraciones) que plantee un reto y termine con preguntas retadoras.
- "valores": valores observables (2 a 3, separados por coma) tomados de los enfoques transversales del CNEB.
- "competencias": lista de 1 a 3 nombres EXACTOS de la lista anterior. Entre todas las unidades deben quedar cubiertas todas las competencias.
- "semanas": número entre 3 y 5.

Formato: {{"unidades":[{{"numero":1,"titulo":"...","problema":"...","situacion":"...","valores":"...","competencias":["..."],"semanas":4}}]}}"""
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
                         "competencias": elegidas, "capacidades": caps,
                         "semanas": entero(u.get("semanas"), 4, 1, 12)})
    return unidades


def _vacia(i, comps_sel):
    nombre = comps_sel[(i - 1) % len(comps_sel)]
    return {"numero": i, "titulo": f"Unidad {i}", "problema": "", "situacion": "", "valores": "",
            "competencias": [nombre["nombre"]], "capacidades": list(nombre["capacidades"]), "semanas": 4}


def render():
    asig = exigir_area()
    uid, aid = st.session_state.user_id, asig["id"]
    st.title("📅 Planificación anual")
    st.caption(f"{asig['area']} · {asig['grado']} · Sección {asig['seccion'] or '—'}  |  Alineada a RM N.° 501-2025-MINEDU")
    st.info("💡 Sigue los pasos de arriba hacia abajo. Todo lo que escribe la IA lo puedes editar antes de guardar.")

    ver_key = f"ver_anual_{aid}"
    ver = st.session_state.get(ver_key, 0)
    doc = get_doc(aid, "anual")
    data = contenido(doc) if doc else {}

    # ① DATOS INFORMATIVOS
    st.subheader("① Datos informativos")
    with st.expander("Ver y editar mis datos", expanded=not asig["director"]):
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

    # ② CARACTERIZACIÓN
    st.subheader("② Caracterización y contexto de tus estudiantes")
    st.caption("Describe brevemente cómo son tus estudiantes. Si no sabes qué escribir, pide un boceto a la IA.")
    notas = st.text_input("Cuéntame algo de tus estudiantes (opcional)", key=f"car_notas_{aid}",
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
    car = campo_texto("Caracterización del estudiante", f"car_{aid}_{ver}", asig.get("caracterizacion") or "", 150)
    if st.button("💾 Guardar caracterización", key=f"car_save_{aid}"):
        actualizar_asignacion(aid, caracterizacion=car)
        flash("Caracterización guardada ✅")
        st.rerun()

    # ③ COMPETENCIAS
    st.subheader("③ Competencias que trabajarás este año")
    comps = competencias_de(asig["nivel"], asig["area"])
    if not comps:
        st.error("Esta área todavía no tiene competencias cargadas. Pide al administrador que las agregue "
                 "en Administración → Currículo.")
        st.stop()
    nombres = [c["nombre"] for c in comps]
    sel = campo_multi("Competencias del año", f"comp_{aid}_{ver}", nombres, data.get("competencias_area") or nombres)
    if not sel:
        st.warning("Elige al menos una competencia.")
        st.stop()
    comps_sel = [c for c in comps if c["nombre"] in sel]
    with st.expander("Ver capacidades de cada competencia"):
        for c in comps_sel:
            st.markdown(f"**{c['nombre']}**" + ("" if c["verificado"] else "  ⚠️ _pendiente de verificación_"))
            st.markdown("\n".join(f"- {x}" for x in c["capacidades"]))

    # ④ SITUACIONES SIGNIFICATIVAS Y UNIDADES
    st.subheader("④ Situaciones significativas y unidades")
    unidades = data.get("unidades") or []
    n = len(unidades)
    if not unidades:
        n = int(st.number_input("¿Cuántas unidades tendrá el año?", 1, 12, 6, key=f"nuni_{aid}"))
    st.caption("La IA propone una situación significativa por unidad, con el problema del contexto, valores y competencias.")
    if confirmar("anual", "✨ Generar situaciones significativas con IA" if not unidades else
                 "🔄 Volver a generar (reemplaza lo actual)", f"anual_{aid}"):
        try:
            with st.spinner("Creando situaciones significativas... (puede tardar un minuto)"):
                nuevas = _generar_unidades(asig, comps_sel, n)
            guardar_doc(uid, aid, "anual", 1, f"Planificación anual {asig['area']} {asig['grado']}",
                        {"competencias_area": sel, "unidades": nuevas}, normativa=normativa_vigente()[1])
            cobrar(uid, "anual")
            siguiente_version(ver_key)
            flash("¡Listo! Revisa cada unidad y ajusta lo que quieras.")
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo generar: {e}")

    if unidades:
        for u in unidades:
            i = u["numero"]
            base = f"an_{aid}_{ver}_{i}"
            with st.expander(f"Unidad {i}: {u['titulo']}", expanded=(i == 1)):
                campo_linea("Título de la unidad", f"{base}_t", u["titulo"])
                campo_texto("Problema identificado", f"{base}_p", u["problema"], 80)
                campo_texto("Situación significativa", f"{base}_s", u["situacion"], 160)
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
                res.append({"numero": i, "titulo": st.session_state.get(f"{base}_t", u["titulo"]),
                            "problema": st.session_state.get(f"{base}_p", ""),
                            "situacion": st.session_state.get(f"{base}_s", ""),
                            "valores": st.session_state.get(f"{base}_v", ""),
                            "competencias": st.session_state.get(f"{base}_c", u["competencias"]),
                            "capacidades": st.session_state.get(f"{base}_k", u["capacidades"]),
                            "semanas": entero(st.session_state.get(f"{base}_w"), 4, 1, 12)})
            return res

        def guardar(lista):
            guardar_doc(uid, aid, "anual", 1, f"Planificación anual {asig['area']} {asig['grado']}",
                        {"competencias_area": sel, "unidades": lista})

        b1, b2, b3 = st.columns(3)
        if b1.button("💾 Guardar planificación", type="primary", key=f"an_save_{aid}", use_container_width=True):
            guardar(recoger())
            st.success("Planificación guardada ✅")
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

    # ⑤ VISTA PREVIA
    if doc:
        st.subheader("⑤ Tu documento")
        vista_previa_y_descarga(doc["id"], f"anual_{aid}")
        st.button("Siguiente: crear las unidades →", on_click=ir_a, args=(PAG_UNIDADES,), type="primary")
