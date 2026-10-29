"""Calendario: vista mensual, eventos, programación automática y sugerencias con IA."""
import calendar
import datetime as dt
import html

import streamlit as st

from eduperu.services.calendario import (AUTO, DIAS, MESES, TIPOS, a_ics, agregar, borrar, eventos_mes, parsear_fechas,
                        programar_clases, sugerir_con_ia)
from eduperu.core.repo import cobrar
from eduperu.ui.components import confirmar, descargar, flash, selector_curso


def _mover(delta):
    y, m = st.session_state["cal_y"], st.session_state["cal_m"] + delta
    if m < 1:
        y, m = y - 1, 12
    elif m > 12:
        y, m = y + 1, 1
    st.session_state["cal_y"], st.session_state["cal_m"] = y, m


def _hoy_cb():
    hoy = dt.date.today()
    st.session_state["cal_y"], st.session_state["cal_m"] = hoy.year, hoy.month


def render():
    uid = st.session_state.user_id
    hoy = dt.date.today()
    st.session_state.setdefault("cal_y", hoy.year)
    st.session_state.setdefault("cal_m", hoy.month)
    y, m = st.session_state["cal_y"], st.session_state["cal_m"]

    st.title("🗓️ Calendario")
    st.info("💡 Programa tus clases, exámenes y actividades. Puedes repartir automáticamente las clases de tu sílabo "
            "y pedir sugerencias a la IA.")

    asig = selector_curso("📌 ¿Para qué curso programas?")
    c1, c2, c3, c4 = st.columns([1, 3, 1, 2])
    c1.button("◀ Anterior", on_click=_mover, args=(-1,), key="cal_prev", use_container_width=True)
    c2.markdown(f"<h3 style='text-align:center;margin:0'>{MESES[m]} {y}</h3>", unsafe_allow_html=True)
    c3.button("Siguiente ▶", on_click=_mover, args=(1,), key="cal_next", use_container_width=True)
    c4.button("Ir a hoy", on_click=_hoy_cb, key="cal_hoy", use_container_width=True)

    solo_curso = False
    if asig:
        solo_curso = st.radio("Mostrar", ["Todos mis cursos", f"Solo {asig['area']} · {asig['grado']}"], horizontal=True,
                              key="cal_filtro", label_visibility="collapsed").startswith("Solo")
    eventos = eventos_mes(uid, y, m, asig["id"] if solo_curso and asig else None)
    por_dia = {}
    for e in eventos:
        por_dia.setdefault(e["fecha"].day, []).append(e)

    cab = st.columns(7)
    for i, nombre in enumerate(DIAS):
        cab[i].markdown(f"<div style='text-align:center;font-weight:600;color:#6D28D9'>{nombre[:3]}</div>",
                        unsafe_allow_html=True)
    for semana in calendar.Calendar(firstweekday=0).monthdayscalendar(y, m):
        cols = st.columns(7)
        for i, dia in enumerate(semana):
            if dia == 0:
                continue
            es_hoy = dt.date(y, m, dia) == hoy
            borde = "#7c3aed" if es_hoy else "#eee"
            fondo = "#faf5ff" if es_hoy else "#fff"
            items = "".join(
                f"<div style='font-size:11px;line-height:1.25;margin-top:2px'>{TIPOS.get(e['tipo'], TIPOS['otro'])[0]} "
                f"{html.escape((e['titulo'] or '')[:28])}</div>" for e in por_dia.get(dia, [])[:3])
            mas = len(por_dia.get(dia, [])) - 3
            if mas > 0:
                items += f"<div style='font-size:11px;color:#888'>+{mas} más</div>"
            cols[i].markdown(f"<div style='min-height:82px;border:1px solid {borde};background:{fondo};"
                             f"border-radius:10px;padding:4px 6px'><b>{dia}</b>{items}</div>", unsafe_allow_html=True)

    st.markdown("#### 📋 Eventos de este mes")
    if not eventos:
        st.caption("No hay eventos este mes.")
    for e in eventos:
        a, b = st.columns([8, 1])
        emoji, nombre = TIPOS.get(e["tipo"], TIPOS["otro"])
        a.markdown(f"**{e['fecha']:%d/%m}** · {emoji} {e['titulo']}")
        if e.get("detalle") and not e["detalle"].startswith(AUTO):
            a.caption(e["detalle"])
        if b.button("✕", key=f"ev_del_{e['id']}", help="Eliminar este evento"):
            borrar(e["id"], uid)
            st.rerun()
    if eventos:
        descargar("⬇️ Descargar calendario (.ics)", a_ics(eventos), f"calendario_{y}_{m:02d}.ics", "text/calendar", "cal_ics")

    with st.expander("➕ Agregar un evento"):
        with st.form("cal_nuevo", clear_on_submit=True):
            f1, f2 = st.columns(2)
            fecha = f1.date_input("Fecha", value=dt.date(y, m, 1) if (y, m) != (hoy.year, hoy.month) else hoy)
            tipo = f2.selectbox("Tipo", list(TIPOS), format_func=lambda k: f"{TIPOS[k][0]} {TIPOS[k][1]}")
            titulo = st.text_input("Título")
            detalle = st.text_area("Detalle (opcional)", height=70)
            vincular = st.checkbox("Asociarlo al curso activo", value=bool(asig), disabled=not asig)
            ok = st.form_submit_button("Agregar", type="primary")
        if ok:
            if not titulo.strip():
                st.warning("Escribe un título.")
            else:
                agregar(uid, asig["id"] if asig and vincular else None, fecha, tipo, titulo.strip(), detalle.strip())
                flash("Evento agregado ✅")
                st.rerun()

    with st.expander("⚡ Programar mis clases automáticamente"):
        if not asig:
            st.info("Primero elige un curso en el menú lateral.")
        else:
            st.caption("Reparte las clases de tu sílabo en los días que elijas y pone un examen al final de cada unidad. "
                       "Lo programado antes automáticamente para este curso se reemplaza.")
            d1, d2 = st.columns(2)
            inicio = d1.date_input("Primer día de clases", value=hoy, key="cal_inicio")
            dias = d2.multiselect("Días de clase", DIAS, default=["Lunes", "Miércoles", "Viernes"], key="cal_dias")
            sin = st.text_area("Días sin clases (opcional): fechas dd/mm/aaaa separadas por comas", height=70, key="cal_sin",
                               help="Feriados, vacaciones, semana de gestión… según el calendario de tu institución.")
            con_ex = st.checkbox("Incluir un examen al final de cada unidad", value=True, key="cal_conex")
            if st.button("📆 Programar clases", type="primary", key="cal_programar"):
                fechas, malas = parsear_fechas(sin)
                if malas:
                    st.warning("No entendí estas fechas (úsalas como dd/mm/aaaa): " + ", ".join(malas))
                try:
                    n = programar_clases(uid, asig, inicio, [DIAS.index(x) for x in dias], fechas, con_ex)
                    flash(f"Se programaron {n} eventos. Revisa los meses siguientes ✅")
                    st.session_state["cal_y"], st.session_state["cal_m"] = inicio.year, inicio.month
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    with st.expander("🤖 Sugerencias de actividades con IA"):
        if not asig:
            st.info("Primero elige un curso en el menú lateral.")
        else:
            st.caption(f"La IA propone actividades pedagógicas para {MESES[m]} {y}. No conoce los feriados ni fechas oficiales: "
                       "verifica siempre con el calendario de tu institución (RM N.° 501-2025-MINEDU).")
            if confirmar("calendario_ia", f"✨ Sugerir actividades de {MESES[m]}", "cal_ia", asig=None):
                try:
                    with st.spinner("Pensando actividades..."):
                        st.session_state["cal_sug"] = sugerir_con_ia(asig, y, m)
                    cobrar(uid, "calendario_ia")
                except Exception as e:
                    st.error(f"No se pudo: {e}")
            sug = st.session_state.get("cal_sug") or []
            marcados = []
            for i, x in enumerate(sug):
                if st.checkbox(f"{x['fecha']:%d/%m} · {TIPOS[x['tipo']][0]} {x['titulo']}", value=True, key=f"cal_s_{i}"):
                    marcados.append(x)
                if x["detalle"]:
                    st.caption(x["detalle"])
            if sug and st.button("➕ Agregar los marcados", key="cal_sug_add"):
                for x in marcados:
                    agregar(uid, asig["id"], x["fecha"], x["tipo"], x["titulo"], x["detalle"])
                st.session_state["cal_sug"] = []
                flash(f"Se agregaron {len(marcados)} actividades ✅")
                st.rerun()
