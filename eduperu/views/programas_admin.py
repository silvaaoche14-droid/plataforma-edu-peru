"""Administración: buscar, leer y cargar los Programas Curriculares oficiales (PDF) con verificación."""
import pandas as pd
import streamlit as st

from eduperu.services.curriculo import NIVELES, areas_de
from eduperu.core.db import execute, fetch
from eduperu.services.programas import (aprobar, buscar_programas, descargar_y_leer, extraer, leer_subido, pendientes, registrar_url,
                       rechazar)

ESTADOS = {"nuevo": "🆕 Nuevo", "leido": "📖 Leído", "actualizado": "🔄 Actualizado en gob.pe", "descartado": "🚫 Descartado"}


def render():
    st.caption("El sistema revisa las páginas oficiales del MINEDU en gob.pe y trae los PDF de los Programas Curriculares. "
               "La IA **no navega por internet**: solo ayuda a clasificar y a ordenar el texto, y todo lo que extrae "
               "se comprueba contra el PDF. Nada pasa a los docentes sin tu aprobación.")

    # ---------------- 1. Buscar
    st.markdown("### ① Buscar en el MINEDU")
    if st.button("🔎 Buscar Programas Curriculares en gob.pe", type="primary", key="prog_buscar"):
        with st.spinner("Revisando las páginas oficiales..."):
            try:
                lista, avisos = buscar_programas()
                for a in avisos:
                    st.warning(a)
                st.success(f"Listo. Hay {len(lista)} documento(s) registrados.")
            except Exception as e:
                st.error(f"No se pudo buscar: {e}")
    with st.expander("Otras formas de traer un PDF (pegar enlace o subir archivo)"):
        c1, c2 = st.columns(2)
        url = c1.text_input("Enlace directo al PDF", key="prog_url", placeholder="https://cdn.www.gob.pe/uploads/...pdf")
        nivel_url = c1.selectbox("Nivel del documento", [""] + NIVELES, key="prog_url_nivel")
        if c1.button("➕ Agregar enlace", key="prog_url_btn") and url.startswith("http"):
            registrar_url(url.strip(), nivel=nivel_url)
            st.rerun()
        archivo = c2.file_uploader("…o sube el PDF", type=["pdf"], key="prog_subir")
        nivel_sub = c2.selectbox("Nivel del documento", [""] + NIVELES, key="prog_sub_nivel")
        if archivo is not None and c2.button("📥 Leer este PDF", key="prog_sub_btn"):
            try:
                with st.spinner("Leyendo el PDF (puede tardar)..."):
                    _, n = leer_subido(archivo.name, archivo.getvalue(), nivel_sub)
                st.success(f"PDF leído: {n} páginas.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo leer: {e}")

    docs = fetch("SELECT * FROM curriculo_pdf WHERE estado<>'descartado' ORDER BY id DESC")
    if not docs:
        st.info("Aún no hay documentos. Pulsa «Buscar» o agrega un enlace.")
        return
    st.dataframe(pd.DataFrame([{"id": d["id"], "estado": ESTADOS.get(d["estado"], d["estado"]), "nivel": d["nivel"],
                                "título": d["titulo"], "páginas": d["paginas"], "leído": d["leido_en"]} for d in docs]),
                 hide_index=True)

    # ---------------- 2. Leer
    st.markdown("### ② Descargar y leer el PDF")
    ids = [d["id"] for d in docs]
    pid = st.selectbox("Documento", ids, key="prog_sel", format_func=lambda i: next(
        f"{d['id']} · {d['nivel'] or '¿nivel?'} · {(d['titulo'] or d['url'])[:70]}" for d in docs if d["id"] == i))
    doc = next(d for d in docs if d["id"] == pid)
    if doc["estado"] == "actualizado":
        st.warning("Este PDF cambió en gob.pe desde la última lectura. Vuelve a leerlo y a extraer.")
    if not doc["url"].startswith("subido:"):
        if st.button("⬇️ Descargar y leer", key=f"prog_leer_{pid}"):
            try:
                with st.spinner("Descargando y leyendo el PDF..."):
                    n = descargar_y_leer(pid)
                st.success(f"Leído: {n} páginas.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo leer: {e}")
    if doc["estado"] not in ("leido", "actualizado") or not doc["paginas"]:
        st.caption("Cuando el PDF esté leído podrás extraer los desempeños.")
        return

    # ---------------- 3. Extraer
    st.markdown("### ③ Extraer desempeños y estándares (IA + verificación contra el PDF)")
    nivel = st.selectbox("Nivel a extraer", NIVELES, key="prog_nivel",
                         index=NIVELES.index(doc["nivel"]) if doc["nivel"] in NIVELES else 1)
    areas = areas_de(nivel)
    sel = st.multiselect("Áreas (vacío = todas)", areas, key=f"prog_areas_{nivel}")
    if st.button("🤖 Extraer y verificar", type="primary", key=f"prog_ext_{pid}"):
        barra = st.progress(0.0)
        try:
            res = extraer(pid, nivel, sel or None, lambda f, t: barra.progress(min(f, 1.0), text=t))
            st.success(f"Verificados contra el PDF: {res['verificados']} · descartados por no aparecer en el PDF: "
                       f"{res['descartados']}")
            if res["sin_paginas"]:
                with st.expander(f"No se encontraron páginas para {len(res['sin_paginas'])} competencia(s)"):
                    st.write("\n".join(f"- {x}" for x in res["sin_paginas"]))
        except Exception as e:
            st.error(f"No se pudo extraer: {e}")

    # ---------------- 4. Revisar y aprobar
    st.markdown("### ④ Revisar y aprobar")
    pend = pendientes(pid)
    if not pend:
        st.success("No hay textos pendientes de revisión en este documento.")
        return
    st.caption(f"{len(pend)} texto(s) pendientes. Marca «aprobar» solo los que coinciden con el documento oficial. "
               "Puedes corregir el texto antes de aprobar.")
    df = pd.DataFrame([{"aprobar": True, "id": p["id"], "área": p["area"], "competencia": p["competencia"][:50],
                        "tipo": p["tipo"], "grado/ciclo": p["grado"], "página": p["pagina"], "texto": p["texto"]}
                       for p in pend])
    ed = st.data_editor(df, key=f"prog_rev_{pid}_{len(pend)}", hide_index=True, disabled=["id", "área", "competencia",
                        "tipo", "grado/ciclo", "página"])
    marcar = st.checkbox("Marcar como «verificadas» las competencias aprobadas", value=True, key=f"prog_ver_{pid}")
    c1, c2 = st.columns(2)
    if c1.button("✅ Aprobar los marcados", type="primary", key=f"prog_apr_{pid}"):
        for _, r in ed.iterrows():
            if r["aprobar"]:
                execute("UPDATE curriculo_importado SET texto=%s WHERE id=%s", (str(r["texto"]).strip(), int(r["id"])))
        n = aprobar([int(r["id"]) for _, r in ed.iterrows() if r["aprobar"]], marcar,
                    doc["titulo"] or doc["url"])
        st.success(f"Se aprobaron {n} texto(s) y ya están disponibles para los docentes.")
        st.rerun()
    if c2.button("🗑️ Rechazar los desmarcados", key=f"prog_rec_{pid}"):
        rechazar([int(r["id"]) for _, r in ed.iterrows() if not r["aprobar"]])
        st.rerun()
