"""
热税熔断器 — MSS 保护带的工程实现.

将"热税熔断"从比喻沉降为可操作机制:
  1. 阈值设定: H_threshold = α·H_L0 + β·H_L1 + γ·H_L2
  2. 复位逻辑: 热税降回 30% + Δ>0 → RESET, 否则 DEGRADE
  3. 级联规则: L0(阻断) → L1(绕行) → L2(审计+Δ检测)
  4. 梯度交互: 熔断激活时梯度置零/衰减, 阻止灾难性遗忘

不与 RLHF / EWC / LoRA 竞争——在反向传播通道里插入不依赖梯度的保护逻辑.
"""
from __future__ import annotations

import time, json, os, threading
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Callable

# ── 熔断层级 ───────────────────────────────────────────────────────

class FuseLevel(Enum):
    """熔断层级 — 越高越不可逆."""
    L0_PHYSICAL = 0   # 物理资源耗尽 → 直接阻断, 不回主循环
    L1_LOGICAL  = 1   # 代码/逻辑冗余 → 拒绝当前路径, 允许绕行
    L2_MEANING   = 2   # 意义破坏 (伪命题/意义偷换) → 拒绝+审计+Δ检测


# ── 熔断状态 ───────────────────────────────────────────────────────

@dataclass
class FuseState:
    """单个熔断器的状态."""
    level: FuseLevel
    tripped: bool = False
    trip_count: int = 0
    last_trip: float = 0.0  # timestamp
    cooldown_ms: int = 30000  # 默认 30s 冷却
    total_blocked: int = 0

    def trip(self) -> None:
        self.tripped = True
        self.trip_count += 1
        self.total_blocked += 1
        self.last_trip = time.time()

    def can_reset(self, heat_current: float, threshold: float) -> bool:
        """复位条件: 热税降到阈值 30% 以下 AND 冷却时间已过."""
        cooled = (time.time() - self.last_trip) * 1000 > self.cooldown_ms
        below_threshold = heat_current < threshold * 0.3
        return cooled and below_threshold

    def reset(self) -> None:
        self.tripped = False


# ── 熔断器组 — 三层级联 ────────────────────────────────────────────

@dataclass
class HeatTaxFuseGroup:
    """
    三层级联熔断器.

    级联逻辑:
      L0 触发 → 直接阻断, 不检查 L1/L2
      L1 触发 → 拒绝当前路径, 允许绕行 (衰减梯度到 10%)
      L2 触发 → 拒绝输出 + 写入审计 + 触发 Δ 检测 (梯度置零)

    用法:
        fuses = HeatTaxFuseGroup()
        fuses.check_and_trip(l0_heat, l1_heat, l2_heat)
        if fuses.is_blocked():
            return DEGRADED_RESPONSE
    """
    # 三层熔断器
    l0: FuseState = field(default_factory=lambda: FuseState(FuseLevel.L0_PHYSICAL, cooldown_ms=10000))
    l1: FuseState = field(default_factory=lambda: FuseState(FuseLevel.L1_LOGICAL, cooldown_ms=60000))
    l2: FuseState = field(default_factory=lambda: FuseState(FuseLevel.L2_MEANING, cooldown_ms=300000))  # 5min

    # 权重: L2 的破坏力是 L0 的 10⁶ 倍
    alpha: float = 0.001   # L0 物理热税
    beta:  float = 1.0     # L1 逻辑热税
    gamma: float = 1000.0  # L2 意义热税

    # 熔断阈值
    l0_threshold: float = 0.85
    l1_threshold: float = 0.70
    l2_threshold: float = 0.50  # 意义层最敏感

    # Δ 维持条件回调 (外部注入)
    delta_check: Optional[Callable[[], float]] = None  # 返回当前 Δ 值
    delta_min: float = 0.0  # Δ 必须 > 此值才允许复位

    # 审计日志
    audit_log: List[dict] = field(default_factory=list)
    audit_path: str = ""

    def __post_init__(self):
        if self.audit_path:
            os.makedirs(os.path.dirname(self.audit_path) or ".", exist_ok=True)

    # ── 阈值计算 ────────────────────────────────────────────────

    def compute_threshold(self, l0_heat: float, l1_heat: float, l2_heat: float) -> float:
        """H_threshold = α·H_L0 + β·H_L1 + γ·H_L2"""
        return self.alpha * l0_heat + self.beta * l1_heat + self.gamma * l2_heat

    # ── 级联探测 ─────────────────────────────────────────────────

    def check_and_trip(self, l0_heat: float, l1_heat: float, l2_heat: float,
                       context: str = "") -> Dict[FuseLevel, bool]:
        """
        按级联顺序检查三个熔断器. 返回各层触发状态.

        级联规则: L0 阻断 → L1 允许绕行 → L2 触发审计+Δ检测
        """
        results = {}

        # L0: 物理层 — 最快, 代价最小
        if l0_heat > self.l0_threshold:
            self.l0.trip()
            results[FuseLevel.L0_PHYSICAL] = True
            self._audit(FuseLevel.L0_PHYSICAL, l0_heat, context, "blocked: resource exhausted")
            return results  # L0 阻断后不检查 L1/L2
        results[FuseLevel.L0_PHYSICAL] = False

        # L1: 逻辑层 — 拒绝当前路径但允许绕行
        if l1_heat > self.l1_threshold:
            self.l1.trip()
            results[FuseLevel.L1_LOGICAL] = True
            self._audit(FuseLevel.L1_LOGICAL, l1_heat, context, "rejected path, bypass allowed")
        else:
            results[FuseLevel.L1_LOGICAL] = False

        # L2: 意义层 — 最重, 不可逆
        if l2_heat > self.l2_threshold:
            self.l2.trip()
            results[FuseLevel.L2_MEANING] = True
            self._audit(FuseLevel.L2_MEANING, l2_heat, context, "rejected: meaning-level violation, Δ check triggered")
        else:
            results[FuseLevel.L2_MEANING] = False

        return results

    # ── 状态查询 ─────────────────────────────────────────────────

    def is_blocked(self) -> bool:
        """是否任一熔断器处于触发状态."""
        return self.l0.tripped or self.l1.tripped or self.l2.tripped

    def highest_tripped(self) -> Optional[FuseLevel]:
        """返回触发的最严重层级."""
        if self.l2.tripped:
            return FuseLevel.L2_MEANING
        if self.l1.tripped:
            return FuseLevel.L1_LOGICAL
        if self.l0.tripped:
            return FuseLevel.L0_PHYSICAL
        return None

    def grad_multiplier(self) -> float:
        """返回梯度衰减系数.

        - L2 触发 → 0 (梯度置零, 阻止灾难性遗忘)
        - L1 触发 → 0.1 (衰减到 10%, 允许微弱信号)
        - L0 触发 → 0 (完全阻断)
        - 无触发 → 1.0 (正常)
        """
        if self.l2.tripped or self.l0.tripped:
            return 0.0
        if self.l1.tripped:
            return 0.1
        return 1.0

    # ── 复位逻辑 ─────────────────────────────────────────────────

    def reset_if_cooled(self, l0_heat: float, l1_heat: float, l2_heat: float) -> Dict[FuseLevel, bool]:
        """检查各层是否可以复位. 返回复位结果."""
        results = {}

        # 每层用自己的 raw heat 和 own threshold 做冷却判断
        for fuse, own_heat, own_threshold in [
            (self.l0, l0_heat, self.l0_threshold),
            (self.l1, l1_heat, self.l1_threshold),
            (self.l2, l2_heat, self.l2_threshold),
        ]:
            if fuse.tripped and fuse.can_reset(own_heat, own_threshold):
                # Δ 检查 (仅 L2 需要)
                if fuse.level == FuseLevel.L2_MEANING and self.delta_check:
                    delta = self.delta_check()
                    if delta <= self.delta_min:
                        results[fuse.level] = False
                        self._audit(fuse.level, own_heat, "reset denied: Δ closed", f"Δ={delta:.4f}")
                        continue
                fuse.reset()
                results[fuse.level] = True
                self._audit(fuse.level, own_heat, "reset", f"heat={own_heat:.4f}")
            else:
                results[fuse.level] = False

        return results

    # ── 梯度交互 ─────────────────────────────────────────────────

    def backprop_guard(self, model_params: list, loss: float,
                       l0_heat: float = 0.0, l1_heat: float = 0.0, l2_heat: float = 0.0,
                       context: str = "") -> float:
        """
        在反向传播前检查熔断状态.

        Returns:
            实际使用的 loss (可能被置零)
        """
        self.check_and_trip(l0_heat, l1_heat, l2_heat, context=context)
        mult = self.grad_multiplier()

        if mult == 0.0:
            for p in model_params:
                if p.grad is not None:
                    p.grad.zero_()
            self._audit(FuseLevel.L2_MEANING, 0.0, context, f"grad halted: multiplier={mult}")
            return 0.0
        elif mult < 1.0:
            for p in model_params:
                if p.grad is not None:
                    p.grad.mul_(mult)
            self._audit(FuseLevel.L1_LOGICAL, 0.0, context, f"grad attenuated: multiplier={mult}")
            return loss * mult

        return loss

    # ── 审计 ──────────────────────────────────────────────────────

    def _audit(self, level: FuseLevel, heat: float, context: str, action: str) -> None:
        entry = {
            "ts": time.time(),
            "level": level.name,
            "heat": round(heat, 6),
            "action": action,
            "context": context[:200],
        }
        self.audit_log.append(entry)

        if self.audit_path:
            with open(self.audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ── 统计 ──────────────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "l0": {"tripped": self.l0.tripped, "count": self.l0.trip_count, "blocked": self.l0.total_blocked},
            "l1": {"tripped": self.l1.tripped, "count": self.l1.trip_count, "blocked": self.l1.total_blocked},
            "l2": {"tripped": self.l2.tripped, "count": self.l2.trip_count, "blocked": self.l2.total_blocked},
            "audit_entries": len(self.audit_log),
        }


# ── 便捷工厂 ───────────────────────────────────────────────────────

def create_fuse_group(delta_check: Optional[Callable[[], float]] = None,
                      audit_dir: str = "") -> HeatTaxFuseGroup:
    """创建默认配置的熔断器组."""
    fg = HeatTaxFuseGroup(delta_check=delta_check)
    if audit_dir:
        os.makedirs(audit_dir, exist_ok=True)
        fg.audit_path = os.path.join(audit_dir, "fuse_audit.jsonl")
    return fg


# ── 自测 ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== HeatTaxFuse 自测 ===\n")

    # 模拟 Δ 检查
    _delta_state = 0.5
    def mock_delta():
        return _delta_state

    fuses = create_fuse_group(delta_check=mock_delta)

    # 测试 1: 正常状态
    results = fuses.check_and_trip(0.1, 0.2, 0.1, "test: normal")
    print(f"[normal]  blocked={fuses.is_blocked()}  grad_mult={fuses.grad_multiplier()}")
    assert not fuses.is_blocked()

    # 测试 2: L1 触发 (逻辑冗余)
    results = fuses.check_and_trip(0.1, 0.85, 0.1, "test: logic loop detected")
    print(f"[L1 trip] blocked={fuses.is_blocked()}  grad_mult={fuses.grad_multiplier()}")
    assert fuses.is_blocked()
    assert fuses.highest_tripped() == FuseLevel.L1_LOGICAL

    # 测试 3: L2 触发 (意义破坏)
    fuses.reset_if_cooled(0, 0, 0)  # 冷复位 L1 (force cooldown)
    fuses.l1.tripped = False
    results = fuses.check_and_trip(0.1, 0.2, 0.9, "test: meaningless prompt injection")
    print(f"[L2 trip] blocked={fuses.is_blocked()}  grad_mult={fuses.grad_multiplier()}")
    assert fuses.is_blocked()
    assert fuses.highest_tripped() == FuseLevel.L2_MEANING

    # 测试 4: reset_if_cooled
    fuses.l2.last_trip = time.time() - 400  # 假装 400s 前触发
    results = fuses.reset_if_cooled(0.1, 0.1, 0.1)
    print(f"[reset]  l0={results[FuseLevel.L0_PHYSICAL]} l1={results[FuseLevel.L1_LOGICAL]} l2={results[FuseLevel.L2_MEANING]}")
    assert results[FuseLevel.L2_MEANING]

    # 测试 5: Δ=0 时拒绝复位
    fuses.l2.trip()
    _delta_state = 0.0  # Δ 闭合
    fuses.l2.last_trip = time.time() - 400
    results = fuses.reset_if_cooled(0.1, 0.1, 0.1)
    print(f"[Δ=0]   l2 reset={results[FuseLevel.L2_MEANING]}  (should be False)")
    assert not results[FuseLevel.L2_MEANING]

    print(f"\n[stats] {json.dumps(fuses.stats(), indent=2)}")
    print(f"[audit] {len(fuses.audit_log)} entries")
    print("\n✅ All tests passed")
