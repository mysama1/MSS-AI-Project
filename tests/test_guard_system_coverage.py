"""
Track C-6: Guard system coverage — CompactionGuard, DriftGuard, GuardNetwork,
FeedbackEvolution, DetectionWindow, HeatTaxSystem
"""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mssclaw.core.compaction_guard import CompactionGuard, CompactionReport
from mssclaw.core.drift_guard import DriftGuard, DriftReport, DriftSignal
from mssclaw.core.guard_network import GuardConfig, GuardExperiment, GuardNetworkModel, GuardLayer
from mssclaw.core.feedback_evolution import FeedbackEvolution, EvolutionRecord, Adaptation
from mssclaw.core.detection_window import DetectionWindowTracker, ViolationEvent
from mssclaw.core.heat_tax_system import HeatTaxMonitor, L0PhysicalSample, L1LogicalSample, L2MeaningSample


# ═══ CompactionGuard ═══
class TestCompactionGuard:
    def test_create(self):
        cg = CompactionGuard()
        assert cg is not None

    def test_defaults(self):
        cg = CompactionGuard()
        assert cg.first_msg_prefix_len == 50
        assert cg.negation_lost_warn == 2
        assert cg.negation_lost_critical == 5

    def test_custom_params(self):
        cg = CompactionGuard(first_msg_prefix_len=100, negation_lost_warn=3, negation_lost_critical=8)
        assert cg.first_msg_prefix_len == 100
        assert cg.negation_lost_warn == 3

    def test_quick_check(self):
        cg = CompactionGuard()
        result = cg.quick_check("Original text here.", "Compressed text.")
        assert isinstance(result, (CompactionReport, dict, str))


class TestCompactionReport:
    def test_defaults(self):
        r = CompactionReport()
        assert r.overall_health == "healthy"
        assert r.score == 1.0
        assert r.negation_lost == 0
        assert r.destructive_downgraded == 0

    def test_with_losses(self):
        r = CompactionReport(negation_lost=3, destructive_downgraded=1, overall_health="warning", score=0.7)
        assert r.negation_lost == 3
        assert r.destructive_downgraded == 1
        assert r.overall_health == "warning"
        assert r.score == 0.7


# ═══ DriftGuard ═══
class TestDriftGuard:
    def test_create(self):
        dg = DriftGuard()
        assert dg is not None

    def test_custom_threshold(self):
        dg = DriftGuard(severity_threshold=0.8)
        assert dg is not None

    def test_scan(self):
        dg = DriftGuard()
        result = dg.scan("original text", "drifting text")
        assert result is not None

    def test_scan_batch(self):
        dg = DriftGuard()
        result = dg.scan_batch([("a", "a"), ("b", "c")])
        assert isinstance(result, list)


class TestDriftReport:
    def test_create(self):
        r = DriftReport()
        assert r.quarantined == False
        assert r.summary == ""

    def test_quarantined(self):
        r = DriftReport(quarantined=True, stacked=True, summary="danger")
        assert r.quarantined == True
        assert r.stacked == True


class TestDriftSignal:
    def test_create(self):
        ds = DriftSignal(level=1, name="negation_loss", detected=True, evidence="test", severity=0.5)
        assert ds.level == 1
        assert ds.name == "negation_loss"
        assert ds.detected == True
        assert ds.severity == 0.5


# ═══ GuardNetwork ═══
class TestGuardConfig:
    def test_create(self):
        gc = GuardConfig(name="test", layers={GuardLayer.L0_RAW: True, GuardLayer.L6_SAFETY: True})
        assert gc is not None
        assert gc.name == "test"


class TestGuardNetworkModel:
    def test_create(self):
        gnm = GuardNetworkModel()
        assert gnm is not None

    def test_eta_default(self):
        gnm = GuardNetworkModel()
        assert gnm.eta_0 == 0.0
        assert gnm.r_squared == 0.0


# ═══ FeedbackEvolution ═══
class TestFeedbackEvolution:
    def test_create(self):
        fe = FeedbackEvolution(db_path=":memory:")
        assert fe is not None

    def test_mutation_rate(self):
        fe = FeedbackEvolution(db_path=":memory:", mutation_rate=0.5)
        assert fe is not None

    def test_record(self):
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        tmp.write(b'{"records": []}')
        tmp.close()
        fe = FeedbackEvolution(db_path=tmp.name)
        fe.record(agent="a1", task_id="t1", success=True)
        os.unlink(tmp.name)
        assert True  # record succeeded without error


class TestEvolutionRecord:
    def test_create(self):
        er = EvolutionRecord(agent="a1", task_id="t1", success=True)
        assert er.agent == "a1"
        assert er.task_id == "t1"
        assert er.success == True


class TestAdaptation:
    def test_create(self):
        a = Adaptation(agent="a1", pattern="redundant_call", frequency=5, adaptation="batch calls")
        assert a.agent == "a1"
        assert a.pattern == "redundant_call"
        assert a.frequency == 5


# ═══ DetectionWindow ═══
class TestDetectionWindowTracker:
    def test_create(self):
        dwt = DetectionWindowTracker()
        assert dwt is not None

    def test_record_violation(self):
        dwt = DetectionWindowTracker()
        event = ViolationEvent(violation_id="v1", event_type="breach", detected_at=1000.0, first_occurrence=990.0, damage_scope="pipeline")
        dwt.record(event)
        # Should track the event


class TestViolationEvent:
    def test_create(self):
        ve = ViolationEvent(violation_id="v1", event_type="breach", detected_at=100.0, first_occurrence=90.0, damage_scope="local")
        assert ve.violation_id == "v1"
        assert ve.event_type == "breach"
        assert ve.damage_scope == "local"


# ═══ HeatTaxSystem ═══
class TestL0PhysicalSample:
    def test_create(self):
        s = L0PhysicalSample()
        assert s.cpu_percent == 0.0
        assert s.memory_mb == 0.0

    def test_with_values(self):
        s = L0PhysicalSample(cpu_percent=45.0, memory_mb=512.0, memory_percent=60.0)
        assert s.cpu_percent == 45.0
        assert s.memory_mb == 512.0


class TestL1LogicalSample:
    def test_create(self):
        s = L1LogicalSample()
        assert s.token_count == 0
        assert s.redundancy_ratio == 0.0

    def test_with_values(self):
        s = L1LogicalSample(token_count=500, unique_tokens=200, redundancy_ratio=0.6)
        assert s.token_count == 500
        assert s.unique_tokens == 200


class TestL2MeaningSample:
    def test_create(self):
        s = L2MeaningSample()
        assert s.guardian_score == 1.0
        assert s.meaning_heat_tax == 0.0

    def test_with_values(self):
        s = L2MeaningSample(guardian_score=0.7, meaning_heat_tax=0.3, forbidden_hits=3)
        assert s.guardian_score == 0.7
        assert s.meaning_heat_tax == 0.3


class TestHeatTaxMonitor:
    def test_create(self):
        htm = HeatTaxMonitor()
        assert htm is not None

    def test_l_weights(self):
        htm = HeatTaxMonitor(l0_weight=0.01, l1_weight=2.0, l2_weight=500.0)
        assert htm is not None

    def test_snapshot(self):
        htm = HeatTaxMonitor()
        snap = htm.snapshot()
        assert snap is not None
