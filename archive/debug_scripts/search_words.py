import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('persona_v2_1_compliant.md','r',encoding='utf-8') as f:
    content = f.read()

for word in ['绝对','零值承认','MAX']:
    matches = list(re.finditer(re.escape(word), content))
    for m in matches:
        start = max(0, m.start()-40)
        end = min(len(content), m.end()+40)
        snippet = content[start:end]
        print(f"{word} at {m.start()}: ...{snippet}...")
    print("---")
