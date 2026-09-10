import codecs

path = 'app/services/gemini_service.py'
with codecs.open(path, 'r', 'utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'return {"markdown": "# Analisis no disponible' in line:
        lines[i] = '    return {"markdown": "# Analisis no disponible\\nNo se pudo obtener el analisis del servidor de IA."}\n'
        
with codecs.open(path, 'w', 'utf-8') as f:
    f.writelines(lines)
    
print("Fixed backslash issue!")
