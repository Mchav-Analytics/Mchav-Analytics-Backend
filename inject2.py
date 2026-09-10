import codecs
import re

path = 'app/services/gemini_service.py'
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

# Load restored prompts
with codecs.open(r'scratch\restored_sprint_prompt.txt', 'r', 'utf-8') as f:
    restored = f.read()

match = re.search(r'(# ═══════════════════════════════════════════════════════════════════════════════\n# PROMPT: REPORTE POR SPRINT.*)', restored, re.DOTALL)

if match:
    prompts_text = match.group(1)
    # the rest contains some garbage from transcript parsing like -----
    prompts_text = prompts_text.split("-----------------")[0]
    
    # We need to insert this right after generate_report_insights
    idx = content.find('def chat_with_gemini')
    if idx != -1:
        content = content[:idx] + prompts_text + '\n\n' + content[idx:]
        with codecs.open(path, 'w', 'utf-8') as f:
            f.write(content)
        print("Successfully injected all build prompts!")
    else:
        print("chat_with_gemini not found!")
else:
    print("Could not find prompts in restored file")
