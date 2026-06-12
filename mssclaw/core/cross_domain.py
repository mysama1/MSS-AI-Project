"""
CrossDomainRouter — 公/私域跨域路由器.

双域架构的安全边界:
  Work Bus (公域) ←→ CrossDomainRouter ←→ Personal Bus (私域)

设计约束:
  1. 默认隔离: 两域 Agent 不能直接通信
  2. 有限通道: 仅特定消息类型可通过
  3. 全量审计: 每条跨域消息都记录
  4. 不对称规则: Work→Personal 宽松, Personal→Work 严格

通道清单:
  Work→Personal:
    - life_notify: "6点提醒吃饭" (文本提醒)
    - break_suggest: "该休息了" (健康建议)
  Personal→Work:
    - work_pause: "暂停工作" (通知, 不含数据)
    - time_check: "几点了" (纯查询)

禁止:
  - Personal→Work 的任何数据/文件/指令传递
  - Work→Personal 的任何任务分配
  - 跨域代码执行
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from ..swarm.swarm import SwarmBus
from ..swarm.protocol import Message, MessageHeader, MessageType, Priority


# ── 跨域通道定义 ──

class CrossDomainChannel(Enum):
    """允许的跨域通道"""
    # Work → Personal
    LIFE_NOTIFY = "life_notify"          # 生活提醒 (文本)
    BREAK_SUGGEST = "break_suggest"      # 休息建议
    MEETING_REMIND = "meeting_remind"    # 会议提醒

    # Personal → Work
    WORK_PAUSE = "work_pause"            # 暂停请求
    TIME_QUERY = "time_query"            # 时间查询

    # 双向
    HEALTH_CHECK = "health_check"        # 健康检查 (互 ping)


# 通道规则: (允许方向, 最大payload大小, 是否需要审计)
CHANNEL_RULES: dict[CrossDomainChannel, dict] = {
    CrossDomainChannel.LIFE_NOTIFY:     {"dir": "work_to_personal", "max_bytes": 512,  "audit": True},
    CrossDomainChannel.BREAK_SUGGEST:   {"dir": "work_to_personal", "max_bytes": 256,  "audit": True},
    CrossDomainChannel.MEETING_REMIND:  {"dir": "work_to_personal", "max_bytes": 1024, "audit": True},
    CrossDomainChannel.WORK_PAUSE:      {"dir": "personal_to_work", "max_bytes": 256,  "audit": True},
    CrossDomainChannel.TIME_QUERY:      {"dir": "personal_to_work", "max_bytes": 128,  "audit": False},
    CrossDomainChannel.HEALTH_CHECK:    {"dir": "bidirectional",    "max_bytes": 64,   "audit": False},
}


@dataclass
class CrossDomainRecord:
    """单条跨域记录"""
    id: str
    channel: str
    direction: str
    sender: str
    receiver: str
    payload_summary: str  # 仅摘要, 不存储原始数据
    payload_size: int
    timestamp: str
    allowed: bool
    deny_reason: str = ""


class CrossDomainRouter:
    """公/私域跨域路由器.

    用法:
        router = CrossDomainRouter(work_bus, personal_bus)
        router.start()

        # Work → Personal 发送提醒
        router.send(CrossDomainChannel.LIFE_NOTIFY,
                    sender="Code-Agent", receiver="Life",
                    payload={"text": "该吃饭了"})

        # Personal → Work 暂停请求
        router.send(CrossDomainChannel.WORK_PAUSE,
                    sender="Concierge", receiver="PLAN",
                    payload={"reason": "晚饭时间"})
    """

    def __init__(self, work_bus: SwarmBus, personal_bus: SwarmBus,
                 audit_dir: str = None):
        self.work_bus = work_bus
        self.personal_bus = personal_bus
        self.audit_dir = audit_dir or os.path.expanduser(
            "~/.mssclaw/personal/audit"
        )
        os.makedirs(self.audit_dir, exist_ok=True)

        self._audit_log: list[CrossDomainRecord] = []
        self._lock = threading.Lock()
        self._running = False

        # 统计
        self.stats = {
            "work_to_personal": 0,
            "personal_to_work": 0,
            "blocked": 0,
            "total": 0,
        }

    # ── 核心路由 ──

    def send(self, channel: CrossDomainChannel,
             sender: str, receiver: str,
             payload: dict[str, Any],
             dry_run: bool = False) -> dict[str, Any]:
        """跨域发送消息. 返回 {allowed, record_id, reason}.
        
        Args:
            dry_run: 如果 True, 跳过实际 bus.route() 调用 (用于测试和审计模式)
        """

        with self._lock:
            rule = CHANNEL_RULES[channel]
            direction = rule["dir"]
            self.stats["total"] += 1

            # 验证方向
            sender_in_work = sender not in ["Concierge", "Life", "Entertain", "Social"]
            receiver_in_work = receiver not in ["Concierge", "Life", "Entertain", "Social"]

            if direction == "work_to_personal" and not sender_in_work:
                return self._deny(channel, sender, receiver, payload,
                                  "work_to_personal 通道只允许 Work→Personal")
            if direction == "personal_to_work" and not receiver_in_work:
                return self._deny(channel, sender, receiver, payload,
                                  "personal_to_work 通道只允许 Personal→Work")

            if direction == "bidirectional":
                # 双向通道: 至少一端在工作域
                if sender_in_work == receiver_in_work:
                    return self._deny(channel, sender, receiver, payload,
                                      "bidirectional 通道需要跨域")

            # 验证 payload 大小
            payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            if len(payload_bytes) > rule["max_bytes"]:
                return self._deny(channel, sender, receiver, payload,
                    f"Payload 超限: {len(payload_bytes)} > {rule['max_bytes']} bytes")

            # 构建跨域消息
            msg = Message(
                header=MessageHeader(
                    msg_type=MessageType.INFO_COUPLING,
                    sender=f"{sender}[cross-domain]",
                    receiver=receiver,
                    priority=Priority.NORMAL,
                ),
                payload={
                    **payload,
                    "_cross_domain": {
                        "channel": channel.value,
                        "direction": direction,
                        "routed_by": "CrossDomainRouter",
                        "timestamp": time.time(),
                    },
                },
            )

            # 路由到目标 Bus (dry_run 模式跳过)
            if not dry_run:
                if sender_in_work:
                    target_bus = self.personal_bus
                else:
                    target_bus = self.work_bus
                target_bus.route(msg)

            # 更新统计
            if sender_in_work:
                self.stats["work_to_personal"] += 1
            else:
                self.stats["personal_to_work"] += 1

            # 审计记录
            record = CrossDomainRecord(
                id=f"xdr_{int(time.time() * 10000)}",
                channel=channel.value,
                direction=direction,
                sender=sender,
                receiver=receiver,
                payload_summary=str(list(payload.keys())),
                payload_size=len(payload_bytes),
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
                allowed=True,
            )
            self._audit_log.append(record)
            self._save_audit(record)

            return {"allowed": True, "record_id": record.id}

    def _deny(self, channel, sender, receiver, payload, reason) -> dict:
        """拒绝跨域消息"""
        self.stats["blocked"] += 1
        record = CrossDomainRecord(
            id=f"xdr_{int(time.time() * 10000)}",
            channel=channel.value,
            direction=CHANNEL_RULES[channel]["dir"],
            sender=sender,
            receiver=receiver,
            payload_summary="[BLOCKED]",
            payload_size=len(json.dumps(payload or {}).encode("utf-8")),
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            allowed=False,
            deny_reason=reason,
        )
        self._audit_log.append(record)
        self._save_audit(record)
        return {"allowed": False, "record_id": record.id, "reason": reason}

    # ── 审计持久化 ──

    def _save_audit(self, record: CrossDomainRecord) -> None:
        """追加审计记录到 JSONL"""
        audit_file = os.path.join(
            self.audit_dir,
            f"cross_domain_{time.strftime('%Y%m%d')}.jsonl"
        )
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "id": record.id,
                "channel": record.channel,
                "direction": record.direction,
                "sender": record.sender,
                "receiver": record.receiver,
                "payload_summary": record.payload_summary,
                "payload_size": record.payload_size,
                "timestamp": record.timestamp,
                "allowed": record.allowed,
                "deny_reason": record.deny_reason,
            }, ensure_ascii=False) + "\n")

    def get_recent_audits(self, hours: int = 24) -> list[dict]:
        """获取最近的跨域审计记录"""
        cutoff = time.time() - hours * 3600
        return [
            {
                "id": r.id, "channel": r.channel, "direction": r.direction,
                "sender": r.sender, "receiver": r.receiver,
                "allowed": r.allowed, "timestamp": r.timestamp,
            }
            for r in self._audit_log
            if r.timestamp and time.strptime(r.timestamp, "%Y-%m-%dT%H:%M:%S") >= time.localtime(cutoff)
        ]

    def get_stats(self) -> dict[str, Any]:
        return dict(self.stats)

    # ── 生命周期 ──

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False
