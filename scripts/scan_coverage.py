import os
from collections import defaultdict

core_dir = r'E:\AI_Workspace\MSS-AI\project\mssclaw\core'
tests_dir = r'E:\AI_Workspace\MSS-AI\project\tests'

# Scan core modules
core_mods = [f.replace('.py', '') for f in os.listdir(core_dir) if f.endswith('.py') and not f.startswith('__')]

# Scan test files
test_files = []
for root, dirs, files in os.walk(tests_dir):
    for f in files:
        if f.startswith('test_') and f.endswith('.py'):
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, tests_dir)
            test_files.append(rel)

# Count tests per file
test_counts = {}
for tf in test_files:
    fp = os.path.join(tests_dir, tf)
    content = open(fp, 'r', encoding='utf-8', errors='ignore').read()
    count = sum(1 for line in content.split('\n') if line.strip().startswith('def test_'))
    test_counts[tf] = count

# Map test files to core modules
module_tests = defaultdict(list)
for tf in test_files:
    name = tf.replace('test_', '').replace('.py', '').replace('\\', '_').replace('/', '_')
    for cm in core_mods:
        # Check if test name matches module name
        if cm in name or name in cm:
            module_tests[cm].append(tf)
            break
    else:
        # Check for multi-module tests (e.g., test_agents for agent*.py)
        for cm in core_mods:
            if cm.startswith(name[:8]) or name.startswith(cm[:8]):
                module_tests[cm].append(tf)
                break

print('=' * 70)
print(f'MSS Test Coverage Matrix')
print(f'Core modules: {len(core_mods)}  |  Test files: {len(test_files)}  |  Tests: {sum(test_counts.values())}')
print('=' * 70)
print()

# Coverage stats
covered = set()
for cm, tfs in module_tests.items():
    for tf in tfs:
        covered.add(cm)

coverage_pct = 100 * len(covered) // len(core_mods)
print(f'Module coverage: {len(covered)}/{len(core_mods)} ({coverage_pct}%)')
print()

# Top coverage modules
print('--- Most Tested Modules (by test files) ---')
sorted_mods = sorted(module_tests.items(), key=lambda x: -len(x[1]))
for cm, tfs in sorted_mods[:15]:
    bars = '\u2588' * len(tfs)
    print(f'  {cm:35s} [{len(tfs):2d} files] {bars}')

# Untested modules
print(f'\n--- Untested Modules ({len(core_mods) - len(covered)}) ---')
untested = [cm for cm in core_mods if cm not in covered]
for cm in sorted(untested)[:30]:
    print(f'  - {cm}')
if len(untested) > 30:
    print(f'  ... and {len(untested) - 30} more')

# Test file sizes
print(f'\n--- Test File Sizes ---')
sizes = [(tf, test_counts[tf]) for tf in test_files]
sizes.sort(key=lambda x: -x[1])
for tf, count in sizes[:10]:
    print(f'  {tf:45s} {count:3d} tests')
print(f'  ... ({len(test_files)} files total, {sum(test_counts.values())} tests)')

# Domain coverage
domains = {
    '核心引擎': ['l2op','mcdp','pipeline','phase','topo','scene','adaptive','type2','auto_layering','delta','conflict','nash','vcg'],
    '防御系统': ['defense','vaccine','virus','escalat','layering','goal','blackhole','logic_virus','hallucination'],
    'Agent框架': ['agent','session','channel','approval','group','sandbox','quorum','checkpoint','rollback','mss_'],
    '审计/SE': ['audit','se_','defer','heat_tax_self','lint','safe_run'],
    '实验/评测': ['experiment','bench','ollama_bench','perf'],
    '知识/记忆': ['kb_','conv_','vector_','memory','tombstone'],
    '工具桥接': ['tool_','mcp_','prompt','tactic','dialog'],
    '基础设施': ['vault','init_','dashboard','model_catalog','library','doctor','heat_tax_timer'],
    '理论基础': ['normative','evolutionary','observable'],
}

print('\n--- Domain Coverage ---')
for domain, keys in domains.items():
    domain_mods = [cm for cm in core_mods if any(k in cm for k in keys)]
    domain_covered = [cm for cm in domain_mods if cm in covered]
    pct = 100 * len(domain_covered) // len(domain_mods) if domain_mods else 0
    bar = '\u2588' * (pct // 10) + '\u2591' * (10 - pct // 10)
    print(f'  {domain:10s} {pct:3d}% [{bar}] ({len(domain_covered)}/{len(domain_mods)})')
