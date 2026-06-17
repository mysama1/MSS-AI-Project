import os
from collections import defaultdict

core_dir = r'E:\AI_Workspace\MSS-AI\project\mssclaw\core'
modules = [f for f in os.listdir(core_dir) if f.endswith('.py') and not f.startswith('__')]

DOMAINS = {
    'l2op': '核心引擎', 'mcdp': '核心引擎', 'pipeline': '核心引擎',
    'phase': '核心引擎', 'topo': '核心引擎', 'scene_router': '核心引擎',
    'adaptive': '核心引擎', 'type2': '核心引擎', 'auto_layering': '核心引擎',
    'defense': '防御系统', 'vaccine': '防御系统', 'virus': '防御系统',
    'escalat': '防御系统', 'layering': '防御系统', 'goal': '防御系统',
    'agent': 'Agent框架', 'session': 'Agent框架', 'channel': 'Agent框架',
    'approval': 'Agent框架', 'group': 'Agent框架', 'sandbox': 'Agent框架',
    'quorum': 'Agent框架', 'audit': '审计/SE', 'se_': '审计/SE',
    'defer': '审计/SE', 'heat_tax_self': '审计/SE', 'lint': '审计/SE',
    'safe_run': '审计/SE', 'experiment': '实验/评测', 'bench': '实验/评测',
    'ollama_bench': '实验/评测', 'kb_': '知识/记忆', 'conv_': '知识/记忆',
    'vector_': '知识/记忆', 'memory': '知识/记忆', 'tool_': '工具桥接',
    'mcp_': '工具桥接', 'prompt': '工具桥接', 'tactic': '工具桥接',
    'dialog': '工具桥接', 'vault': '基础设施', 'init_': '基础设施',
    'dashboard': '基础设施', 'model_catalog': '基础设施', 'library': '基础设施',
    'doctor': '基础设施', 'normative': '理论基础', 'evolutionary': '理论基础',
    'observable': '理论基础', 'tombstone': '理论基础', 'heat_tax_timer': '基础设施',
    'vdp_': 'VDP扫描器', 'delta': '核心引擎', 'conflict': '核心引擎',
    'blackhole': '防御系统', 'mss_': 'Agent框架', 'checkpoint': 'Agent框架',
    'rollback': 'Agent框架', 'nash': '核心引擎', 'percolation': '理论基础',
    'vcg': '核心引擎', 'token_': '基础设施', 'credential': '基础设施',
}

domains = defaultdict(list)
unclassified = []

for m in modules:
    name = m.replace('.py', '')
    matched = False
    for key, domain in DOMAINS.items():
        if key in name:
            domains[domain].append(name)
            matched = True
            break
    if not matched:
        unclassified.append(name)

print('=== MSS 146 Module Architecture ===')
print()
total = sum(len(v) for v in domains.values()) + len(unclassified)
print(f'Total modules: {total}')
print()

for domain, mods in sorted(domains.items(), key=lambda x: -len(x[1])):
    bar = '\u2588' * min(len(mods), 20)
    print(f'{domain:10s} [{len(mods):3d}] {bar}')
    shown = sorted(mods)[:8]
    print(f'           {", ".join(shown)}{" ..." if len(mods)>8 else ""}')
    print()

if unclassified:
    print(f'{"Unclassified":10s} [{len(unclassified):3d}]')
    shown = sorted(unclassified)[:20]
    print(f'           {", ".join(shown)}{" ..." if len(unclassified)>20 else ""}')
    print()

# Quality metrics
print('--- Quality ---')
total_doc = 0
total_lines = 0
for m in modules:
    path = os.path.join(core_dir, m)
    content = open(path, 'r', encoding='utf-8', errors='ignore').read()
    total_lines += content.count('\n')
    if content.strip().startswith('"""') or content.strip().startswith("'''"):
        total_doc += 1
print(f'With docstring: {total_doc}/{len(modules)} ({100*total_doc//len(modules)}%)')
print(f'Total lines: {total_lines:,}')

# TOP 5 heaviest
sizes = [(m, os.path.getsize(os.path.join(core_dir, m))) for m in modules]
sizes.sort(key=lambda x: -x[1])
print(f'\nTOP 5 heaviest:')
for name, sz in sizes[:5]:
    print(f'  {name:45s} {sz:>10,} bytes')

# TOP 5 lightest
print(f'\nTOP 5 lightest:')
for name, sz in sizes[-5:]:
    print(f'  {name:45s} {sz:>10,} bytes')
