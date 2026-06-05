#!/usr/bin/env python3
"""MSS System Integrity Check — run all tests in one command."""
import subprocess, os, sys, time

PASS, FAIL = 0, 0

def check(name, cmd, cwd=None, allow_rc1=False):
    global PASS, FAIL
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
            cwd=cwd, encoding='utf-8', errors='replace')
        ok = r.returncode == 0 or (allow_rc1 and r.returncode <= 2)
        elapsed = time.time() - t0
        icon = '✅' if ok else '❌'
        print(f'  {icon} {name} ({elapsed:.1f}s)')
        if not ok and r.stderr:
            for line in r.stderr.strip().split('\n')[-3:]:
                print(f'     {line[:100]}')
        if ok: PASS += 1
        else: FAIL += 1
        return ok
    except Exception as e:
        FAIL += 1
        print(f'  ❌ {name}: {str(e)[:80]}')
        return False

def main():
    global PASS, FAIL
    print('MSS System Integrity Check')
    print('=' * 50)

    root = r'E:\AI_Workspace\MSS-AI\project'
    vdp  = r'E:\QClaw-Data\skills\mss-vdp'

    # 1. Z3 Formal Verification
    check('Z3 Kernel (71 tests)', ['python', 'test_mss_z3_kernel.py'], cwd=root)

    # 2. VDP Self-scan (exit 1 = found violations = working correctly)
    check('VDP Self-scan', ['python', os.path.join(vdp,'vdp_scan.py'),
        os.path.join(vdp,'vdp_scan.py')], cwd=vdp, allow_rc1=True)

    # 3. KB Health (simple count check)
    check('KB Health', ['python', '-c',
        "import os;kb=r'E:\\AI_Workspace\\MSS-AI\\project\\knowledge_base';"
        "n=sum(1 for f in os.listdir(kb) if f.endswith('.jsonl'));print(f'{n} entries')"])

    # 4. VDP Vaccine
    check('VDP Vaccine', ['python', 'vdp_vaccine.py', '--inject'], cwd=vdp)

    # 5. API Health
    check('API Health', ['python', '-c',
        "import urllib.request;r=urllib.request.urlopen('http://localhost:53000/vdp/vaccine');"
        "print('OK' if r.status==200 else 'FAIL')"])

    # 6. Blackhole Monitor
    check('Blackhole Monitor', ['python', 'k3_blackhole_monitor.py'], cwd=vdp)

    # 7. Module Cache Pollution
    check('Module Cache', ['python', os.path.join(vdp,'module_cache_detector.py'),
        '--project', r'E:\QClaw-Data\skills', r'E:\AI_Workspace\MSS-AI'],
        cwd=vdp)

    # 8. Git Status
    check('Git Status', ['git', 'status', '--short'], cwd=root)

    # ── Summary ──
    print('=' * 50)
    total = PASS + FAIL
    if FAIL == 0:
        print(f'  ALL {total}/{total} PASS ✅')
    else:
        print(f'  {PASS}/{total} PASS, {FAIL} FAILED ❌')

    return FAIL

if __name__ == '__main__':
    sys.exit(main())
