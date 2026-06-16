"""Sprint 52: HallucinationShield smoke test."""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_hallucination_shield_basic():
    """HallucinationShield: 4类检测器加载正常."""
    from mssclaw.core.hallucination_shield import HallucinationShield
    hs = HallucinationShield()
    assert hs is not None


def test_norm_shield_bridge_full():
    """NormShieldBridge: 31规则→盾→交叉验证 完整链路."""
    from mssclaw.core.normative_field import NormativeField
    from mssclaw.core.norm_shield_bridge import NormShieldBridge, CrossVerdict

    nf = NormativeField()
    nf.load_defaults()
    bridge = NormShieldBridge()
    bridge.sync_rules(nf)

    # Verify mappings
    assert len(bridge.mapped_patterns) == len(nf._rules)
    for mp in bridge.mapped_patterns:
        assert mp.shield_type in ("Type1", "Type2", "Type3", "Type4")
        assert len(mp.detection_keywords) > 0

    # Cross-validate
    assert bridge.cross_validate(["alert"], ["alert"]) == CrossVerdict.HIGH_CONFIDENCE
    assert bridge.cross_validate(["alert"], []) == CrossVerdict.NORM_ONLY
    assert bridge.cross_validate([], ["alert"]) == CrossVerdict.SHIELD_ONLY
    assert bridge.cross_validate([], []) == CrossVerdict.PASS
