import codecs

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
        "Genera múltiples párrafos largos y muy formales de análisis denso para cada sección sin viñetas innecesarias.",
        "",
        "ESTRUCTURA ESTRICTA DE CADA SECCION (OBLIGATORIO):",
        "El sistema UI separa el reporte usando etiquetas [PROYECTO_X].",
        "1. TITULO CON ETIQUETA: Empieza exactamente con [PROYECTO_X] TITULO EN MAYUSCULAS.",
        "2. ANALISIS FLUIDO: Párrafos largos de texto denso.",
        "",
        "LAS 6 SECCIONES A DESARROLLAR (Debes incluir EXACTAMENTE estas 6 en este orden):",
        "",
        "[PROYECTO_1] CONTEXTO GENERAL DEL PERIODO",
        "  - Evaluación del rendimiento global del proyecto, alineación operativa y desviaciones.",
        "",
        "[PROYECTO_2] ESTADO DEL FLUJO DE TRABAJO Y CUELLOS DE BOTELLA",
        "  - Análisis del flujo y atascos operativos. El sistema insertará aquí automáticamente el CFD.",
        "",
        "[PROYECTO_3] AVANCE Y ENTREGA DE VALOR",
        "  - Brecha entre valor planeado y entregado. El sistema insertará aquí automáticamente el Burnup Chart.",
        "",
        "[PROYECTO_4] VELOCIDAD DEL EQUIPO",
        "  - Constancia del equipo, inestabilidad de la capacidad productiva. El sistema insertará aquí automáticamente la gráfica de Velocidad.",
        "",
        "[PROYECTO_5] TIEMPOS Y PREDICTIBILIDAD",
        "  - Análisis del ciclo de vida y percentiles. El sistema insertará aquí automáticamente la gráfica de Predictibilidad.",
        "",
        "[PROYECTO_6] CONCLUSIONES ESTRATEGICAS Y PLAN DE ACCION",
        "  - Resumen y plan de acción con viñetas claras (solo en esta sección).",
        "",
        "REGLAS ESTRICTAS DE ESTILO Y FORMATO:",
        "- CERO USO DE LA PALABRA 'ACTO'.",
        "- CERO uso de etiquetas %%HIGHLIGHT%%. Este informe NO lleva highlights, solo prosa densa.",
        "- Formato: Solo texto en párrafos fluidos y densos corporativos. No uses código."
    ]
    return "\\n".join(lines)'''

start_idx = content.find('def _build_proyecto_prompt')
if start_idx != -1:
    end_idx = content.find('def _build_desarrollador_prompt', start_idx)
    
    if end_idx != -1:
        # Also include the decorative comments
        end_idx = content.rfind('# ════════════', start_idx, end_idx)
        if end_idx == -1: # fallback
            end_idx = content.rfind('# ', start_idx, end_idx)
            
        new_content = content[:start_idx] + new_prompt + '\n\n\n' + content[end_idx:]
        with codecs.open(path, 'w', 'utf-8') as f:
            f.write(new_content)
        print("Replaced project prompt by index splitting!")
    else:
        print("Could not find _build_desarrollador_prompt")
else:
    print("Could not find _build_proyecto_prompt")
