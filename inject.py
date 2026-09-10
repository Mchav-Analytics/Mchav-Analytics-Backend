import json
import codecs

path = 'app/services/gemini_service.py'
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

# I will append generate_report_insights and its helpers directly to the file!
# Let me extract the function from fix_gemini_prompt.py first.
import re
with codecs.open(r'C:\Users\vhoyos\.gemini\antigravity-ide\brain\4cdb3d15-64b9-4074-b88a-ef56aa73a983\scratch\fix_gemini_prompt.py', 'r', 'utf-8') as f:
    fix_content = f.read()

# The function is in new_function string
pattern = r"new_function = '''(.*?)'''\n\npattern"
match = re.search(pattern, fix_content, re.DOTALL)
if match:
    new_func = match.group(1)
    
    # Check if generate_report_insights already exists
    if 'def generate_report_insights' not in content:
        # Append before chat_with_gemini
        idx = content.find('def chat_with_gemini')
        if idx != -1:
            content = content[:idx] + new_func + '\n\n' + content[idx:]
            with codecs.open(path, 'w', 'utf-8') as f:
                f.write(content)
            print("Successfully injected generate_report_insights!")
        else:
            print("chat_with_gemini not found!")
    else:
        print("generate_report_insights already exists!")
else:
    print("Could not extract new_function from fix_gemini_prompt.py")
