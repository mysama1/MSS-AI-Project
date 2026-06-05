import json

with open('knowledge_base/k3_computing_paradigm_verdict_v12.5.jsonl', 'r', encoding='utf-8') as f:
    entries = [json.loads(line) for line in f if line.strip()]

print(f'K4计算范式知识库归档完成: {len(entries)}条')
print(f'  L1硬核: {sum(1 for e in entries if e["layer"]=="L1")}')
print(f'  L2保护带: {sum(1 for e in entries if e["layer"]=="L2")}')
print(f'  L3试探法: {sum(1 for e in entries if e["layer"]=="L3")}')
print()
for e in entries:
    print(f'  [{e["layer"]}] {e["id"]}: {e["title"]}')
