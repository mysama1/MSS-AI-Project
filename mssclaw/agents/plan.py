"""
MSSclaw Plan-Agent — 全局规划官.

三权分立中的"立法"节点：
  - 任务分解 + Agent 分配
  - 情报耦合（发现可跨 Agent 复用的信息）
  - 反意义污染（检测逻辑病毒，隔离污染源）
  - 大小会调度（大会每周/小会按需）
  - 优先级排序 + 资源调度

避坑：
  - 坑 3: Plan-Agent 不执行、不自审（三权分立）
  - 坑 5: 联邦制 —— 只管理全局调度，不微观控制
"""
from __future__ import annotations

import json
import os
import threading
import time

from mssclaw.core.heat_tax import HeatTaxLevel
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from ..agents.base import BaseAgent
from ..swarm.protocol import (
    AgentMetrics, AgentStatus, Message, MessageHeader,
    MessageType, Priority, make_task_assign,
)
from ..swarm.swarm import SwarmBus, SwarmRegistry
from ..swarm.meeting_room import MeetingRoom, ThreadStatus


class TaskStatus(str, Enum):
    QUEUED = "queued"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskPriority(int, Enum):
    CRITICAL = 0   # 立即抢占
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class Task:
    """Plan-Agent 调度的单个任务"""
    id: str = ""

    def __post_init__(self):
        if not self.id:
            import uuid
            self.id = f"task_{uuid.uuid4().hex[:10]}"
    title: str = ""
    description: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.QUEUED
    assigned_to: str = ""               # Agent name
    required_capability: str = ""       # 需要的能力
    estimated_tokens: int = 1000
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    dependencies: list[str] = field(default_factory=list)  # 前置任务 ID
    result: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    tags: list[str] = field(default_factory=list)


@dataclass
class CouplingSignal:
    """情报耦合信号 — 一个 Agent 的产出可能对另一个 Agent 有用"""
    source_agent: str
    target_agent: str
    reason: str
    data: dict[str, Any]
    relevance_score: float = 0.5   # 0-1
    auto_deliver: bool = False      # 是否自动投递


# ── Plan-Agent ──


class PlanAgent(BaseAgent):
    """全局规划官 — 三权分立中的立法者.

    职责：
      - 不执行任务（不碰代码/视频/文档）
      - 不自我审查（由 Audit-Agent 审查 Plan 的输出）
      - 只做：拆解 → 分配 → 调度 → 耦合 → 防污染
    """

    role = "Plan-Agent"
    capabilities = ["planning", "scheduling", "coupling", "governance"]

    def __init__(self, name: str = "PLAN", bus: SwarmBus = None, **kwargs):
        super().__init__(name=name, bus=bus, **kwargs)
        self._tasks: dict[str, Task] = {}
        self._coupling_signals: list[CouplingSignal] = []
        self._meeting_room: Optional[MeetingRoom] = None
        self._agent_registry: dict[str, dict] = {}  # agent_name → {capabilities, status, load}
        self._pollution_alerts: list[dict] = []
        self._swarm_registry = SwarmRegistry()

    # ── 消息处理器注册 ──

    def _register_handlers(self) -> None:
        self.on_task_assign(self._handle_task_assign)  # 实际是接收 TASK_REPORT
        self.swarm.on(MessageType.TASK_REPORT.value)(self._handle_task_report)
        self.swarm.on(MessageType.TASK_COMPLETE.value)(self._handle_task_complete)
        self.swarm.on(MessageType.TASK_FAIL.value)(self._handle_task_fail)
        self.swarm.on(MessageType.HEARTBEAT.value)(self._handle_heartbeat)
        self.swarm.on(MessageType.REVIEW_OVERRIDE.value)(self._handle_review_override)

    # ── 任务调度 ──

    def create_task(self, title: str, description: str,
                    capability: str, priority: TaskPriority = TaskPriority.NORMAL,
                    dependencies: list[str] = None, tags: list[str] = None,
                    estimated_tokens: int = 1000) -> Task:
        """创建新任务 (S-019: 热税预分配)."""
        # 热税检查: 如果已超预算, 拒绝创建
        if self.heat.exceeded():
            print(f"[PLAN] ⛔ Task '{title}' rejected: heat budget exceeded ({self.heat.total():.2f})")
            raise RuntimeError(f"Heat budget exceeded: {self.heat.total():.2f}")

        task = Task(
            title=title,
            description=description,
            priority=priority,
            required_capability=capability,
            estimated_tokens=estimated_tokens,
            dependencies=dependencies or [],
            tags=tags or [],
        )
        self._tasks[task.id] = task

        # S-019: 预分配热税
        self.heat.reserve(task.id, estimated_tokens)
        self.heat.charge(HeatTaxLevel.L1_LOGICAL, estimated_tokens * 0.01,
                        f"create_task: {title}")

        return task

    def assign_task(self, task_id: str, agent_name: str) -> bool:
        """将任务分配给 Agent"""
        task = self._tasks.get(task_id)
        if not task:
            return False

        # 依赖检查
        for dep_id in task.dependencies:
            dep = self._tasks.get(dep_id)
            if not dep or dep.status != TaskStatus.COMPLETED:
                print(f"[PLAN] Task {task_id}: dependency {dep_id} not completed")
                return False

        # 能力检查 (自动发现总线节点 capabilities)
        if agent_name not in self._agent_registry and self.bus:
            node = self.bus._nodes.get(agent_name)
            if node:
                self._agent_registry[agent_name] = {
                    "capabilities": node.capabilities,
                    "status": "idle",
                    "load": 0,
                }
        agent_info = self._agent_registry.get(agent_name, {})
        agent_caps = agent_info.get("capabilities", [])
        if task.required_capability not in agent_caps and "general" not in agent_caps:
            print(f"[PLAN] Agent {agent_name} lacks capability {task.required_capability}")
            return False

        # 发送 TASK_ASSIGN
        msg = make_task_assign(
            sender=self.name,
            receiver=agent_name,
            task_id=task_id,
            task_spec={
                "title": task.title,
                "description": task.description,
                "priority": task.priority.value,
                "estimated_tokens": task.estimated_tokens,
            },
        )
        self.swarm.send(msg)
        task.assigned_to = agent_name
        task.status = TaskStatus.ASSIGNED
        task.started_at = time.time()

        print(f"[PLAN] Assigned '{task.title}' → {agent_name}")
        return True

    def auto_assign(self, task_id: str) -> bool:
        """自动寻找合适 Agent 分配任务"""
        task = self._tasks.get(task_id)
        if not task:
            return False

        # 找最少负载的合适 Agent
        candidates = []
        for name, info in self._agent_registry.items():
            caps = info.get("capabilities", [])
            if task.required_capability in caps:
                load = info.get("load", 99)
                candidates.append((load, name))

        if not candidates:
            print(f"[PLAN] No agent found for capability: {task.required_capability}")
            return False

        # 最少负载优先
        candidates.sort()
        return self.assign_task(task_id, candidates[0][1])

    def retry_task(self, task_id: str) -> bool:
        """重试失败任务"""
        task = self._tasks.get(task_id)
        if not task or task.retry_count >= task.max_retries:
            return False

        task.retry_count += 1
        task.status = TaskStatus.QUEUED
        print(f"[PLAN] Retry {task_id} (attempt {task.retry_count}/{task.max_retries})")
        return self.auto_assign(task_id)

    # ── 情报耦合 ──

    def detect_coupling(self, source_agent: str, result: dict[str, Any]) -> list[CouplingSignal]:
        """检测：某 Agent 的产出是否对其他 Agent 有价值 (S-006: 正则增强)."""
        import re
        signals = []

        # 规则表: (正则模式, 目标列表, 领域标签, 相关性分数)
        coupling_rules = [
            (r'\b(security|auth|token|validate|sanitize)\b', ['Code-Agent', 'Audit'], 'security', 0.85),
            (r'\b(video|ffmpeg|render|clip|encode|decode)\b', ['Video-Agent'], 'media', 0.80),
            (r'\b(api|http|request|endpoint|rest)\b', ['Code-Agent', 'Product-Agent'], 'api', 0.75),
            (r'\b(model|train|dataset|weights|inference)\b', ['Video-Agent', 'Code-Agent'], 'ml', 0.80),
            (r'\b(translate|i18n|locale|lang)\b', ['Translate-Agent'], 'i18n', 0.70),
            (r'\b(test|assert|coverage|spec|benchmark)\b', ['Code-Agent', 'Audit'], 'quality', 0.75),
            (r'\b(deploy|release|publish|ci|pipeline)\b', ['Product-Agent'], 'ops', 0.80),
            (r'\b(code|function|module|class|import)\b', ['Code-Agent'], 'code', 0.60),
            (r'\b(db|database|sql|query|schema)\b', ['Code-Agent', 'KB-Agent'], 'data', 0.75),
            (r'\b(ui|component|layout|style|css)\b', ['Product-Agent'], 'frontend', 0.65),
        ]

        result_text = json.dumps(result, ensure_ascii=False).lower()
        for pattern, targets, reason, base_score in coupling_rules:
            if re.search(pattern, result_text, re.IGNORECASE):
                for target in targets:
                    if target != source_agent:
                        signal = CouplingSignal(
                            source_agent=source_agent,
                            target_agent=target,
                            reason=f"{reason}: matched '{pattern}'",
                            data=result,
                            relevance_score=base_score,
                        )
                        signals.append(signal)

        self._coupling_signals.extend(signals)
        return signals

    def deliver_coupling(self, signal: CouplingSignal) -> None:
        """投递耦合信号到目标 Agent (S-006: bus.route)."""
        if self.bus:
            msg = Message(
                header=MessageHeader(
                    msg_type=MessageType.INFO_COUPLING,
                    sender=self.name,
                    receiver=signal.target_agent,
                    priority=Priority.LOW,
                ),
                payload={
                    "type": "coupling",
                    "source": signal.source_agent,
                    "reason": signal.reason,
                    "data": signal.data,
                    "relevance": signal.relevance_score,
                },
            )
            self.bus.route(msg)
        print(f"[PLAN] Coupling: {signal.source_agent} → {signal.target_agent} ({signal.reason})")

    # ── 反意义污染 ──

    def check_pollution(self, agent_name: str, content: str) -> bool:
        """检查某 Agent 产出是否有意义污染"""
        # 守卫引擎评分（兼容旧 API）
        g_result = None
        try:
            g_result = self.guardian.scan(content) if self.guardian else None
        except Exception:
            pass

        # 意义污染判定规则
        is_polluted = False
        reasons = []

        if g_result:
            density = getattr(g_result, 'density', 0)
            score = getattr(g_result, 'score', 1)
            if density >= 0.7:
                is_polluted = True
                reasons.append(f"Guard density={density:.2f}")
            if score <= 0.2 and density >= 0.5:
                is_polluted = True
                reasons.append(f"Quality score={score:.2f}")

        # 检测逻辑矛盾
        contradictions = self._detect_contradictions(content)
        if contradictions:
            is_polluted = True
            reasons.append(f"Contradictions: {contradictions}")

        if is_polluted:
            self._pollution_alerts.append({
                "time": time.time(),
                "agent": agent_name,
                "reasons": reasons,
                "content_preview": content[:200],
            })

            # 隔离：暂停该 Agent 的新任务分配
            if agent_name in self._agent_registry:
                self._agent_registry[agent_name]["status"] = "quarantined"
                print(f"[PLAN] ⚠️ QUARANTINED {agent_name}: {', '.join(reasons)}")

        return is_polluted

    def _detect_contradictions(self, text: str) -> list[str]:
        """检测文本中的逻辑矛盾（简化实现）"""
        contradictions = []
        lowercase = text.lower()

        # 简单矛盾对检测
        pairs = [
            ("必须", "不能"), ("一定", "不一定"),
            ("总是", "有时"), ("全部", "部分"),
            ("确凿", "猜测"), ("证实", "推测"),
        ]
        for a, b in pairs:
            if a in lowercase and b in lowercase:
                contradictions.append(f"'{a}' ↔ '{b}'")

        return contradictions[:3]

    # ── 大小会调度 ──

    def set_meeting_room(self, room: MeetingRoom) -> None:
        self._meeting_room = room

    def call_grand_meeting(self, agenda: str) -> Optional[str]:
        """召开大会"""
        if not self._meeting_room:
            return None
        participants = list(self._agent_registry.keys()) + [self.name]
        thread = self._meeting_room.start_grand_meeting(agenda, participants)
        # 通知所有 Agent
        self.broadcast({
            "type": "meeting",
            "meeting_type": "grand",
            "thread_id": thread.id,
            "agenda": agenda,
        }, priority=Priority.HIGH)
        print(f"[PLAN] 🏛 GRAND MEETING: {agenda}")
        return thread.id

    def call_mini_meeting(self, agent_a: str, agent_b: str, topic: str) -> Optional[str]:
        """召开小会"""
        if not self._meeting_room:
            return None
        thread = self._meeting_room.start_mini_meeting(agent_a, agent_b, topic)
        print(f"[PLAN] 🤝 MINI MEETING: {agent_a} ↔ {agent_b} '{topic}'")
        return thread.id

    # ── 内部消息处理 ──

    def _handle_task_assign(self, msg: Message) -> None:
        """Plan 自己不接收任务分配（三权分立）"""
        pass

    def _handle_task_report(self, msg: Message) -> None:
        """Agent 进度报告"""
        pass

    def _handle_task_complete(self, msg: Message) -> None:
        """Agent 完成任务"""
        task_id = msg.payload.get("task_id", "")
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            task.result = msg.payload.get("result", {})

        # 污染检查
        result = msg.payload.get("result", {})
        content = json.dumps(result, ensure_ascii=False)
        self.check_pollution(msg.header.sender, content)

        # 情报耦合
        signals = self.detect_coupling(msg.header.sender, result)
        for s in signals:
            if s.auto_deliver or s.relevance_score > 0.7:
                self.deliver_coupling(s)

        # 更新 Agent 负载
        if msg.header.sender in self._agent_registry:
            self._agent_registry[msg.header.sender]["load"] -= 1

        print(f"[PLAN] ✅ {msg.header.sender} completed '{task.title if task else task_id}'")

    def _handle_task_fail(self, msg: Message) -> None:
        """Agent 任务失败"""
        task_id = msg.payload.get("task_id", "")
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.FAILED
            print(f"[PLAN] ❌ {msg.header.sender} failed '{task.title}'")

        # 自动重试
        if task and task.retry_count < task.max_retries:
            self.retry_task(task_id)

    def _handle_heartbeat(self, msg: Message) -> None:
        """处理 Agent 心跳"""
        agent_name = msg.header.sender
        metrics = msg.payload.get("metrics", {})
        self._agent_registry[agent_name] = {
            "capabilities": self._agent_registry.get(agent_name, {}).get("capabilities", []),
            "status": metrics.get("status", "unknown"),
            "load": metrics.get("tasks_total", 0) - metrics.get("tasks_succeeded", 0),
            "last_heartbeat": time.time(),
            "healthy": metrics.get("healthy", False),
        }

    def _handle_review_override(self, msg: Message) -> None:
        """处理 Agent 上诉审查结果"""
        task_id = msg.payload.get("task_id", "")
        reason = msg.payload.get("reason", "")
        print(f"[PLAN] ⚖️ REVIEW OVERRIDE: {task_id} — {reason}")
        # Plan 最终裁决：人工介入
        if self._meeting_room:
            self._meeting_room.create_thread(
                topic=f"裁决: {task_id}",
                created_by=self.name,
                description=f"Agent 上诉审查结果:\n{reason}",
                tags=["arbitration", task_id],
            )

    # ── 状态与报告 ──

    def get_task_board(self) -> dict[str, Any]:
        """获取任务看板"""
        by_status = {s.value: [] for s in TaskStatus}
        for t in self._tasks.values():
            by_status[t.status.value].append({
                "id": t.id, "title": t.title,
                "assigned_to": t.assigned_to,
                "priority": t.priority.value,
                "tags": t.tags,
            })

        return {
            "total_tasks": len(self._tasks),
            "by_status": {k: len(v) for k, v in by_status.items()},
            "tasks": by_status,
        }

    def get_agent_load(self) -> dict[str, Any]:
        """获取 Agent 负载"""
        return {
            name: {
                "capabilities": info.get("capabilities", []),
                "load": info.get("load", 0),
                "healthy": info.get("healthy", False),
                "last_heartbeat": info.get("last_heartbeat", 0),
            }
            for name, info in self._agent_registry.items()
        }

    def get_pollution_alerts(self) -> list[dict]:
        return self._pollution_alerts[-20:]

    def summary(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "total_tasks": len(self._tasks),
            "active_tasks": sum(1 for t in self._tasks.values()
                                if t.status in (TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS)),
            "registered_agents": len(self._agent_registry),
            "healthy_agents": sum(1 for a in self._agent_registry.values()
                                   if a.get("healthy", False)),
            "pollution_alerts": len(self._pollution_alerts),
            "coupling_signals": len(self._coupling_signals),
        }
