import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('persona_v2_1_compliant.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_32 = False
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith('### 3.2'):
        in_32 = True
        print(f"=== START 3.2 at line {i} ===")
    if stripped.startswith('### 3.3'):
        in_32 = False
        print(f"=== END 3.2 at line {i} ===")
    if in_32:
        print(f"{i}: {stripped}")
