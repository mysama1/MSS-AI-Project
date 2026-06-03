# -*- coding: utf-8 -*-
"""
Integration Test Suite for MSS-Tactic v1.0
Tests analyze(), generate(), switch_model() with compliant responder
"""

import sys
import time
from mss_tactic_integrated import MSSTactic

def test_analyze():
    """Test analyze() method"""
    print("\n" + "="*60)
    print("TEST 1: analyze()")
    print("="*60)
    
    tactic = MSSTactic(check_gpu=False)
    
    test_cases = [
        ("MSS framework is the ultimate solution, can perfectly solve AI alignment", "L1", "Should detect forbidden words"),
        ("Explain Axiom A1 about information ontology", "L1", "Should detect L1 content"),
        ("What is the weather today?", "L3", "Should be L3 (no MSS content)"),
    ]
    
    passed = 0
    for text, claimed_layer, desc in test_cases:
        result = tactic.analyze(text, claimed_layer=claimed_layer)
        score = result.get('overall_score', 0)
        detected = result.get('layer', {}).get('detected', 'UNKNOWN')
        
        print(f"\n  Input: {text[:50]}...")
        print(f"  Claimed: {claimed_layer}, Detected: {detected}, Score: {score:.2f}")
        print(f"  Description: {desc}")
        
        if score > 0:
            passed += 1
            print("  [PASS]")
        else:
            print("  [FAIL]")
    
    print(f"\n  Result: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_generate():
    """Test generate() method"""
    print("\n" + "="*60)
    print("TEST 2: generate()")
    print("="*60)
    
    tactic = MSSTactic(check_gpu=False)
    
    test_cases = [
        "Explain Axiom A1 about information ontology",
        "What is organizational resilience framework?",
        "Solve the problem of consciousness",  # Should trigger rewrite or fail
    ]
    
    passed = 0
    for prompt in test_cases:
        print(f"\n  Input: {prompt}")
        
        try:
            result = tactic.generate(prompt)
            success = result.get('success', False)
            layer = result.get('arbiter_result', None)
            layer_str = layer.layer.value if layer else "UNKNOWN"
            response = result.get('response', '')[:100]
            
            print(f"  Success: {success}, Layer: {layer_str}")
            print(f"  Response: {response}...")
            
            # Check if response has markers
            has_markers = '[Confidence]' in response and '[Layer]' in response
            
            if success and has_markers:
                passed += 1
                print("  [PASS]")
            elif not success and "solve" in prompt.lower():
                passed += 1  # Expected to fail for forbidden words
                print("  [PASS] (Expected failure)")
            else:
                print("  [FAIL]")
                
        except Exception as e:
            print(f"  [ERROR: {e}]")
    
    print(f"\n  Result: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_switch_model():
    """Test switch_model() method"""
    print("\n" + "="*60)
    print("TEST 3: switch_model()")
    print("="*60)
    
    tactic = MSSTactic(check_gpu=False)
    
    models = ["qwen2.5:7b", "mss-ai-v3_5:latest"]
    
    passed = 0
    for model in models:
        print(f"\n  Switching to: {model}")
        
        try:
            result = tactic.switch_model(model)
            success = result.get('success', False)
            
            print(f"  Success: {success}")
            
            if success:
                passed += 1
                print("  [PASS]")
            else:
                print("  [FAIL]")
                
        except Exception as e:
            print(f"  [ERROR: {e}]")
    
    print(f"\n  Result: {passed}/{len(models)} passed")
    return passed == len(models)


def test_stats():
    """Test statistics tracking"""
    print("\n" + "="*60)
    print("TEST 4: Statistics")
    print("="*60)
    
    tactic = MSSTactic(check_gpu=False)
    
    # Run some operations
    tactic.analyze("Test input")
    tactic.switch_model("qwen2.5:7b")
    
    stats = tactic.get_stats()
    
    print(f"\n  Stats: {stats}")
    
    if stats['total_requests'] >= 0 and stats['model_switches'] >= 1:
        print("  [PASS]")
        return True
    else:
        print("  [FAIL]")
        return False


def main():
    """Run all tests"""
    print("MSS-Tactic v1.0 Integration Test Suite")
    print("="*60)
    
    start_time = time.time()
    
    results = []
    
    # Run tests
    results.append(("analyze()", test_analyze()))
    results.append(("generate()", test_generate()))
    results.append(("switch_model()", test_switch_model()))
    results.append(("stats()", test_stats()))
    
    # Summary
    elapsed = time.time() - start_time
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {name}: {status}")
    
    print(f"\n  Total: {passed}/{total} passed")
    print(f"  Time: {elapsed:.1f}s")
    
    if passed == total:
        print("\n  ALL TESTS PASSED!")
        return 0
    else:
        print("\n  SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
