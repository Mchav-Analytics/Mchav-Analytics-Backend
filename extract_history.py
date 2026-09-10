import json
import os

transcript_path = r"C:\Users\vhoyos\.gemini\antigravity-ide\brain\4cdb3d15-64b9-4074-b88a-ef56aa73a983\.system_generated\logs\transcript.jsonl"
out_path = r"scratch\restored_sprint_prompt.txt"

output = []
try:
    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                if data.get('type') == 'PLANNER_RESPONSE':
                    tool_calls = data.get('tool_calls', [])
                    for call in tool_calls:
                        if call.get('name') in ['replace_file_content', 'write_to_file', 'multi_replace_file_content']:
                            args = call.get('args', {})
                            content = args.get('ReplacementContent', '') or args.get('CodeContent', '')
                            if '_build_sprint_prompt' in content:
                                output.append(content)
                        elif call.get('name') == 'run_command':
                            cmd = call.get('args', {}).get('CommandLine', '')
                            if '_build_sprint_prompt' in cmd:
                                output.append(cmd)
            except:
                pass
except Exception as e:
    output.append(str(e))

if not os.path.exists("scratch"):
    os.makedirs("scratch")

with open(out_path, 'w', encoding='utf-8') as out:
    for item in output:
        out.write(item + "\n\n-----------------\n\n")
