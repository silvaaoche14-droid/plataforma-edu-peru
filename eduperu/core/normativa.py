"""Monitor normativo del MINEDU: detecta cambios en fuentes oficiales; el administrador aprueba."""
import hashlib
from typing import Optional
import requests
from bs4 import BeautifulSoup
from eduperu.core.db import fetch as db_fetch, execute as db_execute
from eduperu.core.ia import generar_texto

UA = {"User-Agent": "Mozilla/5.0 (compatible; EduPeruIA-MonitorNormativo/1.0)"}


def html_a_texto(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "header", "footer", "nav", "form"]):
        t.decompose()
    return " ".join(soup.get_text(" ").split())


def resumir_cambios(nombre: str, nuevo: str, anterior: Optional[str]) -> str:
    if anterior:
        prompt = f"""Compara dos capturas de texto de la fuente oficial «{nombre}» (MINEDU, Perú).
Indica SOLO los cambios relevantes para docentes y colegios y clasifícalos en:
curricular / pedagógico-normativo / administrativo.
Si no hay cambios sustantivos (solo ruido de la página), responde exactamente: "Sin cambios sustantivos (posible ruido de la página)".
No inventes nada que no esté en los textos.

=== VERSIÓN ANTERIOR ===
{anterior[:12000]}

=== VERSIÓN NUEVA ===
{nuevo[:12000]}"""
    else:
        prompt = f"""Resume en español la fuente oficial «{nombre}» (MINEDU, Perú) a partir de este texto.
Indica: qué norma o documento es, vigencia y los puntos clave aplicables a la planificación docente.
No inventes nada que no esté en el texto.

{nuevo[:15000]}"""
    try:
        texto, _ = generar_texto(prompt)
        return texto
    except Exception as e:
        return f"(No se pudo generar el resumen con IA: {e})"


def revisar_fuente(f: dict):
    """Devuelve (estado, mensaje): estado = nueva | sin_cambios | error."""
    try:
        r = requests.get(f["url"], headers=UA, timeout=30)
        r.raise_for_status()
        if "pdf" in r.headers.get("content-type", "").lower():
            return "error", "La fuente es un PDF (por ahora solo se leen páginas HTML)."
        texto = html_a_texto(r.text)[:200000]
        if len(texto) < 200:
            return "error", "La página devolvió muy poco texto (puede requerir JavaScript)."
    except Exception as e:
        return "error", f"No se pudo leer la fuente: {e}"

    h = hashlib.sha256(texto.encode()).hexdigest()
    ultimo = db_fetch(
        "SELECT hash_contenido, contenido FROM normativa_versiones WHERE fuente_id=%s ORDER BY id DESC LIMIT 1",
        (f["id"],), one=True,
    )
    db_execute("UPDATE normativa_fuentes SET ultima_revision=NOW() WHERE id=%s", (f["id"],))
    if ultimo and ultimo["hash_contenido"] == h:
        return "sin_cambios", "Sin cambios desde la última captura."

    resumen = resumir_cambios(f["nombre"], texto, ultimo["contenido"] if ultimo else None)
    db_execute(
        "INSERT INTO normativa_versiones (fuente_id, hash_contenido, contenido, resumen_cambios) VALUES (%s,%s,%s,%s)",
        (f["id"], h, texto, resumen),
    )
    return "nueva", "Nueva versión detectada, pendiente de aprobación."


def normativa_vigente():
    """(contexto para el prompt, etiqueta para el documento)."""
    filas = db_fetch(
        "SELECT f.nombre, v.resumen_cambios, v.aprobado_en FROM normativa_versiones v "
        "JOIN normativa_fuentes f ON f.id = v.fuente_id "
        "WHERE v.estado='aprobada' ORDER BY v.aprobado_en DESC LIMIT 5"
    )
    if not filas:
        return "", "RM N.° 501-2025-MINEDU"
    ctx = "\n\n".join(
        f"[{f['nombre']} · aprobada {f['aprobado_en']:%d/%m/%Y}]\n{f['resumen_cambios']}" for f in filas
    )[:4000]
    etiqueta = (f"RM N.° 501-2025-MINEDU + {len(filas)} actualización(es) verificada(s) "
                f"(última {filas[0]['aprobado_en']:%d/%m/%Y})")
    return ctx, etiqueta[:255]
