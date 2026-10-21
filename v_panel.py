"""Mi Panel: áreas asignadas del docente y guía rápida."""
import streamlit as st

from curriculo import GRADOS, NIVELES, REGIONES, areas_de, estado_area
from repo import borrar_asignacion, crear_asignacion, get_usuario, listar_asignaciones, resumen_asignacion
from ui import PAG_ANUAL, abrir_area, flash


def _pasos(aid):
    r = resumen_asignacion(aid)
    marca = lambda ok: "✅" if ok else "⬜"
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"**1. Tu área** ✅\n\nYa la creaste")
    c2.markdown(f"**2. Planificación anual** {marca(r.get('anual'))}\n\nSituaciones y unidades")
    c3.markdown(f"**3. Unidades** {marca(r.get('unidad'))}\n\n{r.get('unidad', 0)} creadas")
    c4.markdown(f"**4. Sesiones y materiales** {marca(r.get('sesion'))}\n\n{r.get('sesion', 0)} sesiones")


def _crear_area_cb(uid):
    """Se ejecuta ANTES de redibujar la página (así se puede cambiar el área activa sin errores)."""
    ss = st.session_state
    if not ss.get("na_area"):
        flash("No hay áreas para este nivel. Pide al administrador que cargue el currículo.", "error")
        return
    nuevo = crear_asignacion(uid, {"ciclo_escolar": int(ss.get("na_ciclo", 2026)),
                                   "institucion": (ss.get("na_inst") or "").strip(),
                                   "director": (ss.get("na_dir") or "").strip(),
                                   "docente": (ss.get("na_doc") or "").strip(), "region": ss.get("na_region", "Lima"),
                                   "nivel": ss["na_nivel"], "grado": ss["na_grado"], "area": ss["na_area"],
                                   "seccion": (ss.get("na_seccion") or "").strip()})
    ss["area_id"] = nuevo
    flash(f"¡Listo! Creaste {ss['na_area']} · {ss['na_grado']}. Sigue con la planificación anual.")


def _borrar_area_cb():
    ss = st.session_state
    if not ss.get("del_area_ok"):
        flash("Marca la casilla para confirmar que quieres eliminarla.", "warning")
        return
    elegida = ss.get("del_area_sel")
    borrar_asignacion(elegida)
    if ss.get("area_id") == elegida:
        ss["area_id"] = None
    ss["del_area_ok"] = False
    flash("Área eliminada.")


def render():
    uid = st.session_state.user_id
    u = get_usuario(uid)
    st.title(f"👋 ¡Hola, {u['nombre'].split()[0]}!")
    st.caption("Aquí empiezas. Crea tus áreas (el curso que enseñas) y sigue los pasos: Anual → Unidades → Sesiones.")

    asigs = listar_asignaciones(uid)

    if not asigs:
        st.info("💡 **Empieza aquí:** crea tu primera área abajo. Solo toma un minuto y luego todo se llena solo.")
    else:
        activa = st.session_state.get("area_id")
        if activa:
            actual = next((a for a in asigs if a["id"] == activa), None)
            if actual:
                st.subheader(f"Tu ruta en: {actual['area']} · {actual['grado']}")
                _pasos(actual["id"])
                st.button("Continuar con la planificación anual →", on_click=abrir_area,
                          args=(actual["id"], PAG_ANUAL), type="primary")
                st.divider()

        st.subheader("📌 Mis áreas asignadas")
        for nivel in NIVELES:
            grupo = [a for a in asigs if a["nivel"] == nivel]
            if not grupo:
                continue
            st.markdown(f"##### {nivel}")
            cols = st.columns(3)
            for i, a in enumerate(grupo):
                with cols[i % 3]:
                    with st.container(border=True):
                        st.markdown(f"**{a['area']}**")
                        st.caption(f"{a['grado']} · Sección {a['seccion'] or '—'} · {a['ciclo_escolar']}")
                        r = resumen_asignacion(a["id"])
                        st.caption(f"📅 {'✅' if r.get('anual') else '⬜'}  📚 {r.get('unidad', 0)}  📝 {r.get('sesion', 0)}")
                        st.button("Abrir", key=f"abrir_{a['id']}", on_click=abrir_area, args=(a["id"],),
                                  use_container_width=True)

    with st.expander("➕ Nueva área", expanded=not asigs):
        st.caption("Estos datos aparecerán en todos tus documentos (los puedes cambiar después).")
        c1, c2 = st.columns(2)
        nivel = c1.selectbox("Nivel", NIVELES, index=1, key="na_nivel")
        grado = c2.selectbox("Grado / edad", GRADOS[nivel], key="na_grado")
        areas = areas_de(nivel)
        area = c1.selectbox("Área curricular", areas, key="na_area") if areas else None
        seccion = c2.text_input("Sección (ej.: A)", key="na_seccion")
        inst_def = u["colegio"] if u["colegio"] and u["colegio"] != "Independiente" else ""
        inst = c1.text_input("Institución educativa", value=inst_def, key="na_inst")
        director = c2.text_input("Nombre del director(a)", key="na_dir")
        docente = c1.text_input("Nombre del docente", value=u["nombre"], key="na_doc")
        region = c2.selectbox("Región", REGIONES, index=REGIONES.index("Lima"), key="na_region")
        ciclo = c1.number_input("Año escolar", 2024, 2035, 2026, key="na_ciclo")
        if area:
            n_comp, n_ver, n_des = estado_area(nivel, area, grado)
            if n_des == 0:
                st.caption("ℹ️ Para este grado aún no hay desempeños cargados: la IA propondrá algunos "
                           "y los verás marcados como «por verificar».")
        st.button("✅ Crear área", type="primary", key="na_crear", on_click=_crear_area_cb, args=(uid,))

    if asigs:
        with st.expander("🗑️ Eliminar un área"):
            st.caption("Se borran también todos los documentos de esa área.")
            ids = [a["id"] for a in asigs]
            elegida = st.selectbox("Área", ids, key="del_area_sel",
                                   format_func=lambda i: next(f"{a['area']} · {a['grado']} · {a['seccion'] or '—'}"
                                                              for a in asigs if a["id"] == i))
            st.checkbox("Sí, quiero eliminarla", key="del_area_ok")
            st.button("Eliminar área", key="del_area_btn", on_click=_borrar_area_cb)
