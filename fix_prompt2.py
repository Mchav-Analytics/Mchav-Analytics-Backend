import codecs
import re

path = 'c:/Users/vhoyos/Desktop/Prueba2/Mchav-Analytics-Backend/app/services/gemini_service.py'
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

# Replace Sprint structure
content = re.sub(
    r'"2\. DESCRIPCION \(contexto breve en 1-2 lineas\)\.",\s*"3\. HIGHLIGHT: %%HIGHLIGHT%% Frase de impacto \(max 10 palabras\) %%/HIGHLIGHT%%\.",\s*"4\. ANALISIS \(Interpretación profunda\)\.",',
    '"2. HIGHLIGHT: %%HIGHLIGHT%% Frase de impacto (max 10 palabras) %%/HIGHLIGHT%%.",\n        "3. ANALISIS FLUIDO: Redacta múltiples párrafos de forma natural y profesional profundizando exhaustivamente en los datos, SIN usar subtítulos robóticos como DESCRIPCION o ANALISIS.",',
    content
)
content = re.sub(
    r'"Para CADA sección, la redacción debe explicar:"',
    '"Para lograr un reporte dinámico y exhaustivo, redacta cada sección como una historia continua y fluida que explique detalladamente la salud del sprint.",\n        "IMPORTANTE: NO reduzcas la cantidad de análisis. Cada sección debe ser profunda, explicando orgánicamente: qué ocurrió, qué significa, por qué es relevante y qué evidencia lo respalda."',
    content
)

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(content)
print("Updated sprint prompt via regex.")
