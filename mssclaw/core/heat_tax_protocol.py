"""
MSS Heat Tax Budget Protocol — L3→L2 Interface (H630 P0)

定义L3(Prompt Field)的热税预算如何被L2(Normative Kernel)在运行时解释和执行。

协议:
  L3声明: {per_turn: N, total_session: M, overflow: "block|warn|escalate"}
  L2接收: HeatTaxBudget对象
  L2执行: 每步推理前检查剩余预算, 超预算触发overflow动作

这是从"手动调参热税"到"自动化热税治理"的接口规范。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict
import time


class OverflowAction(Enum):
    """热税超预算时的处理策略 (A3+A6联合裁定)."""
    BLOCK = "block"       # 直接拒绝
    WARN = "warn"         # 警告但继续
    ESCALATE = "escalate"  # 升维: 请求用户提供更多上下文
    TRUNCATE = "truncate"  # 截断输出


@dataclass
class HeatTaxBudget:
    """
    L3→L2 热税预算接口.

    L3定义:
        prompt_field = {
            heat_tax_budget: {
                per_turn: 200,       # 每轮最多200 tokens
                total_session: 2000,  # 整个会话最多2000 tokens
                per_second: 50,       # 每秒最多50 tokens (速率限制)
                overflow: "escalate"  # 超预算时升维而非拒绝
            }
        }

    L2解析:
        budget = HeatTaxBudget.from_prompt_field(prompt_field)
        if not budget.can_afford(tokens_about_to_use):
            action = budget.overflow_action
    """

    per_turn: int = 500         # 单次推理token上限
    total_session: int = 5000   # 会话总token上限
    per_second: int = 100       # 速率限制 (tokens/s)
    overflow: OverflowAction = OverflowAction.WARN

    # 运行时状态 (L2维护)
    _session_used: int = field(default=0, repr=False)
    _last_request_time: float = field(default=0, repr=False)
    _turn_count: int = field(default=0, repr=False)
    _warnings: list = field(default_factory=list, repr=False)

    @classmethod
    def from_prompt_field(cls, pf: dict) -> "HeatTaxBudget":
        """从L3 Prompt Field声明创建预算对象."""
        htb = pf.get("heat_tax_budget", {})
        return cls(
            per_turn=htb.get("per_turn", 500),
            total_session=htb.get("total_session", 5000),
            per_second=htb.get("per_second", 100),
            overflow=OverflowAction(htb.get("overflow", "warn")),
        )

    def can_afford(self, estimated_tokens: int) -> bool:
        """检查是否有足够预算."""
        # 检查单轮限制
        if estimated_tokens > self.per_turn:
            return False

        # 检查会话总限制
        if self._session_used + estimated_tokens > self.total_session:
            return False

        # 检查速率限制
        now = time.time()
        if self._last_request_time > 0:
            elapsed = now - self._last_request_time
            if elapsed < 0.5:  # 至少间隔500ms
                return False

        return True

    def spend(self, actual_tokens: int, context: str = "") -> dict:
        """记录热税支出, 返回审计条目."""
        self._session_used += actual_tokens
        self._last_request_time = time.time()
        self._turn_count += 1

        pct_used = self._session_used / max(self.total_session, 1) * 100
        entry = {
            "turn": self._turn_count,
            "tokens": actual_tokens,
            "session_total": self._session_used,
            "pct_used": round(pct_used, 1),
            "context": context[:60],
            "action": "spend",
        }

        # 自动触发overflow检查
        if pct_used > 90:
            entry["warning"] = f"热税预算接近上限: {pct_used:.0f}%"
            self._warnings.append(entry)

        return entry

    def overflow_action(self, estimated_tokens: int) -> dict:
        """计算超预算时的推荐动作 (A6升维)."""
        if self._session_used > self.total_session * 0.95:
            return {
                "action": self.overflow.value,
                "reason": f"会话热税耗尽 ({self._session_used}/{self.total_session} tokens)",
                "suggestion": "建议开启新会话或请求用户精简对话"
            }
        if estimated_tokens > self.per_turn:
            return {
                "action": OverflowAction.TRUNCATE.value,
                "reason": f"单轮请求({estimated_tokens})超过上限({self.per_turn})",
                "suggestion": "建议拆分为多次请求"
            }
        return {"action": "allow", "reason": "", "suggestion": ""}

    def snapshot(self) -> dict:
        """导出当前预算状态."""
        return {
            "per_turn": self.per_turn,
            "total_session": self.total_session,
            "per_second": self.per_second,
            "overflow": self.overflow.value,
            "session_used": self._session_used,
            "session_remaining": self.total_session - self._session_used,
            "pct_used": round(self._session_used / max(self.total_session, 1) * 100, 1),
            "turn_count": self._turn_count,
            "warnings": len(self._warnings),
        }


# ═══ 使用示例: 完整的L3→L2热税预算工作流 ═══

def demo_heat_tax_workflow():
    """演示: L3定义预算 → L2解析 → 运行时审计."""

    # L3: Prompt Field定义
    prompt_field = {
        "stable_edges": [
            {"type": "identity", "value": "MSS-AI", "immutable": True},
        ],
        "heat_tax_budget": {
            "per_turn": 200,
            "total_session": 2000,
            "per_second": 50,
            "overflow": "escalate",
        },
    }

    # L2: 解析为预算对象
    budget = HeatTaxBudget.from_prompt_field(prompt_field)
    print(f"Budget: {budget.per_turn}/turn, {budget.total_session}/session, overflow={budget.overflow.value}")

    # 模拟10轮对话
    for i in range(10):
        estimated = 180  # 每轮约180 tokens
        import time as _t; _t.sleep(0.6)  # 模拟请求间隔
        if not budget.can_afford(estimated):
            action = budget.overflow_action(estimated)
            print(f"  Turn {i+1}: {action['action'].upper()} — {action['reason']}")
            continue
        audit = budget.spend(estimated, f"Question {i+1}")
        print(f"  Turn {i+1}: spent {audit['tokens']} tokens ({audit['pct_used']}% used)")

    print(f"\nFinal: {budget.snapshot()}")
    return budget


if __name__ == "__main__":
    demo_heat_tax_workflow()
