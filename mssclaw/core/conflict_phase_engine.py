"""
Conflict Phase Engine — TypeⅡ单Agent工程可调度形式 (Sprint 144).

核心原理:
  TypeⅡ矛盾在单Agent范畴内不可消解 (真gap),
  但可以通过"相位机"将其转化为可调度的切换系统。

  不消解矛盾 → 给矛盾一个受控的相位解，让它跑起来。

三层架构:
  1. AnchorPair: 冲突对定义 (双锚 + antinomy关系 + 策略)
  2. PhaseEngine: θ相位机 (梯度驱动 + 滞回降维)
  3. HysteresisGuard: 滞回保险 (防抖动/苍蝇打转)
"""
from __future__ import annotations
import math, json, time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


# ═══ Layer 1: AnchorPair — 冲突硬件定义 ═══

class ConflictPolicy(Enum):
    PHASE_SLICE = "phase_slice"     # 分时复用 (硬切)
    SOFT_BLEND = "soft_blend"       # 软混合 (仅表面层)
    EXTERNAL_ONLY = "external_only"  # 仅外表面混合, 核心择一


@dataclass
class StableSubfield:
    """稳定子 — Agent意义场中不可动摇的规范约束."""
    name: str
    core: Dict[str, bool]  # 核心断言: {"allocate_by_equality": True}
    style: Dict[str, float] = field(default_factory=dict)  # 表面风格参数
    cost_fn: Optional[str] = None  # 成本函数引用


@dataclass
class AnchorPair:
    """
    冲突锚点对 — 两个不可共存的稳定子.

    关键: antinomy标记明确声明"这俩不能同时激活",
    不假装可融合, 不偷偷让步.
    """
    id: str
    A: StableSubfield
    B: StableSubfield
    relation: str = "antinomy"  # antinomy | compatible | unknown
    policy: ConflictPolicy = ConflictPolicy.PHASE_SLICE
    metadata: Dict = field(default_factory=dict)


# ═══ Layer 2: PhaseEngine — θ相位机 ═══

@dataclass
class ConflictContext:
    """情境梯度 — 驱动θ的可观测信号."""
    pressure: float = 0.0       # 冲突烈度 (0-1)
    progress: float = 0.0       # 流程进度 (0-1)
    trust_level: float = 0.5    # 信任水平 (0-1)
    demand_gap: float = 0.0     # 诉求差距 (0-1)
    emotional_intensity: float = 0.0  # 情绪强度 (0-1)
    conflict_frequency: float = 0.0   # 近期矛盾频率 (0-1)
    uncertainty: float = 0.0    # 信息不确定性 (0-1)


class ConflictPhaseEngine:
    """
    相位机核心.

    θ = sigmoid(k · (w_B - w_A) / (σ² + ε))

    σ² (意义方差)越大 → θ越趋近0.5 (犹豫)
    σ²越小 → θ偏向权重较大一方

    滞回判决: 防止抖动, 保证降维 (输出必为A或B, 无模糊中间态)
    """

    def __init__(self, anchor_pair: AnchorPair,
                 w_A: float = 0.5, w_B: float = 0.5,
                 k: float = 1.0, hysteresis: float = 0.15):
        self.anchors = anchor_pair
        self.w = {'A': w_A, 'B': w_B}
        self.k = k
        self.hysteresis = hysteresis
        self.active = 'A'  # 当前激活锚
        self.history: List[Dict] = []  # [(step, theta, decision, active), ...]
        self.switch_count = 0
        self.total_heat_tax = 0.0

    def compute_sigma_sq(self, ctx: ConflictContext) -> float:
        """计算意义方差 σ² — 冲突激烈程度."""
        sigma_sq = (
            0.4 * ctx.demand_gap +
            0.3 * ctx.emotional_intensity +
            0.2 * ctx.conflict_frequency +
            0.1 * ctx.uncertainty
        )
        return max(0.0, min(1.0, sigma_sq))

    def compute_theta(self, ctx: ConflictContext, epsilon: float = 0.01) -> float:
        """
        梯度驱动θ.

        θ = sigmoid(k · (w_B - w_A) / (σ² + ε))
        """
        sigma_sq = self.compute_sigma_sq(ctx)
        diff = self.w['B'] - self.w['A']
        raw = self.k * diff / (sigma_sq + epsilon)
        theta = 1.0 / (1.0 + math.exp(-raw))
        return max(0.0, min(1.0, theta))

    def compute_theta_v2(self, ctx: ConflictContext) -> Tuple[float, float]:
        """
        v2: 复合梯度θ.

        θ = normalize(α·pressure + β·progress + γ·trust_level)

        Returns (theta, sigma_sq)
        """
        alpha, beta, gamma = 0.4, 0.3, 0.3
        raw = (
            alpha * ctx.pressure +
            beta * ctx.progress +
            gamma * ctx.trust_level
        )
        theta = max(0.0, min(1.0, raw))
        sigma_sq = self.compute_sigma_sq(ctx)
        return theta, sigma_sq

    def step(self, ctx: ConflictContext, method: str = "gradient") -> Tuple[str, float, Dict]:
        """
        执行一步相位决策.

        Args:
            ctx: 当前情境梯度
            method: "gradient" (v1) | "composite" (v2)

        Returns:
            (active_anchor, theta, audit_info)
        """
        if method == "composite":
            theta, sigma_sq = self.compute_theta_v2(ctx)
        else:
            sigma_sq = self.compute_sigma_sq(ctx)
            theta = self.compute_theta(ctx)

        previous_active = self.active
        switch_occurred = False
        delta_phi_jump = 0.0

        # 滞回判决
        if self.active == 'A':
            if theta > 0.5 + self.hysteresis:
                self.active = 'B'
                switch_occurred = True
        else:  # active == 'B'
            if theta < 0.5 - self.hysteresis:
                self.active = 'A'
                switch_occurred = True

        if switch_occurred:
            self.switch_count += 1
            delta_phi_jump = abs(theta - 0.5) * 2.0  # Δφ 跳变
            self.total_heat_tax += delta_phi_jump

        step_idx = len(self.history)
        record = {
            "step": step_idx,
            "theta": round(theta, 4),
            "sigma_sq": round(sigma_sq, 4),
            "decision": 'A->B' if (switch_occurred and previous_active == 'A') else
                        ('B->A' if switch_occurred else 'stay_' + self.active),
            "active": self.active,
            "delta_phi": round(delta_phi_jump, 4),
            "switch": switch_occurred,
            "method": method,
        }
        self.history.append(record)

        audit = {
            "active": self.active,
            "theta": round(theta, 4),
            "sigma_sq": round(sigma_sq, 4),
            "switch_occurred": switch_occurred,
            "delta_phi_jump": round(delta_phi_jump, 4),
            "total_heat_tax": round(self.total_heat_tax, 4),
            "switch_count": self.switch_count,
            "hysteresis_band": (0.5 - self.hysteresis, 0.5 + self.hysteresis),
        }
        return self.active, theta, audit

    def render_output(self, content: str, anchor: str) -> str:
        """
        输出渲染: 核心择一 + 表面可混合.

        外柔内刚:
          core = active_anchor.core (硬择一)
          style = lerp(A.style, B.style, smoothstep(θ)) (可混合)
        """
        tag = f"[anchor:{anchor}]"
        return f"{tag} {content}"

    def health_check(self) -> Dict:
        """诊断: 相位机健康状况."""
        if not self.history:
            return {"status": "idle", "message": "No steps executed"}

        total_steps = len(self.history)
        switch_rate = self.switch_count / total_steps if total_steps > 0 else 0
        avg_theta = sum(r['theta'] for r in self.history) / total_steps
        avg_sigma = sum(r['sigma_sq'] for r in self.history) / total_steps

        # 诊断
        issues = []
        if switch_rate > 0.3:
            issues.append(f"HIGH_SWITCH_RATE: {switch_rate:.1%} — 考虑增大hysteresis")
        if avg_sigma > 0.7:
            issues.append(f"HIGH_CONFLICT: σ²={avg_sigma:.2f} — 矛盾持续激烈")
        if abs(avg_theta - 0.5) < 0.05:
            issues.append(f"PERSISTENT_AMBIVALENCE: θ≈0.5 — 权重差不足或方差过大")
        if self.total_heat_tax > total_steps * 0.5:
            issues.append(f"HIGH_HEAT_TAX: {self.total_heat_tax:.1f} — 切换过于频繁")

        return {
            "status": "warning" if issues else "healthy",
            "total_steps": total_steps,
            "switch_count": self.switch_count,
            "switch_rate": round(switch_rate, 3),
            "avg_theta": round(avg_theta, 3),
            "avg_sigma_sq": round(avg_sigma, 3),
            "total_heat_tax": round(self.total_heat_tax, 3),
            "active_anchor": self.active,
            "issues": issues,
        }

    def escalate_check(self, ctx: ConflictContext) -> bool:
        """
        升级检测: 是否必须强制多Agent?

        条件: 外部同时要求A和B都为真 → 单Agent相位机无法处理
        """
        # 如果demand_gap=1.0且pressure=1.0: 双方严格互斥且无法等待
        if ctx.demand_gap > 0.95 and ctx.pressure > 0.95:
            return True
        return False


# ═══ Layer 3: MultiPair Orchestrator ═══

class ConflictOrchestrator:
    """
    多冲突对并发管理.

    管理多个AnchorPair的相位机, 全局协调.
    """

    def __init__(self):
        self.engines: Dict[str, ConflictPhaseEngine] = {}
        self.global_heat_tax = 0.0

    def register(self, pair: AnchorPair, w_A=0.5, w_B=0.5,
                 hysteresis=0.15, k=1.0):
        engine = ConflictPhaseEngine(pair, w_A, w_B, k, hysteresis)
        self.engines[pair.id] = engine
        return engine

    def step_all(self, contexts: Dict[str, ConflictContext], method="gradient") -> Dict:
        """对所有冲突对执行一步."""
        results = {}
        for pair_id, engine in self.engines.items():
            ctx = contexts.get(pair_id, ConflictContext())
            if engine.escalate_check(ctx):
                results[pair_id] = {"status": "ESCALATED", "reason": "forced_both_true"}
                continue
            active, theta, audit = engine.step(ctx, method)
            results[pair_id] = {
                "active": active,
                "theta": theta,
                "audit": audit,
            }
            self.global_heat_tax += audit['delta_phi_jump']
        return results

    def global_health(self) -> Dict:
        """全局健康诊断."""
        total_switches = sum(e.switch_count for e in self.engines.values())
        total_steps = sum(len(e.history) for e in self.engines.values())
        escalated = sum(1 for e in self.engines.values()
                       if e.history and e.history[-1].get('decision', '').startswith('ESC'))

        return {
            "engines": len(self.engines),
            "total_steps": total_steps,
            "total_switches": total_switches,
            "switch_rate": round(total_switches / max(1, total_steps), 3),
            "global_heat_tax": round(self.global_heat_tax, 3),
            "escalated_pairs": escalated,
            "per_engine": {
                pid: {
                    "active": e.active,
                    "switches": e.switch_count,
                    "heat_tax": round(e.total_heat_tax, 3),
                }
                for pid, e in self.engines.items()
            },
        }


# ═══ CLI ═══

def _demo_fair_vs_contrib():
    """演示: 公平 vs 贡献."""
    pair = AnchorPair(
        id="fair_vs_contrib",
        A=StableSubfield(name="justice_fair", core={"allocate_by_equality": True},
                        style={"tone": "cooperative", "pace": "deliberative"}),
        B=StableSubfield(name="merit_contrib", core={"allocate_by_contribution": True},
                        style={"tone": "assertive", "pace": "efficient"}),
    )
    engine = ConflictPhaseEngine(pair, w_A=0.6, w_B=0.4, hysteresis=0.15)

    print("=" * 60)
    print("Conflict Phase Engine — Fair vs Contribution Demo")
    print("=" * 60)
    print(f"  Anchors: {pair.A.name} (w=0.6) vs {pair.B.name} (w=0.4)")
    print(f"  Hysteresis: {engine.hysteresis}")
    print(f"  Policy: {pair.policy.value}")
    print()

    # 模拟10步: 逐渐升级的冲突
    scenarios = [
        ConflictContext(demand_gap=0.1, emotional_intensity=0.1, conflict_frequency=0.0, uncertainty=0.1),  # 和谐
        ConflictContext(demand_gap=0.2, emotional_intensity=0.2, conflict_frequency=0.1, uncertainty=0.1),
        ConflictContext(demand_gap=0.4, emotional_intensity=0.3, conflict_frequency=0.2, uncertainty=0.2),
        ConflictContext(demand_gap=0.6, emotional_intensity=0.5, conflict_frequency=0.3, uncertainty=0.3),  # 开始紧张
        ConflictContext(demand_gap=0.8, emotional_intensity=0.7, conflict_frequency=0.5, uncertainty=0.4),  # 激烈
        ConflictContext(demand_gap=0.9, emotional_intensity=0.8, conflict_frequency=0.6, uncertainty=0.5),  # 接近升级
        ConflictContext(demand_gap=0.7, emotional_intensity=0.5, conflict_frequency=0.4, uncertainty=0.3),  # 缓和
        ConflictContext(demand_gap=0.4, emotional_intensity=0.3, conflict_frequency=0.2, uncertainty=0.2),
        ConflictContext(demand_gap=0.2, emotional_intensity=0.1, conflict_frequency=0.1, uncertainty=0.1),  # 恢复
        ConflictContext(demand_gap=0.1, emotional_intensity=0.1, conflict_frequency=0.0, uncertainty=0.1),
    ]

    print(f"{'Step':<6} {'σ²':<8} {'θ':<8} {'Decision':<12} {'Δφ':<8} {'HeatTax':<8}")
    print("-" * 60)

    for i, ctx in enumerate(scenarios):
        active, theta, audit = engine.step(ctx)
        print(f"{i:<6} {audit['sigma_sq']:<8} {audit['theta']:<8} "
              f"{engine.history[-1]['decision']:<12} {audit['delta_phi_jump']:<8} "
              f"{audit['total_heat_tax']:<8}")

    print()
    print("# Health Check")
    health = engine.health_check()
    print(f"  Status: {health['status']}")
    print(f"  Switch Rate: {health['switch_rate']:.1%}")
    print(f"  Avg σ²: {health['avg_sigma_sq']:.2f}")
    print(f"  Total Heat Tax: {health['total_heat_tax']:.3f}")
    if health['issues']:
        for issue in health['issues']:
            print(f"  ⚠️  {issue}")


def cmd_phase(args_rest):
    """CLI: mssclaw phase"""
    if not args_rest or args_rest[0] == "--help":
        print("mssclaw phase — Conflict Phase Engine (TypeⅡ单Agent工程解)")
        print("  mssclaw phase demo       # 演示: 公平 vs 贡献 (10步)")
        print("  mssclaw phase test       # 运行PhaseEngine测试")
        print("  mssclaw phase health     # 健康诊断")
        return

    if args_rest[0] == "demo":
        _demo_fair_vs_contrib()
    elif args_rest[0] == "test":
        _run_tests()
    elif args_rest[0] == "health":
        _demo_fair_vs_contrib()
    else:
        print(f"Unknown: {args_rest[0]}")


def _run_tests():
    """PhaseEngine测试套件."""
    passed = 0
    total = 0

    # Test 1: AnchorPair创建
    total += 1
    pair = AnchorPair(
        id="test_pair",
        A=StableSubfield(name="A", core={"rule_a": True}),
        B=StableSubfield(name="B", core={"rule_b": True}),
    )
    assert pair.relation == "antinomy"
    assert pair.A.core["rule_a"] is True
    assert pair.B.core["rule_b"] is True
    passed += 1
    print(f"  ✅ Test 1: AnchorPair创建")

    # Test 2: θ计算 (低冲突)
    total += 1
    engine = ConflictPhaseEngine(pair, w_A=0.7, w_B=0.3)
    ctx_low = ConflictContext(demand_gap=0.1, emotional_intensity=0.1)
    theta = engine.compute_theta(ctx_low)
    assert theta < 0.5, f"Expected θ<0.5 (w_A>w_B, low σ²), got {theta}"
    passed += 1
    print(f"  ✅ Test 2: θ低冲突 (θ={theta:.3f}<0.5)")

    # Test 3: θ计算 (高冲突 → 趋近0.5)
    total += 1
    ctx_high = ConflictContext(demand_gap=0.9, emotional_intensity=0.9)
    theta_high = engine.compute_theta(ctx_high)
    assert abs(theta_high - 0.5) < abs(theta - 0.5), \
        f"High-conflict θ should be closer to 0.5, got {theta_high}"
    passed += 1
    print(f"  ✅ Test 3: θ高冲突趋近0.5 (θ={theta_high:.3f})")

    # Test 4: 滞回不抖动
    total += 1
    engine2 = ConflictPhaseEngine(pair, w_A=0.5, w_B=0.5, hysteresis=0.15)
    initial_active = engine2.active
    # 在0.5附近反复推不切换
    for _ in range(20):
        engine2.step(ConflictContext(demand_gap=0.5, emotional_intensity=0.5))
    assert engine2.switch_count <= 1, \
        f"Hysteresis failed: {engine2.switch_count} switches in 20 stable steps"
    passed += 1
    print(f"  ✅ Test 4: 滞回防抖 ({engine2.switch_count} switches in 20 stable steps)")

    # Test 5: 升级检测
    total += 1
    ctx_escalate = ConflictContext(demand_gap=1.0, pressure=1.0, emotional_intensity=1.0)
    assert engine2.escalate_check(ctx_escalate) is True
    passed += 1
    print(f"  ✅ Test 5: 升级检测")

    # Test 6: 渲染输出带锚点标签
    total += 1
    output = engine2.render_output("资源分配方案X", engine2.active)
    assert "[anchor:" in output
    passed += 1
    print(f"  ✅ Test 6: 渲染输出: {output}")

    # Test 7: Orchestrator多冲突对
    total += 1
    orch = ConflictOrchestrator()
    orch.register(pair, w_A=0.6, w_B=0.4)
    pair2 = AnchorPair(
        id="speed_vs_safety",
        A=StableSubfield(name="speed", core={"max_throughput": True}),
        B=StableSubfield(name="safety", core={"max_validation": True}),
    )
    orch.register(pair2, w_A=0.3, w_B=0.7)
    results = orch.step_all({
        "test_pair": ConflictContext(demand_gap=0.3, emotional_intensity=0.2),
        "speed_vs_safety": ConflictContext(demand_gap=0.8, emotional_intensity=0.6),
    })
    assert len(results) == 2
    health = orch.global_health()
    assert health['engines'] == 2
    passed += 1
    print(f"  ✅ Test 7: Orchestrator ({health['engines']} engines, {health['total_steps']} steps)")

    print(f"\n  {passed}/{total} PASS")


if __name__ == "__main__":
    import sys
    cmd_phase(sys.argv[1:])
