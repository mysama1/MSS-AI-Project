#!/usr/bin/env python3
"""
MSS-VDP 服务健康监控器 v2.0
检测: skill_api.py (53000) / QClaw Gateway (52930) / IMA Proxy (11435)
支持: NSSM 服务状态 / 进程存活 / HTTP 端点响应 / 自动重启建议 / 状态变化告警
"""
import sys, os, json, subprocess, time, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path

# ── 告警集成 ──
try:
    from alert_sender import alert_service_down, alert_service_up
except ImportError:
    def alert_service_down(n, p, d=""): return True
    def alert_service_up(n, p): return True

# ── 状态追踪 (避免重复告警) ──
_last_status: dict = {}

SERVICES = {
    "skill_api": {
        "host": "127.0.0.1", "port": 53000,
        "endpoint": "/vdp/scan?content=test",
        "nssm_name": "mss-skill-api",
        "method": "POST",
        "body": json.dumps({"content": "echo test", "filetype": "powershell_script"}).encode(),
        "headers": {"Content-Type": "application/json"},
    },
    "qclaw_gateway": {
        "host": "127.0.0.1", "port": 52930,
        "endpoint": "/",
        "method": "GET",
    },
    "ima_proxy": {
        "host": "127.0.0.1", "port": 11435,
        "endpoint": "/api/tags",
        "method": "GET",
    },
}


def check_http(host: str, port: int, endpoint: str, method: str = "GET",
               body: bytes = None, headers: dict = None, timeout: int = 5) -> dict:
    """Check HTTP endpoint health."""
    url = f"http://{host}:{port}{endpoint}"
    req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    try:
        start = time.monotonic()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = round((time.monotonic() - start) * 1000)
            return {
                "reachable": True,
                "status": resp.status,
                "latency_ms": elapsed,
                "size": len(resp.read() or b""),
            }
    except urllib.error.HTTPError as e:
        return {"reachable": True, "status": e.code, "latency_ms": 0, "error": str(e)}
    except Exception as e:
        return {"reachable": False, "error": str(e)[:120]}


def check_nssm(service_name: str) -> dict:
    """Check NSSM service status."""
    try:
        r = subprocess.run(
            ["nssm", "status", service_name],
            capture_output=True, text=True, timeout=5,
            encoding='utf-8', errors='replace'
        )
        output = r.stdout.strip()
        return {
            "installed": r.returncode == 0 or "SERVICE_" in output,
            "status": output,
            "raw": output[:200],
        }
    except FileNotFoundError:
        return {"installed": False, "error": "NSSM not found in PATH"}
    except Exception as e:
        return {"installed": False, "error": str(e)[:100]}


def check_process(port: int) -> dict:
    """Check if a process is listening on the port."""
    try:
        r = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            capture_output=True, text=True, timeout=5,
            encoding='utf-8', errors='replace'
        )
        matches = [l for l in r.stdout.split('\n') if f':{port}' in l and 'LISTENING' in l]
        if matches:
            pid = matches[0].strip().split()[-1]
            # Get process name
            try:
                r2 = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                                  capture_output=True, text=True, timeout=5)
                proc_name = r2.stdout.strip().split(',')[0].strip('"') if r2.stdout else pid
            except:
                proc_name = pid
            return {"running": True, "pid": pid, "process": proc_name}
        return {"running": False}
    except Exception as e:
        return {"running": False, "error": str(e)[:100]}


def full_health_check() -> dict:
    """Run a comprehensive health check on all services. Triggers alerts on state change."""
    global _last_status
    results = {}
    all_healthy = True
    
    for name, config in SERVICES.items():
        method = config.get("method", "GET")
        hc = check_http(
            config["host"], config["port"], config["endpoint"],
            method=method,
            body=config.get("body"),
            headers=config.get("headers"),
        )
        
        nssm = check_nssm(config.get("nssm_name", f"mss-{name}"))
        proc = check_process(config["port"])
        
        healthy = hc.get("reachable", False) and hc.get("status", 0) < 500
        if not healthy:
            all_healthy = False
        
        # ── 状态变化告警 ──
        prev = _last_status.get(name)
        _last_status[name] = healthy
        
        if prev is not None and healthy != prev:
            if not healthy:
                alert_service_down(name, config["port"], 
                                   f"Error: {hc.get('error', 'No response')}")
            else:
                alert_service_up(name, config["port"])
        
        results[name] = {
            "healthy": healthy,
            "http": hc,
            "nssm": nssm,
            "process": proc,
        }
    
    return {
        "timestamp": datetime.now().isoformat(),
        "all_healthy": all_healthy,
        "services": results,
        "verdict": "PASS" if all_healthy else "FAIL",
    }


def restart_service(nssm_name: str, dry_run: bool = False) -> dict:
    """Restart an NSSM-managed service."""
    if dry_run:
        return {"action": "restart", "service": nssm_name, "dry_run": True}
    
    try:
        r = subprocess.run(
            ["nssm", "restart", nssm_name],
            capture_output=True, text=True, timeout=30,
            encoding='utf-8', errors='replace'
        )
        return {
            "action": "restart",
            "service": nssm_name,
            "success": r.returncode == 0,
            "output": r.stdout.strip()[:200],
        }
    except Exception as e:
        return {"action": "restart", "service": nssm_name, "error": str(e)[:100]}


def main():
    import argparse
    ap = argparse.ArgumentParser(description='MSS 服务健康监控器')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--restart', metavar='SERVICE', help='重启指定服务')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--watch', type=int, metavar='SEC', help='持续监控间隔(秒)')
    args = ap.parse_args()
    
    if args.restart:
        r = restart_service(args.restart, dry_run=args.dry_run)
        if args.json:
            print(json.dumps(r, indent=2, ensure_ascii=False))
        else:
            print(f"Restart {args.restart}: {'OK' if r.get('success') else 'FAILED'}")
        return
    
    if args.watch:
        interval = args.watch
        print(f"Watching every {interval}s (Ctrl+C to stop)")
        try:
            while True:
                report = full_health_check()
                status = "✅" if report["all_healthy"] else "❌"
                ts = report["timestamp"][:19]
                details = " | ".join(f"{n}:{'👍' if s['healthy'] else '👎'}" for n,s in report["services"].items())
                print(f"[{ts}] {status} {details}")
                if not report["all_healthy"]:
                    for n, s in report["services"].items():
                        if not s["healthy"]:
                            print(f"       ↓ {n}: {s['http'].get('error','?')}")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nStopped")
        return
    
    report = full_health_check()
    
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for name, s in report["services"].items():
            icon = "✅" if s["healthy"] else "❌"
            http = s["http"]
            proc = s["process"]
            print(f"{icon} {name:18s} "
                  f"HTTP {'UP' if http.get('reachable') else 'DOWN':5s} "
                  f"{str(http.get('status','?')):3s} {str(http.get('latency_ms','?')):>4s}ms  "
                  f"PID:{str(proc.get('pid','?')):6s}")
        
        print(f"\nVerdict: {report['verdict']}")
    
    sys.exit(0 if report["all_healthy"] else 1)


if __name__ == '__main__':
    main()
