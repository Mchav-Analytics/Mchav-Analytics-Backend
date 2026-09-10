import codecs
import re

path = 'app/services/gemini_service.py'
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

# Delete the duplicate block
pattern = r'    return {"markdown": "# Analisis no disponible\\nNo se pudo obtener el analisis del servidor de IA."}\n    """\n    Genera el reporte ejecutivo dinamico completo en Markdown usando Gemini.*?\n    return {"markdown": "# Analisis no disponible\\\\nNo se pudo obtener el analisis del servidor de IA."}'
new_content = re.sub(pattern, '    return {"markdown": "# Analisis no disponible\\nNo se pudo obtener el analisis del servidor de IA."}', content, flags=re.DOTALL)

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(new_content)
    
print("Duplicate removed!")
