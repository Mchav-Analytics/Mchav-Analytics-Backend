import codecs

path = 'c:/Users/vhoyos/Desktop/Prueba2/Mchav-Analytics-Backend/app/services/gemini_service.py'
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

# Fix Sprint Prompt
def fix_sprint(c):
    idx = c.find('def _build_sprint_prompt')
    if idx == -1: return c
    start_str = '"ESTRATEGIA NARRATIVA Y MARCO DE AN'
    start = c.find(start_str, idx)
    end = c.find('"LAS 8 SECCIONES A DESARROLLAR', start)
    
    if start != -1 and end != -1:
        new_text = '''"ESTRATEGIA NARRATIVA Y MARCO DE ANÁLISIS:",
          "Para lograr un reporte dinámico y exhaustivo, redacta cada sección como una historia continua y fluida que explique detalladamente la salud del sprint.",
          "IMPORTANTE: NO reduzcas la cantidad de análisis. Cada sección debe ser profunda, explicando orgánicamente: qué ocurrió, qué significa, por qué es relevante y qué evidencia lo respalda.",
          "",
          "ESTRUCTURA ESTRICTA DE CADA SECCION (REQUERIDO POR EL SISTEMA NATIVO):",
          "El informe se divide en 8 secciones. Para asegurar la integracion con la UI nativa, TODA seccion debe contener exactamente esta estructura:",
          "1. TITULO EN FORMATO H1 (# 0X — NOMBRE). Ejemplo: # 01 — CONTEXTO DEL SPRINT",
          "2. HIGHLIGHT: Genera exactamente esta etiqueta: %%HIGHLIGHT%% Tu frase de impacto aquí %%/HIGHLIGHT%%. Debe ser una frase corta (max 10 palabras), contundente y con el dato más importante de la sección.",
          "3. ANALISIS FLUIDO: Redacta múltiples párrafos de forma natural y profesional profundizando exhaustivamente en los datos, SIN usar subtítulos robóticos como DESCRIPCION o ANALISIS.",
          "",
          '''
        return c[:start] + new_text + c[end:]
    return c

content = fix_sprint(content)

# Fix Developer Prompt
def fix_dev(c):
    idx = c.find('def _build_developer_prompt')
    if idx == -1: return c
    start_str = '"ESTRATEGIA NARRATIVA Y MARCO DE AN'
    start = c.find(start_str, idx)
    end = c.find('"LAS 8 SECCIONES A DESARROLLAR', start)
    
    if start != -1 and end != -1:
        new_text = '''"ESTRATEGIA NARRATIVA Y MARCO DE ANÁLISIS:",
          "Para lograr un reporte dinámico y exhaustivo, redacta cada sección como una historia continua y fluida que explique el rendimiento del desarrollador.",
          "IMPORTANTE: NO reduzcas la cantidad de análisis. Cada sección debe ser profunda, explicando orgánicamente: qué ocurrió, qué significa, por qué es relevante y qué evidencia lo respalda.",
          "",
          "ESTRUCTURA ESTRICTA DE CADA SECCION (REQUERIDO POR EL SISTEMA NATIVO):",
          "El informe se divide en 8 secciones. Para asegurar la integracion con la UI nativa, TODA seccion debe contener exactamente esta estructura:",
          "1. TITULO EN FORMATO H1 (# 0X — NOMBRE).",
          "2. HIGHLIGHT: Genera exactamente esta etiqueta: %%HIGHLIGHT%% Tu frase de impacto aquí %%/HIGHLIGHT%%. Debe ser una frase corta (max 10 palabras), contundente y con el dato más importante de la sección.",
          "3. ANALISIS FLUIDO: Redacta múltiples párrafos de forma natural y profesional profundizando exhaustivamente en los datos, SIN usar subtítulos robóticos como DESCRIPCION o ANALISIS.",
          "",
          '''
        return c[:start] + new_text + c[end:]
    return c

content = fix_dev(content)

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(content)
print("Updated Sprint and Dev Prompts!")
