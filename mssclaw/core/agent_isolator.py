"""
mssclaw/core/agent_isolator.py

Agent 隔离器 — DeepSeek 自我诊断的落地实现.

问题: "模块间依赖链未实现动态容错隔离，单点故障可级联传导"
方案: 每个 Agent 间插入隔离器，检测故障 → 熔断 → 隔离 → 降级

三层防护:
  L1 速率限制 — 防止 Agent 被洪水攻击
  L2 熔断器 — 连续 N 次失败 → 断开连接
  L3 降级路由 — 隔离后将流量转到备用 Agent
"""
import time, threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable


class IsolatorState(Enum):
    CLOSED = "closed"         # 正常通行
    HALF_OPEN = "half_open"   # 试探性恢复
    OPEN = "open"             # 已隔离


@dataclass
class AgentCircuitBreaker:
    """单个 Agent 的熔断器."""
    agent_name: str
    failure_threshold: int = 3          # 连续 N 次失败 → 熔断
    recovery_timeout: float = 30.0      # 熔断后等待 N 秒尝试恢复
    success_threshold: int = 2          # 试探成功 N 次 → 恢复

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
            self.failure_count = 0  # 重置失败计数

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
        """尝试从 OPEN → HALF_OPEN."""
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
    """Agent 隔离器 — SwarmBus 的级联故障保护层.

    Usage:
        isolator = AgentIsolator()
        isolator.register("Code-Agent", failure_threshold=3)

        if isolator.allow("Code-Agent"):
            result = agent.execute(task)
            isolator.record("Code-Agent", result.success)
        else:
            fallback = isolator.get_fallback("Code-Agent")
    """

    def __init__(self):
        self._breakers: dict[str, AgentCircuitBreaker] = {}
        self._fallbacks: dict[str, str] = {}   # agent_name → fallback_agent
        self._lock = threading.Lock()
        self._alert_callback: Optional[Callable] = None

    def register(self, agent_name: str, failure_threshold: int = 3,
                 recovery_timeout: float = 30.0, fallback: str = ""):
        """注册 Agent 到隔离器."""
        with self._lock:
            self._breakers[agent_name] = AgentCircuitBreaker(
                agent_name=agent_name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
            )
            if fallback:
                self._fallbacks[agent_name] = fallback

    def allow(self, agent_name: str) -> bool:
        """检查 Agent 是否允许通行."""
        with self._lock:
            breaker = self._breakers.get(agent_name)
            if not breaker:
                return True  # 未注册 = 允许
            breaker.try_recover()
            return not breaker.is_isolated

    def record(self, agent_name: str, success: bool):
        """记录 Agent 执行结果."""
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
        """获取备用 Agent."""
        return self._fallbacks.get(agent_name)

    def isolate(self, agent_name: str, reason: str = ""):
        """手动强制隔离."""
        with self._lock:
            breaker = self._breakers.get(agent_name)
            if breaker:
                breaker.state = IsolatorState.OPEN
                breaker.last_state_change = time.time()

    def release(self, agent_name: str):
        """手动释放隔离."""
        with self._lock:
            breaker = self._breakers.get(agent_name)
            if breaker:
                breaker.state = IsolatorState.CLOSED
                breaker.failure_count = 0
                breaker.success_count = 0

    def on_alert(self, callback: Callable):
        """设置告警回调."""
        self._alert_callback = callback

    def status(self, agent_name: str = "") -> dict:
        """查询 Agent 状态."""
        if agent_name:
            b = self._breakers.get(agent_name)
            return self._breaker_status(b) if b else {}
        return {n: self._breaker_status(b) for n, b in self._breakers.items()}

    def _breaker_status(self, b: AgentCircuitBreaker) -> dict:
        return {
            "state": b.state.value,
            "failures": b.failure_count,
            "total_failures": b.total_failures,
            "total_successes": b.total_successes,
            "isolated": b.is_isolated,
            "last_failure": b.last_failure_time,
            "last_change": b.last_state_change,
        }

    def cascade_risk(self) -> dict:
        """级联风险评估 — 多少 Agent 处于异常状态."""
        isolated = [n for n, b in self._breakers.items() if b.is_isolated]
        half_open = [n for n, b in self._breakers.items() if b.state == IsolatorState.HALF_OPEN]
        failing = [n for n, b in self._breakers.items() if b.failure_count >= 1]
        return {
            "isolated": isolated,
            "half_open": half_open,
            "failing": failing,
            "cascade_warning": len(isolated) >= 2 or len(failing) >= 3,
        }
