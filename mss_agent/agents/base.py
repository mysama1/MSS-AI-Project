"""
MSSclaw BaseAgent — 所有专项 Agent 的基类.

每个 Agent 携带：
  - 六公理内核 (immutable)
  - 热税预算 (heat_tax)
  - Δ 维持条件 (delta)
  - 守卫引擎 (guardian)
  - 规范场接入 (norm_field)
  - SwarmNode 注册
  - AgentMetrics 上报
"""
from __future__ import annotations

import json
import os
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

# MSS-Agent 已有核心
from ..core.heat_tax import HeatTaxBudget, HeatTaxLevel
from ..core.delta import DeltaProtocol
from ..core.guardian_engine import GuardianEngine
from ..core.normative_field import NormativeField, NormLevel, NormVerdict
from ..swarm.protocol import AgentMetrics, AgentStatus, AuditVerdict, MessageType, Priority
from ..swarm.swarm import SwarmBus, SwarmNode


class BaseAgent(ABC):
    """MSSclaw Agent 基类.

    使用方法：
        class MyAgent(BaseAgent):
            role = "Code-Agent"
            capabilities = ["coding", "python", "debug"]

            def handle_task_assign(self, msg):
                result = do_something(msg.payload)
                self.report(task_id, result, success=True)
    """

    # 子类覆盖
    role: str = "BaseAgent"
    capabilities: list[str] = ["general"]
    description: str = ""

    def __init__(self, name: str, bus: SwarmBus = None,
                 heat_budget: HeatTaxBudget = None,
                 delta: DeltaProtocol = None,
                 guardian: GuardianEngine = None,
                 norm_field: NormativeField = None):
        self.name = name
        self.swarm = SwarmNode(name=name, role=self.role,
                                capabilities=self.capabilities)
        self.heat = heat_budget or HeatTaxBudget()
        self.delta = delta or DeltaProtocol()
        self.guardian = guardian or GuardianEngine()
        self.norm = norm_field or NormativeField()
        self.bus = bus
        self._task_queue: list[dict] = []
        self._running = False
        self._lock = threading.Lock()

        if bus:
            self.connect(bus)

    # ── 生命周期 ──

    def connect(self, bus: SwarmBus) -> None:
        """接入蜂巢总线"""
        self.bus = bus
        self.swarm.connect(bus)
        self._register_handlers()
        self._running = True

    def disconnect(self) -> None:
        self._running = False
        self.swarm.disconnect()

    @abstractmethod
    def _register_handlers(self) -> None:
        """注册消息处理器 — 子类实现"""
        pass

    # ── 消息处理 ──

    def on_task_assign(self, handler: Callable):
        """注册任务分配处理器"""
        self.swarm.on(MessageType.TASK_ASSIGN.value)(handler)

    def on_review_result(self, handler: Callable):
        """注册审查结果处理器"""
        self.swarm.on(MessageType.REVIEW_RESULT.value)(handler)

    def on_info_broadcast(self, handler: Callable):
        self.swarm.on(MessageType.INFO_BROADCAST.value)(handler)

    def on_info_coupling(self, handler: Callable):
        self.swarm.on(MessageType.INFO_COUPLING.value)(handler)

    # ── 行为 API ──

    def accept_task(self, task_spec: dict) -> bool:
        """接受任务前的检查"""
        # 热税检查
        estimated_tokens = task_spec.get("estimated_tokens", 1000)
        if self.heat.exceeded:
            return False

        # Δ 检查
        if self.delta.health < 0.3:
            return False

        # 守卫检查（简化：如果 guardian 不可用则跳过）
        task_text = task_spec.get("description", "")
        try:
            g_result = self.guardian.scan(task_text) if self.guardian else None
            if g_result and getattr(g_result, 'waste', 0) >= 0.8:
                return False
        except Exception:
            pass  # guardian 不可用时宽容处理

        self._task_queue.append(task_spec)
        return True

    def report(self, task_id: str, result: dict, success: bool) -> None:
        """报告任务结果"""
        self.swarm.report_task(task_id, result, success)

    def request_review(self, task_id: str, content: dict) -> None:
        """请求审计 Agent 审查"""
        self.swarm.request_review(task_id, content)

    def broadcast(self, info: dict, priority: Priority = Priority.NORMAL) -> None:
        """广播信息到所有 Agent"""
        from ..swarm.protocol import Message, MessageHeader, MessageType
        msg = Message(
            header=MessageHeader(
                msg_type=MessageType.INFO_BROADCAST,
                sender=self.name,
                receiver="ALL",
                priority=priority,
            ),
            payload=info,
        )
        self.swarm.send(msg)

    def send_to(self, agent_name: str, info: dict,
                priority: Priority = Priority.NORMAL) -> None:
        """发送信息到特定 Agent"""
        from ..swarm.protocol import Message, MessageHeader, MessageType
        msg = Message(
            header=MessageHeader(
                msg_type=MessageType.INFO_COUPLING,
                sender=self.name,
                receiver=agent_name,
                priority=priority,
            ),
            payload=info,
        )
        self.swarm.send(msg)

    # ── 健康检查 ──

    def health_check(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "running": self._running,
            "delta": self.delta.health,
            "heat_remaining": self.heat.total(),
            "tasks_queued": len(self._task_queue),
            "metrics": self.swarm.metrics.to_dict(),
        }

    def heartbeat(self) -> None:
        self.swarm.heartbeat()

    def get_config(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "capabilities": self.capabilities,
            "description": self.description,
        }
