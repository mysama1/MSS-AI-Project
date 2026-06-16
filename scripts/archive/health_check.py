#!/usr/bin/env python3
"""
MSS Project Health Monitor — One-command status snapshot.
py -3.11 health_check.py
"""
import os, json, sys, subprocess, shutil
from datetime import datetime

def check_kb():
    kb = r'E:\AI_Workspace\MSS-AI\project\knowledge_base'
    layers = {'L0_FOUNDATION':0,'L1_CORE_THEORY':0,'L2_APPLIED_THEORY':0,'L3_STRATEGIC':0,'L4_META':0}
    total = 0
    for layer in layers:
        d = os.path.join(kb, layer)
        if os.path.isdir(d):
            count = len([f for f in os.listdir(d) if f.endswith('.jsonl')])
            layers[layer] = count
            total += count
    root_count = len([f for f in os.listdir(kb) if f.endswith('.jsonl')])
    return {'total': total, 'by_layer': layers, 'root_left': root_count}

def check_git():
    repos = {
        'vdp': r'E:\QClaw-Data\skills\mss-vdp',
        'theory': r'E:\AI_Workspace\MSS-AI\project'
    }
    status = {}
    for name, path in repos.items():
        try:
            r = subprocess.run(['git','-C',path,'log','--oneline','-1'], 
                             capture_output=True, text=True, timeout=5)
            status[name] = r.stdout.strip() if r.returncode==0 else 'ERROR'
        except: status[name] = 'UNREACHABLE'
    return status

def check_models():
    try:
        r = subprocess.run(['ollama','list'], capture_output=True, text=True, timeout=10)
        lines = [l for l in r.stdout.split('\n') if 'mss-ai' in l.lower()]
        return lines
    except: return ['OLLAMA_UNAVAILABLE']

def check_services():
    services = {}
    # VDP API
    try:
        import urllib.request
        r = urllib.request.urlopen('http://127.0.0.1:53000/health', timeout=3)
        services['vdp_api:53000'] = 'OK' if r.status==200 else str(r.status)
    except: services['vdp_api:53000'] = 'DOWN'
    # Ollama
    try:
        r = urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=3)
        services['ollama:11434'] = 'OK' if r.status==200 else str(r.status)
    except: services['ollama:11434'] = 'DOWN'
    return services

def check_disk():
    try:
        total, used, free = shutil.disk_usage(r'E:')
        return {'total_gb': round(total/1e9,1), 'used_gb': round(used/1e9,1), 'free_gb': round(free/1e9,1)}
    except: return {'error': 'cannot read disk'}

def check_backup():
    backups = {}
    paths = {
        'kb': r'E:\AI_Workspace\MSS-AI\project\knowledge_base',
        'vdp': r'E:\QClaw-Data\skills\mss-vdp',
        'config': r'C:\Users\Administrator\.qclaw'
    }
    for name, path in paths.items():
        if os.path.exists(path):
            try:
                total_size = 0
                for root, dirs, files in os.walk(path):
                    for f in files:
                        try: total_size += os.path.getsize(os.path.join(root,f))
                        except: pass
                backups[name] = f'{round(total_size/1e6,1)}MB'
            except: backups[name] = 'ERROR'
        else:
            backups[name] = 'MISSING'
    return backups

# ── Main ──
print("="*60)
print(f"MSS Project Health — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("="*60)

kb = check_kb()
print(f"\n📚 KB: {kb['total']} entries ({kb['root_left']} at root)")
for layer, count in kb['by_layer'].items():
    print(f"   {layer}: {count}")

print(f"\n📡 Services:")
for s, status in check_services().items():
    icon = '✅' if status=='OK' else '❌'
    print(f"   {icon} {s}: {status}")

print(f"\n🤖 Models:")
for m in check_models():
    print(f"   {m}")

print(f"\n💾 Disk (E:): {check_disk().get('free_gb','?')}GB free")

print(f"\n📝 Git:")
for name, commit in check_git().items():
    print(f"   {name}: {commit[:60]}")

print(f"\n📦 Backup sizes:")
for name, size in check_backup().items():
    print(f"   {name}: {size}")

print(f"\n{'-'*60}")
print("Health Report Complete")
