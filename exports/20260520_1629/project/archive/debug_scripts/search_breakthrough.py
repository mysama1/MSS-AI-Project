import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('entropy_radar_content.md', 'r', encoding='utf-8') as f:
    text = f.read()

idx = 0
while True:
    idx = text.find('突破', idx)
    if idx == -1:
        break
    start = max(0, idx-30)
    end = min(len(text), idx+30)
    print(f"'突破' at {idx}: ...{text[start:end]}...")
    idx += 1
