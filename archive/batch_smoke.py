#!/usr/bin/env python3
"""Run smoke_test in batches and merge results."""
import json, os, subprocess, sys, glob

cwd = os.path.dirname(os.path.abspath(__file__))
batches = [20, 20, 20, 20, 10]  # 90 more = 100 total
all_json = []

for b in batches:
    print('Running batch of %d iterations...' % b)
    r = subprocess.run([sys.executable, 'smoke_test.py', '-n', str(b), '--json'],
                       capture_output=True, text=True, timeout=300, cwd=cwd,
                       encoding='utf-8', errors='replace')
    d = json.loads(r.stdout)
    all_json.append(d)
    pp = d['tests']['python']['pass']
    print('  python: %d/%d, total elapsed: %.1fs' % (pp, d['iterations'], d['elapsed_s']))

# Merge
merged = {
    'iterations': sum(d['iterations'] for d in all_json),
    'elapsed_s': sum(d['elapsed_s'] for d in all_json),
}
tests = {}
for d in all_json:
    for name, stats in d['tests'].items():
        if name not in tests:
            tests[name] = {'pass': 0, 'total': 0}
        tests[name]['pass'] += stats['pass']
        tests[name]['total'] += stats['total']

for name, stats in tests.items():
    stats['rate'] = round(stats['pass'] / stats['total'], 4)

total_p = sum(s['pass'] for s in tests.values())
total_t = sum(s['total'] for s in tests.values())
merged['tests'] = tests
merged['overall_rate'] = round(total_p / total_t, 4)

print()
print('=' * 60)
print('SMOKE TEST 100 SUMMARY')
print('Total: %d/%d (%.0f%%) | Elapsed: %.1fs' % (total_p, total_t, merged['overall_rate'] * 100, merged['elapsed_s']))
print('=' * 60)
for name, stats in sorted(tests.items()):
    if stats['rate'] == 1.0:
        status = 'STABLE'
    elif stats['rate'] >= 0.95:
        status = 'FLAKY'
    else:
        status = 'BROKEN'
    print('  %-20s %3d/%-3d %5.0f%%  %s' % (name, stats['pass'], stats['total'], stats['rate'] * 100, status))

os.makedirs(os.path.join(cwd, '.run'), exist_ok=True)
report_path = os.path.join(cwd, '.run', 'smoke_test_100_report.json')
json.dump(merged, open(report_path, 'w'), ensure_ascii=False, indent=2)
print('\nReport saved: %s' % report_path)
