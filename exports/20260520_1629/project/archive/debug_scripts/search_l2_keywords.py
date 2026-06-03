import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('entropy_radar_content.md', 'r', encoding='utf-8') as f:
    text = f.read()

L2_KEYWORDS = [
    "BCT", "Bekenstein", "Church-Turing", "holographic",
    "全息", "entropy", "熵", "coupling", "耦合",
    "phase transition", "相变", "fractal", "分形"
]

print("L2 keywords found:")
for kw in L2_KEYWORDS:
    count = text.count(kw)
    if count > 0:
        print(f"  {kw}: {count}")
        # Show context
        idx = 0
        while True:
            idx = text.find(kw, idx)
            if idx == -1:
                break
            start = max(0, idx-25)
            end = min(len(text), idx+len(kw)+25)
            print(f"    at {idx}: ...{text[start:end]}...")
            idx += 1
