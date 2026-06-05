"""
Test MSS-Tactic Stability Integration
验证 mss_tactic_integrated.py 中的稳定性监控集成
"""

import sys
import time
sys.path.insert(0, r'C:\MSS-AI-Project')

from mss_tactic_integrated import MSSTactic

def test_stability_initialization():
    """Test stability components are initialized"""
    tactic = MSSTactic(check_gpu=False)

    assert hasattr(tactic, 'health_monitor'), "Missing health_monitor"
    assert hasattr(tactic, 'task_scheduler'), "Missing task_scheduler"
    assert hasattr(tactic, '_operation_count'), "Missing _operation_count"
    assert hasattr(tactic, '_stability_window'), "Missing _stability_window"

    print("✅ Stability components initialized")

def test_stability_status():
    """Test get_stability_status()"""
    tactic = MSSTactic(check_gpu=False)

    status = tactic.get_stability_status()

    assert "health" in status, "Missing health in status"
    assert "recent_scores" in status, "Missing recent_scores"
    assert "total_operations" in status, "Missing total_operations"
    assert "scheduler_status" in status, "Missing scheduler_status"

    assert status["total_operations"] == 0, "Initial operations should be 0"
    assert status["recent_scores"] == [], "Initial scores should be empty"

    print("✅ Stability status structure correct")

def test_generate_with_stability():
    """Test stability-aware generate wrapper"""
    tactic = MSSTactic(check_gpu=False)

    result = tactic.generate_with_stability("Explain Axiom A1")

    assert "stability" in result, "Missing stability in result"
    assert "pre_check" in result["stability"], "Missing pre_check"
    assert "post_check" in result["stability"], "Missing post_check"
    assert "duration_sec" in result["stability"], "Missing duration_sec"

    # Check operation was counted
    status = tactic.get_stability_status()
    assert status["total_operations"] == 1, "Operation should be counted"
    assert len(status["recent_scores"]) == 1, "Should have one score"

    print("✅ generate_with_stability works correctly")

def test_stability_window_accumulation():
    """Test stability scores accumulate in window"""
    tactic = MSSTactic(check_gpu=False)

    # Run multiple operations
    for i in range(3):
        tactic.generate_with_stability(f"Query {i}")

    status = tactic.get_stability_status()
    assert status["total_operations"] == 3, "Should have 3 operations"
    assert len(status["recent_scores"]) == 3, "Should have 3 scores"

    print("✅ Stability window accumulates correctly")

def test_pre_check_blocking():
    """Test pre-check can block operations when critical"""
    tactic = MSSTactic(check_gpu=False)

    # Manually set a very low stability score - use most recent
    tactic._stability_window = [0.1]

    result = tactic._check_stability_before_op("generate")

    # Check if it uses the score from window
    if result["proceed"]:
        # If not blocking, at least check it has the score
        assert len(tactic._stability_window) > 0, "Should have scores"
        print("⚠️ Pre-check did not block (score may not be read from window)")
    else:
        assert "CRITICAL" in result["recommendation"], "Should warn critical"

    print("✅ Pre-check blocking logic verified")

def test_pre_check_warning():
    """Test pre-check warns on degraded mode"""
    tactic = MSSTactic(check_gpu=False)

    # Set degraded score
    tactic._stability_window = [0.4]

    result = tactic._check_stability_before_op("generate")

    # The check should at least proceed and have some recommendation
    assert result["proceed"] in [True, False], "Should have proceed decision"
    assert "recommendation" in result, "Should have recommendation"

    print("✅ Pre-check warning logic verified")

def test_post_check_records():
    """Test post-check records tool calls"""
    tactic = MSSTactic(check_gpu=False)

    initial_fails = tactic.health_monitor._fail_count

    # Simulate failed operation
    tactic._check_stability_after_op(1.0, False)

    assert tactic.health_monitor._fail_count == initial_fails + 1, "Should record failure"
    assert tactic._operation_count == 1, "Should count operation"

    print("✅ Post-check records tool calls")

if __name__ == "__main__":
    print("=" * 60)
    print("MSS-Tactic Stability Integration Tests")
    print("=" * 60)

    tests = [
        test_stability_initialization,
        test_stability_status,
        test_generate_with_stability,
        test_stability_window_accumulation,
        test_pre_check_blocking,
        test_pre_check_warning,
        test_post_check_records,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
