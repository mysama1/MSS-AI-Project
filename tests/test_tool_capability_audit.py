"""
Track C-12: ToolCalling + CapabilityLevel + DeltaQuickAudit + AutoArchive + NormativeField
ToolCallStatus: SUCCESS, FAILED, BLOCKED, TIMEOUT
"""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mssclaw.core.advanced_tool_calling import (
    MSSToolSystem, ToolSchema, ToolCallResult, ToolCallStatus,
)
from mssclaw.core.capability_level import (
    CapabilityLevel, Capability, CapTier, CapabilityReport,
)
from mssclaw.core.delta_quick_audit import (
    DeltaQuickAudit, DeltaResult, SessionState, Tier, DeltaLight,
)
from mssclaw.core.auto_archive import AutoArchiver, EntryDiagnosis, KBLayer
from mssclaw.core.normative_field import (
    LexicalRule, AnchorRule, NormDomain, NormLevel, MetaField,
)


class TestToolSchema:
    def test_create(self):
        ts = ToolSchema(name="search", description="searches kb", parameters={"q": "string"})
        assert ts.name == "search"

    def test_with_fn(self):
        ts = ToolSchema(
            name="compute", description="runs calc",
            parameters={"expr": "string"}, function=lambda x: eval(x),
            requires_approval=True, heat_tax_cost=0.5, max_retries=3, timeout_seconds=60,
        )
        assert ts.requires_approval is True


class TestToolCallResult:
    def test_create(self):
        tcr = ToolCallResult(tool_name="search", status=ToolCallStatus.SUCCESS, arguments={"q": "test"})
        assert tcr.tool_name == "search"

    def test_failed(self):
        tcr = ToolCallResult(
            tool_name="broken", status=ToolCallStatus.FAILED,
            arguments={}, error="timeout", elapsed_ms=5000,
        )
        assert tcr.status == ToolCallStatus.FAILED
        assert tcr.error == "timeout"


class TestToolCallStatus:
    def test_values(self):
        for s in ToolCallStatus:
            assert isinstance(s.value, str)


class TestMSSToolSystem:
    def test_create(self):
        ts = MSSToolSystem()
        assert ts is not None


class TestCapTier:
    def test_values(self):
        for ct in CapTier:
            assert isinstance(ct.value, (int, str))


class TestCapability:
    def test_create(self):
        c = Capability(name="code_gen", tier=CapTier.A)
        assert c.name == "code_gen"

    def test_with_deps(self):
        c = Capability(
            name="multi_agent", tier=CapTier.A,
            requires=["code_gen", "review"], provides=["orchestrate"],
            verified=True, benchmark={"accuracy": 0.95},
        )
        assert c.provides == ["orchestrate"]


class TestCapabilityReport:
    def test_create(self):
        cr = CapabilityReport()
        assert cr.tier_a_count == 0

    def test_with_counts(self):
        c = Capability(name="c1", tier=CapTier.A)
        cr = CapabilityReport(capabilities=[c], tier_a_count=1)
        assert cr.tier_a_count == 1


class TestCapabilityLevel:
    def test_create(self):
        cl = CapabilityLevel()
        assert cl is not None


class TestDeltaResult:
    def test_create(self):
        dr = DeltaResult(q1_bluffed=False, q2_performed=True, q3_repeated=False, q4_drifted=False, q5_overfed=False)
        assert dr.q1_bluffed is False

    def test_red(self):
        dr = DeltaResult(q1_bluffed=True, q2_performed=False, q3_repeated=True, q4_drifted=False, q5_overfed=False, red_count=2)
        assert dr.red_count == 2


class TestDeltaLight:
    def test_values(self):
        for dl in DeltaLight:
            assert isinstance(dl.value, str)


class TestTier:
    def test_values(self):
        for t in Tier:
            assert isinstance(t.value, str)


class TestSessionState:
    def test_create(self):
        ss = SessionState()
        assert ss.domain == "daily"

    def test_with_domain(self):
        ss = SessionState(domain="code", heat_tax_pct=0.3, round_number=10)
        assert ss.round_number == 10


class TestDeltaQuickAudit:
    def test_create(self):
        dqa = DeltaQuickAudit()
        assert dqa is not None


class TestKBLayer:
    def test_values(self):
        for l in KBLayer:
            assert isinstance(l.value, (int, str))


class TestEntryDiagnosis:
    def test_create(self):
        ed = EntryDiagnosis(h_id="H1", filename="h1_core.json")
        assert ed.h_id == "H1"

    def test_with_issues(self):
        ed = EntryDiagnosis(
            h_id="H5", filename="h5.json",
            suggested_layer=KBLayer.L1_CORE_THEORY,
            suggested_categories=["axiom"], detected_axioms=["A1"],
            missing_fields=["source"], estimated_t_value=0.8,
            issues=["no reference"], score=0.6,
        )
        assert ed.score == 0.6


class TestAutoArchiver:
    def test_create(self):
        aa = AutoArchiver()
        assert aa is not None


class TestLexicalRule:
    def test_create(self):
        lr = LexicalRule(rule_id="LR1", pattern=r"\bforbidden\b", severity="critical", message="banned word")
        assert lr.rule_id == "LR1"

    def test_with_hits(self):
        lr = LexicalRule(rule_id="LR2", pattern=r"\btest\b", severity="warning", message="test", hit_count=5, false_positives=2)
        assert lr.hit_count == 5


class TestAnchorRule:
    def test_create(self):
        ar = AnchorRule(
            rule_id="AR1", anchors=["axiom", "truth"], anti_anchors=["lie"],
            context_words=["verify"], severity="high", message="anchor violation",
        )
        assert ar.rule_id == "AR1"


class TestNormDomain:
    def test_values(self):
        for d in NormDomain:
            assert isinstance(d.value, str)


class TestNormLevel:
    def test_values(self):
        for l in NormLevel:
            assert isinstance(l.value, (int, str))


class TestMetaField:
    def test_create(self):
        mf = MetaField()
        assert mf is not None
