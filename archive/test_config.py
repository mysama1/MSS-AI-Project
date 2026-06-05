"""Test suite for MSS Configuration Management"""
import sys, os
from mss_config import MSSConfig, Environment, load_config, get_config, set_config

def test_default_config():
    print("Test 1: Default Config")
    c = MSSConfig()
    assert c.environment == Environment.DEVELOPMENT
    assert c.model.arbiter_model == "qwen2.5:7b"
    assert c.model.temperature == 0.05
    print("  [OK] Defaults correct")
    print("  PASSED\n")
    return True

def test_env_configs():
    print("Test 2: Environment Configs")
    dev = load_config(Environment.DEVELOPMENT)
    assert dev.logging.level == "DEBUG"
    assert dev.model.check_gpu == False

    test = load_config(Environment.TESTING)
    assert test.logging.file_enabled == False
    assert test.symbolic.cache_enabled == False

    prod = load_config(Environment.PRODUCTION)
    assert prod.logging.level == "INFO"
    assert prod.security.content_filter_enabled == True
    print("  [OK] All environments configured")
    print("  PASSED\n")
    return True

def test_dot_notation():
    print("Test 3: Dot Notation")
    c = MSSConfig()
    assert c.get("model.arbiter_model") == "qwen2.5:7b"
    assert c.get("nonexistent", "default") == "default"

    c.set("model.temperature", 0.1)
    assert c.model.temperature == 0.1
    print("  [OK] Dot notation works")
    print("  PASSED\n")
    return True

def test_validation():
    print("Test 4: Validation")
    c = MSSConfig()
    assert c.validate() == []

    c.model.temperature = 3.0
    issues = c.validate()
    assert len(issues) > 0
    assert "temperature" in issues[0]
    print(f"  [OK] Validation caught: {issues[0]}")
    print("  PASSED\n")
    return True

def test_save_load():
    print("Test 5: Save/Load")
    c = MSSConfig()
    c.version = "1.2.3"
    c.set("model.arbiter_model", "test-model")

    c.save("test_config.json")
    loaded = MSSConfig.load("test_config.json")

    assert loaded.version == "1.2.3"
    assert loaded.model.arbiter_model == "test-model"

    os.remove("test_config.json")
    print("  [OK] Save/load roundtrip")
    print("  PASSED\n")
    return True

def test_global_config():
    print("Test 6: Global Config")
    c = MSSConfig()
    c.version = "global-test"
    set_config(c)

    g = get_config()
    assert g.version == "global-test"
    print("  [OK] Global config works")
    print("  PASSED\n")
    return True

def run_all_tests():
    print("=" * 60)
    print("MSS Config Test Suite")
    print("=" * 60)
    print()

    tests = [test_default_config, test_env_configs, test_dot_notation,
             test_validation, test_save_load, test_global_config]
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
