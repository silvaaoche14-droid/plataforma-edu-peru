"""Temas y clases: sesión, ficha, rúbrica, desafíos y examen de cada tema; unidad, desafíos y examen de la unidad."""
import streamlit as st

from eduperu.views.examen_unidad import render as render_examen_unidad
from eduperu.core.ia import pedir_json, preambulo
from eduperu.core.normativa import normativa_vigente
from eduperu.core.repo import cobrar, contenido, crear_sesiones_desde_secuencia, get_doc, guardar_doc, listar_docs
from eduperu.ui.components import (PAG_ANUAL, barra_edicion, campo_linea, campo_num, campo_texto, confirmar, editor_items, exigir_area,
                exigir_cadena, flash, ir_a, recoger_items, seccion, siguiente_version, vista_previa_y_descarga)
from eduperu.views.unidades import _unidad, asegurar_unidad
from eduperu.core.util import a_lista, a_texto, entero, norm, s


# ------------------------------------------------------------------
# GENERACIÓN
# ------------------------------------------------------------------
def generar_sesion(asig, udata, sdata, duracion, comps_sel, notas=""):
    props = {p["competencia"]: p for p in udata.get("propositos", [])}
    comps_sel = [c for c in comps_sel if c in props] or list(props)[:1]
    if not comps_sel:
        raise RuntimeError("La unidad no tiene propósitos de aprendizaje. Genera o completa la unidad primero.")
    bloque = "\n".join(
        f"- {n}\n  Capacidades: {'; '.join(props[n].get('capacidades', []))}\n"
        f"  Desempeños: {' | '.join(props[n].get('desempenos', []))}\n  Propósito de la unidad: {props[n].get('proposito', '')}"
        for n in comps_sel)
    prompt = f"""{preambulo()}
Elabora una SESIÓN DE APRENDIZAJE.
Datos: nivel {asig['nivel']}, grado {asig['grado']}, área {asig['area']}, región {asig['region']}.
Unidad {udata.get('numero')}: {udata.get('titulo')}
Situación significativa: {udata.get('situacion')}
Título o reto de la sesión: {sdata.get('titulo')}
Duración: {duracion} minutos. Indicaciones del docente: {notas or 'ninguna'}

Competencias que se trabajan (no cambies su redacción):
{bloque}

Entrega:
- "titulo": título de la sesión (puedes mejorar el propuesto).
- "proposito": propósito en lenguaje del estudiante ("Hoy aprenderemos a...").
- "competencias": un objeto por competencia: {{"competencia": nombre EXACTO, "criterios": [2 a 3 criterios de evaluación observables], "evidencia": "...", "instrumento": "Lista de cotejo / Rúbrica / Escala de valoración"}}
- "inicio": {{"actividades": "motivación, saberes previos, conflicto cognitivo y propósito", "minutos": n}}
- "desarrollo": {{"actividades": "pasos detallados de la actividad principal", "minutos": n}}
- "cierre": {{"actividades": "síntesis y metacognición", "minutos": n}}
- "materiales": lista de materiales y recursos.
- "reflexion": 3 preguntas de metacognición.
Los minutos de inicio, desarrollo y cierre deben sumar {duracion}."""
    ia, _ = pedir_json(prompt)
    if not isinstance(ia, dict):
        raise RuntimeError("La IA devolvió un formato inesperado. Intenta de nuevo.")
    por_ia = {norm(x.get("competencia")): x for x in ia.get("competencias") or [] if isinstance(x, dict)}
    filas = []
    for nombre in comps_sel:
        p, x = props[nombre], por_ia.get(norm(nombre), {})
        filas.append({"competencia": nombre, "capacidades": p.get("capacidades", []),
                      "desempenos": p.get("desempenos", []), "por_verificar": bool(p.get("por_verificar")),
                      "criterios": a_lista(x.get("criterios")), "evidencia": s(x.get("evidencia")),
                      "instrumento": s(x.get("instrumento"))})

    def momento(k, defecto):
        m = ia.get(k) if isinstance(ia.get(k), dict) else {}
        return {"actividades": s(m.get("actividades")), "minutos": entero(m.get("minutos"), defecto, 1, 240)}

    return {**sdata, "titulo": s(ia.get("titulo")) or sdata.get("titulo", ""), "proposito": s(ia.get("proposito")),
            "duracion": int(duracion), "competencias": filas, "inicio": momento("inicio", round(duracion * 0.15)),
            "desarrollo": momento("desarrollo", round(duracion * 0.7)), "cierre": momento("cierre", round(duracion * 0.15)),
            "materiales": a_lista(ia.get("materiales")), "reflexion": a_lista(ia.get("reflexion")),
            "enfoques": udata.get("enfoques", []), "unidad_numero": udata.get("numero")}


def _resumen_competencias(sdata):
    return "\n".join(f"- {c['competencia']}: criterios {c.get('criterios')}; evidencia: {c.get('evidencia')}"
                     for c in sdata.get("competencias", []))


# ------------------------------------------------------------------
# PANTALLA: TEMAS Y CLASES
# ------------------------------------------------------------------
def render():
    asig = exigir_area()
    uid, aid = st.session_state.user_id, asig["id"]
    st.title("🎯 Temas y clases")
    st.info("💡 Elige un tema de tu sílabo (una clase) o una unidad completa y crea con IA sus sesiones, fichas, "
            "desafíos, rúbricas y exámenes.")
    anual = get_doc(aid, "anual")
    if not anual:
        exigir_cadena("Primero crea tu sílabo anual: de ahí salen las unidades y los temas.", PAG_ANUAL,
                      "Ir al Sílabo anual")
    unidades = contenido(anual).get("unidades") or []
    if not unidades:
        exigir_cadena("Tu sílabo anual todavía no tiene unidades. Genera el sílabo primero.", PAG_ANUAL,
                      "Ir al Sílabo anual")

    num = st.radio("Unidad", [u["numero"] for u in unidades], horizontal=True, key=f"tc_unidad_{aid}",
                   format_func=lambda n: f"Unidad {n}")
    ua = next(u for u in unidades if u["numero"] == num)
    st.caption(f"**{ua['titulo']}** · {len(ua.get('temas') or [])} temas")
    udoc = asegurar_unidad(asig, anual, ua)
    udata = contenido(udoc)

    ambito = st.radio("¿Qué quieres trabajar?", ["📖 Una clase (un tema)", "📚 Toda la unidad"], horizontal=True,
                      key="tc_ambito")
    if ambito.startswith("📚"):
        sec = seccion(["📚 Unidad de aprendizaje", "🏆 Desafíos de la unidad", "📋 Examen de la unidad"], "tc_sec_unidad")
        if sec.startswith("📚"):
            _unidad(asig, anual, ua)
        elif sec.startswith("🏆"):
            _tab_desafios(asig, udoc, udata, "unidad")
        else:
            render_examen_unidad(asig, udoc)
        return

    sesiones = listar_docs(aid, "sesion", padre_id=udoc["id"])
    if not sesiones and udata.get("secuencia"):
        crear_sesiones_desde_secuencia(uid, asig, udoc)
        sesiones = listar_docs(aid, "sesion", padre_id=udoc["id"])
    if not sesiones:
        st.warning("Esta unidad todavía no tiene temas. Agrégalos en el **Sílabo anual** (campo «Temas / clases») "
                   "o elige «Toda la unidad» para generar la unidad con IA.")
        st.button("Ir al Sílabo anual", on_click=ir_a, args=(PAG_ANUAL,))
        st.stop()

    def etiqueta(i):
        sd = contenido(sesiones[i])
        return f"{'✅' if sd.get('inicio') else '⬜'} Clase {sesiones[i]['numero']}: {sd.get('titulo', '')}"

    _masivo(asig, udoc, udata, sesiones)
    idx = st.selectbox("Elige el tema (clase)", list(range(len(sesiones))), format_func=etiqueta,
                       key=f"se_sel_{udoc['id']}")
    sdoc = sesiones[idx]
    sec = seccion(["📖 Sesión de aprendizaje", "📄 Ficha de trabajo", "📊 Rúbrica", "🏆 Desafíos", "📋 Examen"],
                  "tc_sec_clase")
    if sec.startswith("📖"):
        _tab_contenido(asig, udoc, udata, sdoc)
    elif sec.startswith("📄"):
        _tab_ficha(asig, sdoc)
    elif sec.startswith("📊"):
        _tab_rubrica(asig, sdoc)
    elif sec.startswith("🏆"):
        _tab_desafios(asig, sdoc, udata, "clase")
    else:
        _tab_examen(asig, sdoc)


def _masivo(asig, udoc, udata, sesiones):
    uid = st.session_state.user_id
    faltan = [x for x in sesiones if not contenido(x).get("inicio")]
    with st.expander(f"⚡ Generar todas las sesiones de la unidad ({len(faltan)} pendientes)"):
        if not faltan:
            st.success("Todas las sesiones de esta unidad ya tienen contenido.")
            return
        dur = st.number_input("Duración de cada sesión (minutos)", 20, 240, 90, step=5, key=f"mas_dur_{udoc['id']}")
        if confirmar("sesion", f"Generar las {len(faltan)} sesiones", f"mas_{udoc['id']}", veces=len(faltan), asig=asig):
            barra = st.progress(0.0)
            hechas = 0
            for k, sdoc in enumerate(faltan, 1):
                sd = contenido(sdoc)
                try:
                    nuevo = generar_sesion(asig, udata, sd, int(dur), sd.get("competencias_sugeridas") or [])
                    guardar_doc(uid, asig["id"], "sesion", sdoc["numero"], f"Sesión {sdoc['numero']}: {nuevo['titulo']}",
                                nuevo, padre_id=udoc["id"], normativa=normativa_vigente()[1])
                    cobrar(uid, "sesion")
                    hechas += 1
                except Exception as e:
                    st.error(f"Se detuvo en la sesión {sdoc['numero']}: {e}")
                    break
                barra.progress(k / len(faltan))
            flash(f"Se generaron {hechas} sesión(es) ✅")
            st.rerun()


# ------------------------------------------------------------------
# SESIÓN
# ------------------------------------------------------------------
def _tab_contenido(asig, udoc, udata, sdoc):
    uid, aid = st.session_state.user_id, asig["id"]
    d = contenido(sdoc)
    ver_key = f"ver_ses_{sdoc['id']}"
    ver = st.session_state.get(ver_key, 0)
    props = [p["competencia"] for p in udata.get("propositos", [])]
    hecho = bool(d.get("inicio"))

    with st.expander("⚙️ Opciones y generación con IA", expanded=not hecho):
        c1, c2 = st.columns(2)
        duracion = c1.number_input("Duración (minutos)", 20, 240, entero(d.get("duracion"), 90, 20, 240), step=5,
                                   key=f"ses_dur_{sdoc['id']}_{ver}")
        sel = c2.multiselect("Competencias de esta sesión", props,
                             default=[x for x in (d.get("competencias_sugeridas") or props[:1]) if x in props],
                             key=f"ses_comp_{sdoc['id']}_{ver}")
        notas = st.text_input("Indicaciones especiales (opcional)", key=f"ses_notas_{sdoc['id']}_{ver}",
                              placeholder="Ej.: aula multigrado, sin proyector, usar material reciclable")
        etiqueta = "✨ Generar sesión con IA" if not hecho else "🔄 Volver a generar (reemplaza lo actual)"
        if confirmar("sesion", etiqueta, f"ses_{sdoc['id']}", asig=asig):
            try:
                with st.spinner("Creando la sesión..."):
                    nuevo = generar_sesion(asig, udata, d, int(duracion), sel, notas)
                guardar_doc(uid, aid, "sesion", sdoc["numero"], f"Sesión {sdoc['numero']}: {nuevo['titulo']}", nuevo,
                            padre_id=udoc["id"], normativa=normativa_vigente()[1])
                cobrar(uid, "sesion")
                siguiente_version(ver_key)
                flash("¡Sesión lista! Descárgala en Word o edítala.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo generar: {e}")
    if not hecho:
        st.caption("Aún no hay contenido en esta sesión.")
        return

    vista_previa_y_descarga(sdoc["id"], f"sesion_{sdoc['id']}")
    with st.expander("✏️ Editar la sesión"):
        base = f"s_{sdoc['id']}_{ver}"
        campo_linea("Título de la sesión", f"{base}_tit", d.get("titulo", ""))
        campo_texto("Propósito de aprendizaje", f"{base}_pro", d.get("proposito", ""), 80)
        filas = d.get("competencias", [])
        for j, c in enumerate(filas):
            st.markdown(f"**Competencia:** {c['competencia']}" + ("  ⚠️ _desempeños por verificar_" if c.get("por_verificar") else ""))
            campo_texto("Criterios de evaluación (uno por línea)", f"{base}_c{j}_cr", a_texto(c.get("criterios")), 100)
            campo_texto("Evidencia de aprendizaje", f"{base}_c{j}_ev", c.get("evidencia", ""), 70)
            campo_linea("Instrumento", f"{base}_c{j}_in", c.get("instrumento", ""))
        st.markdown("**Secuencia didáctica**")
        for k, nombre in (("inicio", "Inicio"), ("desarrollo", "Desarrollo"), ("cierre", "Cierre")):
            m = d.get(k) or {}
            campo_texto(nombre, f"{base}_{k}_a", m.get("actividades", ""), 140 if k == "desarrollo" else 100)
            campo_num(f"Minutos de {nombre.lower()}", f"{base}_{k}_m", 1, 240, entero(m.get("minutos"), 10))
        campo_texto("Materiales y recursos (uno por línea)", f"{base}_mat", a_texto(d.get("materiales")), 90)
        campo_texto("Reflexión sobre el aprendizaje (una pregunta por línea)", f"{base}_ref", a_texto(d.get("reflexion")), 90)
        if st.button("💾 Guardar sesión", type="primary", key=f"s_save_{sdoc['id']}"):
            ss = st.session_state
            nuevas = [{**c, "criterios": a_lista(ss.get(f"{base}_c{j}_cr")), "evidencia": ss.get(f"{base}_c{j}_ev", ""),
                       "instrumento": ss.get(f"{base}_c{j}_in", "")} for j, c in enumerate(filas)]
            nuevo = {**d, "titulo": ss.get(f"{base}_tit", ""), "proposito": ss.get(f"{base}_pro", ""), "competencias": nuevas,
                     "materiales": a_lista(ss.get(f"{base}_mat")), "reflexion": a_lista(ss.get(f"{base}_ref"))}
            for k in ("inicio", "desarrollo", "cierre"):
                nuevo[k] = {"actividades": ss.get(f"{base}_{k}_a", ""), "minutos": entero(ss.get(f"{base}_{k}_m"), 10, 1, 240)}
            guardar_doc(uid, aid, "sesion", sdoc["numero"], f"Sesión {sdoc['numero']}: {nuevo['titulo']}", nuevo,
                        padre_id=udoc["id"])
            st.success("Sesión guardada ✅ (la vista previa se actualiza al volver a abrir esta sección)")


def _necesita_sesion(sdoc):
    sd = contenido(sdoc)
    if not sd.get("inicio"):
        st.info("Primero genera la **sesión de aprendizaje** (sección «📖 Sesión de aprendizaje»): de ahí salen los "
                "criterios y las evidencias.")
        return None
    return sd


# ------------------------------------------------------------------
# RÚBRICA
# ------------------------------------------------------------------
CAMPOS_RUBRICA = [{"k": "criterio", "label": "Criterio", "tipo": "linea"},
                  {"k": "AD", "label": "AD · Logro destacado", "tipo": "area", "alto": 70},
                  {"k": "A", "label": "A · Logro esperado", "tipo": "area", "alto": 70},
                  {"k": "B", "label": "B · En proceso", "tipo": "area", "alto": 70},
                  {"k": "C", "label": "C · En inicio", "tipo": "area", "alto": 70}]


def _tab_rubrica(asig, sdoc):
    sd = _necesita_sesion(sdoc)
    if not sd:
        return
    uid, aid = st.session_state.user_id, asig["id"]
    doc = get_doc(aid, "rubrica", padre_id=sdoc["id"])
    d = contenido(doc) if doc else {}
    ver_key = f"ver_rub_{sdoc['id']}"
    ver = st.session_state.get(ver_key, 0)
    with st.expander("⚙️ Generar con IA", expanded=not doc):
        if confirmar("rubrica", "✨ Generar rúbrica con IA" if not doc else "🔄 Volver a generar la rúbrica",
                     f"rub_{sdoc['id']}", asig=asig):
            try:
                prompt = f"""{preambulo()}
Elabora una RÚBRICA de evaluación para esta sesión (nivel {asig['nivel']}, grado {asig['grado']}, área {asig['area']}).
Sesión: {sd.get('titulo')}
Competencias, criterios y evidencias:
{_resumen_competencias(sd)}
Entrega entre 3 y 5 criterios (puedes partir de los criterios dados). Para cada uno describe lo observable en cuatro niveles: AD (logro destacado), A (logro esperado), B (en proceso), C (en inicio).
Formato: {{"criterios":[{{"criterio":"...","AD":"...","A":"...","B":"...","C":"..."}}]}}"""
                with st.spinner("Creando la rúbrica..."):
                    ia, _ = pedir_json(prompt)
                lista = ia.get("criterios") if isinstance(ia, dict) else ia
                filas = [{"numero": i, "criterio": s(r.get("criterio")), "AD": s(r.get("AD")), "A": s(r.get("A")),
                          "B": s(r.get("B")), "C": s(r.get("C"))} for i, r in enumerate(lista or [], 1) if isinstance(r, dict)]
                if not filas:
                    raise RuntimeError("La IA no devolvió criterios. Intenta de nuevo.")
                guardar_doc(uid, aid, "rubrica", 1, f"Rúbrica: {sd.get('titulo')}", {"criterios": filas},
                            padre_id=sdoc["id"], normativa=normativa_vigente()[1])
                cobrar(uid, "rubrica")
                siguiente_version(ver_key)
                flash("Rúbrica lista ✅")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo generar: {e}")
    if not doc:
        return
    vista_previa_y_descarga(doc["id"], f"rub_{sdoc['id']}")
    with st.expander("✏️ Editar la rúbrica"):
        clave = f"rub_{sdoc['id']}_{ver}"
        items = d.get("criterios", [])
        editor_items(clave, items, CAMPOS_RUBRICA, lambda i, x: f"Criterio {i + 1}: {s(x.get('criterio'))[:60]}")
        barra_edicion(clave, items, CAMPOS_RUBRICA,
                      lambda n: {"numero": n, "criterio": "", "AD": "", "A": "", "B": "", "C": ""},
                      lambda lista: guardar_doc(uid, aid, "rubrica", 1, doc["titulo"], {"criterios": lista}, padre_id=sdoc["id"]),
                      ver_key)


# ------------------------------------------------------------------
# FICHA DE TRABAJO
# ------------------------------------------------------------------
CAMPOS_FICHA = [{"k": "consigna", "label": "Consigna", "tipo": "area", "alto": 90},
                {"k": "respuesta", "label": "Respuesta esperada (solo para el docente)", "tipo": "linea"}]


def _tab_ficha(asig, sdoc):
    sd = _necesita_sesion(sdoc)
    if not sd:
        return
    uid, aid = st.session_state.user_id, asig["id"]
    doc = get_doc(aid, "ficha", padre_id=sdoc["id"])
    d = contenido(doc) if doc else {}
    ver_key = f"ver_fic_{sdoc['id']}"
    ver = st.session_state.get(ver_key, 0)
    with st.expander("⚙️ Generar con IA", expanded=not doc):
        n_act = st.number_input("Número de actividades", 3, 12, 6, key=f"fic_n_{sdoc['id']}")
        if confirmar("ficha", "✨ Generar ficha con IA" if not doc else "🔄 Volver a generar la ficha",
                     f"fic_{sdoc['id']}", asig=asig):
            try:
                prompt = f"""{preambulo()}
Elabora una FICHA DE TRABAJO para estudiantes de {asig['grado']} ({asig['nivel']}), área {asig['area']}, región {asig['region']}.
Sesión: {sd.get('titulo')}. Propósito: {sd.get('proposito')}
Competencias y criterios:
{_resumen_competencias(sd)}
Entrega {int(n_act)} actividades graduadas (de lo simple a lo complejo), con lenguaje adecuado a la edad y contexto cercano a la región. Cada actividad incluye la respuesta esperada para el docente.
Formato: {{"titulo":"...","instrucciones":"...","actividades":[{{"numero":1,"consigna":"...","respuesta":"..."}}]}}"""
                with st.spinner("Creando la ficha..."):
                    ia, _ = pedir_json(prompt)
                acts = [{"numero": i, "consigna": s(a.get("consigna")), "respuesta": s(a.get("respuesta"))}
                        for i, a in enumerate((ia.get("actividades") if isinstance(ia, dict) else []) or [], 1) if isinstance(a, dict)]
                if not acts:
                    raise RuntimeError("La IA no devolvió actividades. Intenta de nuevo.")
                guardar_doc(uid, aid, "ficha", 1, f"Ficha: {sd.get('titulo')}",
                            {"titulo": s(ia.get("titulo")), "instrucciones": s(ia.get("instrucciones")), "actividades": acts},
                            padre_id=sdoc["id"], normativa=normativa_vigente()[1])
                cobrar(uid, "ficha")
                siguiente_version(ver_key)
                flash("Ficha lista ✅")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo generar: {e}")
    if not doc:
        return
    vista_previa_y_descarga(doc["id"], f"fic_{sdoc['id']}")
    with st.expander("✏️ Editar la ficha"):
        clave = f"fic_{sdoc['id']}_{ver}"
        campo_linea("Título de la ficha", f"{clave}_t", d.get("titulo", ""))
        campo_texto("Indicaciones", f"{clave}_i", d.get("instrucciones", ""), 80)
        items = d.get("actividades", [])
        editor_items(clave, items, CAMPOS_FICHA, lambda i, x: f"Actividad {i + 1}: {s(x.get('consigna'))[:60]}")
        barra_edicion(clave, items, CAMPOS_FICHA, lambda n: {"numero": n, "consigna": "", "respuesta": ""},
                      lambda lista: guardar_doc(uid, aid, "ficha", 1, doc["titulo"],
                                                {"titulo": st.session_state.get(f"{clave}_t", ""),
                                                 "instrucciones": st.session_state.get(f"{clave}_i", ""),
                                                 "actividades": lista}, padre_id=sdoc["id"]), ver_key)


# ------------------------------------------------------------------
# EXAMEN DE LA SESIÓN
# ------------------------------------------------------------------
CAMPOS_EXAMEN = [{"k": "tipo", "label": "Tipo de pregunta", "tipo": "select",
                  "opciones": ["opcion_multiple", "desarrollo", "verdadero_falso"]},
                 {"k": "enunciado", "label": "Pregunta", "tipo": "area", "alto": 80},
                 {"k": "opciones", "label": "Alternativas (una por línea, ej.: a) …)", "tipo": "lineas", "alto": 100},
                 {"k": "respuesta", "label": "Respuesta correcta", "tipo": "linea"},
                 {"k": "puntaje", "label": "Puntaje", "tipo": "linea"}]


def _tab_examen(asig, sdoc):
    sd = _necesita_sesion(sdoc)
    if not sd:
        return
    uid, aid = st.session_state.user_id, asig["id"]
    doc = get_doc(aid, "examen", padre_id=sdoc["id"])
    d = contenido(doc) if doc else {}
    ver_key = f"ver_exa_{sdoc['id']}"
    ver = st.session_state.get(ver_key, 0)
    with st.expander("⚙️ Generar con IA", expanded=not doc):
        c1, c2, c3 = st.columns(3)
        n_preg = c1.number_input("Número de preguntas", 3, 20, 8, key=f"exa_n_{sdoc['id']}")
        tipos = c2.selectbox("Tipo de preguntas", ["Mixto", "Solo opción múltiple", "Solo desarrollo"], key=f"exa_t_{sdoc['id']}")
        total = c3.number_input("Puntaje total", 5, 100, 20, key=f"exa_p_{sdoc['id']}")
        if confirmar("examen", "✨ Generar examen con IA" if not doc else "🔄 Volver a generar el examen",
                     f"exa_{sdoc['id']}", asig=asig):
            try:
                prompt = f"""{preambulo()}
Elabora un EXAMEN para estudiantes de {asig['grado']} ({asig['nivel']}), área {asig['area']}.
Sesión: {sd.get('titulo')}
Competencias y criterios:
{_resumen_competencias(sd)}
Número de preguntas: {int(n_preg)}. Tipo: {tipos}. Puntaje total: {int(total)} (los puntajes de las preguntas deben sumar exactamente {int(total)}).
Para "opcion_multiple": 4 opciones escritas como "a) ...", "b) ...", y "respuesta" con la letra correcta. Para "desarrollo": "opciones" vacía y "respuesta" con la respuesta esperada.
Formato: {{"titulo":"...","instrucciones":"...","preguntas":[{{"numero":1,"tipo":"opcion_multiple","enunciado":"...","opciones":["a) ...","b) ...","c) ...","d) ..."],"respuesta":"b","puntaje":2}}]}}"""
                with st.spinner("Creando el examen..."):
                    ia, _ = pedir_json(prompt)
                pregs = []
                for i, p in enumerate((ia.get("preguntas") if isinstance(ia, dict) else []) or [], 1):
                    if isinstance(p, dict):
                        pregs.append({"numero": i, "tipo": s(p.get("tipo")) or "desarrollo", "enunciado": s(p.get("enunciado")),
                                      "opciones": a_lista(p.get("opciones")), "respuesta": s(p.get("respuesta")),
                                      "puntaje": s(p.get("puntaje")) or "1"})
                if not pregs:
                    raise RuntimeError("La IA no devolvió preguntas. Intenta de nuevo.")
                guardar_doc(uid, aid, "examen", 1, f"Examen: {sd.get('titulo')}",
                            {"titulo": s(ia.get("titulo")), "instrucciones": s(ia.get("instrucciones")), "preguntas": pregs},
                            padre_id=sdoc["id"], normativa=normativa_vigente()[1])
                cobrar(uid, "examen")
                siguiente_version(ver_key)
                flash("Examen listo ✅")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo generar: {e}")
    if not doc:
        return
    vista_previa_y_descarga(doc["id"], f"exa_{sdoc['id']}")
    with st.expander("✏️ Editar el examen"):
        clave = f"exa_{sdoc['id']}_{ver}"
        campo_linea("Título del examen", f"{clave}_t", d.get("titulo", ""))
        campo_texto("Indicaciones", f"{clave}_i", d.get("instrucciones", ""), 80)
        items = d.get("preguntas", [])
        editor_items(clave, items, CAMPOS_EXAMEN, lambda i, x: f"Pregunta {i + 1}: {s(x.get('enunciado'))[:60]}")
        barra_edicion(clave, items, CAMPOS_EXAMEN,
                      lambda n: {"numero": n, "tipo": "desarrollo", "enunciado": "", "opciones": [], "respuesta": "", "puntaje": "1"},
                      lambda lista: guardar_doc(uid, aid, "examen", 1, doc["titulo"],
                                                {"titulo": st.session_state.get(f"{clave}_t", ""),
                                                 "instrucciones": st.session_state.get(f"{clave}_i", ""),
                                                 "preguntas": lista}, padre_id=sdoc["id"]), ver_key)


# ------------------------------------------------------------------
# DESAFÍOS DE APRENDIZAJE (por clase o por unidad)
# ------------------------------------------------------------------
CAMPOS_DESAFIO = [{"k": "nombre", "label": "Nombre del desafío", "tipo": "linea"},
                  {"k": "nivel", "label": "Nivel", "tipo": "select", "opciones": ["Básico", "Intermedio", "Avanzado"]},
                  {"k": "puntos", "label": "Puntos", "tipo": "linea"},
                  {"k": "reto", "label": "El reto", "tipo": "area", "alto": 90},
                  {"k": "pasos", "label": "Pasos (uno por línea)", "tipo": "lineas", "alto": 90},
                  {"k": "producto", "label": "Producto que presentarán", "tipo": "linea"},
                  {"k": "criterios", "label": "Lo lograrás si… (uno por línea)", "tipo": "lineas", "alto": 80}]


def _contexto_desafio(padre, udata, ambito):
    d = contenido(padre)
    if ambito == "unidad":
        temas = "; ".join(f.get("titulo", "") for f in d.get("secuencia", []))
        comps = d.get("propositos", [])
        cab = f"UNIDAD: {d.get('titulo')}\nSituación significativa: {d.get('situacion')}\nTemas de la unidad: {temas}"
    else:
        sug = d.get("competencias_sugeridas") or []
        comps = [c for c in (d.get("competencias") or [])] or [p for p in udata.get("propositos", [])
                                                                if not sug or p["competencia"] in sug]
        cab = f"TEMA (CLASE): {d.get('titulo')}\nPropósito: {d.get('proposito', '')}\nUnidad: {udata.get('titulo')}"
    des = "\n".join(f"- {c.get('competencia')}: " + " | ".join((c.get("desempenos") or [])[:3]) for c in comps)
    return cab + "\nDesempeños oficiales que se desarrollan:\n" + des


def _tab_desafios(asig, padre, udata, ambito):
    uid, aid = st.session_state.user_id, asig["id"]
    doc = get_doc(aid, "desafio", padre_id=padre["id"])
    d = contenido(doc) if doc else {}
    ver_key = f"ver_des_{padre['id']}"
    ver = st.session_state.get(ver_key, 0)
    st.caption("Retos motivadores para tus estudiantes, basados en el tema y en los desempeños oficiales. "
               "Incluyen pasos, producto, criterios de logro y una hoja de seguimiento.")
    with st.expander("⚙️ Generar con IA", expanded=not doc):
        c1, c2 = st.columns(2)
        n = c1.number_input("Número de desafíos", 3, 10, 5, key=f"des_n_{padre['id']}")
        modalidad = c2.selectbox("Modalidad", ["Mixto", "Individual", "En equipos"], key=f"des_m_{padre['id']}")
        if confirmar("desafio", "✨ Crear desafíos con IA" if not doc else "🔄 Volver a crear los desafíos",
                     f"des_{padre['id']}", asig=asig):
            try:
                prompt = f"""{preambulo()}
Crea DESAFÍOS DE APRENDIZAJE para estudiantes de {asig['grado']} ({asig['nivel']}), área {asig['area']}, región {asig['region']}.
{_contexto_desafio(padre, udata, ambito)}
Número de desafíos: {int(n)}. Modalidad: {modalidad}.
Cada desafío es un reto motivador y contextualizado que hace que el estudiante use lo aprendido, con dificultad creciente (Básico, Intermedio, Avanzado).
Formato: {{"titulo":"...","introduccion":"mensaje motivador para los estudiantes","desafios":[{{"numero":1,"nombre":"...","reto":"...","pasos":["..."],"producto":"...","criterios":["..."],"nivel":"Básico","puntos":5}}]}}"""
                with st.spinner("Creando los desafíos..."):
                    ia, _ = pedir_json(prompt)
                lista = [x for x in (ia.get("desafios") if isinstance(ia, dict) else []) or [] if isinstance(x, dict)]
                if not lista:
                    raise RuntimeError("La IA no devolvió desafíos. Intenta de nuevo.")
                desafios = [{"numero": i, "nombre": s(x.get("nombre")), "reto": s(x.get("reto")), "pasos": a_lista(x.get("pasos")),
                             "producto": s(x.get("producto")), "criterios": a_lista(x.get("criterios")),
                             "nivel": s(x.get("nivel")), "puntos": s(x.get("puntos"))} for i, x in enumerate(lista, 1)]
                guardar_doc(uid, aid, "desafio", 1, s(ia.get("titulo")) or f"Desafíos: {contenido(padre).get('titulo')}",
                            {"titulo": s(ia.get("titulo")), "introduccion": s(ia.get("introduccion")),
                             "modalidad": modalidad, "desafios": desafios}, padre_id=padre["id"],
                            normativa=normativa_vigente()[1])
                cobrar(uid, "desafio")
                siguiente_version(ver_key)
                flash("¡Desafíos listos! Descárgalos en Word o edítalos.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo generar: {e}")
    if not doc:
        return
    vista_previa_y_descarga(doc["id"], f"des_{padre['id']}")
    with st.expander("✏️ Editar los desafíos"):
        clave = f"des_{padre['id']}_{ver}"
        campo_linea("Título", f"{clave}_t", d.get("titulo", ""))
        campo_texto("Mensaje para los estudiantes", f"{clave}_i", d.get("introduccion", ""), 80)
        items = d.get("desafios", [])
        editor_items(clave, items, CAMPOS_DESAFIO, lambda i, x: f"Desafío {i + 1}: {s(x.get('nombre'))[:50]}")
        barra_edicion(clave, items, CAMPOS_DESAFIO,
                      lambda n: {"numero": n, "nombre": "", "reto": "", "pasos": [], "producto": "", "criterios": [],
                                 "nivel": "Básico", "puntos": "5"},
                      lambda lista: guardar_doc(uid, aid, "desafio", 1, st.session_state.get(f"{clave}_t", "") or doc["titulo"],
                                                {**d, "titulo": st.session_state.get(f"{clave}_t", ""),
                                                 "introduccion": st.session_state.get(f"{clave}_i", ""),
                                                 "desafios": lista}, padre_id=padre["id"]), ver_key)
