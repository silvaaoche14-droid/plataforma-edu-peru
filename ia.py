"""Proveedores de IA (OpenRouter primero, Gemini de respaldo) y utilidades para pedir JSON."""
import json
import re
import requests
import streamlit as st


def llamar_openrouter(prompt: str) -> str:
    cfg = st.secrets["openrouter"]
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"},
        json={"model": cfg.get("model", "openai/gpt-4o-mini"),
              "messages": [{"role": "user", "content": prompt}],
              "max_tokens": 6000},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def llamar_gemini(prompt: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    return genai.GenerativeModel("gemini-2.5-flash").generate_content(prompt).text


def generar_texto(prompt: str):
    """Devuelve (texto, proveedor). Lanza RuntimeError si fallan todos los proveedores."""
    errores = []
    if "openrouter" in st.secrets:
        try:
            return llamar_openrouter(prompt), "OpenRouter"
        except Exception as e:
            errores.append(f"OpenRouter: {e}")
    if "gemini" in st.secrets:
        try:
            return llamar_gemini(prompt), "Gemini"
        except Exception as e:
            errores.append(f"Gemini: {e}")
    raise RuntimeError(" | ".join(errores) or "No hay proveedores de IA configurados en Secrets.")


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
    """Devuelve (datos, proveedor). Reintenta una vez si la IA no devuelve JSON válido."""
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
    from normativa import normativa_vigente
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
