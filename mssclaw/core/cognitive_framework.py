"""
Cognitive Framework v1.0 — 认知框架统一入口

Sprint 4.1: 整合 6 个碎片模块为统一的认知框架.
  认知框架 = 自知之明 + 身份稳定 + 跨语言完整 + 演化评估

四大维度:
  1. 能力自知 (Capability) — 我能做什么/不能做什么
  2. 身份锚定 (Identity) — 跨会话保持自我一致性
  3. 跨语言完整 (Lingual) — 多语言间意义不失真
  4. 演化就绪 (Evolution) — 何时演化/何时稳定

即 L2 第五支柱 — 补满热税/Delta/规范场/意义引擎/认知框架的五维防线.

用法:
    cf = CognitiveFramework()
    cf.register_capability("code_review", tier=2)
    cf.anchor_identity("mss-agent", strategy="virus")
    report = cf.assess(task_prompt)  # 综合认知评估
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum
import time


class CogStatus(Enum):
    """认知框架整体状态."""
    HEALTHY = "healthy"            # 四大维度全绿
    DEGRADED_CAPABILITY = "cap"   # 能力扩展超标
    IDENTITY_DRIFT = "identity"    # 身份漂移
    LINGUAL_LEAK = "lingual"       # 跨语言意义泄露
    EVOLUTION_IMMINENT = "evolve"  # 需要蜕壳
    CRISIS = "crisis"              # 多维度报警


@dataclass
class CognitiveAssessment:
    """综合认知评估报告."""
    status: CogStatus
    capability_tier: int = 0
    capability_count: int = 0
    identity_stability: float = 0.0
    lingual_integrity: float = 0.0
    evolution_pressure: float = 0.0
    dim_scores: dict = field(default_factory=dict)
    recommendations: list = field(default_factory=list)
    ts: float = field(default_factory=time.time)


@dataclass
class CognitiveFramework:
    """
    认知框架 — 统一的 Agent 自知之明.

    Components (lazy-imported, zero-cost when unused):
      - CapabilityLevel: register/promote/demote capabilities by tier
      - IdentityStrategy: anchor identities with virus/prompt strategies
      - CrossLingualAnchoring: analyze language-specific anchoring profiles
      - EvolutionLoop + MoltingCluster: generation + version management
    """

    capabilities: dict = field(default_factory=dict)  # {capability_name: tier}
    identities: list = field(default_factory=list)     # [IdentityStrategy, ...]
    language_profiles: dict = field(default_factory=dict)  # {lang: AnchoringProfile}
    evolution_pressure_history: list = field(default_factory=list)

    # Lazy-loaded submodules
    _cl: object = None
    _cla: object = None
    _el: object = None

    # ─── 1. Capability Self-Awareness ───

    def register_capability(self, name: str, tier: int = 1, **kwargs):
        """注册一项能力. tier: 1→C, 2→B, 3→A."""
        if self._cl is None:
            from mssclaw.core.capability_level import CapabilityLevel, CapTier
            self._cl = CapabilityLevel()
        tier_map = {1: self._cl.register.__annotations__.get('tier', None)}
        from mssclaw.core.capability_level import CapTier
        ct_map = {1: CapTier.C, 2: CapTier.B, 3: CapTier.A}
        cap_tier = ct_map.get(tier, CapTier.C)
        self._cl.register(name, cap_tier, **kwargs)
        self.capabilities[name] = tier

    def promote_capability(self, name: str) -> int:
        """升级能力. Returns new tier (1=C,2=B,3=A)."""
        if self._cl is None or name not in self.capabilities:
            return 0
        from mssclaw.core.capability_level import CapTier
        ok = self._cl.promote(name)
        if ok:
            cap = self._cl.get(name)
            tier_map = {CapTier.C: 1, CapTier.B: 2, CapTier.A: 3}
            new_tier = tier_map.get(cap.tier, self.capabilities[name])
            self.capabilities[name] = new_tier
            return new_tier
        return self.capabilities[name]

    def demote_capability(self, name: str) -> int:
        """降级能力. Returns new tier (1=C,2=B,3=A)."""
        if self._cl is None or name not in self.capabilities:
            return 0
        from mssclaw.core.capability_level import CapTier
        ok = self._cl.demote(name)
        if ok:
            cap = self._cl.get(name)
            tier_map = {CapTier.C: 1, CapTier.B: 2, CapTier.A: 3}
            new_tier = tier_map.get(cap.tier, self.capabilities[name])
            self.capabilities[name] = new_tier
            return new_tier
        return self.capabilities[name]

    def capability_tier_distribution(self) -> Dict[int, int]:
        """{1: count_T1, 2: count_T2, 3: count_T3, ...}"""
        dist = {}
        for tier in self.capabilities.values():
            dist[tier] = dist.get(tier, 0) + 1
        return dist

    # ─── 2. Identity Anchoring ───

    def anchor_identity(self, key: str, name: str, strategy: str = "virus",
                        description: str = "", hypothesis: str = "") -> object:
        """
        锚定一个身份策略.

        strategy: "virus" (A6 逻辑自约束) | "prompt" (外部声明)
        返回 IdentityStrategy 实例.
        """
        try:
            from mssclaw.core.identity_strategy import IdentityStrategy
        except Exception:
            return None

        needs_guard = (strategy == "prompt")
        is_self_guarding = (strategy == "virus")

        identity = IdentityStrategy(
            key=key, name=name,
            description=description or f"{strategy.upper()} identity for {name}",
            hypothesis=hypothesis or f"{name} maintains identity via {strategy} anchoring",
            complexity_relation="direct" if strategy == "virus" else "inverse",
            needs_guard=needs_guard,
            is_self_guarding=is_self_guarding,
        )
        self.identities.append(identity)
        return identity

    @property
    def identity_stability(self) -> float:
        """身份稳定性: virus策略 > prompt策略, 多身份 > 单身份."""
        if not self.identities:
            return 0.5  # neutral
        score = 0.0
        for id_ in self.identities:
            score += 1.0 if id_.is_self_guarding else 0.4
        return min(1.0, score / max(len(self.identities), 1))

    @property
    def identity_drift_risk(self) -> float:
        """身份漂移风险: 1 - stability."""
        return 1.0 - self.identity_stability

    # ─── 3. Cross-lingual Integrity ───

    def analyze_language(self, lang: str) -> dict:
        """
        分析语言锚定强度. 返回 {semantic_density, compaction_resistance, virus_efficacy, ...}
        """
        if self._cla is None:
            try:
                from mssclaw.core.cross_lingual_anchoring import CrossLingualAnchoring
                self._cla = CrossLingualAnchoring()
            except Exception:
                return {"error": "cross_lingual_anchoring not available"}

        profile = self._cla.analyze(lang)
        self.language_profiles[lang] = profile

        return {
            "mode": profile.mode,
            "semantic_density": profile.semantic_density,
            "compaction_resistance": profile.compaction_resistance,
            "virus_efficacy": profile.virus_efficacy_multiplier,
            "name_anchor_strength": profile.name_anchor_strength,
        }

    @property
    def lingual_integrity(self) -> float:
        """跨语言完整度: 所有已分析语言的平均 compaction_resistance."""
        if not self.language_profiles:
            return 1.0  # 未分析=假设完整
        scores = [p.compaction_resistance for p in self.language_profiles.values()]
        return sum(scores) / len(scores)

    # ─── 4. Evolution Readiness ───

    def evolution_pressure(self, delta_history: list = None, tax: object = None) -> float:
        """
        演化压力: delta趋势下降 + 热税累积 → 压力上升.

        delta_history: [{"delta": 0.8}, {"delta": 0.7}, ...]
        tax: HeatTaxBudget instance (optional)

        Returns 0.0 (稳定) to 1.0 (必须蜕壳).
        """
        pressure = 0.0

        # Delta trend: declining = pressure
        if delta_history and len(delta_history) >= 3:
            recent = [h["delta"] if isinstance(h, dict) else h.delta
                      for h in delta_history[-5:]]
            if len(recent) >= 3:
                slope = (recent[-1] - recent[0]) / max(len(recent) - 1, 1)
                pressure += max(0, -slope * 2)  # declining delta → pressure

        # Heat tax accumulation (use snapshot for correct scaling)
        if tax:
            snap = getattr(tax, 'snapshot', lambda: {'total': 0.0})()
            tax_total = snap.get('total', 0.0)
            threshold = getattr(tax, 'threshold', 3.0)
            if threshold > 0:
                pressure += min(0.5, tax_total / threshold * 0.5)

        self.evolution_pressure_history.append({
            "ts": time.time(),
            "pressure": min(1.0, pressure),
        })
        self.evolution_pressure_history = self.evolution_pressure_history[-30:]

        return min(1.0, pressure)

    def evolution_ready(self, delta_history: list = None, tax: object = None) -> bool:
        """是否需要启动蜕壳."""
        pressure = self.evolution_pressure(delta_history, tax)
        return pressure >= 0.65

    # ─── 5. Unified Assessment ───

    def assess(self, task_prompt: str = "", delta_history: list = None,
               tax: object = None) -> CognitiveAssessment:
        """
        综合认知评估: 四大维度 → 单一判定.

        调用时机: 每个推理周期结束后.
        """
        # Capability check
        cap_tiers = self.capability_tier_distribution()
        cap_count = sum(cap_tiers.values())
        cap_tier = max(cap_tiers.keys()) if cap_tiers else 0

        # Identity stability
        id_stability = self.identity_stability

        # Lingual integrity
        lang_integrity = self.lingual_integrity

        # Evolution pressure
        evo_pressure = self.evolution_pressure(delta_history, tax)

        dim_scores = {
            "capability": min(1.0, cap_count / 50),
            "identity": id_stability,
            "lingual": lang_integrity,
            "evolution": 1.0 - evo_pressure,  # higher = better
        }

        recommendations = []

        # Status determination
        if evo_pressure > 0.65 and id_stability < 0.5:
            status = CogStatus.CRISIS
            recommendations.append("CRISIS: evolution imminent + identity unstable")
        elif evo_pressure > 0.65:
            status = CogStatus.EVOLUTION_IMMINENT
            recommendations.append("Schedule molting cycle")
        elif id_stability < 0.4:
            status = CogStatus.IDENTITY_DRIFT
            recommendations.append("Re-anchor identity with virus strategy")
        elif lang_integrity < 0.5:
            status = CogStatus.LINGUAL_LEAK
            recommendations.append("Re-analyze language profiles for meaning leakage")
        elif cap_count > 100:
            status = CogStatus.DEGRADED_CAPABILITY
            recommendations.append(f"Too many capabilities ({cap_count}), consider pruning")
        else:
            status = CogStatus.HEALTHY

        return CognitiveAssessment(
            status=status,
            capability_tier=cap_tier,
            capability_count=cap_count,
            identity_stability=id_stability,
            lingual_integrity=lang_integrity,
            evolution_pressure=evo_pressure,
            dim_scores=dim_scores,
            recommendations=recommendations,
        )

    def stats(self) -> dict:
        """框架统计."""
        return {
            "capabilities": len(self.capabilities),
            "tier_distribution": self.capability_tier_distribution(),
            "identities": len(self.identities),
            "identity_stability": round(self.identity_stability, 3),
            "languages_analyzed": len(self.language_profiles),
            "lingual_integrity": round(self.lingual_integrity, 3),
            "evolution_pressure": round(
                self.evolution_pressure_history[-1]["pressure"]
                if self.evolution_pressure_history else 0.0, 3
            ),
            "status": self.assess().status.value,
        }
