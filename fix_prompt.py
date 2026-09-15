import codecs

path = 'c:/Users/vhoyos/Desktop/Prueba2/Mchav-Analytics-Backend/app/services/gemini_service.py'
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

old_sprint_structure = '''        "ESTRATEGIA NARRATIVA Y MARCO DE ANÁLISIS:",
        "Para CADA sección, la redacción debe explicar:",
        "1. Qué ocurrió: identifica el comportamiento más relevante observado.",
        "2. Qué significa: interpreta qué representa para la salud del sprint.",
        "3. Por qué es relevante: describe el impacto en el objetivo del sprint.",
        "4. Qué evidencia lo respalda: relaciona con las métricas proporcionadas.",
        "",
        "ESTRUCTURA ESTRICTA DE CADA SECCION:",
        "El informe se divide en 6 secciones. TODA seccion debe contener:",
        "1. TITULO EN FORMATO H1 (# 0X — NOMBRE).",
        "2. DESCRIPCION (contexto breve en 1-2 lineas).",
        "3. HIGHLIGHT: %%HIGHLIGHT%% Frase de impacto (max 10 palabras) %%/HIGHLIGHT%%.",
        "4. ANALISIS (Interpretación profunda).",'''

new_sprint_structure = '''        "ESTRATEGIA NARRATIVA Y MARCO DE ANÁLISIS:",
        "Para lograr un reporte dinámico y exhaustivo, redacta cada sección como una historia continua y fluida que explique detalladamente la salud del sprint.",
        "IMPORTANTE: NO reduzcas la cantidad de análisis. Cada sección debe ser profunda, explicando exhaustivamente: qué ocurrió, qué significa, por qué es relevante y qué evidencia lo respalda.",
        "",
        "ESTRUCTURA ESTRICTA DE CADA SECCION:",
        "El informe se divide en 6 secciones. TODA seccion debe contener:",
        "1. TITULO EN FORMATO H1 (# 0X — NOMBRE).",
        "2. HIGHLIGHT: %%HIGHLIGHT%% Frase de impacto (max 10 palabras) %%/HIGHLIGHT%%.",
        "3. ANALISIS FLUIDO: Redacta múltiples párrafos de forma natural y profesional profundizando en los datos, SIN usar subtítulos robóticos como DESCRIPCION o ANALISIS.",'''

if old_sprint_structure in content:
    content = content.replace(old_sprint_structure, new_sprint_structure)
    with codecs.open(path, 'w', 'utf-8') as f:
        f.write(content)
    print("Updated sprint prompt.")
else:
    print("Old sprint structure not found.")
