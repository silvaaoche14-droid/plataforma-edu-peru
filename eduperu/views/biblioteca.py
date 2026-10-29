"""Mi Biblioteca: todos tus documentos ordenados por área y grado."""
import streamlit as st

from eduperu.core.db import fetch
from eduperu.services.exportar import bloques_de
from eduperu.core.repo import borrar_doc, docs_del_usuario, get_doc_by_id, listar_asignaciones
from eduperu.services.render import COLOR_DEFECTO, a_docx, texto_a_docx
from eduperu.ui.components import MIME_DOCX, PAG_ANUAL, PAG_SESIONES, PAG_UNIDADES, abrir_area, descargar, flash

TIPOS = {"anual": ("📅", "Planificación anual", PAG_ANUAL), "unidad": ("📚", "Unidad", PAG_UNIDADES),
         "sesion": ("📝", "Sesión", PAG_SESIONES), "rubrica": ("📊", "Rúbrica", PAG_SESIONES),
         "ficha": ("📄", "Ficha", PAG_SESIONES), "examen": ("📋", "Examen de sesión", PAG_SESIONES),
         "examen_unidad": ("🧪", "Examen de unidad", PAG_UNIDADES),
         "desafio": ("🏆", "Desafíos", PAG_SESIONES)}
ORDEN = {"anual": 0, "unidad": 1, "sesion": 2, "rubrica": 3, "ficha": 4, "examen": 5, "examen_unidad": 6, "desafio": 7}


def render():
    uid = st.session_state.user_id
    st.title("🗂️ Mi biblioteca")
    st.caption("Todos tus documentos, organizados por área y grado. Descárgalos en Word cuando los necesites.")
    asigs = listar_asignaciones(uid)
    if not asigs:
        st.info("Cuando crees documentos aparecerán aquí.")
    filtro = st.selectbox("Mostrar", ["Todos los documentos"] + list(TIPOS), key="bib_filtro",
                          format_func=lambda k: k if k.startswith("Todos") else f"{TIPOS[k][0]} {TIPOS[k][1]}")
    todos = docs_del_usuario(uid)
    for a in asigs:
        docs = [d for d in todos if d["asignacion_id"] == a["id"] and (filtro.startswith("Todos") or d["tipo"] == filtro)]
        docs.sort(key=lambda d: (ORDEN.get(d["tipo"], 9), d["numero"], d["id"]))
        titulo = f"{a['area']} · {a['grado']} · Sección {a['seccion'] or '—'}  ({len(docs)} documentos)"
        with st.expander(titulo, expanded=len(asigs) == 1):
            if not docs:
                st.caption("Todavía no hay documentos en esta área.")
            for d in docs:
                icono, nombre, pagina = TIPOS.get(d["tipo"], ("📄", d["tipo"], PAG_ANUAL))
                c1, c2, c3, c4 = st.columns([5, 2, 2, 1])
                c1.markdown(f"{icono} **{nombre}** — {d['titulo'] or ''}")
                c1.caption(f"Actualizado: {d['actualizado_en']:%d/%m/%Y %H:%M}")
                kb = f"bib_bytes_{d['id']}"
                if c2.button("📄 Preparar Word", key=f"prep_{d['id']}"):
                    completo = get_doc_by_id(d["id"])
                    bloques, horizontal, archivo = bloques_de(completo)
                    st.session_state[kb] = (a_docx(bloques, d.get("color") or COLOR_DEFECTO, d.get("normativa_usada"),
                                                   horizontal), archivo)
                if kb in st.session_state:
                    datos, archivo = st.session_state[kb]
                    descargar("⬇️ Descargar", datos, archivo, MIME_DOCX, f"dlb_{d['id']}")
                c3.button("Abrir curso", key=f"op_{d['id']}", on_click=abrir_area, args=(a["id"], pagina))
                if c4.button("🗑️", key=f"del_{d['id']}", help="Eliminar (también lo que depende de él)"):
                    st.session_state[f"_del_{d['id']}"] = True
                if st.session_state.get(f"_del_{d['id']}"):
                    st.warning("¿Eliminar este documento y lo que depende de él? No se puede deshacer.")
                    y, n = st.columns(2)
                    if y.button("Sí, eliminar", key=f"dely_{d['id']}"):
                        borrar_doc(d["id"])
                        st.session_state.pop(f"_del_{d['id']}", None)
                        flash("Documento eliminado.")
                        st.rerun()
                    if n.button("Cancelar", key=f"deln_{d['id']}"):
                        st.session_state.pop(f"_del_{d['id']}", None)
                        st.rerun()

    antiguos = fetch("SELECT id, titulo, contenido_texto, normativa_usada, creado_en FROM planificaciones "
                     "WHERE usuario_id=%s ORDER BY creado_en DESC LIMIT 30", (uid,))
    if antiguos:
        with st.expander(f"🕰️ Documentos del generador anterior ({len(antiguos)})"):
            for d in antiguos:
                st.markdown(f"**{d['titulo']}** · {d['creado_en']:%d/%m/%Y}")
                descargar("⬇️ Word", texto_a_docx(d["titulo"], d["contenido_texto"], d["normativa_usada"]),
                          f"documento_{d['id']}.docx", MIME_DOCX, f"old_{d['id']}")
