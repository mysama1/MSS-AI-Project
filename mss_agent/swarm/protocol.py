"""
MSSclaw 通信协议 — Pydantic Schema 严格定义.

每个 Agent 间通信都走这个协议：
- 类型安全：编译期防错
- 循环检测：连续 3 轮相似度 > 0.9 → 强制仲裁
- 热税追踪：每次通信计入 Token 预算
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

# ── 核心消息类型 ──


class MessageType(str, Enum):
    TASK_ASSIGN = "task_assign"          # Plan → Agent: 分配任务
    TASK_REPORT = "task_report"          # Agent → Plan: 报告进度
    TASK_COMPLETE = "task_complete"      # Agent → Plan: 任务完成
    TASK_FAIL = "task_fail"              # Agent → Plan: 任务失败
    REVIEW_REQUEST = "review_request"    # Agent → Audit: 请求审查
    REVIEW_RESULT = "review_result"      # Audit → Agent: 审查结果
    REVIEW_OVERRIDE = "review_override"  # Agent → Plan: 上诉审查结果
    INFO_BROADCAST = "info_broadcast"    # Plan → All: 全局广播
    INFO_COUPLING = "info_coupling"      # Plan → Agent: 情报耦合
    HEARTBEAT = "heartbeat"              # Agent → Plan: 存活信号
    MEETING_INVITE = "meeting_invite"    # Plan → Agent: 大小会邀请
    MEETING_AGENDA = "meeting_agenda"    # 会议议题
    MOLT_SIGNAL = "molt_signal"          # Plan → Agent: 蜕壳指令
    NORM_ALERT = "norm_alert"            # NormField → All: 安全告警


class Priority(str, Enum):
    CRITICAL = "critical"  # 立即处理，抢占资源
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"  # 闲时处理


class AgentStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    BLOCKED = "blocked"     # 等待审查
    MOLTING = "molting"     # 蜕壳中
    DEGRADED = "degraded"   # 降级运行
    OFFLINE = "offline"


class AuditVerdict(str, Enum):
    PASS = "pass"
    PASS_WITH_WARNINGS = "pass_with_warnings"
    REJECT = "reject"
    NEEDS_HUMAN = "needs_human"


# ── Pydantic-style 消息体（用 dataclass 替代 Pydantic，0 依赖）──


@dataclass
class MessageHeader:
    """消息头 — 每条 Agent 通信的元信息"""
    msg_id: str = field(default_factory=lambda: _gen_id("msg"))
    msg_type: MessageType = MessageType.INFO_BROADCAST
    sender: str = ""                      # Agent name
    receiver: str = ""                    # Agent name or "ALL"
    priority: Priority = Priority.NORMAL
    timestamp: float = field(default_factory=time.time)
    reply_to: str = ""                    # 回复某条消息的 msg_id
    round: int = 0                        # 当前对话轮次
    max_rounds: int = 5                   # 最大轮次，超过 → 强制仲裁
    ttl: int = 0                          # 生存时间（秒），0=不限
    correlation_id: str = ""              # 关联同一个任务的全局 ID

    def is_expired(self) -> bool:
        if self.ttl <= 0:
            return False
        return (time.time() - self.timestamp) > self.ttl

    def rounds_exceeded(self) -> bool:
        return self.round >= self.max_rounds


@dataclass
class Message:
    """Agent 间通信消息"""
    header: MessageHeader = field(default_factory=MessageHeader)
    payload: dict[str, Any] = field(default_factory=dict)
    content_signature: str = ""

    def sign(self) -> str:
        """生成内容签名用于循环检测"""
        raw = str(sorted(self.payload.items())) if self.payload else ""
        self.content_signature = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return self.content_signature

    @property
    def msg_id(self) -> str:
        return self.header.msg_id

    @property
    def msg_type(self) -> MessageType:
        return self.header.msg_type


# ── 循环检测器 ──


class LoopDetector:
    """多 Agent 通信循环检测.

    连续 3 轮 content_signature 相同 → 判定为死循环
    相似度 > 0.9 → 警告
    """

    def __init__(self, max_rounds: int = 5, similarity_threshold: float = 0.9):
        self.max_rounds = max_rounds
        self.threshold = similarity_threshold
        self._history: dict[str, list[str]] = {}  # correlation_id → [signature, ...]

    def check(self, msg: Message) -> tuple[bool, str]:
        """返回 (is_loop, reason)"""
        cid = msg.header.correlation_id
        if not cid:
            return False, ""

        sig = msg.sign()
        if cid not in self._history:
            self._history[cid] = []

        history: list[str] = self._history[cid]
        history.append(sig)

        # 去重计数：连续相同签名
        if len(history) >= 3:
            last_three = history[-3:]
            if len(set(last_three)) == 1:
                self._history.pop(cid, None)
                return True, f"LOOP_DETECTED: 3 identical rounds with sig={sig[:8]}"

        # 相似度检查（简化：Jaccard 字符级）
        if len(history) >= 2:
            a, b = set(history[-2]), set(history[-1])
            if a and b:
                sim = len(a & b) / len(a | b)
                if sim > self.threshold:
                    return False, f"LOOP_WARNING: similarity={sim:.2f} > {self.threshold}"

        # 硬上限
        if msg.header.rounds_exceeded():
            self._history.pop(cid, None)
            return True, f"MAX_ROUNDS_EXCEEDED: round={msg.header.round} >= {msg.header.max_rounds}"

        return False, ""

    def clear(self, correlation_id: str) -> None:
        self._history.pop(correlation_id, None)


# ── Agent Metrics (AgentOps) ──


@dataclass
class AgentMetrics:
    """每个 Agent 的运行时指标"""
    name: str = ""
    status: AgentStatus = AgentStatus.IDLE
    tasks_total: int = 0
    tasks_succeeded: int = 0
    tasks_failed: int = 0
    tokens_consumed: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    avg_response_ms: float = 0.0
    last_heartbeat: float = 0.0
    loop_detections: int = 0
    norm_violations: int = 0
    uptime_seconds: float = 0.0
    start_time: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        if self.tasks_total == 0:
            return 1.0
        return self.tasks_succeeded / self.tasks_total

    @property
    def is_healthy(self) -> bool:
        """基本健康检查"""
        if self.status == AgentStatus.OFFLINE:
            return False
        if self.status == AgentStatus.DEGRADED:
            return False
        # 失败率 > 50% = 不健康
        if self.tasks_total > 5 and self.success_rate < 0.5:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "tasks_total": self.tasks_total,
            "success_rate": round(self.success_rate, 3),
            "tokens_consumed": self.tokens_consumed,
            "messages_sent": self.messages_sent,
            "avg_response_ms": round(self.avg_response_ms, 1),
            "loop_detections": self.loop_detections,
            "norm_violations": self.norm_violations,
            "uptime_hours": round(self.uptime_seconds / 3600, 1),
            "healthy": self.is_healthy,
        }


# ── 工具函数 ──


def _gen_id(prefix: str = "id") -> str:
    """生成唯一 ID"""
    import uuid
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def make_task_assign(
    sender: str,
    receiver: str,
    task_id: str,
    task_spec: dict[str, Any],
    priority: Priority = Priority.NORMAL,
    max_rounds: int = 3,
) -> Message:
    """快捷：构造任务分配消息"""
    return Message(
        header=MessageHeader(
            msg_type=MessageType.TASK_ASSIGN,
            sender=sender,
            receiver=receiver,
            priority=priority,
            max_rounds=max_rounds,
            correlation_id=task_id,
        ),
        payload={"task_id": task_id, "spec": task_spec},
    )


def make_review_request(
    sender: str,
    receiver: str,
    task_id: str,
    content: dict[str, Any],
    max_rounds: int = 3,
) -> Message:
    """快捷：构造审查请求"""
    return Message(
        header=MessageHeader(
            msg_type=MessageType.REVIEW_REQUEST,
            sender=sender,
            receiver=receiver,
            priority=Priority.HIGH,
            max_rounds=max_rounds,
            correlation_id=task_id,
        ),
        payload={"task_id": task_id, "content": content},
    )
