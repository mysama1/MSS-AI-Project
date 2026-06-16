"""
MSSclaw Service Manager — NSSM 集成模块.

将 OpenClaw Gateway 注册为 Windows Service，脱离 Job Object 树：
  - CrossDomainRouter.bus.route() 在 Service 模式下不再被 SIGKILL
  - 服务管理：install / start / stop / restart / status / uninstall
  - 零外部依赖（nssm.exe 自动下载到 tools/ 目录）

架构：
  ServiceManager (Python wrapper)
      └── tools/nssm.exe (auto-downloaded, ~500KB, Public Domain)
          └── Windows SCM → OpenClaw Gateway (port 52930)

使用：
  from mss_agent.core.service_manager import ServiceManager
  sm = ServiceManager()
  sm.install()    # 注册 Windows Service
  sm.start()      # 启动服务
  sm.status()     # 查询状态
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


# ── 常量 ──

NSSM_VERSION = "2.24-101"
NSSM_DOWNLOAD_URL = f"https://nssm.cc/ci/nssm-{NSSM_VERSION}-g897c7ad.zip"
NSSM_EXPECTED_SIZE = (400 * 1024, 600 * 1024)  # ~500KB

# 默认服务配置
DEFAULT_SERVICE_NAME = "MSSclawGateway"
DEFAULT_GATEWAY_PORT = 52930
DEFAULT_GATEWAY_BIN = "openclaw"  # openclaw CLI
DEFAULT_GATEWAY_ARGS = "gateway start"


class ServiceStatus(str, Enum):
    """服务状态枚举"""
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    STARTING = "starting"
    STOPPING = "stopping"
    UNKNOWN = "unknown"
    NOT_INSTALLED = "not_installed"


@dataclass
class ServiceInfo:
    """服务信息"""
    name: str = DEFAULT_SERVICE_NAME
    status: ServiceStatus = ServiceStatus.NOT_INSTALLED
    pid: int = 0
    exit_code: int = 0
    uptime_seconds: float = 0.0


# ── 核心类 ──


class ServiceManager:
    """MSSclaw Windows Service 管理器.

    封装 NSSM 全部命令行操作，自动处理：
      - nssm.exe 首次下载/完整性校验
      - 服务安装参数（端口、工作目录、环境变量）
      - 状态轮询与超时保护
      - 存量服务检测（避免重复安装）

    nssm.exe 存放于 <project_root>/tools/nssm.exe
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        Args:
            project_root: MSS-AI 项目根目录，默认自动检测
        """
        self._project_root = project_root or self._detect_project_root()
        self._tools_dir = os.path.join(self._project_root, "tools")
        self._nssm_exe = os.path.join(self._tools_dir, "nssm.exe")

        # 可覆盖的服务配置
        self.service_name: str = DEFAULT_SERVICE_NAME
        self.gateway_bin: str = DEFAULT_GATEWAY_BIN
        self.gateway_args: str = DEFAULT_GATEWAY_ARGS
        self.gateway_port: int = DEFAULT_GATEWAY_PORT

    # ── 公开 API ──

    def ensure_nssm(self) -> bool:
        """确保 nssm.exe 可用，不存在则下载.

        Returns:
            True if nssm.exe is ready to use.
        """
        if self._check_nssm():
            return True
        return self._download_nssm()

    def install(self, name: str = "", display_name: str = "",
                description: str = "", auto_start: bool = True) -> dict:
        """安装 Windows Service.

        Args:
            name: 服务名 (默认 MSSclawGateway)
            display_name: 显示名称
            description: 服务描述
            auto_start: 是否自动启动
        """
        svc_name = name or self.service_name
        self.ensure_nssm()

        # 检查是否已安装
        existing = self.status(svc_name)
        if existing.status != ServiceStatus.NOT_INSTALLED:
            return {
                "success": False,
                "message": f"Service '{svc_name}' already installed (status={existing.status.value})",
                "service": existing,
            }

        display = display_name or f"MSSclaw Gateway v{NSSM_VERSION}"
        desc = description or "MSSclaw multi-agent system gateway (OpenClaw)"

        # nssm install <service> <program> [args]
        cmd = [
            self._nssm_exe, "install", svc_name,
            self.gateway_bin, self.gateway_args,
        ]
        result = self._run_nssm(cmd)
        if not result["success"]:
            return result

        # 配置参数
        self._nssm_set(svc_name, "AppDirectory", self._project_root)
        self._nssm_set(svc_name, "DisplayName", display)
        self._nssm_set(svc_name, "Description", desc)
        self._nssm_set(svc_name, "Start", "AUTO" if auto_start else "DEMAND")
        self._nssm_set(svc_name, "AppStdout", os.path.join(self._project_root, "logs", "gateway_service.log"))
        self._nssm_set(svc_name, "AppStderr", os.path.join(self._project_root, "logs", "gateway_service_err.log"))
        self._nssm_set(svc_name, "AppRotateFiles", "1")
        self._nssm_set(svc_name, "AppRotateOnline", "1")
        self._nssm_set(svc_name, "AppRotateBytes", "10485760")  # 10MB
        self._nssm_set(svc_name, "AppExit", "Restart")

        # 环境变量
        env_vars = self._build_env()
        for key, val in env_vars.items():
            self._nssm_set(svc_name, "AppEnvironmentExtra", f"{key}={val}")

        return {
            "success": True,
            "message": f"Service '{svc_name}' installed successfully",
            "service": self.status(svc_name),
        }

    def start(self, name: str = "", timeout: float = 30.0) -> dict:
        """启动服务.

        Args:
            name: 服务名
            timeout: 等待启动完成的超时 (秒)
        """
        svc_name = name or self.service_name
        self.ensure_nssm()

        result = self._run_nssm([self._nssm_exe, "start", svc_name])
        if not result["success"]:
            return result

        # 等待启动完成
        deadline = time.time() + timeout
        while time.time() < deadline:
            info = self.status(svc_name)
            if info.status == ServiceStatus.RUNNING:
                return {
                    "success": True,
                    "message": f"Service '{svc_name}' started (pid={info.pid})",
                    "service": info,
                }
            if info.status == ServiceStatus.STOPPED:
                return {
                    "success": False,
                    "message": f"Service '{svc_name}' exited immediately (code={info.exit_code})",
                    "service": info,
                }
            time.sleep(1.0)

        # 超时 — 检查当前状态
        info = self.status(svc_name)
        return {
            "success": info.status == ServiceStatus.RUNNING,
            "message": f"Service start timed out after {timeout}s, current status={info.status.value}",
            "service": info,
        }

    def stop(self, name: str = "", timeout: float = 30.0) -> dict:
        """停止服务."""
        svc_name = name or self.service_name
        result = self._run_nssm([self._nssm_exe, "stop", svc_name])
        if not result["success"]:
            return result

        deadline = time.time() + timeout
        while time.time() < deadline:
            info = self.status(svc_name)
            if info.status == ServiceStatus.STOPPED:
                return {
                    "success": True,
                    "message": f"Service '{svc_name}' stopped",
                    "service": info,
                }
            time.sleep(1.0)

        return {
            "success": False,
            "message": f"Service stop timed out after {timeout}s",
            "service": self.status(svc_name),
        }

    def restart(self, name: str = "", timeout: float = 60.0) -> dict:
        """重启服务."""
        svc_name = name or self.service_name
        result = self._run_nssm([self._nssm_exe, "restart", svc_name])
        if not result["success"]:
            # 降级：手动 stop + start
            self.stop(svc_name, timeout=timeout / 2)
            return self.start(svc_name, timeout=timeout / 2)

        deadline = time.time() + timeout
        while time.time() < deadline:
            info = self.status(svc_name)
            if info.status == ServiceStatus.RUNNING:
                return {
                    "success": True,
                    "message": f"Service '{svc_name}' restarted (pid={info.pid})",
                    "service": info,
                }
            time.sleep(1.0)
        return {
            "success": False,
            "message": f"Restart timed out after {timeout}s",
            "service": self.status(svc_name),
        }

    def status(self, name: str = "") -> ServiceInfo:
        """查询服务状态."""
        svc_name = name or self.service_name
        if not self._check_nssm():
            # 回退：检查服务是否在任务列表
            return self._fallback_status(svc_name)

        result = self._run_nssm([self._nssm_exe, "status", svc_name])
        stdout = result.get("stdout", "").strip()
        stderr = result.get("stderr", "").strip()

        info = ServiceInfo(name=svc_name)

        if "not installed" in stderr.lower() or "not installed" in stdout.lower():
            info.status = ServiceStatus.NOT_INSTALLED
            return info

        if stdout.startswith("SERVICE_RUNNING"):
            info.status = ServiceStatus.RUNNING
        elif stdout.startswith("SERVICE_STOPPED"):
            info.status = ServiceStatus.STOPPED
        elif stdout.startswith("SERVICE_PAUSED"):
            info.status = ServiceStatus.PAUSED
        elif stdout.startswith("SERVICE_START_PENDING"):
            info.status = ServiceStatus.STARTING
        elif stdout.startswith("SERVICE_STOP_PENDING"):
            info.status = ServiceStatus.STOPPING
        else:
            info.status = ServiceStatus.UNKNOWN

        # 提取 PID
        pid_line = result.get("pid_out", "")
        if pid_line and pid_line.strip().isdigit():
            info.pid = int(pid_line.strip())

        return info

    def uninstall(self, name: str = "", force: bool = False) -> dict:
        """卸载服务."""
        svc_name = name or self.service_name

        info = self.status(svc_name)
        if info.status == ServiceStatus.NOT_INSTALLED:
            return {"success": True, "message": f"Service '{svc_name}' not installed — nothing to uninstall"}

        if info.status == ServiceStatus.RUNNING and not force:
            return {
                "success": False,
                "message": f"Service '{svc_name}' is running. Stop first or use force=True",
            }

        if info.status == ServiceStatus.RUNNING:
            self.stop(svc_name)

        result = self._run_nssm([self._nssm_exe, "remove", svc_name, "confirm"])
        if result["success"]:
            return {"success": True, "message": f"Service '{svc_name}' uninstalled"}
        return result

    def is_running_as_service(self) -> bool:
        """检测当前进程是否在 NSSM Service 环境中运行.

        Returns True 如果在 Service 环境 (非 Job Object) 中.
        """
        info = self.status(self.service_name)
        return info.status == ServiceStatus.RUNNING

    # ── 内部实现 ──

    def _check_nssm(self) -> bool:
        """检查 nssm.exe 是否存在且有效."""
        if not os.path.isfile(self._nssm_exe):
            return False
        size = os.path.getsize(self._nssm_exe)
        min_size, max_size = NSSM_EXPECTED_SIZE
        return min_size <= size <= max_size

    def _download_nssm(self) -> bool:
        """下载 nssm.exe 到 tools/ 目录."""
        os.makedirs(self._tools_dir, exist_ok=True)

        zip_path = os.path.join(self._tools_dir, "nssm.zip")
        extract_dir = os.path.join(self._tools_dir, "_nssm_extract")
        logger.info(f"Downloading NSSM from {NSSM_DOWNLOAD_URL} ...")

        try:
            # Download
            urllib.request.urlretrieve(NSSM_DOWNLOAD_URL, zip_path)

            # Extract
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)

            # Find nssm.exe (it's in a subdir like nssm-2.24-101/win64/nssm.exe)
            for root, dirs, files in os.walk(extract_dir):
                for f in files:
                    if f.lower() == "nssm.exe":
                        src = os.path.join(root, f)
                        # Prefer 64-bit
                        dst = os.path.join(self._tools_dir, "nssm.exe")
                        if "win64" in root.lower():
                            shutil.copy2(src, dst)
                            break
                        elif "win32" in root.lower() and not os.path.exists(dst):
                            shutil.copy2(src, dst)

            # Cleanup
            os.remove(zip_path)
            shutil.rmtree(extract_dir, ignore_errors=True)

            if not self._check_nssm():
                logger.error("NSSM download failed: exe not found or wrong size")
                return False

            logger.info(f"NSSM installed: {self._nssm_exe}")
            return True

        except Exception as e:
            logger.error(f"NSSM download failed: {e}")
            # 清理
            for p in [zip_path, extract_dir]:
                try:
                    if os.path.isfile(p):
                        os.remove(p)
                    elif os.path.isdir(p):
                        shutil.rmtree(p)
                except Exception:
                    pass
            return False

    def _nssm_set(self, svc_name: str, param: str, value: str) -> bool:
        """nssm set <service> <param> <value>"""
        result = self._run_nssm([self._nssm_exe, "set", svc_name, param, value])
        return result["success"]

    def _run_nssm(self, cmd: list[str]) -> dict:
        """执行 nssm 命令，返回结构化结果."""
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self._tools_dir,
            )
            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "returncode": proc.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "", "stderr": "Command timed out", "returncode": -1}
        except FileNotFoundError:
            return {"success": False, "stdout": "", "stderr": f"nssm.exe not found at {self._nssm_exe}", "returncode": -1}

    def _fallback_status(self, svc_name: str) -> ServiceInfo:
        """回退状态检测 (无 nssm.exe 时)."""
        # 用 Windows sc query 检测
        try:
            result = subprocess.run(
                ["sc", "query", svc_name],
                capture_output=True, text=True, timeout=10,
            )
            out = result.stdout.lower()
            if "1060" in out or "not installed" in out:
                return ServiceInfo(name=svc_name, status=ServiceStatus.NOT_INSTALLED)
            if "running" in out:
                return ServiceInfo(name=svc_name, status=ServiceStatus.RUNNING)
            if "stopped" in out:
                return ServiceInfo(name=svc_name, status=ServiceStatus.STOPPED)
            return ServiceInfo(name=svc_name, status=ServiceStatus.UNKNOWN)
        except Exception:
            return ServiceInfo(name=svc_name, status=ServiceStatus.NOT_INSTALLED)

    def _build_env(self) -> dict[str, str]:
        """构建服务环境变量."""
        return {
            "MSS_AGENT_HOME": self._project_root,
            "MSS_GATEWAY_PORT": str(self.gateway_port),
            "LOG_LEVEL": "INFO",
        }

    @staticmethod
    def _detect_project_root() -> str:
        """自动检测项目根目录."""
        # 1. 环境变量
        env_root = os.environ.get("MSS_AGENT_HOME")
        if env_root:
            return env_root

        # 2. 从当前模块路径推断
        module_dir = Path(__file__).resolve().parent.parent.parent
        if (module_dir / "mss_agent").is_dir():
            return str(module_dir)

        # 3. cwd
        return os.getcwd()


# ── CLI 快捷入口 ──

def run_service_cli(args: list[str]) -> int:
    """MSSclaw service 子命令入口.

    用法: mssclaw service <action> [--name NAME] [--port PORT]

    示例:
      mssclaw service install           # 安装为 Windows Service
      mssclaw service start             # 启动
      mssclaw service stop              # 停止
      mssclaw service restart           # 重启
      mssclaw service status            # 查询状态
      mssclaw service uninstall         # 卸载
    """
    if len(args) < 2:
        _cli_usage()
        return 1

    action = args[1].lower()
    sm = ServiceManager()

    # 解析可选参数
    name = ""
    kwargs = {}
    i = 2
    while i < len(args):
        if args[i] == "--name" and i + 1 < len(args):
            name = args[i + 1]
            i += 2
        elif args[i] == "--port" and i + 1 < len(args):
            sm.gateway_port = int(args[i + 1])
            i += 2
        elif args[i] == "--force":
            kwargs["force"] = True
            i += 1
        else:
            i += 1

    try:
        if action == "install":
            result = sm.install(name=name, **kwargs)
        elif action == "start":
            result = sm.start(name=name, **kwargs)
        elif action == "stop":
            result = sm.stop(name=name, **kwargs)
        elif action == "restart":
            result = sm.restart(name=name, **kwargs)
        elif action == "status":
            info = sm.status(name=name)
            _print_status(info)
            return 0
        elif action == "uninstall":
            result = sm.uninstall(name=name, **kwargs)
        else:
            _cli_usage()
            return 1

        if isinstance(result, dict):
            print(f"{'✅' if result['success'] else '❌'} {result['message']}")
            if "service" in result:
                _print_status(result["service"])
            return 0 if result["success"] else 1

        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def _cli_usage() -> None:
    print("MSSclaw Service Manager")
    print()
    print("Usage: mssclaw service <action> [options]")
    print()
    print("Actions:")
    print("  install    Register as Windows Service")
    print("  start      Start the service")
    print("  stop       Stop the service")
    print("  restart    Restart the service")
    print("  status     Query service status")
    print("  uninstall  Remove Windows Service")
    print()
    print("Options:")
    print("  --name NAME   Service name (default: MSSclawGateway)")
    print("  --port PORT   Gateway port (default: 52930)")
    print("  --force       Force uninstall even if running")


def _print_status(info: ServiceInfo) -> None:
    """打印服务状态."""
    emoji = {"running": "🟢", "stopped": "🔴", "paused": "🟡",
             "starting": "🟠", "stopping": "🟠", "unknown": "⚪", "not_installed": "⚫"}
    e = emoji.get(info.status.value, "❓")
    print(f"  {e} {info.name}: {info.status.value}", end="")
    if info.pid:
        print(f" (pid={info.pid})", end="")
    if info.exit_code:
        print(f" (exit={info.exit_code})", end="")
    print()
