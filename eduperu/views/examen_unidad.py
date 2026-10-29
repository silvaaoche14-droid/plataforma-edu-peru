"""Examen de unidad o bimestral: se arma con los desempeños (de la base oficial) y los temas de las unidades."""
import streamlit as st

from eduperu.core.ia import pedir_json, preambulo
from eduperu.core.normativa import normativa_vigente
from eduperu.core.repo import cobrar, contenido, get_doc, guardar_doc, listar_docs
from eduperu.ui.components import (barra_edicion, campo_linea, campo_texto, confirmar, editor_items, siguiente_version,
                vista_previa_y_descarga)
from eduperu.core.util import a_lista, entero, norm, s


def _contexto(unidades):
    """Texto para la IA + lista numerada de desempeños verificados {n, competencia, texto}."""
    des, lineas = [], []
    for ud in unidades:
        d = contenido(ud)
        temas = "; ".join(f.get("titulo", "") for f in d.get("secuencia", []))
        lineas.append(f"UNIDAD {d.get('numero')}: {d.get('titulo')}\n  Situación: {d.get('situacion', '')}\n  Temas de las sesiones: {temas}")
        for p in d.get("propositos", []):
            lineas.append(f"  Competencia: {p['competencia']} | Campo temático: {p.get('campo_tematico', '')}")
            for texto in p.get("desempenos", []):
                des.append({"n": len(des) + 1, "competencia": p["competencia"], "texto": texto})
                lineas.append(f"    D{len(des)}: {texto}")
    return "\n".join(lineas), des


def generar(asig, unidades, n_preg, tipos, total):
    ctx, des = _contexto(unidades)
    if not des:
        raise RuntimeError("Las unidades elegidas no tienen desempeños. Completa los propósitos de aprendizaje primero.")
    nums = ", ".join(str(ud["numero"]) for ud in unidades)
    prompt = f"""{preambulo()}
Elabora un EXAMEN {'de la unidad' if len(unidades) == 1 else 'bimestral'} para estudiantes de {asig['grado']} ({asig['nivel']}), área {asig['area']}.
Unidades incluidas: {nums}. Número de preguntas: {n_preg}. Tipo: {tipos}. Puntaje total: {total} (los puntajes deben sumar exactamente {total}).

Contenido de las unidades (los desempeños D1, D2... son oficiales; NO los reescribas):
{ctx}

Reglas:
- Cada pregunta evalúa UN desempeño: indica su número en "desempeno" (ej. 3) y el nombre exacto de su competencia en "competencia".
- Reparte las preguntas entre los desempeños y los temas de las unidades.
- "opcion_multiple": 4 opciones "a) ...", "b) ...", y "respuesta" con la letra. "desarrollo": "opciones" vacía y "respuesta" con la respuesta esperada.
- Lenguaje adecuado a la edad y contexto cercano a la región {asig['region']}.
Formato: {{"titulo":"...","instrucciones":"...","preguntas":[{{"numero":1,"tipo":"opcion_multiple","enunciado":"...","opciones":["a) ...","b) ...","c) ...","d) ..."],"respuesta":"b","puntaje":2,"competencia":"...","desempeno":3}}]}}"""
    ia, _ = pedir_json(prompt)
    if not isinstance(ia, dict):
        raise RuntimeError("La IA devolvió un formato inesperado. Intenta de nuevo.")
    por_n = {x["n"]: x for x in des}
    preguntas = []
    for i, p in enumerate(ia.get("preguntas") or [], 1):
        if not isinstance(p, dict):
            continue
        x = por_n.get(entero(p.get("desempeno"), 0))
        preguntas.append({"numero": i, "tipo": s(p.get("tipo")) or "desarrollo", "enunciado": s(p.get("enunciado")),
                          "opciones": a_lista(p.get("opciones")), "respuesta": s(p.get("respuesta")),
                          "puntaje": s(p.get("puntaje")) or "1",
                          "competencia": x["competencia"] if x else s(p.get("competencia")),
                          "desempeno_texto": x["texto"] if x else ""})
    if not preguntas:
        raise RuntimeError("La IA no devolvió preguntas. Intenta de nuevo.")
    titulo = s(ia.get("titulo")) or (f"Examen de la Unidad {nums}" if len(unidades) == 1 else f"Examen bimestral (Unidades {nums})")
    return {"titulo": titulo, "instrucciones": s(ia.get("instrucciones")), "unidades": [ud["numero"] for ud in unidades],
            "preguntas": preguntas}


CAMPOS = [{"k": "tipo", "label": "Tipo de pregunta", "tipo": "select",
           "opciones": ["opcion_multiple", "desarrollo", "verdadero_falso"]},
          {"k": "enunciado", "label": "Pregunta", "tipo": "area", "alto": 80},
          {"k": "opciones", "label": "Alternativas (una por línea, ej.: a) …)", "tipo": "lineas", "alto": 100},
          {"k": "respuesta", "label": "Respuesta correcta", "tipo": "linea"},
          {"k": "puntaje", "label": "Puntaje", "tipo": "linea"},
          {"k": "competencia", "label": "Competencia", "tipo": "lectura"},
          {"k": "desempeno_texto", "label": "Desempeño que evalúa", "tipo": "lectura"}]


def render(asig, udoc):
    uid, aid = st.session_state.user_id, asig["id"]
    st.caption("Se arma con los temas y los desempeños oficiales de las unidades que elijas. Incluye una matriz que "
               "muestra qué desempeño evalúa cada pregunta.")
    todas = listar_docs(aid, "unidad")
    numeros = [u["numero"] for u in todas]
    doc = get_doc(aid, "examen_unidad", numero=udoc["numero"])
    d = contenido(doc) if doc else {}
    ver_key = f"ver_exu_{udoc['id']}"
    ver = st.session_state.get(ver_key, 0)

    with st.expander("⚙️ Generar con IA", expanded=not doc):
        sel = st.multiselect("Unidades que incluye (para un examen bimestral elige varias)", numeros,
                             default=[x for x in d.get("unidades", [udoc["numero"]]) if x in numeros] or [udoc["numero"]],
                             key=f"exu_sel_{udoc['id']}_{ver}", format_func=lambda n: f"Unidad {n}")
        c1, c2, c3 = st.columns(3)
        n_preg = c1.number_input("Número de preguntas", 5, 40, 12, key=f"exu_n_{udoc['id']}")
        tipos = c2.selectbox("Tipo de preguntas", ["Mixto", "Solo opción múltiple", "Solo desarrollo"], key=f"exu_t_{udoc['id']}")
        total = c3.number_input("Puntaje total", 5, 100, 20, key=f"exu_p_{udoc['id']}")
        etiqueta = "✨ Generar examen" if not doc else "🔄 Volver a generar el examen"
        if confirmar("examen_unidad", etiqueta, f"exu_{udoc['id']}", asig=asig):
            try:
                elegidas = [u for u in todas if u["numero"] in sel] or [udoc]
                with st.spinner("Armando el examen con los desempeños de las unidades..."):
                    nuevo = generar(asig, elegidas, int(n_preg), tipos, int(total))
                guardar_doc(uid, aid, "examen_unidad", udoc["numero"], nuevo["titulo"], nuevo, padre_id=udoc["id"],
                            normativa=normativa_vigente()[1])
                cobrar(uid, "examen_unidad")
                siguiente_version(ver_key)
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo generar: {e}")
    if not doc:
        return

    vista_previa_y_descarga(doc["id"], f"exu_{udoc['id']}")
    with st.expander("✏️ Editar el examen"):
        clave = f"exu_{udoc['id']}_{ver}"
        campo_linea("Título del examen", f"{clave}_t", d.get("titulo", ""))
        campo_texto("Indicaciones", f"{clave}_i", d.get("instrucciones", ""), 80)
        items = d.get("preguntas", [])
        editor_items(clave, items, CAMPOS, lambda i, x: f"Pregunta {i + 1}: {s(x.get('enunciado'))[:60]}")
        barra_edicion(clave, items, CAMPOS,
                      lambda n: {"numero": n, "tipo": "desarrollo", "enunciado": "", "opciones": [], "respuesta": "",
                                 "puntaje": "1", "competencia": "", "desempeno_texto": ""},
                      lambda lista: guardar_doc(uid, aid, "examen_unidad", udoc["numero"],
                                                st.session_state.get(f"{clave}_t", "") or doc["titulo"],
                                                {**d, "titulo": st.session_state.get(f"{clave}_t", ""),
                                                 "instrucciones": st.session_state.get(f"{clave}_i", ""),
                                                 "preguntas": lista}, padre_id=udoc["id"]), ver_key)
