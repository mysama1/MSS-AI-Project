"""
Comprehensive Integration Test Suite for MSS-AI v1.0+
Covers: End-to-end workflows, edge cases, performance benchmarks
"""

import sys
import time
import os

# Import all components
from mss_tactic_integrated import MSSTactic
from symbolic_engine import MSSKnowledgeGraph, SymbolicReasoner, ConceptNode, NodeType, RelationEdge, RelationType
from auto_analyzer import AutoAnalyzer, SmartSymbolicReasoner, RiskLevel, Recommendation
from post_process_engine import PostProcessEngine, FilterRule, RuleCategory, RulePriority
from symbolic_engine import InferenceResult

def test_e2e_arbiter_responder_flow():
    """Test Arbiter→Responder end-to-end flow"""
    print("Test 1: E2E Arbiter→Responder Flow")

    tactic = MSSTactic(check_gpu=False)

    # Test with compliant query
    test_queries = [
        "What is the MSS framework?",
        "Explain the 0/1 critical mapping",
        "How does organizational resilience work?",
    ]

    for query in test_queries:
        # Simulate arbiter check
        arbiter_result = tactic.arbiter.check(query)
        assert arbiter_result is not None
        assert hasattr(arbiter_result, 'layer')
        print(f"  [OK] Arbiter processed: '{query[:40]}...' → Layer: {arbiter_result.layer.value}")

    print("  PASSED\n")
    return True

def test_post_process_integration():
    """Test post-processing integrated with MSSTactic"""
    print("Test 2: Post-Process Integration")

    tactic = MSSTactic(check_gpu=False)

    test_cases = [
        ("This is the ultimate solution.", "current best approach"),
        ("The perfect framework never fails.", "high fidelity"),
        ("This breakthrough transcends all limits.", "goes beyond"),
    ]

    for original, should_contain in test_cases:
        result = tactic._post_process(original)
        assert should_contain in result, \
            f"Expected '{should_contain}' in: {result}"
        assert original != result, "Text should be modified"

    # Check stats tracking
    assert tactic.stats.get("post_filter_replacements", 0) > 0
    print(f"  [OK] Post-filter replacements tracked: {tactic.stats['post_filter_replacements']}")

    print("  PASSED\n")
    return True

def test_symbolic_auto_analyzer_integration():
    """Test SymbolicEngine + AutoAnalyzer integration"""
    print("Test 3: Symbolic + AutoAnalyzer Integration")

    graph = MSSKnowledgeGraph()
    reasoner = SymbolicReasoner(graph)
    analyzer = AutoAnalyzer(graph.stats())
    smart = SmartSymbolicReasoner(reasoner, analyzer)

    # Add test nodes
    for i in range(5):
        node = ConceptNode(
            id=f"T{i}",
            name=f"Test Node {i}",
            node_type=NodeType.THEOREM,
            layer="L2",
            content=f"Content {i}",
            confidence=0.8
        )
        graph.add_node(node)

    # Add edges
    graph.add_edge(RelationEdge("T0", "T1", RelationType.IMPLIES))
    graph.add_edge(RelationEdge("T1", "T2", RelationType.DERIVES_FROM))

    # Test smart query
    result, nodes = smart.smart_query(layer="L2")
    assert result.recommendation == Recommendation.PROCEED
    assert len(nodes) == 5
    print(f"  [OK] Smart query: {len(nodes)} L2 nodes found")

    # Test path finding
    path = graph.find_path("T0", "T2")
    assert path is not None
    assert len(path.steps) == 2  # 2 steps = 3 nodes
    print(f"  [OK] Path found: T0 → T1 → T2 ({len(path.steps)} steps)")

    print("  PASSED\n")
    return True

def test_edge_cases():
    """Test edge cases and boundary conditions"""
    print("Test 4: Edge Cases")

    engine = PostProcessEngine()

    # Disable compliance rules for edge case testing (they interfere with long text)
    engine.disable_category(RuleCategory.COMPLIANCE)

    edge_cases = [
        # Empty input
        ("", "", "empty string"),
        # Single word
        ("solve", "address", "single forbidden word"),
        # Very long input (1000 words)
        ("solve " * 500, "address", "very long input"),
        # Unicode
        ("终极解决方案 solve the problem", "address", "mixed unicode"),
        # Already filtered
        ("This is the current best approach.", "current best approach", "already filtered"),
        # Multiple forbidden words
        ("The ultimate perfect solution that completely transcends all limits.",
         "current best high fidelity approach", "multiple forbidden words"),
        # Case variations
        ("SOLVE Solve solve SOLVED Solved solved", "address", "case variations"),
        # Punctuation
        ("Solve, solve; solve! solve?", "address", "punctuation"),
    ]

    for original, should_contain, description in edge_cases:
        result = engine.filter(original)
        if original:  # Skip empty check for empty string
            assert should_contain in result.text.lower(), \
                f"Failed for '{description}': {result.text}"
        print(f"  [OK] {description}")

    print("  PASSED\n")
    return True

def test_performance_benchmark():
    """Benchmark filter performance"""
    print("Test 5: Performance Benchmark")

    engine = PostProcessEngine()

    # Generate test text with forbidden words
    test_text = "The ultimate perfect solution completely transcends all limits. " * 100

    # Warm up
    for _ in range(5):
        engine.filter(test_text)
    engine.reset_session()

    # Benchmark
    iterations = 100
    start = time.time()
    for _ in range(iterations):
        engine.filter(test_text)
    elapsed = time.time() - start

    avg_time_ms = (elapsed / iterations) * 1000
    throughput = iterations / elapsed

    print(f"  Text length: {len(test_text)} chars")
    print(f"  Iterations: {iterations}")
    print(f"  Total time: {elapsed:.3f}s")
    print(f"  Avg per filter: {avg_time_ms:.3f}ms")
    print(f"  Throughput: {throughput:.1f} filters/sec")

    # Assert reasonable performance (< 10ms per filter for 5KB text)
    assert avg_time_ms < 10, f"Too slow: {avg_time_ms:.3f}ms per filter"
    print(f"  [OK] Performance within threshold")

    print("  PASSED\n")
    return True

def test_concurrent_rule_operations():
    """Test rule operations don't break filtering"""
    print("Test 6: Concurrent Rule Operations")

    engine = PostProcessEngine()

    # Filter while modifying rules
    text = "The ultimate solution is perfect."

    # Initial filter
    r1 = engine.filter(text)
    assert r1.had_changes

    # Disable a rule
    engine.disable_rule("ultimate_term")
    r2 = engine.filter(text)
    # Should still filter "perfect" but not "ultimate"
    assert "ultimate" in r2.text  # ultimate no longer filtered
    assert "perfect" not in r2.text  # perfect still filtered

    # Re-enable
    engine.enable_rule("ultimate_term")
    r3 = engine.filter(text)
    assert "ultimate" not in r3.text

    # Add new rule
    engine.add_rule(FilterRule(
        id="custom_test_rule",
        category=RuleCategory.TERMINOLOGY,
        priority=RulePriority.LOW,
        pattern=r'\bcustomword\b',
        replacement="replacedword"
    ))
    r4 = engine.filter("This has customword in it.")
    assert "replacedword" in r4.text

    print("  [OK] Rule modifications work correctly")
    print("  PASSED\n")
    return True

def test_knowledge_base_workflow():
    """Test full KB loading → query workflow"""
    print("Test 7: Knowledge Base Workflow")

    graph = MSSKnowledgeGraph()
    reasoner = SymbolicReasoner(graph)

    # Simulate loading from KB
    kb_entries = [
        {"id": "H100", "title": "Test Axiom 1", "layer": "L1", "content": "Information is fundamental"},
        {"id": "H101", "title": "Test Theorem 1", "layer": "L2", "content": "BCT coupling applies"},
        {"id": "H102", "title": "Test Concept 1", "layer": "L3", "content": "Metaphor for understanding"},
    ]

    for entry in kb_entries:
        node = ConceptNode(
            id=entry["id"],
            name=entry["title"],
            node_type=NodeType.AXIOM if entry["layer"] == "L1" else NodeType.THEOREM,
            layer=entry["layer"],
            content=entry["content"]
        )
        graph.add_node(node)

    # Add relations
    graph.add_edge(RelationEdge("H100", "H101", RelationType.IMPLIES))
    graph.add_edge(RelationEdge("H101", "H102", RelationType.ANALOGOUS))

    # Query by layer
    l1_nodes = graph.query(layer="L1")
    assert len(l1_nodes) == 1
    assert l1_nodes[0].id == "H100"
    print(f"  [OK] L1 query: {len(l1_nodes)} nodes")

    # Query by type
    theorems = graph.query(node_type=NodeType.THEOREM)
    assert len(theorems) == 2
    print(f"  [OK] Theorem query: {len(theorems)} nodes")

    # Path finding
    path = graph.find_path("H100", "H102")
    assert path is not None
    assert len(path.steps) == 2  # 2 steps = 3 nodes
    print(f"  [OK] Path H100→H102: {len(path.steps)} steps")

    # Verify claim
    result = reasoner.verify_claim("BCT coupling is fundamental", ["H100", "H101"])
    assert result.result == InferenceResult.PROVEN
    print(f"  [OK] Claim verification: {result.result}")

    # Stats
    stats = graph.stats()
    assert stats["total_nodes"] == 3
    assert stats["total_edges"] == 2
    print(f"  [OK] Graph stats: {stats}")

    print("  PASSED\n")
    return True

def test_stats_consistency():
    """Test that stats are consistent across components"""
    print("Test 8: Stats Consistency")

    tactic = MSSTactic(check_gpu=False)

    # Run multiple operations
    for i in range(5):
        tactic._post_process(f"This is the ultimate solution {i}.")

    # Check stats
    stats = tactic.get_stats()
    assert "post_filter_replacements" in stats
    assert stats["post_filter_replacements"] > 0
    print(f"  [OK] Post-filter stats: {stats['post_filter_replacements']} replacements")

    # Check engine stats
    engine_stats = tactic.post_processor.get_stats()
    assert engine_stats["total_filters"] == 5
    print(f"  [OK] Engine stats: {engine_stats['total_filters']} filters")

    print("  PASSED\n")
    return True

def test_error_handling():
    """Test graceful error handling"""
    print("Test 9: Error Handling")

    graph = MSSKnowledgeGraph()
    reasoner = SymbolicReasoner(graph)

    # Query non-existent node
    result = reasoner.explain("NONEXISTENT")
    assert "not found" in result.lower()
    print("  [OK] Non-existent node handled gracefully")

    # Path to non-existent node
    path = graph.find_path("A", "B")
    assert path is None
    print("  [OK] Missing path returns None")

    # Empty graph stats
    stats = graph.stats()
    assert stats["total_nodes"] == 0
    print("  [OK] Empty graph stats correct")

    # Auto-analyzer on missing file
    analyzer = AutoAnalyzer()
    result = analyzer.analyze_knowledge_base_loading("nonexistent.jsonl")
    assert result.recommendation.name == "ABORT"
    print("  [OK] Missing KB file returns ABORT")

    print("  PASSED\n")
    return True

def test_rule_priority_order():
    """Test that rules execute in correct priority order"""
    print("Test 10: Rule Priority Order")

    engine = PostProcessEngine()

    # Get rules sorted by priority
    rules = engine._rules_sorted

    # Verify order: priority ascending
    for i in range(len(rules) - 1):
        assert rules[i].priority.value <= rules[i+1].priority.value, \
            f"Rule order violation: {rules[i].id} ({rules[i].priority.value}) > {rules[i+1].id} ({rules[i+1].priority.value})"

    print(f"  [OK] {len(rules)} rules in correct priority order")
    print("  PASSED\n")
    return True

def run_all_tests():
    """Run comprehensive integration test suite"""
    print("=" * 70)
    print("MSS-AI Comprehensive Integration Test Suite")
    print("=" * 70)
    print()

    tests = [
        test_e2e_arbiter_responder_flow,
        test_post_process_integration,
        test_symbolic_auto_analyzer_integration,
        test_edge_cases,
        test_performance_benchmark,
        test_concurrent_rule_operations,
        test_knowledge_base_workflow,
        test_stats_consistency,
        test_error_handling,
        test_rule_priority_order,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            import traceback
            print(f"  FAILED: {e}")
            traceback.print_exc()
            print()
            failed += 1

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 70)

    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
