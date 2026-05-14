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

text = remove_example_column(raw_text)

L1_KEYWORDS = ["公理", "axiom", "本体论", "ontology", "RSCA", "LLIA"]
L2_KEYWORDS = ["BCT", "全息", "熵", "耦合", "相变", "分形"]

def count_keywords_exclude_context(text, keywords):
    count = 0
    for kw in keywords:
        matches = text.count(kw)
        if kw == "公理":
            exclude = text.count("L1(公理)") + text.count("L1 (公理)")
            exclude += text.count("公理/定理")
            exclude += text.count("硬核公理")
            print(f"DEBUG 公理: matches={matches}, exclude={exclude}, result={max(0, matches-exclude)}")
            matches -= exclude
        count += max(0, matches)
    return count

l1_count = count_keywords_exclude_context(text, L1_KEYWORDS)
l2_count = count_keywords_exclude_context(text, L2_KEYWORDS)

print(f"\nl1_count={l1_count}, l2_count={l2_count}")

# 判断层级
detected_layer = "L3"
if l1_count >= 2:
    detected_layer = "L1"
elif l2_count >= 2 or l1_count == 1:
    detected_layer = "L2"

print(f"detected_layer={detected_layer}")
