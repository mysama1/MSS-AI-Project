import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('persona_v2_1_compliant.md', 'r', encoding='utf-8') as f:
    raw_text = f.read()

# 复制过滤逻辑
def remove_example_column(text):
    lines = text.split('\n')
    filtered_lines = []
    in_example_table = False
    for line in lines:
        stripped = line.strip()
        if '|' in stripped and not stripped.startswith('#'):
            cells = [c.strip() for c in stripped.split('|')]
            if len(cells) > 2 and ('原表述' in cells[1] or '违规' in cells[1]):
                in_example_table = True
                continue
            if in_example_table and ':---' in stripped:
                continue
            if in_example_table and len(cells) > 2:
                continue
            if in_example_table and not stripped.startswith('|'):
                in_example_table = False
        else:
            in_example_table = False
        filtered_lines.append(line)
    return '\n'.join(filtered_lines)

text = remove_example_column(raw_text)

L1_KEYWORDS = ["公理", "axiom", "本体论", "ontology", "RSCA", "LLIA"]
L2_KEYWORDS = ["BCT", "全息", "熵", "耦合", "相变", "分形"]

print("L1 keywords:")
for kw in L1_KEYWORDS:
    count = text.count(kw)
    print(f"  {kw}: {count}")

print("\nL2 keywords:")
for kw in L2_KEYWORDS:
    count = text.count(kw)
    print(f"  {kw}: {count}")

# 检查"公理"的具体位置
idx = 0
while True:
    idx = text.find('公理', idx)
    if idx == -1:
        break
    start = max(0, idx-30)
    end = min(len(text), idx+30)
    print(f"\n'公理' at {idx}: ...{text[start:end]}...")
    idx += 1
