"""
Test suite for MSS Post-Process Engine v2.0
"""

import sys
import os
from post_process_engine import (
    PostProcessEngine, FilterRule, FilterResult,
    RuleCategory, RulePriority, ReplacementRecord, filter_response
)

def test_basic_filtering():
    """Test basic terminology filtering"""
    print("Test 1: Basic Terminology Filtering")

    engine = PostProcessEngine()

    test_cases = [
        # (input, expected_contains, expected_not_contains)
        ("This is the ultimate solution.", "current best approach", "ultimate solution"),
        ("A perfect and complete framework.", "high fidelity", "perfect"),
        ("This breakthrough transcends limits.", "goes beyond", "transcend"),
        ("The final result is absolutely perfect.", "ongoing", "final"),
        ("We solve the problem completely.", "address", "solved"),
    ]

    for original, should_contain, should_not_contain in test_cases:
        result = engine.filter(original)
        filtered = result.text.lower()
        assert should_contain.lower() in filtered, \
            f"Expected '{should_contain}' in: {filtered}"
        assert should_not_contain.lower() not in filtered, \
            f"'{should_not_contain}' should not be in: {filtered}"
        assert result.had_changes, f"Expected changes for: {original}"

    print("  [OK] All basic filter tests passed")
    print("  PASSED\n")
    return True

def test_overconfidence_dampening():
    """Test assertion dampening rules"""
    print("Test 2: Overconfidence Dampening")

    engine = PostProcessEngine()

    test_cases = [
        ("This never fails.", "consistently performs", "never fails"),
        ("This always works correctly.", "consistently demonstrates", "always works"),
        ("The result is guaranteed.", "expected", "guaranteed"),
        ("This is undeniably correct.", "well-supported consistent", "undeniably correct"),
        ("Without a doubt, this clearly proves it.", "with high confidence", "without a doubt"),
        ("It is obviously true.", "apparently", "obviously"),
        ("This must be the answer.", "appears to be", "must be"),
    ]

    for original, should_contain, should_not_contain in test_cases:
        result = engine.filter(original)
        filtered = result.text.lower()
        assert should_contain.lower() in filtered, \
            f"Expected '{should_contain}' in: {filtered}"
        assert should_not_contain.lower() not in filtered, \
            f"'{should_not_contain}' should not be in: {filtered}"

    print("  [OK] All assertion dampening tests passed")
    print("  PASSED\n")
    return True

def test_tense_aware_replacements():
    """Test tense-aware replacement for transcend family"""
    print("Test 3: Tense-Aware Replacements")

    engine = PostProcessEngine()

    test_cases = [
        ("It transcends", "goes beyond", None),
        ("She transcended", "went beyond", None),
        ("They are transcending", "are going beyond", None),
        ("The transcendence", "going beyond", None),
    ]

    for original, should_contain, _ in test_cases:
        result = engine.filter(original)
        assert should_contain in result.text, \
            f"Expected '{should_contain}' in: {result.text}"

    print("  [OK] All tense-aware tests passed")
    print("  PASSED\n")
    return True

def test_no_false_positives():
    """Test that normal text is not modified"""
    print("Test 4: No False Positives")

    engine = PostProcessEngine()

    normal_texts = [
        "The cat sat on the mat and watched the birds fly by.",
        "Python is a programming language used for data science.",
        "The framework provides tools for analysis and visualization.",
        "Please process the request and return the results.",
        "Nature finds a way to balance ecosystems over time.",
    ]

    for text in normal_texts:
        result = engine.filter(text)
        assert not result.had_changes, \
            f"Expected no changes for: '{text}', got: '{result.text}'"

    print("  [OK] No false positives in normal text")
    print("  PASSED\n")
    return True

def test_rule_management():
    """Test rule enable/disable/add/remove"""
    print("Test 5: Rule Management")

    engine = PostProcessEngine()

    # Test disable/enable
    engine.disable_rule("solve_problem")
    assert not engine.rules["solve_problem"].enabled
    print("  [OK] Rule disabled")

    result = engine.filter("We solved the problem.")
    assert "solved" in result.text, "Disabled rule should not filter"
    print("  [OK] Disabled rule does not filter")

    engine.enable_rule("solve_problem")
    assert engine.rules["solve_problem"].enabled
    print("  [OK] Rule re-enabled")

    # Test category operations
    engine.disable_category(RuleCategory.ASSERTION)
    result = engine.filter("This never fails to impress.")
    assert "never fails" in result.text, "Disabled category should not filter"
    print("  [OK] Category disable works")

    engine.enable_category(RuleCategory.ASSERTION)
    result = engine.filter("This never fails to impress.")
    assert "consistently performs" in result.text
    print("  [OK] Category re-enable works")

    # Test add rule
    new_rule = FilterRule(
        id="test_new_rule",
        category=RuleCategory.TERMINOLOGY,
        priority=RulePriority.LOW,
        pattern=r'\btestword\b',
        replacement="replacedword",
        description="Test rule"
    )
    engine.add_rule(new_rule)
    assert "test_new_rule" in engine.rules
    print("  [OK] Rule added")

    result = engine.filter("This contains testword here.")
    assert "replacedword" in result.text
    print("  [OK] New rule works")

    # Test remove rule
    engine.remove_rule("test_new_rule")
    assert "test_new_rule" not in engine.rules
    print("  [OK] Rule removed")

    print("  PASSED\n")
    return True

def test_statistics():
    """Test statistics tracking"""
    print("Test 6: Statistics Tracking")

    engine = PostProcessEngine()

    # Initial stats
    stats = engine.get_stats()
    assert stats["total_filters"] == 0
    assert stats["total_replacements"] == 0
    print("  [OK] Initial stats correct")

    # Run filters
    engine.filter("This is the ultimate solution.")
    engine.filter("A perfect and complete answer.")

    stats = engine.get_stats()
    assert stats["total_filters"] == 2
    assert stats["total_replacements"] > 0
    print(f"  [OK] Stats after filtering: {stats['total_filters']} filters, {stats['total_replacements']} replacements")

    # Session replacements
    assert stats["session_total_replacements"] > 0
    print(f"  [OK] Session replacements tracked")

    print("  PASSED\n")
    return True

def test_export_import():
    """Test rules export and import"""
    print("Test 7: Export/Import")

    engine = PostProcessEngine()

    # Export rules
    exported = engine.export_rules()
    assert len(exported) > 0
    assert "id" in exported[0]
    assert "category" in exported[0]
    print(f"  [OK] Exported {len(exported)} rules")

    # Import into new engine
    engine2 = PostProcessEngine()
    count = engine2.import_rules(exported)
    assert count == len(exported)
    print(f"  [OK] Imported {count} rules")

    # Verify filtering works on imported
    result = engine2.filter("This is the ultimate solution.")
    assert "current best approach" in result.text
    print("  [OK] Imported rules function correctly")

    print("  PASSED\n")
    return True

def test_case_preservation():
    """Test case-preserving replacements"""
    print("Test 8: Case Preservation")

    engine = PostProcessEngine()

    test_cases = [
        # (input, expected_contains)
        ("THE ULTIMATE SOLUTION.", "CURRENT BEST APPROACH"),
        ("The Ultimate Solution.", "The Current Best Approach"),
        ("the ultimate solution.", "the current best approach"),
    ]

    for original, should_contain in test_cases:
        result = engine.filter(original)
        assert should_contain in result.text, \
            f"Expected '{should_contain}' in: {result.text}"

    print("  [OK] All case preservation tests passed")
    print("  PASSED\n")
    return True

def test_legacy_compatibility():
    """Test legacy filter_response compatibility"""
    print("Test 9: Legacy Compatibility")

    result = filter_response("This is the ultimate solution.")
    assert "current best approach" in result
    print("  [OK] filter_response() works")

    print("  PASSED\n")
    return True

def test_structure_rules():
    """Test structure/compliance rules"""
    print("Test 10: Structure Rules")

    engine = PostProcessEngine()

    # Test quadruple backtick fix (```` should become ```)
    result = engine.filter("````")
    assert result.text == "```", f"Expected triple backtick, got: {result.text}"
    print("  [OK] Quadruple backtick fixed to triple")

    print("  PASSED\n")
    return True

def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("MSS Post-Process Engine v2.0 Test Suite")
    print("=" * 60)
    print()

    tests = [
        test_basic_filtering,
        test_overconfidence_dampening,
        test_tense_aware_replacements,
        test_no_false_positives,
        test_rule_management,
        test_statistics,
        test_export_import,
        test_case_preservation,
        test_legacy_compatibility,
        test_structure_rules,
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
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
