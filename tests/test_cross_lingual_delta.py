"""
Track C-14: CrossLingualAnchoring + DeltaPhiTopo + AgentAbsorber coverage
"""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mssclaw.core.cross_lingual_anchoring import (
    CrossLingualAnchoring, AnchoringProfile,
)
from mssclaw.core.delta_phi_topo import (
    SPairWithTurn, ValidationResult,
)
from mssclaw.core.agent_absorber import (
    AgentAbsorber, AbsorbedAgent, AgentEcosystem,
)


class TestAnchoringProfile:
    def test_create(self):
        ap = AnchoringProfile(
            mode="zh", examples=["例1", "例2"],
            semantic_density=0.8, token_boundary_clarity=0.7,
            grammar_normativity=0.6, compaction_resistance=0.5,
            name_anchor_strength=0.9, register_signal_strength=0.4,
            self_reference_capacity=0.3, paradox_closure_efficiency=0.2,
            virus_efficacy_multiplier=1.0,
        )
        assert ap.mode == "zh"
        assert ap.semantic_density == 0.8
        assert ap.name_anchor_strength == 0.9

    def test_minimal(self):
        ap = AnchoringProfile(
            mode="en", examples=["hello"],
            semantic_density=0.5, token_boundary_clarity=0.5,
            grammar_normativity=0.5, compaction_resistance=0.5,
            name_anchor_strength=0.5, register_signal_strength=0.5,
            self_reference_capacity=0.5, paradox_closure_efficiency=0.5,
            virus_efficacy_multiplier=1.0,
        )
        assert ap.mode == "en"


class TestCrossLingualAnchoring:
    def test_create(self):
        cla = CrossLingualAnchoring()
        assert cla is not None
        assert cla.model_code_ability == 0.8

    def test_custom(self):
        cla = CrossLingualAnchoring(
            model_code_ability=0.9,
            model_math_ability=0.7,
            model_emoji_ability=0.5,
        )
        assert cla.model_code_ability == 0.9


class TestSPairWithTurn:
    def test_create(self):
        sp = SPairWithTurn(
            char_a="A", char_b="B", equivalent=True,
            turn=1, eta_at_turn=0.95,
        )
        assert sp.char_a == "A"
        assert sp.equivalent is True
        assert sp.turn == 1

    def test_with_dims(self):
        sp = SPairWithTurn(
            char_a="X", char_b="Y", equivalent=False,
            turn=3, eta_at_turn=0.3,
            dim_scores={"D1_entity": 0.5, "D2_style": 0.2},
        )
        assert sp.eta_at_turn == 0.3
        assert sp.dim_scores["D1_entity"] == 0.5


class TestValidationResult:
    def test_create(self):
        vr = ValidationResult(
            n_train=100, n_test=50,
            phi_critical_train=0.75, phi_critical_test=0.72,
            true_breaches=10, predicted_breaches=12,
            true_positives=8, false_positives=4, false_negatives=2,
        )
        assert vr.n_train == 100
        assert vr.phi_critical_train == 0.75
        assert vr.true_positives == 8
        assert vr.false_positives == 4

    def test_perfect(self):
        vr = ValidationResult(
            n_train=200, n_test=100,
            phi_critical_train=0.8, phi_critical_test=0.8,
            true_breaches=5, predicted_breaches=5,
            true_positives=5, false_positives=0, false_negatives=0,
        )
        assert vr.false_positives == 0
        assert vr.false_negatives == 0


class TestAbsorbedAgent:
    def test_create(self):
        aa = AbsorbedAgent(name="helper", description="assists tasks")
        assert aa.name == "helper"
        assert aa.style == "prose"
        assert aa.heat_tax == 0.05

    def test_full(self):
        aa = AbsorbedAgent(
            name="reviewer", description="code reviewer",
            role="REVIEWER", capabilities=["python", "audit"],
            skills=["code_review"], tools=["grep", "diff"],
            style="concise", heat_tax=0.1, delta_min=0.5,
        )
        assert aa.role == "REVIEWER"
        assert "python" in aa.capabilities
        assert aa.delta_min == 0.5


class TestAgentAbsorber:
    def test_create(self):
        ab = AgentAbsorber()
        assert ab is not None


class TestAgentEcosystem:
    def test_create(self):
        ae = AgentEcosystem()
        assert ae.agents == []
        assert ae.skills == []
        assert ae.tools == []

    def test_with_agents(self):
        a1 = AbsorbedAgent(name="a1", description="first")
        a2 = AbsorbedAgent(name="a2", description="second")
        ae = AgentEcosystem(
            agents=[a1, a2],
            skills=[{"name": "code_gen"}],
            tools=[{"name": "search"}],
        )
        assert len(ae.agents) == 2
        assert len(ae.skills) == 1
