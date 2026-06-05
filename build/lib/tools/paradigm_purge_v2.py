#!/usr/bin/env python3
"""MSS-AI 范式纯净度清洗 v2 - 第二轮精确清洗"""

import os, re, sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = r"C:\MSS-AI-Project"
EXCLUDE_DIRS = {"__pycache__", "dist", "node_modules", "resilience_reports", ".git", "tools", ".pytest_cache", "build", "mss_agent_sdk.egg-info"}

# 第二轮替换规则（处理第一轮遗漏的复合词+边缘情况）
REPLACEMENTS = [
    # 数据集 → 锚定案例库（边缘情况）
    # 纯词干"训练"（K3范式语境）
    (r"通过预测下一个词训练", "通过预测下一个词统计拟合"),
    (r"词训练智能", "词统计拟合智能"),
    (r"训练AI", "调谐AI"),
    (r"训练时不只看即时", "调谐时不只看即时"),
    (r"训练首要目标", "调谐首要目标"),
    (r"训练偏好", "统计拟合偏好"),
    (r"训练时学习了", "统计拟合时学习了"),
    (r"先训练能说会道", "先统计拟合能说会道"),
    (r"训练时未遇到", "统计拟合时未遇到"),
    (r"数据训练→逻辑", "数据调谐→逻辑"),
    (r"情绪极化训练", "情绪极化驯化"),
    (r"训练逻辑", "统计拟合逻辑"),
    (r"训练计算量", "统计拟合计算量"),
    # 认知训练者 - 保留（合法，MSS框架下的主动调谐）
    # 微调 - 保留（技术术语，非K3训练）
]

SKIP_CONTAINING = ["大样本统计", "random_sample", "抽样", "认知训练者", "微调"]

def process_file(filepath):
    rel = os.path.relpath(filepath, PROJECT_ROOT)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        return 0, str(e)
    
    modified = []
    changes = 0
    for line in lines:
        if any(s in line for s in SKIP_CONTAINING):
            modified.append(line)
            continue
        new_line = line
        for pat, rep in REPLACEMENTS:
            nl = re.sub(pat, rep, new_line)
            if nl != new_line:
                new_line = nl
        if new_line != line:
            changes += 1
        modified.append(new_line)
    
    if changes > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(modified)
    
    return changes, None

print("=" * 60)
print("MSS-AI 范式纯净度清洗 v2")
print("=" * 60)

results = []
for root, dirs, files in os.walk(PROJECT_ROOT):
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    for fn in files:
        ext = os.path.splitext(fn)[1].lower()
        if ext not in ('.py', '.md', '.jsonl', '.json', '.txt'):
            continue
        fp = os.path.join(root, fn)
        n, err = process_file(fp)
        if n > 0:
            rel = os.path.relpath(fp, PROJECT_ROOT)
            results.append((rel, n))
            print(f"  ✅ {rel} ({n}处)")

print()
if results:
    print(f"修改: {len(results)} 文件, {sum(x[1] for x in results)} 处")
else:
    print("无新增修改")
