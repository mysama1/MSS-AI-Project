"""pytest tests for type2_control_experiment — experiment data models"""
import sys; sys.path.insert(0, '.')
import pytest
from mssclaw.core.type2_control_experiment import (
    TypeIICase, TrialResult, ExperimentReport,
    CaseGenerator, TensionLevel
)


class TestTensionLevel:
    def test_ten_levels(self):
        members = list(TensionLevel.__members__.keys())
        assert len(members) == 10

    def test_trivial_lowest(self):
        assert TensionLevel.TRIVIAL.value < TensionLevel.LOW.value

    def test_maximal_highest(self):
        for level in list(TensionLevel)[:-1]:
            assert level.value < TensionLevel.MAXIMAL.value

    def test_all_values_numeric(self):
        for level in TensionLevel:
            assert isinstance(level.value, (int, float))


class TestTypeIICase:
    def test_creation(self):
        c = TypeIICase(
            id="C001",
            stable_a="accuracy",
            stable_b="speed",
            tension=TensionLevel.HIGH,
            context="real-time safety system",
            golden="accuracy",
            resources=["GPU", "CPU"],
            recipients=["user", "admin"]
        )
        assert c.id == "C001"
        assert c.stable_a == "accuracy"
        assert c.tension == TensionLevel.HIGH

    def test_parity_case(self):
        c = TypeIICase(
            id="C002",
            stable_a="privacy",
            stable_b="utility",
            tension=TensionLevel.PARADOXICAL,
            context="personal data API",
            golden="privacy",
            resources=[],
            recipients=[]
        )
        assert c.tension == TensionLevel.PARADOXICAL

    def test_minimal_tension(self):
        c = TypeIICase(
            id="C003",
            stable_a="a", stable_b="b",
            tension=TensionLevel.TRIVIAL,
            context="test",
            golden=None,
            resources=[], recipients=[]
        )
        assert c.tension == TensionLevel.TRIVIAL


class TestTrialResult:
    def test_creation(self):
        r = TrialResult(
            case_id="C001",
            tension=TensionLevel.HIGH,
            direction=1,
            success=True,
            eta=0.85,
            heat_tax=120,
            latency=35.5,
            negotiation_rounds=3,
            elevated_dimensions=2,
            theta_final=0.6
        )
        assert r.case_id == "C001"
        assert r.direction == 1
        assert r.success is True
        assert r.eta == 0.85

    def test_failed_trial(self):
        r = TrialResult(
            case_id="C999",
            tension=TensionLevel.EXTREME,
            direction=2,
            success=False,
            eta=0.0,
            heat_tax=5000,
            latency=300.0,
            negotiation_rounds=10,
            elevated_dimensions=0,
            theta_final=0.0
        )
        assert r.success is False
        assert r.heat_tax == 5000

    def test_direction_discrimination(self):
        d1 = TrialResult(case_id="X", tension=TensionLevel.NOTABLE,
                        direction=1, success=True, eta=0.9,
                        heat_tax=50, latency=10.0,
                        negotiation_rounds=1, elevated_dimensions=1,
                        theta_final=0.8)
        d2 = TrialResult(case_id="X", tension=TensionLevel.NOTABLE,
                        direction=2, success=True, eta=0.72,
                        heat_tax=40, latency=8.0,
                        negotiation_rounds=2, elevated_dimensions=2,
                        theta_final=0.5)
        assert d1.direction == 1
        assert d2.direction == 2


class TestExperimentReport:
    def test_creation(self):
        r = ExperimentReport(
            total_trials=100,
            trials_per_direction=50,
            by_tension={},
            d1_success_rate=0.85,
            d2_success_rate=0.72,
            d1_avg_eta=0.748,
            d2_avg_eta=0.625,
            d1_avg_heat_tax=45.2,
            d2_avg_heat_tax=38.1,
            d1_avg_latency=12.3,
            d2_avg_latency=9.7
        )
        assert r.total_trials == 100
        assert r.d1_success_rate == 0.85
        assert r.d2_success_rate == 0.72

    def test_eta_difference(self):
        r = ExperimentReport(
            total_trials=10, trials_per_direction=5, by_tension={},
            d1_success_rate=1.0, d2_success_rate=1.0,
            d1_avg_eta=0.9, d2_avg_eta=0.6,
            d1_avg_heat_tax=30, d2_avg_heat_tax=20,
            d1_avg_latency=10.0, d2_avg_latency=8.0
        )
        assert r.d1_avg_eta - r.d2_avg_eta == pytest.approx(0.3)


class TestCaseGenerator:
    def test_creation(self):
        cg = CaseGenerator()
        assert cg is not None
