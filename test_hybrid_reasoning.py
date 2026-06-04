"""Test suite for Hybrid Reasoning Engine"""
import sys
from hybrid_reasoning import (
    HybridReasoningEngine, ReasoningMode, FusionStrategy,
    SymbolicResult, LLMResult, HybridResult
)
from test_symbolic_v2 import create_test_graph

def test_symbolic_only():
    print("Test 1: Symbolic Only Mode")
    graph = create_test_graph()
    engine = HybridReasoningEngine(
        knowledge_graph=graph,
        mode=ReasoningMode.SYMBOLIC_ONLY
    )
    
    result = engine.reason("Prove A1 implies T1")
    assert result.mode == ReasoningMode.SYMBOLIC_ONLY
    assert result.symbolic_result is not None
    assert result.llm_result is None
    print(f"  [OK] Symbolic-only: proven={result.symbolic_result.proven}")
    print("  PASSED\n")
    return True

def test_llm_only():
    print("Test 2: LLM Only Mode")
    graph = create_test_graph()
    engine = HybridReasoningEngine(
        knowledge_graph=graph,
        mode=ReasoningMode.LLM_ONLY
    )
    
    result = engine.reason("What is meaning?")
    assert result.mode == ReasoningMode.LLM_ONLY
    assert result.symbolic_result is None
    assert result.llm_result is not None
    print(f"  [OK] LLM-only: confidence={result.llm_result.confidence}")
    print("  PASSED\n")
    return True

def test_hybrid_symbolic_first():
    print("Test 3: Hybrid Symbolic-First")
    graph = create_test_graph()
    engine = HybridReasoningEngine(
        knowledge_graph=graph,
        mode=ReasoningMode.HYBRID_SYMBOLIC_FIRST,
        strategy=FusionStrategy.CASCADE
    )
    
    # Query with known path
    result = engine.reason("Prove T1 derives T2")
    assert result.mode == ReasoningMode.HYBRID_SYMBOLIC_FIRST
    assert result.symbolic_result is not None
    assert result.llm_result is not None
    print(f"  [OK] Hybrid: symbolic_proven={result.symbolic_result.proven}, final_confidence={result.final_confidence:.2f}")
    print("  PASSED\n")
    return True

def test_cascade_strategy():
    print("Test 4: Cascade Strategy")
    graph = create_test_graph()
    engine = HybridReasoningEngine(
        knowledge_graph=graph,
        mode=ReasoningMode.HYBRID_SYMBOLIC_FIRST,
        strategy=FusionStrategy.CASCADE
    )
    
    # Known path - should use symbolic
    result1 = engine.reason("Prove A1 implies T1")
    # Unknown path - should fallback to LLM
    result2 = engine.reason("Explain quantum physics")
    
    assert result1.symbolic_result.proven or "fallback" not in str(result1.fusion_notes)
    print(f"  [OK] Cascade: known_path={result1.symbolic_result.proven}, unknown_fallback={'fallback' in str(result2.fusion_notes)}")
    print("  PASSED\n")
    return True

def test_weighted_strategy():
    print("Test 5: Weighted Strategy")
    graph = create_test_graph()
    engine = HybridReasoningEngine(
        knowledge_graph=graph,
        mode=ReasoningMode.HYBRID_SYMBOLIC_FIRST,
        strategy=FusionStrategy.WEIGHTED,
        symbolic_weight=0.7,
        llm_weight=0.3
    )
    
    result = engine.reason("Prove A1 implies T1")
    assert result.strategy == FusionStrategy.WEIGHTED
    print(f"  [OK] Weighted: confidence={result.final_confidence:.2f}")
    print("  PASSED\n")
    return True

def test_consensus_strategy():
    print("Test 6: Consensus Strategy")
    graph = create_test_graph()
    engine = HybridReasoningEngine(
        knowledge_graph=graph,
        mode=ReasoningMode.HYBRID_SYMBOLIC_FIRST,
        strategy=FusionStrategy.CONSENSUS
    )
    
    result = engine.reason("Prove A1 implies T1")
    assert result.strategy == FusionStrategy.CONSENSUS
    print(f"  [OK] Consensus: layer={result.final_layer}")
    print("  PASSED\n")
    return True

def test_adaptive_mode():
    print("Test 7: Adaptive Mode")
    graph = create_test_graph()
    engine = HybridReasoningEngine(
        knowledge_graph=graph,
        mode=ReasoningMode.ADAPTIVE
    )
    
    # Structured query - should use symbolic
    result1 = engine.reason("Prove A1 implies T1")
    # Unstructured query - should use LLM
    result2 = engine.reason("What is the meaning of life?")
    
    assert result1.mode == ReasoningMode.ADAPTIVE
    assert result2.mode == ReasoningMode.ADAPTIVE
    print(f"  [OK] Adaptive: structured_notes={result1.fusion_notes}, unstructured_notes={result2.fusion_notes}")
    print("  PASSED\n")
    return True

def test_stats():
    print("Test 8: Statistics")
    graph = create_test_graph()
    engine = HybridReasoningEngine(
        knowledge_graph=graph,
        mode=ReasoningMode.HYBRID_SYMBOLIC_FIRST
    )
    
    # Run multiple queries
    for _ in range(3):
        engine.reason("Prove A1 implies T1")
    
    stats = engine.get_stats()
    assert stats["symbolic_calls"] == 3
    assert stats["llm_calls"] == 3
    assert stats["fusion_calls"] == 3
    print(f"  [OK] Stats: symbolic_calls={stats['symbolic_calls']}, success_rate={stats['symbolic_success_rate']:.2f}")
    print("  PASSED\n")
    return True

def run_all_tests():
    print("=" * 60)
    print("Hybrid Reasoning Engine Test Suite")
    print("=" * 60)
    print()
    
    tests = [
        test_symbolic_only, test_llm_only,
        test_hybrid_symbolic_first, test_cascade_strategy,
        test_weighted_strategy, test_consensus_strategy,
        test_adaptive_mode, test_stats
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
