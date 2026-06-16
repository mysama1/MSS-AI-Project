#!/usr/bin/env python3
"""
mss — MSS-AI v15.2 Unified CLI

Usage:
  mss status         Dashboard overview
  mss verify         Full 8-check integrity
  mss audit          Daily health audit
  mss scan <path>    VDP precommit scan
  mss cache [--clean] [--fresh]  Module cache detection. Default: fresh_scan (subprocess isolation)
  mss kb search <q>  Knowledge base query
  mss kb quality     KB metadata health
  mss link           External link validator
  mss paper          Paper status
"""
import subprocess, sys, os

VDP_DIR = r'E:\QClaw-Data\skills\mss-vdp'
PROJECT = r'E:\AI_Workspace\MSS-AI\project'

COMMANDS = {
    'status':  ['python', f'{VDP_DIR}\\status.py'],
    'verify':  ['python', f'{VDP_DIR}\\verify_all.py'],
    'audit':   ['python', f'{VDP_DIR}\\daily_audit.py'],
    'cache':   ['python', f'{VDP_DIR}\\module_cache_detector.py',
                '--project', r'E:\QClaw-Data\skills', r'E:\AI_Workspace\MSS-AI'],
    'link':    ['python', f'{VDP_DIR}\\link_validator.py'],
    'quality': ['python', f'{VDP_DIR}\\kb_quality.py'],
    'paper':   ['python', '-c',
        "print('DOI: 10.5281/zenodo.20537026');print('ORCID: 0009-0008-2550-130X');print('v0.5 honesty version');print('a<=68 closed, a>=69 open')"],
}

def run(cmd, cwd=None, extra_args=None):
    final = cmd + (extra_args or [])
    return subprocess.run(final, cwd=cwd or PROJECT)

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    cmd = args[0]

    if cmd == 'scan':
        path = args[1] if len(args) > 1 else '.'
        run(['python', f'{VDP_DIR}\\vdp_precommit.py', 'check', path],
            extra_args=args[2:])
    elif cmd == 'cache':
        extra = ['--clean'] if '--clean' in args else []
        run(COMMANDS['cache'], extra_args=extra)
    elif cmd == 'kb':
        sub = args[1] if len(args) > 1 else 'search'
        if sub == 'search' and len(args) > 2:
            import urllib.request, json
            q = ' '.join(args[2:])
            url = f'http://localhost:53000/kb/search?q={q}'
            r = urllib.request.urlopen(url)
            data = json.loads(r.read())
            for item in data.get('results', [])[:10]:
                print(f"  {item.get('id','?')}: {item.get('title','')[:80]}")
        elif sub == 'quality':
            run(COMMANDS['quality'])
        else:
            print(f"mss kb: unknown subcommand '{sub}'")
    elif cmd in COMMANDS:
        run(COMMANDS[cmd], extra_args=args[1:])
    else:
        print(f"mss: unknown command '{cmd}'")
        print("Available: status verify audit scan cache kb link paper quality")

if __name__ == '__main__':
    main()
