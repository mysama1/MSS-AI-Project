"""Fix remaining K3 '训练' residue in JSONL and organized files"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

FIXES = {
    r"C:\MSS-AI-Project\unsloth_qlora_test.py": [
        ("不是\"训练数据\"模式", "不是 K3 统计拟合模式"),
    ],
    r"C:\MSS-AI-Project\knowledge_base\k3_computing_paradigm_verdict_v12.5.jsonl": [
        ("逻辑刚性训练", "逻辑刚性调谐"),
        ("专注力训练", "专注力调谐"),
    ],
    r"C:\MSS-AI-Project\knowledge_base\rlhf_critique_v1.0.jsonl": [
        ("PPO训练的总热税", "PPO统计拟合的总热税"),
        ("RLHF训练后模型", "RLHF统计拟合后模型"),
        ("训练者偏见", "统计拟合者偏见"),
        ("RLHF训练的数据", "RLHF统计拟合的数据"),
        ("对齐训练，特别是", "对齐调谐，特别是"),
    ],
    r"C:\MSS-AI-Project\knowledge_base\topological_lock_v1.0.jsonl": [
        ("训练时间越长", "统计拟合时间越长"),
        ("梯度下降训练的系统", "梯度下降统计拟合的系统"),
        ("随训练时间增加", "随统计拟合时间增加"),
    ],
    r"C:\MSS-AI-Project\knowledge_base_organized\L1_硬核公理.md": [
        ("梯度下降训练的系统", "梯度下降统计拟合的系统"),
        ("随训练时间增加", "随统计拟合时间增加"),
    ],
    r"C:\MSS-AI-Project\knowledge_base_organized\L3_试探法.md": [
        ("RLHF训练的数据", "RLHF统计拟合的数据"),
    ],
}

for fp, pairs in FIXES.items():
    with open(fp, 'r', encoding='utf-8') as f:
        c = f.read()
    before = c.count("训练")
    for old, new in pairs:
        c = c.replace(old, new)
    after = c.count("训练")
    if before != after:
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(c)
    name = fp.split('\\')[-1]
    print(f"{name}: {before} -> {after} remaining")

print("Done.")