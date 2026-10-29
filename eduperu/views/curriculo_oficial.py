"""Currículo oficial: los lineamientos del MINEDU por curso (solo lectura; la IA no toca este contenido)."""
import streamlit as st

from eduperu.services.curriculo import (GRADOS, NIVELES, areas_de, ciclo_de, competencias_de, desempenos_de, detalle_competencia,
                       estandar_de)
from eduperu.core.db import fetch
from eduperu.ui.components import area_activa


def render():
    st.title("📖 Currículo oficial")
    st.info("💡 Aquí ves los lineamientos oficiales del MINEDU por curso. Son los textos que usa el sistema: "
            "la IA **no** los escribe ni los modifica; solo prepara actividades y materiales a partir de ellos.")

    act = area_activa()
    c1, c2, c3 = st.columns(3)
    niveles = NIVELES
    nivel = c1.selectbox("Nivel", niveles, index=niveles.index(act["nivel"]) if act else 1, key="cur_ver_nivel")
    areas = areas_de(nivel)
    if not areas:
        st.warning("Este nivel todavía no tiene áreas cargadas.")
        return
    area = c2.selectbox("Área", areas, index=areas.index(act["area"]) if act and act["nivel"] == nivel
                        and act["area"] in areas else 0, key="cur_ver_area")
    grados = GRADOS[nivel]
    grado = c3.selectbox("Grado", grados, index=grados.index(act["grado"]) if act and act["nivel"] == nivel
                         and act["grado"] in grados else 0, key="cur_ver_grado")
    ciclo = ciclo_de(nivel, grado)

    comps = competencias_de(nivel, area)
    if not comps:
        st.warning("Esta área todavía no tiene competencias cargadas.")
        return
    verificadas = sum(1 for c in comps if c["verificado"])
    con_des = sum(1 for c in comps if desempenos_de(c["id"], grado))
    if verificadas == len(comps) and con_des == len(comps):
        st.success(f"✅ Currículo verificado para {area} · {grado} (ciclo {ciclo}).")
    else:
        st.warning(f"⚠️ Pendiente de verificación: {verificadas} de {len(comps)} competencias verificadas; "
                   f"{con_des} de {len(comps)} con desempeños cargados para {grado}.")

    for c in comps:
        det = detalle_competencia(c["id"])
        with st.expander(("✅ " if c["verificado"] else "⚠️ ") + c["nombre"]):
            st.markdown("**Capacidades**")
            st.markdown("\n".join(f"- {x}" for x in c["capacidades"]) or "_Sin capacidades cargadas._")
            est = estandar_de(c["id"], ciclo)
            st.markdown(f"**Estándar de aprendizaje (ciclo {ciclo})**")
            st.write(est or "_Aún no cargado._")
            des = desempenos_de(c["id"], grado)
            st.markdown(f"**Desempeños de {grado}**")
            if des:
                st.markdown("\n".join(f"{i}. {d['texto']}" for i, d in enumerate(des, 1)))
            else:
                st.caption("Aún no cargados por el administrador.")
            if det.get("fuente"):
                fecha = f" · verificado el {det['verificado_en']:%d/%m/%Y}" if det.get("verificado_en") else ""
                st.caption(f"Fuente: {det['fuente']}{fecha}")

    with st.expander("📜 Normativa vigente aprobada (MINEDU)"):
        st.caption("Base: RM N.° 501-2025-MINEDU. Estas son las actualizaciones que el administrador revisó y aprobó.")
        filas = fetch("SELECT f.nombre, f.url, v.resumen_cambios, v.aprobado_en FROM normativa_versiones v "
                      "JOIN normativa_fuentes f ON f.id = v.fuente_id WHERE v.estado='aprobada' "
                      "ORDER BY v.aprobado_en DESC LIMIT 10")
        if not filas:
            st.write("Todavía no hay actualizaciones aprobadas; se aplica la RM N.° 501-2025-MINEDU.")
        for f in filas:
            st.markdown(f"**{f['nombre']}** · aprobada el {f['aprobado_en']:%d/%m/%Y}")
            st.caption(f["url"])
            st.write(f["resumen_cambios"])
