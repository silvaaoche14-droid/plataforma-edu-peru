"""Mi Biblioteca: todos tus documentos ordenados por área y grado."""
import streamlit as st

from db import fetch
from exportar import bloques_de
from repo import borrar_doc, get_asignacion, listar_asignaciones, listar_docs
from render import COLOR_DEFECTO, a_docx, texto_a_docx
from ui import MIME_DOCX, PAG_ANUAL, PAG_SESIONES, PAG_UNIDADES, abrir_area, flash

TIPOS = {"anual": ("📅", "Planificación anual", PAG_ANUAL), "unidad": ("📚", "Unidad", PAG_UNIDADES),
         "sesion": ("📝", "Sesión", PAG_SESIONES), "rubrica": ("📊", "Rúbrica", PAG_SESIONES),
         "ficha": ("📄", "Ficha", PAG_SESIONES), "examen": ("📋", "Examen", PAG_SESIONES)}
ORDEN = {"anual": 0, "unidad": 1, "sesion": 2, "rubrica": 3, "ficha": 4, "examen": 5}


def render():
    uid = st.session_state.user_id
    st.title("🗂️ Mi Biblioteca")
    st.caption("Todos tus documentos, organizados por área y grado. Descárgalos en Word cuando los necesites.")
    asigs = listar_asignaciones(uid)
    if not asigs:
        st.info("Cuando crees documentos aparecerán aquí.")
    filtro = st.selectbox("Mostrar", ["Todos los documentos"] + list(TIPOS), key="bib_filtro",
                          format_func=lambda k: k if k.startswith("Todos") else f"{TIPOS[k][0]} {TIPOS[k][1]}")
    for a in asigs:
        docs = listar_docs(a["id"], None if filtro.startswith("Todos") else filtro)
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
                    bloques, horizontal, archivo = bloques_de(d)
                    st.session_state[kb] = (a_docx(bloques, d.get("color") or COLOR_DEFECTO, d.get("normativa_usada"),
                                                   horizontal), archivo)
                if kb in st.session_state:
                    datos, archivo = st.session_state[kb]
                    c2.download_button("⬇️ Descargar", data=datos, file_name=archivo, mime=MIME_DOCX, key=f"dlb_{d['id']}")
                c3.button("Abrir área", key=f"op_{d['id']}", on_click=abrir_area, args=(a["id"], pagina))
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
                st.download_button("⬇️ Word", data=texto_a_docx(d["titulo"], d["contenido_texto"], d["normativa_usada"]),
                                   file_name=f"documento_{d['id']}.docx", mime=MIME_DOCX, key=f"old_{d['id']}")
