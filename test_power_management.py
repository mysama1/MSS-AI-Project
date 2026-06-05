"""
Test suite for Power Management functionality
"""

import sys
import time
from mss_tactic_integrated import MSSTactic

def test_power_basic():
    """Test basic power management functionality"""
    print("Test 1: Basic Power Management")

    tactic = MSSTactic(check_gpu=False)

    # Enable with short timeouts for testing
    result = tactic.enable_power_management(standby_timeout=1, hibernate_timeout=2)
    assert result["enabled"] == True
    assert result["current_state"] == "active"
    print("  [OK] Power management enabled")

    # Check status
    status = tactic.get_power_status()
    assert status["state"] == "active"
    assert status["standby_timeout"] == 1
    print("  [OK] Status check OK")

    # Manual standby
    result = tactic.manual_standby()
    assert result["success"] == True
    assert result["current_state"] == "standby"
    print("  [OK] Manual standby OK")

    # Resume
    result = tactic.manual_resume()
    assert result["success"] == True
    assert result["current_state"] == "active"
    print("  [OK] Resume from standby OK")

    # Manual hibernate
    result = tactic.manual_hibernate()
    assert result["success"] == True
    assert result["current_state"] == "hibernate"
    print("  [OK] Manual hibernate OK")

    # Resume from hibernate
    result = tactic.manual_resume()
    assert result["success"] == True
    assert result["current_state"] == "active"
    print("  [OK] Resume from hibernate OK")

    print("  PASSED\n")
    return True

def test_power_not_enabled():
    """Test behavior when power management not enabled"""
    print("Test 2: Power Management Not Enabled")

    tactic = MSSTactic(check_gpu=False)
    # Don't enable power management

    result = tactic.manual_standby()
    assert result["success"] == False
    assert "not enabled" in result["message"]
    print("  [OK] Standby without PM returns error")

    result = tactic.get_power_status()
    assert result["enabled"] == False
    print("  [OK] Status without PM returns disabled")

    print("  PASSED\n")
    return True

def test_activity_tracking():
    """Test activity tracking affects idle time"""
    print("Test 3: Activity Tracking")

    from power_manager import PowerManager

    pm = PowerManager()

    # Initial idle time should be very small
    time.sleep(0.1)
    idle1 = pm.get_idle_time_seconds()
    assert idle1 > 0
    print(f"  [OK] Initial idle: {idle1:.3f}s")

    # Record activity
    pm.record_activity("test")
    idle2 = pm.get_idle_time_seconds()
    assert idle2 < idle1
    print(f"  [OK] After activity: {idle2:.3f}s (reset)")

    print("  PASSED\n")
    return True

def test_auto_transition():
    """Test automatic state transitions"""
    print("Test 4: Auto Transition Logic")

    from power_manager import PowerManager, PowerProfile

    # Very short timeouts for testing
    profile = PowerProfile(
        standby_timeout_minutes=0.01,  # 0.6 seconds
        hibernate_timeout_minutes=0.02  # 1.2 seconds
    )
    pm = PowerManager(profile)

    # Should not trigger immediately
    result = pm.check_auto_power_management()
    assert result is None
    print("  [OK] No immediate transition")

    # Wait for standby
    time.sleep(0.8)
    result = pm.check_auto_power_management()
    assert result is not None
    assert result["current_state"] == "standby"
    print("  [OK] Auto-standby triggered")

    # Wait for hibernate
    time.sleep(0.8)
    result = pm.check_auto_power_management()
    assert result is not None
    assert result["current_state"] == "hibernate"
    print("  [OK] Auto-hibernate triggered")

    print("  PASSED\n")
    return True

def test_state_persistence():
    """Test hibernate state save/load"""
    print("Test 5: State Persistence")

    from power_manager import PowerManager, SystemState
    import os
    import json

    pm = PowerManager()

    # Create a mock state
    state = SystemState(
        timestamp="2026-05-10T00:00:00",
        active_model="qwen2.5:7b",
        loaded_models=["qwen2.5:7b", "mss-ai-v1"],
        dialog_history_count=5,
        stats_snapshot={"total_requests": 100},
        skill_context_level="L2",
        arbiter_config={}
    )

    # Save state
    pm._save_state_to_disk(state)
    assert os.path.exists(pm.state_file_path)
    print("  [OK] State saved to disk")

    # Load state
    loaded = pm._load_state_from_disk()
    assert loaded is not None
    assert loaded.active_model == "qwen2.5:7b"
    assert loaded.loaded_models == ["qwen2.5:7b", "mss-ai-v1"]
    print("  [OK] State loaded from disk")

    # Cleanup
    os.remove(pm.state_file_path)
    print("  [OK] Cleanup completed")

    print("  PASSED\n")
    return True

def run_all_tests():
    """Run all power management tests"""
    print("=" * 60)
    print("MSS-AI Power Management Test Suite")
    print("=" * 60)
    print()

    tests = [
        test_power_basic,
        test_power_not_enabled,
        test_activity_tracking,
        test_auto_transition,
        test_state_persistence,
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
