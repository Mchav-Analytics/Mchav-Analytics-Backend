import codecs
import re

path = 'c:/Users/vhoyos/Desktop/Prueba2/Mchav-Analytics-Backend/app/services/gemini_service.py'
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

# Replace the Sprint old structure
old_sprint = r'''          "ESTRATEGIA NARRATIVA Y MARCO DE AN\xc1LISIS:",
          "Para CADA seccin, la redaccin de tu anǭlisis debe explicar obligatoriamente:",
          "1. QuǸ ocurri: identifica el comportamiento mǭs relevante observado en los datos.",
          "2. QuǸ significa: interpreta la relacin entre las mǸtricas y explica quǸ puede representar este comportamiento.",
          "3. Por quǸ es relevante: describe el posible impacto sobre la planificacin, el flujo de trabajo, la entrega o la calidad.",
          "4. QuǸ evidencia lo respalda: relaciona la explicacin con las mǸtricas y grǭficas proporcionadas.",
          "",
          "ESTRUCTURA ESTRICTA DE CADA SECCION \(REQUERIDO POR EL SISTEMA NATIVO\):",
          "El informe se divide en 8 secciones. Para asegurar la integracion con la UI nativa, TODA seccion debe contener exactamente esta estructura:",
          "1. TITULO EN FORMATO H1 \(# 0X — NOMBRE\). Ejemplo: # 01 — CONTEXTO DEL SPRINT",
          "2. DESCRIPCION \(Que estamos viendo, contexto breve en 1-2 lineas\)\.",
          "3. HIGHLIGHT: Genera exactamente esta etiqueta: %%HIGHLIGHT%% Tu frase de impacto aquí %%/HIGHLIGHT%%. Debe ser una frase corta \(max 10 palabras\), contundente y con el dato más importante de la sección \(ej. '80% DEL COMPROMISO COMPLETADO'\)\.",
          "4. ANALISIS \(Interpretacion profunda de los datos según el marco definido arriba\)\.",'''

# Let's just find and replace using simple string find, as python string literals in file have special characters.
def replace_sprint_prompt(c):
    start = c.find('ESTRATEGIA NARRATIVA Y MARCO DE')
    end = c.find('LAS 8 SECCIONES A DESARROLLAR')
    
    if start != -1 and end != -1:
        new_text = '''ESTRATEGIA NARRATIVA Y MARCO DE ANÁLISIS:",
          "Para lograr un reporte dinámico y exhaustivo, redacta cada sección como una historia continua y fluida que explique detalladamente la salud del sprint.",
          "IMPORTANTE: NO reduzcas la cantidad de análisis. Cada sección debe ser profunda, explicando orgánicamente: qué ocurrió, qué significa, por qué es relevante y qué evidencia lo respalda.",
          "",
          "ESTRUCTURA ESTRICTA DE CADA SECCION (REQUERIDO POR EL SISTEMA NATIVO):",
          "El informe se divide en 8 secciones. Para asegurar la integracion con la UI nativa, TODA seccion debe contener exactamente esta estructura:",
          "1. TITULO EN FORMATO H1 (# 0X — NOMBRE). Ejemplo: # 01 — CONTEXTO DEL SPRINT",
          "2. HIGHLIGHT: Genera exactamente esta etiqueta: %%HIGHLIGHT%% Tu frase de impacto aquí %%/HIGHLIGHT%%. Debe ser una frase corta (max 10 palabras), contundente y con el dato más importante de la sección.",
          "3. ANALISIS FLUIDO: Redacta múltiples párrafos de forma natural y profesional profundizando exhaustivamente en los datos, SIN usar subtítulos robóticos como DESCRIPCION o ANALISIS.",
          "",
          "'''
        
        # We need to make sure we only replace inside _build_sprint_prompt
        # _build_sprint_prompt is after _build_proyecto_prompt
        idx_sprint = c.find('def _build_sprint_prompt')
        if idx_sprint != -1:
            real_start = c.find('ESTRATEGIA NARRATIVA', idx_sprint)
            real_end = c.find('LAS 8 SECCIONES A DESARROLLAR', real_start)
            
            return c[:real_start] + new_text + c[real_end:]
    return c

new_content = replace_sprint_prompt(content)
if new_content != content:
    with codecs.open(path, 'w', 'utf-8') as f:
        f.write(new_content)
    print("Sprint prompt narrative updated!")
else:
    print("Could not find Sprint prompt.")

