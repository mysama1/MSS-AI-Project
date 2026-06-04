"""
MSS-AI Master Test Runner
Runs all test suites and generates combined report
"""

import sys
import time
import subprocess
from typing import List, Tuple


TEST_SUITES = [
    ("Symbolic Engine", "test_symbolic_engine.py"),
    ("Auto Analyzer", "test_auto_analyzer.py"),
    ("Post-Process Engine", "test_post_process_engine.py"),
    ("Integration Comprehensive", "test_integration_comprehensive.py"),
    ("Symbolic Rules Omega", "test_symbolic_rules_omega.py"),
    ("Symbolic Engine V2", "test_symbolic_v2.py"),
    ("Stability Monitor", "test_stability.py"),
    ("Hybrid Reasoning", "test_hybrid_reasoning.py"),
    ("Topology Propagation", "test_topology_propagation.py"),
    ("Omega Integration", "test_omega_integration.py"),
    ("Topology Metrics", "test_topology_metrics.py"),
    ("Post-Process Engine V3", "test_post_process_v3.py"),
    ("KB Loader", "test_kb_loader.py"),
    ("Symbolic Engine V3", "test_symbolic_engine_v3.py"),
    ("NL Bridge", "test_nl_bridge.py"),
    ("Organizational Resilience", "test_organizational_resilience.py"),
    ("V3 Integration", "test_v3_integration.py"),
    ("NL Bridge V2", "test_nl_bridge_v2.py"),
    ("Anti-Distillation", "test_anti_distillation.py"),
    ("He Guang Tong Chen", "test_heguang_tongchen.py"),
    ("Interactive CLI", "test_interactive_cli.py"),
    ("Web API", "test_web_api.py"),
    ("Simulation Framework", "test_simulation_framework.py"),
    ("Visualization Engine", "test_visualization_engine.py"),
    ("Numba Simulation", "test_simulation_numba.py"),
    ("WebSocket Server", "test_websocket_server.py"),
]


def run_suite(name: str, script: str) -> Tuple[bool, float, str]:
    """Run a single test suite. Returns (success, duration_seconds, output)"""
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True,
            text=True,
            timeout=120,
            encoding='utf-8',
            errors='replace'
        )
        duration = time.time() - start
        output = result.stdout + (result.stderr if result.stderr else "")
        
        # Parse results from output to determine true success
        passed, failed = parse_results(output)
        success = (failed == 0) and (passed > 0)
        
        return success, duration, output
    except subprocess.TimeoutExpired:
        return False, time.time() - start, "TIMEOUT"
    except Exception as e:
        return False, 0, str(e)


def parse_results(output: str) -> Tuple[int, int]:
    """Parse passed/failed counts from test output"""
    passed = 0
    failed = 0
    output_lower = output.lower()
    
    for line in output.split('\n'):
        line_lower = line.lower()
        # Match patterns like:
        # "Results: 6 passed, 0 failed"
        # "Results: 10 passed, 0 failed out of 10 tests"
        if 'results:' in line_lower and 'passed' in line_lower and 'failed' in line_lower:
            try:
                import re
                match = re.search(r'(\d+)\s+passed.*?[,\s]+(\d+)\s+failed', line_lower)
                if match:
                    passed = int(match.group(1))
                    failed = int(match.group(2))
                    return passed, failed
            except (ValueError, AttributeError):
                pass
    
    # Match unittest format: "Ran 24 tests in 0.005s" + "OK" or "FAILED"
    # Search in full output, not per-line
    import re
    ran_match = re.search(r'ran\s+(\d+)\s+tests?', output_lower)
    if ran_match:
        total = int(ran_match.group(1))
        # Check for OK (can appear before or after "Ran X tests")
        if 'ok' in output_lower:
            passed = total
            failed = 0
        elif 'failed' in output_lower or 'failures' in output_lower or 'errors' in output_lower:
            # Extract failed count from "FAILED (failures=X, errors=Y)" or "FAILED (failures=X)"
            fail_match = re.search(r'failures?[=\s:]+(\d+)', output_lower)
            error_match = re.search(r'errors?[=\s:]+(\d+)', output_lower)
            failed_count = int(fail_match.group(1)) if fail_match else 0
            error_count = int(error_match.group(1)) if error_match else 0
            failed = failed_count + error_count
            passed = total - failed
        else:
            passed = total
        return passed, failed
    
    # Match pytest-style: "X passed in Ys" or "X failed in Ys"
    pytest_match = re.search(r'(\d+)\s+passed', output_lower)
    if pytest_match:
        passed = int(pytest_match.group(1))
        pytest_failed = re.search(r'(\d+)\s+failed', output_lower)
        if pytest_failed:
            failed = int(pytest_failed.group(1))
        return passed, failed
    
    return passed, failed


def main():
    print("=" * 70)
    print("MSS-AI Master Test Runner")
    print("=" * 70)
    print()
    
    total_suites = 0
    passed_suites = 0
    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_time = 0
    
    results = []
    
    for name, script in TEST_SUITES:
        print(f"Running: {name}...")
        success, duration, output = run_suite(name, script)
        
        passed, failed = parse_results(output)
        total_tests += passed + failed
        total_passed += passed
        total_failed += failed
        total_time += duration
        total_suites += 1
        
        if success:
            passed_suites += 1
            status = "PASS"
        else:
            status = "FAIL"
        
        results.append({
            "name": name,
            "status": status,
            "duration": duration,
            "passed": passed,
            "failed": failed,
            "output": output
        })
        
        print(f"  Status: {status} | Tests: {passed}/{passed+failed} | Time: {duration:.2f}s")
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    
    for r in results:
        icon = "OK" if r["status"] == "PASS" else "XX"
        print(f"  [{icon}] {r['name']:<30} {r['passed']:>3}/{r['passed']+r['failed']:<3} tests  {r['duration']:>6.2f}s")
    
    print()
    print(f"  Suites: {passed_suites}/{total_suites} passed")
    print(f"  Tests:  {total_passed}/{total_tests} passed")
    print(f"  Time:   {total_time:.2f}s total")
    print()
    
    if total_failed > 0:
        print("=" * 70)
        print("FAILED TEST DETAILS")
        print("=" * 70)
        for r in results:
            if r["status"] == "FAIL":
                print(f"\n--- {r['name']} ---")
                # Show last 30 lines of output
                lines = r["output"].split('\n')
                for line in lines[-30:]:
                    print(line)
    
    print()
    print("=" * 70)
    if passed_suites == total_suites and total_failed == 0:
        print("ALL TESTS PASSED")
    else:
        print(f"FAILED: {total_failed} tests in {total_suites - passed_suites} suites")
    print("=" * 70)
    
    return total_failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
