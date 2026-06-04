#!/usr/bin/env python3
"""D5-034: T-value Auto-Filter Tool v0.1.
Scores MSS content for T-value (tuning degree) based on keyword/axiom/protocol density."""
import json, os, re, glob

KB_DIR = r'E:\AI_Workspace\MSS-AI\project\knowledge_base'
FORMAL_DIR = r'E:\AI_Workspace\MSS-AI\project\formalization'

# T-value scoring weights
WEIGHTS = {
    'axiom_present': {'A1': 2, 'A2': 1, 'A3': 3, 'A4': 2, 'A5': 1, 'A6': 2},
    'keyword_high': [r'公理', r'axiom', r'定理', r'theorem', r'证明', r'proof',
                     r'形式化', r'formal', r'第一性原理', r'first.principle'],
    'keyword_mid': [r'协议', r'protocol', r'规范', r'spec', r'框架', r'framework',
                    r'架构', r'architecture', r'裁定', r'ruling'],
    'keyword_low': [r'指南', r'guide', r'教程', r'tutorial', r'FAQ', r'参考', r'reference'],
    'length_bonus': [(500, 1), (2000, 2), (10000, 3)],  # (chars, bonus)
    'version_bonus': [(r'v1[5-9]', 2), (r'v2[0-9]', 3)],  # newer versions get bonus
}


def score_t_value(content, filename=''):
    """Calculate T-value (1-10) for a piece of MSS content."""
    score = 5.0  # baseline

    # Axiom presence
    for ax, weight in WEIGHTS['axiom_present'].items():
        if ax in content:
            score += weight * 0.5

    # Keyword density
    high_count = sum(1 for pat in WEIGHTS['keyword_high'] if re.search(pat, content, re.I))
    mid_count = sum(1 for pat in WEIGHTS['keyword_mid'] if re.search(pat, content, re.I))
    low_count = sum(1 for pat in WEIGHTS['keyword_low'] if re.search(pat, content, re.I))
    score += high_count * 0.5 + mid_count * 0.3 + low_count * 0.1

    # Length bonus
    length = len(content)
    for threshold, bonus in WEIGHTS['length_bonus']:
        if length >= threshold:
            score += bonus

    # Version bonus
    for pat, bonus in WEIGHTS['version_bonus']:
        if re.search(pat, filename, re.I) or re.search(pat, content, re.I):
            score += bonus

    # Clamp
    return round(min(10, max(1, score)), 1)


def scan_directory(directory=KB_DIR, pattern='h*.jsonl'):
    """Scan all H entries and report T-values."""
    results = []
    for fp in glob.glob(os.path.join(directory, pattern)):
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                raw = f.read(5000)
        except:
            continue
        try:
            data = json.loads(raw.split('\n')[0])
        except:
            continue

        h_id = data.get('h_id', data.get('id', '?'))
        title = data.get('title', '?')[:60]
        existing_t = data.get('t_value', data.get('T', None))
        content = raw
        computed_t = score_t_value(content, os.path.basename(fp))
        results.append((h_id, title, existing_t, computed_t))

    results.sort(key=lambda x: x[3], reverse=True)
    return results


def print_report():
    """Generate T-value scan report."""
    print('=' * 60)
    print('MSS T-Value Auto-Filter v0.1 — Scan Report')
    print('=' * 60)
    print(f'{"H ID":<8} {"Computed T":>10} {"Existing T":>10} {"Title":.40}')
    print('-' * 60)

    results = scan_directory()
    for h_id, title, existing_t, computed_t in results:
        existing_str = str(existing_t) if existing_t else '?'
        print(f'{h_id:<8} {computed_t:>10.1f} {existing_str:>10} {title[:40]}')

    avg = sum(r[3] for r in results) / len(results) if results else 0
    print('-' * 60)
    print(f'Total: {len(results)} entries | Avg T-value: {avg:.1f}')


if __name__ == '__main__':
    print_report()
