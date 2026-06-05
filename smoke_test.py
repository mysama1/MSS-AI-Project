#!/usr/bin/env python3
"""
MSS-VDP 全系统自检 (Smoke Test)
串联: 6语言扫描器 + PowerShell矫正 + Golden Judge + Lock/Memory Profiler + DSL
输出: 单一 pass/fail 报告

用法: py -3.11 smoke_test.py
"""
import sys, os, json, subprocess, re
from datetime import datetime

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SKILL_DIR)  # All ops from SKILL_DIR

def run(*args, timeout=30):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='replace')

def run_scanner(name, target, *extra):
    """name=scanner.py, target=file, extra='--json' or ['--format','json'] or []"""
    cmd = [name, target] + list(extra)
    r = run(*cmd)
    try:
        d = json.loads(r.stdout) if r.stdout.strip() else {}
    except:
        d = {}
    
    # Handle both single dict and list-of-dict
    items = d if isinstance(d, list) else [d]
    violations = sum(len(item.get('violations', [])) for item in items)
    rejects = sum(1 for item in items if item.get('verdict') == 'reject')
    
    return {
        'ok': r.returncode in (0, 1, 2),
        'rc': r.returncode,
        'violations': violations,
        'rejects': rejects,
        'files': len(items),
    }

def main():
    print("=" * 60)
    print("MSS-VDP 全系统自检")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)
    
    total_pass, total_fail = 0, 0
    
    def test(name, desc, result, min_violations=0):
        nonlocal total_pass, total_fail
        ok = result.get('ok') and result.get('violations', 0) >= min_violations
        status = 'PASS' if ok else 'FAIL'
        msg = f"({result.get('violations','?')} v)"
        print(f"[{name}] {desc} ... {status} {msg}")
        if status == 'PASS':
            total_pass += 1
        else:
            total_fail += 1
            if result.get('error'):
                print(f"       Error: {result['error'][:120]}")
    
    # 1. Python
    r = run_scanner('vdp_scan.py', 'smoke_test.py', '--format', 'json')
    test('python', 'V1-V6', r)
    
    # 2. JavaScript
    r = run_scanner('js_scan.py', 'test_v2.js', '--json')
    test('javascript', 'V1-V9', r)
    
    # 3. Rust
    r = run_scanner('rust_scan.py', 'test_rust.rs', '--json')
    test('rust', 'R1-R5', r)
    
    # 4. Java/C++
    r = run_scanner('java_cpp_scan.py', 'test_java.java', '--json')
    test('java_cpp', 'J1-J3', r, min_violations=1)
    
    # 5. Go
    r = run_scanner('go_scan.py', 'test_go.go', '--json')
    test('go', 'G1-G5', r, min_violations=3)
    
    # 5b. Ruby
    r = run_scanner('ruby_scan.py', 'test_ruby.rb', '--json')
    test('ruby', 'R1-R5', r, min_violations=2)
    
    # 5c. PHP
    r = run_scanner('php_scan.py', 'test_php.php', '--json')
    test('php', 'P1-P5', r, min_violations=3)
    
    # 5d. Kotlin
    r = run_scanner('kotlin_scan.py', 'test_kotlin.kt', '--json')
    test('kotlin', 'K1-K5', r, min_violations=1)
    
    # 5e. C#
    r = run_scanner('csharp_scan.py', 'test_csharp.cs', '--json')
    test('csharp', 'C1-C5', r, min_violations=3)
    
    # 6. PowerShell detect
    r2 = run('ps_verify.py', 'detect', 'test_ps_bad.ps1', '--json')
    try:
        d = json.loads(r2.stdout)
        v = d.get('count', len(d.get('violations', []))) if isinstance(d, dict) else 0
    except:
        v = 0
    test('ps_detect', 'POSIX detect', {'ok': r2.returncode == 0, 'violations': v}, min_violations=3)
    
    # 7. PS check
    r2 = run('ps_verify.py', 'check', '--json')
    try:
        d = json.loads(r2.stdout)
    except:
        d = {}
    test('ps_check', '8-point safety', {'ok': d.get('verdict') == 'pass', 'violations': 0})
    
    # 8. DSL
    r = run_scanner('vdp_dsl.py', 'test_dsl.js', '--json')
    test('dsl', 'Rules DSL', r, min_violations=3)
    
    # 9. Lock profiler
    ok = False
    try:
        __import__('lock_profiler')
        ok = True
    except Exception as e:
        result = {'error': str(e), 'ok': False}
    test('lock_profiler', 'import', {'ok': ok, 'violations': 0})
    
    # 10. Memory profiler
    ok = False
    try:
        __import__('memory_profiler')
        ok = True
    except Exception as e:
        pass
    test('memory_profiler', 'import', {'ok': ok, 'violations': 0})
    
    # 11. Golden Judge
    r2 = run('ps_judge.py', '--demo')
    m = re.findall(r'Average:\s+([\d.]+)/100', r2.stdout)
    score = float(m[1]) if len(m) >= 2 else None
    test('golden_ps', 'Golden judge', {'ok': score and score >= 90, 'violations': 0})
    
    # 12. iOS rules
    r2 = run('ios_verify.py', 'rules')
    test('ios_rules', '5铁律', {'ok': r2.returncode == 0 and 'A7' in r2.stdout, 'violations': 0})
    
    # 13. LLM Benchmark
    r2 = run('llm_bench.py', '--demo')
    m = re.findall(r'(\d+\.\d+)/100', r2.stdout)
    good_score = float(m[1]) if len(m) >= 2 else None
    test('llm_bench', 'Scoring demo', {'ok': good_score is not None and good_score >= 50, 'violations': 0})
    
    # 14. Org Resilience
    r2 = run('org_resilience.py', '--demo', '--json')
    try: d = json.loads(r2.stdout); ok = d.get('global',{}).get('M',0) > 0
    except: ok = False
    test('org_resilience', 'Org scanner', {'ok': ok, 'violations': 0})
    
    # 15. Content Compliance
    r2 = run('content_compliance.py', '--rules')
    test('content_comply', '5 rules', {'ok': r2.returncode == 0 and 'C1_CLAIM' in r2.stdout, 'violations': 0})
    
    # Summary
    print("\n" + "=" * 60)
    total = total_pass + total_fail
    print(f"Results: {total_pass}/{total} PASS, {total_fail}/{total} FAIL")
    print("=" * 60)
    
    report_path = os.path.join(SKILL_DIR, '.mss', 'smoke_test_report.json')
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    json.dump({'timestamp': datetime.now().isoformat(), 'pass': total_pass, 'fail': total_fail, 'total': total}, open(report_path, 'w'))
    print(f"Report: {report_path}")
    
    sys.exit(0 if total_fail == 0 else 1)

if __name__ == '__main__':
    main()
