"""
mssclaw/core/platform_service.py — 跨平台服务管理器抽象
Windows: NSSM | Linux: systemd
"""
import platform, subprocess, os, json, urllib.request
from dataclasses import dataclass
from typing import Optional

@dataclass
class ServiceInfo:
    name: str
    running: bool
    pid: int = 0
    platform: str = ""
    error: str = ""

class PlatformService:
    def __init__(self, name="MSSclawGateway"):
        self.name = name
        self._plat = platform.system()
    
    def status(self):
        if self._plat == "Windows":
            try:
                nssm = self._find_nssm()
                if nssm:
                    r = subprocess.run([nssm, "status", self.name], capture_output=True, text=True, timeout=10)
                    return ServiceInfo(self.name, "SERVICE_RUNNING" in r.stdout, platform="nssm")
            except: pass
            try:
                req = urllib.request.Request("http://127.0.0.1:50942/health")
                resp = urllib.request.urlopen(req, timeout=3)
                return ServiceInfo(self.name, json.loads(resp.read()).get("ok", False), platform="direct")
            except:
                return ServiceInfo(self.name, False, platform="unknown")
        else:
            try:
                r = subprocess.run(["systemctl", "is-active", self.name], capture_output=True, text=True, timeout=10)
                return ServiceInfo(self.name, "active" in r.stdout, platform="systemd")
            except:
                return ServiceInfo(self.name, False, platform="unknown")
    
    def _find_nssm(self):
        for p in [r"C:\nssm\nssm.exe", r"C:\Program Files\nssm\nssm.exe"]:
            if os.path.exists(p): return p
        return None
    
    def start(self, timeout=30):
        if self._plat == "Windows":
            nssm = self._find_nssm()
            if nssm:
                r = subprocess.run([nssm, "start", self.name], capture_output=True, text=True, timeout=timeout)
                return {"ok": r.returncode == 0}
        else:
            r = subprocess.run(["systemctl", "start", self.name], capture_output=True, text=True, timeout=timeout)
            return {"ok": r.returncode == 0}
        return {"ok": False, "error": "no service manager"}
    
    def stop(self, timeout=30):
        if self._plat == "Windows":
            nssm = self._find_nssm()
            if nssm:
                r = subprocess.run([nssm, "stop", self.name], capture_output=True, text=True, timeout=timeout)
                return {"ok": r.returncode == 0}
        else:
            r = subprocess.run(["systemctl", "stop", self.name], capture_output=True, text=True, timeout=timeout)
            return {"ok": r.returncode == 0}
        return {"ok": False}
    
    def restart(self, timeout=60):
        if self._plat == "Windows":
            nssm = self._find_nssm()
            if nssm:
                r = subprocess.run([nssm, "restart", self.name], capture_output=True, text=True, timeout=timeout)
                return {"ok": r.returncode == 0}
        else:
            r = subprocess.run(["systemctl", "restart", self.name], capture_output=True, text=True, timeout=timeout)
            return {"ok": r.returncode == 0}
        return {"ok": False}
    
    def generate_systemd_unit(self, exec_path="/opt/mssclaw/bin/gateway.sh"):
        return f"""[Unit]
Description=MSSclaw Gateway
After=network.target

[Service]
Type=simple
ExecStart={exec_path}
Restart=on-failure
RestartSec=5
StartLimitInterval=60
StartLimitBurst=5
User=mssclaw
Group=mssclaw
Environment=MSSCLAW_PORT=50942

[Install]
WantedBy=multi-user.target
"""

    def generate_deploy_script(self, target="/opt/mssclaw"):
        return f"""#!/bin/bash
set -e
TARGET="{target}"
echo "=== MSSclaw Linux Deploy ==="
sudo mkdir -p "$TARGET" "$TARGET/logs" "$TARGET/data"
sudo useradd -r -s /bin/false mssclaw 2>/dev/null || true
sudo chown -R mssclaw:mssclaw "$TARGET"
pip3 install httpx urllib3
sudo tee /etc/systemd/system/{self.name}.service > /dev/null <<'UNIT'
{self.generate_systemd_unit()}
UNIT
sudo systemctl daemon-reload
sudo systemctl enable {self.name}
sudo systemctl start {self.name}
echo "Done. Logs: sudo journalctl -u {self.name} -f"
"""
