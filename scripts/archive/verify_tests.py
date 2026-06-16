"""Quick verification script - writes results to file"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

results = []
results.append("=" * 60)
results.append("MSS-AI Test Verification")
results.append("=" * 60)

# Test 1: Import check
try:
    from mssclaw.core.semantic.symbolic_engine import MSSKnowledgeGraph, ConceptNode, RelationEdge
    from mssclaw.core.semantic.symbolic_engine import NodeType, RelationType, InferenceResult, SymbolicReasoner
    from kb_loader import KBLoader, KBEntry
    results.append("[PASS] All imports successful")
except Exception as e:
    results.append(f"[FAIL] Import error: {e}")

# Test 2: KB integration
try:
    loader = KBLoader()
    count = loader.load_all()
    graph = loader.to_graph()
    stats = graph.stats()

    reasoner = SymbolicReasoner()
    reasoner.load_from_kb_loader(graph)

    results.append(f"[PASS] KB integration: {stats['total_nodes']} nodes, {stats['total_edges']} edges")
except Exception as e:
    results.append(f"[FAIL] KB integration: {e}")

# Test 3: New methods exist
try:
    reasoner = SymbolicReasoner()
    assert hasattr(reasoner, 'load_relations_from_kb')
    assert hasattr(reasoner, 'load_from_kb_loader')
    results.append("[PASS] New methods exist: load_relations_from_kb, load_from_kb_loader")
except Exception as e:
    results.append(f"[FAIL] Method check: {e}")

results.append("=" * 60)
results.append("Verification complete")
results.append("=" * 60)

output = "\n".join(results)
print(output)

# Write to file
with open("test_verification_result.txt", "w", encoding="utf-8") as f:
    f.write(output + "\n")
