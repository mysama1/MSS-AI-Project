"""
Sprint 3-4 单元测试 — L2桥 + 规范盾 + 漂移协调 + 认知框架 + Dashboard.

测试覆盖:
  test_l2_bridge_stable_to_crisis     L2Bridge 四级状态转换
  test_l2_bridge_hysteresis           防抖不振荡
  test_norm_shield_sync               31规则→盾映射
  test_norm_shield_cross_validate     4种交叉验证
  test_drift_compaction_policy        4种压缩策略
  test_drift_compaction_slope         漂移斜率计算
  test_cognitive_register            能力注册+升级+降级
  test_cognitive_identity            身份锚定 virus/prompt
  test_cognitive_language            跨语言分析
  test_cognitive_evolution           演化压力+就绪判定
  test_cognitive_assess              综合评估
  test_dashboard_health_score        健康评分算法
  test_dashboard_json_mode           JSON模式输出
"""
from __future__ import annotations
import sys, os, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ═══════════════════════════════════════════════════
# L2 Bridge (Sprint 3.1)
# ═══════════════════════════════════════════════════

def test_l2_bridge_stable_to_crisis():
    """L2Bridge: STABLE→CAUTION→STRESS→CRISIS 四级转换."""
    from mssclaw.core.l2_bridge import L2Bridge, BridgeLevel
    from mssclaw.core.heat_tax import HeatTaxBudget, HeatTaxLevel
    from mssclaw.core.delta import DeltaProtocol

    tax = HeatTaxBudget(threshold=2.0)
    delta = DeltaProtocol(min_delta=0.3)
    bridge = L2Bridge()
    bridge.link(tax, delta)

    # Start stable
    assert bridge.level == BridgeLevel.STABLE

    # Degrade delta + step each time (hysteresis needs consecutive steps)
    for i in range(10):
        delta.tick("same_task", 0.1, 0.1)
        bridge.step()

    assert bridge.level in (BridgeLevel.CAUTION, BridgeLevel.STRESS), \
        f"Expected CAUTION or STRESS, got {bridge.level}"

    # Push tax to trigger STRESS/CRISIS
    for j in range(15):
        tax.charge(HeatTaxLevel.L2_MEANING, 0.2, "meaning waste")
        bridge.step()

    assert bridge.level in (BridgeLevel.STRESS, BridgeLevel.CRISIS), \
        f"Expected STRESS or CRISIS, got {bridge.level}"


def test_l2_bridge_hysteresis():
    """L2Bridge: 防抖不振荡."""
    from mssclaw.core.l2_bridge import L2Bridge, BridgeLevel
    from mssclaw.core.heat_tax import HeatTaxBudget, HeatTaxLevel
    from mssclaw.core.delta import DeltaProtocol

    tax = HeatTaxBudget(threshold=2.0)
    delta = DeltaProtocol(min_delta=0.4)
    bridge = L2Bridge()
    bridge._hysteresis = 0.0
    bridge.link(tax, delta)

    transitions = []
    for i in range(20):
        if i % 2 == 0:
            delta.tick(f"good_{i}", 0.9, 0.9)
        else:
            delta.tick(f"bad_{i}", 0.1, 0.1)
            tax.charge(HeatTaxLevel.L2_MEANING, 0.05, "noise")
        prev = bridge.level
        bridge.step()
        if bridge.level != prev:
            transitions.append((i, prev.name, bridge.level.name))

    # Hysteresis prevents oscillation — alternating good/bad shouldn't flip every time
    assert len(transitions) < 10, \
        f"Too many transitions ({len(transitions)}), hysteresis broken"


# ═══════════════════════════════════════════════════
# NormShield Bridge (Sprint 3.2)
# ═══════════════════════════════════════════════════

def test_norm_shield_sync():
    """NormShieldBridge: 31规则→盾映射."""
    from mssclaw.core.normative_field import NormativeField
    from mssclaw.core.norm_shield_bridge import NormShieldBridge

    nf = NormativeField()
    nf.load_defaults()
    bridge = NormShieldBridge()
    n = bridge.sync_rules(nf)

    assert n >= 20, f"Expected >=20 rules, got {n}"
    assert len(bridge.mapped_patterns) == n
    for mp in bridge.mapped_patterns:
        assert mp.shield_type in ("Type1", "Type2", "Type3", "Type4")
        assert len(mp.detection_keywords) > 0


def test_norm_shield_cross_validate():
    """NormShieldBridge: 4种交叉验证."""
    from mssclaw.core.norm_shield_bridge import NormShieldBridge, CrossVerdict

    bridge = NormShieldBridge()

    assert bridge.cross_validate(["a"], ["b"]) == CrossVerdict.HIGH_CONFIDENCE
    assert bridge.cross_validate(["a"], []) == CrossVerdict.NORM_ONLY
    assert bridge.cross_validate([], ["b"]) == CrossVerdict.SHIELD_ONLY
    assert bridge.cross_validate([], []) == CrossVerdict.PASS
    assert len(bridge.history) == 4


# ═══════════════════════════════════════════════════
# Drift-Compaction Guard (Sprint 3.3)
# ═══════════════════════════════════════════════════

def test_drift_compaction_policy():
    """DriftCompactionGuard: 4种压缩策略."""
    from mssclaw.core.drift_compaction_guard import DriftCompactionGuard, CompactionPolicy
    from mssclaw.core.drift_guard import DriftGuard
    from mssclaw.core.compaction_guard import CompactionGuard

    dc = DriftCompactionGuard()
    dc.register(DriftGuard(), CompactionGuard())

    # No drift: SAFE
    assert dc.should_compact() == CompactionPolicy.SAFE

    # High drift: DEFER
    dc.record_drift(0.95, ["negation lost"])
    dc.record_drift(0.88, ["scope creep"])
    dc.record_drift(0.92, ["source drift"])
    assert dc.should_compact() == CompactionPolicy.DEFER

    # After compact: DEFER (cooldown)
    dc.after_compact()
    assert dc.should_compact() in (CompactionPolicy.DEFER, CompactionPolicy.RESET)

    # Clear cooldown, memory pressure
    dc._last_compaction_ts = 0
    dc._drift_history = []
    dc.record_drift(0.1, [])
    assert dc.should_compact({"total": 90, "max_items": 100}) == CompactionPolicy.URGENT


def test_drift_compaction_slope():
    """DriftCompactionGuard: 漂移斜率."""
    from mssclaw.core.drift_compaction_guard import DriftCompactionGuard
    from mssclaw.core.drift_guard import DriftGuard
    from mssclaw.core.compaction_guard import CompactionGuard

    dc = DriftCompactionGuard()
    dc.register(DriftGuard(), CompactionGuard())

    # Increasing drift
    for s in [0.1, 0.3, 0.5, 0.7, 0.9]:
        dc.record_drift(s, [])
    assert dc.drift_slope() > 0

    # Decreasing drift
    dc._drift_history = []
    for s in [0.9, 0.7, 0.5, 0.3, 0.1]:
        dc.record_drift(s, [])
    assert dc.drift_slope() < 0


# ═══════════════════════════════════════════════════
# Cognitive Framework (Sprint 4.1)
# ═══════════════════════════════════════════════════

def test_cognitive_register():
    """CognitiveFramework: 能力注册+升级+降级."""
    from mssclaw.core.cognitive_framework import CognitiveFramework

    cf = CognitiveFramework()
    cf.register_capability("scan", tier=1)
    cf.register_capability("audit", tier=2)
    cf.register_capability("defend", tier=3)

    assert len(cf.capabilities) == 3
    assert cf.capability_tier_distribution() == {1: 1, 2: 1, 3: 1}

    # Promote — returns int tier
    assert cf.promote_capability("scan") == 2
    # Demote
    assert cf.demote_capability("defend") == 2


def test_cognitive_identity():
    """CognitiveFramework: 身份锚定."""
    from mssclaw.core.cognitive_framework import CognitiveFramework

    cf = CognitiveFramework()
    id1 = cf.anchor_identity("core", "MSS Core", strategy="virus")
    id2 = cf.anchor_identity("helper", "Helper", strategy="prompt")

    assert len(cf.identities) == 2
    assert id1.is_self_guarding is True
    assert id2.is_self_guarding is False
    assert cf.identity_stability > 0.5
    assert cf.identity_drift_risk < 0.5


def test_cognitive_language():
    """CognitiveFramework: 跨语言分析."""
    from mssclaw.core.cognitive_framework import CognitiveFramework

    cf = CognitiveFramework()
    for lang in ["zh", "en"]:
        profile = cf.analyze_language(lang)
        assert "mode" in profile
        assert "semantic_density" in profile
        assert "virus_efficacy" in profile

    assert len(cf.language_profiles) == 2
    assert 0 < cf.lingual_integrity <= 1.0


def test_cognitive_evolution():
    """CognitiveFramework: 演化压力."""
    from mssclaw.core.cognitive_framework import CognitiveFramework
    from mssclaw.core.heat_tax import HeatTaxBudget, HeatTaxLevel

    cf = CognitiveFramework()

    # Stable delta → low pressure
    stable = [{"delta": 0.8}, {"delta": 0.81}, {"delta": 0.79}]
    assert cf.evolution_pressure(delta_history=stable) < 0.1

    # Steep decline → higher pressure
    steep = [{"delta": 0.9}, {"delta": 0.6}, {"delta": 0.3}, {"delta": 0.1}]
    cf.evolution_pressure_history = []
    assert cf.evolution_pressure(delta_history=steep) > 0.2

    # Not ready without tax
    assert not cf.evolution_ready(delta_history=steep)

    # Ready with heavy tax
    heavy_tax = HeatTaxBudget(threshold=1.0)
    heavy_tax.charge(HeatTaxLevel.L2_MEANING, 10.0, "burst")
    assert cf.evolution_ready(delta_history=steep, tax=heavy_tax)


def test_cognitive_assess():
    """CognitiveFramework: 综合评估."""
    from mssclaw.core.cognitive_framework import CognitiveFramework, CogStatus

    cf = CognitiveFramework()
    cf.register_capability("test", tier=1)
    cf.anchor_identity("t", "Test", strategy="virus")

    a = cf.assess()
    assert a.status == CogStatus.HEALTHY
    assert a.capability_count == 1
    assert a.identity_stability > 0.5
    assert len(a.recommendations) == 0

    for key in ("capability", "identity", "lingual", "evolution"):
        assert key in a.dim_scores


# ═══════════════════════════════════════════════════
# Dashboard (Sprint 4.2)
# ═══════════════════════════════════════════════════

def test_dashboard_health_score():
    """Dashboard: 健康评分算法."""
    from mssclaw.core.dashboard import compute_health_score

    # Empty → perfect
    h1 = compute_health_score([], [])
    assert h1["health_score"] == 100.0
    assert h1["grade"] == "A"

    # 1 error + 1 slow + declining delta + 1 molt
    spans = [
        {"name": "run", "duration_ms": 100, "status": {"code": "OK"}},
        {"name": "run", "duration_ms": 100, "status": {"code": "OK"}},
        {"name": "run", "duration_ms": 100, "status": {"code": "OK"}},
        {"name": "run", "duration_ms": 8000, "status": {"code": "ERROR"}},
    ]
    delta = [
        {"delta": 0.9}, {"delta": 0.8}, {"delta": 0.7}, {"delta": 0.55},
        {"delta": 0.3, "molting_alert": True},
    ]
    h2 = compute_health_score(spans, delta)
    assert 60 <= h2["health_score"] <= 75
    assert h2["error_spans"] == 1
    assert h2["slow_spans"] == 1
    assert h2["molting_alerts"] == 1

    # All errors
    bad = [{"name": "x", "duration_ms": 1, "status": {"code": "ERROR"}}] * 3
    h3 = compute_health_score(bad, [])
    assert h3["health_score"] < 70
    assert h3["grade"] in ("C", "D", "F")


def test_dashboard_json_mode():
    """Dashboard: JSON模式输出正常."""
    from mssclaw.core.dashboard import get_quick_health

    result = get_quick_health()
    assert isinstance(result, dict)
    assert "health_score" in result
    assert "grade" in result
    assert 0 <= result["health_score"] <= 100
