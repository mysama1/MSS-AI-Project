"""
defer_guard v1.0 — H648 postcondition gate (逆优先级闭锁)

defer_after = "此操作不能执行，直到后置条件全部满足"
不是低优先级 — 是不同排序轴的closure-dependent约束。

对称于 H634 joint_enter (precondition gate).
两者合为完整临界区: safe enter + safe exit.

Usage:
    from mssclaw.core.defer_guard import DeferGuard, defer_after

    # 声明式标注
    @defer_after(["git_push", "artifact_write"])
    def restart_gateway():
        ...

    # 调度前检查
    guard = DeferGuard()
    guard.satisfy("git_push")
    guard.satisfy("artifact_write")
    guard.can_execute(restart_gateway)  # True

    # 紧急覆盖 (需人工确认)
    guard.force_execute(restart_gateway, reason="emergency")
"""
from __future__ import annotations
import time
import json
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set
from enum import Enum


class DeferState(Enum):
    PENDING = "pending"       # 后置条件未满足，阻塞
    READY = "ready"           # 全部满足，可执行
    FORCED = "forced"         # 紧急覆盖
    TIMED_OUT = "timed_out"   # 超时降级
    EXECUTED = "executed"     # 已执行


@dataclass
class DeferredAction:
    """带闭锁约束的操作."""
    name: str
    defer_after: List[str]           # 后置条件列表
    state: DeferState = DeferState.PENDING
    registered_at: float = field(default_factory=time.time)
    force_reason: Optional[str] = None
    executed_at: Optional[float] = None

    def satisfied(self, completed: Set[str]) -> bool:
        """检查所有后置条件是否满足."""
        return all(c in completed for c in self.defer_after)

    def missing(self, completed: Set[str]) -> Set[str]:
        """返回未满足的条件."""
        return set(self.defer_after) - completed


class DeferGuard:
    """
    逆优先级闭锁守卫.

    维护两个集合:
      completed:  批次中已完成的后置条件 (如 git_push, artifact_write)
      deferred:   等待闭锁的操作队列
    """

    def __init__(self):
        self._completed: Set[str] = set()
        self._deferred: Dict[str, DeferredAction] = {}
        self._history: List[DeferredAction] = []

    # ── 后置条件管理 ──

    def satisfy(self, condition: str) -> None:
        """标记一个后置条件为已完成."""
        self._completed.add(condition)

    def is_satisfied(self, condition: str) -> bool:
        return condition in self._completed

    def reset_batch(self) -> None:
        """新批次：清空已满足条件."""
        self._completed.clear()

    # ── 操作注册与检查 ──

    def register(self, name: str, defer_after: List[str]) -> DeferredAction:
        """注册一个带闭锁约束的操作."""
        action = DeferredAction(name=name, defer_after=defer_after)
        self._deferred[name] = action
        return action

    def can_execute(self, name_or_action: str | DeferredAction) -> tuple[bool, Set[str]]:
        """
        检查操作是否可以执行.
        Returns: (can_execute, missing_conditions)
        """
        if isinstance(name_or_action, str):
            action = self._deferred.get(name_or_action)
            if action is None:
                return True, set()  # 未注册=无约束
        else:
            action = name_or_action

        if action.state == DeferState.FORCED:
            return True, set()

        missing = action.missing(self._completed)
        return len(missing) == 0, missing

    def execute(self, name: str, force: bool = False, force_reason: str = "") -> tuple[bool, str]:
        """
        尝试执行操作.
        Returns: (success, message)
        """
        action = self._deferred.get(name)
        if action is None:
            return True, f"'{name}': no defer constraint → allowed"

        if force:
            action.state = DeferState.FORCED
            action.force_reason = force_reason
            action.executed_at = time.time()
            self._history.append(action)
            return True, f"'{name}': FORCED override (reason: {force_reason})"

        ok, missing = self.can_execute(action)
        if ok:
            action.state = DeferState.EXECUTED
            action.executed_at = time.time()
            self._history.append(action)
            return True, f"'{name}': all conditions met → executing"

        return False, f"'{name}': BLOCKED — missing: {missing}"

    # ── 声明式装饰器 ──

    @staticmethod
    def wrap_with_defer(name: str, conditions: List[str]):
        """创建带闭锁约束的函数包装器 (用于装饰器模式)."""
        def decorator(fn):
            fn.__defer_after__ = conditions
            fn.__defer_name__ = name
            return fn
        return decorator

    # ── 查询 ──

    def pending(self) -> List[DeferredAction]:
        """列出所有未满足条件的操作."""
        return [a for a in self._deferred.values()
                if a.state == DeferState.PENDING and not a.satisfied(self._completed)]

    def status(self) -> dict:
        return {
            "completed": sorted(self._completed),
            "deferred": {name: {"state": a.state.value, "missing": list(a.missing(self._completed))}
                         for name, a in self._deferred.items()},
            "ready_count": sum(1 for a in self._deferred.values() if a.satisfied(self._completed)),
            "blocked_count": sum(1 for a in self._deferred.values() if not a.satisfied(self._completed)),
        }

    def snapshot(self) -> dict:
        """导出当前闭锁状态."""
        return self.status()

    def load_snapshot(self, data: dict) -> None:
        """恢复闭锁状态."""
        self._completed = set(data.get("completed", []))
        for name, info in data.get("deferred", {}).items():
            action = self._deferred.get(name)
            if action:
                action.state = DeferState(info.get("state", "pending"))


# ── 单例 ──
_guard: Optional[DeferGuard] = None

def get_guard() -> DeferGuard:
    global _guard
    if _guard is None:
        _guard = DeferGuard()
    return _guard

def reset_guard() -> None:
    global _guard
    _guard = DeferGuard()


# ── 预定义的危险操作闭锁约束 ──
DANGEROUS_ACTIONS = {
    "gateway_restart":   ["git_push", "artifact_write", "commit"],
    "server_shutdown":   ["all_connections_drained", "metrics_saved"],
    "model_unload":      ["all_inference_complete"],
    "db_vacuum":         ["all_writes_complete", "backup_done"],
    "cleanup_temp":      ["all_experiments_done"],
}


def auto_register_dangerous_actions(guard: Optional[DeferGuard] = None) -> DeferGuard:
    """自动注册预定义的危险操作闭锁约束."""
    g = guard or get_guard()
    for name, conditions in DANGEROUS_ACTIONS.items():
        g.register(name, conditions)
    return g


# ── 装饰器语法糖 ──
def defer_after(conditions: List[str]):
    """
    装饰器: 标注函数必须在指定条件完成后才能执行.

    @defer_after(["git_push", "artifact_write"])
    def restart_gateway():
        ...
    """
    def decorator(fn):
        name = fn.__name__
        fn.__defer_after__ = conditions
        fn.__defer_name__ = name
        guard = get_guard()
        guard.register(name, conditions)
        return fn
    return decorator
