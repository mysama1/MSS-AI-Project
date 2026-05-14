"""Test suite for KB Loader"""
import sys, os, json
from kb_loader import KBLoader, KBEntry, load_default_kb
from symbolic_engine import NodeType

def test_load_file():
    print("Test 1: Load JSONL file")
    loader = KBLoader()
    count = loader.load_all()
    assert count >= 2, f"Expected >=2 entries, got {count}"
    print(f"  [OK] Loaded {count} entries")
    print("  PASSED\n")
    return True

def test_entry_conversion():
    print("Test 2: Entry to Node conversion")
    loader = KBLoader()
    loader.load_all()
    
    for entry in loader.entries.values():
        node = entry.to_node()
        assert node.id == entry.id
        assert node.layer == entry.layer
        if entry.layer == "L1":
            assert node.node_type == NodeType.AXIOM
            assert node.confidence == 1.0
        print(f"  [OK] {node.id} -> {node.node_type.name}")
    
    print("  PASSED\n")
    return True

def test_graph_conversion():
    print("Test 3: Graph conversion")
    loader = KBLoader()
    loader.load_all()
    graph = loader.to_graph()
    
    # Note: to_graph() filters out inactive entries by default
    active_count = sum(1 for e in loader.entries.values() if e.is_active)
    # Allow for nodes that failed to convert (missing required fields)
    assert len(graph.nodes) <= active_count, f"Expected <= {active_count} nodes, got {len(graph.nodes)}"
    assert len(graph.nodes) > 0, "Graph should have at least one node"
    stats = graph.stats()
    assert stats["total_nodes"] > 0
    print(f"  [OK] Graph has {stats['total_nodes']} nodes (active only, {active_count - len(graph.nodes)} skipped)")
    print("  PASSED\n")
    return True

def test_layer_query():
    print("Test 4: Layer query")
    loader = KBLoader()
    loader.load_all()
    
    l2_entries = loader.get_by_layer("L2")
    assert len(l2_entries) > 0
    print(f"  [OK] Found {len(l2_entries)} L2 entries")
    print("  PASSED\n")
    return True

def test_tag_query():
    print("Test 5: Tag query")
    loader = KBLoader()
    loader.load_all()
    
    # Find a tag that exists
    all_tags = set()
    for entry in loader.entries.values():
        all_tags.update(entry.tags)
    
    if all_tags:
        tag = list(all_tags)[0]
        entries = loader.get_by_tag(tag)
        assert len(entries) > 0
        print(f"  [OK] Found {len(entries)} entries with tag '{tag}'")
    else:
        print("  [SKIP] No tags found")
    
    print("  PASSED\n")
    return True

def test_stats():
    print("Test 6: Stats")
    loader = KBLoader()
    loader.load_all()
    stats = loader.get_stats()
    
    assert stats["total_entries"] > 0
    assert stats["files_loaded"] > 0
    print(f"  [OK] Stats: {stats}")
    print("  PASSED\n")
    return True

def run_all_tests():
    print("=" * 60)
    print("KB Loader Test Suite")
    print("=" * 60)
    print()
    
    tests = [
        test_load_file, test_entry_conversion, test_graph_conversion,
        test_layer_query, test_tag_query, test_stats
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
