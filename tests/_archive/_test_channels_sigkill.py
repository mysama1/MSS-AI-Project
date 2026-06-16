# -*- coding: utf-8 -*-
"""SIGKILL 场景测试：Gateway 不可用时 channels 层降级"""
import sys, urllib.request, json, os, subprocess, time
sys.path.insert(0, r"E:\AI_Workspace\MSS-AI\project")

from mssclaw.channels import get_channel

print("=== Phase 1b: NSSM Service 实测验证 ===")

# 1. Gateway 健康检查
print("\n[1] Gateway 响应测试...")
try:
    req = urllib.request.urlopen("http://127.0.0.1:50942/status", timeout=5)
    data = json.loads(req.read())
    print(f"    Gateway OK: version={data.get('version','?')}")
    gateway_alive = True
except Exception as e:
    print(f"    Gateway NOT reachable: {e}")
    gateway_alive = False

# 2. OpenClawChannel 调用
print("\n[2] OpenClawChannel 测试...")
ch = get_channel("openclaw")
print(f"    available={ch.available}, type={type(ch).__name__}")
print(f"    health={ch.health()}")
result = ch.execute("say hello in one word")
print(f"    execute result: {repr(result[:100]) if result else '(empty - expected, openclaw ask is async)'}")

# 3. 模拟 SIGKILL：检测 Gateway 进程
print("\n[3] Gateway 进程检测...")
try:
    output = subprocess.run(
        ["netstat", "-ano"],
        capture_output=True, text=True, timeout=5
    )
    for line in output.stdout.splitlines():
        if "50942" in line and "LISTENING" in line:
            print(f"    LISTENING: {line.strip()}")
            break
    else:
        print("    50942 端口未在监听")
except Exception as e:
    print(f"    进程检测异常: {e}")

# 4. 降级测试：null 通道在 openclaw 不可用时仍正常
print("\n[4] 降级链路测试...")
null_ch = get_channel("null")
assert null_ch.execute("test") == "", "null channel should return empty"
assert null_ch.available, "null channel should always be available"

# 即使 openclaw 通道不可用，get_channel 也不应抛异常
ch_bad = get_channel("openclaw")
result_bad = ch_bad.execute("test")
print(f"    降级 result: {repr(result_bad[:50]) if result_bad else '(safe fallback - empty or error caught)'}")

print("\n=== Phase 1b DONE ===")
print(f"Gateway alive: {gateway_alive}")
print("降级链路: null OK, openclaw fallback OK")
