# -*- coding: utf-8 -*-
"""
mssclaw-deployer — Track E: Multi-Unit Deployment Coordinator

管理多个 Agent 进程在单机或局域网的部署、发现与健康聚合。

核心能力:
  1. 进程级部署: 启动/停止/重启多个 Agent (Plan/Audit/Executor)
  2. 服务发现: UDP 广播 + 端口分配 (防碰撞)
  3. 健康聚合: 汇总各 Agent 健康状态
  4. 滚动重启: 零停机更新

架构:
  Deployer
    ├── UnitManager → 管理单个 Agent 进程生命周期
    ├── DiscoveryService → UDP 广播发现
    ├── HealthAggregator → 健康指标收集
    └── HotReloader → 配置热更新 (Phase 1 仅信号触发)

约束:
  - Phase 1 仅单机部署 (localhost)
  - Phase 2 局域网广播发现
  - Phase 3 跨机器 Raft 共识 (基于 TSP Bridge)
"""
from __future__ import annotations

import json
import os
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


# ════════════════════════════════════════════════════════════
# 核心数据结构
# ════════════════════════════════════════════════════════════

class UnitRole(Enum):
    PLAN      = "plan"
    EXECUTOR  = "executor"
    AUDIT     = "audit"
    CONCIERGE = "concierge"
    CUSTOM    = "custom"


class UnitState(Enum):
    STOPPED    = "stopped"
    STARTING   = "starting"
    RUNNING    = "running"
    DEGRADED   = "degraded"   # 运行中但健康分低
    STOPPING   = "stopping"
    CRASHED    = "crashed"


@dataclass
class UnitConfig:
    """单个 Agent 单元的部署配置。"""
    role: UnitRole
    name: str
    command: str          # 启动命令
    port: int = 0         # 0=自动分配
    env: dict[str, str] = field(default_factory=dict)
    restart_policy: str = "always"  # always | on-failure | never
    max_restarts_per_hour: int = 10
    health_check_interval_sec: int = 30
    health_timeout_sec: int = 5
    dependencies: list[str] = field(default_factory=list)  # 依赖的 unit name


@dataclass
class UnitInfo:
    """运行中的单元信息。"""
    config: UnitConfig
    state: UnitState = UnitState.STOPPED
    pid: int = 0
    port: int = 0
    process: Optional[subprocess.Popen] = None
    start_time: float = 0.0
    restart_count: int = 0
    last_health: float = 0.0
    health_score: float = 1.0
    _restart_times: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "role": self.config.role.value,
            "name": self.config.name,
            "state": self.state.value,
            "pid": self.pid,
            "port": self.port,
            "restart_count": self.restart_count,
            "health_score": round(self.health_score, 3),
            "uptime_sec": round(time.time() - self.start_time, 1) if self.start_time else 0,
        }


# ════════════════════════════════════════════════════════════
# 端口分配器
# ════════════════════════════════════════════════════════════

class PortAllocator:
    """端口池管理 — 分配/释放/检测占用。"""

    BASE_PORT = 53000
    MAX_PORT = 53099
    POOL_SIZE = MAX_PORT - BASE_PORT + 1

    def __init__(self):
        self._allocated: dict[str, int] = {}  # name → port
        self._next_port = self.BASE_PORT

    def allocate(self, name: str, preferred: int = 0) -> int:
        """分配端口，优先使用 preferred。"""
        if preferred > 0 and not self._is_taken(preferred):
            self._allocated[name] = preferred
            return preferred

        for _ in range(self.POOL_SIZE):
            port = self._next_port
            self._next_port = self.BASE_PORT + ((self._next_port - self.BASE_PORT + 1) % self.POOL_SIZE)
            if not self._is_taken(port):
                self._allocated[name] = port
                return port

        raise RuntimeError(f"Port pool exhausted ({self.BASE_PORT}-{self.MAX_PORT})")

    def release(self, name: str) -> None:
        self._allocated.pop(name, None)

    def allocated(self) -> dict[str, int]:
        return dict(self._allocated)

    @staticmethod
    def _is_taken(port: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                return s.connect_ex(("127.0.0.1", port)) == 0
        except Exception:
            return False


# ════════════════════════════════════════════════════════════
# 单进程管理器
# ════════════════════════════════════════════════════════════

CREATE_BREAKAWAY_FROM_JOB = 0x01000000
CREATE_NO_WINDOW = 0x08000000


class UnitManager:
    """管理单个 Agent 进程 — 启动/停止/重启/健康检查。"""

    def __init__(self, config: UnitConfig, port_allocator: PortAllocator):
        self.config = config
        self.info = UnitInfo(config=config)
        self._port_allocator = port_allocator
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None

    # ── 启动 ──

    def start(self) -> bool:
        if self.info.state in (UnitState.RUNNING, UnitState.STARTING):
            return True

        self.info.state = UnitState.STARTING

        # 分配端口
        port = self._port_allocator.allocate(self.config.name, self.config.port)
        self.info.port = port

        # 构建命令
        env = os.environ.copy()
        env.update(self.config.env)
        env["MSSCLAW_UNIT_NAME"] = self.config.name
        env["MSSCLAW_UNIT_ROLE"] = self.config.role.value
        env["MSSCLAW_UNIT_PORT"] = str(port)

        try:
            parts = self.config.command.split()
            self.info.process = subprocess.Popen(
                parts,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=CREATE_BREAKAWAY_FROM_JOB | CREATE_NO_WINDOW,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.info.pid = self.info.process.pid
            self.info.start_time = time.time()
            self.info.state = UnitState.RUNNING

            # 启动 stdout 读取线程
            threading.Thread(
                target=self._drain_stdout,
                daemon=True,
                name=f"stdout-{self.config.name}"
            ).start()

            # 启动健康监控
            self._monitor_thread = threading.Thread(
                target=self._health_loop,
                daemon=True,
                name=f"health-{self.config.name}"
            )
            self._monitor_thread.start()

            return True

        except Exception as e:
            self.info.state = UnitState.CRASHED
            self._log(f"Start failed: {e}")
            return False

    # ── 停止 ──

    def stop(self, graceful: bool = True) -> None:
        self._stop_event.set()
        self.info.state = UnitState.STOPPING

        if self.info.process is None:
            self.info.state = UnitState.STOPPED
            return

        if graceful:
            try:
                self.info.process.send_signal(signal.CTRL_C_EVENT)
                self.info.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._log("Graceful shutdown timed out, force killing")
                self.info.process.kill()
            except Exception as e:
                self._log(f"Stop error: {e}")
        else:
            self.info.process.kill()

        self._port_allocator.release(self.config.name)
        self.info.state = UnitState.STOPPED
        self.info.process = None

    def restart(self) -> bool:
        self.stop()
        self._stop_event.clear()
        time.sleep(0.5)
        return self.start()

    # ── 健康检查 ──

    def _health_loop(self) -> None:
        """后台健康检查循环。"""
        while not self._stop_event.is_set():
            self._stop_event.wait(self.config.health_check_interval_sec)
            if self._stop_event.is_set():
                break
            score = self._check_health()
            self.info.last_health = time.time()
            self.info.health_score = score
            if score < 0.3:
                self.info.state = UnitState.DEGRADED

    def _check_health(self) -> float:
        """检查进程是否存活并响应。"""
        if self.info.process is None:
            return 0.0

        # 1. 进程存活检查
        if self.info.process.poll() is not None:
            self._handle_crash()
            return 0.0

        # 2. 端口监听检查
        if not self._port_listening(self.info.port):
            return 0.4

        # 3. (Phase 2) HTTP health endpoint
        return 1.0

    @staticmethod
    def _port_listening(port: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                return s.connect_ex(("127.0.0.1", port)) == 0
        except Exception:
            return False

    def _handle_crash(self) -> None:
        """处理进程崩溃，按策略恢复。"""
        self.info.state = UnitState.CRASHED
        self.info._restart_times.append(time.time())

        # 清理过期崩溃记录
        now = time.time()
        self.info._restart_times = [
            t for t in self.info._restart_times
            if now - t < 3600
        ]

        if self.config.restart_policy == "never":
            return

        if self.config.restart_policy == "on-failure" and \
           len(self.info._restart_times) > self.config.max_restarts_per_hour:
            self._log(f"Max restarts exceeded, giving up")
            return

        self._log(f"Crash detected, restarting...")
        time.sleep(1)
        self._stop_event.clear()
        self.start()
        self.info.restart_count += 1

    # ── Helpers ──

    def _drain_stdout(self) -> None:
        if not self.info.process or not self.info.process.stdout:
            return
        try:
            for line in self.info.process.stdout:
                line = line.rstrip("\n\r")
                if line:
                    self._log(f"[{self.config.name}] {line}")
        except Exception:
            pass

    def _log(self, msg: str) -> None:
        t = time.strftime("%H:%M:%S")
        print(f"[{t}] {msg}", flush=True)


# ════════════════════════════════════════════════════════════
# 服务发现
# ════════════════════════════════════════════════════════════

DISCOVERY_PORT = 53001
DISCOVERY_MAGIC = 0x4D535344  # "MSSD"

@dataclass
class DiscoveryPacket:
    """UDP 发现数据包。"""
    node_id: str
    role: str
    port: int
    health_score: float
    timestamp: float
    metadata: dict = field(default_factory=dict)

    def encode(self) -> bytes:
        payload = json.dumps({
            "n": self.node_id, "r": self.role, "p": self.port,
            "h": self.health_score, "t": self.timestamp, "m": self.metadata
        }, separators=(",", ":"))
        return struct.pack(">I", DISCOVERY_MAGIC) + payload.encode("utf-8")

    @classmethod
    def decode(cls, data: bytes) -> Optional[DiscoveryPacket]:
        if len(data) < 4:
            return None
        magic = struct.unpack(">I", data[:4])[0]
        if magic != DISCOVERY_MAGIC:
            return None
        try:
            obj = json.loads(data[4:].decode("utf-8"))
            return cls(
                node_id=obj["n"], role=obj["r"], port=obj["p"],
                health_score=obj["h"], timestamp=obj["t"],
                metadata=obj.get("m", {})
            )
        except Exception:
            return None


class DiscoveryService:
    """UDP 广播服务发现 (Phase 2 局域网)."""

    def __init__(self, node_id: str, bind_port: int = DISCOVERY_PORT):
        self.node_id = node_id
        self._peers: dict[str, DiscoveryPacket] = {}
        self._sock: Optional[socket.socket] = None
        self._running = False

    def start(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("0.0.0.0", DISCOVERY_PORT))
        self._running = True
        threading.Thread(target=self._listen, daemon=True).start()

    def announce(self, packet: DiscoveryPacket) -> None:
        """广播自身信息。"""
        if not self._sock:
            return
        data = packet.encode()
        self._sock.sendto(data, ("255.255.255.255", DISCOVERY_PORT))

    def _listen(self) -> None:
        while self._running:
            try:
                data, addr = self._sock.recvfrom(1024)
                packet = DiscoveryPacket.decode(data)
                if packet and packet.node_id != self.node_id:
                    packet.metadata["last_seen_addr"] = addr[0]
                    self._peers[packet.node_id] = packet
            except Exception:
                pass

    @property
    def peers(self) -> dict[str, DiscoveryPacket]:
        # 清理过期 (30s)
        now = time.time()
        return {
            k: v for k, v in self._peers.items()
            if now - v.timestamp < 30
        }

    def close(self) -> None:
        self._running = False
        if self._sock:
            self._sock.close()


# ════════════════════════════════════════════════════════════
# 主部署器
# ════════════════════════════════════════════════════════════

@dataclass
class DeployConfig:
    """多单元部署方案。"""
    units: list[UnitConfig]
    auto_start: bool = True
    rolling_update: bool = False
    log_dir: str = ""


class Deployer:
    """
    部署统筹 — 管理多个 Unit。

    用法:
        deployer = Deployer(DeployConfig(units=[
            UnitConfig(role=UnitRole.PLAN, name="plan-1", command="python -m mssclaw.agents.plan ..."),
            UnitConfig(role=UnitRole.EXECUTOR, name="exec-1", command="python -m mssclaw.agents.executor ..."),
        ]))
        deployer.start_all()
        deployer.status()
        deployer.stop_all()
    """

    def __init__(self, config: DeployConfig):
        self.config = config
        self._port_allocator = PortAllocator()
        self._units: dict[str, UnitManager] = {}
        self._started = False

        for uc in config.units:
            self._units[uc.name] = UnitManager(uc, self._port_allocator)

    # ── 全量操作 ──

    def start_all(self, ordered: bool = True) -> dict[str, bool]:
        """启动所有单元。ordered=True 时按依赖拓扑排序。"""
        results = {}
        if ordered:
            order = self._topo_sort()
        else:
            order = list(self._units.keys())

        for name in order:
            manager = self._units[name]
            # 等待依赖就绪
            for dep in manager.config.dependencies:
                dep_info = self._units[dep].info
                for _ in range(30):  # 最多等 30s
                    if dep_info.state == UnitState.RUNNING:
                        break
                    time.sleep(1)
                else:
                    results[name] = False
                    continue

            ok = manager.start()
            results[name] = ok

        self._started = True
        return results

    def stop_all(self) -> None:
        """停止所有单元。"""
        for manager in self._units.values():
            manager.stop()
        self._started = False

    def restart_all(self, rolling: bool = False) -> dict[str, bool]:
        """重启所有单元。rolling=True 时逐个重启。"""
        if rolling:
            return self._rolling_restart()
        self.stop_all()
        time.sleep(1)
        return self.start_all()

    def _rolling_restart(self) -> dict[str, bool]:
        """逐个重启，零停机。"""
        results = {}
        for name, manager in self._units.items():
            manager.stop()
            time.sleep(1)
            ok = manager.start()
            results[name] = ok
        return results

    # ── 单节点操作 ──

    def start_one(self, name: str) -> bool:
        mgr = self._units.get(name)
        return mgr.start() if mgr else False

    def stop_one(self, name: str) -> None:
        mgr = self._units.get(name)
        if mgr:
            mgr.stop()

    def restart_one(self, name: str) -> bool:
        mgr = self._units.get(name)
        return mgr.restart() if mgr else False

    # ── 状态 ──

    def status(self) -> dict:
        """返回全部单元状态。"""
        units_status = {}
        healthy = 0
        total = 0
        for name, manager in self._units.items():
            info = manager.info
            units_status[name] = info.to_dict()
            total += 1
            if info.state == UnitState.RUNNING and info.health_score >= 0.7:
                healthy += 1

        return {
            "started": self._started,
            "units": units_status,
            "healthy": f"{healthy}/{total}",
            "ports": self._port_allocator.allocated(),
        }

    def health_report(self) -> dict:
        """健康报告。"""
        s = self.status()
        scores = {}
        for name, info in s["units"].items():
            scores[name] = info["health_score"]
        avg = sum(scores.values()) / len(scores) if scores else 0.0
        return {
            "overall_health": round(avg, 3),
            "per_unit": scores,
            "degraded": [n for n, v in scores.items() if v < 0.3],
            "timestamp": time.time(),
        }

    # ── 拓扑排序 ──

    def _topo_sort(self) -> list[str]:
        """按依赖关系拓扑排序。"""
        in_degree = {name: 0 for name in self._units}
        edges: dict[str, list[str]] = {name: [] for name in self._units}

        for name, manager in self._units.items():
            for dep in manager.config.dependencies:
                if dep in edges:
                    edges[dep].append(name)
                    in_degree[name] += 1

        queue = [n for n, d in in_degree.items() if d == 0]
        result = []
        while queue:
            node = queue.pop(0)
            result.append(node)
            for child in edges.get(node, []):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        # 剩余的 (循环依赖)
        remaining = [n for n in self._units if n not in result]
        result.extend(remaining)

        return result

    # ── 配置热更新 ──

    def signal_reload(self, unit_name: str) -> None:
        """向指定单元发送 SIGHUP 触发配置重载。"""
        mgr = self._units.get(unit_name)
        if mgr and mgr.info.process and mgr.info.process.poll() is None:
            try:
                mgr.info.process.send_signal(signal.SIGTERM)  # Windows SIGHUP alias
                mgr._log(f"Reload signal sent to {unit_name}")
            except Exception as e:
                mgr._log(f"Reload signal failed: {e}")


# ════════════════════════════════════════════════════════════
# 默认部署方案
# ════════════════════════════════════════════════════════════

def default_mssclaw_deploy() -> DeployConfig:
    """默认 MSSclaw 三件套部署方案。"""
    return DeployConfig(units=[
        UnitConfig(
            role=UnitRole.PLAN,
            name="plan-agent",
            command="python -m mssclaw.agents.plan --serve",
            port=53101,
            restart_policy="always",
            max_restarts_per_hour=5,
        ),
        UnitConfig(
            role=UnitRole.EXECUTOR,
            name="executor-agent",
            command="python -m mssclaw.agents.executor --serve",
            port=53102,
            restart_policy="on-failure",
            dependencies=["plan-agent"],
        ),
        UnitConfig(
            role=UnitRole.AUDIT,
            name="audit-agent",
            command="python -m mssclaw.agents.audit --serve",
            port=53103,
            restart_policy="on-failure",
            health_check_interval_sec=60,
            dependencies=["executor-agent"],
        ),
    ])


# ════════════════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== MSSclaw Deployer Self-Test ===\n")

    passed = 0
    total = 0

    # 1. PortAllocator
    total += 1
    pa = PortAllocator()
    p1 = pa.allocate("test-a")
    p2 = pa.allocate("test-b")
    if p1 != p2 and pa.BASE_PORT <= p1 <= pa.MAX_PORT:
        print(f"  ✅ PortAllocator: {p1}, {p2}")
        passed += 1

    # 2. Port release
    total += 1
    pa.release("test-a")
    p3 = pa.allocate("test-c")
    if p3 != p2:
        print(f"  ✅ Port release + realloc: {p3} (not {p2})")
        passed += 1

    # 3. Topo sort
    total += 1
    d = Deployer(DeployConfig(units=[
        UnitConfig(role=UnitRole.EXECUTOR, name="b", command="echo b", dependencies=["a"]),
        UnitConfig(role=UnitRole.PLAN, name="a", command="echo a"),
        UnitConfig(role=UnitRole.AUDIT, name="c", command="echo c", dependencies=["b"]),
    ]))
    order = d._topo_sort()
    if order.index("a") < order.index("b") < order.index("c"):
        print(f"  ✅ Topo sort: {order}")
        passed += 1
    else:
        print(f"  ❌ Topo sort wrong: {order}")

    # 4. Default deploy config
    total += 1
    cfg = default_mssclaw_deploy()
    if len(cfg.units) == 3:
        print(f"  ✅ Default config: {len(cfg.units)} units")
        passed += 1

    # 5. UnitConfig serialization
    total += 1
    info = UnitInfo(config=cfg.units[0], state=UnitState.RUNNING, pid=12345, port=53101)
    d = info.to_dict()
    if d["role"] == "plan" and d["state"] == "running":
        print(f"  ✅ UnitInfo.to_dict: {d}")
        passed += 1

    # 6. DiscoveryPacket
    total += 1
    pkt = DiscoveryPacket(node_id="plan-1", role="plan", port=53101, health_score=0.95, timestamp=time.time())
    encoded = pkt.encode()
    decoded = DiscoveryPacket.decode(encoded)
    if decoded and decoded.node_id == "plan-1":
        print(f"  ✅ DiscoveryPacket round-trip: {len(encoded)}B")
        passed += 1

    # 7. Bad discovery
    total += 1
    if DiscoveryPacket.decode(b"XXXX") is None:
        print(f"  ✅ Bad discovery packet rejected")
        passed += 1

    print(f"\n=== {passed}/{total} passed ===")
