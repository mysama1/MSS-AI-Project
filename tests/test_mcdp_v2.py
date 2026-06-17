"""pytest tests for mcdp_v2 — multi-agent consensus data models"""
import sys; sys.path.insert(0, '.')
import pytest
from mssclaw.core.mcdp_v2 import (
    AgentRole, AgentConflict, GossipMessage, NormativeVote,
    MeanFieldConflict, MeaningField
)


class TestAgentRole:
    def test_mediator_exists(self):
        assert hasattr(AgentRole, 'MEDIATOR') or 'MEDIATOR' in AgentRole.__members__

    def test_values_are_strings(self):
        # AgentRole is an Enum
        assert isinstance(AgentRole.MEDIATOR.value, str)

    def test_multiple_roles(self):
        members = list(AgentRole.__members__.keys())
        assert len(members) >= 2  # at least MEDIATOR + one more


class TestAgentConflict:
    def test_creation(self):
        c = AgentConflict(agent_A="A1", agent_B="A2",
                         degree=0.7, conflict_type="resource",
                         dimensions=["time", "budget"])
        assert c.agent_A == "A1"
        assert c.degree == 0.7
        assert c.conflict_type == "resource"

    def test_dimensions_list(self):
        c = AgentConflict(agent_A="X", agent_B="Y",
                         degree=0.3, conflict_type="goal",
                         dimensions=["accuracy", "speed"])
        assert len(c.dimensions) == 2

    def test_max_degree(self):
        c = AgentConflict(agent_A="P", agent_B="Q",
                         degree=1.0, conflict_type="total",
                         dimensions=[])
        assert c.degree == 1.0

    def test_zero_degree(self):
        c = AgentConflict(agent_A="P", agent_B="Q",
                         degree=0.0, conflict_type="none",
                         dimensions=[])
        assert c.degree == 0.0


class TestGossipMessage:
    def test_creation(self):
        msg = GossipMessage(sender_id="node1",
                           message_type="consensus",
                           payload={"score": 0.8},
                           timestamp=1718123456, ttl=10,
                           signature="sig_abc")
        assert msg.sender_id == "node1"
        assert msg.message_type == "consensus"
        assert msg.payload["score"] == 0.8
        assert msg.ttl == 10

    def test_high_ttl(self):
        msg = GossipMessage(sender_id="gossip1",
                           message_type="heartbeat",
                           payload={}, timestamp=0, ttl=999,
                           signature="")
        assert msg.ttl == 999


class TestNormativeVote:
    def test_creation(self):
        v = NormativeVote(agent_id="agent3",
                         rule_id="rule_heat_tax",
                         vote="approve",
                         timestamp=1718123000,
                         justification="Reduces L2 heat tax by 90%")
        assert v.agent_id == "agent3"
        assert v.vote == "approve"

    def test_reject_vote(self):
        v = NormativeVote(agent_id="agent4",
                         rule_id="rule_mandatory_review",
                         vote="reject",
                         timestamp=1718123000,
                         justification="Too expensive for fast iteration")
        assert v.vote == "reject"

    def test_rule_id(self):
        v = NormativeVote(agent_id="a", rule_id="H634",
                         vote="abstain", timestamp=0,
                         justification="Need more data")
        assert v.rule_id == "H634"


class TestMeanFieldConflict:
    def test_creation(self):
        mf = MeanFieldConflict(
            conflicts=[],
            n_agents=50,
            tension_field={"economy": 0.8, "safety": 0.4},
            mean_tension=0.6,
            critical_agents=["A7", "B12"],
            dominant_strategies={"avoidance": 30, "competition": 15},
            nash_equilibrium="mixed"
        )
        assert mf.n_agents == 50
        assert mf.mean_tension == 0.6

    def test_tension_field(self):
        mf = MeanFieldConflict(
            conflicts=[], n_agents=10,
            tension_field={"privacy": 0.9, "utility": 0.2},
            mean_tension=0.55,
            critical_agents=[], dominant_strategies={},
            nash_equilibrium="pure"
        )
        assert mf.tension_field["privacy"] == 0.9

    def test_nash_labels(self):
        for ne in ["pure", "mixed", "correlated"]:
            mf = MeanFieldConflict(
                conflicts=[], n_agents=1,
                tension_field={}, mean_tension=0.0,
                critical_agents=[], dominant_strategies={},
                nash_equilibrium=ne
            )
            assert mf.nash_equilibrium == ne


class TestMeaningField:
    def test_creation(self):
        mf = MeaningField(
            id="MF_001",
            vertices=["v1", "v2", "v3"],
            edges=[("v1", "v2"), ("v2", "v3")],
            stable_core=["v1"]
        )
        assert mf.id == "MF_001"
        assert len(mf.vertices) == 3
        assert len(mf.edges) == 2

    def test_empty_core(self):
        mf = MeaningField(
            id="MF_empty",
            vertices=["a"],
            edges=[],
            stable_core=[]
        )
        assert mf.stable_core == []

    def test_large_graph(self):
        vertices = [f"v{i}" for i in range(100)]
        edges = [(f"v{i}", f"v{i+1}") for i in range(99)]
        mf = MeaningField(
            id="MF_large",
            vertices=vertices,
            edges=edges,
            stable_core=vertices[:10]
        )
        assert len(mf.vertices) == 100
        assert len(mf.edges) == 99
