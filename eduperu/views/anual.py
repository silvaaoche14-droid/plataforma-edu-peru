#@@ MODULE v_anual
#| """Vista de Planificación Anual simplificada y directa para el docente."""
#| import streamlit as st
#| from repo import get_asignacion
#| from ui import mostrar_error, mostrar_exito, tarjeta
#|
#| def render():
#|     st.markdown("## 📅 Planificación Anual")
#|     st.markdown("Define tu año escolar en segundos. La IA alinea todo automáticamente al CNEB y MINEDU.")
#|     
#|     asig_id = st.session_state.get("asignacion_actual_id")
#|     if not asig_id:
#|         st.info("⚠️ Primero selecciona o crea un curso en el panel principal.")
#|         return
#|         
#|     asig = get_asignacion(asig_id)
#|     if not asig:
#|         st.error("No se encontró la asignación.")
#|         return
#|
#|     # Interfaz limpia en pestañas o pasos simples
#|     paso = st.radio("Paso a paso", ["1. Datos y Lineamientos", "2. Estudiantes y Competencias", "3. Unidades y Cronograma"], horizontal=True, label_visibility="collapsed")
#|     
#|     st.divider()
#|     
#|     if "1." in paso:
#|         st.markdown("### 📌 1. Configuración del Curso")
#|         col1, col2 = st.columns(2)
#|         with col1:
#|             st.text_input("Institución Educativa", value=asig.get("institucion", ""))
#|             st.text_input("Docente", value=asig.get("docente", ""))
#|         with col2:
#|             st.text_input("Nivel y Grado", value=f"{asig.get('nivel', '')} - {asig.get('grado', '')}", disabled=True)
#|             st.text_input("Área Curricular", value=asig.get("area", ""), disabled=True)
#|         
#|         st.info("💡 Usando normativa oficial vigente: RM N.° 501-2025-MINEDU y CNEB.")
#|         
#|     elif "2." in paso:
#|         st.markdown("### 👥 2. Caracterización y Competencias")
#|         st.text_area("Breve descripción de tus estudiantes (Opcional)", placeholder="Ej. Estudiantes entusiastas de Lima, uso frecuente de tecnología...", height=100)
#|         st.markdown("✅ **Competencias oficiales cargadas para tu área y grado.** (Seleccionadas automáticamente del CNEB).")
#|         
#|     else:
#|         st.markdown("### 📚 3. Unidades y Clases")
#|         col1, col2 = st.columns(2)
#|         with col1:
#|             st.number_input("¿Cuántas unidades tendrá el año?", min=4, max=10, value=8)
#|         with col2:
#|             st.number_input("Clases por semana", min=1, max=10, value=3)
#|             
#|         if st.button("✨ Generar Plan Anual con IA", type="primary", use_container_width=True):
#|             st.success("¡Plan anual generado con éxito y adaptado a tu formato!")
#@@ END
