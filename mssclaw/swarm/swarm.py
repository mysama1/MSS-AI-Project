"""
MSSclaw Swarm — 分布式 Agent 蜂巢运行时.

SwarmNode:     单个 Agent 节点（注册/心跳/metrics）
SwarmRegistry: 注册中心（发现/健康检查）
SwarmBus:      消息总线（路由/循环检测/热税追踪）

避坑：
  - 协议层确立行为边界（坑 1）
  - 循环检测 + 强制仲裁（坑 2）
  - 通信 Token 预算纳入热税（坑 4）
  - AgentOps 指标上报（坑 7）
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections import defaultdict
from typing import Any, Callable, Optional

from .protocol import (
    AgentMetrics,
    AgentStatus,
    AuditVerdict,
    LoopDetector,
    Message,
    MessageHeader,
    MessageType,
    Priority,
    make_review_request,
    make_task_assign,
)


# ── SwarmNode: 单个 Agent 节点 ──


class SwarmNode:
    """MSSclaw 蜂巢中的一个 Agent 节点.

    每个 Agent 通过 SwarmNode 注册自己、收发消息、上报指标。
    """

    def __init__(self, name: str, role: str, capabilities: list[str]):
        self.name = name
        self.role = role
        self.capabilities = capabilities
        self.metrics = AgentMetrics(name=name)
        self._inbox: list[Message] = []
        self._outbox: list[Message] = []
        self._handlers: dict[str, Callable] = {}
        self._bus: Optional[SwarmBus] = None
        self._lock = threading.Lock()
        self._running = False

    # ── 生命周期 ──

    def connect(self, bus: SwarmBus) -> None:
        """接入消息总线"""
        self._bus = bus
        bus.register(self)
        self.metrics.status = AgentStatus.IDLE
        self._running = True

    def disconnect(self) -> None:
        """断开连接"""
        if self._bus:
            self._bus.unregister(self.name)
        self._running = False
        self.metrics.status = AgentStatus.OFFLINE

    # ── 消息收发 ──

    def send(self, msg: Message, track_token: int = 0) -> str:
        """发送消息到总线.

        Args:
            msg: 消息对象
            track_token: 此消息估算 Token 消耗（用于热税追踪）

        Returns:
            msg_id
        """
        msg.header.sender = self.name
        msg.header.timestamp = time.time()
        msg.sign()

        with self._lock:
            self._outbox.append(msg)
            self.metrics.messages_sent += 1
            self.metrics.tokens_consumed += track_token

        if self._bus:
            self._bus.route(msg)

        return msg.msg_id

    def receive(self, msg: Message) -> None:
        """接收来自总线的消息"""
        with self._lock:
            self._inbox.append(msg)
            self.metrics.messages_received += 1

        # 自动路由到处理器
        handler = self._handlers.get(msg.msg_type.value)
        if handler:
            handler(msg)

    def on(self, msg_type: str):
        """装饰器：注册消息处理器"""
        def decorator(fn):
            self._handlers[msg_type] = fn
            return fn
        return decorator

    # ── 状态与指标 ──

    def heartbeat(self) -> AgentMetrics:
        """发送心跳并更新指标"""
        self.metrics.last_heartbeat = time.time()
        self.metrics.uptime_seconds = time.time() - self.metrics.start_time

        if self._bus:
            hb = Message(
                header=MessageHeader(
                    msg_type=MessageType.HEARTBEAT,
                    sender=self.name,
                    receiver="PLAN",
                ),
                payload={"metrics": self.metrics.to_dict()},
            )
            self._bus.route(hb)

        return self.metrics

    def report_task(self, task_id: str, result: dict[str, Any], success: bool) -> str:
        """报告任务结果"""
        msg_type = MessageType.TASK_COMPLETE if success else MessageType.TASK_FAIL
        msg = Message(
            header=MessageHeader(
                msg_type=msg_type,
                sender=self.name,
                receiver="PLAN",
                priority=Priority.HIGH,
                correlation_id=task_id,
            ),
            payload={"task_id": task_id, "result": result, "success": success},
        )
        self.metrics.tasks_total += 1
        if success:
            self.metrics.tasks_succeeded += 1
        else:
            self.metrics.tasks_failed += 1
        return self.send(msg)

    def request_review(self, task_id: str, content: dict[str, Any]) -> str:
        """请求 Audit-Agent 审查"""
        msg = make_review_request(self.name, "AUDIT", task_id, content)
        return self.send(msg)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "capabilities": self.capabilities,
            "metrics": self.metrics.to_dict(),
            "inbox_size": len(self._inbox),
            "outbox_size": len(self._outbox),
            "running": self._running,
        }


# ── SwarmBus: 消息总线 ──


class SwarmBus:
    """蜂巢消息总线 — 路由 + 循环检测 + 热税追踪."""

    def __init__(self, loop_max_rounds: int = 5):
        self._nodes: dict[str, SwarmNode] = {}
        self._loop_detector = LoopDetector(max_rounds=loop_max_rounds)
        self._message_log: list[dict] = []  # 最近 1000 条
        self._total_tokens: int = 0
        self._lock = threading.Lock()
        self._arbiter: Optional[Callable] = None  # 强制仲裁函数
        self._audit_node: Optional[str] = None     # 审计节点名

    # ── 注册 ──

    def register(self, node: SwarmNode) -> None:
        with self._lock:
            self._nodes[node.name] = node

    def unregister(self, name: str) -> None:
        with self._lock:
            self._nodes.pop(name, None)

    def set_audit_node(self, name: str) -> None:
        self._audit_node = name

    def set_arbiter(self, fn: Callable) -> None:
        """设置强制仲裁回调，当消息陷入死循环时调用"""
        self._arbiter = fn

    # ── 路由 ──

    def route(self, msg: Message, retries: int = 3, retry_delay: float = 0.5) -> bool:
        """路由消息到接收者.

        Args:
            msg: 消息对象
            retries: 投递失败时的重试次数
            retry_delay: 重试间隔 (秒)

        Returns:
            True: 投递成功
            False: 被拦截（循环检测/超时）或重试耗尽
        """
        msg.sign()

        # 循环检测
        is_loop, reason = self._loop_detector.check(msg)
        if is_loop:
            self._log(msg, "blocked", reason)
            if self._arbiter:
                self._arbiter(msg, reason, self._nodes.get(msg.header.sender))
            return False

        # TTL 检查
        if msg.header.is_expired():
            self._log(msg, "expired", "")
            return False

        # 路由 (带重试)
        receiver = msg.header.receiver
        for attempt in range(retries + 1):
            try:
                with self._lock:
                    if receiver == "ALL":
                        for name, node in list(self._nodes.items()):
                            if name != msg.header.sender:
                                node.receive(msg)
                    elif receiver in self._nodes:
                        self._nodes[receiver].receive(msg)
                    else:
                        raise KeyError(receiver)
                self._log(msg, "routed", f"{reason} (attempt {attempt+1})" if attempt > 0 else reason)
                return True
            except KeyError:
                # Agent 未注册: 等待重试 (可能正在 connect)
                if attempt < retries:
                    time.sleep(retry_delay)
                    continue
                self._log(msg, "no_receiver", f"receiver '{receiver}' not found after {retries+1} attempts")
            except Exception as e:
                if attempt < retries:
                    time.sleep(retry_delay)
                    continue
                self._log(msg, "error", f"route failed: {e}")
        return False

    # ── 查询 ──

    def discover(self, capability: str) -> list[SwarmNode]:
        """按能力发现 Agent"""
        return [
            n for n in self._nodes.values()
            if capability in n.capabilities and n._running
        ]

    def get_status(self) -> dict[str, Any]:
        """全集群状态"""
        nodes = {}
        for name, node in self._nodes.items():
            nodes[name] = node.to_dict()
        return {
            "nodes": nodes,
            "total_nodes": len(nodes),
            "healthy_nodes": sum(1 for n in self._nodes.values() if n.metrics.is_healthy),
            "total_tokens": self._total_tokens,
            "total_messages": len(self._message_log),
        }

    def health_check(self) -> dict[str, bool]:
        """简单健康检查"""
        return {
            name: node.metrics.is_healthy
            for name, node in self._nodes.items()
        }

    # ── 内部 ──

    def _log(self, msg: Message, status: str, detail: str) -> None:
        entry = {
            "ts": time.time(),
            "msg_id": msg.msg_id,
            "sender": msg.header.sender,
            "receiver": msg.header.receiver,
            "type": msg.msg_type.value,
            "status": status,
            "detail": detail,
        }
        with self._lock:
            self._message_log.append(entry)
            if len(self._message_log) > 1000:
                self._message_log = self._message_log[-500:]

    def get_logs(self, limit: int = 50) -> list[dict]:
        return self._message_log[-limit:]


# ── SwarmRegistry: 持久化注册中心 ──


class SwarmRegistry:
    """Agent 注册信息的持久化存储."""

    def __init__(self, db_path: str = ""):
        self._path = db_path or "data/swarm_registry.json"
        self._entries: dict[str, dict] = {}
        self._load()

    def register_agent(self, name: str, role: str, capabilities: list[str], config: dict = None) -> None:
        self._entries[name] = {
            "name": name,
            "role": role,
            "capabilities": capabilities,
            "config": config or {},
            "registered_at": time.time(),
        }
        self._save()

    def unregister_agent(self, name: str) -> None:
        self._entries.pop(name, None)
        self._save()

    def discover(self, capability: str = "") -> list[dict]:
        if not capability:
            return list(self._entries.values())
        return [
            e for e in self._entries.values()
            if capability in e.get("capabilities", [])
        ]

    def list_all(self) -> dict[str, dict]:
        return dict(self._entries)

    def _load(self) -> None:
        try:
            if os.path.exists(self._path):
                with open(self._path, encoding="utf-8") as f:
                    self._entries = json.load(f)
        except Exception:
            self._entries = {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._entries, f, ensure_ascii=False, indent=2)


# ── 三权分立仲裁器 ──


class TriasArbiter:
    """三权分立仲裁器 — Plan / Execute / Audit 冲突解决.

    场景：
    - Audit 驳回 Execute 的结果
    - Execute 上诉 Audit 的驳回
    - Plan 最终仲裁
    """

    def __init__(self, plan_node: SwarmNode, audit_node: SwarmNode):
        self.plan = plan_node
        self.audit = audit_node
        self._cases: dict[str, dict] = {}  # task_id → case

    def submit_audit_result(self, task_id: str, verdict: AuditVerdict, reason: str) -> None:
        self._cases[task_id] = {
            "verdict": verdict,
            "reason": reason,
            "escalated": False,
            "resolved": verdict == AuditVerdict.PASS,
        }

    def escalate(self, task_id: str, appeal_reason: str) -> AuditVerdict:
        """Execute Agent 上诉 → Plan Agent 最终裁决"""
        case = self._cases.get(task_id)
        if not case:
            return AuditVerdict.NEEDS_HUMAN

        case["escalated"] = True
        case["appeal_reason"] = appeal_reason

        # Plan Agent 仲裁逻辑:
        # 如果驳回次数 > 2 → 人工介入
        # 如果争议不可调和 → Needs_human
        if case["verdict"] == AuditVerdict.REJECT:
            # 简化版：Plan 直接判定 Needs_human
            case["resolved"] = False
            return AuditVerdict.NEEDS_HUMAN

        return case["verdict"]

    def resolve(self, task_id: str) -> bool:
        return self._cases.get(task_id, {}).get("resolved", False)
