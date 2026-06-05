"""Test suite for MSS Checkpoint System"""
import sys, os, time, shutil
from mss_checkpoint import CheckpointManager, SessionSnapshot, AutoSaver, Checkpoint

def test_manual_checkpoint():
    print("Test 1: Manual Checkpoint")
    cm = CheckpointManager(checkpoint_dir="test_cp", max_checkpoints=3)

    cp = cm.save({"key": "value"}, label="test")
    assert cp is not None
    assert cp.data["key"] == "value"
    assert cp.label == "test"

    cm.clear_all()
    shutil.rmtree("test_cp", ignore_errors=True)
    print("  [OK] Manual save works")
    print("  PASSED\n")
    return True

def test_auto_check_time():
    print("Test 2: Auto-Check (Time-based)")
    cm = CheckpointManager(
        checkpoint_dir="test_cp2",
        max_checkpoints=3,
        auto_save_interval_sec=0.1,  # 100ms for testing
        auto_save_operations=999
    )

    # Should not trigger immediately
    cp1 = cm.auto_check({"step": 1})
    assert cp1 is None

    # Wait for interval
    time.sleep(0.15)
    cp2 = cm.auto_check({"step": 2})
    assert cp2 is not None
    assert "time" in cp2.label

    cm.clear_all()
    shutil.rmtree("test_cp2", ignore_errors=True)
    print("  [OK] Time-based auto-save works")
    print("  PASSED\n")
    return True

def test_auto_check_ops():
    print("Test 3: Auto-Check (Operation-based)")
    cm = CheckpointManager(
        checkpoint_dir="test_cp3",
        max_checkpoints=3,
        auto_save_interval_sec=999,
        auto_save_operations=3
    )

    cp = None
    for i in range(6):
        cp = cm.auto_check({"op": i})
        if cp:
            break

    assert cp is not None, "Auto-save should have triggered"
    assert "operations" in cp.label
    assert cp.metadata["operation_count"] == 3

    cm.clear_all()
    shutil.rmtree("test_cp3", ignore_errors=True)
    print("  [OK] Operation-based auto-save works")
    print("  PASSED\n")
    return True

def test_max_checkpoints():
    print("Test 4: Max Checkpoints Cleanup")
    cm = CheckpointManager(
        checkpoint_dir="test_cp4",
        max_checkpoints=2
    )

    cm.save({"n": 1}, label="1")
    cm.save({"n": 2}, label="2")
    cm.save({"n": 3}, label="3")

    assert len(cm.checkpoints) == 2
    assert cm.checkpoints[0].label == "2"
    assert cm.checkpoints[1].label == "3"

    cm.clear_all()
    shutil.rmtree("test_cp4", ignore_errors=True)
    print("  [OK] Old checkpoints cleaned up")
    print("  PASSED\n")
    return True

def test_recovery():
    print("Test 5: Recovery")
    cm = CheckpointManager(checkpoint_dir="test_cp5", max_checkpoints=3)

    cm.save({"important": "data", "version": 1}, label="before_crash")

    recovered = cm.recover()
    assert recovered["important"] == "data"
    assert recovered["version"] == 1

    cm.clear_all()
    shutil.rmtree("test_cp5", ignore_errors=True)
    print("  [OK] Recovery works")
    print("  PASSED\n")
    return True

def test_session_snapshot():
    print("Test 6: Session Snapshot")
    cm = CheckpointManager(checkpoint_dir="test_cp6", max_checkpoints=3)
    snapshot = SessionSnapshot(cm)

    snapshot.register("config", lambda: {"model": "qwen"})
    snapshot.register("stats", lambda: {"requests": 10})

    cp = snapshot.capture(label="full")
    assert "config" in cp.data
    assert "stats" in cp.data
    assert cp.data["config"]["model"] == "qwen"

    cm.clear_all()
    shutil.rmtree("test_cp6", ignore_errors=True)
    print("  [OK] Snapshot captures all components")
    print("  PASSED\n")
    return True

def test_disabled():
    print("Test 7: Disabled Mode")
    cm = CheckpointManager(enabled=False)

    cp = cm.save({"data": "test"})
    assert cp is None
    assert len(cm.checkpoints) == 0

    print("  [OK] Disabled mode prevents saves")
    print("  PASSED\n")
    return True

def test_persistence():
    print("Test 8: Disk Persistence")
    cm1 = CheckpointManager(checkpoint_dir="test_cp8", max_checkpoints=3)
    cm1.save({"persistent": True}, label="disk")

    # Create new manager, should load existing
    cm2 = CheckpointManager(checkpoint_dir="test_cp8", max_checkpoints=3)
    assert len(cm2.checkpoints) >= 1

    recovered = cm2.recover()
    assert recovered["persistent"] is True

    cm2.clear_all()
    shutil.rmtree("test_cp8", ignore_errors=True)
    print("  [OK] Checkpoints persist to disk")
    print("  PASSED\n")
    return True

def run_all_tests():
    print("=" * 60)
    print("MSS Checkpoint Test Suite")
    print("=" * 60)
    print()

    tests = [
        test_manual_checkpoint, test_auto_check_time,
        test_auto_check_ops, test_max_checkpoints,
        test_recovery, test_session_snapshot,
        test_disabled, test_persistence
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
