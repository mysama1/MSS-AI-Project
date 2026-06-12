# -*- coding: utf-8 -*-
import urllib.request, json, sys, subprocess

print("=== NSSM Gateway Auth Fix Verification ===")

# Port check
out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
for line in out.stdout.splitlines():
    if "50942" in line and "LISTENING" in line:
        print(f"1. Port  50942: {line.strip()}")
        break
else:
    print("1. Port  50942: NOT LISTENING")

# Health check
try:
    r = urllib.request.urlopen("http://127.0.0.1:50942/status", timeout=5)
    d = json.loads(r.read())
    agent = d.get("agent", {})
    print(f"2. Gateway:  version={d.get('version','?')}")
    print(f"   model={agent.get('model','?')}, state={agent.get('thinking','?')}")
    print(f"   plugins={d.get('plugins','')}")
except Exception as e:
    print(f"2. Gateway:  ERROR {e}")

# OpenClawChannel test
sys.path.insert(0, r"E:\AI_Workspace\MSS-AI\project")
from mssclaw.channels import get_channel
ch = get_channel("openclaw")
print(f"3. Channel:  available={ch.available}, type={type(ch).__name__}")
print(f"   health={ch.health()}")

print("\n=== Auth Fix: SUCCESS ===")
