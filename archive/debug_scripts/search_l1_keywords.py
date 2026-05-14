import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('entropy_radar_content.md', 'r', encoding='utf-8') as f:
    text = f.read()

L1_KEYWORDS = [
    "axiom", "公理", "information ontology", "信息本体论",
    "0/1", "critical", "临界", "RSCA", "LLIA",
    "meaning space", "意义空间", "tuning degree", "调谐度"
]

print("L1 keywords found:")
for kw in L1_KEYWORDS:
    count = text.count(kw)
    if count > 0:
        print(f"  {kw}: {count}")
        idx = 0
        while True:
            idx = text.find(kw, idx)
            if idx == -1:
                break
            start = max(0, idx-25)
            end = min(len(text), idx+len(kw)+25)
            print(f"    at {idx}: ...{text[start:end]}...")
            idx += 1
