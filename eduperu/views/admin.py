"""Administración: resumen, usuarios, colegios, currículo, normativa MINEDU y costos."""
import io

import mysql.connector
import pandas as pd
import streamlit as st

from eduperu.core.auth import hash_password
from eduperu.services.curriculo import (CICLOS, GRADOS, NIVELES, areas_de, competencias_de, desempenos_de, limpiar_cache,
                       sembrar_curriculo, transversales)
from eduperu.core.db import conexion, execute as db_execute, execute_many, fetch as db_fetch
from eduperu.core.normativa import revisar_fuente
from eduperu.core.repo import COSTOS_DEFAULT, NOMBRES_COSTO, config_get, config_set, costo_de, mapa_colegios
from eduperu.core.util import a_lista, entero, norm, s
import time

import requests

from eduperu.views import programas_admin as v_programas
from eduperu.core.db import medir_latencia
from eduperu.core.ia import (PROVEEDORES, clave_de, llamar_gemini, llamar_openrouter, modelo_de, origen_clave,
                probar_proveedor, registros_recientes)
from eduperu.services.programas import PORTALES
from eduperu.ui.components import descargar, flash

ROLES = ["docente", "director", "admin"]
TIPOS_NORMA = ["curricular", "pedagógico/normativo", "administrativo"]


def render(admin_id):
    st.title("⚙️ Administración")
    t = st.tabs(["📊 Resumen", "👥 Usuarios", "🏫 Colegios", "🎓 Currículo", "📜 Normativa MINEDU", "🎟️ Costos",
                 "🩺 Diagnóstico", "🤖 IA"])
    with t[0]:
        panel_resumen()
    with t[1]:
        panel_usuarios(admin_id)
    with t[2]:
        panel_colegios()
    with t[3]:
        panel_curriculo()
    with t[4]:
        panel_normativa(admin_id)
    with t[5]:
        panel_costos()
    with t[6]:
        panel_diagnostico()
    with t[7]:
        panel_ia()


# ------------------------------------------------------------------
def panel_resumen():
    st.subheader("Resumen")
    n = lambda sql: db_fetch(sql, one=True)["n"]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Usuarios", n("SELECT COUNT(*) AS n FROM usuarios"))
    c2.metric("Colegios", n("SELECT COUNT(*) AS n FROM colegios"))
    c3.metric("Documentos", n("SELECT COUNT(*) AS n FROM documentos"))
    c4.metric("Áreas asignadas", n("SELECT COUNT(*) AS n FROM asignaciones"))
    c5.metric("Normativa pendiente", n("SELECT COUNT(*) AS n FROM normativa_versiones WHERE estado='pendiente'"))
    st.markdown("#### Últimos documentos de todos los usuarios")
    docs = db_fetch("SELECT d.id, u.nombre AS usuario, d.tipo, d.titulo, d.normativa_usada AS normativa, d.actualizado_en "
                    "FROM documentos d LEFT JOIN usuarios u ON u.id = d.usuario_id ORDER BY d.actualizado_en DESC LIMIT 30")
    if docs:
        st.dataframe(pd.DataFrame(docs), hide_index=True)
    else:
        st.info("Todavía no hay documentos.")


# ------------------------------------------------------------------
def panel_usuarios(admin_id):
    st.subheader("Usuarios")
    filas = db_fetch(
        "SELECT u.id, u.nombre, u.correo, u.rol, u.colegio_id, c.nombre AS colegio, u.nivel_educativo AS nivel, "
        "u.creditos, u.activo, u.creado_en FROM usuarios u LEFT JOIN colegios c ON c.id = u.colegio_id ORDER BY u.id DESC")
    colegios = mapa_colegios(solo_activos=False)
    claves_col = list(colegios.keys())
    if filas:
        st.dataframe(pd.DataFrame(filas).drop(columns=["colegio_id"]), hide_index=True)

    with st.expander("➕ Crear usuario"):
        with st.form("crear_usuario", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre completo")
            correo = c2.text_input("Correo electrónico")
            pw = c1.text_input("Contraseña inicial (mínimo 8)", type="password")
            rol = c2.selectbox("Rol", ROLES)
            colegio = c1.selectbox("Colegio", claves_col, format_func=lambda k: colegios[k])
            nivel_u = c2.selectbox("Nivel", NIVELES)
            cred = c1.number_input("Créditos", min_value=0, max_value=100000, value=50)
            enviar = st.form_submit_button("Crear usuario", type="primary")
        if enviar:
            if not (nombre and correo and pw):
                st.warning("Completa nombre, correo y contraseña.")
            elif len(pw) < 8:
                st.warning("La contraseña debe tener al menos 8 caracteres.")
            else:
                try:
                    db_execute("INSERT INTO usuarios (nombre, correo, password_hash, rol, colegio_id, colegio, nivel_educativo, creditos) "
                               "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                               (nombre.strip(), correo.strip().lower(), hash_password(pw), rol, colegio or None,
                                colegios[colegio] if colegio else "Independiente", nivel_u, cred))
                    st.success("Usuario creado.")
                    st.rerun()
                except mysql.connector.Error as err:
                    st.error("Ese correo ya existe." if err.errno == 1062 else "No se pudo crear el usuario.")

    if filas:
        st.markdown("#### Editar o eliminar")
        opciones = {u["id"]: f"{u['id']} · {u['nombre']} · {u['correo']}" for u in filas}
        uid = st.selectbox("Usuario", list(opciones.keys()), format_func=lambda k: opciones[k], key="adm_user_sel")
        u = next(x for x in filas if x["id"] == uid)
        with st.form(f"edit_user_{uid}"):
            c1, c2 = st.columns(2)
            e_nombre = c1.text_input("Nombre", u["nombre"], key=f"en_{uid}")
            e_rol = c2.selectbox("Rol", ROLES, index=ROLES.index(u["rol"]) if u["rol"] in ROLES else 0, key=f"er_{uid}")
            actual = u["colegio_id"] or 0
            e_col = c1.selectbox("Colegio", claves_col, index=claves_col.index(actual) if actual in claves_col else 0,
                                 format_func=lambda k: colegios[k], key=f"ec_{uid}")
            e_cred = c2.number_input("Créditos", 0, 100000, int(u["creditos"] or 0), key=f"ecr_{uid}")
            e_activo = c1.checkbox("Cuenta activa", bool(u["activo"]), key=f"ea_{uid}")
            e_pw = c2.text_input("Nueva contraseña (opcional)", type="password", key=f"ep_{uid}")
            guardar = st.form_submit_button("Guardar cambios", type="primary")
        if guardar:
            if uid == admin_id and (e_rol != "admin" or not e_activo):
                st.error("No puedes quitarte el rol de admin ni desactivarte a ti mismo.")
            elif e_pw and len(e_pw) < 8:
                st.warning("La nueva contraseña debe tener al menos 8 caracteres.")
            else:
                db_execute("UPDATE usuarios SET nombre=%s, rol=%s, colegio_id=%s, colegio=%s, creditos=%s, activo=%s WHERE id=%s",
                           (e_nombre.strip(), e_rol, e_col or None, colegios[e_col] if e_col else "Independiente",
                            e_cred, 1 if e_activo else 0, uid))
                if e_pw:
                    db_execute("UPDATE usuarios SET password_hash=%s WHERE id=%s", (hash_password(e_pw), uid))
                st.success("Cambios guardados.")
                st.rerun()
        with st.expander("🗑️ Eliminar este usuario"):
            st.caption("También se eliminan sus áreas y documentos.")
            ok = st.checkbox("Confirmo que quiero eliminarlo", key=f"cd_{uid}")
            if st.button("Eliminar usuario", key=f"del_{uid}"):
                if uid == admin_id:
                    st.error("No puedes eliminarte a ti mismo.")
                elif not ok:
                    st.warning("Marca la confirmación primero.")
                else:
                    db_execute("DELETE FROM documentos WHERE usuario_id=%s", (uid,))
                    db_execute("DELETE FROM asignaciones WHERE usuario_id=%s", (uid,))
                    db_execute("DELETE FROM planificaciones WHERE usuario_id=%s", (uid,))
                    db_execute("DELETE FROM usuarios WHERE id=%s", (uid,))
                    st.success("Usuario eliminado.")
                    st.rerun()


# ------------------------------------------------------------------
def panel_colegios():
    st.subheader("Colegios")
    from eduperu.services.curriculo import REGIONES
    filas = db_fetch("SELECT c.id, c.nombre, c.codigo_modular, c.region, c.ugel, c.activo, "
                     "(SELECT COUNT(*) FROM usuarios u WHERE u.colegio_id = c.id) AS usuarios FROM colegios c ORDER BY c.nombre")
    if filas:
        st.dataframe(pd.DataFrame(filas), hide_index=True)
    else:
        st.info("Aún no hay colegios registrados.")
    with st.expander("➕ Crear colegio"):
        with st.form("crear_colegio", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre de la institución")
            codigo = c2.text_input("Código modular (opcional)")
            reg = c1.selectbox("Región", REGIONES, index=REGIONES.index("Lima"))
            ugel = c2.text_input("UGEL (opcional)")
            enviar = st.form_submit_button("Crear colegio", type="primary")
        if enviar:
            if not nombre.strip():
                st.warning("Escribe el nombre del colegio.")
            else:
                db_execute("INSERT INTO colegios (nombre, codigo_modular, region, ugel) VALUES (%s,%s,%s,%s)",
                           (nombre.strip(), codigo.strip(), reg, ugel.strip()))
                st.success("Colegio creado.")
                st.rerun()
    if filas:
        st.markdown("#### Editar o eliminar")
        opciones = {c["id"]: f"{c['id']} · {c['nombre']}" for c in filas}
        cid = st.selectbox("Colegio", list(opciones.keys()), format_func=lambda k: opciones[k], key="adm_col_sel")
        c = next(x for x in filas if x["id"] == cid)
        with st.form(f"edit_col_{cid}"):
            c1, c2 = st.columns(2)
            e_nombre = c1.text_input("Nombre", c["nombre"], key=f"cn_{cid}")
            e_codigo = c2.text_input("Código modular", c["codigo_modular"] or "", key=f"cc_{cid}")
            e_reg = c1.selectbox("Región", REGIONES, index=REGIONES.index(c["region"]) if c["region"] in REGIONES
                                 else REGIONES.index("Lima"), key=f"cr_{cid}")
            e_ugel = c2.text_input("UGEL", c["ugel"] or "", key=f"cu_{cid}")
            e_activo = c1.checkbox("Activo", bool(c["activo"]), key=f"ca_{cid}")
            guardar = st.form_submit_button("Guardar cambios", type="primary")
        if guardar:
            db_execute("UPDATE colegios SET nombre=%s, codigo_modular=%s, region=%s, ugel=%s, activo=%s WHERE id=%s",
                       (e_nombre.strip(), e_codigo.strip(), e_reg, e_ugel.strip(), 1 if e_activo else 0, cid))
            db_execute("UPDATE usuarios SET colegio=%s WHERE colegio_id=%s", (e_nombre.strip(), cid))
            st.success("Cambios guardados.")
            st.rerun()
        with st.expander("🗑️ Eliminar este colegio"):
            if c["usuarios"] > 0:
                st.warning(f"Tiene {c['usuarios']} usuario(s). Reasígnalos o desactívalo en lugar de eliminarlo.")
            else:
                ok = st.checkbox("Confirmo que quiero eliminarlo", key=f"ccd_{cid}")
                if st.button("Eliminar colegio", key=f"cdel_{cid}"):
                    if ok:
                        db_execute("DELETE FROM colegios WHERE id=%s", (cid,))
                        st.success("Colegio eliminado.")
                        st.rerun()
                    else:
                        st.warning("Marca la confirmación primero.")


# ------------------------------------------------------------------
# CURRÍCULO
# ------------------------------------------------------------------
def panel_curriculo():
    st.subheader("Base curricular verificada")
    st.caption("La IA solo usa los textos de esta base. Competencias y capacidades vienen precargadas (marcadas «por verificar»). "
               "Los **desempeños** los cargas tú desde los Programas Curriculares oficiales del MINEDU.")
    exigir = st.checkbox("🔒 Bloquear la generación en las áreas cuyo currículo aún no esté verificado "
                         "(los docentes solo podrán generar cuando todas las competencias estén verificadas y tengan desempeños)",
                         value=config_get("exigir_verificado", "0") == "1", key="cur_exigir")
    if exigir != (config_get("exigir_verificado", "0") == "1"):
        config_set("exigir_verificado", "1" if exigir else "0")
        st.success("Configuración guardada.")
    t0, t_resto = st.tabs(["📥 Programas oficiales (PDF)", "✏️ Editar currículo"])
    with t0:
        v_programas.render()
    with t_resto:
        _panel_curriculo_editor()


def _panel_curriculo_editor():
    c1, c2 = st.columns(2)
    nivel = c1.selectbox("Nivel", NIVELES, key="cur_nivel")
    areas = areas_de(nivel)
    area = c2.selectbox("Área", areas, key="cur_area") if areas else None
    if st.button("♻️ Agregar competencias base que falten", key="cur_sembrar"):
        n = sembrar_curriculo(conexion())
        limpiar_cache()
        st.success(f"Se agregaron {n} competencia(s) base.")
        st.rerun()
    t1, t2, t3, t4 = st.tabs(["Competencias y capacidades", "Desempeños", "Importar Excel / CSV", "Transversales"])
    with t1:
        _cur_competencias(nivel, area)
    with t2:
        _cur_desempenos(nivel, area)
    with t3:
        _cur_importar()
    with t4:
        _cur_transversales()


def _cur_competencias(nivel, area):
    if not area:
        st.info("No hay áreas en este nivel.")
        return
    comps = competencias_de(nivel, area)
    for c in comps:
        with st.expander(("✅ " if c["verificado"] else "⚠️ ") + c["nombre"]):
            nombre = st.text_input("Competencia", c["nombre"], key=f"cn_{c['id']}")
            caps = st.text_area("Capacidades (una por línea)", "\n".join(c["capacidades"]), key=f"cp_{c['id']}", height=130)
            ver = st.checkbox("Verificada con el Programa Curricular oficial", c["verificado"], key=f"cv_{c['id']}")
            b1, b2 = st.columns(2)
            if b1.button("💾 Guardar", key=f"cs_{c['id']}"):
                db_execute("UPDATE curriculo_competencias SET nombre=%s, verificado=%s WHERE id=%s",
                           (nombre.strip(), 1 if ver else 0, c["id"]))
                db_execute("DELETE FROM curriculo_capacidades WHERE competencia_id=%s", (c["id"],))
                execute_many("INSERT INTO curriculo_capacidades (competencia_id, nombre, orden) VALUES (%s,%s,%s)",
                             [(c["id"], x, i) for i, x in enumerate(a_lista(caps), 1)])
                st.success("Guardado ✅")
            if b2.button("🗑️ Eliminar competencia", key=f"cx_{c['id']}"):
                db_execute("DELETE FROM curriculo_desempenos WHERE competencia_id=%s", (c["id"],))
                db_execute("DELETE FROM curriculo_capacidades WHERE competencia_id=%s", (c["id"],))
                db_execute("DELETE FROM curriculo_competencias WHERE id=%s", (c["id"],))
                st.rerun()
    with st.expander("➕ Agregar competencia a esta área"):
        n = st.text_input("Nombre de la competencia", key="nc_nombre")
        k = st.text_area("Capacidades (una por línea)", key="nc_caps", height=100)
        if st.button("Agregar", key="nc_add") and n.strip():
            nuevo, _ = db_execute("INSERT INTO curriculo_competencias (nivel, area, nombre, orden, verificado) "
                                  "VALUES (%s,%s,%s,%s,0)", (nivel, area, n.strip(), len(comps) + 1))
            execute_many("INSERT INTO curriculo_capacidades (competencia_id, nombre, orden) VALUES (%s,%s,%s)",
                         [(nuevo, x, i) for i, x in enumerate(a_lista(k), 1)])
            st.rerun()
    with st.expander("➕ Crear un área nueva en este nivel (ej.: Tutoría)"):
        na = st.text_input("Nombre del área", key="na_nombre")
        nc = st.text_input("Primera competencia del área", key="na_comp")
        if st.button("Crear área", key="na_add") and na.strip() and nc.strip():
            db_execute("INSERT INTO curriculo_competencias (nivel, area, nombre, orden, verificado) VALUES (%s,%s,%s,1,0)",
                       (nivel, na.strip(), nc.strip()))
            st.rerun()


def _cur_desempenos(nivel, area):
    if not area:
        return
    comps = competencias_de(nivel, area)
    if not comps:
        st.info("Esta área no tiene competencias.")
        return
    resumen = [{"competencia": c["nombre"][:60], **{g: len(desempenos_de(c["id"], g)) for g in GRADOS[nivel]}} for c in comps]
    st.caption("Cantidad de desempeños cargados por grado:")
    st.dataframe(pd.DataFrame(resumen), hide_index=True)
    cid = st.selectbox("Competencia", [c["id"] for c in comps], key="des_comp",
                       format_func=lambda i: next(c["nombre"] for c in comps if c["id"] == i)[:90])
    grado = st.selectbox("Grado", GRADOS[nivel], key="des_grado")
    actuales = desempenos_de(cid, grado)
    df = pd.DataFrame([{"desempeño": d["texto"]} for d in actuales], columns=["desempeño"])
    ed = st.data_editor(df, key=f"des_ed_{cid}_{grado}", num_rows="dynamic", hide_index=True,
                        column_config={"desempeño": st.column_config.TextColumn("Desempeño (texto oficial)", width="large")})
    if st.button("💾 Guardar desempeños", type="primary", key=f"des_save_{cid}_{grado}"):
        db_execute("DELETE FROM curriculo_desempenos WHERE competencia_id=%s AND grado=%s AND asignacion_id IS NULL", (cid, grado))
        filas = [(cid, grado, s(t), i) for i, t in enumerate(ed["desempeño"].fillna(""), 1) if s(t)]
        execute_many("INSERT INTO curriculo_desempenos (competencia_id, grado, texto, orden) VALUES (%s,%s,%s,%s)", filas)
        st.success(f"{len(filas)} desempeño(s) guardados ✅")


def _cur_importar():
    st.caption("Sube un Excel o CSV con las columnas: **nivel, area, competencia, grado, desempeno**. "
               "Si la competencia no existe, se crea (sin verificar).")
    plantilla = pd.DataFrame([{"nivel": "Primaria", "area": "Matemática", "competencia": "Resuelve problemas de cantidad",
                               "grado": "3.° grado", "desempeno": "Escribe aquí el desempeño oficial..."}])
    descargar("⬇️ Descargar plantilla (CSV)", plantilla.to_csv(index=False).encode("utf-8-sig"),
              "plantilla_desempenos.csv", "text/csv", "cur_plantilla")
    archivo = st.file_uploader("Archivo", type=["csv", "xlsx"], key="cur_archivo")
    reemplazar = st.checkbox("Reemplazar los desempeños existentes de cada competencia/grado del archivo", value=False)
    if archivo is not None and st.button("📥 Importar", type="primary", key="cur_importar_btn"):
        try:
            df = pd.read_csv(archivo) if archivo.name.lower().endswith(".csv") else pd.read_excel(archivo)
            df.columns = [norm(c).replace(" ", "") for c in df.columns]
            falta = {"nivel", "area", "competencia", "grado", "desempeno"} - set(df.columns)
            if falta:
                st.error(f"Faltan columnas: {', '.join(sorted(falta))}")
                return
            insertados, creadas, limpiados = 0, 0, set()
            for _, r in df.fillna("").iterrows():
                nivel, area, comp, grado, texto = (s(r[k]) for k in ("nivel", "area", "competencia", "grado", "desempeno"))
                if not (nivel and area and comp and grado and texto):
                    continue
                cid = None
                for c in competencias_de(nivel, area):
                    if norm(c["nombre"]) == norm(comp):
                        cid = c["id"]
                if cid is None:
                    cid, _ = db_execute("INSERT INTO curriculo_competencias (nivel, area, nombre, orden, verificado) "
                                        "VALUES (%s,%s,%s,99,0)", (nivel, area, comp))
                    creadas += 1
                if reemplazar and (cid, grado) not in limpiados:
                    db_execute("DELETE FROM curriculo_desempenos WHERE competencia_id=%s AND grado=%s AND asignacion_id IS NULL", (cid, grado))
                    limpiados.add((cid, grado))
                db_execute("INSERT INTO curriculo_desempenos (competencia_id, grado, texto, orden) VALUES (%s,%s,%s,%s)",
                           (cid, grado, texto, insertados + 1))
                insertados += 1
            st.success(f"Importados {insertados} desempeño(s). Competencias nuevas: {creadas}.")
        except Exception as e:
            st.error(f"No se pudo importar: {e}")


def _cur_transversales():
    filas = db_fetch("SELECT id, tipo, nombre, detalle FROM curriculo_transversal ORDER BY id")
    for tipo, titulo in (("competencia", "Competencias transversales"), ("enfoque", "Enfoques transversales")):
        st.markdown(f"**{titulo}** (en «detalle» escribe una capacidad o valor por línea)")
        df = pd.DataFrame([{"nombre": f["nombre"], "detalle": f["detalle"] or ""} for f in filas if f["tipo"] == tipo],
                          columns=["nombre", "detalle"])
        ed = st.data_editor(df, key=f"trans_{tipo}", num_rows="dynamic", hide_index=True,
                            column_config={"detalle": st.column_config.TextColumn("detalle", width="large")})
        if st.button(f"💾 Guardar {titulo.lower()}", key=f"trans_save_{tipo}"):
            db_execute("DELETE FROM curriculo_transversal WHERE tipo=%s", (tipo,))
            execute_many("INSERT INTO curriculo_transversal (tipo, nombre, detalle) VALUES (%s,%s,%s)",
                         [(tipo, s(r["nombre"]), s(r["detalle"])) for _, r in ed.fillna("").iterrows() if s(r["nombre"])])
            limpiar_cache()
            st.success("Guardado ✅")


# ------------------------------------------------------------------
# IA: claves y modelos (se aplican al instante, sin reiniciar)
# ------------------------------------------------------------------
def _guardar_ia(prov):
    ss = st.session_state
    nueva = (ss.get(f"ia_k_{prov}") or "").strip()
    modelo = (ss.get(f"ia_m_{prov}") or "").strip()
    if nueva and (" " in nueva or len(nueva) > 250):
        flash("Esa clave no parece válida (tiene espacios o es demasiado larga). No se guardó nada.", "error")
        return
    if nueva:
        config_set(f"ia_{prov}_key", nueva)
    config_set(f"ia_{prov}_model", modelo)
    ss[f"ia_k_{prov}"] = ""  # se borra el campo para que la clave no quede en pantalla
    flash(f"{PROVEEDORES[prov]['nombre']}: guardado ✅ Ya lo usa todo el sistema. Pulsa «Probar» para comprobarlo.")


def _quitar_ia(prov):
    config_set(f"ia_{prov}_key", "")
    flash(f"Se quitó la clave del panel para {PROVEEDORES[prov]['nombre']}. "
          "Si hay una en Secrets, se usará esa.", "info")


def panel_ia():
    st.subheader("Proveedores de IA")
    st.caption("Orden automático: **OpenRouter** primero; si falla, **Gemini**. Las claves que guardes aquí tienen "
               "prioridad sobre las de Secrets. Nunca se muestran completas.")
    for prov, etiqueta in (("openrouter", "OpenRouter · principal"), ("gemini", "Gemini · respaldo")):
        with st.container(border=True):
            st.markdown(f"**{etiqueta}**")
            k, origen = clave_de(prov), origen_clave(prov)
            if not k:
                st.error("Sin clave configurada.")
            else:
                donde = "panel de Administración" if origen == "panel" else "Secrets de Streamlit"
                st.success(f"Clave configurada (termina en …{k[-4:]}) · origen: {donde}")
            st.text_input("Pegar una clave nueva (déjalo vacío para no cambiarla)", type="password", key=f"ia_k_{prov}")
            st.text_input("Modelo", value=modelo_de(prov), key=f"ia_m_{prov}",
                          help="Ejemplos: openai/gpt-4o-mini en OpenRouter. En Gemini usa el nombre exacto que vea tu cuenta.")
            c1, c2, c3 = st.columns(3)
            c1.button("💾 Guardar", key=f"ia_g_{prov}", type="primary", on_click=_guardar_ia, args=(prov,),
                      use_container_width=True)
            if c2.button("🧪 Probar", key=f"ia_t_{prov}", use_container_width=True):
                with st.spinner("Probando..."):
                    ok, msg, ms = probar_proveedor(prov)
                (st.success if ok else st.error)(f"{'✅' if ok else '❌'} {msg} ({ms:.0f} ms)")
            c3.button("🗑️ Quitar del panel", key=f"ia_q_{prov}", on_click=_quitar_ia, args=(prov,),
                      use_container_width=True, disabled=origen != "panel")
    st.markdown("#### Últimos intentos (sin claves)")
    reg = registros_recientes(20)
    if reg:
        st.dataframe(pd.DataFrame(reg), hide_index=True)
    else:
        st.caption("Todavía no hay registros.")


# ------------------------------------------------------------------
# NORMATIVA
# ------------------------------------------------------------------
def panel_normativa(admin_id):
    st.subheader("Actualización normativa MINEDU")
    st.caption("La IA detecta cambios y los resume; nada se usa en los documentos hasta que lo apruebes. "
               "La IA no modifica el currículo oficial.")
    fuentes = db_fetch("SELECT * FROM normativa_fuentes ORDER BY id")
    if st.button("🔄 Revisar todas las fuentes activas ahora", type="primary", key="norm_revisar"):
        with st.spinner("Consultando fuentes oficiales y analizando cambios..."):
            for f in fuentes:
                if f["activa"]:
                    estado, msg = revisar_fuente(f)
                    st.write(f"{ {'nueva': '🆕', 'sin_cambios': '✅', 'error': '⚠️'}[estado] } **{f['nombre']}** — {msg}")
    st.markdown("#### Pendientes de revisión")
    pend = db_fetch("SELECT v.id, f.nombre, f.tipo, v.resumen_cambios, v.detectado_en FROM normativa_versiones v "
                    "JOIN normativa_fuentes f ON f.id = v.fuente_id WHERE v.estado='pendiente' ORDER BY v.id DESC")
    if not pend:
        st.success("No hay cambios pendientes.")
    for p in pend:
        with st.expander(f"🆕 {p['nombre']} · {p['tipo']} · {p['detectado_en']:%d/%m/%Y %H:%M}"):
            st.markdown(p["resumen_cambios"] or "_Sin resumen_")
            b1, b2, _ = st.columns([1, 1, 3])
            if b1.button("✅ Aprobar", key=f"ap_{p['id']}"):
                db_execute("UPDATE normativa_versiones SET estado='aprobada', aprobado_por=%s, aprobado_en=NOW() WHERE id=%s",
                           (admin_id, p["id"]))
                st.rerun()
            if b2.button("❌ Rechazar", key=f"rj_{p['id']}"):
                db_execute("UPDATE normativa_versiones SET estado='rechazada', aprobado_por=%s, aprobado_en=NOW() WHERE id=%s",
                           (admin_id, p["id"]))
                st.rerun()
    st.markdown("#### Fuentes monitoreadas")
    if fuentes:
        st.dataframe(pd.DataFrame(fuentes).drop(columns=["url"]), hide_index=True)
        opciones = {f["id"]: f"{f['id']} · {f['nombre']}" for f in fuentes}
        fid = st.selectbox("Fuente", list(opciones.keys()), format_func=lambda k: opciones[k], key="adm_fuente_sel")
        f = next(x for x in fuentes if x["id"] == fid)
        c1, c2 = st.columns(2)
        if c1.button("⏯️ Activar / desactivar", key=f"tg_{fid}"):
            db_execute("UPDATE normativa_fuentes SET activa=%s WHERE id=%s", (0 if f["activa"] else 1, fid))
            st.rerun()
        if c2.button("🗑️ Eliminar fuente y su historial", key=f"fd_{fid}"):
            db_execute("DELETE FROM normativa_versiones WHERE fuente_id=%s", (fid,))
            db_execute("DELETE FROM normativa_fuentes WHERE id=%s", (fid,))
            st.rerun()
    with st.expander("➕ Agregar fuente (MINEDU, DRE o UGEL)"):
        with st.form("nueva_fuente", clear_on_submit=True):
            n_nombre = st.text_input("Nombre")
            n_url = st.text_input("URL (página web HTML)")
            n_tipo = st.selectbox("Tipo de cambio que suele traer", TIPOS_NORMA)
            enviar = st.form_submit_button("Agregar", type="primary")
        if enviar:
            if n_nombre.strip() and n_url.strip().startswith(("http://", "https://")):
                db_execute("INSERT INTO normativa_fuentes (nombre, url, tipo) VALUES (%s,%s,%s)",
                           (n_nombre.strip(), n_url.strip(), n_tipo))
                st.success("Fuente agregada.")
                st.rerun()
            else:
                st.warning("Escribe un nombre y una URL que empiece con http:// o https://")
    st.markdown("#### Historial de versiones")
    hist = db_fetch("SELECT v.id, f.nombre AS fuente, v.estado, v.detectado_en, v.aprobado_en FROM normativa_versiones v "
                    "JOIN normativa_fuentes f ON f.id = v.fuente_id ORDER BY v.id DESC LIMIT 30")
    if hist:
        st.dataframe(pd.DataFrame(hist), hide_index=True)


# ------------------------------------------------------------------
def panel_costos():
    st.subheader("Costo en créditos por acción")
    st.caption("Lo que paga un docente cada vez que la IA genera algo (0 = gratis). El administrador nunca paga.")
    valores = {}
    cols = st.columns(3)
    for i, (clave, nombre) in enumerate(NOMBRES_COSTO.items()):
        valores[clave] = cols[i % 3].number_input(nombre, 0, 100, costo_de(clave), key=f"costo_{clave}")
    if st.button("💾 Guardar costos", type="primary", key="costos_save"):
        for clave, v in valores.items():
            config_set(f"costo_{clave}", int(v))
        st.success("Costos guardados ✅")


# ------------------------------------------------------------------
def panel_diagnostico():
    st.subheader("Diagnóstico del sistema")
    st.caption("Comprueba en un clic la velocidad de la base de datos, las claves de IA, las tablas y el acceso al MINEDU.")
    if not st.button("▶️ Ejecutar pruebas", type="primary", key="diag_run"):
        return
    filas = []

    def probar(nombre, fn):
        t0 = time.time()
        try:
            estado, detalle = fn()
        except Exception as e:
            estado, detalle = "❌", f"{type(e).__name__}: {e}"
        filas.append((estado, nombre, detalle, f"{(time.time() - t0) * 1000:.0f} ms"))

    def _bd():
        ms = medir_latencia(5)
        if ms < 120:
            return "✅", f"{ms:.0f} ms por consulta: buena velocidad."
        return "⚠️", (f"{ms:.0f} ms por consulta: es lento. Tu base de Aiven probablemente está lejos de Streamlit Cloud; "
                     "crea el servicio de Aiven en una región de EE. UU. (la misma zona de Google Cloud) para ganar velocidad.")

    def _tablas():
        existentes = {f["TABLE_NAME"] if "TABLE_NAME" in f else list(f.values())[0]
                      for f in db_fetch("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()")}
        necesarias = {"usuarios", "asignaciones", "documentos", "curriculo_competencias", "curriculo_desempenos",
                      "eventos", "config", "normativa_versiones"}
        faltan = necesarias - {x.lower() for x in existentes}
        return ("✅", "Todas las tablas existen.") if not faltan else ("❌", "Faltan tablas: " + ", ".join(sorted(faltan)))

    def _secrets():
        faltan = [PROVEEDORES[p]["nombre"] for p in ("openrouter", "gemini") if not clave_de(p)]
        for x in ("mysql", "admin"):
            if x not in st.secrets:
                faltan.append(f"Secrets [{x}]")
        return ("✅", "Claves y Secrets completos.") if not faltan else ("⚠️", "Falta configurar: " + ", ".join(faltan))

    def _or():
        if not clave_de("openrouter"):
            return "⚠️", "No hay clave de OpenRouter (panel IA o Secrets)."
        return "✅", "Respondió: " + llamar_openrouter("Responde solo con la palabra: ok")[:40]

    def _gem():
        if not clave_de("gemini"):
            return "⚠️", "No hay clave de Gemini (panel IA o Secrets)."
        return "✅", "Respondió: " + llamar_gemini("Responde solo con la palabra: ok")[:40]

    def _minedu():
        r = requests.get(PORTALES[0], timeout=25, headers={"User-Agent": "Mozilla/5.0"})
        return ("✅", f"gob.pe respondió ({r.status_code}).") if r.status_code < 400 else ("⚠️", f"gob.pe respondió {r.status_code}.")

    def _libs():
        import docx, pypdf  # noqa: F401
        return "✅", "python-docx y pypdf instalados."

    probar("Velocidad de la base de datos", _bd)
    probar("Tablas de la base de datos", _tablas)
    probar("Secrets (claves)", _secrets)
    probar("IA principal: OpenRouter", _or)
    probar("IA de respaldo: Gemini", _gem)
    probar("Acceso a gob.pe (MINEDU)", _minedu)
    probar("Librerías de Word y PDF", _libs)
    for estado, nombre, detalle, tiempo in filas:
        st.markdown(f"{estado} **{nombre}** · {tiempo}  \n{detalle}")
