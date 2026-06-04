"""Test suite for Symbolic Engine v2.0"""
import sys
from symbolic_engine import MSSKnowledgeGraph, ConceptNode, RelationEdge, NodeType, RelationType
from symbolic_engine_v2 import GraphAlgorithms, LayerAwareReasoner

def create_test_graph():
    """Create a test graph with L1/L2/L3 structure"""
    graph = MSSKnowledgeGraph()
    
    nodes = [
        ConceptNode("A1", "Info Ontology", NodeType.AXIOM, "L1", "Info is fundamental", confidence=1.0),
        ConceptNode("A2", "0/1 Critical", NodeType.AXIOM, "L1", "Phase transition", confidence=1.0),
        ConceptNode("T1", "BCT Coupling", NodeType.THEOREM, "L2", "BCT theorem", confidence=0.9),
        ConceptNode("T2", "Resilience", NodeType.THEOREM, "L2", "R=T/phi", confidence=0.85),
        ConceptNode("H1", "Redshift", NodeType.CONCEPT, "L3", "Metaphor", confidence=0.7),
        ConceptNode("H2", "Time Crystal", NodeType.CONCEPT, "L3", "Time structure", confidence=0.6),
    ]
    
    for n in nodes:
        graph.add_node(n)
    
    edges = [
        RelationEdge("A1", "T1", RelationType.IMPLIES, 1.0),
        RelationEdge("A2", "T1", RelationType.IMPLIES, 0.9),
        RelationEdge("T1", "T2", RelationType.DERIVES_FROM, 0.8),
        RelationEdge("T2", "H1", RelationType.ANALOGOUS, 0.6),
        RelationEdge("T2", "H2", RelationType.ANALOGOUS, 0.5),
    ]
    
    for e in edges:
        graph.add_edge(e)
    
    return graph

def test_shortest_path():
    print("Test 1: Shortest Path")
    graph = create_test_graph()
    algo = GraphAlgorithms(graph)
    
    path = algo.shortest_path("A1", "H1")
    assert path.result.name == "PROVEN"
    assert len(path.steps) == 3
    assert path.certainty > 0
    print(f"  [OK] Path: {len(path.steps)} steps, certainty={path.certainty:.2f}")
    print("  PASSED\n")
    return True

def test_shortest_path_avoid_layer():
    print("Test 2: Shortest Path Avoid Layer")
    graph = create_test_graph()
    algo = GraphAlgorithms(graph)
    
    # Avoid L3 - should still find path but different
    path = algo.shortest_path("A1", "T2", avoid_layers={"L3"})
    assert path.result.name == "PROVEN"
    print(f"  [OK] Path avoiding L3: {len(path.steps)} steps")
    print("  PASSED\n")
    return True

def test_centrality():
    print("Test 3: Centrality Analysis")
    graph = create_test_graph()
    algo = GraphAlgorithms(graph)
    
    c = algo.centrality("T1")
    assert c["degree"] > 0
    assert c["layer_authority"] == 0.7  # L2
    print(f"  [OK] T1: degree={c['degree']}, authority={c['layer_authority']}")
    
    c_a1 = algo.centrality("A1")
    assert c_a1["layer_authority"] == 1.0  # L1
    print(f"  [OK] A1: authority={c_a1['layer_authority']}")
    print("  PASSED\n")
    return True

def test_layer_analysis():
    print("Test 4: Layer Analysis")
    graph = create_test_graph()
    algo = GraphAlgorithms(graph)
    
    analysis = algo.layer_analysis()
    assert analysis["layer_counts"]["L1"] == 2
    assert analysis["layer_counts"]["L2"] == 2
    assert analysis["upward_flow"] > 0
    assert analysis["downward_flow"] == 0
    print(f"  [OK] L1={analysis['layer_counts']['L1']}, upward={analysis['upward_flow']}")
    print("  PASSED\n")
    return True

def test_connected_components():
    print("Test 5: Connected Components")
    graph = create_test_graph()
    algo = GraphAlgorithms(graph)
    
    components = algo.connected_components()
    assert len(components) == 1  # All connected
    assert len(components[0]) == 6
    print(f"  [OK] {len(components)} component(s), {len(components[0])} nodes")
    print("  PASSED\n")
    return True

def test_layer_aware_verify():
    print("Test 6: Layer-Aware Verification")
    graph = create_test_graph()
    reasoner = LayerAwareReasoner(graph)
    
    # L2 claim should be valid
    result = reasoner.verify_with_hierarchy(["T1", "T2"], "L2")
    assert result.result.name == "PROVEN"
    print(f"  [OK] L2 claim: {result.result.name}")
    print("  PASSED\n")
    return True

def test_find_support():
    print("Test 7: Find Support Paths")
    graph = create_test_graph()
    reasoner = LayerAwareReasoner(graph)
    
    supports = reasoner.find_support("T2")
    assert len(supports) > 0
    print(f"  [OK] Found {len(supports)} support path(s)")
    print("  PASSED\n")
    return True

def test_layer_summary():
    print("Test 8: Layer Summary")
    graph = create_test_graph()
    reasoner = LayerAwareReasoner(graph)
    
    summary = reasoner.get_layer_summary()
    assert len(summary["L1"]) == 2
    assert len(summary["L2"]) == 2
    assert len(summary["L3"]) == 2
    print(f"  [OK] L1={len(summary['L1'])}, L2={len(summary['L2'])}, L3={len(summary['L3'])}")
    print("  PASSED\n")
    return True

def run_all_tests():
    print("=" * 60)
    print("Symbolic Engine v2.0 Test Suite")
    print("=" * 60)
    print()
    
    tests = [
        test_shortest_path, test_shortest_path_avoid_layer,
        test_centrality, test_layer_analysis,
        test_connected_components, test_layer_aware_verify,
        test_find_support, test_layer_summary
    ]
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test(): passed += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
