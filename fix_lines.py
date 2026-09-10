import codecs

path = 'app/services/gemini_service.py'
with codecs.open(path, 'r', 'utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'No se pudo obtener el analisis del servidor de IA."' in line and 'return' not in line:
        continue # skip the broken next line
    new_lines.append(line)

with codecs.open(path, 'w', 'utf-8') as f:
    f.writelines(new_lines)
    
print("Fixed lines!")
