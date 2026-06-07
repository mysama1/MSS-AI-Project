"""
A3 热税预算 — MSS-Agent 的第一道防线.

三层热税:
  L0 物理热税 (token cost, latency)  — 权重 0.001
  L1 逻辑热税 (redundancy, loops)    — 权重 1.0
  L2 意义热税 (meaningless work)     — 权重 1000.0

如果 L2 意义热税超过 budget → 拒绝执行.
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable


class HeatTaxLevel(Enum):
    """热税层级. 修复顺序: L2→L1→L0. 反了=白费."""
    L0_PHYSICAL = 0       # GPU/时间/token
    L1_LOGICAL = 1        # 冗余/重复/缓存污染
    L2_MEANING = 2        # 虚假数据/概念偷换/无意义任务


@dataclass
class HeatTaxBudget:
    """
    热税预算. 每个 Agent 实例有一个.

    threshold: 总热税上限 (0-1, 超过则拒绝)
    weights: 各层权重

    Usage:
        budget = HeatTaxBudget()
        budget.charge(HeatTaxLevel.L2_MEANING, 0.01, "生成无意义报告")
        if budget.exceeded():
            raise HeatTaxAbort("此任务无意义")
    """
    threshold: float = 2.0
    weights: dict = field(default_factory=lambda: {
        HeatTaxLevel.L0_PHYSICAL: 0.001,
        HeatTaxLevel.L1_LOGICAL: 1.0,
        HeatTaxLevel.L2_MEANING: 1000.0,
    })
    spent: dict = field(default_factory=dict)
    log: list = field(default_factory=list)

    def __post_init__(self):
        for level in HeatTaxLevel:
            self.spent.setdefault(level, 0.0)

    def charge(self, level: HeatTaxLevel, amount: float, reason: str = "") -> float:
        """
        征收热税. 返回加权后的税值.
        如果单次 L2 热税 > threshold*0.3 → 立即标记.
        """
        weighted = amount * self.weights[level]
        self.spent[level] += weighted
        self.log.append({
            "level": level.name,
            "amount": amount,
            "weighted": weighted,
            "reason": reason[:120],
            "total": self.total(),
        })
        return weighted

    def total(self) -> float:
        """当前累计热税 (归一化到 0-1)."""
        return min(sum(self.spent.values()) / 100.0, 1.0)

    def exceeded(self) -> bool:
        """热税超过阈值? 超过 → 应该停止."""
        return self.total() > self.threshold

    def l2_dominant(self) -> bool:
        """L2 意义热税占比 > 50%? → 任务的方向错了."""
        pt = sum(self.spent.values()) or 1.0
        return self.spent[HeatTaxLevel.L2_MEANING] / pt > 0.5

    def snapshot(self) -> dict:
        return {
            "total": round(self.total(), 4),
            "L0_physical": round(self.spent[HeatTaxLevel.L0_PHYSICAL], 2),
            "L1_logical": round(self.spent[HeatTaxLevel.L1_LOGICAL], 2),
            "L2_meaning": round(self.spent[HeatTaxLevel.L2_MEANING], 2),
            "l2_dominant": self.l2_dominant(),
            "exceeded": self.exceeded(),
            "log_count": len(self.log),
        }


class HeatTaxAbort(Exception):
    """抛出此异常 = Agent 判定任务无意义, 拒绝执行."""
    pass
