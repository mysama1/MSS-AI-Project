#!/usr/bin/env python
"""
mssclaw_daemon.py — Layer 2 守护进程
持续监控 Gateway 健康，崩溃自动恢复 + 指数退避 + 洪水保护

用法:
  python mssclaw_daemon.py status     # 健康仪表盘 (json)
  python mssclaw_daemon.py monitor    # 前台监控模式 (每30s一次检查)
  python mssclaw_daemon.py monitor --daemon  # 后台守护模式

依赖: NSSM 服务 (MSSclawGateway) 已安装并运行
      Gateway /health 端点 (127.0.0.1:50942)
"""
import sys, os, time, json, signal, threading, logging
from pathlib import Path

# Add project root
sys.path.insert(0, r"E:\AI_Workspace\MSS-AI\project")

from mssclaw.core.watchdog import (
    GatewayWatchdog, MAX_CRASHES_IN_WINDOW, CRASH_WINDOW_SEC,
    MAX_BACKOFF_MS, CREATE_BREAKAWAY_FROM_JOB, RESTART_BACKOFF
)
from mssclaw.core.service_manager import ServiceManager, ServiceStatus
import urllib.request as urlreq

logging.basicConfig(level=logging.INFO, format="%(asctime)s [DAEMON] %(message)s")
logger = logging.getLogger("mssclaw.daemon")

GATEWAY_HEALTH_URL = "http://127.0.0.1:50942/health"
CHECK_INTERVAL = 30  # seconds between health checks

def check_gateway_health(timeout=2):
    try:
        req = urlreq.Request(GATEWAY_HEALTH_URL)
        resp = urlreq.urlopen(req, timeout=timeout)
        data = json.loads(resp.read())
        return data.get('ok', False)
    except Exception:
        return False

def status_json():
    """Generate full health dashboard."""
    wd = GatewayWatchdog()
    sm = ServiceManager()
    svc = sm.status()
    return {
        "timestamp": time.time(),
        "nssm": {
            "name": sm.service_name,
            "status": svc.status.value if hasattr(svc.status, 'value') else str(svc.status),
        },
        "gateway": {
            "healthy": check_gateway_health(),
            "url": GATEWAY_HEALTH_URL,
        },
        "watchdog": wd.status(),
        "recovery": {
            "max_crashes_per_window": MAX_CRASHES_IN_WINDOW,
            "crash_window_sec": CRASH_WINDOW_SEC,
            "max_backoff_ms": MAX_BACKOFF_MS,
            "backoff_sequence_ms": list(RESTART_BACKOFF) if isinstance(RESTART_BACKOFF, list) else [RESTART_BACKOFF],
        },
    }

def monitor_loop(once=False):
    """Health check monitor loop."""
    wd = GatewayWatchdog()
    sm = ServiceManager()
    check_count = 0
    consecutive_failures = 0
    crash_window = []
    
    logger.info(f"Monitor started (interval={CHECK_INTERVAL}s)")
    
    while True:
        check_count += 1
        svc = sm.status()
        gateway_ok = check_gateway_health()
        
        if gateway_ok:
            consecutive_failures = 0
            logger.info(f"[{check_count}] Gateway OK")
        else:
            consecutive_failures += 1
            now = time.time()
            crash_window.append(now)
            crash_window = [t for t in crash_window if now - t < CRASH_WINDOW_SEC]
            
            logger.warning(f"[{check_count}] Gateway DOWN (consecutive={consecutive_failures}, crashes_in_window={len(crash_window)})")
            
            if len(crash_window) >= MAX_CRASHES_IN_WINDOW:
                logger.critical(f"CRASH FLOOD: {len(crash_window)} crashes in {CRASH_WINDOW_SEC}s → CIRCUIT BREAK")
                logger.critical("Manual intervention required. Daemon stopping.")
                return False
            
            # Determine backoff
            idx = min(consecutive_failures - 1, len(RESTART_BACKOFF) - 1)
            backoff_s = RESTART_BACKOFF[idx] / 1000.0  # ms → s
            logger.error(f"Attempting restart in {backoff_s:.0f}s (backoff level {idx+1})")
            
            time.sleep(backoff_s)
            
            # Restart via NSSM
            logger.info("Restarting Gateway via NSSM...")
            result = sm.restart(timeout=60)
            logger.info(f"Restart result: {result.get('ok', result)}")
            
            time.sleep(5)  # Let Gateway stabilize
            
            if check_gateway_health():
                logger.info("Gateway recovered!")
                consecutive_failures = 0
            else:
                logger.warning("Gateway still down after restart")
        
        if once:
            return True
        
        time.sleep(CHECK_INTERVAL)

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    
    if cmd == "status":
        print(json.dumps(status_json(), indent=2))
    elif cmd == "monitor":
        daemon = "--daemon" in sys.argv
        if daemon:
            logger.info("Starting in daemon mode...")
        monitor_loop(once=False)
    elif cmd == "test":
        # One-shot test
        logger.info("One-shot test...")
        monitor_loop(once=True)
    else:
        print(f"Usage: {sys.argv[0]} [status|monitor|test]")
        sys.exit(1)

if __name__ == "__main__":
    main()
