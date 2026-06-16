"""
L2 Bridge v1.0 — 热税↔Δ 双向自适应耦合

Sprint 3 核心模块: 将两个独立工作的 L2 防线整合为单一反馈回路.

耦合方向:
  Δ↓ (健康下降) → 热税阈值收紧 (effective_threshold)
  热税↑ (预算告警) → Δ 审计加速 (触发更深层模式分析)

设计原则 (H593 范畴论统一):
  两个模块不是"通信"关系, 是同一认知动力学的两个投影.
  Δ 测量的是意义场的开放度 (A6),
  热税测量的是意义场的闭合度 (A3).
  它们是互补的, 应该共变而非独立.

用法:
  bridge = L2Bridge()
  tax.link_delta(delta)          # HeatTax ← Δ (已有)
  bridge.link(tax, delta)        # 双向链接
  bridge.step()                  # 每个任务周期调用一次

三层响应:
  LEVEL 0: Δ正常 + 热税正常 → 无操作
  LEVEL 1: Δ warning + 热税接近阈值 → 收紧阈值 20%
  LEVEL 2: Δ molting + 热税超阈值 → 熔断 + 触发蜕壳
  LEVEL 3: Δ collapse + L2 意义税爆表 → 紧急拒绝所有输入
"""
import time
import math
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class BridgeLevel(Enum):
    """桥接响应等级."""
    STABLE = 0       # 两个都正常
    CAUTION = 1      # 一方预警
    STRESS = 2       # 双方预警
    CRISIS = 3       # 双方告急


@dataclass
class L2Bridge:
    """
    L2 双向桥.

    tax: HeatTaxBudget 实例 (需要 _delta_ref 已 set)
    delta: DeltaProtocol 实例
    """
    tax: object = None
    delta: object = None
    level: BridgeLevel = BridgeLevel.STABLE
    history: list = field(default_factory=list)  # [{ts, level, tax_total, delta_health}]
    _hysteresis: float = 0.0  # 防抖累积

    def link(self, tax, delta) -> None:
        """建立双向桥接."""
        self.tax = tax
        self.delta = delta
        # Ensure one-way link exists
        if not getattr(tax, '_delta_ref', None):
            tax._delta_ref = delta

    def step(self) -> BridgeLevel:
        """
        每个任务周期调用.
        评估双方状态 → 决定响应等级 → 调整参数 → 返回新等级.
        """
        if not self.tax or not self.delta:
            return BridgeLevel.STABLE

        # Read states
        ds = self.delta.snapshot()
        ts = self.tax.snapshot()

        delta_health = ds.get("current_delta", 1.0) or 1.0
        delta_pattern = ds.get("pattern", "healthy")
        molting = ds.get("molting_alert", False)
        tax_total = ts.get("total", 0)
        tax_threshold = ts.get("threshold", 2.0)
        tax_ratio = tax_total / max(tax_threshold, 0.01)
        l2_spent = ts.get("L2_meaning", 0)
        l2_ratio = l2_spent / max(tax_threshold * 1000, 0.01)  # L2 weight ≈ 1000x

        # ── Level determination ──
        if delta_pattern == "collapse" or (molting and tax_ratio > 0.8):
            new_level = BridgeLevel.CRISIS
        elif molting or delta_pattern == "decline" or tax_ratio > 0.7 or l2_ratio > 0.5:
            new_level = BridgeLevel.STRESS
        elif (delta_health < self.delta.min_delta * 1.5) or tax_ratio > 0.5:
            new_level = BridgeLevel.CAUTION
        else:
            new_level = BridgeLevel.STABLE

        # ── Hysteresis: prevent oscillation ──
        if new_level != self.level:
            self._hysteresis += 0.25
            if self._hysteresis >= 1.0:
                self.level = new_level
                self._hysteresis = 0.0
                self._apply_level()
        else:
            self._hysteresis = max(0.0, self._hysteresis - 0.1)

        # Record
        self.history.append({
            "ts": time.time(), "level": self.level.name,
            "tax_total": round(tax_total, 3), "tax_ratio": round(tax_ratio, 3),
            "delta_health": round(delta_health, 3), "pattern": delta_pattern,
            "l2_ratio": round(l2_ratio, 3),
        })
        self.history = self.history[-50:]

        return self.level

    def _apply_level(self):
        """根据响应等级调整双方参数."""
        level_actions = {
            BridgeLevel.STABLE: (1.0, 1.0),    # (tax_threshold_mult, delta_min_mult)
            BridgeLevel.CAUTION: (0.8, 1.0),
            BridgeLevel.STRESS: (0.55, 1.3),
            BridgeLevel.CRISIS: (0.3, 1.6),
        }
        tax_mult, delta_mult = level_actions[self.level]

        # Store originals on first application
        if not hasattr(self, '_orig_tax_threshold'):
            self._orig_tax_threshold = self.tax.threshold
            self._orig_delta_min = self.delta.min_delta

        self.tax.threshold = self._orig_tax_threshold * tax_mult
        self.delta.min_delta = self._orig_delta_min * delta_mult

    def reset(self):
        """恢复到初始参数."""
        if hasattr(self, '_orig_tax_threshold'):
            self.tax.threshold = self._orig_tax_threshold
        if hasattr(self, '_orig_delta_min'):
            self.delta.min_delta = self._orig_delta_min
        self.level = BridgeLevel.STABLE
        self._hysteresis = 0.0

    def stats(self) -> dict:
        return {
            "level": self.level.name,
            "hysteresis": round(self._hysteresis, 2),
            "history_len": len(self.history),
            "transitions": sum(
                1 for i in range(1, len(self.history))
                if self.history[i]["level"] != self.history[i-1]["level"]
            ),
        }
