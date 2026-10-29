"""Inicio (bienvenida y herramientas) y Mis cursos (crear, abrir y eliminar cursos)."""
import html

import streamlit as st

from eduperu.services.curriculo import GRADOS, NIVELES, REGIONES, areas_de, estado_area
from eduperu.core.repo import (borrar_asignacion, borrar_todas_asignaciones, crear_asignacion, get_usuario, listar_asignaciones,
                  resumen_todas)
from eduperu.ui.components import PAG_ANUAL, PAG_CURSOS, PAG_TEMAS, abrir_siguiente, caja, flash

CLASE, UNIDAD = "📖 Una clase (un tema)", "📚 Toda la unidad"
# (icono, título, descripción, pestaña de la clase o None, ámbito)
HERRAMIENTAS = [
    ("🎒", "Mis cursos", "Todos tus cursos en un solo lugar: crea, abre o elimina.", "CURSOS", None, None),
    ("📚", "Unidad de aprendizaje", "Diseña una unidad completa con su secuencia.", PAG_TEMAS, UNIDAD, "📚 Unidad de aprendizaje"),
    ("📝", "Sesión de aprendizaje", "Elige un tema y crea su sesión.", PAG_TEMAS, CLASE, "📖 Sesión de aprendizaje"),
    ("🏆", "Fichas y desafíos", "Desglosa un tema en fichas de trabajo y retos.", PAG_TEMAS, CLASE, "📄 Ficha de trabajo"),
    ("📊", "Rúbricas", "Evalúa con criterios claros y niveles de logro.", PAG_TEMAS, CLASE, "📊 Rúbrica"),
    ("📋", "Exámenes", "Por clase, por unidad o bimestral.", PAG_TEMAS, CLASE, "📋 Examen"),
]
ICONO_AREA = {"Matemática": "🔢", "Comunicación": "📖", "Ciencia y Tecnología": "🔬", "Personal Social": "🧑‍🤝‍🧑",
              "Ciencias Sociales": "🌎", "Desarrollo Personal, Ciudadanía y Cívica": "🤝", "Arte y Cultura": "🎨",
              "Educación Física": "⚽", "Inglés": "🔤", "Educación Religiosa": "🕊️", "Educación para el Trabajo": "🛠️",
              "Psicomotricidad": "🤸"}


# ---------------- callbacks (se ejecutan antes de redibujar: así pueden cambiar el curso activo) ----------------
def _crear_curso_cb(uid):
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
    ss["crear_abierto"] = False
    flash(f"¡Listo! Creaste {ss['na_area']} · {ss['na_grado']}. Ahora ábrelo y empieza por el sílabo anual.")


def _ir_crear():
    st.session_state["nav"] = PAG_CURSOS
    st.session_state["crear_abierto"] = True


def _alternar_crear():
    st.session_state["crear_abierto"] = not st.session_state.get("crear_abierto", False)


def _pedir_borrar(aid):
    st.session_state[f"_del_{aid}"] = True


def _cancelar_borrar(aid):
    st.session_state.pop(f"_del_{aid}", None)


def _borrar_curso_cb(aid):
    borrar_asignacion(aid)
    st.session_state.pop(f"_del_{aid}", None)
    if st.session_state.get("area_id") == aid:
        st.session_state["area_id"] = None
    flash("Curso eliminado.")


def _pedir_borrar_todos():
    st.session_state["_del_todos"] = True


def _cancelar_borrar_todos():
    st.session_state.pop("_del_todos", None)


def _borrar_todos_cb(uid):
    borrar_todas_asignaciones(uid)
    st.session_state.pop("_del_todos", None)
    st.session_state["area_id"] = None
    flash("Se eliminaron todos tus cursos.")


def _ir_herramienta(pagina, ambito, seccion):
    ss = st.session_state
    if pagina == "CURSOS":
        ss["nav"] = PAG_CURSOS
        return
    ss["nav"] = pagina
    if ambito:
        ss["tc_ambito"] = ambito
        ss["tc_sec_unidad" if ambito == UNIDAD else "tc_sec_clase"] = seccion


# ---------------- INICIO ----------------
def render():
    uid = st.session_state.user_id
    u = get_usuario(uid)
    asigs = listar_asignaciones(uid)
    nombre = html.escape(u["nombre"].split()[0])
    creditos = "ilimitados" if u["rol"] == "admin" else u["creditos"]

    with caja("hero"):
        st.markdown(f"<div class='hero-t'>¡Hola, {nombre}! 👋</div>"
                    "<div class='hero-s'>Crea tu sílabo, tus clases, fichas, desafíos y exámenes en minutos, "
                    "alineados al CNEB y a la RM N.° 501-2025-MINEDU.</div>"
                    f"<span class='chip'>🎟️ Créditos: {creditos}</span>", unsafe_allow_html=True)
        b1, b2, _ = st.columns([1.4, 1.4, 3])
        b1.button("➕ Crear curso", key="hero_crear", on_click=_ir_crear, use_container_width=True)
        b2.button("📚 Mis cursos", key="hero_cursos", on_click=lambda: st.session_state.update(nav=PAG_CURSOS),
                  use_container_width=True)

    resumen_total = resumen_todas(uid)
    n_unidades = sum(r.get("unidad", 0) for r in resumen_total.values())
    n_sesiones = sum(r.get("sesion", 0) for r in resumen_total.values())
    n_docs = sum(sum(r.values()) for r in resumen_total.values())
    cred_txt = "∞" if u["rol"] == "admin" else str(u["creditos"])
    cred_cls = "ok" if u["rol"] == "admin" or u["creditos"] > 10 else "warn"
    cred_lbl = "Ilimitados" if u["rol"] == "admin" else ("Disponibles" if u["creditos"] > 10 else "Pocos")
    kpis = [("🎟️", cred_txt, "Créditos", cred_lbl, cred_cls),
            ("🎒", len(asigs), "Cursos creados", "Activos" if asigs else "Crea el primero", "info"),
            ("📚", n_unidades, "Unidades elaboradas", "En tus cursos", "info"),
            ("📝", n_sesiones, "Sesiones generadas", "Clases listas", "info"),
            ("🗂️", n_docs, "Documentos guardados", "En tu biblioteca", "ok")]
    st.markdown("<div class='kpi-grid'>" + "".join(
        f"<div class='kpi'><div class='kpi-top'><div class='kpi-ico'>{i}</div><span class='kpi-b {c}'>{b}</span></div>"
        f"<div class='kpi-v'>{v}</div><div class='kpi-l'>{l}</div></div>" for i, v, l, b, c in kpis) + "</div>",
        unsafe_allow_html=True)

    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    if not asigs:
        st.info("💡 **Empieza aquí:** pulsa **➕ Crear curso** (solo toma un minuto) y luego sigue con el sílabo anual.")
    else:
        activa = next((a for a in asigs if a["id"] == st.session_state.get("area_id")), asigs[0])
        r = resumen_todas(uid).get(activa["id"], {})
        with caja("continuar", borde=True):
            c1, c2 = st.columns([4, 1.3])
            c1.markdown(f"**▶ Sigue donde te quedaste:** {ICONO_AREA.get(activa['area'], '📘')} {activa['area']} · {activa['grado']} · "
                        f"Sección {activa['seccion'] or '—'}")
            c1.caption(f"Sílabo {'✅' if r.get('anual') else '⬜'}   ·   Unidades {r.get('unidad', 0)}   ·   "
                       f"Clases {r.get('sesion', 0)}   ·   Documentos {sum(r.values()) if r else 0}")
            c2.button("Continuar ▶", key="continuar_btn", on_click=abrir_siguiente, args=(activa["id"],),
                      type="primary", use_container_width=True)

    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
    st.subheader("🛠️ ¿Qué quieres crear hoy?")
    st.caption("Elige una herramienta. En la siguiente pantalla te preguntaré para qué curso.")
    for fila in range(0, len(HERRAMIENTAS), 3):
        cols = st.columns(3, gap="medium")
        for col, (icono, titulo, desc, pagina, ambito, seccion) in zip(cols, HERRAMIENTAS[fila:fila + 3]):
            with col:
                with caja(f"card_{titulo.replace(' ', '_')}", borde=True):
                    st.markdown(f"<div class='tool-i'>{icono}</div><div class='tool-t'>{titulo}</div>"
                                f"<div class='tool-d'>{desc}</div>", unsafe_allow_html=True)
                    st.button("Abrir", key=f"tool_{titulo}", on_click=_ir_herramienta, args=(pagina, ambito, seccion),
                              use_container_width=True, type="primary" if pagina == "CURSOS" else "secondary")
    st.caption("Los pasos también están en el menú de la izquierda: Sílabo anual, Calendario, Currículo oficial y Mi biblioteca.")


# ---------------- MIS CURSOS ----------------
def _formulario_crear(uid, u):
    with caja("form_crear", borde=True):
        st.markdown("#### ➕ Nuevo curso")
        st.caption("Estos datos aparecerán en todos tus documentos (los puedes cambiar después).")
        c1, c2 = st.columns(2, gap="medium")
        nivel = c1.selectbox("Nivel", NIVELES, index=1, key="na_nivel")
        grado = c2.selectbox("Grado / edad", GRADOS[nivel], key="na_grado")
        areas = areas_de(nivel)
        area = c1.selectbox("Área curricular", areas, key="na_area") if areas else None
        c2.text_input("Sección (ej.: A)", key="na_seccion")
        inst_def = u["colegio"] if u["colegio"] and u["colegio"] != "Independiente" else ""
        c1.text_input("Institución educativa", value=inst_def, key="na_inst")
        c2.text_input("Nombre del director(a)", key="na_dir")
        c1.text_input("Nombre del docente", value=u["nombre"], key="na_doc")
        c2.selectbox("Región", REGIONES, index=REGIONES.index("Lima"), key="na_region")
        c1.number_input("Año escolar", 2024, 2035, 2026, key="na_ciclo")
        if area:
            _, _, n_des = estado_area(nivel, area, grado)
            if n_des == 0:
                st.caption("ℹ️ Para este grado aún no hay desempeños oficiales cargados. Después podrás traerlos del MINEDU "
                           "con IA o subir tus propios lineamientos en el paso «Lineamientos» del sílabo.")
        b1, b2, _ = st.columns([1.3, 1, 3])
        b1.button("✅ Crear curso", type="primary", key="na_crear", on_click=_crear_curso_cb, args=(uid,),
                  use_container_width=True)
        b2.button("Cancelar", key="na_cancelar", on_click=_alternar_crear, use_container_width=True)


def render_cursos():
    uid = st.session_state.user_id
    u = get_usuario(uid)
    asigs = listar_asignaciones(uid)
    st.title("📚 Mis cursos")
    st.caption("Aquí están todos tus cursos. Abre uno para seguir trabajando.")

    b1, b2, b3 = st.columns([1.4, 3.6, 0.6])
    abierto = st.session_state.get("crear_abierto", False) or not asigs
    if not abierto:
        b1.button("➕ Crear curso", key="cursos_crear", on_click=_alternar_crear, type="primary", use_container_width=True)
    if asigs:
        b3.button("🗑️", key="del_todos_btn", on_click=_pedir_borrar_todos, help="Eliminar TODOS mis cursos")
    if st.session_state.get("_del_todos"):
        st.warning("⚠️ ¿Eliminar **todos** tus cursos y todos sus documentos? No se puede deshacer.")
        y, n, _ = st.columns([2, 1, 3])
        y.button("Sí, eliminar todos", key="del_todos_si", on_click=_borrar_todos_cb, args=(uid,), type="primary")
        n.button("No", key="del_todos_no", on_click=_cancelar_borrar_todos)
    if abierto:
        _formulario_crear(uid, u)
    if not asigs:
        st.info("💡 Aún no tienes cursos. Completa los datos de arriba y pulsa **Crear curso**.")
        return

    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
    activa = st.session_state.get("area_id")
    resumen = resumen_todas(uid)
    for nivel in NIVELES:
        grupo = [a for a in asigs if a["nivel"] == nivel]
        if not grupo:
            continue
        st.markdown(f"### {nivel}")
        for fila in range(0, len(grupo), 3):
            cols = st.columns(3, gap="medium")
            for col, a in zip(cols, grupo[fila:fila + 3]):
                with col:
                    with caja(f"curso_{a['id']}", borde=True):
                        st.markdown(f"<div class='curso-t'>{ICONO_AREA.get(a['area'], '📘')} {html.escape(a['area'])}</div>",
                                    unsafe_allow_html=True)
                        st.markdown(f"<div class='curso-s'>{a['grado']} · Sección {html.escape(a['seccion'] or '—')} · "
                                    f"{a['ciclo_escolar']}</div>", unsafe_allow_html=True)
                        if st.session_state.get(f"_del_{a['id']}"):
                            st.warning(f"¿Eliminar «{a['area']}»? Se borran sus documentos.")
                            y, n = st.columns(2)
                            y.button("Sí", key=f"xy_{a['id']}", on_click=_borrar_curso_cb, args=(a["id"],), type="primary",
                                     use_container_width=True)
                            n.button("No", key=f"xn_{a['id']}", on_click=_cancelar_borrar, args=(a["id"],),
                                     use_container_width=True)
                        else:
                            r = resumen.get(a["id"], {})
                            pills = [("pill ok", "📅 Sílabo listo") if r.get("anual") else ("pill warn", "📅 Sílabo pendiente"),
                                     ("pill info", f"📚 {r.get('unidad', 0)} unidades"),
                                     ("pill", f"📝 {r.get('sesion', 0)} clases")]
                            if a["id"] == activa:
                                pills.insert(0, ("pill active", "● Activo"))
                            st.markdown("<div class='pills'>" + "".join(f"<span class='{c}'>{x}</span>" for c, x in pills)
                                        + "</div>", unsafe_allow_html=True)
                            b1, b2 = st.columns([4, 1.3])
                            b1.button("Abrir ▶", key=f"abrir_{a['id']}", on_click=abrir_siguiente, args=(a["id"],),
                                      use_container_width=True, type="primary")
                            b2.button("🗑️", key=f"x_{a['id']}", on_click=_pedir_borrar, args=(a["id"],),
                                      help="Eliminar este curso", use_container_width=True)
