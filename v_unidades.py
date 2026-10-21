"""Unidades de aprendizaje: producto, secuencia por semanas, propósitos, enfoques; importar y sincronizar."""
import pandas as pd
import streamlit as st

from curriculo import buscar_competencia, contexto_curricular, transversales
from docx import Document
from ia import generar_texto, pedir_json, preambulo
from normativa import normativa_vigente
from repo import (cobrar, contenido, crear_sesiones_desde_secuencia, get_doc, get_doc_by_id, guardar_doc,
                  listar_docs)
from ui import (PAG_ANUAL, PAG_SESIONES, campo_linea, campo_multi, campo_texto, confirmar, exigir_area,
                exigir_cadena, flash, ir_a, siguiente_version, vista_previa_y_descarga)
from util import a_lista, a_texto, entero, norm, s


# ------------------------------------------------------------------
# Normalización de lo que devuelve la IA (los textos oficiales vienen de la base curricular)
# ------------------------------------------------------------------
def _enfoques(ia_enfoques, enfoques_db):
    por_nombre = {norm(e["nombre"]): e for e in enfoques_db}
    res = []
    for x in ia_enfoques or []:
        if not isinstance(x, dict):
            continue
        e = por_nombre.get(norm(x.get("enfoque")))
        if e and not any(r["enfoque"] == e["nombre"] for r in res):
            res.append({"enfoque": e["nombre"], "valores": ", ".join(e["items"]), "acciones": s(x.get("acciones"))})
    return res


def normalizar_unidad(ia, mapa, ua, semanas, spw):
    """Convierte el JSON de la IA en la unidad final. Desempeños y capacidades salen de la base curricular."""
    prod = ia.get("producto") or {}
    producto = {"evidencia": s(prod.get("evidencia")), "criterios": a_texto(prod.get("criterios")),
                "relacion": s(prod.get("relacion"))}

    props = []
    for p in ia.get("propositos") or []:
        if not isinstance(p, dict):
            continue
        nombre = buscar_competencia(p.get("competencia"), mapa)
        raw = s(p.get("competencia"))
        info = mapa.get(nombre) if nombre else None
        if not info and not raw:
            continue
        caps, des, por_ver = [], [], False
        if info:
            caps = info["comp"]["capacidades"]
            for idx in p.get("desempenos") or []:
                digitos = "".join(ch for ch in str(idx) if ch.isdigit())
                if digitos and 1 <= int(digitos) <= len(info["des"]):
                    des.append(info["des"][int(digitos) - 1]["texto"])
            if not des and info["des"]:
                des = [d["texto"] for d in info["des"][:3]]
        else:
            caps = a_lista(p.get("capacidades"))
        if not des:
            des, por_ver = a_lista(p.get("desempenos_texto")), True
        if nombre and any(x["competencia"] == nombre for x in props):
            continue
        props.append({"competencia": nombre or raw, "capacidades": caps, "desempenos": des, "por_verificar": por_ver,
                      "proposito": s(p.get("proposito")), "campo_tematico": s(p.get("campo_tematico")),
                      "evidencia": s(p.get("evidencia")), "instrumento": s(p.get("instrumento"))})
    for nombre, info in mapa.items():  # toda competencia de la unidad debe tener su fila
        if not any(x["competencia"] == nombre for x in props):
            ds = [d["texto"] for d in info["des"][:3]]
            props.append({"competencia": nombre, "capacidades": info["comp"]["capacidades"], "desempenos": ds,
                          "por_verificar": not ds, "proposito": "", "campo_tematico": "", "evidencia": "",
                          "instrumento": ""})

    primera = next(iter(mapa), "")
    secuencia = []
    for f in ia.get("secuencia") or []:
        if isinstance(f, dict):
            secuencia.append({"semana": entero(f.get("semana"), 1, 1, 20), "titulo": s(f.get("titulo")),
                              "competencia": buscar_competencia(f.get("competencia"), mapa) or primera})
    if not secuencia:
        for sem in range(1, semanas + 1):
            for k in range(spw):
                secuencia.append({"semana": sem, "titulo": f"Sesión {len(secuencia) + 1}", "competencia": primera})

    enfoques = _enfoques(ia.get("enfoques"), transversales()[1])
    return {"numero": ua["numero"], "titulo": s(ia.get("titulo")) or ua["titulo"],
            "situacion": s(ia.get("situacion")) or ua["situacion"], "producto": producto,
            "secuencia": secuencia, "propositos": props, "enfoques": enfoques,
            "semanas": semanas, "sesiones_por_semana": spw}


def _generar_unidad(asig, ua, semanas, spw):
    ctx, mapa = contexto_curricular(asig["nivel"], asig["area"], asig["grado"], ua["competencias"])
    if not mapa:
        raise RuntimeError("La unidad no tiene competencias válidas. Revisa la planificación anual.")
    enfoques = transversales()[1]
    total = semanas * spw
    prompt = f"""{preambulo()}
Elabora una UNIDAD DE APRENDIZAJE.
Datos: nivel {asig['nivel']}, grado {asig['grado']}, área {asig['area']}, región {asig['region']}.
Unidad N.° {ua['numero']}: {ua['titulo']}
Problema identificado: {ua.get('problema') or '-'}
Situación significativa: {ua['situacion']}
Valores observables: {ua.get('valores') or '-'}
Duración: {semanas} semanas, {spw} sesiones por semana (total {total} sesiones).

Competencias, capacidades y desempeños disponibles (D1, D2... son los desempeños; NO los reescribas, solo indica sus números):
{ctx}

Enfoques transversales disponibles (usa nombres EXACTOS): {'; '.join(e['nombre'] for e in enfoques)}

Entrega:
- "titulo": título de la unidad.
- "producto": {{"evidencia": producto o evidencia final de la unidad, "criterios": lista de 3 a 5 criterios de evaluación, "relacion": cómo se relaciona con otras áreas}}
- "secuencia": lista de EXACTAMENTE {total} sesiones, cada una {{"semana": n, "titulo": pregunta o reto en voz del estudiante (ej. "¿Cómo repartimos en partes iguales?"), "competencia": nombre EXACTO}}.
- "propositos": un objeto por competencia: {{"competencia": nombre EXACTO, "desempenos": [números de los D elegidos, p. ej. [1,3]], "desempenos_texto": [solo si no hay D disponibles, 2 desempeños propuestos], "proposito": propósito de aprendizaje, "campo_tematico": contenidos, "evidencia": evidencia, "instrumento": instrumento de evaluación}}
- "enfoques": 2 a 3 objetos {{"enfoque": nombre EXACTO, "acciones": acciones observables concretas para esta unidad}}."""
    ia, _ = pedir_json(prompt)
    if not isinstance(ia, dict):
        raise RuntimeError("La IA devolvió un formato inesperado. Intenta de nuevo.")
    return normalizar_unidad(ia, mapa, ua, semanas, spw)


def _texto_de_docx(archivo):
    doc = Document(archivo)
    partes = [p.text for p in doc.paragraphs if p.text.strip()]
    for t in doc.tables:
        for fila in t.rows:
            partes.append(" | ".join(c.text.strip() for c in fila.cells))
    return "\n".join(partes)[:15000]


def _importar_unidad(asig, ua, texto, semanas, spw):
    ctx, mapa = contexto_curricular(asig["nivel"], asig["area"], asig["grado"], ua["competencias"])
    prompt = f"""{preambulo()}
Tengo una unidad de aprendizaje escrita por un docente. Conviértela al formato indicado SIN inventar contenido nuevo (si falta algo, déjalo vacío).
Competencias de esta unidad: {', '.join(ua['competencias'])}

TEXTO DEL DOCENTE:
{texto}

Formato: {{"titulo": "...", "situacion": "...", "producto": {{"evidencia": "...", "criterios": ["..."], "relacion": "..."}},
"secuencia": [{{"semana": 1, "titulo": "...", "competencia": "..."}}],
"propositos": [{{"competencia": "...", "capacidades": ["..."], "desempenos_texto": ["..."], "proposito": "...", "campo_tematico": "...", "evidencia": "...", "instrumento": "..."}}],
"enfoques": [{{"enfoque": "...", "acciones": "..."}}]}}"""
    ia, _ = pedir_json(prompt)
    if not isinstance(ia, dict):
        raise RuntimeError("La IA devolvió un formato inesperado.")
    for p in ia.get("propositos") or []:  # lo importado se marca "por verificar"
        if isinstance(p, dict):
            p.pop("desempenos", None)
    return normalizar_unidad(ia, mapa, ua, semanas, spw)


# ------------------------------------------------------------------
# Pantalla
# ------------------------------------------------------------------
def render():
    asig = exigir_area()
    aid = asig["id"]
    st.title("📚 Unidades de aprendizaje")
    st.info("💡 Elige una unidad, pulsa **Generar** y revisa. Cada unidad nace de tu planificación anual.")
    anual = get_doc(aid, "anual")
    if not anual:
        exigir_cadena("Primero necesitas tu planificación anual (de ahí salen las unidades).", PAG_ANUAL,
                      "Ir a Planificación anual")
    unidades = contenido(anual).get("unidades") or []
    if not unidades:
        exigir_cadena("Tu planificación anual todavía no tiene unidades. Genera las situaciones significativas.",
                      PAG_ANUAL, "Ir a Planificación anual")
    existentes = {d["numero"] for d in listar_docs(aid, "unidad")}
    num = st.radio("Elige la unidad", [u["numero"] for u in unidades], horizontal=True, key=f"un_sel_{aid}",
                   format_func=lambda n: f"{'✅' if n in existentes else '⬜'} Unidad {n}")
    _unidad(asig, anual, next(u for u in unidades if u["numero"] == num))


def _unidad(asig, anual, ua):
    uid, aid, n = st.session_state.user_id, asig["id"], ua["numero"]
    doc = get_doc(aid, "unidad", numero=n)
    d = contenido(doc) if doc else {}
    ver_key = f"ver_unidad_{aid}_{n}"
    ver = st.session_state.get(ver_key, 0)

    st.subheader(f"Unidad {n}: {ua['titulo']}")
    st.markdown(f"**Situación significativa:** {ua['situacion'] or '_(vacía: complétala en la planificación anual)_'}")
    st.caption("Competencias: " + ", ".join(ua["competencias"]))

    # --- Generar / importar
    with st.container(border=True):
        c1, c2 = st.columns(2)
        semanas = c1.number_input("Semanas de la unidad", 1, 12, entero(d.get("semanas") or ua.get("semanas"), 4, 1, 12),
                                  key=f"sem_{aid}_{n}_{ver}")
        spw = c2.number_input("Sesiones por semana", 1, 8, entero(d.get("sesiones_por_semana"), 3, 1, 8),
                              key=f"spw_{aid}_{n}_{ver}")
        etiqueta = "✨ Generar unidad con IA" if not doc else "🔄 Volver a generar (reemplaza lo actual)"
        if confirmar("unidad", etiqueta, f"unidad_{aid}_{n}"):
            try:
                with st.spinner("Armando la unidad... (puede tardar un minuto)"):
                    nueva = _generar_unidad(asig, ua, int(semanas), int(spw))
                guardar_doc(uid, aid, "unidad", n, f"Unidad {n}: {nueva['titulo']}", nueva,
                            padre_id=anual["id"], normativa=normativa_vigente()[1])
                cobrar(uid, "unidad")
                siguiente_version(ver_key)
                flash("¡Unidad lista! Revisa y ajusta lo que quieras.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo generar: {e}")

        with st.expander("📥 Cargar una unidad que ya tengo en Word"):
            st.caption("Sube tu unidad (.docx) y la IA la ordena en este formato. Lo importado queda marcado «por verificar».")
            archivo = st.file_uploader("Archivo Word", type=["docx"], key=f"up_{aid}_{n}_{ver}")
            if archivo is not None and confirmar("importar", "Convertir mi unidad", f"imp_{aid}_{n}"):
                try:
                    with st.spinner("Leyendo y ordenando tu unidad..."):
                        nueva = _importar_unidad(asig, ua, _texto_de_docx(archivo), int(semanas), int(spw))
                    guardar_doc(uid, aid, "unidad", n, f"Unidad {n}: {nueva['titulo']}", nueva,
                                padre_id=anual["id"], normativa=normativa_vigente()[1])
                    cobrar(uid, "importar")
                    siguiente_version(ver_key)
                    flash("Unidad importada. Revísala con calma.")
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo importar: {e}")

    if not doc:
        st.caption("Aún no hay contenido para esta unidad.")
        return

    # --- Edición
    base = f"u_{aid}_{n}_{ver}"
    st.markdown("### ✏️ Edita tu unidad")
    campo_linea("Título de la unidad", f"{base}_tit", d.get("titulo", ""))
    campo_texto("Situación significativa", f"{base}_sit", d.get("situacion", ""), 150)

    st.markdown("**Producto de aprendizaje**")
    pr = d.get("producto") or {}
    campo_texto("Evidencia (producto final)", f"{base}_pe", pr.get("evidencia", ""), 80)
    campo_texto("Criterios de evaluación (uno por línea)", f"{base}_pc", pr.get("criterios", ""), 110)
    campo_texto("Relación con otras áreas", f"{base}_pr", pr.get("relacion", ""), 80)

    st.markdown("**Secuencia de la unidad** (cada fila es una sesión; puedes agregar, borrar o cambiar títulos)")
    nombres_comp = [p["competencia"] for p in d.get("propositos", [])]
    filas = [{"semana": f.get("semana", 1), "titulo": f.get("titulo", ""),
              "competencia": f.get("competencia") if f.get("competencia") in nombres_comp else (nombres_comp[0] if nombres_comp else "")}
             for f in d.get("secuencia", [])]
    df = pd.DataFrame(filas, columns=["semana", "titulo", "competencia"])
    df["semana"] = pd.to_numeric(df["semana"], errors="coerce").fillna(1).astype(int)
    seq = st.data_editor(df, key=f"{base}_seq", num_rows="dynamic", hide_index=True, column_config={
        "semana": st.column_config.NumberColumn("Semana", min_value=1, max_value=20, step=1),
        "titulo": st.column_config.TextColumn("Título / pregunta retadora", width="large"),
        "competencia": st.column_config.SelectboxColumn("Competencia", options=nombres_comp or [""])})

    st.markdown("**Propósitos de aprendizaje**")
    props = d.get("propositos", [])
    for j, p in enumerate(props):
        with st.expander(p["competencia"], expanded=(j == 0)):
            if p.get("por_verificar"):
                st.caption("⚠️ Desempeños por verificar con el Programa Curricular oficial.")
            campo_texto("Capacidades (una por línea)", f"{base}_p{j}_cap", a_texto(p.get("capacidades")), 90)
            campo_texto("Desempeños (uno por línea)", f"{base}_p{j}_des", a_texto(p.get("desempenos")), 130)
            campo_texto("Propósito de aprendizaje", f"{base}_p{j}_pro", p.get("proposito", ""), 80)
            campo_linea("Campo temático", f"{base}_p{j}_ct", p.get("campo_tematico", ""))
            campo_texto("Evidencia", f"{base}_p{j}_ev", p.get("evidencia", ""), 70)
            campo_linea("Instrumento de evaluación", f"{base}_p{j}_in", p.get("instrumento", ""))

    st.markdown("**Enfoques transversales**")
    enfoques_db = transversales()[1]
    nombres_enf = [e["nombre"] for e in enfoques_db]
    elegidos = campo_multi("Enfoques de esta unidad", f"{base}_enf", nombres_enf,
                           [e["enfoque"] for e in d.get("enfoques", [])])
    previos = {e["enfoque"]: e.get("acciones", "") for e in d.get("enfoques", [])}
    for k, nombre in enumerate(elegidos):
        campo_texto(f"Acciones observables — {nombre}", f"{base}_enf_{k}_{norm(nombre)[:12]}",
                    previos.get(nombre, ""), 70)

    def recoger():
        st_ = st.session_state
        nueva_seq = []
        for _, f in seq.fillna("").iterrows():
            if s(f["titulo"]):
                nueva_seq.append({"semana": entero(f["semana"], 1, 1, 20), "titulo": s(f["titulo"]),
                                  "competencia": s(f["competencia"])})
        nuevos_props = []
        for j, p in enumerate(props):
            nuevos_props.append({**p, "capacidades": a_lista(st_.get(f"{base}_p{j}_cap")),
                                 "desempenos": a_lista(st_.get(f"{base}_p{j}_des")),
                                 "proposito": st_.get(f"{base}_p{j}_pro", ""),
                                 "campo_tematico": st_.get(f"{base}_p{j}_ct", ""),
                                 "evidencia": st_.get(f"{base}_p{j}_ev", ""),
                                 "instrumento": st_.get(f"{base}_p{j}_in", "")})
        nuevos_enf = []
        for k, nombre in enumerate(st_.get(f"{base}_enf", [])):
            e = next((x for x in enfoques_db if x["nombre"] == nombre), None)
            nuevos_enf.append({"enfoque": nombre, "valores": ", ".join(e["items"]) if e else "",
                               "acciones": st_.get(f"{base}_enf_{k}_{norm(nombre)[:12]}", "")})
        return {**d, "titulo": st_.get(f"{base}_tit", d.get("titulo")), "situacion": st_.get(f"{base}_sit", ""),
                "producto": {"evidencia": st_.get(f"{base}_pe", ""), "criterios": st_.get(f"{base}_pc", ""),
                             "relacion": st_.get(f"{base}_pr", "")},
                "secuencia": nueva_seq, "propositos": nuevos_props, "enfoques": nuevos_enf}

    b1, b2, b3 = st.columns(3)
    if b1.button("💾 Guardar unidad", type="primary", key=f"u_save_{aid}_{n}", use_container_width=True):
        nuevo = recoger()
        guardar_doc(uid, aid, "unidad", n, f"Unidad {n}: {nuevo['titulo']}", nuevo, padre_id=anual["id"])
        st.success("Unidad guardada ✅")
    if b2.button("🔄 Sincronizar con la anual", key=f"u_sync_{aid}_{n}", use_container_width=True,
                 help="Trae de la planificación anual la situación significativa y ajusta las competencias."):
        _sincronizar(asig, anual, ua, recoger(), ver_key)
    if b3.button("🧩 Crear sesiones de la secuencia", key=f"u_ses_{aid}_{n}", use_container_width=True,
                 help="Crea una sesión por cada fila de la secuencia, listas para generar."):
        nuevo = recoger()
        gid = guardar_doc(uid, aid, "unidad", n, f"Unidad {n}: {nuevo['titulo']}", nuevo, padre_id=anual["id"])
        creadas = crear_sesiones_desde_secuencia(uid, asig, get_doc_by_id(gid))
        flash(f"Se crearon {creadas} sesión(es). Ahora ve a la pestaña Sesiones.")
        st.rerun()

    with st.expander("🔎 Revisar coherencia con la planificación anual"):
        if confirmar("revision", "Revisar con IA", f"rev_{aid}_{n}"):
            try:
                with st.spinner("Revisando..."):
                    prompt = (f"{preambulo()}\nRevisa la coherencia de esta unidad con su situación en la planificación anual. "
                              f"Anual: título «{ua['titulo']}», competencias {ua['competencias']}, situación: {ua['situacion']}\n"
                              f"Unidad: {recoger()}\n"
                              "Devuelve hasta 8 observaciones breves en viñetas, empezando con ✅ si está bien o ⚠️ si hay que corregir, "
                              "y di cómo corregirlo. No reescribas la unidad.")
                    texto, _ = generar_texto(prompt)
                cobrar(uid, "revision")
                st.session_state[f"rev_txt_{aid}_{n}"] = texto
            except Exception as e:
                st.error(f"No se pudo revisar: {e}")
        if st.session_state.get(f"rev_txt_{aid}_{n}"):
            st.markdown(st.session_state[f"rev_txt_{aid}_{n}"])

    st.divider()
    vista_previa_y_descarga(doc["id"], f"unidad_{aid}_{n}", abierta=False)
    if listar_docs(aid, "sesion", padre_id=doc["id"]):
        st.button("Siguiente: generar las sesiones →", on_click=ir_a, args=(PAG_SESIONES,), type="primary",
                  key=f"u_next_{aid}_{n}")


def _sincronizar(asig, anual, ua, actual, ver_key):
    """Trae la situación de la anual y alinea las filas de propósitos con las competencias de la unidad anual."""
    uid, aid = st.session_state.user_id, asig["id"]
    _, mapa = contexto_curricular(asig["nivel"], asig["area"], asig["grado"], ua["competencias"])
    props = [p for p in actual.get("propositos", []) if p["competencia"] in mapa]
    for nombre, info in mapa.items():
        if not any(p["competencia"] == nombre for p in props):
            ds = [x["texto"] for x in info["des"][:3]]
            props.append({"competencia": nombre, "capacidades": info["comp"]["capacidades"], "desempenos": ds,
                          "por_verificar": not ds, "proposito": "", "campo_tematico": "", "evidencia": "",
                          "instrumento": ""})
    actual["propositos"] = props
    actual["situacion"] = ua["situacion"]
    guardar_doc(uid, aid, "unidad", ua["numero"], f"Unidad {ua['numero']}: {actual.get('titulo', ua['titulo'])}",
                actual, padre_id=anual["id"])
    siguiente_version(ver_key)
    flash("Unidad sincronizada con la planificación anual ✅")
    st.rerun()
