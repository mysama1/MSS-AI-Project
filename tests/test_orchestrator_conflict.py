"""
Track C-11: AgentOrchestrator + ConflictPhaseEngine coverage
AgentRole: REVIEWER, ANALYST, WRITER, SYNTHESIZER, CUSTOM
"""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mssclaw.core.agent_orchestrator import (
    AgentOrchestrator, AgentNode, AgentRole, OrchestratorMode,
    ExecutionContext, QuorumResult,
)
from mssclaw.core.conflict_phase_engine import (
    ConflictPhaseEngine, ConflictOrchestrator, ConflictContext,
    AnchorPair, StableSubfield, ConflictPolicy,
)


class TestAgentNode:
    def test_create(self):
        def handler(text): return {"ok": True}
        an = AgentNode(id="n1", role=AgentRole.ANALYST, handler=handler)
        assert an.id == "n1"
        assert an.role == AgentRole.ANALYST

    def test_with_options(self):
        an = AgentNode(id="n2", role=AgentRole.REVIEWER, handler=lambda x: x, heat_tax_budget=500, timeout_seconds=60, retries=3)
        assert an.role == AgentRole.REVIEWER


class TestOrchestratorMode:
    def test_values(self):
        for m in OrchestratorMode:
            assert isinstance(m.value, str)


class TestAgentRole:
    def test_values(self):
        for r in AgentRole:
            assert isinstance(r.value, str)


class TestExecutionContext:
    def test_create(self):
        ctx = ExecutionContext(task_id="t1", input_text="hello")
        assert ctx.task_id == "t1"
        assert ctx.heat_tax_pool == 3000

    def test_custom(self):
        ctx = ExecutionContext(task_id="t2", input_text="test", heat_tax_pool=5000, quorum_threshold=0.9)
        assert ctx.heat_tax_pool == 5000


class TestQuorumResult:
    def test_create(self):
        qr = QuorumResult(
            quorum_reached=True, quorum_size=3, total_voters=5,
            convergent=True, divergent_agents=[], consensus_output="agreed",
        )
        assert qr.quorum_reached is True
        assert qr.consensus_output == "agreed"

    def test_no_quorum(self):
        qr = QuorumResult(
            quorum_reached=False, quorum_size=2, total_voters=5,
            convergent=False, divergent_agents=["a1", "a2"], consensus_output=None,
        )
        assert qr.quorum_reached is False
        assert len(qr.divergent_agents) == 2


class TestAgentOrchestrator:
    def test_create(self):
        ao = AgentOrchestrator()
        assert ao is not None


class TestStableSubfield:
    def test_create(self):
        sf = StableSubfield(name="field_a", core={"axiom_1": True, "axiom_2": False})
        assert sf.name == "field_a"

    def test_with_style(self):
        sf = StableSubfield(name="f1", core={"a": True}, style={"verbosity": 0.8})
        assert sf.style == {"verbosity": 0.8}


class TestAnchorPair:
    def test_create(self):
        sf_a = StableSubfield(name="A", core={"x": True})
        sf_b = StableSubfield(name="B", core={"x": False})
        ap = AnchorPair(id="ab1", A=sf_a, B=sf_b)
        assert ap.id == "ab1"

    def test_custom_policy(self):
        sf_a = StableSubfield(name="A", core={"v": True})
        sf_b = StableSubfield(name="B", core={"v": False})
        ap = AnchorPair(id="ab2", A=sf_a, B=sf_b, relation="tension", policy=ConflictPolicy.PHASE_SLICE)
        assert ap.relation == "tension"


class TestConflictContext:
    def test_create(self):
        ctx = ConflictContext()
        assert ctx.pressure == 0.0

    def test_with_values(self):
        ctx = ConflictContext(pressure=0.8, progress=0.3, trust_level=0.2)
        assert ctx.pressure == 0.8


class TestConflictPhaseEngine:
    def test_create(self):
        sf_a = StableSubfield(name="A", core={"v": True})
        sf_b = StableSubfield(name="B", core={"v": False})
        ap = AnchorPair(id="ab1", A=sf_a, B=sf_b)
        cpe = ConflictPhaseEngine(anchor_pair=ap)
        assert cpe is not None


class TestConflictOrchestrator:
    def test_create(self):
        co = ConflictOrchestrator()
        assert co is not None


class TestConflictPolicy:
    def test_values(self):
        for p in ConflictPolicy:
            assert isinstance(p.value, str)
