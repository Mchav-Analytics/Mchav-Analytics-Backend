import codecs
import re

path = 'app/services/gemini_service.py'
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

new_prompt = '''def _build_proyecto_prompt(v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct):
    lines = [
        "Actúa como un Director de Portafolio y analista ejecutivo corporativo.",
        "Tu tarea es generar un INFORME EJECUTIVO DEL PROYECTO extremadamente profesional y denso.",
        "",
        "ESTRATEGIA NARRATIVA Y MARCO DE ANÁLISIS:",
        "No uses lenguaje genérico. Evalúa críticamente la desconexión operacional, la alineación con los objetivos de negocio y la viabilidad a largo plazo.",
        "Genera múltiples párrafos largos y muy formales de análisis denso para cada sección.",
        "",
        "ESTRUCTURA ESTRICTA DE CADA SECCION:",
        "1. TITULO EN FORMATO H1 (# 0X — NOMBRE).",
        "2. ANALISIS FLUIDO: Párrafos largos de texto denso. NO generes viñetas ni KPIs vacíos, escribe prosa narrativa corporativa.",
        "",
        "LAS 6 SECCIONES A DESARROLLAR (Debes incluir EXACTAMENTE estas 6 y en este orden):",
        "",
        "# 01 — CONTEXTO GENERAL DEL PERIODO",
        "  - Evaluación del rendimiento global del proyecto, alineación operativa y desviaciones.",
        "",
        "# 02 — ESTADO DEL FLUJO DE TRABAJO Y CUELLOS DE BOTELLA",
        "  - Análisis del flujo y atascos operativos. El sistema insertará aquí automáticamente el CFD.",
        "",
        "# 03 — AVANCE Y ENTREGA DE VALOR",
        "  - Brecha entre valor planeado y entregado. El sistema insertará aquí automáticamente el Burnup Chart.",
        "",
        "# 04 — VELOCIDAD DEL EQUIPO",
        "  - Constancia del equipo, inestabilidad de la capacidad productiva. El sistema insertará aquí automáticamente la gráfica de Velocidad.",
        "",
        "# 05 — TIEMPOS Y PREDICTIBILIDAD",
        "  - Análisis del ciclo de vida y percentiles. El sistema insertará aquí automáticamente la gráfica de Predictibilidad.",
        "",
        "# 06 — CONCLUSIONES ESTRATEGICAS Y PLAN DE ACCION",
        "  - Resumen y plan de acción con viñetas claras.",
        "",
        "REGLAS ESTRICTAS DE ESTILO Y FORMATO:",
        "- CERO USO DE LA PALABRA 'ACTO'.",
        "- CERO uso de etiquetas %%HIGHLIGHT%%. Este informe NO lleva highlights, solo prosa.",
        "- Redacta en párrafos densos, con lenguaje de nivel C-Level.",
        "- Formato: Solo texto en párrafos. No uses código ni etiquetas [GRAFICA]."
    ]
    return "\\n".join(lines)'''

pattern = r'def _build_proyecto_prompt.*?return "\\\\n"\.join\(lines\)'
new_content = re.sub(pattern, new_prompt, content, flags=re.DOTALL)

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(new_content)
    
print("Proyecto prompt restored!")
