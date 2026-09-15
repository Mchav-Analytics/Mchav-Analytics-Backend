import codecs

path = 'app/services/gemini_service.py'
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

functions = '''
# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT: REPORTE POR SPRINT
# ═══════════════════════════════════════════════════════════════════════════════
def _build_sprint_prompt(v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct):
    lines = [
        "Actúa como un analista senior de proyectos ágiles y especialista en reportes ejecutivos de Sprint.",
        "",
        "Tu tarea es generar un REPORTE EJECUTIVO PROFESIONAL DEL SPRINT con los datos reales.",
        "El reporte NO debe ser solo texto plano: debes intercalar gráficas visuales en los momentos exactos",
        "donde la narrativa necesita respaldo visual. El lector verá una gráfica interactiva real en ese punto.",
        "",
        "ESTRATEGIA NARRATIVA Y MARCO DE ANÁLISIS:",
        "Para lograr un reporte dinámico y exhaustivo, redacta cada sección como una historia continua y fluida que explique detalladamente la salud del sprint.",
        "IMPORTANTE: NO reduzcas la cantidad de análisis. Cada sección debe ser profunda, explicando orgánicamente: qué ocurrió, qué significa, por qué es relevante y qué evidencia lo respalda.",
        "",
        "ESTRUCTURA ESTRICTA DE CADA SECCION (REQUERIDO POR EL SISTEMA NATIVO):",
        "El informe se divide en 6 secciones. Para asegurar la integracion con la UI nativa, TODA seccion debe contener exactamente esta estructura:",
        "1. TITULO EN FORMATO H1 (# 0X — NOMBRE). Ejemplo: # 01 — RESUMEN EJECUTIVO",
        "2. HIGHLIGHT: Genera exactamente esta etiqueta: %%HIGHLIGHT%% Tu frase de impacto aquí %%/HIGHLIGHT%%. Debe ser una frase corta (max 10 palabras), contundente y con el dato más importante de la sección.",
        "3. ANALISIS FLUIDO: Redacta múltiples párrafos de forma natural y profesional profundizando exhaustivamente en los datos, SIN usar subtítulos robóticos como DESCRIPCION o ANALISIS.",
        "",
        "LAS 6 SECCIONES A DESARROLLAR (Debes incluir EXACTAMENTE estas 6 y en este orden):",
        "",
        "# 01 — RESUMEN EJECUTIVO",
        "  - Síntesis de alto nivel del sprint: ¿Fue un éxito o un fracaso?",
        "  - Menciona el nivel de salud del sprint y las métricas más críticas a simple vista.",
        "",
        "# 02 — KPIs DEL SPRINT",
        "  - (Deja esta sección vacía de texto. Solo pon el título y el HIGHLIGHT. El frontend inyectará los KPIs automáticamente aquí).",
        "",
        "# 03 — PLANIFICADO VS ENTREGADO",
        "  - Análisis detallado del alcance. ¿Qué tanto se cumplió el compromiso inicial?",
        "  - Habla del Scope Creep (trabajo añadido a mitad del sprint) si hubo.",
        "  - Compara la velocidad actual con la tendencia histórica si es relevante.",
        "  - Aquí el sistema inyectará automáticamente la gráfica Burnup y de Velocidad. Haz referencia a la 'curva de avance' o 'tendencia de velocidad' en tu narrativa.",
        "",
        "# 04 — FLUJO DE TRABAJO Y CUELLOS DE BOTELLA",
        "  - Diagnóstico de cómo se movieron las tareas por el tablero (ej: mucho tiempo en revisión o pruebas).",
        "  - Analiza si hubo bloqueos prolongados y su impacto.",
        "  - Aquí el sistema inyectará automáticamente el Diagrama de Flujo Acumulado (CFD). Habla de los 'cuellos de botella' o 'estancamientos' visibles.",
        "",
        "# 05 — PATRONES DE PREDICTIBILIDAD",
        "  - Analiza el Cycle Time (tiempo de ciclo) promedio.",
        "  - Interpreta los percentiles de predictibilidad (P50, P85, P95) y qué dicen sobre la estabilidad del equipo.",
        "  - Aquí el sistema inyectará automáticamente la gráfica de distribución de Cycle Time. Tu análisis debe hacer referencia a ella.",
        "",
        "# 06 — CONCLUSIÓN Y RECOMENDACIONES",
        "  - Síntesis ejecutiva de los hallazgos.",
        "  - Incluye una lista de acciones concretas con viñetas para el próximo sprint.",
        "",
        "IMPORTANTE SOBRE VISUALIZACIONES:",
        "NO incluyas etiquetas de gráficas ni marcadores visuales en el texto. El sistema las inyecta automáticamente basándose en el número de sección.",
        "Tu trabajo es SOLO escribir el análisis narrativo.",
        "",
        "REGLAS ESTRICTAS DE ESTILO Y FORMATO:",
        "- CERO USO DE LA PALABRA 'ACTO'. Está totalmente prohibido usar esa palabra en el reporte.",
        "- Enfoque estratégico: Habla desde la perspectiva de la dirección del proyecto.",
        "- Párrafos espaciados: Párrafos cortos (3-4 líneas máximo) y viñetas donde sea necesario.",
        "- Formato: Solo párrafos, negritas y listas con viñetas (•). No uses código, JSON, XML ni tablas markdown."
    ]
    return "\\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT: REPORTE EJECUTIVO POR PROYECTO
# ═══════════════════════════════════════════════════════════════════════════════
def _build_proyecto_prompt(v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct):
    lines = [
        "Actúa como un Director de Portafolio y especialista en agilidad.",
        "Tu tarea es generar un REPORTE EJECUTIVO DEL PROYECTO COMPLETO.",
        "",
        "ESTRATEGIA NARRATIVA Y MARCO DE ANÁLISIS:",
        "Analiza el proyecto a nivel macro. No te enfoques en el día a día de un sprint corto, sino en la viabilidad a largo plazo, la estabilidad del pipeline de entrega y los riesgos estructurales.",
        "",
        "ESTRUCTURA ESTRICTA DE CADA SECCION:",
        "1. TITULO EN FORMATO H1 (# 0X — NOMBRE).",
        "2. HIGHLIGHT: Genera exactamente esta etiqueta: %%HIGHLIGHT%% Tu frase de impacto aquí %%/HIGHLIGHT%%.",
        "3. ANALISIS FLUIDO.",
        "",
        "LAS 6 SECCIONES A DESARROLLAR:",
        "",
        "# 01 — RESUMEN EJECUTIVO",
        "  - Síntesis de alto nivel del proyecto.",
        "",
        "# 02 — KPIs DEL PROYECTO",
        "  - (Solo título y HIGHLIGHT).",
        "",
        "# 03 — FLUJO DE TRABAJO ACUMULADO",
        "  - Analiza la eficiencia del pipeline completo.",
        "",
        "# 04 — AVANCE HISTÓRICO Y VELOCIDAD",
        "  - Tendencia de entrega a lo largo del tiempo.",
        "",
        "# 05 — PREDICTIBILIDAD Y RIESGO",
        "  - Análisis estadístico del Cycle Time y riesgo de atrasos.",
        "",
        "# 06 — CONCLUSIONES ESTRATEGICAS",
        "  - Plan de acción corporativo.",
        "",
        "REGLAS ESTRICTAS DE ESTILO Y FORMATO:",
        "- CERO USO DE LA PALABRA 'ACTO'. Está totalmente prohibido usar esa palabra en el reporte.",
        "- Párrafos espaciados: Párrafos cortos (3-4 líneas máximo) y viñetas donde sea necesario.",
        "- Formato: Solo párrafos, negritas y listas con viñetas (•). No uses código, JSON, XML ni tablas markdown."
    ]
    return "\\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT: REPORTE POR DESARROLLADOR
# ═══════════════════════════════════════════════════════════════════════════════
def _build_desarrollador_prompt(v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct):
    lines = [
        "Actúa como un analista especializado en productividad individual y métricas de rendimiento de desarrolladores.",
        "Tu objetivo es evaluar el desempeño de un desarrollador específico basándote en sus métricas personales.",
        "No juzgues al desarrollador. Analiza su ritmo de trabajo, eficiencia y posibles oportunidades de mejora.",
        "",
        "ESTRUCTURA ESTRICTA DE CADA SECCION:",
        "1. TITULO EN FORMATO H1 (# 0X — NOMBRE).",
        "2. HIGHLIGHT: Genera exactamente esta etiqueta: %%HIGHLIGHT%% Tu frase de impacto aquí %%/HIGHLIGHT%%.",
        "3. ANALISIS FLUIDO.",
        "",
        "LAS 4 SECCIONES A DESARROLLAR:",
        "",
        "# 01 — RESUMEN DE RENDIMIENTO",
        "  - Síntesis de alto nivel.",
        "",
        "# 02 — EFICIENCIA Y CICLO DE VIDA",
        "  - Análisis del tiempo de ciclo.",
        "",
        "# 03 — CALIDAD DEL CODIGO",
        "  - Análisis de bugs y retrabajo.",
        "",
        "# 04 — OPORTUNIDADES DE MEJORA",
        "  - Recomendaciones constructivas.",
        "",
        "REGLAS ESTRICTAS DE ESTILO Y FORMATO:",
        "- CERO USO DE LA PALABRA 'ACTO'. Está totalmente prohibido usar esa palabra en el reporte.",
        "- Párrafos espaciados: Párrafos cortos (3-4 líneas máximo) y viñetas donde sea necesario.",
        "- Formato: Solo párrafos, negritas y listas con viñetas (•). No uses código, JSON, XML ni tablas markdown."
    ]
    return "\\n".join(lines)
'''

idx = content.find('def chat_with_gemini')
if idx != -1:
    content = content[:idx] + functions + '\n\n' + content[idx:]
    with codecs.open(path, 'w', 'utf-8') as f:
        f.write(content)
    print("Successfully injected all build prompts!")
else:
    print("chat_with_gemini not found!")
