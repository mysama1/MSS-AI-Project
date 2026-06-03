import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('persona_v2_1_compliant.md', 'r', encoding='utf-8') as f:
    raw_text = f.read()

# 复制两个过滤逻辑
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
            print(f"SKIP forbidden: {stripped[:80]}")
            continue
        filtered_lines.append(line)
    return '\n'.join(filtered_lines)

text = remove_example_column(raw_text)
print(f"After column filter, '熵' count: {text.count('熵')}")

text = remove_forbidden_examples(text)
print(f"After forbidden filter, '熵' count: {text.count('熵')}")
