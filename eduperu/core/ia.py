"""IA: OpenRouter primero y Gemini de respaldo, de forma automática.
Las claves se leen primero del panel de Administración (base de datos) y, si no hay, de Secrets.
Nunca se muestran ni se guardan en los registros."""
import json
import re
import time

import requests
import streamlit as st

TIMEOUT = (10, 90)  # (segundos para conectar, segundos para esperar la respuesta)
ORDEN = ["openrouter", "gemini"]
PROVEEDORES = {
    "openrouter": {"nombre": "OpenRouter", "modelo": "openai/gpt-4o-mini"},
    "gemini": {"nombre": "Gemini", "modelo": "gemini-3.8-flash"},
}


class ErrorIA(RuntimeError):
    def __init__(self, status, detalle):
        super().__init__(f"{status}: {detalle}" if status else str(detalle))
        self.status = status


# ------------------------------------------------------------------
# Claves y modelos (panel de Administración primero, Secrets después)
# ------------------------------------------------------------------
def _db(clave):
    try:
        from eduperu.core.db import fetch
        f = fetch("SELECT valor FROM config WHERE clave=%s", (clave,), one=True)
        return (f["valor"] or "").strip() if f else ""
    except Exception:
        return ""


def _secret(seccion, campo):
    try:
        return str(st.secrets[seccion].get(campo, "") or "").strip()
    except Exception:
        return ""


def clave_de(prov):
    return _db(f"ia_{prov}_key") or _secret(prov, "api_key")


def origen_clave(prov):
    if _db(f"ia_{prov}_key"):
        return "panel"
    return "secrets" if _secret(prov, "api_key") else ""


def modelo_de(prov):
    return _db(f"ia_{prov}_model") or _secret(prov, "model") or PROVEEDORES[prov]["modelo"]


def _limpiar(texto):
    """Quita cualquier clave del texto antes de mostrarlo o guardarlo."""
    t = str(texto)
    for p in PROVEEDORES:
        k = clave_de(p)
        if k and len(k) > 6:
            t = t.replace(k, "***")
    t = re.sub(r"(sk-[A-Za-z0-9_\-]{8,}|AIza[A-Za-z0-9_\-]{10,})", "***", t)
    return t[:300]


# ------------------------------------------------------------------
# Registro técnico seguro (tabla nueva ia_registro; no toca nada existente)
# ------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _tabla_registro():
    from eduperu.core.db import conexion
    c = conexion()
    try:
        cur = c.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS ia_registro (
            id INT AUTO_INCREMENT PRIMARY KEY,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            proveedor VARCHAR(20),
            modelo VARCHAR(120),
            ok TINYINT(1),
            ms INT,
            motivo VARCHAR(120),
            detalle VARCHAR(400)
        )""")
        c.commit()
        cur.close()
    finally:
        c.close()
    return True


def _registrar(prov, ok, ms, motivo, detalle=""):
    try:
        _tabla_registro()
        from eduperu.core.db import execute
        execute("INSERT INTO ia_registro (proveedor, modelo, ok, ms, motivo, detalle) VALUES (%s,%s,%s,%s,%s,%s)",
                (prov, modelo_de(prov)[:120], 1 if ok else 0, int(ms), motivo[:120], _limpiar(detalle)[:400]))
    except Exception:
        pass  # el registro nunca debe romper la generación


def registros_recientes(n=20):
    try:
        _tabla_registro()
        from eduperu.core.db import fetch
        return fetch("SELECT creado_en, proveedor, modelo, ok, ms, motivo, detalle FROM ia_registro "
                     "ORDER BY id DESC LIMIT %s", (int(n),))
    except Exception:
        return []


# ------------------------------------------------------------------
# Llamadas a cada proveedor (una sola vez, sin reintentos)
# ------------------------------------------------------------------
def _post(url, **kw):
    r = requests.post(url, timeout=TIMEOUT, **kw)
    if r.status_code >= 400:
        try:
            det = r.json().get("error", {})
            det = det.get("message", r.text) if isinstance(det, dict) else str(det)
        except ValueError:
            det = r.text
        raise ErrorIA(r.status_code, _limpiar(det))
    return r


def llamar_openrouter(prompt: str) -> str:
    k = clave_de("openrouter")
    if not k:
        raise ErrorIA(None, "sin clave")
    r = _post("https://openrouter.ai/api/v1/chat/completions",
              headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json", "X-Title": "EduPeru IA"},
              json={"model": modelo_de("openrouter"), "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 6000})
    datos = r.json()
    if isinstance(datos, dict) and datos.get("error"):
        e = datos["error"]
        raise ErrorIA(e.get("code") if isinstance(e, dict) else None,
                      _limpiar(e.get("message") if isinstance(e, dict) else e))
    try:
        return datos["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        raise ErrorIA(None, "respuesta con formato inesperado")


def llamar_gemini(prompt: str) -> str:
    k = clave_de("gemini")
    if not k:
        raise ErrorIA(None, "sin clave")
    r = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{modelo_de('gemini')}:generateContent",
              headers={"x-goog-api-key": k, "Content-Type": "application/json"},  # la clave NO va en la URL
              json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": 8000}})
    cand = r.json().get("candidates") or []
    if not cand:
        raise ErrorIA(None, "Gemini no devolvió texto (posible bloqueo de contenido)")
    partes = (cand[0].get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in partes)


_LLAMAR = {"openrouter": llamar_openrouter, "gemini": llamar_gemini}


def _motivo(e):
    """Explicación corta y sin datos sensibles, en lenguaje claro."""
    if isinstance(e, requests.exceptions.Timeout):
        return "tardó demasiado en responder"
    if isinstance(e, requests.exceptions.ConnectionError):
        return "no hubo conexión con el servicio"
    st_ = getattr(e, "status", None)
    txt = str(e).lower()
    if st_ in (401, 403) or ("api key" in txt and "valid" in txt):
        return "clave rechazada (inválida, vencida o sin permiso)"
    if st_ == 402:
        return "sin saldo o créditos en la cuenta del proveedor"
    if st_ == 404:
        return "modelo no encontrado (revisa el nombre del modelo)"
    if st_ == 429:
        return "límite de uso alcanzado"
    if isinstance(st_, int) and st_ >= 500:
        return "el servicio tiene fallas temporales"
    if "sin clave" in txt:
        return "sin clave configurada"
    return "respondió con un error"


def generar_texto(prompt: str):
    """Devuelve (texto, proveedor). Siempre prueba OpenRouter primero; si falla, pasa a Gemini.
    Si el primero respondió bien, NO se llama al segundo (no se duplica el contenido)."""
    fallos = []
    for prov in ORDEN:
        nombre = PROVEEDORES[prov]["nombre"]
        if not clave_de(prov):
            fallos.append((nombre, "sin clave configurada"))
            continue
        t0 = time.time()
        try:
            texto = _LLAMAR[prov](prompt)
            if not (texto or "").strip():
                raise ErrorIA(None, "respuesta vacía")
        except Exception as e:
            motivo = _motivo(e)
            _registrar(prov, False, (time.time() - t0) * 1000, motivo, str(e))
            fallos.append((nombre, motivo))
            continue
        _registrar(prov, True, (time.time() - t0) * 1000, "ok")
        return texto, nombre
    detalle = "; ".join(f"{n}: {m}" for n, m in fallos)
    raise RuntimeError(f"La IA no está disponible en este momento ({detalle}). No se descontaron créditos. "
                       "Intenta de nuevo en unos minutos; si continúa, avisa al administrador.")


def probar_proveedor(prov):
    """Para el panel de Administración: (ok, mensaje, milisegundos). No usa el otro proveedor."""
    if not clave_de(prov):
        return False, "No hay clave configurada.", 0
    t0 = time.time()
    try:
        res = _LLAMAR[prov]("Responde solo con la palabra: ok")
        ms = (time.time() - t0) * 1000
        _registrar(prov, True, ms, "prueba ok")
        return True, f"Respondió: {res.strip()[:40]}", ms
    except Exception as e:
        ms = (time.time() - t0) * 1000
        _registrar(prov, False, ms, _motivo(e), str(e))
        return False, f"{_motivo(e)} · {_limpiar(e)}", ms


def parse_json(texto: str):
    """Extrae el primer objeto/arreglo JSON de un texto (tolera ``` y texto alrededor). None si no puede."""
    t = (texto or "").strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    candidatos = []
    for ini, fin in (("{", "}"), ("[", "]")):
        i, j = t.find(ini), t.rfind(fin)
        if i != -1 and j > i:
            candidatos.append((i, t[i:j + 1]))
    for _, trozo in sorted(candidatos):
        try:
            return json.loads(trozo)
        except json.JSONDecodeError:
            continue
    return None


SUFIJO_JSON = ("\n\nResponde ÚNICAMENTE con JSON válido (sin ```, sin comentarios, sin texto antes ni después). "
               "Usa comillas dobles y escribe los saltos de línea dentro de los textos como \\n.")


def pedir_json(prompt: str):
    """Devuelve (datos, proveedor). Reintenta una vez SOLO si la IA respondió pero no con JSON válido."""
    texto, prov = generar_texto(prompt + SUFIJO_JSON)
    datos = parse_json(texto)
    if datos is None:
        texto, prov = generar_texto(prompt + SUFIJO_JSON +
                                    "\n\nIMPORTANTE: tu respuesta anterior no era JSON válido. Devuelve solo el JSON completo.")
        datos = parse_json(texto)
    if datos is None:
        raise RuntimeError("La IA no devolvió un formato válido. Intenta de nuevo.")
    return datos, prov


def preambulo() -> str:
    """Instrucciones comunes + disposiciones normativas aprobadas por el administrador."""
    from eduperu.core.normativa import normativa_vigente
    try:
        ctx, _ = normativa_vigente()
    except Exception:
        ctx = ""
    base = ("Eres un especialista en pedagogía y en el Currículo Nacional de la Educación Básica (CNEB) del Perú, "
            "y trabajas alineado a la RM N.° 501-2025-MINEDU. Escribes en español claro, práctico y contextualizado, "
            "para docentes peruanos. NO inventes competencias, capacidades ni desempeños oficiales: usa solo los que "
            "se te entregan, con su redacción exacta.")
    if ctx:
        base += ("\n\nDisposiciones normativas verificadas por el administrador (úsalas como referencia sin contradecir el CNEB):\n"
                 + ctx)
    return base
