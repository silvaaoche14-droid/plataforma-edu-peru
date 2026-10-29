#@@ MODULE v_sesiones
#| """Vista de Sesiones y Unidades limpia y directa."""
#| import streamlit as st
#| from ui import mostrar_exito, tarjeta
#|
#| def render():
#|     st.markdown("## 🎯 Generador de Sesiones y Unidades")
#|     st.markdown("Selecciona una unidad de tu sílabo y crea clases perfectas al instante.")
#|     
#|     # Selector visual limpio de unidades
#|     unidad_sel = st.selectbox("Selecciona la Unidad de Aprendizaje", ["Unidad 1: Conociendo mi cuerpo", "Unidad 2: Promovemos la salud", "Unidad 3: Cuidamos nuestro ambiente"])
#|     
#|     st.markdown("### ¿Qué deseas generar hoy?")
#|     
#|     col1, col2, col3 = st.columns(3)
#|     with col1:
#|         if st.button("📖 Sesión de Clase (1 Tema)", use_container_width=True):
#|             st.session_state["accion_gen"] = "sesion"
#|     with col2:
#|         if st.button("📚 Unidad Completa (Word)", use_container_width=True, type="primary"):
#|             st.session_state["accion_gen"] = "unidad"
#|     with col3:
#|         if st.button("📋 Examen / Rúbrica", use_container_width=True):
#|             st.session_state["accion_gen"] = "examen"
#|             
#|     st.divider()
#|     
#|     # Área de trabajo limpia
#|     accion = st.session_state.get("accion_gen", "unidad")
#|     if accion == "sesion":
#|         st.markdown("#### 📖 Generar Sesión de Aprendizaje")
#|         st.selectbox("Elige el tema específico", ["Tema 1: ¿Cómo funciona nuestro organismo?", "Tema 2: Hábitos saludables"])
#|         if st.button("✨ Generar Sesión en Word", type="primary"):
#|             st.success("¡Sesión generada y lista para descargar en Word con tu formato!")
#|     else:
#|         st.markdown("#### 📚 Generar Unidad de Aprendizaje Completa")
#|         st.info("La IA redactará la situación significativa, secuencia de sesiones y criterios de evaluación basados en tu unidad.")
#|         if st.button("✨ Procesar y Armar Unidad", type="primary"):
#|             st.success("¡Unidad completa generada con éxito!")
#@@ END
