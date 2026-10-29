"""Convierte un documento guardado en bloques listos para vista previa y Word."""
from eduperu.services.curriculo import competencias_de, transversales
from eduperu.core.repo import contenido, get_asignacion, get_doc_by_id
from eduperu.services.render import (bloques_anual, bloques_desafio, bloques_examen, bloques_ficha, bloques_rubrica,
                    bloques_sesion, bloques_unidad)
from eduperu.core.util import norm, slug


def bloques_de(doc):
    """Devuelve (bloques, horizontal, nombre_de_archivo)."""
    asig = get_asignacion(doc["asignacion_id"]) or {}
    d = contenido(doc)
    tipo = doc["tipo"]
    trans = transversales()
    base = slug(f"{asig.get('area', '')} {asig.get('grado', '')}")
    if tipo == "anual":
        elegidas = {norm(n) for n in d.get("competencias_area", [])}
        comps = [c for c in competencias_de(asig.get("nivel"), asig.get("area")) if norm(c["nombre"]) in elegidas]
        return bloques_anual(asig, d, comps, trans), True, f"planificacion_anual_{base}.docx"
    if tipo == "unidad":
        return bloques_unidad(asig, d, trans), True, f"unidad_{doc.get('numero', 1)}_{base}.docx"
    padre = get_doc_by_id(doc.get("padre_id")) or {}
    pdata = contenido(padre) if padre else {}
    if tipo == "sesion":
        return bloques_sesion(asig, pdata, d, trans), False, f"sesion_{doc.get('numero', 1)}_{base}.docx"
    if tipo == "desafio":
        return bloques_desafio(asig, pdata, d), False, f"desafios_{base}.docx"
    if tipo == "examen_unidad":
        return bloques_examen(asig, pdata, d), False, f"examen_unidad_{doc.get('numero', 1)}_{base}.docx"
    if tipo == "rubrica":
        return bloques_rubrica(asig, pdata, d), True, f"rubrica_{base}.docx"
    if tipo == "ficha":
        return bloques_ficha(asig, pdata, d), False, f"ficha_{base}.docx"
    return bloques_examen(asig, pdata, d), False, f"examen_{base}.docx"
