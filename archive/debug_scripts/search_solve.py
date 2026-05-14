import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('persona_v2_1_compliant.md', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('解决')
if idx >= 0:
    start = max(0, idx-60)
    end = min(len(text), idx+60)
    snippet = text[start:end]
    print(f"'解决' at {idx}: ...{snippet}...")
else:
    print("'解决' NOT FOUND")
