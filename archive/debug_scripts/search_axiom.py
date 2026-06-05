import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('persona_v2_1_compliant.md', 'r', encoding='utf-8') as f:
    text = f.read()

idx = 0
while True:
    idx = text.find('公理', idx)
    if idx == -1:
        break
    start = max(0, idx-40)
    end = min(len(text), idx+40)
    print(f"'公理' at {idx}: ...{text[start:end]}...")
    idx += 1
