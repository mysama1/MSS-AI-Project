"""
Test suite for MSS Exception Hierarchy
"""

import sys
from mss_exceptions import (
    ErrorCode, MSSBaseException,
    SystemException, ModelException, KnowledgeBaseException,
    SymbolicEngineException, PostProcessException,
    ValidationException, NetworkException, SecurityException,
    wrap_exception, safe_execute, ErrorLogger
)


def test_error_codes():
    """Test all error codes are unique and valid"""
    print("Test 1: Error Codes")
    
    codes = list(ErrorCode)
    values = [c.value for c in codes]
    
    # All unique
    assert len(values) == len(set(values)), "Duplicate error codes found"
    print(f"  [OK] {len(codes)} unique error codes")
    
    # Categorized correctly
    system_codes = [c for c in codes if 1000 <= c.value < 2000]
    model_codes = [c for c in codes if 2000 <= c.value < 3000]
    kb_codes = [c for c in codes if 3000 <= c.value < 4000]
    symbolic_codes = [c for c in codes if 4000 <= c.value < 5000]
    pp_codes = [c for c in codes if 5000 <= c.value < 6000]
    validation_codes = [c for c in codes if 6000 <= c.value < 7000]
    network_codes = [c for c in codes if 7000 <= c.value < 8000]
    security_codes = [c for c in codes if 8000 <= c.value < 9000]
    
    assert len(system_codes) > 0
    assert len(model_codes) > 0
    assert len(kb_codes) > 0
    print(f"  [OK] Categories: SYS={len(system_codes)} MDL={len(model_codes)} KB={len(kb_codes)} SYM={len(symbolic_codes)} PP={len(pp_codes)} VAL={len(validation_codes)} NET={len(network_codes)} SEC={len(security_codes)}")
    
    print("  PASSED\n")
    return True


def test_exception_creation():
    """Test exception creation and properties"""
    print("Test 2: Exception Creation")
    
    exc = ModelException(
        "Test error",
        code=ErrorCode.MODEL_TIMEOUT,
        details={"model": "test"}
    )
    
    assert exc.message == "Test error"
    assert exc.code == ErrorCode.MODEL_TIMEOUT
    assert exc.details == {"model": "test"}
    assert exc.cause is None
    
    # Test to_dict
    d = exc.to_dict()
    assert d["error"] is True
    assert d["code"] == 2003
    assert d["code_name"] == "MODEL_TIMEOUT"
    assert d["message"] == "Test error"
    
    print("  [OK] Exception properties correct")
    print("  PASSED\n")
    return True


def test_exception_hierarchy():
    """Test exception class hierarchy"""
    print("Test 3: Exception Hierarchy")
    
    exceptions = [
        SystemException("sys"),
        ModelException("model"),
        KnowledgeBaseException("kb"),
        SymbolicEngineException("sym"),
        PostProcessException("pp"),
        ValidationException("val"),
        NetworkException("net"),
        SecurityException("sec"),
    ]
    
    for exc in exceptions:
        assert isinstance(exc, MSSBaseException), f"{type(exc).__name__} not subclass of MSSBaseException"
        assert exc.to_dict()["error"] is True
    
    print(f"  [OK] All {len(exceptions)} exception types are proper subclasses")
    print("  PASSED\n")
    return True


def test_wrap_exception():
    """Test exception wrapping"""
    print("Test 4: Exception Wrapping")
    
    # Wrap built-in exception
    original = ValueError("original error")
    wrapped = wrap_exception(original, ModelException, ErrorCode.MODEL_INFERENCE_FAILED)
    
    assert isinstance(wrapped, ModelException)
    assert wrapped.code == ErrorCode.MODEL_INFERENCE_FAILED
    assert wrapped.cause is original
    assert wrapped.details["original_type"] == "ValueError"
    
    # Don't re-wrap MSS exceptions
    wrapped2 = wrap_exception(wrapped, SystemException)
    assert wrapped2 is wrapped
    
    print("  [OK] Exception wrapping works correctly")
    print("  PASSED\n")
    return True


def test_safe_execute():
    """Test safe execution wrapper"""
    print("Test 5: Safe Execute")
    
    # Successful execution
    def success(x):
        return x * 2
    
    result = safe_execute(success, 5, error_code=ErrorCode.SYSTEM_UNKNOWN)
    assert result == 10
    print("  [OK] Successful execution")
    
    # Failed execution
    def failure():
        raise RuntimeError("boom")
    
    try:
        safe_execute(failure, error_code=ErrorCode.SYSTEM_RESOURCE_EXHAUSTED)
        assert False, "Should have raised"
    except MSSBaseException as e:
        assert e.code == ErrorCode.SYSTEM_RESOURCE_EXHAUSTED
        assert e.cause is not None
        print("  [OK] Failed execution caught and wrapped")
    
    print("  PASSED\n")
    return True


def test_error_logger():
    """Test error logger"""
    print("Test 6: Error Logger")
    
    logger = ErrorLogger("test_module")
    
    # Log some errors
    for i in range(3):
        try:
            raise ValidationException(f"Error {i}", code=ErrorCode.VALIDATION_INPUT_EMPTY)
        except MSSBaseException as e:
            logger.log(e, context={"iteration": i})
    
    stats = logger.get_stats()
    assert stats["total_errors"] == 3
    assert stats["module"] == "test_module"
    assert ErrorCode.VALIDATION_INPUT_EMPTY.value in stats["error_codes"]
    assert len(stats["recent_errors"]) == 3
    
    print(f"  [OK] Logger tracked {stats['total_errors']} errors")
    print("  PASSED\n")
    return True


def test_exception_string_format():
    """Test exception string formatting"""
    print("Test 7: String Formatting")
    
    exc = ModelException(
        "Inference failed",
        code=ErrorCode.MODEL_TIMEOUT,
        details={"timeout": 30},
        cause=TimeoutError("Connection timed out")
    )
    
    s = str(exc)
    assert "MODEL_TIMEOUT" in s
    assert "Inference failed" in s
    assert "timeout" in s
    assert "TimeoutError" in s
    
    print(f"  [OK] Formatted: {s[:80]}...")
    print("  PASSED\n")
    return True


def test_catch_all():
    """Test catching all MSS exceptions"""
    print("Test 8: Catch-All Handler")
    
    exceptions_to_test = [
        SystemException("sys"),
        ModelException("model"),
        ValidationException("val"),
    ]
    
    for exc in exceptions_to_test:
        try:
            raise exc
        except MSSBaseException as e:
            assert e.to_dict()["error"] is True
            assert e.code.value > 0
    
    print("  [OK] All exceptions catchable via MSSBaseException")
    print("  PASSED\n")
    return True


def run_all_tests():
    """Run all exception tests"""
    print("=" * 60)
    print("MSS Exception Hierarchy Test Suite")
    print("=" * 60)
    print()
    
    tests = [
        test_error_codes,
        test_exception_creation,
        test_exception_hierarchy,
        test_wrap_exception,
        test_safe_execute,
        test_error_logger,
        test_exception_string_format,
        test_catch_all,
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
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
