# -*- coding: utf-8 -*-
"""
MSSclaw Security Sandbox — Track B

进程级安全沙盒，补现有 GuardianEngine + NormativeField 缺失的系统层防护。

设计原则:
  1. Capability-based: 每个 Agent 声明 capability 清单，未声明=禁止
  2. Fail-closed: 任何未匹配规则 → 拒绝
  3. 双层集成: Sandbox 在 Agent 与 OS 之间，Guardian 在语义层
  4. 零外部依赖: 纯 Python stdlib (仅 subprocess/psutil 探测依赖放入函数内)

五维约束:
  - FS:   文件系统访问 (读/写/删除/执行 白名单路径)
  - NET:  网络访问 (host/port 白名单)
  - PROC: 进程操作 (可调用的子进程)
  - MEM:  内存配额 (硬/软限制)
  - TIME: 时间预算 (wall-clock + CPU time)
"""
from __future__ import annotations

import os
import re
import sys
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from fnmatch import fnmatch
from pathlib import Path
from typing import Optional


# ════════════════════════════════════════════════════════════
# Capability 定义
# ════════════════════════════════════════════════════════════

class Capability(Enum):
    """Agent 可以声明的能力。未声明=禁止。"""
    # FS
    FS_READ_HOME = "fs.read.home"
    FS_READ_PROJECT = "fs.read.project"
    FS_READ_ANY = "fs.read.any"
    FS_WRITE_HOME = "fs.write.home"
    FS_WRITE_PROJECT = "fs.write.project"
    FS_WRITE_ANY = "fs.write.any"
    FS_DELETE_ANY = "fs.delete.any"
    FS_EXEC_ANY = "fs.exec.any"
    FS_EXEC_SAFE = "fs.exec.safe"

    # NET
    NET_INBOUND = "net.inbound"
    NET_OUTBOUND_LOCAL = "net.outbound.local"
    NET_OUTBOUND_ANY = "net.outbound.any"
    NET_DNS = "net.dns"

    # PROC
    PROC_SUBPROCESS = "proc.subprocess"
    PROC_SUBPROCESS_SAFE = "proc.subprocess.safe"
    PROC_SIGNAL = "proc.signal"

    # SPECIAL
    SYS_TIME = "sys.time"
    SYS_ENV_READ = "sys.env.read"
    SYS_STDIO = "sys.stdio"


# ════════════════════════════════════════════════════════════
# 数据模型
# ════════════════════════════════════════════════════════════

@dataclass
class QuotaLimits:
    """资源配额 — 硬限制 + 软限制"""
    max_memory_mb: int = 512          # 硬
    soft_memory_mb: int = 384         # 软 (达此值触发 GC/降级)
    max_wall_time_s: float = 300.0    # 硬
    soft_wall_time_s: float = 240.0   # 软
    max_cpu_time_s: float = 60.0      # 硬
    max_open_files: int = 100
    max_subprocesses: int = 5

    # 是否允许超出软限制 (需 Supervisor 审批)
    allow_soft_exceed: bool = False


@dataclass
class QuotaUsage:
    """当前资源使用量"""
    memory_current_mb: float = 0.0
    memory_peak_mb: float = 0.0
    wall_time_elapsed: float = 0.0
    cpu_time_elapsed: float = 0.0
    open_files: int = 0
    subprocess_count: int = 0
    io_read_mb: float = 0.0
    io_write_mb: float = 0.0


@dataclass
class SandboxVerdict:
    """沙盒判定结果"""
    allowed: bool
    rule_id: str           # 匹配的规则 ID
    reason: str            # 拒绝原因
    capability: Optional[Capability] = None
    suggestion: Optional[str] = None


@dataclass
class SandboxProfile:
    """Agent 沙盒配置"""
    agent_id: str
    agent_type: str          # "plan" | "audit" | "executor" | "concierge"
    capabilities: set[Capability] = field(default_factory=set)
    quotas: QuotaLimits = field(default_factory=QuotaLimits)
    fs_allowlist: list[str] = field(default_factory=list)  # glob patterns
    fs_denylist: list[str] = field(default_factory=list)   # glob patterns (优先级 > allowlist)
    net_allowlist: list[str] = field(default_factory=list)  # "host:port" patterns
    proc_allowlist: list[str] = field(default_factory=list)  # executable names

    # 运行时状态
    _usage: QuotaUsage = field(default_factory=QuotaUsage, init=False, repr=False)
    _start_time: float = field(default_factory=time.time, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)


# ════════════════════════════════════════════════════════════
# 预设配置
# ════════════════════════════════════════════════════════════

PRESET_PROFILES: dict[str, SandboxProfile] = {}


def _init_presets():
    """初始化预设沙盒配置 (延迟调用，避免模块导入副作用)."""
    if PRESET_PROFILES:
        return

    # Plan-Agent: 立法者，只读 + 统计
    PRESET_PROFILES["plan"] = SandboxProfile(
        agent_id="plan-agent",
        agent_type="plan",
        capabilities={
            Capability.FS_READ_PROJECT,
            Capability.FS_WRITE_PROJECT,  # 写任务计划
            Capability.NET_DNS,
            Capability.NET_OUTBOUND_LOCAL,  # localhost Ollama
            Capability.PROC_SUBPROCESS_SAFE,
            Capability.SYS_TIME,
            Capability.SYS_ENV_READ,
            Capability.SYS_STDIO,
        },
        quotas=QuotaLimits(
            max_memory_mb=1024, soft_memory_mb=768,
            max_wall_time_s=600, soft_wall_time_s=480,
            max_cpu_time_s=120, max_subprocesses=10,
        ),
        fs_allowlist=[
            "E:\\AI_Workspace\\MSS-AI\\project\\**",
            "C:\\Users\\Administrator\\.openclaw\\workspace\\**",
        ],
        fs_denylist=[
            "**\\secrets\\**",
            "**\\.env",
            "**\\credentials\\**",
            "**\\private_key*",
            "**\\id_rsa*",
        ],
        net_allowlist=["localhost:*", "127.0.0.1:*", "*.github.com:443"],
        proc_allowlist=["python", "python3", "git", "ollama"],
    )

    # Audit-Agent: 司法者，只读
    PRESET_PROFILES["audit"] = SandboxProfile(
        agent_id="audit-agent",
        agent_type="audit",
        capabilities={
            Capability.FS_READ_PROJECT,
            Capability.NET_DNS,
            Capability.SYS_TIME,
            Capability.SYS_STDIO,
        },
        quotas=QuotaLimits(
            max_memory_mb=512, soft_memory_mb=384,
            max_wall_time_s=300, soft_wall_time_s=240,
            max_cpu_time_s=30, max_open_files=200,
        ),
        fs_allowlist=[
            "E:\\AI_Workspace\\MSS-AI\\project\\**",
        ],
        fs_denylist=[
            "**\\secrets\\**",
            "**\\.env",
        ],
        net_allowlist=["localhost:*"],
        proc_allowlist=[],
    )

    # Executor Agent: 行政者，有限写
    PRESET_PROFILES["executor"] = SandboxProfile(
        agent_id="executor-agent",
        agent_type="executor",
        capabilities={
            Capability.FS_READ_PROJECT,
            Capability.FS_WRITE_PROJECT,
            Capability.NET_DNS,
            Capability.NET_OUTBOUND_LOCAL,
            Capability.PROC_SUBPROCESS_SAFE,
            Capability.SYS_TIME,
            Capability.SYS_ENV_READ,
            Capability.SYS_STDIO,
        },
        quotas=QuotaLimits(
            max_memory_mb=2048, soft_memory_mb=1536,
            max_wall_time_s=1200, soft_wall_time_s=960,
            max_cpu_time_s=300, max_subprocesses=20,
        ),
        fs_allowlist=[
            "E:\\AI_Workspace\\MSS-AI\\project\\**",
            "C:\\Users\\Administrator\\.openclaw\\workspace\\**",
        ],
        fs_denylist=[
            "**\\secrets\\**",
            "**\\.env",
            "**\\credentials\\**",
            "**\\private_key*",
            "C:\\Windows\\**",
            "C:\\Program Files\\**",
        ],
        net_allowlist=["localhost:*", "127.0.0.1:*", "*.github.com:443", "*.pypi.org:443"],
        proc_allowlist=["python", "python3", "git", "ollama", "pip", "maturin", "cargo"],
    )

    # Concierge Agent: 生活助手，最受限
    PRESET_PROFILES["concierge"] = SandboxProfile(
        agent_id="concierge-agent",
        agent_type="concierge",
        capabilities={
            Capability.NET_DNS,
            Capability.NET_OUTBOUND_LOCAL,  # 仅 allowlist 内目标
            Capability.SYS_TIME,
            Capability.SYS_STDIO,
        },
        quotas=QuotaLimits(
            max_memory_mb=256, soft_memory_mb=192,
            max_wall_time_s=120, soft_wall_time_s=90,
            max_cpu_time_s=15,
        ),
        fs_allowlist=[],
        fs_denylist=["**"],  # 全禁文件系统
        net_allowlist=[
            "localhost:*",
            "*.openai.com:443",
            "*.deepseek.com:443",
            "*.google.com:443",
            "api.weather.gov:443",
        ],
        proc_allowlist=[],
    )


# ════════════════════════════════════════════════════════════
# 沙盒引擎
# ════════════════════════════════════════════════════════════

class SandboxRegistry:
    """全局沙盒注册表 — 管理所有 Agent 的沙盒配置。"""

    def __init__(self):
        _init_presets()
        self._profiles: dict[str, SandboxProfile] = {}
        self._audit_log: list[dict] = []

    def register(self, profile: SandboxProfile) -> None:
        self._profiles[profile.agent_id] = profile

    def get(self, agent_id: str) -> Optional[SandboxProfile]:
        return self._profiles.get(agent_id)

    def get_or_preset(self, agent_id: str, agent_type: str) -> SandboxProfile:
        """获取已有 profile 或从预设创建。"""
        if agent_id in self._profiles:
            return self._profiles[agent_id]
        preset = PRESET_PROFILES.get(agent_type)
        if preset:
            profile = SandboxProfile(
                agent_id=agent_id,
                agent_type=agent_type,
                capabilities=preset.capabilities.copy(),
                quotas=preset.quotas,
                fs_allowlist=preset.fs_allowlist.copy(),
                fs_denylist=preset.fs_denylist.copy(),
                net_allowlist=preset.net_allowlist.copy(),
                proc_allowlist=preset.proc_allowlist.copy(),
            )
            self._profiles[agent_id] = profile
            return profile
        # 未知类型 → 最小权限
        profile = SandboxProfile(agent_id=agent_id, agent_type=agent_type)
        self._profiles[agent_id] = profile
        return profile

    def remove(self, agent_id: str) -> None:
        self._profiles.pop(agent_id, None)

    def audit_log(self) -> list[dict]:
        return list(self._audit_log)

    def _log(self, entry: dict) -> None:
        entry["timestamp"] = time.time()
        self._audit_log.append(entry)
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-5000:]


# ── 全局单例 ──
_registry: Optional[SandboxRegistry] = None
_registry_lock = threading.Lock()


def get_registry() -> SandboxRegistry:
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = SandboxRegistry()
    return _registry


# ════════════════════════════════════════════════════════════
# 五维检查引擎
# ════════════════════════════════════════════════════════════

class CapabilityChecker:
    """Capability 驱动的一站式权限检查。"""

    def __init__(self, registry: Optional[SandboxRegistry] = None):
        self.registry = registry or get_registry()

    # ── FS 检查 ──

    def check_fs_read(self, agent_id: str, path: str) -> SandboxVerdict:
        profile = self._require_profile(agent_id)
        if profile is None:
            return SandboxVerdict(False, "SANDBOX-FS-00", "Agent not registered")

        # 检查 capability
        if Capability.FS_READ_ANY not in profile.capabilities:
            if Capability.FS_READ_HOME not in profile.capabilities \
               and Capability.FS_READ_PROJECT not in profile.capabilities:
                return SandboxVerdict(False, "SANDBOX-FS-CAP",
                    "Agent has no FS read capability",
                    suggestion="Add fs.read.home or fs.read.project capability")

        # Denylist first (优先)
        for pattern in profile.fs_denylist:
            if self._glob_match(path, pattern):
                self._audit(agent_id, "fs_read_denied", {"path": path, "pattern": pattern})
                return SandboxVerdict(False, "SANDBOX-FS-DENY",
                    f"Path {path} matches denylist pattern {pattern}")

        # Allowlist
        if profile.fs_allowlist:
            for pattern in profile.fs_allowlist:
                if self._glob_match(path, pattern):
                    self._audit(agent_id, "fs_read_ok", {"path": path})
                    return SandboxVerdict(True, "SANDBOX-FS-OK", "")
            return SandboxVerdict(False, "SANDBOX-FS-NOMATCH",
                f"Path {path} not in allowlist",
                suggestion="Add path to fs_allowlist")

        # 无 allowlist = 全允许 (但受 capability 限制)
        self._audit(agent_id, "fs_read_ok", {"path": path})
        return SandboxVerdict(True, "SANDBOX-FS-OK", "")

    def check_fs_write(self, agent_id: str, path: str) -> SandboxVerdict:
        profile = self._require_profile(agent_id)
        if profile is None:
            return SandboxVerdict(False, "SANDBOX-FS-00", "Agent not registered")

        if Capability.FS_WRITE_ANY not in profile.capabilities:
            if Capability.FS_WRITE_HOME not in profile.capabilities \
               and Capability.FS_WRITE_PROJECT not in profile.capabilities:
                return SandboxVerdict(False, "SANDBOX-FS-CAP",
                    "Agent has no FS write capability")

        # Always check denylist
        for pattern in profile.fs_denylist:
            if self._glob_match(path, pattern):
                return SandboxVerdict(False, "SANDBOX-FS-DENY",
                    f"Write path {path} matches denylist {pattern}")

        if profile.fs_allowlist:
            for pattern in profile.fs_allowlist:
                if self._glob_match(path, pattern):
                    return SandboxVerdict(True, "SANDBOX-FS-OK", "")
            return SandboxVerdict(False, "SANDBOX-FS-NOMATCH",
                f"Write path {path} not in allowlist")

        return SandboxVerdict(True, "SANDBOX-FS-OK", "")

    # ── Network 检查 ──

    def check_net(self, agent_id: str, host: str, port: int = 0) -> SandboxVerdict:
        profile = self._require_profile(agent_id)
        if profile is None:
            return SandboxVerdict(False, "SANDBOX-NET-00", "Agent not registered")

        # Localhost always allowed if capability present
        if host in ("localhost", "127.0.0.1", "::1"):
            if Capability.NET_OUTBOUND_LOCAL in profile.capabilities \
               or Capability.NET_OUTBOUND_ANY in profile.capabilities:
                return SandboxVerdict(True, "SANDBOX-NET-LOCAL", "")

        # Non-localhost: need NET_OUTBOUND_ANY OR NET_OUTBOUND_LOCAL with allowlist match
        has_any = Capability.NET_OUTBOUND_ANY in profile.capabilities
        has_local = Capability.NET_OUTBOUND_LOCAL in profile.capabilities
        if not has_any and not has_local:
            return SandboxVerdict(False, "SANDBOX-NET-CAP",
                f"Agent lacks net.outbound capability for {host}")

        # Check allowlist
        for pattern in profile.net_allowlist:
            if self._net_match(host, port, pattern):
                return SandboxVerdict(True, "SANDBOX-NET-OK", "")

        # NET_OUTBOUND_ANY can reach anything
        if has_any:
            return SandboxVerdict(True, "SANDBOX-NET-ANY", "")

        return SandboxVerdict(False, "SANDBOX-NET-NOMATCH",
            f"Host {host}:{port} not in net allowlist",
            suggestion=f"Add {host}:{port} to net_allowlist")

    # ── Process 检查 ──

    def check_proc(self, agent_id: str, executable: str) -> SandboxVerdict:
        profile = self._require_profile(agent_id)
        if profile is None:
            return SandboxVerdict(False, "SANDBOX-PROC-00", "Agent not registered")

        if Capability.PROC_SUBPROCESS not in profile.capabilities \
           and Capability.PROC_SUBPROCESS_SAFE not in profile.capabilities:
            return SandboxVerdict(False, "SANDBOX-PROC-CAP",
                "Agent has no subprocess capability")

        # Strip .exe on Windows for allowlist matching
        exe_stem = Path(executable).stem.lower()
        exe_name = Path(executable).name.lower()
        if profile.proc_allowlist:
            for allowed in profile.proc_allowlist:
                al = allowed.lower()
                if exe_name == al or exe_stem == al or fnmatch(exe_name, allowed):
                    return SandboxVerdict(True, "SANDBOX-PROC-OK", "")
            return SandboxVerdict(False, "SANDBOX-PROC-NOMATCH",
                f"Executable {exe_name} not in proc allowlist")

        return SandboxVerdict(True, "SANDBOX-PROC-OK", "")

    # ── Quota 检查 ──

    def check_quota(self, agent_id: str) -> SandboxVerdict:
        profile = self._require_profile(agent_id)
        if profile is None:
            return SandboxVerdict(False, "SANDBOX-Q-00", "Agent not registered")

        with profile._lock:
            u = profile._usage
            q = profile.quotas

            # Wall time
            elapsed = time.time() - profile._start_time
            if elapsed > q.max_wall_time_s:
                return SandboxVerdict(False, "SANDBOX-Q-WALL",
                    f"Wall time {elapsed:.1f}s exceeded limit {q.max_wall_time_s}s",
                    suggestion="Increase max_wall_time_s or split work into multiple tasks")

            # Memory
            if u.memory_current_mb > q.max_memory_mb:
                return SandboxVerdict(False, "SANDBOX-Q-MEM",
                    f"Memory {u.memory_current_mb:.0f}MB exceeded limit {q.max_memory_mb}MB",
                    suggestion="Reduce batch size or release caches")

            # Soft limits → warning but allow (if soft_exceed allowed)
            warnings = []
            if elapsed > q.soft_wall_time_s:
                warnings.append(f"Soft wall time limit exceeded ({elapsed:.1f}s > {q.soft_wall_time_s}s)")
            if u.memory_current_mb > q.soft_memory_mb:
                warnings.append(f"Soft memory limit exceeded ({u.memory_current_mb:.0f}MB > {q.soft_memory_mb}MB)")

            if warnings and not q.allow_soft_exceed:
                return SandboxVerdict(False, "SANDBOX-Q-SOFT",
                    "; ".join(warnings),
                    suggestion="Request soft limit override from Supervisor")

            return SandboxVerdict(True, "SANDBOX-Q-OK",
                "; ".join(warnings) if warnings else "")

    def update_usage(self, agent_id: str, memory_mb: Optional[float] = None,
                     cpu_s: Optional[float] = None) -> None:
        """更新资源使用量 (由 Agent 或监控线程调用)."""
        profile = self._require_profile(agent_id)
        if profile is None:
            return
        with profile._lock:
            if memory_mb is not None:
                profile._usage.memory_current_mb = memory_mb
                profile._usage.memory_peak_mb = max(
                    profile._usage.memory_peak_mb, memory_mb
                )
            if cpu_s is not None:
                profile._usage.cpu_time_elapsed = cpu_s

    # ── Helpers ──

    def _require_profile(self, agent_id: str) -> Optional[SandboxProfile]:
        return self.registry.get(agent_id)

    @staticmethod
    def _glob_match(path: str, pattern: str) -> bool:
        """Cross-platform glob matching with Windows path normalization."""
        normalized = path.replace("\\", "/")
        pat = pattern.replace("\\", "/")
        return fnmatch(normalized, pat)

    @staticmethod
    def _net_match(host: str, port: int, pattern: str) -> bool:
        """Match network target against pattern like '*.example.com:443' or 'localhost:*'.
        Handles fnmatch quirk: '*.example.com' does NOT match 'example.com' —
        so we also try stripping the leading '*.' prefix."""
        if ":" in pattern:
            host_pat, port_pat = pattern.rsplit(":", 1)
        else:
            host_pat, port_pat = pattern, "*"
        port_ok = port_pat == "*" or str(port) == port_pat
        if not port_ok:
            return False
        # Standard glob match
        if fnmatch(host, host_pat):
            return True
        # Edge case: '*.example.com' should also match bare 'example.com'
        if host_pat.startswith("*.") and fnmatch(host, host_pat[2:]):
            return True
        return False

    def _audit(self, agent_id: str, event: str, detail: dict) -> None:
        self.registry._log({
            "agent_id": agent_id, "event": event, "detail": detail,
        })


# ════════════════════════════════════════════════════════════
# System Call Filter (应用层模拟 - Windows)
# ════════════════════════════════════════════════════════════

class SyscallFilter:
    """
    系统调用过滤器 — 在 subprocess.run 调用前拦截。

    不同于真正的内核 seccomp/bpf，这是应用层保护：
      - 拦截 subprocess 调用 → 检查 proc allowlist
      - 拦截文件操作 → 检查 fs allowlist/denylist
      - 拦截网络操作 → 检查 net allowlist

    对于需要真正内核隔离的场景，Phase 2 可转向 Windows Job Object
    (CREATE_BREAKAWAY_FROM_JOB) 或 WSL2 沙盒。
    """

    DANGEROUS_COMMANDS: set[str] = {
        "rm", "rmdir", "del", "format", "diskpart",
        "shutdown", "restart", "logoff", "taskkill",
        "reg", "regedit", "msconfig", "bcdedit",
        "icacls", "cacls", "takeown", "rundll32",
        "wmic", "sc", "net user", "net localgroup",
    }

    @classmethod
    def sanitize_command(cls, cmd: str) -> tuple[bool, str]:
        """检查命令是否安全。返回 (is_safe, reason)."""
        cmd_lower = cmd.strip().lower()

        for dangerous in cls.DANGEROUS_COMMANDS:
            if cmd_lower.startswith(dangerous + " ") or cmd_lower == dangerous:
                return False, f"Blocked dangerous command: {dangerous}"

        # Shell injection detection
        injection_patterns = [
            (r'`.*`', "backtick injection"),
            (r'\$\(', "command substitution"),
            (r';\s*(rm|del|shutdown)', "chained destructive command"),
            (r'\|\s*(rm|del|shutdown)', "piped destructive command"),
            (r'&{', "PowerShell script block injection"),
            (r'eval\s*\(', "eval injection"),
            (r'exec\s*\(', "exec injection"),
            (r'__import__\s*\(', "dynamic import injection"),
            (r'base64\s+-d', "base64 decode"),
            (r'FromBase64String', "PowerShell base64"),
        ]
        for pattern, desc in injection_patterns:
            if re.search(pattern, cmd):
                return False, f"Injection pattern detected: {desc}"

        return True, ""

    @classmethod
    def sanitize_python_code(cls, code: str) -> tuple[bool, str]:
        """检查 Python 代码是否安全。"""
        dangerous_calls = [
            (r'\bos\.system\s*\(', "os.system()"),
            (r'\bsubprocess\.(run|call|Popen)\s*\(', "subprocess call"),
            (r'\beval\s*\(', "eval()"),
            (r'\bexec\s*\(', "exec()"),
            (r'\bcompile\s*\(', "compile()"),
            (r'\b__import__\s*\(', "__import__()"),
            (r'\bopen\s*\([^)]*\bw[a+]?\b', "open() with write mode"),
            (r'\bos\.remove\s*\(', "os.remove()"),
            (r'\bshutil\.rmtree\s*\(', "shutil.rmtree()"),
            (r'\breload\s*\(', "reload()"),
            (r'\bsetattr\s*\([^)]*__class__', "setattr() on __class__"),
        ]
        for pattern, desc in dangerous_calls:
            if re.search(pattern, code):
                return False, f"Dangerous Python call: {desc}"
        return True, ""


# ════════════════════════════════════════════════════════════
# 一体化检查入口
# ════════════════════════════════════════════════════════════

class SandboxGate:
    """
    一体化入口 — Agent 在执行操作前调用此门控。

    用法:
        gate = SandboxGate("plan-agent")
        result = gate.gate_fs_write("E:/some/path")
        if not result.allowed:
            raise SandboxViolation(result.reason)
    """

    def __init__(self, agent_id: str, registry: Optional[SandboxRegistry] = None):
        self.agent_id = agent_id
        self.checker = CapabilityChecker(registry)

    def gate_fs_read(self, path: str) -> SandboxVerdict:
        return self.checker.check_fs_read(self.agent_id, path)

    def gate_fs_write(self, path: str) -> SandboxVerdict:
        return self.checker.check_fs_write(self.agent_id, path)

    def gate_net(self, host: str, port: int = 0) -> SandboxVerdict:
        return self.checker.check_net(self.agent_id, host, port)

    def gate_proc(self, executable: str) -> SandboxVerdict:
        return self.checker.check_proc(self.agent_id, executable)

    def gate_quota(self) -> SandboxVerdict:
        return self.checker.check_quota(self.agent_id)

    def gate_subprocess(self, cmd: str) -> SandboxVerdict:
        """完整子进程门控: 命令安全检查 + proc allowlist。"""
        # Step 1: 命令安全检查
        safe, reason = SyscallFilter.sanitize_command(cmd)
        if not safe:
            return SandboxVerdict(False, "SANDBOX-CMD-DANGER", reason,
                suggestion="Use a safer alternative or request Supervisor override")

        # Step 2: 解析可执行文件名
        exe = cmd.split()[0] if cmd.strip() else ""
        return self.checker.check_proc(self.agent_id, exe)

    def gate_python_eval(self, code: str) -> SandboxVerdict:
        """Python eval/exec 门控。"""
        safe, reason = SyscallFilter.sanitize_python_code(code)
        if not safe:
            return SandboxVerdict(False, "SANDBOX-PY-DANGER", reason)
        return SandboxVerdict(True, "SANDBOX-PY-OK", "")

    def summary(self) -> dict:
        """返回当前 Agent 的沙盒状态摘要。"""
        profile = self.checker.registry.get(self.agent_id)
        if profile is None:
            return {"error": "Agent not registered"}
        return {
            "agent_id": self.agent_id,
            "agent_type": profile.agent_type,
            "capabilities": [c.value for c in profile.capabilities],
            "quotas": {
                "memory_max_mb": profile.quotas.max_memory_mb,
                "wall_time_max_s": profile.quotas.max_wall_time_s,
            },
            "fs_allowlist_count": len(profile.fs_allowlist),
            "fs_denylist_count": len(profile.fs_denylist),
            "net_allowlist_count": len(profile.net_allowlist),
            "proc_allowlist_count": len(profile.proc_allowlist),
        }


class SandboxViolation(Exception):
    """沙盒违规异常 — Agent 试图执行被禁止的操作。"""
    def __init__(self, verdict: SandboxVerdict):
        self.verdict = verdict
        super().__init__(f"Sandbox violation: {verdict.rule_id} - {verdict.reason}")


# ════════════════════════════════════════════════════════════
# 测试
# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=== Security Sandbox Self-Test ===\n")

    registry = get_registry()

    # Register agents from presets
    for atype in ["plan", "audit", "executor", "concierge"]:
        registry.get_or_preset(f"test-{atype}", atype)

    tests_passed = 0
    tests_total = 0

    def expect(verdict: SandboxVerdict, expected: bool, label: str):
        global tests_passed, tests_total
        tests_total += 1
        ok = verdict.allowed == expected
        if ok:
            tests_passed += 1
            print(f"  ✅ {label}")
        else:
            print(f"  ❌ {label}: expected allowed={expected}, got {verdict.allowed} ({verdict.reason})")

    # Plan-Agent tests
    gate_p = SandboxGate("test-plan")
    expect(gate_p.gate_fs_read("E:/AI_Workspace/MSS-AI/project/file.py"), True,
           "Plan: read project file")
    expect(gate_p.gate_fs_read("E:/AI_Workspace/MSS-AI/project/README.md"), True,
           "Plan: read project README")
    expect(gate_p.gate_fs_read("E:/AI_Workspace/MSS-AI/secrets/key.pem"), False,
           "Plan: read secrets dir (denylist)")
    expect(gate_p.gate_fs_write("E:/AI_Workspace/MSS-AI/project/output.txt"), True,
           "Plan: write project file")
    expect(gate_p.gate_net("github.com", 443), True,
           "Plan: GitHub API")
    expect(gate_p.gate_net("evil.com", 6666), False,
           "Plan: unknown host blocked")
    expect(gate_p.gate_proc("python.exe"), True,
           "Plan: python in allowlist")
    expect(gate_p.gate_proc("hack.exe"), False,
           "Plan: unknown executable blocked")
    expect(gate_p.gate_subprocess("git status"), True,
           "Plan: safe git command")
    expect(gate_p.gate_subprocess("rm -rf /"), False,
           "Plan: dangerous command blocked")

    # Audit-Agent tests
    gate_a = SandboxGate("test-audit")
    expect(gate_a.gate_fs_write("E:/AI_Workspace/MSS-AI/project/output.txt"), False,
           "Audit: cannot write (no write capability)")
    expect(gate_a.gate_proc("python.exe"), False,
           "Audit: cannot run subprocess")

    # Concierge tests
    gate_c = SandboxGate("test-concierge")
    expect(gate_c.gate_fs_read("E:/AI_Workspace/file.py"), False,
           "Concierge: cannot read files (denylist **)")
    expect(gate_c.gate_net("api.openai.com", 443), True,
           "Concierge: OpenAI API allowed")
    expect(gate_c.gate_net("random-site.com", 443), False,
           "Concierge: unknown site blocked")

    # Quota tests
    gate_p.checker.update_usage("test-plan", memory_mb=800)
    expect(gate_p.gate_quota(), False,
           "Plan: soft memory limit exceeded")

    # Proc injection tests
    expect(gate_p.gate_subprocess("ls | rm -rf"), False,
           "Plan: piped destructive command blocked")
    expect(gate_p.gate_subprocess("eval('os.system(\"rm -rf\")')"), False,
           "Plan: eval injection blocked")

    print(f"\n=== {tests_passed}/{tests_total} passed ===")
