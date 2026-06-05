import re, sys
sys.stdout.reconfigure(encoding='utf-8')

fixes = [
    (r"C:\MSS-AI-Project\knowledge_base\iq_ruler_trap_v1.0.jsonl",
     [("训练首要目标", "调谐首要目标")]),
    (r"C:\MSS-AI-Project\knowledge_base\multimodal_critique_v1.0.jsonl",
     [("相似度训练", "相似度调谐")]),
    (r"C:\MSS-AI-Project\sfm_architecture.md",
     [("训练逻辑", "统计拟合逻辑")]),
]

for fp, pairs in fixes:
    with open(fp, 'r', encoding='utf-8') as f:
        c = f.read()
    before = c.count("训练")
    for old, new in pairs:
        c = c.replace(old, new)
    after = c.count("训练")
    if before != after:
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(c)
        print(f"OK {fp.split(chr(92))[-1]}: {before}->{after}")
    else:
        print(f"SKIP {fp.split(chr(92))[-1]}: no change")

print("\nDone.")