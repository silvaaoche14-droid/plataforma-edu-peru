"""Base curricular verificada: competencias, capacidades, desempeños y transversales.

Las competencias y capacidades base se cargan una sola vez (marcadas como "por verificar").
Los desempeños los carga el administrador (Excel/CSV) desde los Programas Curriculares oficiales.
La IA NUNCA inventa estos textos: solo elige entre los que están en esta base.
"""
import streamlit as st
from db import fetch, execute
from util import norm

NIVELES = ["Inicial", "Primaria", "Secundaria"]
GRADOS = {
    "Inicial": ["3 años", "4 años", "5 años"],
    "Primaria": ["1.° grado", "2.° grado", "3.° grado", "4.° grado", "5.° grado", "6.° grado"],
    "Secundaria": ["1.° grado", "2.° grado", "3.° grado", "4.° grado", "5.° grado"],
}
CICLOS = {
    "Inicial": {"3 años": "II", "4 años": "II", "5 años": "II"},
    "Primaria": {"1.° grado": "III", "2.° grado": "III", "3.° grado": "IV", "4.° grado": "IV",
                 "5.° grado": "V", "6.° grado": "V"},
    "Secundaria": {"1.° grado": "VI", "2.° grado": "VI", "3.° grado": "VII", "4.° grado": "VII", "5.° grado": "VII"},
}
REGIONES = ["Amazonas", "Áncash", "Apurímac", "Arequipa", "Ayacucho", "Cajamarca", "Callao", "Cusco",
            "Huancavelica", "Huánuco", "Ica", "Junín", "La Libertad", "Lambayeque", "Lima", "Loreto",
            "Madre de Dios", "Moquegua", "Pasco", "Piura", "Puno", "San Martín", "Tacna", "Tumbes", "Ucayali"]


def ciclo_de(nivel, grado):
    return CICLOS.get(nivel, {}).get(grado, "")


# ------------------------------------------------------------------
# DATOS BASE (CNEB)
# ------------------------------------------------------------------
_ORAL = ["Obtiene información del texto oral", "Infiere e interpreta información del texto oral",
         "Adecúa, organiza y desarrolla las ideas de forma coherente y cohesionada",
         "Utiliza recursos no verbales y paraverbales de forma estratégica",
         "Interactúa estratégicamente con distintos interlocutores",
         "Reflexiona y evalúa la forma, el contenido y contexto del texto oral"]
_LEE = ["Obtiene información del texto escrito", "Infiere e interpreta información del texto",
        "Reflexiona y evalúa la forma, el contenido y contexto del texto"]
_ESCRIBE = ["Adecúa el texto a la situación comunicativa",
            "Organiza y desarrolla las ideas de forma coherente y cohesionada",
            "Utiliza convenciones del lenguaje escrito de forma pertinente",
            "Reflexiona y evalúa la forma, el contenido y contexto del texto escrito"]
_CREA = ["Explora y experimenta los lenguajes del arte", "Aplica procesos creativos",
         "Evalúa y comunica sus procesos y proyectos"]

COMPETENCIAS = {
    "cantidad": ("Resuelve problemas de cantidad",
                 ["Traduce cantidades a expresiones numéricas", "Comunica su comprensión sobre los números y las operaciones",
                  "Usa estrategias y procedimientos de estimación y cálculo",
                  "Argumenta afirmaciones sobre las relaciones numéricas y las operaciones"]),
    "regularidad": ("Resuelve problemas de regularidad, equivalencia y cambio",
                    ["Traduce datos y condiciones a expresiones algebraicas y gráficas",
                     "Comunica su comprensión sobre las relaciones algebraicas",
                     "Usa estrategias y procedimientos para encontrar equivalencias y reglas generales",
                     "Argumenta afirmaciones sobre relaciones de cambio y equivalencia"]),
    "forma": ("Resuelve problemas de forma, movimiento y localización",
              ["Modela objetos con formas geométricas y sus transformaciones",
               "Comunica su comprensión sobre las formas y relaciones geométricas",
               "Usa estrategias y procedimientos para orientarse en el espacio",
               "Argumenta afirmaciones sobre relaciones geométricas"]),
    "datos": ("Resuelve problemas de gestión de datos e incertidumbre",
              ["Representa datos con gráficos y medidas estadísticas o probabilísticas",
               "Comunica la comprensión de los conceptos estadísticos y probabilísticos",
               "Usa estrategias y procedimientos para recopilar y procesar datos",
               "Sustenta conclusiones o decisiones con base en la información obtenida"]),
    "oral": ("Se comunica oralmente en su lengua materna", _ORAL),
    "lee": ("Lee diversos tipos de textos escritos en su lengua materna", _LEE),
    "escribe": ("Escribe diversos tipos de textos en su lengua materna", _ESCRIBE),
    "crea": ("Crea proyectos desde los lenguajes artísticos", _CREA),
    "aprecia": ("Aprecia de manera crítica manifestaciones artístico-culturales",
                ["Percibe manifestaciones artístico-culturales", "Contextualiza manifestaciones culturales",
                 "Reflexiona creativa y críticamente"]),
    "oral_en": ("Se comunica oralmente en inglés como lengua extranjera", _ORAL),
    "lee_en": ("Lee diversos tipos de textos escritos en inglés como lengua extranjera", _LEE),
    "escribe_en": ("Escribe diversos tipos de textos en inglés como lengua extranjera", _ESCRIBE),
    "indaga": ("Indaga mediante métodos científicos para construir sus conocimientos",
               ["Problematiza situaciones", "Diseña estrategias para hacer indagación",
                "Genera y registra datos o información", "Analiza datos e información",
                "Evalúa y comunica el proceso y resultados de su indagación"]),
    "explica": ("Explica el mundo físico basándose en conocimientos sobre los seres vivos, materia y energía, "
                "biodiversidad, Tierra y universo",
                ["Comprende y usa conocimientos sobre los seres vivos, materia y energía, biodiversidad, Tierra y universo",
                 "Evalúa las implicancias del saber y del quehacer científico y tecnológico"]),
    "disena": ("Diseña y construye soluciones tecnológicas para resolver problemas de su entorno",
               ["Determina una alternativa de solución tecnológica", "Diseña la alternativa de solución tecnológica",
                "Implementa y valida la alternativa de solución tecnológica",
                "Evalúa y comunica el funcionamiento y los impactos de su alternativa de solución tecnológica"]),
    "identidad": ("Construye su identidad",
                  ["Se valora a sí mismo", "Autorregula sus emociones", "Reflexiona y argumenta éticamente",
                   "Vive su sexualidad de manera integral y responsable de acuerdo a su etapa de desarrollo y madurez"]),
    "identidad_ini": ("Construye su identidad", ["Se valora a sí mismo", "Autorregula sus emociones"]),
    "convive": ("Convive y participa democráticamente en la búsqueda del bien común",
                ["Interactúa con todas las personas", "Construye normas y asume acuerdos y leyes",
                 "Maneja conflictos de manera constructiva", "Delibera sobre asuntos públicos",
                 "Participa en acciones que promueven el bienestar común"]),
    "historia": ("Construye interpretaciones históricas",
                 ["Interpreta críticamente fuentes diversas", "Comprende el tiempo histórico",
                  "Elabora explicaciones sobre procesos históricos"]),
    "espacio": ("Gestiona responsablemente el espacio y el ambiente",
                ["Comprende las relaciones entre los elementos naturales y sociales",
                 "Maneja fuentes de información para comprender el espacio geográfico y el ambiente",
                 "Genera acciones para conservar el ambiente local y global"]),
    "economia": ("Gestiona responsablemente los recursos económicos",
                 ["Comprende las relaciones entre los elementos del sistema económico y financiero",
                  "Toma decisiones económicas y financieras"]),
    "motricidad": ("Se desenvuelve de manera autónoma a través de su motricidad",
                   ["Comprende su cuerpo", "Se expresa corporalmente"]),
    "vida_saludable": ("Asume una vida saludable",
                       ["Comprende las relaciones entre la actividad física, alimentación, postura e higiene corporal y la salud",
                        "Incorpora prácticas que mejoran su calidad de vida"]),
    "sociomotrices": ("Interactúa a través de sus habilidades sociomotrices",
                      ["Se relaciona utilizando sus habilidades sociomotrices", "Crea y aplica estrategias y tácticas de juego"]),
    "rel_identidad": ("Construye su identidad como persona humana, amada por Dios, digna, libre y trascendente, "
                      "comprendiendo la doctrina de su propia religión, abierto al diálogo con las que le son cercanas",
                      ["Conoce a Dios y asume su identidad religiosa y espiritual como persona digna, libre y trascendente",
                       "Cultiva y valora las manifestaciones religiosas de su entorno argumentando su fe de manera comprensible y respetuosa"]),
    "rel_encuentro": ("Asume la experiencia del encuentro personal y comunitario con Dios en su proyecto de vida "
                      "en coherencia con su creencia religiosa",
                      ["Transforma su entorno desde el encuentro personal y comunitario con Dios y desde la fe que profesa",
                       "Actúa coherentemente en razón de su fe según los principios de su conciencia moral en situaciones concretas de la vida"]),
    "emprende": ("Gestiona proyectos de emprendimiento económico o social",
                 ["Crea propuestas de valor", "Aplica habilidades técnicas",
                  "Trabaja cooperativamente para lograr objetivos y metas",
                  "Evalúa los resultados del proyecto de emprendimiento"]),
}

_REL = ["rel_identidad", "rel_encuentro"]
_MAT4 = ["cantidad", "regularidad", "forma", "datos"]
CATALOGO = {
    ("Inicial", "Personal Social"): ["identidad_ini", "convive"],
    ("Inicial", "Psicomotricidad"): ["motricidad"],
    ("Inicial", "Comunicación"): ["oral", "lee", "escribe", "crea"],
    ("Inicial", "Matemática"): ["cantidad", "forma"],
    ("Inicial", "Ciencia y Tecnología"): ["indaga"],
    ("Inicial", "Educación Religiosa"): _REL,
    ("Primaria", "Matemática"): _MAT4,
    ("Primaria", "Comunicación"): ["oral", "lee", "escribe"],
    ("Primaria", "Ciencia y Tecnología"): ["indaga", "explica", "disena"],
    ("Primaria", "Personal Social"): ["identidad", "convive", "historia", "espacio", "economia"],
    ("Primaria", "Arte y Cultura"): ["aprecia", "crea"],
    ("Primaria", "Educación Física"): ["motricidad", "vida_saludable", "sociomotrices"],
    ("Primaria", "Inglés"): ["oral_en", "lee_en", "escribe_en"],
    ("Primaria", "Educación Religiosa"): _REL,
    ("Secundaria", "Matemática"): _MAT4,
    ("Secundaria", "Comunicación"): ["oral", "lee", "escribe"],
    ("Secundaria", "Ciencia y Tecnología"): ["indaga", "explica", "disena"],
    ("Secundaria", "Ciencias Sociales"): ["historia", "espacio", "economia"],
    ("Secundaria", "Desarrollo Personal, Ciudadanía y Cívica"): ["identidad", "convive"],
    ("Secundaria", "Arte y Cultura"): ["aprecia", "crea"],
    ("Secundaria", "Educación Física"): ["motricidad", "vida_saludable", "sociomotrices"],
    ("Secundaria", "Inglés"): ["oral_en", "lee_en", "escribe_en"],
    ("Secundaria", "Educación para el Trabajo"): ["emprende"],
    ("Secundaria", "Educación Religiosa"): _REL,
}

TRANSVERSALES = [
    ("competencia", "Se desenvuelve en entornos virtuales generados por las TIC",
     "Personaliza entornos virtuales\nGestiona información del entorno virtual\n"
     "Interactúa en entornos virtuales\nCrea objetos virtuales en diversos formatos"),
    ("competencia", "Gestiona su aprendizaje de manera autónoma",
     "Define metas de aprendizaje\nOrganiza acciones estratégicas para alcanzar sus metas de aprendizaje\n"
     "Monitorea y ajusta su desempeño durante el proceso de aprendizaje"),
    ("enfoque", "Enfoque de Derechos",
     "Conciencia de derechos\nLibertad y responsabilidad\nDiálogo y concertación"),
    ("enfoque", "Enfoque Inclusivo o de Atención a la diversidad",
     "Respeto por las diferencias\nEquidad en la enseñanza\nConfianza en la persona"),
    ("enfoque", "Enfoque Intercultural",
     "Respeto a la identidad cultural\nJusticia\nDiálogo intercultural"),
    ("enfoque", "Enfoque Igualdad de género", "Igualdad y Dignidad\nJusticia\nEmpatía"),
    ("enfoque", "Enfoque Ambiental",
     "Solidaridad planetaria y equidad intergeneracional\nJusticia y solidaridad\nRespeto a toda forma de vida"),
    ("enfoque", "Enfoque Orientación al bien común",
     "Equidad y justicia\nSolidaridad\nEmpatía\nResponsabilidad"),
    ("enfoque", "Enfoque Búsqueda de la Excelencia", "Flexibilidad y apertura\nSuperación personal"),
]


def sembrar_curriculo(conn) -> int:
    """Agrega las competencias/capacidades base que falten. Devuelve cuántas competencias nuevas insertó."""
    cur = conn.cursor(buffered=True)
    nuevas = 0
    for (nivel, area), claves in CATALOGO.items():
        for orden, clave in enumerate(claves, 1):
            nombre, caps = COMPETENCIAS[clave]
            cur.execute("SELECT id FROM curriculo_competencias WHERE nivel=%s AND area=%s AND nombre=%s",
                        (nivel, area, nombre))
            if cur.fetchone():
                continue
            cur.execute("INSERT INTO curriculo_competencias (nivel, area, nombre, orden, verificado) "
                        "VALUES (%s, %s, %s, %s, 0)", (nivel, area, nombre, orden))
            cid = cur.lastrowid
            for j, cap in enumerate(caps, 1):
                cur.execute("INSERT INTO curriculo_capacidades (competencia_id, nombre, orden) VALUES (%s, %s, %s)",
                            (cid, cap, j))
            nuevas += 1
    for tipo, nombre, detalle in TRANSVERSALES:
        cur.execute("SELECT id FROM curriculo_transversal WHERE tipo=%s AND nombre=%s", (tipo, nombre))
        if not cur.fetchone():
            cur.execute("INSERT INTO curriculo_transversal (tipo, nombre, detalle) VALUES (%s, %s, %s)",
                        (tipo, nombre, detalle))
    conn.commit()
    cur.close()
    return nuevas


# ------------------------------------------------------------------
# CONSULTAS
# ------------------------------------------------------------------
def areas_de(nivel):
    filas = fetch("SELECT area, MIN(id) AS m FROM curriculo_competencias WHERE nivel=%s GROUP BY area ORDER BY m",
                  (nivel,))
    return [f["area"] for f in filas]


def competencias_de(nivel, area):
    filas = fetch("SELECT id, nombre, verificado FROM curriculo_competencias "
                  "WHERE nivel=%s AND area=%s ORDER BY orden, id", (nivel, area))
    if not filas:
        return []
    ids = [f["id"] for f in filas]
    marcas = ",".join(["%s"] * len(ids))
    caps = fetch(f"SELECT competencia_id, nombre FROM curriculo_capacidades "
                 f"WHERE competencia_id IN ({marcas}) ORDER BY orden, id", tuple(ids))
    por = {}
    for c in caps:
        por.setdefault(c["competencia_id"], []).append(c["nombre"])
    return [{"id": f["id"], "nombre": f["nombre"], "verificado": bool(f["verificado"]),
             "capacidades": por.get(f["id"], [])} for f in filas]


def desempenos_de(competencia_id, grado):
    return fetch("SELECT id, texto FROM curriculo_desempenos WHERE competencia_id=%s AND grado=%s ORDER BY orden, id",
                 (competencia_id, grado))


def estado_area(nivel, area, grado):
    """(n competencias, n verificadas, n con desempeños para el grado)."""
    comps = competencias_de(nivel, area)
    con_des = sum(1 for c in comps if desempenos_de(c["id"], grado))
    return len(comps), sum(1 for c in comps if c["verificado"]), con_des


@st.cache_data(ttl=120, show_spinner=False)
def transversales():
    """(competencias transversales, enfoques) → listas de dicts con 'nombre' y 'items'."""
    filas = fetch("SELECT tipo, nombre, detalle FROM curriculo_transversal ORDER BY id")
    comps, enf = [], []
    for f in filas:
        item = {"nombre": f["nombre"], "items": [x.strip() for x in (f["detalle"] or "").split("\n") if x.strip()]}
        (comps if f["tipo"] == "competencia" else enf).append(item)
    return comps, enf


def limpiar_cache():
    try:
        transversales.clear()
    except Exception:
        pass


def contexto_curricular(nivel, area, grado, nombres):
    """Texto para el prompt + mapa {nombre competencia: {'comp':..., 'des': [...]}} (desempeños numerados D1..Dn)."""
    objetivo = {norm(n) for n in nombres}
    lineas, mapa = [], {}
    for c in competencias_de(nivel, area):
        if norm(c["nombre"]) not in objetivo:
            continue
        ds = desempenos_de(c["id"], grado)
        mapa[c["nombre"]] = {"comp": c, "des": ds}
        lineas.append(f"COMPETENCIA: {c['nombre']}")
        lineas.append("  Capacidades: " + "; ".join(c["capacidades"]))
        if ds:
            for k, d in enumerate(ds, 1):
                lineas.append(f"  D{k}: {d['texto']}")
        else:
            lineas.append("  (No hay desempeños cargados: propón 2 desempeños en 'desempenos_texto'.)")
    return "\n".join(lineas), mapa


def buscar_competencia(nombre, mapa):
    """Devuelve el nombre exacto de la competencia (de 'mapa') que coincide con 'nombre', o None."""
    n = norm(nombre)
    for real in mapa:
        if norm(real) == n:
            return real
    for real in mapa:  # coincidencia parcial
        if n and (n in norm(real) or norm(real) in n):
            return real
    return None
