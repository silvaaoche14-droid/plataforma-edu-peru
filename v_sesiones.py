"""Sesiones de aprendizaje + rúbrica, ficha de trabajo y examen de cada sesión."""
import pandas as pd
import streamlit as st

from ia import pedir_json, preambulo
from normativa import normativa_vigente
from repo import cobrar, contenido, crear_sesiones_desde_secuencia, get_doc, get_doc_by_id, guardar_doc, listar_docs
from ui import (PAG_ANUAL, PAG_UNIDADES, campo_linea, campo_multi, campo_num, campo_texto, confirmar, exigir_area,
                exigir_cadena, flash, siguiente_version, vista_previa_y_descarga)
from util import a_lista, a_texto, entero, norm, s


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
# PANTALLA
# ------------------------------------------------------------------
def render():
    asig = exigir_area()
    uid, aid = st.session_state.user_id, asig["id"]
    st.title("📝 Sesiones de aprendizaje")
    st.info("💡 Elige la unidad y la sesión. En cada sesión tienes 4 pestañas: contenido, rúbrica, ficha y examen.")
    if not get_doc(aid, "anual"):
        exigir_cadena("Primero crea tu planificación anual.", PAG_ANUAL, "Ir a Planificación anual")
    unidades = listar_docs(aid, "unidad")
    if not unidades:
        exigir_cadena("Primero crea al menos una unidad.", PAG_UNIDADES, "Ir a Unidades")

    num = st.radio("Unidad", [u["numero"] for u in unidades], horizontal=True, key=f"se_unidad_{aid}",
                   format_func=lambda n: f"Unidad {n}")
    udoc = next(u for u in unidades if u["numero"] == num)
    udata = contenido(udoc)
    sesiones = listar_docs(aid, "sesion", padre_id=udoc["id"])
    if not sesiones:
        st.warning("Esta unidad todavía no tiene sesiones. Créalas desde la secuencia de la unidad.")
        if udata.get("secuencia") and st.button("🧩 Crear sesiones de la secuencia", type="primary", key=f"se_crear_{udoc['id']}"):
            creadas = crear_sesiones_desde_secuencia(uid, asig, udoc)
            flash(f"Se crearon {creadas} sesión(es).")
            st.rerun()
        st.stop()

    def etiqueta(i):
        sd = contenido(sesiones[i])
        return f"{'✅' if sd.get('inicio') else '⬜'} Sesión {sesiones[i]['numero']}: {sd.get('titulo', '')}"

    _masivo(asig, udoc, udata, sesiones)

    idx = st.selectbox("Sesión", list(range(len(sesiones))), format_func=etiqueta, key=f"se_sel_{udoc['id']}")
    sdoc = sesiones[idx]
    t1, t2, t3, t4 = st.tabs(["📖 Contenido de sesión", "📊 Rúbrica", "📄 Ficha de trabajo", "📋 Examen"])
    with t1:
        _tab_contenido(asig, udoc, udata, sdoc)
    with t2:
        _tab_rubrica(asig, sdoc)
    with t3:
        _tab_ficha(asig, sdoc)
    with t4:
        _tab_examen(asig, sdoc)


def _masivo(asig, udoc, udata, sesiones):
    uid = st.session_state.user_id
    faltan = [x for x in sesiones if not contenido(x).get("inicio")]
    with st.expander(f"⚡ Generar todas las sesiones de la unidad ({len(faltan)} pendientes)"):
        if not faltan:
            st.success("Todas las sesiones de esta unidad ya tienen contenido.")
            return
        dur = st.number_input("Duración de cada sesión (minutos)", 20, 240, 90, step=5, key=f"mas_dur_{udoc['id']}")
        if confirmar("sesion", f"Generar las {len(faltan)} sesiones", f"mas_{udoc['id']}", veces=len(faltan)):
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
# PESTAÑA 1: CONTENIDO
# ------------------------------------------------------------------
def _tab_contenido(asig, udoc, udata, sdoc):
    uid, aid = st.session_state.user_id, asig["id"]
    d = contenido(sdoc)
    ver_key = f"ver_ses_{sdoc['id']}"
    ver = st.session_state.get(ver_key, 0)
    props = [p["competencia"] for p in udata.get("propositos", [])]

    c1, c2 = st.columns(2)
    duracion = c1.number_input("Duración (minutos)", 20, 240, entero(d.get("duracion"), 90, 20, 240), step=5,
                               key=f"ses_dur_{sdoc['id']}_{ver}")
    sel = c2.multiselect("Competencias de esta sesión", props,
                         default=[x for x in (d.get("competencias_sugeridas") or props[:1]) if x in props],
                         key=f"ses_comp_{sdoc['id']}_{ver}")
    notas = st.text_input("Indicaciones especiales (opcional)", key=f"ses_notas_{sdoc['id']}_{ver}",
                          placeholder="Ej.: aula multigrado, sin proyector, usar material reciclable")
    etiqueta = "✨ Generar sesión con IA" if not d.get("inicio") else "🔄 Volver a generar (reemplaza lo actual)"
    if confirmar("sesion", etiqueta, f"ses_{sdoc['id']}"):
        try:
            with st.spinner("Creando la sesión..."):
                nuevo = generar_sesion(asig, udata, d, int(duracion), sel, notas)
            guardar_doc(uid, aid, "sesion", sdoc["numero"], f"Sesión {sdoc['numero']}: {nuevo['titulo']}", nuevo,
                        padre_id=udoc["id"], normativa=normativa_vigente()[1])
            cobrar(uid, "sesion")
            siguiente_version(ver_key)
            flash("¡Sesión lista! Revísala y ajústala.")
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo generar: {e}")

    if not d.get("inicio"):
        st.caption("Aún no hay contenido en esta sesión.")
        return

    base = f"s_{sdoc['id']}_{ver}"
    campo_linea("Título de la sesión", f"{base}_tit", d.get("titulo", ""))
    campo_texto("Propósito de aprendizaje", f"{base}_pro", d.get("proposito", ""), 80)
    filas = d.get("competencias", [])
    for j, c in enumerate(filas):
        with st.expander(f"Competencia: {c['competencia']}", expanded=(j == 0)):
            if c.get("por_verificar"):
                st.caption("⚠️ Desempeños por verificar con el Programa Curricular oficial.")
            campo_texto("Criterios de evaluación (uno por línea)", f"{base}_c{j}_cr", a_texto(c.get("criterios")), 100)
            campo_texto("Evidencia de aprendizaje", f"{base}_c{j}_ev", c.get("evidencia", ""), 70)
            campo_linea("Instrumento", f"{base}_c{j}_in", c.get("instrumento", ""))
    st.markdown("**Secuencia didáctica**")
    for k, nombre in (("inicio", "Inicio"), ("desarrollo", "Desarrollo"), ("cierre", "Cierre")):
        m = d.get(k) or {}
        campo_texto(f"{nombre}", f"{base}_{k}_a", m.get("actividades", ""), 140 if k == "desarrollo" else 100)
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
        st.success("Sesión guardada ✅")
    st.divider()
    vista_previa_y_descarga(sdoc["id"], f"sesion_{sdoc['id']}", abierta=False)


# ------------------------------------------------------------------
# PESTAÑAS 2-4: MATERIALES (rúbrica, ficha, examen)
# ------------------------------------------------------------------
def _necesita_sesion(sdoc):
    sd = contenido(sdoc)
    if not sd.get("inicio"):
        st.info("Primero genera el **contenido de la sesión** (pestaña 1); de ahí salen los criterios y las evidencias.")
        return None
    return sd


def _tabla(filas, columnas, clave, config=None):
    df = pd.DataFrame(filas, columns=columnas)
    return st.data_editor(df, key=clave, num_rows="dynamic", hide_index=True, column_config=config or {}).fillna("")


def _tab_rubrica(asig, sdoc):
    sd = _necesita_sesion(sdoc)
    if not sd:
        return
    uid, aid = st.session_state.user_id, asig["id"]
    doc = get_doc(aid, "rubrica", padre_id=sdoc["id"])
    d = contenido(doc) if doc else {}
    ver_key = f"ver_rub_{sdoc['id']}"
    ver = st.session_state.get(ver_key, 0)
    if confirmar("rubrica", "✨ Generar rúbrica con IA" if not doc else "🔄 Volver a generar la rúbrica", f"rub_{sdoc['id']}"):
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
            filas = [{"criterio": s(r.get("criterio")), "AD": s(r.get("AD")), "A": s(r.get("A")), "B": s(r.get("B")),
                      "C": s(r.get("C"))} for r in (lista or []) if isinstance(r, dict)]
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
    ed = _tabla(d.get("criterios", []), ["criterio", "AD", "A", "B", "C"], f"rub_ed_{sdoc['id']}_{ver}", {
        "criterio": st.column_config.TextColumn("Criterio", width="medium"),
        "AD": st.column_config.TextColumn("AD · Destacado", width="medium"),
        "A": st.column_config.TextColumn("A · Esperado", width="medium"),
        "B": st.column_config.TextColumn("B · En proceso", width="medium"),
        "C": st.column_config.TextColumn("C · En inicio", width="medium")})
    if st.button("💾 Guardar rúbrica", type="primary", key=f"rub_save_{sdoc['id']}"):
        filas = [{k: s(r[k]) for k in ("criterio", "AD", "A", "B", "C")} for _, r in ed.iterrows() if s(r["criterio"])]
        guardar_doc(uid, aid, "rubrica", 1, doc["titulo"], {"criterios": filas}, padre_id=sdoc["id"])
        st.success("Rúbrica guardada ✅")
    st.divider()
    vista_previa_y_descarga(doc["id"], f"rub_{sdoc['id']}", abierta=False)


def _tab_ficha(asig, sdoc):
    sd = _necesita_sesion(sdoc)
    if not sd:
        return
    uid, aid = st.session_state.user_id, asig["id"]
    doc = get_doc(aid, "ficha", padre_id=sdoc["id"])
    d = contenido(doc) if doc else {}
    ver_key = f"ver_fic_{sdoc['id']}"
    ver = st.session_state.get(ver_key, 0)
    n_act = st.number_input("Número de actividades", 3, 12, 6, key=f"fic_n_{sdoc['id']}")
    if confirmar("ficha", "✨ Generar ficha con IA" if not doc else "🔄 Volver a generar la ficha", f"fic_{sdoc['id']}"):
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
    base = f"fic_{sdoc['id']}_{ver}"
    campo_linea("Título de la ficha", f"{base}_t", d.get("titulo", ""))
    campo_texto("Indicaciones", f"{base}_i", d.get("instrucciones", ""), 80)
    ed = _tabla(d.get("actividades", []), ["numero", "consigna", "respuesta"], f"{base}_ed", {
        "numero": st.column_config.NumberColumn("N.°", step=1),
        "consigna": st.column_config.TextColumn("Consigna", width="large"),
        "respuesta": st.column_config.TextColumn("Respuesta esperada (docente)", width="medium")})
    if st.button("💾 Guardar ficha", type="primary", key=f"fic_save_{sdoc['id']}"):
        acts = [{"numero": k, "consigna": s(r["consigna"]), "respuesta": s(r["respuesta"])}
                for k, (_, r) in enumerate(ed.iterrows(), 1) if s(r["consigna"])]
        guardar_doc(uid, aid, "ficha", 1, doc["titulo"],
                    {"titulo": st.session_state.get(f"{base}_t", ""), "instrucciones": st.session_state.get(f"{base}_i", ""),
                     "actividades": acts}, padre_id=sdoc["id"])
        st.success("Ficha guardada ✅")
    st.divider()
    vista_previa_y_descarga(doc["id"], f"fic_{sdoc['id']}", abierta=False)


def _tab_examen(asig, sdoc):
    sd = _necesita_sesion(sdoc)
    if not sd:
        return
    uid, aid = st.session_state.user_id, asig["id"]
    doc = get_doc(aid, "examen", padre_id=sdoc["id"])
    d = contenido(doc) if doc else {}
    ver_key = f"ver_exa_{sdoc['id']}"
    ver = st.session_state.get(ver_key, 0)
    c1, c2, c3 = st.columns(3)
    n_preg = c1.number_input("Número de preguntas", 3, 20, 8, key=f"exa_n_{sdoc['id']}")
    tipos = c2.selectbox("Tipo de preguntas", ["Mixto", "Solo opción múltiple", "Solo desarrollo"], key=f"exa_t_{sdoc['id']}")
    total = c3.number_input("Puntaje total", 5, 100, 20, key=f"exa_p_{sdoc['id']}")
    if confirmar("examen", "✨ Generar examen con IA" if not doc else "🔄 Volver a generar el examen", f"exa_{sdoc['id']}"):
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
    base = f"exa_{sdoc['id']}_{ver}"
    campo_linea("Título del examen", f"{base}_t", d.get("titulo", ""))
    campo_texto("Indicaciones", f"{base}_i", d.get("instrucciones", ""), 80)
    filas = [{"numero": p.get("numero"), "tipo": p.get("tipo"), "enunciado": p.get("enunciado"),
              "opciones": " | ".join(p.get("opciones") or []), "respuesta": p.get("respuesta"), "puntaje": p.get("puntaje")}
             for p in d.get("preguntas", [])]
    ed = _tabla(filas, ["numero", "tipo", "enunciado", "opciones", "respuesta", "puntaje"], f"{base}_ed", {
        "numero": st.column_config.NumberColumn("N.°", step=1),
        "tipo": st.column_config.SelectboxColumn("Tipo", options=["opcion_multiple", "desarrollo", "verdadero_falso"]),
        "enunciado": st.column_config.TextColumn("Enunciado", width="large"),
        "opciones": st.column_config.TextColumn("Opciones (separadas por |)", width="large"),
        "respuesta": st.column_config.TextColumn("Respuesta"),
        "puntaje": st.column_config.TextColumn("Puntaje")})
    if st.button("💾 Guardar examen", type="primary", key=f"exa_save_{sdoc['id']}"):
        pregs = []
        for k, (_, r) in enumerate(ed.iterrows(), 1):
            if s(r["enunciado"]):
                pregs.append({"numero": k, "tipo": s(r["tipo"]) or "desarrollo", "enunciado": s(r["enunciado"]),
                              "opciones": [x.strip() for x in s(r["opciones"]).split("|") if x.strip()],
                              "respuesta": s(r["respuesta"]), "puntaje": s(r["puntaje"]) or "1"})
        guardar_doc(uid, aid, "examen", 1, doc["titulo"],
                    {"titulo": st.session_state.get(f"{base}_t", ""), "instrucciones": st.session_state.get(f"{base}_i", ""),
                     "preguntas": pregs}, padre_id=sdoc["id"])
        st.success("Examen guardado ✅")
    st.divider()
    vista_previa_y_descarga(doc["id"], f"exa_{sdoc['id']}", abierta=False)
