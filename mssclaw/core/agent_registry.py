"""
mssclaw/core/agent_registry.py

全局 Agent 注册表 + 状态持久化.

解决 P2 两个问题:
  1. 无全局 Agent 注册 — 每个 PlanAgent 独立 _agent_registry
  2. 无持久化状态 — 重启丢失所有 Agent 状态

特性:
  - Singleton 全局注册 (所有 Agent 自动发现)
  - SQLite/JSON 双持久化
  - Agent 心跳 + 健康监测
  - 热恢复 (重启后自动恢复 Agent 状态)
"""
import json, time, sqlite3, threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Callable


@dataclass
class AgentEntry:
    """Agent 注册条目."""
    name: str
    role: str
    capabilities: list = field(default_factory=list)
    status: str = "idle"       # idle/busy/isolated/offline
    load: int = 0               # 当前任务数
    total_tasks: int = 0        # 累计完成任务
    total_failures: int = 0
    last_heartbeat: float = field(default_factory=time.time)
    registered_at: float = field(default_factory=time.time)


class AgentRegistry:
    """全局 Agent 注册表 — Singleton."""

    _instance: Optional["AgentRegistry"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: str = "data/agent_registry.db"):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._db_path = db_path
        self._entries: dict[str, AgentEntry] = {}
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """初始化 SQLite 持久化."""
        path = Path(self._db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                name TEXT PRIMARY KEY,
                role TEXT,
                capabilities TEXT,
                status TEXT DEFAULT 'offline',
                load INTEGER DEFAULT 0,
                total_tasks INTEGER DEFAULT 0,
                total_failures INTEGER DEFAULT 0,
                last_heartbeat REAL,
                registered_at REAL
            )
        """)
        self._conn.commit()
        self._load_from_db()

    def _load_from_db(self):
        """从数据库恢复 Agent 状态."""
        rows = self._conn.execute("SELECT * FROM agents").fetchall()
        for row in rows:
            name, role, caps_str, status, load, tt, tf, hb, reg = row
            self._entries[name] = AgentEntry(
                name=name, role=role,
                capabilities=json.loads(caps_str) if caps_str else [],
                status=status, load=load,
                total_tasks=tt, total_failures=tf,
                last_heartbeat=hb or time.time(),
                registered_at=reg or time.time(),
            )

    def _save_to_db(self, entry: AgentEntry):
        caps = json.dumps(entry.capabilities)
        self._conn.execute("""
            INSERT OR REPLACE INTO agents 
            (name, role, capabilities, status, load, total_tasks, total_failures, last_heartbeat, registered_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (entry.name, entry.role, caps, entry.status, entry.load,
              entry.total_tasks, entry.total_failures, entry.last_heartbeat, entry.registered_at))
        self._conn.commit()

    # ═══ Registration ═══

    def register(self, name: str, role: str, capabilities: list) -> AgentEntry:
        """注册 Agent."""
        entry = AgentEntry(name=name, role=role, capabilities=capabilities)
        with self._lock:
            self._entries[name] = entry
            self._save_to_db(entry)
        return entry

    def unregister(self, name: str):
        with self._lock:
            self._entries.pop(name, None)
            self._conn.execute("DELETE FROM agents WHERE name = ?", (name,))
            self._conn.commit()

    def get(self, name: str) -> Optional[AgentEntry]:
        return self._entries.get(name)

    def get_capabilities(self, name: str) -> list:
        entry = self._entries.get(name)
        return entry.capabilities if entry else []

    def list_all(self) -> dict[str, AgentEntry]:
        return dict(self._entries)

    def find_by_capability(self, capability: str) -> list[str]:
        return [n for n, e in self._entries.items() if capability in e.capabilities]

    # ═══ Heartbeat + Status ═══

    def heartbeat(self, name: str):
        entry = self._entries.get(name)
        if entry:
            entry.last_heartbeat = time.time()
            with self._lock:
                self._save_to_db(entry)

    def set_status(self, name: str, status: str):
        entry = self._entries.get(name)
        if entry:
            entry.status = status
            with self._lock:
                self._save_to_db(entry)

    def record_task(self, name: str, success: bool):
        entry = self._entries.get(name)
        if entry:
            entry.total_tasks += 1
            if not success:
                entry.total_failures += 1
            entry.load -= 1
            status = "idle" if entry.load <= 0 else "busy"
            entry.status = status
            with self._lock:
                self._save_to_db(entry)

    def assign_task(self, name: str):
        entry = self._entries.get(name)
        if entry:
            entry.load += 1
            entry.status = "busy"
            with self._lock:
                self._save_to_db(entry)

    def get_offline_agents(self, timeout: float = 60.0) -> list[str]:
        now = time.time()
        return [n for n, e in self._entries.items() if now - e.last_heartbeat > timeout]

    # ═══ Query ═══

    def status(self) -> dict:
        entries = self._entries
        return {
            "total": len(entries),
            "online": sum(1 for e in entries.values() if e.status != "offline"),
            "offline": sum(1 for e in entries.values() if e.status == "offline"),
            "busy": sum(1 for e in entries.values() if e.status == "busy"),
            "by_role": {r: [e.name for e in entries.values() if e.role == r]
                        for r in set(e.role for e in entries.values())},
        }

    def snapshot(self) -> list[dict]:
        return [{
            "name": e.name, "role": e.role, "status": e.status,
            "capabilities": e.capabilities, "load": e.load,
            "success_rate": round(1 - e.total_failures / max(e.total_tasks, 1), 2),
            "last_heartbeat": e.last_heartbeat,
        } for e in self._entries.values()]


# ════════════════════════════════════════════════════════════
# Agent 隔离器 (原 agent_isolator.py, 已合并)
# ════════════════════════════════════════════════════════════

class IsolatorState(Enum):
    CLOSED = "closed"
    HALF_OPEN = "half_open"
    OPEN = "open"


@dataclass
class AgentCircuitBreaker:
    """单个 Agent 熔断器."""
    agent_name: str
    failure_threshold: int = 3
    recovery_timeout: float = 30.0
    success_threshold: int = 2

    state: IsolatorState = IsolatorState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    last_state_change: float = field(default_factory=time.time)
    total_failures: int = 0
    total_successes: int = 0

    def record_success(self):
        self.total_successes += 1
        if self.state == IsolatorState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = IsolatorState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.last_state_change = time.time()
        elif self.state == IsolatorState.CLOSED:
            self.failure_count = 0

    def record_failure(self):
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.state == IsolatorState.HALF_OPEN:
            self.state = IsolatorState.OPEN
            self.last_state_change = time.time()
        elif self.state == IsolatorState.CLOSED and self.failure_count >= self.failure_threshold:
            self.state = IsolatorState.OPEN
            self.last_state_change = time.time()

    def try_recover(self) -> bool:
        if self.state == IsolatorState.OPEN:
            if time.time() - self.last_state_change >= self.recovery_timeout:
                self.state = IsolatorState.HALF_OPEN
                self.success_count = 0
                self.last_state_change = time.time()
                return True
        return False

    @property
    def is_isolated(self) -> bool:
        return self.state == IsolatorState.OPEN


class AgentIsolator:
    """Agent 隔离器 — 级联故障保护."""

    def __init__(self):
        self._breakers: dict[str, AgentCircuitBreaker] = {}
        self._fallbacks: dict[str, str] = {}
        self._lock = threading.Lock()
        self._alert_callback: Optional[Callable] = None

    def register(self, agent_name: str, failure_threshold: int = 3,
                 recovery_timeout: float = 30.0, fallback: str = ""):
        with self._lock:
            self._breakers[agent_name] = AgentCircuitBreaker(
                agent_name=agent_name, failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout)
            if fallback:
                self._fallbacks[agent_name] = fallback

    def allow(self, agent_name: str) -> bool:
        with self._lock:
            breaker = self._breakers.get(agent_name)
            if not breaker:
                return True
            breaker.try_recover()
            return not breaker.is_isolated

    def record(self, agent_name: str, success: bool):
        with self._lock:
            breaker = self._breakers.get(agent_name)
            if not breaker:
                return
            if success:
                breaker.record_success()
            else:
                breaker.record_failure()
                if breaker.is_isolated and self._alert_callback:
                    self._alert_callback(agent_name, breaker)

    def get_fallback(self, agent_name: str) -> Optional[str]:
        return self._fallbacks.get(agent_name)

    def isolate(self, agent_name: str, reason: str = ""):
        with self._lock:
            breaker = self._breakers.get(agent_name)
            if breaker:
                breaker.state = IsolatorState.OPEN
                breaker.last_state_change = time.time()

    def release(self, agent_name: str):
        with self._lock:
            breaker = self._breakers.get(agent_name)
            if breaker:
                breaker.state = IsolatorState.CLOSED
                breaker.failure_count = 0
                breaker.success_count = 0

    def on_alert(self, callback: Callable):
        self._alert_callback = callback

    def status(self, agent_name: str = "") -> dict:
        if agent_name:
            b = self._breakers.get(agent_name)
            return self._breaker_status(b) if b else {}
        return {n: self._breaker_status(b) for n, b in self._breakers.items()}

    def _breaker_status(self, b: AgentCircuitBreaker) -> dict:
        return {
            "state": b.state.value, "failures": b.failure_count,
            "total_failures": b.total_failures, "total_successes": b.total_successes,
            "isolated": b.is_isolated, "last_failure": b.last_failure_time,
            "last_change": b.last_state_change,
        }

    def cascade_risk(self) -> dict:
        isolated = [n for n, b in self._breakers.items() if b.is_isolated]
        half_open = [n for n, b in self._breakers.items() if b.state == IsolatorState.HALF_OPEN]
        failing = [n for n, b in self._breakers.items() if b.failure_count >= 1]
        return {
            "isolated": isolated, "half_open": half_open, "failing": failing,
            "cascade_warning": len(isolated) >= 2 or len(failing) >= 3,
        }
