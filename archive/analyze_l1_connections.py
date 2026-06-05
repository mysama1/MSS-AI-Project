"""
Analyze L1 node connections and identify missing IMPLIES edges
"""
from kb_v3_bridge import create_integrated_engine
from kb_loader import KBLoader

engine = create_integrated_engine()

# Check L1→L1 edges
implies_edges = [e for e in engine.graph.edges if e.relation.name == 'IMPLIES']
l1_to_l1 = []
for e in implies_edges:
    src = engine.graph.nodes.get(e.source)
    tgt = engine.graph.nodes.get(e.target)
    if src and tgt and src.layer == 'L1' and tgt.layer == 'L1':
        l1_to_l1.append((e.source, e.target))

print(f'L1→L1 IMPLIES edges: {len(l1_to_l1)}')
for src, tgt in l1_to_l1[:10]:
    print(f'  {src} → {tgt}')

# Check L1 nodes
l1_nodes = [n for n in engine.graph.nodes.values() if n.layer == 'L1']
print(f'\nL1 nodes: {len(l1_nodes)}')
for n in l1_nodes[:15]:
    print(f'  {n.id}: {n.name}')

# Check KB dependencies
loader = KBLoader()
loader.load_all()

with_deps = [(eid, e.dependencies) for eid, e in loader.entries.items() if e.dependencies]
print(f'\nEntries with dependencies: {len(with_deps)}')
for eid, deps in with_deps[:10]:
    print(f'  {eid} depends on: {deps}')
