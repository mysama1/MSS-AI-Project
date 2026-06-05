#!/usr/bin/env python3
"""
auto_archive.py v2.0 — FIX: 完整内容归档，不再截断
原版bug: 'summary': content[:400] → 只存前400字符
修复:    存完整 content + summary 两字段
"""
import json, os, glob, re, hashlib
from datetime import date

KB_DIR = r'E:\AI_Workspace\MSS-AI\project\knowledge_base'
FORMAL_DIR = r'E:\AI_Workspace\MSS-AI\project\formalization'

def safe_jsonl_value(text):
    """确保文本可以安全写入JSONL（单行，无换行符破坏）"""
    return json.dumps(text, ensure_ascii=False)

def next_h_id():
    existing = set()
    for fp in glob.glob(os.path.join(KB_DIR, 'h*.jsonl')):
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    try:
                        d = json.loads(line)
                        hid = d.get('h_id', '')
                        if hid.startswith('H'):
                            existing.add(int(hid[1:]))
                    except: pass
        except: pass
    return 'H%d' % (max(existing) + 1) if existing else 'H212'

def estimate_t_value(content, filename):
    score = 5
    if re.search(r'axiom|公理', content, re.I): score = 9
    elif re.search(r'theorem|定理|proof|证明', content, re.I): score = 8
    elif re.search(r'spec|规范|protocol|协议', content, re.I): score = 7
    elif re.search(r'guide|指导|tutorial', content, re.I): score = 6
    if re.search(r'v\d+\.\d+|version', content, re.I): score += 1
    if len(content) > 5000: score += 1
    return min(10, score)

def scan_and_archive(dry_run=False):
    md_files = sorted(glob.glob(os.path.join(FORMAL_DIR, '*.md')))
    new_count = 0

    for fp in md_files:
        basename = os.path.basename(fp)
        slug = basename.replace('.md', '').replace(' ', '_')

        with open(fp, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract title
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1)[:120] if title_match else basename.replace('.md', '')

        # Extract first 500 chars as preview summary
        summary = content[:500].replace('\n', ' ').replace('\r', '')

        # Generate content hash for dedup
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

        axioms = list(set(re.findall(r'\b(A[1-7])\b', content)))
        t_val = estimate_t_value(content, basename)
        h_id = next_h_id()

        entry = {
            'h_id': h_id,
            'title': title,
            'version': '2.0',
            'date': date.today().isoformat(),
            't_value': t_val,
            'category': 'auto_archived_formalization',
            'tags': ['auto-archived'],
            'axioms_referenced': axioms,
            'source_file': fp,
            'content_hash': content_hash,
            'summary': summary,
            'content': content,           # <<< FIXED: 完整内容
            'content_length': len(content),
        }

        out_name = '%s_%s_v2.0.jsonl' % (h_id.lower(), slug)
        out_path = os.path.join(KB_DIR, out_name)

        if dry_run:
            print('[DRY RUN] Would archive %s: %s (%d chars)' % (h_id, title[:60], len(content)))
        else:
            # Use json.dumps for safe single-line serialization
            line = json.dumps(entry, ensure_ascii=False)
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(line + '\n')
            print('Archived %s: %s -> %s (%d chars)' % (h_id, title[:60], out_name, len(content)))

        new_count += 1

    return new_count

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    n = scan_and_archive(dry_run=args.dry_run)
    print('\nDone. %d entries archived.' % n)