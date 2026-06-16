#!/usr/bin/env python3
"""MSS Status Dashboard — one command to see everything."""
import os, json, subprocess, datetime, sys

def get_git_head(root):
    try:
        r = subprocess.run(['git','log','-1','--format=%h %s'], cwd=root,
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=5)
        return r.stdout.strip()[:80] if r.returncode == 0 else 'N/A'
    except: return 'N/A'

def get_kb_count(kb_dir):
    try:
        return sum(1 for f in os.listdir(kb_dir) if f.endswith('.jsonl'))
    except: return '?'

def get_models():
    try:
        r = subprocess.run(['ollama','list'], capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=5)
        mss_models = [l.split()[0] for l in r.stdout.split('\n') if 'mss-ai' in l]
        # Sort by version: extract vN_N, prefer production suffix
        def sort_key(name):
            import re
            nums = re.findall(r'v?(\d+)[._](\d+)', name)
            if nums:
                major, minor = int(nums[0][0]), int(nums[0][1])
                is_prod = 1 if 'production' in name else 0
                return (is_prod, major, minor)
            return (0, 0, 0)
        mss_models.sort(key=sort_key)
        return mss_models[-1] if mss_models else 'N/A'
    except: return 'N/A'

def get_api_health():
    try:
        import urllib.request
        r = urllib.request.urlopen('http://localhost:53000/vdp/vaccine', timeout=3)
        return 'OK' if r.status == 200 else f'{r.status}'
    except: return 'DOWN'

def main():
    root = r'E:\AI_Workspace\MSS-AI\project'
    kb = os.path.join(root, 'knowledge_base')
    now = datetime.datetime.now()

    print(f'{"="*50}')
    print(f'  MSS Status Dashboard — {now.strftime("%Y-%m-%d %H:%M")}')
    print(f'{"="*50}')

    items = [
        ('KB Entries',    f'{get_kb_count(kb)}'),
        ('Git HEAD',      get_git_head(root)),
        ('API (53000)',   get_api_health()),
        ('Model',         get_models()),
        ('Benchmark',     'v3.4 = 0.72 L4 (21-round LLM Judge)'),
        ('Cross-model',   'v3.4=0.72 v3.7=0.72 v3.6=0.54'),
        ('Paper',         'v0.5 (DOI:10.5281/zenodo.20537026)'),
        ('ORCID',         '0009-0008-2550-130X'),
    ]

    for k, v in items:
        print(f'  {k:<15} {v}')

    print()
    print('  Quick commands:')
    print('    verify_all.py          — full integrity check')
    print('    daily_audit.py         — health audit')
    print('    link_validator.py      — external link check')
    print('    ollama run mss-ai-v3_4-production  — chat with MSS-AI')

if __name__ == '__main__':
    main()
