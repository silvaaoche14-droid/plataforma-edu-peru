"""Piezas de interfaz compartidas: navegación, avisos, confirmación de costo, vista previa y descarga."""
import streamlit as st
import streamlit.components.v1 as components

from repo import cambiar_color, costo_de, get_asignacion, get_doc_by_id, get_usuario
from render import COLORES, COLOR_DEFECTO, ICONO_COLOR, a_docx, a_html
from exportar import bloques_de

PAG_PANEL = "🏠 Mi Panel"
PAG_ANUAL = "📅 Planificación anual"
PAG_UNIDADES = "📚 Unidades"
PAG_SESIONES = "📝 Sesiones"
PAG_BIBLIO = "🗂️ Mi Biblioteca"
PAG_ADMIN = "⚙️ Administración"

MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


# ------------------------------------------------------------------
# Navegación y mensajes
# ------------------------------------------------------------------
def ir_a(pagina):
    st.session_state["nav"] = pagina


def abrir_area(aid, pagina=None):
    st.session_state["area_id"] = aid
    if pagina:
        st.session_state["nav"] = pagina


def flash(mensaje, tipo="success"):
    st.session_state["_flash"] = (tipo, mensaje)


def mostrar_flash():
    f = st.session_state.pop("_flash", None)
    if f:
        {"success": st.success, "info": st.info, "warning": st.warning, "error": st.error}.get(f[0], st.info)(f[1])


def ayuda(texto):
    st.info("💡 " + texto)


def area_activa():
    aid = st.session_state.get("area_id")
    return get_asignacion(aid) if aid else None


def exigir_area():
    asig = area_activa()
    if not asig:
        st.warning("👆 Primero elige o crea un **área** en *Mi Panel*. Ahí indicas tu grado, área y sección.")
        st.button("Ir a Mi Panel", on_click=ir_a, args=(PAG_PANEL,))
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


# ------------------------------------------------------------------
# Costo en créditos con confirmación
# ------------------------------------------------------------------
def confirmar(accion, etiqueta, clave, veces=1):
    """Botón que pide confirmar el costo en créditos. Devuelve True cuando el usuario confirma."""
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
# Vista previa, color y descarga
# ------------------------------------------------------------------
def vista_previa_y_descarga(doc_id, clave, abierta=True):
    doc = get_doc_by_id(doc_id)
    if not doc:
        return
    color_doc = (doc.get("color") or COLOR_DEFECTO).lstrip("#")
    nombre_actual = next((n for n, h in COLORES.items() if h == color_doc), "Azul")
    ckey = f"color_{clave}_{doc_id}"
    if ckey not in st.session_state:
        st.session_state[ckey] = nombre_actual
    elegido = st.radio("🎨 Color del documento", list(COLORES), key=ckey, horizontal=True,
                       format_func=lambda n: f"{ICONO_COLOR[n]} {n}")
    color = COLORES[elegido]
    if color != color_doc:
        cambiar_color(doc_id, color)
        doc["color"] = color
    bloques, horizontal, archivo = bloques_de(doc)
    with st.expander("👁️ Vista previa del documento (se actualiza al guardar)", expanded=abierta):
        components.html(a_html(bloques, color, doc.get("normativa_usada")), height=620, scrolling=True)
    st.download_button("⬇️ Descargar en Word", data=a_docx(bloques, color, doc.get("normativa_usada"), horizontal),
                       file_name=archivo, mime=MIME_DOCX, key=f"dl_{clave}_{doc_id}", type="primary")
