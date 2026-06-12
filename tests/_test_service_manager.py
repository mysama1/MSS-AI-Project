"""Service Manager 冒烟测试 — 无需管理员权限 (仅检查导入+下载+status)"""
import sys; sys.path.insert(0, '.')
sys.path.insert(0, 'E:/AI_Workspace/MSS-AI/project')

from mss_agent.core.service_manager import (
    ServiceManager, ServiceStatus, ServiceInfo, NSSM_VERSION, NSSM_DOWNLOAD_URL
)

print(f"NSSM Version: {NSSM_VERSION}")
print(f"Download URL: {NSSM_DOWNLOAD_URL}")

sm = ServiceManager()
print(f"Project root: {sm._project_root}")
print(f"Tools dir:   {sm._tools_dir}")
print(f"nssm.exe:    {sm._nssm_exe}")

# Check status (no nssm, should fallback)
info = sm.status()
print(f"\nStatus (fallback): {info.status.value}")

# Check nssm availability
print(f"NSSM available: {sm._check_nssm()}")

# Test structs
info2 = ServiceInfo(name="test", status=ServiceStatus.RUNNING, pid=1234)
assert info2.status == ServiceStatus.RUNNING
assert info2.pid == 1234

# Status enum coverage
for s in ServiceStatus:
    assert s.value in ["running","stopped","paused","starting","stopping","unknown","not_installed"]

# _build_env
env = sm._build_env()
assert "MSS_AGENT_HOME" in env
assert "MSS_GATEWAY_PORT" in env
assert env["MSS_GATEWAY_PORT"] == "52930"

print("\n=== ALL PASS ===")
