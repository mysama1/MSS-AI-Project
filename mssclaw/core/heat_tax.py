"""
A3 热税预算 — MSS-Agent 的第一道防线.

三层热税:
  L0 物理热税 (token cost, latency)  — 权重 0.001
  L1 逻辑热税 (redundancy, loops)    — 权重 1.0
  L2 意义热税 (meaningless work)     — 权重 1000.0

如果 L2 意义热税超过 budget → 拒绝执行.

v1.1: 集成 HeatTaxFuseGroup — 三层级联熔断器.
  熔断器与预算独立运行, 熔断器处理"是否安全继续",
  预算处理"是否值得继续".
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable

from .heat_tax_fuse import (
    HeatTaxFuseGroup, FuseLevel, FuseState,
    create_fuse_group,
)


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
    threshold: float = 0.5  # S-019: 归一化阈值 (total() 范围 0-1)
    weights: dict = field(default_factory=lambda: {
        HeatTaxLevel.L0_PHYSICAL: 0.001,
        HeatTaxLevel.L1_LOGICAL: 1.0,
        HeatTaxLevel.L2_MEANING: 1000.0,
    })
    spent: dict = field(default_factory=dict)
    log: list = field(default_factory=list)
    fuse: Optional[HeatTaxFuseGroup] = None  # v1.1: 可选熔断器
    reserved: dict = field(default_factory=dict)  # S-019: task_id → estimated_tokens
    tier_thresholds: dict = field(default_factory=dict)  # S-019: per-tier limits
    _delta_ref: object = None  # S-019: delta protocol reference

    def __post_init__(self):
        for level in HeatTaxLevel:
            self.spent.setdefault(level, 0.0)
            self.tier_thresholds.setdefault(level, float('inf'))  # S-019: default infinite

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
        result = {
            "total": round(self.total(), 4),
            "L0_physical": round(self.spent[HeatTaxLevel.L0_PHYSICAL], 2),
            "L1_logical": round(self.spent[HeatTaxLevel.L1_LOGICAL], 2),
            "L2_meaning": round(self.spent[HeatTaxLevel.L2_MEANING], 2),
            "l2_dominant": self.l2_dominant(),
            "exceeded": self.exceeded(),
            "log_count": len(self.log),
        }
        if self.fuse:
            result["fuse"] = self.fuse.stats()
        return result

    # ── S-019: 任务级预分配 + Δ联动 ────────────────────────────

    def reserve(self, task_id: str, estimated_tokens: int) -> None:
        """预分配热税预算 (任务级)."""
        self.reserved[task_id] = estimated_tokens

    def release(self, task_id: str) -> None:
        """释放任务预留的热税."""
        self.reserved.pop(task_id, None)

    def link_delta(self, delta) -> None:
        """联动 Δ 协议: delta.health 下降 → 热税阈值收紧."""
        self._delta_ref = delta

    def effective_threshold(self) -> float:
        """考虑 Δ 联动后的有效阈值."""
        if not self._delta_ref:
            return self.threshold
        try:
            h = self._delta_ref.health()
            health = float(h) if h != "UNKNOWN" else 1.0
        except (ValueError, TypeError):
            return self.threshold
        if health < 0.3:
            return self.threshold * 0.5
        elif health < 0.6:
            return self.threshold * 0.75
        return self.threshold

    def tier_exceeded(self) -> tuple:
        """检查任一层级是否超阈值. 返回 (exceeded: bool, level: HeatTaxLevel)."""
        for level in HeatTaxLevel:
            if self.spent[level] > self.tier_thresholds[level]:
                return True, level
        return False, None

    # ── v1.1: 熔断器集成 ──────────────────────────────────────

    def enable_fuse(self, delta_check: Optional[Callable[[], float]] = None,
                    audit_dir: str = "") -> HeatTaxFuseGroup:
        """启用三层熔断器. 返回 fuse 对象以便外部操作."""
        self.fuse = create_fuse_group(delta_check=delta_check, audit_dir=audit_dir)
        return self.fuse

    def check_safety(self, context: str = "") -> Optional[str]:
        """
        检查当前热税状态是否触发熔断.
        如果触发 → 返回拒绝原因 (str)
        如果安全 → 返回 None
        """
        if not self.fuse:
            return None

        # 传递给熔断器的是原始裸值（未加权），不是 spent 的加权值
        l0 = self.spent[HeatTaxLevel.L0_PHYSICAL] / self.weights[HeatTaxLevel.L0_PHYSICAL]
        l1 = self.spent[HeatTaxLevel.L1_LOGICAL] / self.weights[HeatTaxLevel.L1_LOGICAL]
        l2 = self.spent[HeatTaxLevel.L2_MEANING] / self.weights[HeatTaxLevel.L2_MEANING]

        results = self.fuse.check_and_trip(l0, l1, l2, context)

        if self.fuse.l2.tripped:
            return f"L2 fuse tripped: meaning-level violation ({l2:.2f})"
        if self.fuse.l1.tripped:
            return f"L1 fuse tripped: logic redundancy ({l1:.2f}), bypass allowed"
        if self.fuse.l0.tripped:
            return f"L0 fuse tripped: resource exhausted ({l0:.2f})"
        return None

    def grad_multiplier(self) -> float:
        """梯度衰减系数. 熔断器激活时返回 <1.0."""
        if self.fuse:
            return self.fuse.grad_multiplier()
        return 1.0

    def reset_fuse_if_cooled(self) -> bool:
        """尝试复位熔断器. 返回是否有熔断器被复位."""
        if not self.fuse:
            return False
        l0 = self.spent[HeatTaxLevel.L0_PHYSICAL] / self.weights[HeatTaxLevel.L0_PHYSICAL]
        l1 = self.spent[HeatTaxLevel.L1_LOGICAL] / self.weights[HeatTaxLevel.L1_LOGICAL]
        l2 = self.spent[HeatTaxLevel.L2_MEANING] / self.weights[HeatTaxLevel.L2_MEANING]
        results = self.fuse.reset_if_cooled(l0, l1, l2)
        return any(results.values())


class HeatTaxAbort(Exception):
    """抛出此异常 = Agent 判定任务无意义, 拒绝执行."""
    pass
