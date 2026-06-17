"""
Scene Router v1.0 — 方向1/2 场景抉择算法.

方向1 (多Agent精准): MCDP — 调解者 + L2.5 + 余极限消解
方向2 (单Agent容错): Phase Engine — θ相位调度 + 抗僵化自适应

抉择五维评分模型:
  1. stakes (决策代价)        ↑ → 方向1
  2. latency_req (延迟敏感)   ↑ → 方向2
  3. agent_count (Agent数量)   ↑ → 方向1
  4. duration (运行持续性)    ↑ → 混合模式
  5. resource (资源约束)      ↑ → 方向2

公式:
  s1 = w_s×stakes + w_n×log₁₀(agent_count)
  s2 = w_l×latency_req + w_r×resource
  direction = 1 if s1 > s2 + threshold else 2
  if duration > D_CRITICAL: mode = "hybrid" (direction 2 daily + direction 1 periodic)
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Literal
from enum import Enum


Direction = Literal[1, 2, "hybrid"]


class SceneProfile(Enum):
    """预设场景模板."""
    HIGH_STAKES = "high_stakes"       # 法律/医疗
    REALTIME = "realtime"             # 聊天/游戏NPC
    LONG_RUNNING = "long_running"     # 客服/教育
    RESOURCE_CONSTRAINED = "resource" # 移动端/IoT
    CRITICAL_BATCH = "critical_batch" # 批量关键决策
    EXPLORATORY = "exploratory"       # 研究/探索


@dataclass
class SceneContext:
    """场景上下文 — 供抉择引擎输入."""
    # 核心五维 (0-1归一化)
    stakes: float = 0.5           # 决策代价 (0=无后果, 1=不可逆)
    latency_req: float = 0.5      # 延迟敏感 (0=可等, 1=必须即时)
    agent_count: int = 1           # 参与Agent数量
    duration_hours: float = 1.0    # 预期运行时长
    resource_tight: float = 0.5    # 资源约束 (0=无限算力, 1=极端受限)

    # 附加特征
    requires_audit: bool = False   # 需要审计追踪
    max_heat_tax_budget: float = float('inf')  # 热税预算上限
    description: str = ""


# ═══════════════════════════════════════════════════════
# 核心抉择引擎
# ═══════════════════════════════════════════════════════

class SceneRouter:
    """
    场景抉择路由器.

    五维评分 → 方向推荐 → 配置输出.

    设计原则:
      - 方向1 = 精准优先: 最高成功率 + 保真度, 热税不是首要约束
      - 方向2 = 效率优先: 低延迟 + 低热税, 可接受偶尔次优
      - 混合 = 方向2为主 + 方向1定期校准

    阈值来源: MeanFieldMCDP 实证 tension 消解率 + PhaseEngine 滞回防抖数据
    """

    # ── 默认权重 ──
    DEFAULT_WEIGHTS = {
        "stakes": 0.35,       # 决策代价权重
        "latency": 0.30,      # 延迟敏感权重
        "agent_count": 0.15,  # Agent数量权重 (对数压缩)
        "duration": 0.10,     # 运行持续权重
        "resource": 0.10,     # 资源约束权重
    }

    # ── 关键阈值 ──
    BIAS_THRESHOLD = 0.15        # s1-s2 > 0.15 → 方向1, < -0.15 → 方向2, 中间 → closest
    D_CRITICAL_HOURS = 24.0       # 超过24h → 考虑混合模式
    AGENT_CRITICAL = 3            # Agent >= 3 → 方向1加分
    HEAT_TAX_CRITICAL = 0.8       # 热税预算 < 0.8 → 方向2强制

    # ── 预设场景 (可直接查表) ──
    PRESET_SCENES = {
        SceneProfile.HIGH_STAKES: SceneContext(
            stakes=0.95, latency_req=0.30, agent_count=1,
            duration_hours=2.0, resource_tight=0.40,
            requires_audit=True,
            description="高 stakes 决策 (法律、医疗)",
        ),
        SceneProfile.REALTIME: SceneContext(
            stakes=0.35, latency_req=0.95, agent_count=1,
            duration_hours=0.1, resource_tight=0.60,
            requires_audit=False,
            description="实时交互 (聊天、游戏NPC)",
        ),
        SceneProfile.LONG_RUNNING: SceneContext(
            stakes=0.55, latency_req=0.50, agent_count=1,
            duration_hours=720.0, resource_tight=0.40,
            requires_audit=True,
            description="长期运行系统 (客服、教育)",
        ),
        SceneProfile.RESOURCE_CONSTRAINED: SceneContext(
            stakes=0.40, latency_req=0.70, agent_count=1,
            duration_hours=0.05, resource_tight=0.95,
            requires_audit=False,
            description="资源受限环境 (移动端、IoT)",
        ),
        SceneProfile.CRITICAL_BATCH: SceneContext(
            stakes=0.90, latency_req=0.20, agent_count=5,
            duration_hours=4.0, resource_tight=0.30,
            requires_audit=True,
            description="批量关键决策 (风控、合规)",
        ),
        SceneProfile.EXPLORATORY: SceneContext(
            stakes=0.25, latency_req=0.30, agent_count=1,
            duration_hours=168.0, resource_tight=0.50,
            requires_audit=False,
            description="研究/探索",
        ),
    }

    def __init__(self, weights: dict = None, custom_scenes: dict = None):
        self.weights = weights or dict(self.DEFAULT_WEIGHTS)
        self.scenes = dict(self.PRESET_SCENES)
        if custom_scenes:
            self.scenes.update(custom_scenes)

    # ── 主入口: 场景 → 方向 ──

    def route(self, ctx: SceneContext) -> Dict:
        """
        对给定场景上下文进行抉择.

        Returns:
            {
                "direction": 1 | 2 | "hybrid",
                "confidence": 0-1,
                "reason": "简短理由",
                "scores": {"direction_1": float, "direction_2": float},
                "recommendation": {
                    "module": "mcdp" | "phase_engine" | "adaptive_topophase",
                    "config": {...},
                },
                "heat_tax_estimate": float,
            }
        """
        # 计算方向得分
        s1, s2 = self._score(ctx)

        # 热税预算约束
        if ctx.max_heat_tax_budget < self.HEAT_TAX_CRITICAL:
            # 热税预算极紧 → 强制方向2
            direction: Direction = 2
            reason = "热税预算不足，强制方向2"
            confidence = 0.95
        else:
            delta = s1 - s2

            if delta > self.BIAS_THRESHOLD:
                direction = 1
                confidence = min(1.0, 0.7 + abs(delta) * 0.5)
                reason = self._reason_direction_1(ctx, delta)
            elif delta < -self.BIAS_THRESHOLD:
                direction = 2
                confidence = min(1.0, 0.7 + abs(delta) * 0.5)
                reason = self._reason_direction_2(ctx, abs(delta))
            else:
                # 模糊区: 选最近的
                direction = 1 if delta >= 0 else 2
                confidence = 0.5 + abs(delta) * 1.5
                reason = f"模糊区: s1={s1:.2f} s2={s2:.2f}, 偏向方向{direction}"

        # 持续时间 → 混合模式判定
        mode = direction
        if ctx.duration_hours > self.D_CRITICAL_HOURS:
            # 长期运行 → 混合模式: 无论基础方向1还是2, 都应定期用1校准
            mode = "hybrid"
            tag = " (日常方向2 + 定期方向1校准)" if direction == 2 else ""
            reason += f"; 持续 {ctx.duration_hours:.0f}h > {self.D_CRITICAL_HOURS}h → 混合模式{tag}"

        # Agent数量 → 方向1推荐加强
        if ctx.agent_count >= self.AGENT_CRITICAL and direction == 2:
            # 多Agent场景被方向2抢了 → 警告
            reason += f"; ⚠ N={ctx.agent_count} Agent, 方向2可能不适用"

        # 模块推荐
        module_config = self._recommend_module(mode, ctx)
        heat_tax = self._estimate_heat_tax(ctx, mode)

        return {
            "direction": mode,
            "confidence": round(confidence, 3),
            "reason": reason,
            "scores": {"direction_1": round(s1, 4), "direction_2": round(s2, 4)},
            "recommendation": module_config,
            "heat_tax_estimate": round(heat_tax, 4),
        }

    # ── 五维评分 ──

    def _score(self, ctx: SceneContext) -> Tuple[float, float]:
        """计算方向1和方向2的得分."""
        w = self.weights

        # 方向1得分 (精准优先)
        # 高 stakes + 多Agent → 方向1
        agent_log = math.log10(max(1, ctx.agent_count))
        s1 = (
            w["stakes"] * ctx.stakes
            + w["agent_count"] * min(1.0, agent_log / 2.0)  # log10(100)=2.0 封顶
            + w["duration"] * min(1.0, ctx.duration_hours / self.D_CRITICAL_HOURS)
            # 低延迟需求 → 方向1 (可以接受等待)
            + w["latency"] * (1.0 - ctx.latency_req)
        )

        # 方向2得分 (效率优先)
        # 高延迟敏感 + 资源紧 → 方向2
        s2 = (
            w["latency"] * ctx.latency_req
            + w["resource"] * ctx.resource_tight
            # 低 stakes → 方向2 (可以接受次优)
            + w["stakes"] * (1.0 - ctx.stakes)
            # 单Agent → 方向2
            + w["agent_count"] * (1.0 - min(1.0, agent_log / 2.0))
        )

        return s1, s2

    # ── 理由生成 ──

    def _reason_direction_1(self, ctx: SceneContext, delta: float) -> str:
        parts = []
        if ctx.stakes > 0.7:
            parts.append(f"高代价决策 (stakes={ctx.stakes:.2f})")
        if ctx.agent_count >= self.AGENT_CRITICAL:
            parts.append(f"多Agent协作 (N={ctx.agent_count})")
        if ctx.requires_audit:
            parts.append("需要审计追踪")
        if not parts:
            parts.append(f"综合评分偏高 (Δ={delta:.2f})")
        return f"方向1推荐: {'; '.join(parts)}"

    def _reason_direction_2(self, ctx: SceneContext, delta: float) -> str:
        parts = []
        if ctx.latency_req > 0.7:
            parts.append(f"低延迟需求 (latency={ctx.latency_req:.2f})")
        if ctx.resource_tight > 0.7:
            parts.append(f"资源受限 (resource={ctx.resource_tight:.2f})")
        if ctx.stakes < 0.3:
            parts.append(f"低代价场景 (stakes={ctx.stakes:.2f})")
        if not parts:
            parts.append(f"综合效率优先 (Δ={delta:.2f})")
        return f"方向2推荐: {'; '.join(parts)}"

    # ── 模块推荐 ──

    def _recommend_module(self, direction: Direction, ctx: SceneContext) -> Dict:
        """根据方向和场景推荐具体模块和配置."""
        if direction == 1 or direction == "hybrid":
            # 方向1核心模块
            module = "mcdp"  # MCDP v0.2 支持 N>2
            config = {
                "engine": "mean_field_mcdp",
                "gossip_rounds": min(30, max(5, int(ctx.agent_count * 3))),
                "normative_stack": "decentralized",
                "convergence_eps": 0.01 if ctx.stakes > 0.7 else 0.05,
                "audit_enabled": ctx.requires_audit,
            }
            if ctx.agent_count == 1:
                module = "phase_engine"  # 单Agent用PhaseEngine
                config = {
                    "engine": "adaptive_topophase",
                    "hysteresis": 0.15,
                    "vitality_check": True,
                }
        else:
            module = "adaptive_topophase"
            config = {
                "engine": "adaptive_topophase",
                "hysteresis": 0.2 if ctx.latency_req > 0.8 else 0.15,
                "vitality_check": True,
                "reanchor_interval": 100,
                "drift_tolerance": 0.3,
            }

        if direction == "hybrid":
            config["hybrid"] = {
                "daily": "adaptive_topophase",
                "periodic": "mcdp",
                "calibration_interval_hours": min(168, max(24, ctx.duration_hours / 30)),
            }

        return {"module": module, "config": config}

    # ── 热税估计 ──

    def _estimate_heat_tax(self, ctx: SceneContext, direction: Direction) -> float:
        """估计热税消耗."""
        # 基础热税系数
        base = {
            1: 0.15,      # 方向1: 高精准度 → 额外热税
            2: 0.02,      # 方向2: 低延迟 → 低热税
            "hybrid": 0.05,  # 混合: 中等
        }[direction]

        # Agent数量加成
        agent_factor = math.log2(max(1, ctx.agent_count)) * 0.01

        # 持续时间加成 (每小时累加热税)
        duration_factor = ctx.duration_hours * 0.001

        heat_tax = base + agent_factor + duration_factor

        # 受资源约束限制
        if ctx.resource_tight > 0.7:
            heat_tax *= 0.5  # 资源紧 → 降低热税

        return min(1.0, heat_tax)

    # ── 快捷方法 ──

    def route_by_profile(self, profile: SceneProfile) -> Dict:
        """按预设场景直接抉择."""
        ctx = self.scenes.get(profile)
        if not ctx:
            return {"error": f"Unknown profile: {profile}"}
        result = self.route(ctx)
        result["profile"] = profile.value
        result["description"] = ctx.description
        return result

    def route_all_profiles(self) -> List[Dict]:
        """对所有预设场景进行抉择."""
        results = []
        for profile in SceneProfile:
            r = self.route_by_profile(profile)
            results.append(r)
        return results

    def route_custom(self, stakes: float = 0.5, latency_req: float = 0.5,
                     agent_count: int = 1, duration_hours: float = 1.0,
                     resource_tight: float = 0.5, requires_audit: bool = False,
                     max_heat_tax: float = 999.0, description: str = "") -> Dict:
        """自定义参数快捷抉择."""
        return self.route(SceneContext(
            stakes=stakes, latency_req=latency_req,
            agent_count=agent_count, duration_hours=duration_hours,
            resource_tight=resource_tight, requires_audit=requires_audit,
            max_heat_tax_budget=max_heat_tax, description=description,
        ))


# ═══════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════

def cmd_router(args_rest):
    """CLI: mssclaw route"""
    if not args_rest or args_rest[0] == "--help":
        print("mssclaw route — MSS 场景抉择路由器")
        print()
        print("  mssclaw route all          对所有预设场景抉择")
        print("  mssclaw route <profile>    按预设场景抉择")
        print("  mssclaw route custom ...   自定义参数")
        print()
        print("Profiles:", ", ".join(p.value for p in SceneProfile))
        print()
        print("Custom: route custom stakes=0.9 latency=0.3 agents=3 duration=2")
        return

    router = SceneRouter()
    cmd = args_rest[0]

    if cmd == "all":
        _print_table(router.route_all_profiles())
        return

    if cmd in [p.value for p in SceneProfile]:
        profile = SceneProfile(cmd)
        r = router.route_by_profile(profile)
        _print_single(r)
        return

    if cmd == "custom":
        # Parse key=value pairs
        kwargs = {
            "stakes": 0.5, "latency_req": 0.5, "agent_count": 1,
            "duration_hours": 1.0, "resource_tight": 0.5,
            "requires_audit": False, "max_heat_tax": 999.0,
        }
        for arg in args_rest[1:]:
            if "=" in arg:
                k, v = arg.split("=", 1)
                if k in kwargs:
                    if k in ("agent_count",):
                        kwargs[k] = int(v)
                    elif k == "requires_audit":
                        kwargs[k] = v.lower() in ("true", "1", "yes")
                    else:
                        kwargs[k] = float(v)
        r = router.route_custom(**kwargs)
        _print_single(r)
        return

    print(f"Unknown: {cmd}")


def _print_single(r: Dict):
    """格式化输出单个结果."""
    d = r["direction"]
    emoji = {1: "🎯", 2: "⚡", "hybrid": "🔄"}
    print(f"\n  {emoji.get(d, '❓')} Direction: {d}")
    print(f"  Confidence: {r['confidence']:.2%}")
    print(f"  Reason: {r['reason']}")
    print(f"  Scores: D1={r['scores']['direction_1']:.4f} D2={r['scores']['direction_2']:.4f}")
    mod = r.get("recommendation", {})
    print(f"  Module: {mod.get('module', 'N/A')}")
    if "hybrid" in mod.get("config", {}):
        h = mod["config"]["hybrid"]
        print(f"  Mode: daily={h['daily']} + calibration(every {h['calibration_interval_hours']:.0f}h)={h['periodic']}")
    print(f"  Heat Tax Est: {r['heat_tax_estimate']:.4f}")


def _print_table(results: List[Dict]):
    """格式化输出表格."""
    print(f"\n{'═'*80}")
    print(f"  MSS 场景抉择路由 — 方向 1 vs 方向 2")
    print(f"{'═'*80}")
    print(f"  {'场景':<20} {'方向':<8} {'置信度':<8} {'D1分':<8} {'D2分':<8} {'热税':<6}")
    print(f"  {'─'*20} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*6}")

    for r in results:
        d = r["direction"]
        emoji = {1: "🎯", 2: "⚡", "hybrid": "🔄"}.get(d, "")
        profile_name = r.get("profile", "?")
        print(f"  {profile_name:<20} {emoji} {str(d):<5}"
              f" {r['confidence']:<7.0%} "
              f"{r['scores']['direction_1']:<8.4f} "
              f"{r['scores']['direction_2']:<8.4f} "
              f"{r['heat_tax_estimate']:<6.4f}")

    print(f"  {'─'*20} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*6}")
    print()

    # 逐场景理由
    for r in results:
        d = r["direction"]
        emoji = {1: "🎯", 2: "⚡", "hybrid": "🔄"}.get(d, "")
        print(f"  {emoji} {r.get('profile','?'):<20} → {r['reason']}")


# ═══════════════════════════════════════════════════════
# Demo + Test
# ═══════════════════════════════════════════════════════

def _demo():
    """演示所有预设场景 + 自定义."""
    router = SceneRouter()
    _print_table(router.route_all_profiles())

    print(f"\n{'═'*80}")
    print("  自定义场景测试")
    print(f"{'═'*80}")

    # 高Agent数场景
    print("\n  [Custom] 风控场景: stakes=0.95, agents=10, latency=0.2")
    r = router.route_custom(0.95, 0.20, 10, 4.0, 0.30, True, description="风控")
    _print_single(r)

    # 极端资源受限
    print("\n  [Custom] IoT边缘: stakes=0.3, agents=1, latency=0.9, resource=0.99")
    r = router.route_custom(0.30, 0.90, 1, 0.01, 0.99, False, 0.3, description="IoT")
    _print_single(r)

    # 热税预算极紧
    print("\n  [Custom] 热税预算不足: stakes=0.8, agents=3, heat_tax=0.2")
    r = router.route_custom(0.80, 0.40, 3, 2.0, 0.50, True, 0.2, description="tight_budget")
    _print_single(r)


def _test_all():
    """测试套件."""
    passed = 0
    total = 0

    router = SceneRouter()

    # 1. 预设场景匹配
    total += 1
    r = router.route_by_profile(SceneProfile.HIGH_STAKES)
    assert r["direction"] == 1, f"high_stakes should be 1, got {r['direction']}"
    passed += 1
    print(f"  ✅ 高代价→方向1")

    total += 1
    r = router.route_by_profile(SceneProfile.REALTIME)
    assert r["direction"] == 2, f"realtime should be 2, got {r['direction']}"
    passed += 1
    print(f"  ✅ 实时→方向2")

    total += 1
    r = router.route_by_profile(SceneProfile.LONG_RUNNING)
    assert r["direction"] == "hybrid", f"long_running should be hybrid, got {r['direction']}"
    passed += 1
    print(f"  ✅ 长期→混合模式")

    total += 1
    r = router.route_by_profile(SceneProfile.RESOURCE_CONSTRAINED)
    assert r["direction"] == 2, f"resource should be 2, got {r['direction']}"
    passed += 1
    print(f"  ✅ 资源受限→方向2")

    # 2. 热税预算强制
    total += 1
    r = router.route_custom(stakes=0.9, max_heat_tax=0.1)
    assert r["direction"] == 2, f"tight heat tax should force direction 2, got {r['direction']}"
    passed += 1
    print(f"  ✅ 热税不足→强制方向2")

    # 3. 多Agent场景
    total += 1
    r = router.route_custom(stakes=0.6, agent_count=10)
    assert r["direction"] == 1, f"multi-agent should be direction 1, got {r['direction']}"
    passed += 1
    print(f"  ✅ 多Agent→方向1")

    # 4. 分数单调性
    total += 1
    r_low = router.route_custom(stakes=0.1, agent_count=1)
    r_high = router.route_custom(stakes=0.9, agent_count=10)
    assert r_high["scores"]["direction_1"] > r_low["scores"]["direction_1"], "stakes monotonicity"
    passed += 1
    print(f"  ✅ 分数单调性")

    print(f"\n  {passed}/{total} PASS")


if __name__ == "__main__":
    import sys
    if not sys.argv[1:]:
        _demo()
    elif sys.argv[1] == "test":
        _test_all()
    else:
        cmd_router(sys.argv[1:])
