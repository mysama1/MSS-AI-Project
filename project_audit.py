#!/usr/bin/env python3
"""MSS-AI Project Health Audit"""

import os, json, subprocess, datetime, urllib.request, shutil

print('=' * 60)
print('MSS-AI v18.11.0  Project Health Audit')
print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
print('=' * 60)

# 1. KB
kb_dir = r'E:\AI_Workspace\MSS-AI\project\knowledge_base'
entries = [f for f in os.listdir(kb_dir) if f.endswith('.jsonl')]
h_ids = set()
id_nums = []
for f in entries:
    if f.startswith('h'):
        # Strip prefix 'h'/'H', then extract leading digits
        base = f[1:]  # remove 'h'
        num = ''
        for ch in base:
            if ch.isdigit():
                num += ch
            else:
                break
        if num:
            h_ids.add('H' + num)
            id_nums.append(int(num))
h_ids = sorted(h_ids)
id_nums.sort()
gaps = []
for i in range(min(id_nums), max(id_nums)+1):
    if i not in id_nums:
        gaps.append(i)

print('\n[KB] %d entries, %d unique H-IDs' % (len(entries), len(h_ids)))
print('  Range: H%d - H%d' % (min(id_nums), max(id_nums)))
if gaps:
    print('  Gaps: H%s' % ', H'.join(str(g) for g in gaps))
else:
    print('  Gaps: NONE (continuous)')

# 2. VDP tools
vdp_dir = r'E:\QClaw-Data\skills\mss-vdp'
all_files = os.listdir(vdp_dir)
# 2. VDP tools (exclude node_modules)
tools = [f for f in all_files if f.endswith('.py') and not f.startswith('__') and not f.startswith('test_')]
# Filter: only actual VDP tools, not build scripts or node_modules support
tools = [t for t in tools if 'package' not in t.lower() and 'setup' not in t.lower()]
mds = [f for f in all_files if f.endswith('.md')]

total_py = sum(os.path.getsize(os.path.join(vdp_dir, t)) for t in tools)
print('\n[VDP] %d Python tools (%d KB)' % (len(tools), total_py // 1024))
for t in sorted(tools)[:8]:
    print('  %-30s %5d B' % (t, os.path.getsize(os.path.join(vdp_dir, t))))
if len(tools) > 8:
    print('  ... +%d more' % (len(tools) - 8))

print('  %d docs (.md)' % len(mds))

# 3. Languages
langs = set()
for t in tools:
    for l in ['python','javascript','typescript','rust','java','cpp','go','ruby','php','kotlin','csharp','ps','bash','ios','android']:
        if l in t.lower():
            langs.add(l)
print('\n[Languages] %d: %s' % (len(langs), ', '.join(sorted(langs))))

# 4. Git
r = subprocess.run(['git','-C',vdp_dir,'log','--oneline','-6'], capture_output=True, text=True, encoding='utf-8', errors='replace')
print('\n[Git] Last 6 commits (mss-vdp):')
for line in r.stdout.strip().split('\n'):
    print('  %s' % line)

# 5. API
try:
    resp = urllib.request.urlopen('http://127.0.0.1:53000/metrics', timeout=3)
    data = json.loads(resp.read())
    print('\n[API] %s v%s (port 53000)' % (data.get('service','?'), data.get('version','?')))
    print('  Uptime: %.0fs | Languages: %s | Tools: %s | Endpoints: %s' % (
        data.get('uptime_seconds',0), data.get('languages'), data.get('tools'), data.get('endpoints')))
except Exception as e:
    print('\n[API] DOWN: %s' % e)

# 6. Models
r = subprocess.run(['ollama','list'], capture_output=True, text=True)
mss_models = [l for l in r.stdout.split('\n') if 'mss' in l.lower()]
print('\n[Models] %d MSS models:' % len(mss_models))
for m in mss_models:
    print('  %s' % m)

# 7. Disk
disk = shutil.disk_usage('E:')
pct_free = disk.free / disk.total * 100
print('\n[Disk] E: %dGB free (%.1f%%)' % (disk.free // 1024**9, pct_free))

# 8. Summary
print('\n' + '=' * 60)
score = 0
if not gaps: score += 2
if len(tools) >= 30: score += 1
if data.get('languages', 0) >= 10: score += 1
if pct_free > 10: score += 1
if mss_models: score += 1

label = {0:'❄️ COLD', 1:'🌡️ LUKEWARM', 2:'🔥 WARM', 3:'🔥🔥 HOT', 4:'🔥🔥🔥 VERY HOT', 5:'🔥🔥🔥🔥 PRODUCTION', 6:'🔥🔥🔥🔥🔥 BLAZING'}
print('Health Score: %d/6 — %s' % (score, label.get(score, label[5])))
