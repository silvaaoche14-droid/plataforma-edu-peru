"""Funciones pequeñas de ayuda (sin dependencias de Streamlit)."""
import re
import unicodedata


def norm(texto) -> str:
    """Normaliza un texto para comparar nombres (sin tildes, minúsculas, sin signos)."""
    t = unicodedata.normalize("NFD", str(texto or ""))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9 ]+", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def s(valor) -> str:
    """Convierte cualquier valor a texto limpio (las listas se unen por saltos de línea)."""
    if valor is None:
        return ""
    if isinstance(valor, (list, tuple)):
        return "\n".join(s(v) for v in valor if s(v))
    return str(valor).replace("**", "").strip()


def a_lista(valor) -> list:
    """Convierte texto con saltos de línea (o lista) en lista de textos no vacíos."""
    if valor is None:
        return []
    if isinstance(valor, (list, tuple)):
        items = [s(v) for v in valor]
    else:
        items = [x.strip() for x in str(valor).replace("**", "").split("\n")]
    limpios = []
    for x in items:
        x = re.sub(r"^[\-\*•·]\s*", "", x).strip()
        if x:
            limpios.append(x)
    return limpios


def a_texto(lista) -> str:
    return "\n".join(a_lista(lista))


def entero(valor, defecto=0, minimo=None, maximo=None) -> int:
    try:
        n = int(float(valor))
    except (TypeError, ValueError):
        n = defecto
    if minimo is not None:
        n = max(minimo, n)
    if maximo is not None:
        n = min(maximo, n)
    return n


def slug(texto) -> str:
    t = norm(texto).replace(" ", "_")
    return t[:60] or "documento"
