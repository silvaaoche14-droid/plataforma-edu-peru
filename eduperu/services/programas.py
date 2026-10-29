"""Programas Curriculares oficiales (PDF de gob.pe): buscar, leer, extraer desempeños y verificarlos.

Reglas de oro:
- La IA NO busca en internet ni inventa: el sistema descarga las páginas oficiales y la IA solo ordena texto.
- Todo desempeño/estándar que la IA devuelva debe aparecer en el PDF (comparación tolerante a saltos de línea
  y signos); si no aparece, se descarta.
- Lo extraído entra como «pendiente» y solo el administrador lo aprueba.
"""
import hashlib
import io
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from eduperu.services.curriculo import GRADOS, areas_de, competencias_de
from eduperu.core.db import execute, execute_many, fetch
from eduperu.core.ia import pedir_json
from eduperu.core.util import norm, s

UA = {"User-Agent": "Mozilla/5.0 (compatible; EduPeruIA-Programas/1.0)"}
PORTALES = [
    "https://www.gob.pe/es/90158-ministerio-de-educacion-programas-curriculares-de-la-educacion-basica-regular",
    "https://www.gob.pe/institucion/minedu/campa%C3%B1as/106784-curriculo-nacional-de-la-educacion-basica",
]
MAX_MB = 120
CICLOS_VALIDOS = ["II", "III", "IV", "V", "VI", "VII"]


def nivel_probable(texto):
    t = norm(texto)
    for n in ("inicial", "primaria", "secundaria"):
        if n in t:
            return n.capitalize()
    return ""


# ------------------------------------------------------------------
# 1) BUSCAR en las páginas oficiales
# ------------------------------------------------------------------
def _titulo_pagina(soup):
    h = soup.find("h1") or soup.title
    return h.get_text(" ", strip=True) if h else ""


def _firma_remota(url):
    try:
        h = requests.head(url, headers=UA, timeout=20, allow_redirects=True)
        return "|".join(h.headers.get(k, "") for k in ("ETag", "Last-Modified", "Content-Length"))[:300]
    except Exception:
        return ""


def buscar_programas():
    """Recorre las páginas oficiales y registra los PDF de Programas Curriculares.
    Devuelve (lista de PDF registrados, lista de avisos/errores)."""
    avisos, hallados, vistos = [], {}, set()
    por_visitar = list(PORTALES)
    for paso in range(2):
        siguientes = []
        for url in por_visitar:
            if url in vistos:
                continue
            vistos.add(url)
            try:
                r = requests.get(url, headers=UA, timeout=40)
                r.raise_for_status()
            except Exception as e:
                avisos.append(f"No se pudo abrir {url}: {e}")
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            titulo_pag = _titulo_pagina(soup)
            for a in soup.find_all("a", href=True):
                href = urljoin(url, a["href"]).split("#")[0]
                texto = a.get_text(" ", strip=True)
                if href.lower().split("?")[0].endswith(".pdf"):
                    # Si el enlace dice solo «Descargar», se usa el título de la página; si dice otra cosa, se usa su texto
                    generico = norm(texto) in ("", "descargar", "ver", "descargar pdf", "pdf", "descargar archivo")
                    titulo = titulo_pag if generico else texto
                    contexto = norm(f"{titulo} {href}")
                    if "curricul" in contexto or "programa" in contexto:
                        hallados.setdefault(href, {"url": href, "titulo": titulo[:300], "origen": url})
                elif paso == 0 and "gob.pe" in href and (
                        "programa-curricular" in href.lower() or "programa curricular" in norm(texto)):
                    siguientes.append(href)
        por_visitar = siguientes[:20]
    if not hallados:
        avisos.append("No se encontraron PDF en las páginas oficiales (puede que gob.pe cargue su contenido con "
                      "JavaScript o bloquee el acceso). Usa «Pegar URL» o «Subir PDF».")

    nuevos = []
    for url, h in hallados.items():
        ex = fetch("SELECT id, firma, estado FROM curriculo_pdf WHERE url=%s", (url,), one=True)
        if ex is None:
            nid, _ = execute("INSERT INTO curriculo_pdf (url, titulo, nivel, origen, firma, estado) "
                             "VALUES (%s,%s,%s,%s,%s,'nuevo')",
                             (url, h["titulo"], nivel_probable(f"{h['titulo']} {url} {h['origen']}"), h["origen"],
                              _firma_remota(url)))
            nuevos.append(nid)
        elif ex["estado"] == "leido":
            firma = _firma_remota(url)
            if firma and ex["firma"] and firma != ex["firma"]:
                execute("UPDATE curriculo_pdf SET estado='actualizado', firma=%s WHERE id=%s", (firma, ex["id"]))
    _clasificar_con_ia(nuevos)
    return fetch("SELECT * FROM curriculo_pdf ORDER BY id DESC"), avisos


def _clasificar_con_ia(ids):
    """La IA solo ayuda a decidir el nivel de los PDF cuyo título no lo dice (no navega por internet)."""
    pend = [f for f in (fetch("SELECT id, titulo, url, nivel FROM curriculo_pdf WHERE id=%s", (i,), one=True) for i in ids)
            if f and not f["nivel"]]
    if not pend:
        return
    lista = "\n".join(f"{i}. título: {f['titulo']} | url: {f['url']}" for i, f in enumerate(pend))
    try:
        datos, _ = pedir_json(
            "Clasifica estos documentos publicados por el MINEDU (Perú). Para cada uno indica a qué nivel de la "
            "Educación Básica Regular corresponde (Inicial, Primaria, Secundaria) o 'Otro', y si es un Programa "
            f"Curricular oficial (true/false).\n{lista}\n"
            'Formato: {"clasificacion":[{"i":0,"nivel":"Primaria","es_programa":true}]}')
        for x in datos.get("clasificacion", []):
            f = pend[int(x["i"])]
            nivel = x.get("nivel") if x.get("nivel") in ("Inicial", "Primaria", "Secundaria") else ""
            estado = "nuevo" if x.get("es_programa", True) else "descartado"
            execute("UPDATE curriculo_pdf SET nivel=%s, estado=%s WHERE id=%s", (nivel, estado, f["id"]))
    except Exception:
        pass  # el administrador puede elegir el nivel a mano


# ------------------------------------------------------------------
# 2) DESCARGAR y LEER el PDF (se guarda el texto por página)
# ------------------------------------------------------------------
def registrar_url(url, titulo="", nivel=""):
    ex = fetch("SELECT id FROM curriculo_pdf WHERE url=%s", (url,), one=True)
    if ex:
        return ex["id"]
    nid, _ = execute("INSERT INTO curriculo_pdf (url, titulo, nivel, origen, estado) VALUES (%s,%s,%s,%s,'nuevo')",
                     (url, titulo or url[-80:], nivel or nivel_probable(f"{titulo} {url}"), "manual"))
    return nid


def _guardar_paginas(pdf_id, datos: bytes, firma=""):
    from pypdf import PdfReader
    lector = PdfReader(io.BytesIO(datos))
    execute("DELETE FROM curriculo_pdf_paginas WHERE pdf_id=%s", (pdf_id,))
    filas = []
    for n, pagina in enumerate(lector.pages, 1):
        try:
            texto = pagina.extract_text() or ""
        except Exception:
            texto = ""
        filas.append((pdf_id, n, texto))
        if len(filas) >= 40:
            execute_many("INSERT INTO curriculo_pdf_paginas (pdf_id, pagina, texto) VALUES (%s,%s,%s)", filas)
            filas = []
    execute_many("INSERT INTO curriculo_pdf_paginas (pdf_id, pagina, texto) VALUES (%s,%s,%s)", filas)
    execute("UPDATE curriculo_pdf SET paginas=%s, hash_contenido=%s, firma=%s, estado='leido', leido_en=NOW() WHERE id=%s",
            (len(lector.pages), hashlib.sha256(datos).hexdigest(), firma or "", pdf_id))
    return len(lector.pages)


def descargar_y_leer(pdf_id):
    f = fetch("SELECT url FROM curriculo_pdf WHERE id=%s", (pdf_id,), one=True)
    r = requests.get(f["url"], headers=UA, timeout=180, stream=True)
    r.raise_for_status()
    datos = b""
    for trozo in r.iter_content(1024 * 512):
        datos += trozo
        if len(datos) > MAX_MB * 1024 * 1024:
            raise RuntimeError(f"El PDF pesa más de {MAX_MB} MB.")
    if not datos.startswith(b"%PDF"):
        raise RuntimeError("El enlace no devolvió un PDF (puede requerir abrirse desde el navegador).")
    firma = "|".join(r.headers.get(k, "") for k in ("ETag", "Last-Modified", "Content-Length"))[:300]
    return _guardar_paginas(pdf_id, datos, firma)


def leer_subido(nombre, datos: bytes, nivel=""):
    if not datos.startswith(b"%PDF"):
        raise RuntimeError("El archivo no es un PDF.")
    pdf_id = registrar_url(f"subido:{nombre}", nombre, nivel)
    return pdf_id, _guardar_paginas(pdf_id, datos)


# ------------------------------------------------------------------
# 3) EXTRAER con IA y VERIFICAR contra el texto del PDF
# ------------------------------------------------------------------
def mapear_grado(valor, nivel):
    m = re.search(r"\d", str(valor or ""))
    if not m:
        return None
    n = m.group(0)
    for g in GRADOS[nivel]:
        if g.startswith(n):
            return g
    return None


def mapear_ciclo(valor):
    v = str(valor or "").upper().replace("CICLO", "").strip()
    return v if v in CICLOS_VALIDOS else None


def _pagina_de(texto_norm, paginas):
    for numero, _, pn in paginas:
        if texto_norm in pn:
            return numero
    return 0


def extraer_items(paginas, nivel, trabajos, progreso=None):
    """Núcleo de la extracción: devuelve (items, resumen).
    paginas = [(n, texto, texto_normalizado)], trabajos = [(area, competencia)].
    item = (competencia_id, tipo, grado_o_ciclo, texto_verificado, pagina)."""
    resumen = {"verificados": 0, "descartados": 0, "sin_paginas": []}
    items = []
    for k, (area, c) in enumerate(trabajos, 1):
        if progreso:
            progreso(k / len(trabajos), f"{area} · {c['nombre'][:60]}")
        clave = norm(c["nombre"])[:70]
        cand = [p for p in paginas if clave in p[2] and ("desempe" in p[2] or "estandar" in p[2])][:8]
        if not cand:
            resumen["sin_paginas"].append(f"{area}: {c['nombre']}")
            continue
        plano = " ".join(p[2] for p in cand)
        texto = "\n".join(f"[Página {p[0]}]\n{p[1]}" for p in cand)[:24000]
        try:
            datos, _ = pedir_json(f"""Del siguiente texto de un Programa Curricular (lineamientos oficiales, Perú), nivel {nivel}, extrae para la competencia «{c['nombre']}»:
- "desempenos": los desempeños de cada grado ({', '.join(GRADOS[nivel])}). Cada uno con "grado" y "texto".
- "estandares": el estándar de aprendizaje de cada ciclo. Cada uno con "ciclo" (II, III, IV, V, VI o VII) y "texto".
COPIA cada texto EXACTAMENTE como aparece en el documento, sin cambiar, resumir ni agregar palabras. Si no encuentras algo, no lo incluyas. No inventes.
Formato: {{"desempenos":[{{"grado":"3.° grado","texto":"..."}}],"estandares":[{{"ciclo":"IV","texto":"..."}}]}}

TEXTO:
{texto}""")
        except Exception:
            resumen["sin_paginas"].append(f"{area}: {c['nombre']} (la IA no respondió)")
            continue
        for tipo, lista, mapear in (("desempeno", datos.get("desempenos") or [], lambda x: mapear_grado(x.get("grado"), nivel)),
                                    ("estandar", datos.get("estandares") or [], lambda x: mapear_ciclo(x.get("ciclo")))):
            for x in lista:
                if not isinstance(x, dict):
                    continue
                clave_g, t = mapear(x), s(x.get("texto"))
                tn = norm(t)
                if clave_g and len(tn) > 25 and tn in plano:
                    items.append((c["id"], tipo, clave_g, t, _pagina_de(tn, cand)))
                    resumen["verificados"] += 1
                else:
                    resumen["descartados"] += 1
    return items, resumen


def paginas_guardadas(pdf_id):
    filas = fetch("SELECT pagina, texto FROM curriculo_pdf_paginas WHERE pdf_id=%s ORDER BY pagina", (pdf_id,))
    if not filas:
        raise RuntimeError("Primero hay que descargar y leer el PDF.")
    return [(f["pagina"], f["texto"], norm(f["texto"])) for f in filas]


def poner_en_cola(pdf_id, items):
    """Deja los textos extraídos como «pendientes» para que el administrador los apruebe."""
    for cid in {i[0] for i in items}:
        execute("DELETE FROM curriculo_importado WHERE pdf_id=%s AND competencia_id=%s AND estado='pendiente'",
                (pdf_id, cid))
    execute_many("INSERT INTO curriculo_importado (pdf_id, competencia_id, tipo, grado, texto, pagina) "
                 "VALUES (%s,%s,%s,%s,%s,%s)", [(pdf_id,) + i for i in items])


def extraer(pdf_id, nivel, areas=None, progreso=None):
    """Extrae desempeños y estándares del PDF ya leído y los deja pendientes de aprobación."""
    paginas = paginas_guardadas(pdf_id)
    trabajos = [(a, c) for a in (areas or areas_de(nivel)) for c in competencias_de(nivel, a)]
    items, resumen = extraer_items(paginas, nivel, trabajos, progreso)
    poner_en_cola(pdf_id, items)
    return resumen


# ------------------------------------------------------------------
# 4) REVISIÓN: aprobar / rechazar
# ------------------------------------------------------------------
def pendientes(pdf_id):
    return fetch("SELECT i.id, i.competencia_id, c.area, c.nombre AS competencia, i.tipo, i.grado, i.texto, i.pagina "
                 "FROM curriculo_importado i JOIN curriculo_competencias c ON c.id = i.competencia_id "
                 "WHERE i.pdf_id=%s AND i.estado='pendiente' ORDER BY c.area, c.id, i.tipo, i.grado, i.id", (pdf_id,))


def aprobar(ids, marcar_verificada=True, fuente=""):
    """Pasa lo aprobado a la base curricular (reemplaza lo anterior de esa competencia y grado/ciclo)."""
    if not ids:
        return 0
    marcas = ",".join(["%s"] * len(ids))
    filas = fetch(f"SELECT * FROM curriculo_importado WHERE id IN ({marcas}) ORDER BY id", tuple(ids))
    grupos = {}
    for f in filas:
        grupos.setdefault((f["competencia_id"], f["tipo"], f["grado"]), []).append(f)
    for (cid, tipo, clave), items in grupos.items():
        if tipo == "desempeno":
            execute("DELETE FROM curriculo_desempenos WHERE competencia_id=%s AND grado=%s AND asignacion_id IS NULL", (cid, clave))
            execute_many("INSERT INTO curriculo_desempenos (competencia_id, grado, texto, orden) VALUES (%s,%s,%s,%s)",
                         [(cid, clave, x["texto"], i) for i, x in enumerate(items, 1)])
        else:
            execute("DELETE FROM curriculo_estandares WHERE competencia_id=%s AND ciclo=%s AND asignacion_id IS NULL", (cid, clave))
            execute("INSERT INTO curriculo_estandares (competencia_id, ciclo, texto) VALUES (%s,%s,%s)",
                    (cid, clave, items[0]["texto"]))
    if marcar_verificada:
        for cid in {f["competencia_id"] for f in filas}:
            execute("UPDATE curriculo_competencias SET verificado=1, verificado_en=NOW(), fuente=%s WHERE id=%s",
                    (fuente[:600], cid))
    execute(f"UPDATE curriculo_importado SET estado='aprobado' WHERE id IN ({marcas})", tuple(ids))
    return len(filas)


def rechazar(ids):
    if ids:
        marcas = ",".join(["%s"] * len(ids))
        execute(f"UPDATE curriculo_importado SET estado='rechazado' WHERE id IN ({marcas})", tuple(ids))
