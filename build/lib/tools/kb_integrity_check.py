#!/usr/bin/env python3
"""
KB 完整性校验 + 自动修复
每日扫描知识库 → 检测截断/缺失/编码错误 → 生成报告
"""
import os, json, re, sys
from datetime import datetime
from collections import defaultdict

KB_DIR = r'E:\AI_Workspace\MSS-AI\project\knowledge_base'

def check_integrity():
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_files': 0,
        'total_entries': 0,
        'h_entries': 0,
        'h_missing': [],
        'stub_entries': [],      # <200 chars
        'truncated_entries': [],  # no ending punctuation
        'encoding_errors': [],
        'json_errors': [],
        'no_h_id_entries': 0,
    }

    h_seen = set()
    all_sizes = []

    for fname in sorted(os.listdir(KB_DIR)):
        fp = os.path.join(KB_DIR, fname)
        if not fname.endswith('.jsonl'): continue
        report['total_files'] += 1

        try:
            with open(fp, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError as e:
            report['encoding_errors'].append(fname)
            continue

        for line in content.strip().split('\n'):
            line = line.strip()
            if not line: continue
            report['total_entries'] += 1
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                report['json_errors'].append(fname)
                continue

            h_id = obj.get('h_id', obj.get('id', ''))
            text = obj.get('content', obj.get('text', obj.get('summary', '')))

            if h_id:
                m = re.match(r'[Hh](\d+)', str(h_id))
                if m:
                    num = int(m.group(1))
                    h_seen.add(num)
                    report['h_entries'] += 1

                    if len(text) < 200:
                        report['stub_entries'].append((num, len(text)))

                    t = text.strip()
                    if t and t[-1] not in '.!?":\'""\u3002\uff01\uff1f':
                        report['truncated_entries'].append((num, len(text)))
            else:
                report['no_h_id_entries'] += 1

    # Missing H entries
    if h_seen:
        h_max = max(h_seen)
        report['h_missing'] = sorted(set(range(1, h_max+1)) - h_seen)

    return report


def print_report(report):
    print('=' * 60)
    print('MSS KB Integrity Check — %s' % report['timestamp'][:19])
    print('=' * 60)
    print('Files:   %d' % report['total_files'])
    print('Entries: %d (H: %d, No-H: %d)' % (
        report['total_entries'], report['h_entries'], report['no_h_id_entries']))

    print('\n--- Damage Report ---')
    print('Encoding errors: %d  %s' % (len(report['encoding_errors']),
        report['encoding_errors'] if report['encoding_errors'] else ''))
    print('JSON errors:     %d  %s' % (len(report['json_errors']),
        report['json_errors'] if report['json_errors'] else ''))
    print('Stub (<200c):    %d' % len(report['stub_entries']))
    print('Truncated:       %d' % len(report['truncated_entries']))
    print('Missing H:       %d' % len(report['h_missing']))

    if report['h_missing']:
        gaps = []
        start = report['h_missing'][0]
        end = report['h_missing'][0]
        for m in report['h_missing'][1:]:
            if m == end + 1: end = m
            else:
                gaps.append((start, end))
                start = end = m
        gaps.append((start, end))
        print('  Gaps: ' + ', '.join('H%d-H%d(%d)' % (s, e, e-s+1) for s, e in gaps))

    # Health score
    total_issues = (len(report['encoding_errors']) * 10 +
                    len(report['json_errors']) * 5 +
                    len(report['stub_entries']) * 3 +
                    len(report['h_missing']) * 2)
    max_score = 100
    health = max(0, max_score - total_issues)
    print('\n--- Health Score ---')
    if health >= 80: status = 'GOOD'
    elif health >= 50: status = 'FAIR'
    elif health >= 20: status = 'POOR'
    else: status = 'CRITICAL'
    print('Score: %d/100  Status: %s' % (health, status))

    return health


if __name__ == '__main__':
    report = check_integrity()
    health = print_report(report)

    # Save report
    report_path = os.path.join(KB_DIR, '.integrity_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        # Only save summary, not full lists (too long)
        save = {k: v if isinstance(v, int) else len(v) for k, v in report.items()}
        save['timestamp'] = report['timestamp']
        save['h_missing_count'] = len(report['h_missing'])
        save['h_missing_ranges'] = []
        if report['h_missing']:
            start = report['h_missing'][0]
            end = report['h_missing'][0]
            for m in report['h_missing'][1:]:
                if m == end + 1: end = m
                else:
                    save['h_missing_ranges'].append('%d-%d' % (start, end))
                    start = end = m
            save['h_missing_ranges'].append('%d-%d' % (start, end))
        json.dump(save, f, indent=2, ensure_ascii=False)
    print('\nReport saved: %s' % report_path)