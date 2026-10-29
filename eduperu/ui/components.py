"""Piezas de interfaz compartidas: navegación, selector de curso, avisos, costos, vista previa y editores."""
import streamlit as st
import streamlit.components.v1 as components

from eduperu.services.curriculo import bloqueo_curricular
from eduperu.services.exportar import bloques_de
from eduperu.core.repo import (cambiar_color, costo_de, get_asignacion, get_doc_by_id, get_usuario, listar_asignaciones,
                  resumen_asignacion)
from eduperu.services.render import COLORES, COLOR_DEFECTO, ICONO_COLOR, a_docx, a_html
from eduperu.core.util import a_lista, a_texto, s

PAG_PANEL = "🏠 Inicio"
PAG_CURSOS = "📚 Mis cursos"
PAG_ANUAL = "📅 Sílabo anual"
PAG_TEMAS = "🎯 Temas y clases"
PAG_CALENDARIO = "🗓️ Calendario"
PAG_CURRICULO = "📖 Currículo oficial"
PAG_BIBLIO = "🗂️ Mi biblioteca"
PAG_ADMIN = "⚙️ Administración"
PAG_UNIDADES = PAG_SESIONES = PAG_TEMAS   # nombres antiguos: ahora todo vive en «Temas y clases»

MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


# ------------------------------------------------------------------
# Navegación y mensajes
# ------------------------------------------------------------------
def caja(clave, borde=False):
    """Contenedor con nombre propio (para darle estilo con CSS). Si tu Streamlit es antiguo, usa uno normal."""
    try:
        return st.container(border=borde, key=clave)
    except TypeError:
        return st.container(border=borde)


def ir_a(pagina):
    st.session_state["nav"] = pagina


def abrir_area(aid, pagina=None):
    st.session_state["area_id"] = aid
    if pagina:
        st.session_state["nav"] = pagina


def abrir_siguiente(aid):
    """Activa el curso y te lleva al siguiente paso pendiente (sílabo anual → temas y clases)."""
    r = resumen_asignacion(aid)
    abrir_area(aid, PAG_ANUAL if not r.get("anual") else PAG_TEMAS)


def flash(mensaje, tipo="success"):
    st.session_state["_flash"] = (tipo, mensaje)


def mostrar_flash():
    f = st.session_state.pop("_flash", None)
    if f:
        {"success": st.success, "info": st.info, "warning": st.warning, "error": st.error}.get(f[0], st.info)(f[1])


def ayuda(texto):
    st.info("💡 " + texto)


def _etiqueta_curso(a):
    return f"{a['area']} · {a['grado']} · Sección {a['seccion'] or '—'}"


def area_activa():
    """Curso activo del usuario (sale de la lista de sus cursos: no hace otra consulta)."""
    aid = st.session_state.get("area_id")
    if not aid:
        return None
    return next((a for a in listar_asignaciones(st.session_state.user_id) if a["id"] == aid), None)


def selector_curso(titulo="📌 ¿Para qué curso?"):
    """Selector de curso al comienzo de la pantalla. Devuelve el curso elegido (o None si no hay cursos)."""
    asigs = listar_asignaciones(st.session_state.user_id)
    if not asigs:
        return None
    ids = [a["id"] for a in asigs]
    actual = st.session_state.get("area_id")
    with st.container(border=True):
        elegido = st.selectbox(titulo, ids, index=ids.index(actual) if actual in ids else 0,
                               key=f"selcurso_{st.session_state.get('nav', '')}",
                               format_func=lambda i: _etiqueta_curso(next(a for a in asigs if a["id"] == i)))
    st.session_state["area_id"] = elegido
    return next(a for a in asigs if a["id"] == elegido)


def exigir_area():
    """Muestra el selector de curso arriba; si no hay cursos, invita a crear uno."""
    asig = selector_curso()
    if not asig:
        st.warning("👆 Primero crea un **curso** en *Inicio*. Ahí indicas tu grado, área y sección.")
        st.button("Ir a Inicio", on_click=ir_a, args=(PAG_PANEL,))
        st.stop()
    return asig


def exigir_cadena(mensaje, pagina_destino, etiqueta_boton):
    st.warning(mensaje)
    st.button(etiqueta_boton, on_click=ir_a, args=(pagina_destino,))
    st.stop()


# ------------------------------------------------------------------
# Campos con estado (evitan conflictos entre valor inicial y edición del usuario)
# ------------------------------------------------------------------
def campo_texto(etiqueta, clave, inicial="", alto=110, ayuda_txt=None):
    if clave not in st.session_state:
        st.session_state[clave] = inicial or ""
    return st.text_area(etiqueta, key=clave, height=alto, help=ayuda_txt)


def campo_linea(etiqueta, clave, inicial="", ayuda_txt=None):
    if clave not in st.session_state:
        st.session_state[clave] = inicial or ""
    return st.text_input(etiqueta, key=clave, help=ayuda_txt)


def campo_num(etiqueta, clave, minimo, maximo, inicial, paso=1):
    if clave not in st.session_state:
        st.session_state[clave] = max(minimo, min(maximo, int(inicial)))
    return st.number_input(etiqueta, min_value=minimo, max_value=maximo, step=paso, key=clave)


def campo_multi(etiqueta, clave, opciones, inicial):
    """Multiselección que nunca falla si cambian las opciones."""
    if clave not in st.session_state:
        st.session_state[clave] = [x for x in (inicial or []) if x in opciones]
    else:
        st.session_state[clave] = [x for x in st.session_state[clave] if x in opciones]
    return st.multiselect(etiqueta, opciones, key=clave)


def siguiente_version(clave_ver):
    st.session_state[clave_ver] = st.session_state.get(clave_ver, 0) + 1


def seccion(opciones, clave):
    """Selector de secciones (reemplaza a las pestañas): solo se dibuja lo que eliges, así la página va más rápido."""
    return st.radio("Sección", opciones, horizontal=True, key=clave, label_visibility="collapsed")


def descargar(etiqueta, data, nombre, mime, key, **kw):
    """Botón de descarga que NO vuelve a calcular la página (más rápido) cuando Streamlit lo permite."""
    try:
        return st.download_button(etiqueta, data=data, file_name=nombre, mime=mime, key=key, on_click="ignore", **kw)
    except TypeError:
        return st.download_button(etiqueta, data=data, file_name=nombre, mime=mime, key=key, **kw)


# ------------------------------------------------------------------
# Costo en créditos con confirmación
# ------------------------------------------------------------------
def confirmar(accion, etiqueta, clave, veces=1, asig=None):
    """Botón que pide confirmar el costo en créditos. Devuelve True cuando el usuario confirma.
    Si se pasa 'asig' y el administrador exige currículo verificado, bloquea los cursos sin verificar."""
    if asig is not None:
        motivo = bloqueo_curricular(asig)
        if motivo:
            st.error("🔒 " + motivo)
            st.button("Ver el currículo oficial", key=f"cv_{clave}", on_click=ir_a, args=(PAG_CURRICULO,))
            return False
    u = get_usuario(st.session_state.user_id)
    costo = 0 if u["rol"] == "admin" else costo_de(accion) * veces
    if costo == 0:
        return st.button(etiqueta, key=f"b_{clave}", type="primary")
    flag = f"_conf_{clave}"
    if not st.session_state.get(flag):
        texto = f"{etiqueta} · {costo} crédito{'s' if costo != 1 else ''}"
        if st.button(texto, key=f"b_{clave}", type="primary"):
            if u["creditos"] < costo:
                st.error(f"Necesitas {costo} créditos y tienes {u['creditos']}. Pide más créditos al administrador.")
                return False
            st.session_state[flag] = True
            st.rerun()
        return False
    st.warning(f"Esta acción cuesta **{costo} crédito(s)**. Tienes **{u['creditos']}**. ¿Quieres continuar?")
    c1, c2 = st.columns(2)
    if c1.button("✅ Sí, continuar", key=f"y_{clave}", use_container_width=True):
        st.session_state[flag] = False
        return True
    if c2.button("✖ Cancelar", key=f"n_{clave}", use_container_width=True):
        st.session_state[flag] = False
        st.rerun()
    return False


# ------------------------------------------------------------------
# Vista previa, color y descarga (la descarga va PRIMERO)
# ------------------------------------------------------------------
def vista_previa_y_descarga(doc_id, clave, abierta=True):
    doc = get_doc_by_id(doc_id)
    if not doc:
        return
    color_doc = (doc.get("color") or COLOR_DEFECTO).lstrip("#")
    nombres = list(COLORES)
    actual = next((n for n, h in COLORES.items() if h == color_doc), "Azul")
    c_desc, c_color = st.columns([3, 2])
    ckey = f"color_{clave}_{doc_id}"
    elegido = c_color.selectbox("🎨 Color del documento", nombres, index=nombres.index(actual), key=ckey,
                                format_func=lambda n: f"{ICONO_COLOR[n]} {n}")
    color = COLORES[elegido]
    if color != color_doc:
        cambiar_color(doc_id, color)
        doc["color"] = color
    bloques, horizontal, archivo = bloques_de(doc)
    with c_desc:
        st.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
        descargar("⬇️ Descargar en Word", a_docx(bloques, color, doc.get("normativa_usada"), horizontal), archivo,
                  MIME_DOCX, f"dl_{clave}_{doc_id}", type="primary", use_container_width=True)
    with st.expander("👁️ Vista previa del documento (se actualiza al guardar)", expanded=abierta):
        components.html(a_html(bloques, color, doc.get("normativa_usada")), height=560, scrolling=True)


# ------------------------------------------------------------------
# Editores por elemento (reemplazan a las tablas anchas: se ven ordenados también en el celular)
# campos = [{"k": "enunciado", "label": "Enunciado", "tipo": "linea|area|lineas|select|lectura", "alto": 90, "opciones": [...]}]
# ------------------------------------------------------------------
def editor_items(clave, items, campos, titulo_fn, abiertos=1):
    for i, it in enumerate(items):
        with st.expander(titulo_fn(i, it), expanded=(i < abiertos)):
            for c in campos:
                k, tipo = f"{clave}_{i}_{c['k']}", c.get("tipo", "linea")
                valor = it.get(c["k"])
                if tipo == "area":
                    campo_texto(c["label"], k, s(valor), c.get("alto", 90))
                elif tipo == "lineas":
                    campo_texto(c["label"], k, a_texto(valor), c.get("alto", 90), c.get("ayuda"))
                elif tipo == "select":
                    ops = list(c["opciones"])
                    if s(valor) and s(valor) not in ops:
                        ops.insert(0, s(valor))
                    if k not in st.session_state or st.session_state[k] not in ops:
                        st.session_state[k] = s(valor) if s(valor) in ops else ops[0]
                    st.selectbox(c["label"], ops, key=k)
                elif tipo == "lectura":
                    if s(valor):
                        st.caption(f"{c['label']}: {s(valor)}")
                else:
                    campo_linea(c["label"], k, s(valor))


def recoger_items(clave, items, campos):
    res = []
    for i, it in enumerate(items):
        d = dict(it)
        for c in campos:
            tipo = c.get("tipo", "linea")
            if tipo == "lectura":
                continue
            v = st.session_state.get(f"{clave}_{i}_{c['k']}")
            if v is not None:
                d[c["k"]] = a_lista(v) if tipo == "lineas" else s(v)
        d["numero"] = i + 1
        res.append(d)
    return res


def barra_edicion(clave, items, campos, vacio, guardar, ver_key):
    """Botones Guardar / Agregar / Quitar el último para un editor_items. guardar(lista) persiste los cambios."""
    c1, c2, c3 = st.columns(3)
    if c1.button("💾 Guardar cambios", type="primary", key=f"{clave}_save", use_container_width=True):
        guardar(recoger_items(clave, items, campos))
        st.success("Guardado ✅")
    if c2.button("➕ Agregar", key=f"{clave}_add", use_container_width=True):
        lista = recoger_items(clave, items, campos)
        lista.append(vacio(len(lista) + 1))
        guardar(lista)
        siguiente_version(ver_key)
        st.rerun()
    if c3.button("➖ Quitar el último", key=f"{clave}_rm", use_container_width=True) and len(items) > 1:
        guardar(recoger_items(clave, items, campos)[:-1])
        siguiente_version(ver_key)
        st.rerun()
