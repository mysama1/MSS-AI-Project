"""Test suite for MSS Stability Monitor"""
import sys, time
from mss_stability import (
    SystemHealthMonitor, AdaptiveTaskScheduler,
    StabilityLevel, TaskPriority, quick_stability_check
)

def test_quick_check():
    print("Test 1: Quick Stability Check")
    report = quick_stability_check()
    assert report.level in StabilityLevel
    assert 0.0 <= report.score <= 1.0
    assert len(report.recommendation) > 0
    print(f"  [OK] Level={report.level.name}, Score={report.score:.3f}")
    print("  PASSED\n")
    return True

def test_tool_call_tracking():
    print("Test 2: Tool Call Tracking")
    monitor = SystemHealthMonitor(enabled=False)

    # Record successful calls
    for _ in range(8):
        monitor.record_tool_call(True, 500)

    # Record failed calls
    for _ in range(2):
        monitor.record_tool_call(False, 2000)

    report = monitor.calculate_stability()
    assert report.metrics.tool_success_rate == 0.8
    print(f"  [OK] Success rate: {report.metrics.tool_success_rate:.1%}")
    print("  PASSED\n")
    return True

def test_stability_degradation():
    print("Test 3: Stability Degradation")
    monitor = SystemHealthMonitor(enabled=False)

    # Simulate degradation
    for _ in range(10):
        monitor.record_tool_call(False, 10000)

    report = monitor.calculate_stability()
    assert report.score < 0.6, f"Expected degraded, got {report.score}"
    assert report.level in (StabilityLevel.CRITICAL, StabilityLevel.DEGRADED)
    print(f"  [OK] Degraded to {report.level.name}, score={report.score:.3f}")
    print("  PASSED\n")
    return True

def test_task_scheduler():
    print("Test 4: Task Scheduler")
    monitor = SystemHealthMonitor(enabled=False)
    scheduler = AdaptiveTaskScheduler(monitor)

    executed = []

    def task_a():
        executed.append("a")
        return "done"

    scheduler.register_task("task_a", TaskPriority.HIGH, "test", task_a)

    result = scheduler.execute_next()
    assert result is not None
    assert result["status"] == "completed"
    assert "a" in executed
    print(f"  [OK] Task executed: {result['name']}")
    print("  PASSED\n")
    return True

def test_priority_filtering():
    print("Test 5: Priority Filtering")
    monitor = SystemHealthMonitor(enabled=False)

    # Degrade stability
    for _ in range(10):
        monitor.record_tool_call(False, 5000)

    scheduler = AdaptiveTaskScheduler(monitor)

    def critical_task():
        return "critical"

    def background_task():
        return "background"

    scheduler.register_task("critical", TaskPriority.CRITICAL, "checkpoint", critical_task)
    scheduler.register_task("background", TaskPriority.BACKGROUND, "cleanup", background_task)

    results = scheduler.execute_all_possible()

    # In degraded mode, critical should execute, background may be skipped
    assert results["executed"] + results["skipped"] == 2
    print(f"  [OK] Executed: {results['executed']}, Skipped: {results['skipped']}")
    print("  PASSED\n")
    return True

def test_can_execute():
    print("Test 6: Can Execute Check")
    monitor = SystemHealthMonitor(enabled=False)
    scheduler = AdaptiveTaskScheduler(monitor)

    # Optimal mode
    can, reason = scheduler.can_execute("analysis")
    assert can is True
    print(f"  [OK] Analysis allowed: {can}")

    print("  PASSED\n")
    return True

def test_status_report():
    print("Test 7: Status Report")
    monitor = SystemHealthMonitor(enabled=False)
    scheduler = AdaptiveTaskScheduler(monitor)

    status = scheduler.get_status()
    assert "stability" in status
    assert "queue_size" in status
    print(f"  [OK] Status keys: {list(status.keys())}")
    print("  PASSED\n")
    return True

def run_all_tests():
    print("=" * 60)
    print("MSS Stability Monitor Test Suite")
    print("=" * 60)
    print()

    tests = [
        test_quick_check, test_tool_call_tracking,
        test_stability_degradation, test_task_scheduler,
        test_priority_filtering, test_can_execute,
        test_status_report
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
