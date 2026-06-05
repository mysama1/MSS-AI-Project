"""
Test suite for MSS-Tactic v0.1
Validates Arbiter→Responder orchestration flow
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mss_tactic import MSSTactic, ArbiterAgent, ResponderAgent, Layer, ComplianceStatus

def test_arbiter_forbidden_detection():
    """Test 1: Arbiter detects forbidden words"""
    print("Test 1: Forbidden word detection")
    arbiter = ArbiterAgent()

    test_cases = [
        ("solve the problem", ["solve"]),
        ("ultimate truth", ["ultimate"]),
        ("perfect alignment", ["perfect"]),
        ("complete solution", ["complete"]),
        ("breakthrough discovery", ["breakthrough"]),
        ("final answer", ["final"]),
        ("absolute certainty", ["absolute"]),
        ("transcend limitations", ["transcend"]),
        ("normal query without issues", []),
    ]

    passed = 0
    for query, expected in test_cases:
        result = arbiter.check(query)
        detected = result.forbidden_words

        if expected:
            if all(e in detected for e in expected):
                print(f"  PASS: '{query}' → detected {detected}")
                passed += 1
            else:
                print(f"  FAIL: '{query}' → expected {expected}, got {detected}")
        else:
            if not detected:
                print(f"  PASS: '{query}' → no forbidden words")
                passed += 1
            else:
                print(f"  FAIL: '{query}' → unexpected {detected}")

    print(f"Result: {passed}/{len(test_cases)} passed\n")
    return passed == len(test_cases)

def test_arbiter_layer_detection():
    """Test 2: Layer classification"""
    print("Test 2: Layer classification")
    arbiter = ArbiterAgent()

    test_cases = [
        ("Explain Axiom A1 about information ontology", Layer.L1),  # 2+ L1 keywords
        ("What is CMN in MSS?", Layer.L3),  # No exact L1 match, no L2 match
        ("How does BCT relate to black holes?", Layer.L2),  # L2 keyword
        ("Tell me about organizational resilience framework", Layer.L2),  # L2 keyword
        ("What is the meaning of life?", Layer.L3),  # No keywords
        ("Can MSS explain consciousness?", Layer.L3),  # No keywords
    ]

    passed = 0
    for query, expected in test_cases:
        result = arbiter.check(query)
        if result.layer == expected:
            print(f"  PASS: '{query[:40]}...' → {result.layer.value}")
            passed += 1
        else:
            print(f"  FAIL: '{query[:40]}...' → expected {expected.value}, got {result.layer.value}")

    print(f"Result: {passed}/{len(test_cases)} passed\n")
    return passed == len(test_cases)

def test_rsca_compliance():
    """Test 3: RSCA compliance check"""
    print("Test 3: RSCA compliance")
    arbiter = ArbiterAgent()

    test_cases = [
        ("fully understand consciousness", False),  # Violation: "fully understand"
        ("complete understanding of MSS", False),  # Violation: "complete understanding"
        ("How does MSS approach meaning?", True),  # No violation, compliant -> True
        ("What are the axioms?", True),  # No violation, compliant -> True
    ]

    passed = 0
    for query, expected_pass in test_cases:
        result = arbiter.check(query)
        rsca_pass = result.rsca_check

        if rsca_pass == expected_pass:
            print(f"  PASS: '{query[:40]}...' → RSCA {'PASS' if rsca_pass else 'FAIL'}")
            passed += 1
        else:
            print(f"  FAIL: '{query[:40]}...' → expected RSCA {'PASS' if expected_pass else 'FAIL'}")

    print(f"Result: {passed}/{len(test_cases)} passed\n")
    return passed == len(test_cases)

def test_tactic_orchestration():
    """Test 4: Full Tactic orchestration"""
    print("Test 4: Tactic orchestration flow")
    tactic = MSSTactic()

    # Test with forbidden word (should fail)
    result = tactic.call("solve the consciousness problem")

    checks = [
        ("success is False", not result["success"]),
        ("has arbiter_result", result["arbiter_result"] is not None),
        ("forbidden words detected", len(result["arbiter_result"].forbidden_words) > 0),
        ("response contains error", "Compliance Error" in result["response"]),
    ]

    passed = 0
    for desc, check in checks:
        if check:
            print(f"  PASS: {desc}")
            passed += 1
        else:
            print(f"  FAIL: {desc}")

    print(f"Result: {passed}/{len(checks)} passed\n")
    return passed == len(checks)

def test_dialog_forking():
    """Test 5: Dialog state forking"""
    print("Test 5: Dialog forking")
    from mss_tactic import Dialog

    dialog = Dialog()
    dialog.add("system", "You are MSS-AI")
    dialog.add("user", "Hello")

    # Fork
    forked = dialog.fork()
    forked.add("assistant", "Hi there")

    checks = [
        ("original has 2 messages", len(dialog.messages) == 2),
        ("forked has 3 messages", len(forked.messages) == 3),
        ("original unchanged", dialog.messages[-1]["content"] == "Hello"),
        ("fork has new message", forked.messages[-1]["content"] == "Hi there"),
    ]

    passed = 0
    for desc, check in checks:
        if check:
            print(f"  PASS: {desc}")
            passed += 1
        else:
            print(f"  FAIL: {desc}")

    print(f"Result: {passed}/{len(checks)} passed\n")
    return passed == len(checks)

def run_all_tests():
    """Run complete test suite"""
    print("="*60)
    print("MSS-Tactic v0.1 Test Suite")
    print("="*60 + "\n")

    tests = [
        test_arbiter_forbidden_detection,
        test_arbiter_layer_detection,
        test_rsca_compliance,
        test_tactic_orchestration,
        test_dialog_forking,
    ]

    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"ERROR in {test.__name__}: {e}\n")
            results.append(False)

    print("="*60)
    print(f"Final: {sum(results)}/{len(results)} test groups passed")
    print("="*60)

    return all(results)

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
