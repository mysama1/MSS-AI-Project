import sys, os, re
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

FILE_SUFFIXES = ('.py', '.md', '.jsonl', '.json', '.txt')
EXCLUDE = {"__pycache__", "dist", "node_modules", "resilience_reports", ".git", "tools"}

ALLOWED = {
    "大样本统计",
    "随机采样",
    "抽样",
    "认知训练者",
    "微调",
    "调整",
    "培训",
}

violations = []
for root, dirs, files in os.walk(r"C:\MSS-AI-Project"):
    dirs[:] = [d for d in dirs if d not in EXCLUDE]
    for fn in files:
        if not fn.endswith(FILE_SUFFIXES):
            continue
        fp = os.path.join(root, fn)
        rel = os.path.relpath(fp, r"C:\MSS-AI-Project")
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                c = f.read()
        except:
            continue
        for match in re.finditer(r'(.{0,10})训练(.{0,10})', c):
            ctx = (match.group(1) + "训练" + match.group(2)).strip()
            is_allowed = any(a in ctx for a in ALLOWED)
            if not is_allowed:
                line_num = c[:match.start()].count('\n') + 1
                violations.append((rel, line_num, ctx))

print("=" * 60)
if violations:
    print(f"K3 '训练' 残留污染: {len(violations)} 处")
    for v in violations[:20]:
        print(f"  {v[0]}:{v[1]}: ...{v[2]}...")
else:
    print("K3 '训练' 清零")

# Check "样本" in K3 context
sample_issues = []
for root, dirs, files in os.walk(r"C:\MSS-AI-Project"):
    dirs[:] = [d for d in dirs if d not in EXCLUDE]
    for fn in files:
        if not fn.endswith(FILE_SUFFIXES):
            continue
        fp = os.path.join(root, fn)
        rel = os.path.relpath(fp, r"C:\MSS-AI-Project")
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                c = f.read()
        except:
            continue
        for match in re.finditer(r'样本', c):
            start = max(0, match.start() - 8)
            end = min(len(c), match.end() + 8)
            ctx = c[start:end]
            if "大样本" in ctx or "抽样" in ctx:
                continue
            line_num = c[:match.start()].count('\n') + 1
            sample_issues.append((rel, line_num, ctx.strip()))

print()
if sample_issues:
    print(f"K3 '样本' 残留: {len(sample_issues)} 处 (多为合法ML术语)")
    for s in sample_issues[:10]:
        print(f"  {s[0]}:{s[1]}: ...{s[2]}...")
else:
    print("'样本' 使用均在合法语境")

print()
print("=" * 60)
print("范式纯净度审计完成")
print("=" * 60)