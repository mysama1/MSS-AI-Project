import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('persona_v2_1_compliant.md', 'r', encoding='utf-8') as f:
    raw_text = f.read()

# 复制remove_example_column逻辑
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
                print(f"SKIP header: {stripped[:60]}")
                continue
            if in_example_table and ':---' in stripped:
                print(f"SKIP separator: {stripped[:60]}")
                continue
            if in_example_table and len(cells) > 2:
                print(f"SKIP data: {stripped[:60]}")
                continue
            if in_example_table and not stripped.startswith('|'):
                in_example_table = False
                print(f"Table END: {stripped[:60]}")
        else:
            in_example_table = False
        filtered_lines.append(line)
    return '\n'.join(filtered_lines)

text = remove_example_column(raw_text)
print(f"\nAfter filter, '熵' count: {text.count('熵')}")
print(f"'无熵增' count: {text.count('无熵增')}")
print(f"'逻辑熵爆' count: {text.count('逻辑熵爆')}")
