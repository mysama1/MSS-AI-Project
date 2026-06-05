fp = r"C:\MSS-AI-Project\knowledge_base\multimodal_critique_v1.0.jsonl"
with open(fp, 'r', encoding='utf-8') as f:
    c = f.read()
before = c.count("训练")
c2 = c.replace("超出训练分布", "超出统计拟合分布")
after = c2.count("训练")
print(f"multimodal: {before} -> {after}")
if before != after:
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(c2)