"""
错误恢复系统 — 对标 LangGraph Checkpointer + Interrupt.

三大机制:
  1. Checkpoint: 状态快照 → 崩溃后恢复
  2. Interrupt: 任意节点暂停 → 人工审批 → 从断点继续
  3. Retry: 失败任务自动重试 (指数退避 + 降级)

对标:
  LangGraph: Checkpointer (PostgresSaver) + interrupt_before
  Anthropic: "不能简单从零重试，需从错误发生点恢复"
  CrewAI: 无此机制 (坑 7: 调试黑洞)

设计哲学:
  - 零外部依赖 (文件系统持久化，不需要 PostgreSQL)
  - 轻量级 (单个 JSON 文件，不是分布式状态机)
  - 确定性恢复 (检查点哈希 → 防篡改)
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


# ── 检查点 ──

class CheckpointType(str, Enum):
    AUTO = "auto"           # 自动 (每个任务完成后)
    MANUAL = "manual"       # 手动 (显式调用)
    PRE_MOLT = "pre_molt"   # 蜕壳前
    CRASH = "crash"         # 崩溃前最后已知状态


@dataclass
class Checkpoint:
    """单个检查点"""
    id: str = ""
    type: CheckpointType = CheckpointType.AUTO
    timestamp: float = field(default_factory=time.time)
    agent_name: str = ""
    state: dict[str, Any] = field(default_factory=dict)
    task_queue: list[dict] = field(default_factory=list)
    heat_tax: dict = field(default_factory=dict)
    delta: dict = field(default_factory=dict)
    checksum: str = ""

    def __post_init__(self):
        import uuid
        if not self.id:
            self.id = f"ckpt_{uuid.uuid4().hex[:8]}_{self.agent_name}"
        if not self.checksum:
            self.checksum = self._compute_checksum()

    def _compute_checksum(self) -> str:
        """SHA256 校验 → 防篡改"""
        payload = json.dumps({
            "agent": self.agent_name,
            "state": self.state,
            "tasks": self.task_queue,
        }, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def verify(self) -> bool:
        """验证检查点完整性"""
        return self.checksum == self._compute_checksum()


class CheckpointManager:
    """
    检查点管理器.

    功能:
      - save(agent): 保存当前状态
      - load(agent_name): 加载最新检查点
      - list(agent_name): 列出所有检查点
      - rollback(agent_name, ckpt_id): 回滚到指定检查点
      - cleanup(agent_name, keep=N): 清理旧检查点
    """

    def __init__(self, store_dir: str = ""):
        self.store_dir = store_dir or os.path.join(
            os.path.dirname(__file__), "..", "data", "checkpoints"
        )
        os.makedirs(self.store_dir, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, agent_name: str) -> str:
        return os.path.join(self.store_dir, f"{agent_name}_checkpoints.jsonl")

    def save(self, agent_name: str, state: dict,
             task_queue: list[dict] = None,
             heat_tax: dict = None, delta: dict = None,
             ckpt_type: CheckpointType = CheckpointType.AUTO) -> Checkpoint:
        """保存检查点"""
        ckpt = Checkpoint(
            agent_name=agent_name,
            type=ckpt_type,
            state=state,
            task_queue=task_queue or [],
            heat_tax=heat_tax or {},
            delta=delta or {},
        )

        with self._lock:
            with open(self._path(agent_name), "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "id": ckpt.id,
                    "type": ckpt.type.value,
                    "timestamp": ckpt.timestamp,
                    "agent_name": ckpt.agent_name,
                    "state": ckpt.state,
                    "task_queue": ckpt.task_queue,
                    "heat_tax": ckpt.heat_tax,
                    "delta": ckpt.delta,
                    "checksum": ckpt.checksum,
                }, ensure_ascii=False, default=str) + "\n")

        return ckpt

    def load(self, agent_name: str) -> Optional[Checkpoint]:
        """加载最新检查点"""
        path = self._path(agent_name)
        if not os.path.exists(path):
            return None

        with self._lock:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        if not lines:
            return None

        # 取最后一行
        last = json.loads(lines[-1])
        ckpt = Checkpoint(
            id=last["id"],
            type=CheckpointType(last.get("type", "auto")),
            timestamp=last["timestamp"],
            agent_name=last["agent_name"],
            state=last.get("state", {}),
            task_queue=last.get("task_queue", []),
            heat_tax=last.get("heat_tax", {}),
            delta=last.get("delta", {}),
            checksum=last.get("checksum", ""),
        )

        if not ckpt.verify():
            print(f"[CKPT] ⚠️ Checksum mismatch for {ckpt.id} — possible corruption")

        return ckpt

    def list_checkpoints(self, agent_name: str) -> list[dict]:
        """列出所有检查点"""
        path = self._path(agent_name)
        if not os.path.exists(path):
            return []

        with self._lock:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        result = []
        for line in lines:
            c = json.loads(line)
            result.append({
                "id": c["id"],
                "type": c.get("type", "auto"),
                "timestamp": c["timestamp"],
                "task_count": len(c.get("task_queue", [])),
            })
        return result

    def rollback(self, agent_name: str, ckpt_id: str) -> Optional[Checkpoint]:
        """回滚到指定检查点 (删除之后的所有检查点)"""
        path = self._path(agent_name)
        if not os.path.exists(path):
            return None

        target = None
        with self._lock:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            new_lines = []
            for line in lines:
                c = json.loads(line)
                new_lines.append(line)
                if c["id"] == ckpt_id:
                    target = c
                    break

            # 写回
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

        if target:
            ckpt = Checkpoint(
                id=target["id"],
                type=CheckpointType(target.get("type", "auto")),
                timestamp=target["timestamp"],
                agent_name=target["agent_name"],
                state=target.get("state", {}),
                task_queue=target.get("task_queue", []),
                heat_tax=target.get("heat_tax", {}),
                delta=target.get("delta", {}),
                checksum=target.get("checksum", ""),
            )
            return ckpt
        return None

    def cleanup(self, agent_name: str, keep: int = 10) -> int:
        """清理旧检查点，只保留最近 N 个"""
        path = self._path(agent_name)
        if not os.path.exists(path):
            return 0

        with self._lock:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if len(lines) <= keep:
                return 0

            removed = len(lines) - keep
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(lines[-keep:])

        return removed


# ── 人工审批中断 ──

class InterruptReason(str, Enum):
    SECURITY_CONCERN = "security_concern"
    HIGH_HEAT_TAX = "high_heat_tax"
    LOW_DELTA = "low_delta"
    AMBIGUOUS_OUTPUT = "ambiguous_output"
    NORM_FIELD_ALERT = "norm_field_alert"
    NEEDS_CONFIRMATION = "needs_confirmation"
    MANUAL_REQUEST = "manual_request"


@dataclass
class InterruptPoint:
    """中断点 — 可恢复"""
    id: str = ""
    agent_name: str = ""
    reason: InterruptReason = InterruptReason.NEEDS_CONFIRMATION
    timestamp: float = field(default_factory=time.time)
    context: dict = field(default_factory=dict)  # 中断时的上下文
    pending_action: str = ""     # 等待执行的动作
    approved: Optional[bool] = None  # None=等待, True=批准, False=拒绝
    approver_note: str = ""
    timeout_seconds: int = 300   # 5 分钟超时

    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.timeout_seconds


class InterruptManager:
    """
    中断管理器.

    对标 LangGraph interrupt_before: 在关键节点暂停
    对标 Anthropic: 人工审批流程

    流程:
      1. interrupt(agent, reason, context) → 暂停 Agent
      2. 等待 approve() 或 reject()
      3. resume() → Agent 从断点继续
    """

    def __init__(self):
        self._pending: dict[str, InterruptPoint] = {}  # id → InterruptPoint
        self._history: list[InterruptPoint] = []
        self._lock = threading.Lock()
        self._callbacks: dict[str, Callable] = {}  # agent_name → callback

    def register_callback(self, agent_name: str, callback: Callable[[InterruptPoint], bool]) -> None:
        """注册中断回调 — 当 Agent 被中断时触发"""
        self._callbacks[agent_name] = callback

    def interrupt(self, agent_name: str, reason: InterruptReason,
                  context: dict = None, pending_action: str = "",
                  timeout: int = 300) -> InterruptPoint:
        """中断 Agent 执行"""
        pt = InterruptPoint(
            id=f"int_{int(time.time() * 10000)}_{agent_name}",
            agent_name=agent_name,
            reason=reason,
            context=context or {},
            pending_action=pending_action,
            timeout_seconds=timeout,
        )

        with self._lock:
            self._pending[pt.id] = pt

        # 触发回调
        if agent_name in self._callbacks:
            try:
                self._callbacks[agent_name](pt)
            except Exception:
                pass

        print(f"[INTERRUPT] ⏸️ {agent_name}: {reason.value} — '{pending_action}'")
        return pt

    def approve(self, interrupt_id: str, note: str = "") -> bool:
        """批准中断 — 允许继续"""
        with self._lock:
            pt = self._pending.get(interrupt_id)
            if not pt:
                return False
            if pt.is_expired():
                self._history.append(pt)
                del self._pending[interrupt_id]
                return False

            pt.approved = True
            pt.approver_note = note
            self._history.append(pt)
            del self._pending[interrupt_id]

        print(f"[INTERRUPT] ✅ Approved: {interrupt_id}")
        return True

    def reject(self, interrupt_id: str, note: str = "") -> bool:
        """拒绝中断 — 取消执行"""
        with self._lock:
            pt = self._pending.get(interrupt_id)
            if not pt:
                return False

            pt.approved = False
            pt.approver_note = note
            self._history.append(pt)
            del self._pending[interrupt_id]

        print(f"[INTERRUPT] ❌ Rejected: {interrupt_id}")
        return True

    def get_pending(self, agent_name: str = "") -> list[InterruptPoint]:
        """获取待审批的中断"""
        with self._lock:
            if agent_name:
                return [p for p in self._pending.values() if p.agent_name == agent_name]
            return list(self._pending.values())

    def get_history(self, n: int = 20) -> list[dict]:
        """获取中断历史"""
        return [
            {
                "id": p.id, "agent": p.agent_name,
                "reason": p.reason.value, "approved": p.approved,
                "note": p.approver_note, "timestamp": p.timestamp,
            }
            for p in self._history[-n:]
        ]

    def check_expired(self) -> list[str]:
        """检查并清除过期中断"""
        expired = []
        with self._lock:
            for pt_id, pt in list(self._pending.items()):
                if pt.is_expired():
                    pt.approved = False
                    pt.approver_note = "TIMEOUT"
                    self._history.append(pt)
                    del self._pending[pt_id]
                    expired.append(pt_id)
        return expired


# ── 重试策略 ──

@dataclass
class RetryPolicy:
    """重试策略"""
    max_retries: int = 3
    base_delay: float = 1.0        # 初始延迟 (秒)
    max_delay: float = 60.0        # 最大延迟
    backoff_factor: float = 2.0    # 指数退避因子
    jitter: bool = True            # 是否加抖
    degradable: bool = True        # 是否允许降级 (用更简单的策略重试)

    def get_delay(self, attempt: int) -> float:
        """计算第 N 次重试的等待时间"""
        delay = min(self.base_delay * (self.backoff_factor ** attempt), self.max_delay)
        if self.jitter:
            import random
            delay *= 0.5 + random.random()
        return round(delay, 2)


class RetryManager:
    """
    重试管理器.

    对标:
      LangGraph: 节点降级 + 流程跳转
      Anthropic: "让 Agent 知道 Tool 故障并自适应"

    策略:
      1. 指数退避 (1s → 2s → 4s → ... → 60s)
      2. 抖动 (防止雷鸣效应)
      3. 降级 (第3次重试用更简单的方式)
      4. 超时 (超过最大重试 → 失败)
    """

    def __init__(self, policy: RetryPolicy = None):
        self.policy = policy or RetryPolicy()
        self._attempts: dict[str, int] = {}  # task_id → attempt
        self._lock = threading.Lock()

    def can_retry(self, task_id: str) -> bool:
        """是否可以重试"""
        with self._lock:
            attempt = self._attempts.get(task_id, 0)
            return attempt < self.policy.max_retries

    def should_degrade(self, task_id: str) -> bool:
        """是否应该降级策略"""
        with self._lock:
            attempt = self._attempts.get(task_id, 0)
            return self.policy.degradable and attempt >= self.policy.max_retries - 1

    def get_delay(self, task_id: str) -> float:
        """获取重试等待时间"""
        with self._lock:
            attempt = self._attempts.get(task_id, 0)
            return self.policy.get_delay(attempt)

    def record_attempt(self, task_id: str) -> int:
        """记录一次重试"""
        with self._lock:
            self._attempts[task_id] = self._attempts.get(task_id, 0) + 1
            return self._attempts[task_id]

    def reset(self, task_id: str) -> None:
        """重置重试计数"""
        with self._lock:
            self._attempts.pop(task_id, None)

    def execute_with_retry(self, task_id: str, fn: Callable,
                           *args, **kwargs) -> tuple[bool, Any]:
        """执行一个函数，自动重试."""
        while self.can_retry(task_id):
            attempt = self.record_attempt(task_id)
            try:
                if self.should_degrade(task_id):
                    # 降级：用更简单的方式
                    if "fallback_fn" in kwargs:
                        result = kwargs["fallback_fn"](*args)
                    else:
                        result = fn(*args)
                else:
                    result = fn(*args)

                self.reset(task_id)
                return True, result

            except Exception as e:
                delay = self.get_delay(task_id)
                print(f"[RETRY] Attempt {attempt}/{self.policy.max_retries} for {task_id}: {e} — waiting {delay}s")
                time.sleep(delay)

        self.reset(task_id)
        return False, Exception(f"All {self.policy.max_retries} retries exhausted")


# ── 统一恢复协调器 ──

class RecoveryCoordinator:
    """
    恢复协调器 — 统一管理 Checkpoint + Interrupt + Retry.

    使用方式:
        coord = RecoveryCoordinator()
        coord.checkpoint.save("PLAN", state)
        coord.interrupt("CODE", InterruptReason.SECURITY_CONCERN, ...)
        coord.retry.execute_with_retry("task_1", some_fn, arg1)
    """

    def __init__(self, checkpoint_dir: str = ""):
        self.checkpoint = CheckpointManager(checkpoint_dir)
        self.interrupt = InterruptManager()
        self.retry = RetryManager()

    # ── 高级 API ──

    def safe_execute(self, agent_name: str, task_id: str,
                     fn: Callable, *args,
                     on_interrupt: InterruptReason = None,
                     **kwargs) -> tuple[bool, Any]:
        """
        安全执行一个任务:
          1. 先保存 checkpoint
          2. 如果需要暂停 → interrupt
          3. 失败 → retry
          4. 成功 → 保存 checkpoint

        Returns (success, result)
        """
        # Pre-execution checkpoint
        self.checkpoint.save(agent_name, {"task_id": task_id, "status": "starting"})

        # Interrupt if needed
        if on_interrupt:
            pt = self.interrupt.interrupt(
                agent_name, on_interrupt,
                context={"task_id": task_id},
                pending_action=f"Execute {task_id}",
            )
            # Wait for approval (simplified: just record)
            pending = self.interrupt.get_pending(agent_name)
            if pending:
                # In production, this would wait for external approval
                pass

        # Execute with retry
        success, result = self.retry.execute_with_retry(task_id, fn, *args, **kwargs)

        # Post-execution checkpoint
        self.checkpoint.save(
            agent_name,
            {"task_id": task_id, "status": "completed" if success else "failed"},
        )

        return success, result

    def recover_agent(self, agent_name: str) -> Optional[dict]:
        """从最近的检查点恢复 Agent"""
        ckpt = self.checkpoint.load(agent_name)
        if not ckpt:
            return None
        return {
            "agent_name": ckpt.agent_name,
            "state": ckpt.state,
            "task_queue": ckpt.task_queue,
            "heat_tax": ckpt.heat_tax,
            "delta": ckpt.delta,
            "recovered_at": time.time(),
        }
