import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('persona_v2_1_compliant.md', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('熵')
if idx >= 0:
    start = max(0, idx-50)
    end = min(len(text), idx+50)
    print(f"'熵' at {idx}: ...{text[start:end]}...")
