import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('persona_v2_1_compliant.md', 'r', encoding='utf-8') as f:
    raw_text = f.read()

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

def remove_forbidden_examples(text):
    lines = text.split('\n')
    filtered_lines = []
    in_forbidden_section = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('### 3.2') or '禁止行为' in stripped:
            in_forbidden_section = True
            filtered_lines.append(line)
            continue
        if stripped.startswith('### 3.3') or stripped.startswith('## 4.'):
            in_forbidden_section = False
        if in_forbidden_section and stripped.startswith('- ❌'):
            continue
        filtered_lines.append(line)
    return '\n'.join(filtered_lines)

text = remove_example_column(raw_text)
text = remove_forbidden_examples(text)

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

# 模拟count_keywords_exclude_context
def count_keywords_exclude_context(text, keywords):
    count = 0
    for kw in keywords:
        matches = text.count(kw)
        if kw == "公理":
            exclude = text.count("L1(公理)") + text.count("L1 (公理)")
            exclude += text.count("公理/定理")
            exclude += text.count("硬核公理")
            matches -= exclude
        elif kw == "本体论":
            exclude = text.count("意义本体论")
            matches -= exclude
        elif kw == "RSCA":
            exclude = text.count("RSCA 合规") + text.count("RSCA合规")
            matches -= exclude
        count += max(0, matches)
    return count

l1_count = count_keywords_exclude_context(text, L1_KEYWORDS)
l2_count = count_keywords_exclude_context(text, L2_KEYWORDS)

print(f"\nl1_count: {l1_count}")
print(f"l2_count: {l2_count}")

if l1_count >= 2:
    detected = "L1"
elif l2_count >= 2 or l1_count == 1:
    detected = "L2"
else:
    detected = "L3"

print(f"detected_layer: {detected}")
