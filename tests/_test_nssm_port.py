# -*- coding: utf-8 -*-
"""Verify NSSM Gateway on port 18789"""
import urllib.request, json

# Test NSSM Gateway directly on 18789
print("=== NSSM Gateway Direct Test ===")
try:
    r = urllib.request.urlopen("http://127.0.0.1:18789/status", timeout=5)
    d = json.loads(r.read())
    agent = d.get("agent", {})
    print(f"HTTP 200: version={d.get('version','?')}, model={agent.get('model','?')}")
    print(f"  plugins={d.get('plugins','')}")
    print("NSSM Gateway: FULLY OPERATIONAL")
except Exception as e:
    print(f"FAIL: {e}")

# Test OpenClawChannel (will use user's openclaw CLI)
import sys
sys.path.insert(0, r"E:\AI_Workspace\MSS-AI\project")
from mssclaw.channels import get_channel, list_channels

print(f"\n=== Channels Status ===")
print(f"list: {list_channels()}")
ch = get_channel("openclaw")
print(f"channel: available={ch.available}, type={type(ch).__name__}")
print(f"health: {ch.health()}")
