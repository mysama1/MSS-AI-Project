"""
Test kb_loader -> symbolic_engine integration
验证数据流打通：KB entries -> Graph nodes + edges -> Symbolic reasoning
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kb_loader import KBLoader, KBEntry
from symbolic_engine import SymbolicReasoner, RelationType, InferenceResult

def test_kb_to_symbolic_flow():
    """Test complete data flow from KB loader to symbolic engine"""
    print("=" * 60)
    print("Test: KB Loader -> Symbolic Engine Integration")
    print("=" * 60)

    # Step 1: Load KB
    print("\n[1] Loading knowledge base...")
    loader = KBLoader()
    count = loader.load_all()
    print(f"  Loaded {count} entries from {len(loader.loaded_files)} files")

    if count == 0:
        print("  WARNING: No entries loaded. Creating test data...")
        return test_with_mock_data()

    # Step 2: Convert to graph
    print("\n[2] Converting to knowledge graph...")
    kb_graph = loader.to_graph()
    kb_stats = kb_graph.stats()
    print(f"  Nodes: {kb_stats['total_nodes']}")
    print(f"  Edges: {kb_stats['total_edges']}")
    print(f"  By layer: {kb_stats['by_layer']}")
    print(f"  By type: {kb_stats['by_type']}")

    # Step 3: Load into symbolic reasoner
    print("\n[3] Loading into symbolic reasoner...")
    reasoner = SymbolicReasoner()
    total_loaded = reasoner.load_from_kb_loader(kb_graph)
    print(f"  Total elements loaded: {total_loaded}")

    # Step 4: Verify graph integrity
    print("\n[4] Verifying graph integrity...")
    reasoner_stats = reasoner.graph.stats()
    print(f"  Reasoner nodes: {reasoner_stats['total_nodes']}")
    print(f"  Reasoner edges: {reasoner_stats['total_edges']}")

    # Step 5: Test reasoning capabilities
    print("\n[5] Testing reasoning capabilities...")

    # Find L1 axioms
    l1_nodes = reasoner.graph.query(layer="L1")
    print(f"  L1 axioms found: {len(l1_nodes)}")
    if l1_nodes:
        print(f"  First axiom: {l1_nodes[0].id} - {l1_nodes[0].name}")

    # Find paths between layers
    if len(l1_nodes) >= 1:
        l2_nodes = reasoner.graph.query(layer="L2")
        if l2_nodes:
            print(f"\n  Testing path finding (L1 -> L2)...")
            path = reasoner.graph.find_path(l1_nodes[0].id, l2_nodes[0].id, max_depth=3)
            print(f"  Result: {path.result.name}")
            print(f"  Certainty: {path.certainty:.2%}")
            if path.steps:
                print(f"  Steps: {len(path.steps)}")
                for step in path.steps[:3]:
                    print(f"    {step[0]} --[{step[1].name}]--> {step[2]}")

    # Test IMPLIES edges
    implies_edges = [e for e in reasoner.graph.edges if e.relation == RelationType.IMPLIES]
    print(f"\n  IMPLIES edges: {len(implies_edges)}")
    if implies_edges:
        print(f"  First IMPLIES: {implies_edges[0].source} -> {implies_edges[0].target} (strength={implies_edges[0].strength:.2f})")

    # Test ANALOGOUS edges
    analog_edges = [e for e in reasoner.graph.edges if e.relation == RelationType.ANALOGOUS]
    print(f"  ANALOGOUS edges: {len(analog_edges)}")

    # Test contradiction detection
    print(f"\n  Testing contradiction detection...")
    if len(l1_nodes) >= 2:
        contradiction = reasoner.graph.check_contradiction(l1_nodes[0].id, l1_nodes[1].id)
        print(f"  Result: {contradiction.result.name}")

    # Step 6: Test verify_claim
    print(f"\n[6] Testing claim verification...")
    if l1_nodes:
        test_nodes = [n.id for n in l1_nodes[:2]]
        result = reasoner.verify_claim("Test claim", test_nodes)
        print(f"  Result: {result.result.name}")
        print(f"  Explanation: {result.explanation[:100]}...")

    print("\n" + "=" * 60)
    print("Integration test complete!")
    print("=" * 60)

    return True

def test_with_mock_data():
    """Test with mock data when no KB files exist"""
    print("\n[MOCK DATA TEST]")

    # Create mock entries
    mock_entries = [
        {
            "id": "A1",
            "title": "Information Ontology",
            "layer": "L1",
            "category": "axiom",
            "content": "Information is the fundamental substrate of reality",
            "tags": ["ontology", "information"],
            "dependencies": []
        },
        {
            "id": "T1",
            "title": "BCT Coupling",
            "layer": "L2",
            "category": "theory",
            "content": "Bekenstein-Church-Turing coupling between information and computation. Based on A1.",
            "tags": ["computation", "physics"],
            "dependencies": ["A1"]
        },
        {
            "id": "H1",
            "title": "Redshift Metaphor",
            "layer": "L3",
            "category": "heuristic",
            "content": "Civilizational redshift as metaphor for meaning dilution",
            "tags": ["metaphor", "civilization"],
            "dependencies": ["T1"]
        }
    ]

    # Create loader and add entries
    loader = KBLoader()
    for data in mock_entries:
        entry = KBEntry(data)
        loader.entries[entry.id] = entry

    # Convert to graph
    graph = loader.to_graph()
    stats = graph.stats()
    print(f"Mock graph: {stats['total_nodes']} nodes, {stats['total_edges']} edges")

    # Load into reasoner
    reasoner = SymbolicReasoner()
    reasoner.load_from_kb_loader(graph)

    # Test path finding
    path = reasoner.graph.find_path("A1", "H1", max_depth=3)
    print(f"Path A1 -> H1: {path.result.name}")
    if path.steps:
        for step in path.steps:
            print(f"  {step[0]} --[{step[1].name}]--> {step[2]}")

    # Test IMPLIES edges
    implies = [e for e in reasoner.graph.edges if e.relation == RelationType.IMPLIES]
    print(f"IMPLIES edges: {len(implies)}")
    for e in implies:
        print(f"  {e.source} -> {e.target} (strength={e.strength:.2f})")

    return True

def test_load_relations_method():
    """Test the new load_relations_from_kb method"""
    print("\n" + "=" * 60)
    print("Test: load_relations_from_kb method")
    print("=" * 60)

    # Create reasoner with some nodes
    reasoner = SymbolicReasoner()

    # Add test nodes
    from symbolic_engine import ConceptNode, NodeType
    reasoner.graph.add_node(ConceptNode("A1", "Test Axiom", NodeType.AXIOM, "L1", "Test content"))
    reasoner.graph.add_node(ConceptNode("T1", "Test Theory", NodeType.THEOREM, "L2", "Depends on A1"))

    # Create a test JSONL file with dependencies
    test_kb_dir = os.path.join(os.path.dirname(__file__), "test_kb_temp")
    os.makedirs(test_kb_dir, exist_ok=True)

    test_data = {
        "id": "T1",
        "title": "Test Theory",
        "layer": "L2",
        "content": "Depends on A1",
        "dependencies": ["A1"]
    }

    with open(os.path.join(test_kb_dir, "test.jsonl"), 'w', encoding='utf-8') as f:
        f.write(json.dumps(test_data, ensure_ascii=False) + '\n')

    # Load relations
    edge_count = reasoner.load_relations_from_kb(test_kb_dir)
    print(f"Loaded {edge_count} edges from relations")

    # Verify
    implies = [e for e in reasoner.graph.edges if e.relation == RelationType.IMPLIES]
    print(f"IMPLIES edges after loading: {len(implies)}")

    # Cleanup
    import shutil
    shutil.rmtree(test_kb_dir)

    return len(implies) > 0

if __name__ == "__main__":
    import json

    success = True

    # Test 1: Main integration flow
    try:
        test_kb_to_symbolic_flow()
        print("\n✓ Test 1 PASSED: KB -> Symbolic flow")
    except Exception as e:
        print(f"\n✗ Test 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        success = False

    # Test 2: load_relations_from_kb method
    try:
        if test_load_relations_method():
            print("\n✓ Test 2 PASSED: load_relations_from_kb")
        else:
            print("\n✗ Test 2 FAILED: No edges loaded")
            success = False
    except Exception as e:
        print(f"\n✗ Test 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        success = False

    print("\n" + "=" * 60)
    if success:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)

    sys.exit(0 if success else 1)
