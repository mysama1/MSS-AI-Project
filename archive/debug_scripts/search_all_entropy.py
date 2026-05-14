import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('persona_v2_1_compliant.md', 'r', encoding='utf-8') as f:
    text = f.read()

idx = 0
while True:
    idx = text.find('熵', idx)
    if idx == -1:
        break
    start = max(0, idx-30)
    end = min(len(text), idx+30)
    print(f"'熵' at {idx}: ...{text[start:end]}...")
    idx += 1
