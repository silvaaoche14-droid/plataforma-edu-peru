# EduPerú IA

Portal docente con IA (OpenRouter + Gemini de respaldo) alineado al CNEB y la RM N.° 501-2025-MINEDU.

## Estructura
```
app.py                       Punto de entrada (página, sesión, menú lateral, rutas)
requirements.txt
crear_zip.py                 Genera eduperu_ia.zip
.streamlit/config.toml       Tema base
.streamlit/secrets.toml.example   Plantilla de Secrets
eduperu/
  core/        util · db (MySQL/Aiven) · repo · auth · ia · normativa
  services/    curriculo · render (Word/HTML) · exportar · programas · lineamientos · calendario
  ui/          theme (CSS del sistema de diseño) · components (navegación, campos, editores)
  views/       panel · anual · unidades · sesiones · examen_unidad · calendario · curriculo_oficial
               biblioteca · programas_admin · admin
```
Regla de dependencias: `views → ui/services → core`. `core` nunca importa de `views`.

## Despliegue
1. Sube todo el contenido a GitHub (sin `secrets.toml`).
2. En Streamlit Cloud: *Main file path* = `app.py`.
3. En *Settings → Secrets* pega el contenido de `.streamlit/secrets.toml.example` con tus valores (`[mysql]` y `[admin]` son obligatorios).
4. Las tablas se crean/actualizan solas al iniciar (`CREATE TABLE IF NOT EXISTS`); no se borra nada.
5. Claves de IA: Administración → 🤖 IA.

## Cambiar el aspecto
Todo el CSS está en `eduperu/ui/theme.py` (tokens en `:root`).
