with open('mss_agent/core/normative_field.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, l in enumerate(lines):
    if 'load_defaults' in l:
        print(f'L{i+1}: {l.rstrip()}')
    elif i >= 280 and i <= 340:
        print(f'  L{i+1}: {l.rstrip()[:100]}')
