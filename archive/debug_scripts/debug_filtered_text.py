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

# 查找所有"熵"的位置
idx = 0
while True:
    idx = text.find('熵', idx)
    if idx == -1:
        break
    start = max(0, idx-50)
    end = min(len(text), idx+50)
    print(f"'熵' at {idx}: ...{text[start:end]}...")
    idx += 1

print(f"\nTotal '熵' count: {text.count('熵')}")
