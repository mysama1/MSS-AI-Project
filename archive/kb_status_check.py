import json, os

kb_dir = 'knowledge_base'
files = [f for f in os.listdir(kb_dir) if f.endswith('.jsonl')]

total_entries = 0
layer_counts = {'L1': 0, 'L2': 0, 'L3': 0, 'L4': 0}

for fname in sorted(files):
    path = os.path.join(kb_dir, fname)
    with open(path, 'r', encoding='utf-8') as f:
        entries = [json.loads(line) for line in f if line.strip()]
    total_entries += len(entries)
    for e in entries:
        layer = e.get('layer', 'unknown')
        if layer in layer_counts:
            layer_counts[layer] += 1

print('=== 知识库状态 ===')
print('总条目:', total_entries)
print('层级分布: L1=', layer_counts['L1'], 'L2=', layer_counts['L2'], 'L3=', layer_counts['L3'], 'L4=', layer_counts['L4'])
print('进度:', f'{total_entries}/500 ({100*total_entries//500}%)')
print('文件数:', len(files))
