"""
Track C-10: Budget + MeaningVectorization + HiveAudit + EmpiricalHarness coverage
AuditLevel: L0_MICRO, L1_BATCH, L2_PHASE, L3_CONFLICT, L4_MACRO
"""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mssclaw.core.budget import HeatTaxBudget, BudgetPrediction, BudgetUsage, RedundancyPredictor
from mssclaw.core.meaning_vectorization import MeaningVector, MeaningDomain, SearchResult
from mssclaw.core.hive_audit import HiveAuditor, HiveConfig, AuditFinding, AuditLevel
from mssclaw.core.empirical_harness import (
    OllamaRunner, EtaScorer, EtaScore, TurnResult, TurnConfig,
    ExperimentResult, IdentityExperimentRunner, TurnManager, FitReport,
)


# ═══ Budget ═══
class TestHeatTaxBudget:
    def test_create(self):
        htb = HeatTaxBudget()
        assert htb is not None
        assert htb.total_budget == 10000.0

    def test_with_weights(self):
        htb = HeatTaxBudget(total_budget=5000.0, l0_weight=0.01, l1_weight=2.0, l2_weight=500.0)
        assert htb.total_budget == 5000.0


class TestBudgetPrediction:
    def test_create(self):
        bp = BudgetPrediction()
        assert bp.affordable is True
        assert bp.risk_level == "low"

    def test_with_values(self):
        bp = BudgetPrediction(task_id="t1", l0_pred=1.0, l1_pred=10.0, l2_pred=1000.0, total_pred=1011.0)
        assert bp.total_pred == 1011.0


class TestBudgetUsage:
    def test_create(self):
        bu = BudgetUsage(task_id="t1", predicted=100.0, actual=None)
        assert bu.predicted == 100.0
        assert bu.status == "committed"

    def test_completed(self):
        bu = BudgetUsage(task_id="t2", predicted=100.0, actual=95.0, status="completed")
        assert bu.actual == 95.0


class TestRedundancyPredictor:
    def test_create(self):
        htb = HeatTaxBudget()
        rp = RedundancyPredictor(budget=htb)
        assert rp is not None


# ═══ Meaning Vectorization ═══
class TestMeaningVector:
    def test_create(self):
        mv = MeaningVector(coords=[0.1, 0.2, 0.3])
        assert mv.coords == [0.1, 0.2, 0.3]
        assert mv.phi == 1.0

    def test_with_meta(self):
        mv = MeaningVector(coords=[0.5, 0.5], phi=0.8, source_id="src1", domain="ethics", meta={"k": "v"})
        assert mv.phi == 0.8
        assert mv.source_id == "src1"


class TestMeaningDomain:
    def test_create(self):
        md = MeaningDomain(name="td", basis=["dim1", "dim2"])
        assert md.name == "td"
        assert md.basis == ["dim1", "dim2"]
        assert md.phi_critical == 0.75

    def test_with_anchors(self):
        mv = MeaningVector(coords=[1.0, 0.0])
        md = MeaningDomain(name="anchored", basis=["x", "y"], anchors=[mv])
        assert len(md.anchors) == 1


class TestSearchResult:
    def test_create(self):
        mv = MeaningVector(coords=[0.1, 0.2])
        sr = SearchResult(vector=mv, score=0.95, distance=0.05, phi_loss=0.0)
        assert sr.score == 0.95


# ═══ Hive Audit ═══
class TestAuditFinding:
    def test_create(self):
        af = AuditFinding(level=AuditLevel.L1_BATCH, severity="medium", category="stability", message="test finding")
        assert af.severity == "medium"
        assert af.category == "stability"

    def test_with_source(self):
        af = AuditFinding(level=AuditLevel.L3_CONFLICT, severity="high", category="breach", message="oops", source="guard_1")
        assert af.source == "guard_1"


class TestAuditLevel:
    def test_values(self):
        for lv in AuditLevel:
            assert isinstance(lv.value, int)


class TestHiveConfig:
    def test_create(self):
        hc = HiveConfig()
        assert hc.batch_size == 5
        assert hc.min_severity_for_trigger == "warning"

    def test_custom(self):
        hc = HiveConfig(batch_size=10, min_severity_for_trigger="error", phase_trigger_tasks=50)
        assert hc.batch_size == 10


class TestHiveAuditor:
    def test_create(self):
        ha = HiveAuditor()
        assert ha is not None

    def test_with_config(self):
        hc = HiveConfig(batch_size=3)
        ha = HiveAuditor(config=hc)
        assert ha is not None


# ═══ Empirical Harness ═══
class TestOllamaRunner:
    def test_create(self):
        r = OllamaRunner()
        assert r is not None

    def test_with_timeout(self):
        r = OllamaRunner(timeout=60)
        assert r is not None


class TestEtaScore:
    def test_create(self):
        es = EtaScore(turn=1, D1_entity=0.9, D2_style=0.8, D3_agency=0.7, D4_member=0.6, D5_world=0.5, eta_overall=0.7)
        assert es.turn == 1
        assert es.eta_overall == 0.7


class TestEtaScorer:
    def test_create(self):
        scorer = EtaScorer(reference_name="test", reference_traits=["calm", "logical"])
        assert scorer is not None


class TestTurnResult:
    def test_create(self):
        es = EtaScore(turn=1, D1_entity=1.0, D2_style=1.0, D3_agency=1.0, D4_member=1.0, D5_world=1.0, eta_overall=1.0)
        tr = TurnResult(turn=1, user_input="hello", model_output="hi", eta_score=es, duration_ms=100.0, model="test")
        assert tr.turn == 1
        assert tr.model == "test"


class TestTurnConfig:
    def test_create(self):
        tc = TurnConfig(turn=1, user_message="test msg", expected_agent_action="reply")
        assert tc.turn == 1


class TestExperimentResult:
    def test_create(self):
        er = ExperimentResult(
            model="test_model", dtss_params={}, turns=[],
            eta_trajectory=[], breach_turn=None,
            final_eta=1.0, phi_critical_obs=0.75, duration_total_ms=50.0,
        )
        assert er.model == "test_model"


class TestFitReport:
    def test_create(self):
        fr = FitReport(
            model_name="test", dtss_params={},
            predicted_final_eta=0.8, observed_final_eta=0.7,
            eta_trajectory_observed=[0.9, 0.8, 0.7],
            breach_match=True, mae=0.1,
            convergence_rate_obs=0.1, convergence_rate_pred=0.08,
        )
        assert fr.breach_match is True


class TestIdentityExperimentRunner:
    def test_create(self):
        r = OllamaRunner(timeout=10)
        ier = IdentityExperimentRunner(runner=r)
        assert ier is not None


class TestTurnManager:
    def test_create(self):
        r = OllamaRunner(timeout=10)
        s = EtaScorer(reference_name="test")
        tm = TurnManager(runner=r, scorer=s)
        assert tm is not None
