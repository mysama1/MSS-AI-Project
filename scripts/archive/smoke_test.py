#!/usr/bin/env python3
"""
MSS-VDP 全系统自检 (Smoke Test) v2.1
Usage: py -3.11 smoke_test.py [--iterations N] [--json]
"""
import sys, os, json, subprocess, re, argparse, time
from datetime import datetime
from collections import defaultdict

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))

def run(*args, timeout=30):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True,
                          timeout=timeout, encoding='utf-8', errors='replace',
                          cwd=SKILL_DIR)

def run_scanner(name, target, *extra):
    cmd = [name, target] + list(extra)
    r = run(*cmd)
    try:
        d = json.loads(r.stdout) if r.stdout.strip() else {}
    except:
        d = {}
    items = d if isinstance(d, list) else [d]
    violations = sum(len(item.get('violations', [])) for item in items)
    rejects = sum(1 for item in items if item.get('verdict') == 'reject')
    return {'ok': r.returncode in (0, 1, 2), 'rc': r.returncode,
            'violations': violations, 'rejects': rejects, 'files': len(items)}

def run_one_iteration():
    """Returns list of (test_name, passed, violations) tuples."""
    results = []
    
    # 1. Python
    r = run_scanner('vdp_scan.py', 'smoke_test.py', '--format', 'json')
    results.append(('python', r['ok'], r['violations']))
    
    # 2. JS
    r = run_scanner('js_scan.py', 'test_v2.js', '--json')
    results.append(('javascript', r['ok'], r['violations']))
    
    # 3. Rust
    r = run_scanner('rust_scan.py', 'test_rust.rs', '--json')
    results.append(('rust', r['ok'], r['violations']))
    
    # 4. Java/C++
    r = run_scanner('java_cpp_scan.py', 'test_java.java', '--json')
    results.append(('java_cpp', r['ok'] and r['violations'] >= 1, r['violations']))
    
    # 5. Go
    r = run_scanner('go_scan.py', 'test_go.go', '--json')
    results.append(('go', r['ok'] and r['violations'] >= 3, r['violations']))
    
    # 6. Ruby
    r = run_scanner('ruby_scan.py', 'test_ruby.rb', '--json')
    results.append(('ruby', r['ok'] and r['violations'] >= 2, r['violations']))
    
    # 7. PHP
    r = run_scanner('php_scan.py', 'test_php.php', '--json')
    results.append(('php', r['ok'] and r['violations'] >= 3, r['violations']))
    
    # 8. Kotlin
    r = run_scanner('kotlin_scan.py', 'test_kotlin.kt', '--json')
    results.append(('kotlin', r['ok'] and r['violations'] >= 1, r['violations']))
    
    # 9. C#
    r = run_scanner('csharp_scan.py', 'test_csharp.cs', '--json')
    results.append(('csharp', r['ok'] and r['violations'] >= 3, r['violations']))
    
    # 10. PS detect
    r2 = run('ps_verify.py', 'detect', 'test_ps_bad.ps1', '--json')
    try:
        d = json.loads(r2.stdout)
        v = d.get('count', len(d.get('violations', []))) if isinstance(d, dict) else 0
    except:
        v = 0
    results.append(('ps_detect', r2.returncode == 0 and v >= 3, v))
    
    # 11. PS check
    r2 = run('ps_verify.py', 'check', '--json')
    try: d = json.loads(r2.stdout)
    except: d = {}
    results.append(('ps_check', d.get('verdict') == 'pass', 0))
    
    # 12. DSL
    r = run_scanner('vdp_dsl.py', 'test_dsl.js', '--json')
    results.append(('dsl', r['ok'] and r['violations'] >= 3, r['violations']))
    
    # 13. Lock profiler
    try:
        __import__('lock_profiler')
        ok = True
    except:
        ok = False
    results.append(('lock_profiler', ok, 0))
    
    # 14. Memory profiler
    try:
        __import__('memory_profiler')
        ok = True
    except:
        ok = False
    results.append(('memory_profiler', ok, 0))
    
    # 15. Golden Judge
    r2 = run('ps_judge.py', '--demo')
    m = re.findall(r'Average:\s+([\d.]+)/100', r2.stdout)
    score = float(m[1]) if len(m) >= 2 else 0
    results.append(('golden_ps', score >= 90, 0))
    
    # 16. iOS rules
    r2 = run('ios_verify.py', 'rules')
    results.append(('ios_rules', r2.returncode == 0 and 'A7' in r2.stdout, 0))
    
    # 17. LLM Bench
    r2 = run('llm_bench.py', '--demo')
    m = re.findall(r'(\d+\.\d+)/100', r2.stdout)
    score = float(m[1]) if len(m) >= 2 else 0
    results.append(('llm_bench', score >= 50, 0))
    
    # 18. Org Resilience
    r2 = run('org_resilience.py', '--demo', '--json')
    try: d = json.loads(r2.stdout); ok = d.get('global', {}).get('M', 0) > 0
    except: ok = False
    results.append(('org_resilience', ok, 0))
    
    # 19. Content Compliance
    r2 = run('content_compliance.py', '--rules')
    results.append(('content_comply', r2.returncode == 0 and 'C1_CLAIM' in r2.stdout, 0))
    
    return results

def main():
    ap = argparse.ArgumentParser(description='MSS-VDP Smoke Test')
    ap.add_argument('--iterations', '-n', type=int, default=1, help='Iterations (default 1)')
    ap.add_argument('--json', action='store_true', help='JSON output')
    args = ap.parse_args()
    
    if not args.json:
        print("=" * 60)
        print("MSS-VDP 全系统自检 v2.1")
        print("Iterations: %d | Time: %s" % (args.iterations, datetime.now().isoformat()))
        print("=" * 60)
    
    all_results = defaultdict(list)
    total_ok_iterations = 0
    t0 = time.time()
    
    for i in range(args.iterations):
        results = run_one_iteration()
        all_pass = all(p for _, p, _ in results)
        if all_pass:
            total_ok_iterations += 1
        
        for name, passed, violations in results:
            all_results[name].append(passed)
        
        if args.iterations > 1 and not args.json:
            pct = (i + 1) * 100 // args.iterations
            print("\r  Progress: %d/%d (%d%%)" % (i + 1, args.iterations, pct), end='', flush=True)
    
    elapsed = time.time() - t0
    
    if args.json:
        summary = {name: {'pass': sum(v), 'total': len(v), 'rate': sum(v)/len(v)}
                   for name, v in all_results.items()}
        print(json.dumps({
            'iterations': args.iterations,
            'elapsed_s': round(elapsed, 1),
            'perfect_iterations': total_ok_iterations,
            'tests': summary,
        }, ensure_ascii=False, indent=2))
        return
    
    print("\n\n" + "=" * 60)
    headers = ('Test', 'Pass/Total', 'Rate', 'Status')
    print("%-20s %12s %8s %8s" % headers)
    print("-" * 60)
    
    total_pass = 0
    total_tests = 0
    for name, passes in sorted(all_results.items()):
        n = len(passes)
        p = sum(passes)
        rate = p / n
        total_pass += p
        total_tests += n
        
        if rate == 1.0:
            status = 'STABLE'
        elif rate >= 0.95:
            status = 'FLAKY'
        else:
            status = 'BROKEN'
        print("%-20s %6d/%-3d %7.0f%% %8s" % (name, p, n, rate * 100, status))
    
    print("-" * 60)
    overall_rate = total_pass / total_tests
    print("%-20s %6d/%-3d %7.0f%%" % ("TOTAL", total_pass, total_tests, overall_rate * 100))
    print("Perfect iterations: %d/%d (%.0f%%)" % (total_ok_iterations, args.iterations, total_ok_iterations/args.iterations*100))
    print("Elapsed: %.1fs" % elapsed)
    print("=" * 60)
    
    # Save report
    report_dir = os.path.join(SKILL_DIR, '.run')
    os.makedirs(report_dir, exist_ok=True)
    report = {
        'timestamp': datetime.now().isoformat(),
        'iterations': args.iterations,
        'elapsed_s': round(elapsed, 1),
        'pass': total_pass,
        'fail': total_tests - total_pass,
        'total': total_tests,
        'overall_rate': round(overall_rate, 4),
        'perfect_iterations': total_ok_iterations,
        'per_test': {name: {'pass': sum(v), 'total': len(v), 'rate': round(sum(v)/len(v), 4)}
                     for name, v in all_results.items()},
    }
    json.dump(report, open(os.path.join(report_dir, 'smoke_test_report.json'), 'w'),
              ensure_ascii=False, indent=2)
    print("Report: %s" % os.path.join(report_dir, 'smoke_test_report.json'))
    
    sys.exit(0 if total_pass == total_tests else 1)

if __name__ == '__main__':
    main()
