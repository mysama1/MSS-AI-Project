#!/usr/bin/env python3
"""
MSS 运行时检测系统 v1.0
实时监控: 进程健康 / 文件完整性 / 沙盒异常 / 端口可用性

监控项:
  1. 关键进程 (skill_api.py, ollama)
  2. 端口占用 (53000, 52930, 11434)
  3. 文件幽灵 (TRAE CLASS_B minifilter)
  4. 磁盘空间 (>5% free)
  5. 异常进程 (未知Python/ollama子进程)

用法:
  py -3.11 runtime_monitor.py --daemon        # 持续监控
  py -3.11 runtime_monitor.py --once           # 单次检查
  py -3.11 runtime_monitor.py --ghosts <dir>   # 幽灵文件扫描
"""

import sys, os, time, json, subprocess, threading, argparse
from datetime import datetime, timedelta
from collections import defaultdict

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SKILL_DIR, '.run', 'runtime_state.json')

# ── 监控配置 ──

CRITICAL_PROCESSES = [
    {"name": "skill_api.py", "port": 53000},
    {"name": "ollama", "port": 11434},
]

WATCH_PORTS = [53000, 52930, 11434]
WATCH_DIRS = [
    "E:\\QClaw-Data\\skills",
    "E:\\AI_Workspace\\MSS-AI",
]

DISK_MIN_FREE_PCT = 5
CHECK_INTERVAL_SEC = 30

# ── 检测模块 ──

def check_process(name: str) -> dict:
    """检查进程是否运行"""
    try:
        r = subprocess.run(
            ['powershell', '-Command', 
             f"(Get-Process -Name '{name}' -ErrorAction SilentlyContinue | Measure-Object).Count"],
            capture_output=True, text=True, timeout=5
        )
        count = int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0
        return {"process": name, "alive": count > 0, "instances": count}
    except:
        return {"process": name, "alive": False, "instances": 0, "error": "check_failed"}


def check_port(port: int) -> dict:
    """检查端口是否被监听"""
    try:
        r = subprocess.run(
            ['powershell', '-Command',
             f"(Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Measure-Object).Count"],
            capture_output=True, text=True, timeout=5
        )
        count = int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0
        pid = None
        if count > 0:
            r2 = subprocess.run(
                ['powershell', '-Command',
                 f"(Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess)"],
                capture_output=True, text=True, timeout=5
            )
            pid = r2.stdout.strip()
        return {"port": port, "bound": count > 0, "pid": pid}
    except:
        return {"port": port, "bound": False, "error": "check_failed"}


def check_ghosts(directory: str) -> dict:
    """扫描目录中的 CLASS_B 幽灵文件 (scandir可见, open失败)"""
    ghosts = []
    try:
        for root, dirs, files in os.walk(directory):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    # Try: scandir metadata (should work if real file)
                    if os.path.exists(fp):
                        # Try: open for reading (will fail for CLASS_B ghosts)
                        try:
                            with open(fp, 'rb') as fh:
                                fh.read(1)
                        except (PermissionError, FileNotFoundError, OSError) as e:
                            ghosts.append({"path": fp, "error": str(e)[:100], "type": "CLASS_B_GHOST"})
                except:
                    pass
    except Exception as e:
        return {"directory": directory, "ghosts": [], "error": str(e)[:200]}
    
    return {"directory": directory, "ghosts": ghosts, "ghost_count": len(ghosts)}


def check_disk() -> dict:
    """检查磁盘空间"""
    try:
        r = subprocess.run(
            ['powershell', '-Command',
             r"Get-PSDrive C | Select-Object Used,Free,@{N='PctFree';E={[math]::Round($_.Free/($_.Used+$_.Free)*100,1)}}"],
            capture_output=True, text=True, timeout=5
        )
        import re
        m = re.search(r'(\d+\.?\d*)\s*$', r.stdout.strip())
        pct_free = float(m.group(1)) if m else 100
        return {"drive": "C:", "pct_free": pct_free, "ok": pct_free > DISK_MIN_FREE_PCT}
    except:
        return {"drive": "C:", "error": "check_failed"}


def check_zombie_processes() -> dict:
    """检查异常进程（可能泄露的子进程）"""
    zombies = []
    try:
        r = subprocess.run(
            ['powershell', '-Command',
             r"Get-Process python* -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 200MB -and $_.CPU -gt 300 } | Select-Object Id,ProcessName,@{N='WS_MB';E={[math]::Round($_.WorkingSet64/1MB,0)}},CPU"],
            capture_output=True, text=True, timeout=5
        )
        for line in r.stdout.strip().split('\n'):
            if line.strip() and not line.startswith('Id'):
                zombies.append(line.strip())
    except:
        pass
    return {"zombies": zombies, "count": len(zombies)}


# ── 状态管理 ──

class RuntimeState:
    def __init__(self):
        self.changes = []  # 状态变化记录
    
    def load(self) -> dict:
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def save(self, state: dict):
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    def diff(self, old: dict, new: dict):
        """对比状态变化"""
        changes = []
        for key in new:
            if key not in old:
                changes.append({"key": key, "change": "NEW", "value": new[key]})
            elif old[key] != new[key]:
                changes.append({"key": key, "change": "CHANGED", 
                               "from": str(old[key])[:100], "to": str(new[key])[:100]})
        for key in old:
            if key not in new:
                changes.append({"key": key, "change": "GONE", "value": old[key]})
        return changes


# ── 主监控循环 ──

def run_once() -> dict:
    """单次全面检查"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "processes": [],
        "ports": [],
        "disk": None,
        "ghosts": [],
        "zombies": None,
        "verdict": "pass",
        "alerts": [],
    }
    
    # 1. Process check
    for proc in CRITICAL_PROCESSES:
        r = check_process(proc["name"])
        results["processes"].append(r)
        if not r["alive"]:
            results["alerts"].append(f"PROCESS_DOWN: {proc['name']}")
            results["verdict"] = "warn"
    
    # 2. Port check
    for port in WATCH_PORTS:
        r = check_port(port)
        results["ports"].append(r)
    
    # 3. Disk check
    disk = check_disk()
    results["disk"] = disk
    if not disk.get("ok"):
        results["alerts"].append(f"DISK_LOW: {disk.get('pct_free', '?')}%")
        results["verdict"] = "warn"
    
    # 4. Ghost scan (only for monitored dirs)
    for d in WATCH_DIRS:
        if os.path.exists(d):
            g = check_ghosts(d)
            results["ghosts"].append(g)
            if g.get("ghost_count", 0) > 0:
                results["alerts"].append(f"GHOST_FILES: {g['directory']} ({g['ghost_count']})")
                results["verdict"] = "warn"
    
    # 5. Zombie processes
    z = check_zombie_processes()
    results["zombies"] = z
    if z.get("count", 0) > 3:
        results["alerts"].append(f"ZOMBIE_PROCS: {z['count']}")
        results["verdict"] = "warn"
    
    # Summary
    total = len(results["processes"])
    alive = sum(1 for p in results["processes"] if p.get("alive"))
    results["summary"] = f"{alive}/{total} processes alive, {len(results['alerts'])} alerts"
    
    return results


def daemon_loop():
    """持续监控守护进程"""
    state_mgr = RuntimeState()
    old_state = state_mgr.load()
    
    print("MSS Runtime Monitor Daemon")
    print(f"Interval: {CHECK_INTERVAL_SEC}s | Time: {datetime.now().isoformat()}")
    print("=" * 50)
    
    iteration = 0
    while True:
        iteration += 1
        try:
            result = run_once()
            
            # Diff against previous
            changes = state_mgr.diff(
                old_state.get("last", {}),
                {"processes": result["processes"], "ports": result["ports"]}
            )
            
            if changes and iteration > 1:
                for c in changes[:5]:
                    print(f"  [CHANGE] {c['key']}: {c['change']}")
            
            if result["alerts"]:
                print(f"\n!!! ALERTS [{datetime.now().strftime('%H:%M:%S')}] !!!")
                for alert in result["alerts"]:
                    print(f"  ⚠️  {alert}")
            
            if iteration % 10 == 0:  # Every 5 min
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {result['summary']}")
            
            # Save state
            old_state["last"] = {"processes": result["processes"], "ports": result["ports"]}
            old_state["last_check"] = datetime.now().isoformat()
            old_state["iterations"] = iteration
            state_mgr.save(old_state)
            
        except Exception as e:
            print(f"[ERROR] {e}")
        
        time.sleep(CHECK_INTERVAL_SEC)


# ── CLI ──

def main():
    ap = argparse.ArgumentParser(description="MSS Runtime Monitor")
    ap.add_argument("--once", action="store_true", help="Single check")
    ap.add_argument("--daemon", action="store_true", help="Continuous monitoring")
    ap.add_argument("--ghosts", help="Scan directory for ghost files")
    ap.add_argument("--json", action="store_true", help="JSON output")
    ap.add_argument("--interval", type=int, default=30, help="Check interval (seconds)")
    args = ap.parse_args()
    
    if args.ghosts:
        result = check_ghosts(args.ghosts)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            ghosts = result.get("ghosts", [])
            print(f"Ghost scan: {result['directory']}")
            print(f"Found: {len(ghosts)} ghosts")
            for g in ghosts:
                print(f"  👻 {g['path']}")
                print(f"     {g['error']}")
        return
    
    if args.daemon:
        global CHECK_INTERVAL_SEC
        CHECK_INTERVAL_SEC = args.interval
        daemon_loop()
        return
    
    # Default: once
    result = run_once()
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=" * 50)
        print(f"MSS Runtime Check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        print("\n[Processes]")
        for p in result["processes"]:
            icon = "✅" if p.get("alive") else "❌"
            print(f"  {icon} {p['process']}: {p.get('instances', 0)} instances")
        
        print("\n[Ports]")
        for p in result["ports"]:
            bound = p.get("bound")
            pid = p.get("pid", "?")
            print(f"  {p['port']}: {'LISTENING' if bound else 'FREE'} (PID: {pid})")
        
        print(f"\n[Disk] C: {result['disk'].get('pct_free', '?')}% free")
        
        if result["ghosts"]:
            print("\n[Ghosts]")
            for g in result["ghosts"]:
                if g.get("ghost_count", 0) > 0:
                    print(f"  👻 {g['directory']}: {g['ghost_count']} ghosts")
                else:
                    print(f"  ✅ {g['directory']}: clean")
        
        if result["zombies"].get("count", 0) > 0:
            print(f"\n[Zombies] {result['zombies']['count']} suspicious processes")
        
        print(f"\nVerdict: {result['verdict'].upper()}")
        if result["alerts"]:
            print(f"Alerts: {len(result['alerts'])}")
            for a in result["alerts"]:
                print(f"  ⚠️  {a}")


if __name__ == "__main__":
    main()
