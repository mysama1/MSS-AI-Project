"""
Test suite for MSS Symbolic Reasoning Engine
"""

import sys
from symbolic_engine import (
    MSSKnowledgeGraph, ConceptNode, RelationEdge,
    NodeType, RelationType, InferenceResult, SymbolicReasoner
)

def test_graph_creation():
    """Test basic graph operations"""
    print("Test 1: Graph Creation")

    graph = MSSKnowledgeGraph()

    # Add nodes
    n1 = ConceptNode("A1", "Test Axiom", NodeType.AXIOM, "L1", "Test content")
    n2 = ConceptNode("T1", "Test Theorem", NodeType.THEOREM, "L2", "Derived content")
    graph.add_node(n1)
    graph.add_node(n2)

    assert len(graph.nodes) == 2
    assert graph.get_node("A1").name == "Test Axiom"
    print("  [OK] Nodes added and retrieved")

    # Add edge
    edge = RelationEdge("A1", "T1", RelationType.IMPLIES)
    graph.add_edge(edge)

    assert len(graph.edges) == 1
    neighbors = graph.get_neighbors("A1")
    assert len(neighbors) == 1
    assert neighbors[0].id == "T1"
    print("  [OK] Edge added and neighbors retrieved")

    print("  PASSED\n")
    return True

def test_path_finding():
    """Test path finding between nodes"""
    print("Test 2: Path Finding")

    graph = MSSKnowledgeGraph()

    # Create chain: A1 -> T1 -> T2
    nodes = [
        ConceptNode("A1", "Axiom 1", NodeType.AXIOM, "L1", "Base"),
        ConceptNode("T1", "Theorem 1", NodeType.THEOREM, "L2", "Derived 1"),
        ConceptNode("T2", "Theorem 2", NodeType.THEOREM, "L2", "Derived 2"),
    ]
    for n in nodes:
        graph.add_node(n)

    edges = [
        RelationEdge("A1", "T1", RelationType.IMPLIES),
        RelationEdge("T1", "T2", RelationType.IMPLIES),
    ]
    for e in edges:
        graph.add_edge(e)

    # Find path A1 -> T2
    path = graph.find_path("A1", "T2", max_depth=3)
    assert path.result == InferenceResult.PROVEN
    assert len(path.steps) == 2
    print("  [OK] Path found: A1 -> T1 -> T2")

    # No path A1 -> nonexistent
    path = graph.find_path("A1", "X1", max_depth=3)
    assert path is None
    print("  [OK] Missing node returns None")

    print("  PASSED\n")
    return True

def test_contradiction_detection():
    """Test contradiction detection"""
    print("Test 3: Contradiction Detection")

    graph = MSSKnowledgeGraph()

    nodes = [
        ConceptNode("A", "Concept A", NodeType.THEOREM, "L2", "A"),
        ConceptNode("B", "Concept B", NodeType.THEOREM, "L2", "B"),
    ]
    for n in nodes:
        graph.add_node(n)

    # Direct contradiction
    graph.add_edge(RelationEdge("A", "B", RelationType.CONTRADICTS))

    result = graph.check_contradiction("A", "B")
    assert result.result == InferenceResult.DISPROVEN
    print("  [OK] Direct contradiction detected")

    # No contradiction
    result = graph.check_contradiction("B", "A")
    assert result.result == InferenceResult.UNDETERMINED
    print("  [OK] No false positives")

    print("  PASSED\n")
    return True

def test_reasoner_verify():
    """Test reasoner claim verification"""
    print("Test 4: Reasoner Verification")

    graph = MSSKnowledgeGraph()
    nodes = [
        ConceptNode("A1", "Axiom", NodeType.AXIOM, "L1", "Base truth"),
        ConceptNode("T1", "Theorem", NodeType.THEOREM, "L2", "Derived"),
    ]
    for n in nodes:
        graph.add_node(n)
    graph.add_edge(RelationEdge("A1", "T1", RelationType.IMPLIES))

    reasoner = SymbolicReasoner(graph)

    # Valid claim
    result = reasoner.verify_claim("Test", ["A1", "T1"])
    assert result.result == InferenceResult.PROVEN
    print("  [OK] Valid claim verified")

    # Missing reference
    result = reasoner.verify_claim("Test", ["A1", "X1"])
    assert result.result == InferenceResult.UNDETERMINED
    print("  [OK] Missing reference detected")

    print("  PASSED\n")
    return True

def test_layer_query():
    """Test layer-based queries"""
    print("Test 5: Layer Query")

    graph = MSSKnowledgeGraph()

    for i, layer in enumerate(["L1", "L1", "L2", "L3"]):
        node_type = NodeType.AXIOM if layer == "L1" else NodeType.THEOREM if layer == "L2" else NodeType.CONCEPT
        graph.add_node(ConceptNode(f"N{i}", f"Node {i}", node_type, layer, f"Content {i}"))

    l1_nodes = graph.query(layer="L1")
    assert len(l1_nodes) == 2
    print("  [OK] L1 query returns 2 nodes")

    l3_nodes = graph.query(layer="L3")
    assert len(l3_nodes) == 1
    print("  [OK] L3 query returns 1 node")

    print("  PASSED\n")
    return True

def test_stats():
    """Test graph statistics"""
    print("Test 6: Graph Statistics")

    graph = MSSKnowledgeGraph()

    # Empty graph
    stats = graph.stats()
    assert stats["total_nodes"] == 0
    print("  [OK] Empty graph stats correct")

    # Add nodes
    graph.add_node(ConceptNode("A1", "A", NodeType.AXIOM, "L1", "x"))
    graph.add_node(ConceptNode("T1", "T", NodeType.THEOREM, "L2", "y"))
    graph.add_edge(RelationEdge("A1", "T1", RelationType.IMPLIES))

    stats = graph.stats()
    assert stats["total_nodes"] == 2
    assert stats["by_layer"]["L1"] == 1
    assert stats["by_layer"]["L2"] == 1
    print("  [OK] Stats accurate")

    print("  PASSED\n")
    return True

def run_all_tests():
    """Run all symbolic engine tests"""
    print("=" * 60)
    print("Symbolic Engine Test Suite")
    print("=" * 60)
    print()

    tests = [
        test_graph_creation,
        test_path_finding,
        test_contradiction_detection,
        test_reasoner_verify,
        test_layer_query,
        test_stats,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  FAILED: {e}\n")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
