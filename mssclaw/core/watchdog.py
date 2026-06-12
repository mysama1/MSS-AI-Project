# -*- coding: utf-8 -*-
"""
mssclaw-gateway-watchdog.py — Track C: Service Wrapper

Windows Gateway 进程守护器。

核心修复:
  - CREATE_BREAKAWAY_FROM_JOB: 子进程脱离父 Job Object
    (根除 NSSM 模式下 Gateway 被 SIGKILL 连锁杀死的元凶)
  - 指数退避崩溃恢复: 1s→5s→15s→30s→60s (max)
  - 时间戳日志轮转
  - 可被 NSSM/SCM 管理 (作为 Windows Service 运行)

用法:
  直接运行:  python mssclaw-gateway-watchdog.py
  安装服务:  nssm install MSSclawGateway python mssclaw-gateway-watchdog.py
  启动服务:  nssm start MSSclawGateway
  手动管理:  sc start/stop/query MSSclawGateway

设计约束:
  - 零外部依赖 (仅 stdlib)
  - 所有异常内部捕获，不向 SCM 传播崩溃
  - 子进程 stdout/stderr 管道连接到日志
"""
import subprocess
import sys
import os
import time
import logging
import threading
import signal
from datetime import datetime
from pathlib import Path
from typing import Optional


# ════════════════════════════════════════════════════════════
# 配置
# ════════════════════════════════════════════════════════════

LOG_DIR = Path(r"E:\AI_Workspace\MSS-AI\project\logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Gateway 启动命令
GATEWAY_CMD = os.environ.get(
    "MSSCLAW_GATEWAY_CMD",
    "openclaw gateway --allow-unconfigured"
)

# 崩溃恢复退避 (ms)
RESTART_BACKOFF = [1000, 5000, 15000, 30000]
MAX_BACKOFF_MS = 60000

# 崩溃窗口
CRASH_WINDOW_SEC = 60
MAX_CRASHES_IN_WINDOW = 5

# 优雅关闭超时 (秒)
GRACEFUL_SHUTDOWN_SEC = 10

# 健康检查间隔 (秒)
HEALTH_CHECK_INTERVAL = 30


# ════════════════════════════════════════════════════════════
# 日志
# ════════════════════════════════════════════════════════════

def _setup_logging() -> logging.Logger:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = LOG_DIR / f"mssclaw-watchdog-{timestamp}.log"

    logger = logging.getLogger("mssclaw-watchdog")
    logger.setLevel(logging.DEBUG)

    # 文件 handler (详细)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(fh)

    # 控制台 handler (简要)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)

    return logger


log = _setup_logging()


# ════════════════════════════════════════════════════════════
# CREATE_BREAKAWAY_FROM_JOB 常量
# ════════════════════════════════════════════════════════════

# Win32 creation flags
CREATE_BREAKAWAY_FROM_JOB = 0x01000000
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200
DETACHED_PROCESS = 0x00000008

CHILD_FLAGS = (
    CREATE_BREAKAWAY_FROM_JOB |
    CREATE_NO_WINDOW |
    CREATE_NEW_PROCESS_GROUP
)

# Windows event codes for SCM
SERVICE_ACCEPT_STOP = 0x00000001
SERVICE_CONTROL_STOP = 0x00000001
SERVICE_CONTROL_INTERROGATE = 0x00000004


# ════════════════════════════════════════════════════════════
# 守护器核心
# ════════════════════════════════════════════════════════════

class GatewayWatchdog:
    """Gateway 进程守护器 — launch, monitor, recover, rotate."""

    def __init__(self, cmd: str = GATEWAY_CMD):
        self.cmd = cmd
        self.process: Optional[subprocess.Popen] = None
        self._stop_requested = threading.Event()
        self._crash_times: list[float] = []
        self._restart_count = 0
        self._running = False

    @property
    def pid(self) -> Optional[int]:
        return self.process.pid if self.process else None

    # ── Launch ──

    def launch(self) -> bool:
        """启动 Gateway 子进程 (带 CREATE_BREAKAWAY_FROM_JOB)."""
        try:
            parts = self.cmd.split()
            log.info(f"Launching: {self.cmd}")
            log.debug(f"Creation flags: 0x{CHILD_FLAGS:08X} "
                      f"(BREAKAWAY_FROM_JOB=0x{CREATE_BREAKAWAY_FROM_JOB:08X})")

            self.process = subprocess.Popen(
                parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=CHILD_FLAGS,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            log.info(f"Child spawned: PID={self.process.pid}")
            self._running = True

            # 启动 stdout 读取线程
            threading.Thread(
                target=self._read_stdout,
                daemon=True,
                name="stdout-reader"
            ).start()

            return True

        except Exception as e:
            log.error(f"Launch failed: {e}")
            return False

    def _read_stdout(self) -> None:
        """读取子进程 stdout，写入日志。"""
        if not self.process or not self.process.stdout:
            return
        try:
            for line in self.process.stdout:
                line = line.rstrip("\n\r")
                if line:
                    log.info(f"[gateway] {line}")
        except Exception:
            pass  # 进程终止时管道关闭

    # ── Monitor ──

    def monitor(self) -> None:
        """主监控循环 — 等待子进程退出，按退避策略重启。"""
        log.info("Watchdog monitor started")
        self._running = True

        while not self._stop_requested.is_set():
            if not self.process or self.process.poll() is not None:
                if not self._running:
                    break

                exit_code = self.process.returncode if self.process else -1
                log.warning(f"Gateway exited (code={exit_code})")

                # 记录崩溃时间
                now = time.time()
                self._crash_times.append(now)
                # 清理过期崩溃记录
                self._crash_times = [
                    t for t in self._crash_times
                    if now - t < CRASH_WINDOW_SEC
                ]

                # 检查是否需要重启
                if self._stop_requested.is_set():
                    break

                delay = self._backoff_delay()
                log.info(f"Restarting in {delay/1000:.1f}s "
                         f"(restart #{self._restart_count + 1})")
                self._stop_requested.wait(delay / 1000)

                if self._stop_requested.is_set():
                    break

                self.launch()
                self._restart_count += 1

            else:
                # 进程仍在运行 — 等退出或停止信号
                try:
                    self.process.wait(timeout=HEALTH_CHECK_INTERVAL)
                except subprocess.TimeoutExpired:
                    # 健康检查通过 — 继续等待
                    pass

        log.info("Watchdog monitor exiting")

    # ── Stop ──

    def stop(self) -> None:
        """优雅关闭 + 强制终止。"""
        log.info("Stop requested")
        self._stop_requested.set()
        self._running = False

        if not self.process:
            return

        # 优雅关闭: CTRL_C_EVENT
        pid = self.process.pid
        log.info(f"Signaling CTRL_C_EVENT to PID={pid}")
        try:
            self.process.send_signal(signal.CTRL_C_EVENT)
        except Exception as e:
            log.warning(f"CTRL_C_EVENT failed: {e}")

        # 等待
        try:
            self.process.wait(timeout=GRACEFUL_SHUTDOWN_SEC)
            log.info("Gateway exited gracefully")
        except subprocess.TimeoutExpired:
            log.warning(f"Gateway unresponsive after {GRACEFUL_SHUTDOWN_SEC}s, force killing")
            self.process.kill()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                log.error("Force kill also timed out")
        except Exception as e:
            log.error(f"Wait error: {e}")

    # ── Backoff ──

    def _backoff_delay(self) -> int:
        """计算退避延迟 (ms)."""
        crashes = len(self._crash_times)
        if crashes > MAX_CRASHES_IN_WINDOW:
            log.warning(f"Crash flood detected: {crashes} in {CRASH_WINDOW_SEC}s")
            return MAX_BACKOFF_MS

        idx = min(crashes - 1, len(RESTART_BACKOFF) - 1)
        delay = RESTART_BACKOFF[idx] if idx >= 0 else RESTART_BACKOFF[0]

        # ±20% 抖动
        import random
        jitter = int(delay * 0.2 * random.random())
        return delay + (jitter if random.random() > 0.5 else -jitter)

    def status(self) -> dict:
        """返回当前状态。"""
        alive = self.process and self.process.poll() is None
        return {
            "alive": alive,
            "pid": self.pid,
            "restart_count": self._restart_count,
            "crashes_in_window": len(self._crash_times),
            "cmd": self.cmd,
            "child_flags": f"0x{CHILD_FLAGS:08X}",
            "breakaway_from_job": True,
        }


# ════════════════════════════════════════════════════════════
# Windows Service 集成
# ════════════════════════════════════════════════════════════

class ServiceHandler:
    """最小 Windows Service 处理器 — 将 SCM 控制映射到 Watchdog。

    仅在 pywin32 可用时激活。不可用时退化为纯前台模式。
    """

    def __init__(self, watchdog: GatewayWatchdog):
        self.watchdog = watchdog
        self._svc_name = "MSSclawGateway"
        self._has_win32 = False

        try:
            import win32serviceutil
            import win32service
            import win32event
            self._win32serviceutil = win32serviceutil
            self._win32service = win32service
            self._win32event = win32event
            self._has_win32 = True
            log.info("pywin32 available — Service mode enabled")
        except ImportError:
            log.info("pywin32 not available — foreground mode only")

    def run(self) -> None:
        if self._has_win32:
            self._run_as_service()
        else:
            self._run_foreground()

    def _run_foreground(self) -> None:
        """纯前台模式 (直接运行/调试)."""
        log.info("Running in foreground mode (Ctrl+C to stop)")
        if not self.watchdog.launch():
            log.error("Failed to launch Gateway")
            return

        # 注册信号处理
        stop_requested = threading.Event()

        def _on_signal(sig, frame):
            log.info(f"Received signal {sig}")
            stop_requested.set()

        signal.signal(signal.SIGINT, _on_signal)
        signal.signal(signal.SIGTERM, _on_signal)

        # 监控线程
        monitor_thread = threading.Thread(
            target=self.watchdog.monitor,
            daemon=True,
            name="monitor"
        )
        monitor_thread.start()

        # 等停止信号
        stop_requested.wait()
        self.watchdog.stop()
        monitor_thread.join(timeout=5)
        log.info("Watchdog exited")

    def _run_as_service(self) -> None:
        """Windows Service 模式。

        pywin32 的 win32serviceutil.ServiceFramework 子类化方案。
        """
        win32serviceutil = self._win32serviceutil
        win32service = self._win32service
        win32event = self._win32event

        class MSSclawService(win32serviceutil.ServiceFramework):
            _svc_name_ = "MSSclawGateway"
            _svc_display_name_ = "MSSclaw Gateway Service"
            _svc_description_ = "MSS-AI Gateway — multi-channel agent orchestration"

            def __init__(self, args):
                win32serviceutil.ServiceFramework.__init__(self, args)
                self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
                self.watchdog = watchdog
                self._monitor_thread = None

            def SvcDoRun(self):
                log.info("Service started")
                if not self.watchdog.launch():
                    log.error("Failed to launch Gateway")
                    return

                self._monitor_thread = threading.Thread(
                    target=self.watchdog.monitor,
                    daemon=True,
                    name="svc-monitor"
                )
                self._monitor_thread.start()

                # SCM 控制循环
                while True:
                    rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
                    if rc == win32event.WAIT_OBJECT_0:
                        break

            def SvcStop(self):
                log.info("Service stop requested")
                self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
                self.watchdog.stop()
                win32event.SetEvent(self.hWaitStop)

        # 注册并运行
        win32serviceutil.HandleCommandLine(MSSclawService)


# ════════════════════════════════════════════════════════════
# CLI 入口
# ════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="MSSclaw Gateway Watchdog — Process Monitor + Crash Recovery"
    )
    parser.add_argument("--cmd", default=GATEWAY_CMD,
                        help="Gateway command to run")
    parser.add_argument("--status", action="store_true",
                        help="Print status and exit")
    parser.add_argument("--direct", action="store_true",
                        help="Run once without recovery loop")
    args = parser.parse_args()

    watchdog = GatewayWatchdog(args.cmd)

    if args.status:
        import json
        print(json.dumps(watchdog.status(), indent=2))
        return

    if args.direct:
        if watchdog.launch():
            print(f"PID={watchdog.pid}")
            watchdog.process.wait()
        return

    handler = ServiceHandler(watchdog)
    handler.run()


if __name__ == "__main__":
    main()
