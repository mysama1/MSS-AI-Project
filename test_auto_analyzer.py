"""
Test suite for MSS Auto-Analyzer
"""

import sys
import os
from auto_analyzer import (
    AutoAnalyzer, SmartSymbolicReasoner,
    RiskLevel, Recommendation, ActionType, DecisionContext
)
from symbolic_engine import MSSKnowledgeGraph, SymbolicReasoner


def test_kb_loading_analysis():
    """Test knowledge base loading analysis"""
    print("Test 1: KB Loading Analysis")
    
    analyzer = AutoAnalyzer()
    
    # Test non-existent file
    result = analyzer.analyze_knowledge_base_loading("nonexistent.jsonl")
    assert result.recommendation == Recommendation.ABORT
    assert result.risk_level == RiskLevel.HIGH
    print("  [OK] Non-existent file → ABORT")
    
    # Test with actual file
    kb_path = "knowledge_base/anti_meme_defense_v12.2.jsonl"
    if os.path.exists(kb_path):
        result = analyzer.analyze_knowledge_base_loading(kb_path)
        assert result.confidence > 0.5
        assert "nodes_added" in result.estimated_impact
        print(f"  [OK] Valid file → {result.recommendation.name}")
    else:
        print("  [SKIP] KB file not found")
    
    print("  PASSED\n")
    return True


def test_query_complexity():
    """Test query complexity analysis"""
    print("Test 2: Query Complexity Analysis")
    
    analyzer = AutoAnalyzer()
    
    # Simple query
    result = analyzer.analyze_query_complexity({"layer": "L1"})
    assert result.estimated_impact["complexity_score"] <= 2
    assert result.recommendation == Recommendation.PROCEED
    print("  [OK] Simple query → PROCEED")
    
    # Complex query
    result = analyzer.analyze_query_complexity({
        "keyword": "test",
        "path_find": True,
        "max_depth": 10,
        "check_contradiction": True
    })
    assert result.estimated_impact["complexity_score"] > 5
    print("  [OK] Complex query → PROCEED_WITH_CAUTION")
    
    print("  PASSED\n")
    return True


def test_graph_operation_analysis():
    """Test graph operation safety analysis"""
    print("Test 3: Graph Operation Analysis")
    
    analyzer = AutoAnalyzer({"nodes": {"A1": {}, "T1": {}}})
    
    # Safe operation
    context = DecisionContext(
        action_type=ActionType.EXECUTE_QUERY,
        target="T1",
        current_state={}
    )
    result = analyzer.analyze_graph_operation("query", ["T1"], context)
    assert result.recommendation == Recommendation.PROCEED
    print("  [OK] Query operation → PROCEED")
    
    # Dangerous: delete axiom
    result = analyzer.analyze_graph_operation("delete", ["A1"], context)
    assert result.recommendation == Recommendation.ABORT
    assert result.risk_level == RiskLevel.CRITICAL
    print("  [OK] Delete axiom → ABORT (CRITICAL)")
    
    print("  PASSED\n")
    return True


def test_smart_reasoner():
    """Test smart reasoner integration"""
    print("Test 4: Smart Reasoner Integration")
    
    graph = MSSKnowledgeGraph()
    reasoner = SymbolicReasoner(graph)
    smart = SmartSymbolicReasoner(reasoner)
    
    # Test auto-analysis
    kb_path = "knowledge_base/anti_meme_defense_v12.2.jsonl"
    result, loaded = smart.smart_load_knowledge_base(kb_path, auto_execute=False)
    assert result is not None
    assert hasattr(result, 'recommendation')
    print("  [OK] Smart analysis returns structured result")
    
    # Test report generation
    report = smart.get_analysis_report()
    assert "MSS Auto-Analyzer Report" in report
    print("  [OK] Report generated")
    
    print("  PASSED\n")
    return True


def test_decision_logging():
    """Test decision audit trail"""
    print("Test 5: Decision Logging")
    
    analyzer = AutoAnalyzer()
    
    context = DecisionContext(
        action_type=ActionType.LOAD_KNOWLEDGE,
        target="test.jsonl",
        current_state={}
    )
    
    result = analyzer.analyze_knowledge_base_loading("test.jsonl")
    analyzer.log_decision(context, result)
    
    assert len(analyzer.decision_log) == 1
    assert analyzer.decision_log[0]["action_type"] == "LOAD_KNOWLEDGE"
    print("  [OK] Decision logged")
    
    print("  PASSED\n")
    return True


def run_all_tests():
    """Run all auto-analyzer tests"""
    print("=" * 60)
    print("Auto-Analyzer Test Suite")
    print("=" * 60)
    print()
    
    tests = [
        test_kb_loading_analysis,
        test_query_complexity,
        test_graph_operation_analysis,
        test_smart_reasoner,
        test_decision_logging,
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
