"""
Track C: 关键未测试模块 — adaptive_topophase, topological_phase_engine, molting_engine
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mssclaw.core.topological_phase_engine import (
    MeaningFieldGraph, MeaningNode, MeaningEdge,
    TopologicalPhaseEngine, BasinBuilder, ConflictBasin
)
from mssclaw.core.adaptive_topophase import (
    AdaptiveTopologicalPhaseEngine, VitalityMonitor, DualAnchorBuffer
)
from mssclaw.core.molting_engine import (
    MoltableEntity, MoltingCluster, MoltValidator, MoltMode, MoltRecord, MoltableEntity
)


@pytest.fixture
def field():
    g = MeaningFieldGraph()
    g.add_node(MeaningNode("A", "Anchor A"))
    g.add_node(MeaningNode("B", "Anchor B"))
    g.add_node(MeaningNode("C", "Node C"))
    g.add_edge(MeaningEdge("A", "C", weight=0.8))
    g.add_edge(MeaningEdge("B", "C", weight=0.3))
    return g


@pytest.fixture
def basin_builder(field):
    return BasinBuilder(field)


@pytest.fixture
def basin(field):
    return ConflictBasin("test_subfield", {"A", "C"}, {"boundary_1"})


# ═══════ AdaptiveTopologicalPhaseEngine ═══════

class TestAdaptiveTopologicalPhase:
    def test_create(self, field):
        e = AdaptiveTopologicalPhaseEngine(field, "A", "B")
        assert e is not None
        assert e.anchor_A == "A"
        assert e.anchor_B == "B"

    def test_vitality_threshold_default(self, field):
        e = AdaptiveTopologicalPhaseEngine(field, "A", "B")
        assert e.vitality_threshold == 0.5

    def test_vitality_threshold_custom(self, field):
        e = AdaptiveTopologicalPhaseEngine(field, "A", "B", vitality_threshold=0.7)
        assert e.vitality_threshold == 0.7

    def test_reanchor_trigger(self, field):
        e = AdaptiveTopologicalPhaseEngine(field, "A", "B")
        e._trigger_reanchor("A", "C", "B")
        assert len(e.anchor_history) >= 1
        assert e.anchor_history[0]['anchor'] == 'A'

    def test_has_basin_builder(self, field):
        e = AdaptiveTopologicalPhaseEngine(field, "A", "B")
        # basin_builder is optional, may be None
        assert hasattr(e, 'basin_builder')


# ═══════ VitalityMonitor ═══════

class TestVitalityMonitor:
    def test_create(self, field, basin_builder):
        vm = VitalityMonitor(field, basin_builder)
        assert vm is not None

    def test_compute_eccentricity(self, field, basin_builder, basin):
        vm = VitalityMonitor(field, basin_builder)
        ecc = vm.compute_eccentricity("A", basin)
        assert isinstance(ecc, float)

    def test_record_feedback(self, field, basin_builder):
        vm = VitalityMonitor(field, basin_builder)
        vm.record_feedback("A", was_correct=True)
        vm.record_feedback("B", was_correct=False)

    def test_compute_vitality(self, field, basin_builder, basin):
        vm = VitalityMonitor(field, basin_builder)
        snap = vm.compute_vitality("A", basin)
        assert snap is not None


# ═══════ DualAnchorBuffer ═══════

class TestDualAnchorBuffer:
    def test_create(self):
        buf = DualAnchorBuffer(old_anchor="X", candidate_anchor="Y", start_step=0)
        assert buf.old_anchor == "X"
        assert buf.candidate_anchor == "Y"

    def test_defaults(self):
        buf = DualAnchorBuffer(old_anchor="X", candidate_anchor="Y", start_step=0)
        assert buf.old_avg_eta == 0.0
        assert buf.candidate_avg_eta == 0.0
        assert buf.finalized is False

    def test_warmup_steps(self):
        buf = DualAnchorBuffer(old_anchor="X", candidate_anchor="Y", start_step=0, warmup_steps=20)
        assert buf.warmup_steps == 20


# ═══════ MeaningFieldGraph ═══════

class TestMeaningFieldGraph:
    def test_create(self):
        g = MeaningFieldGraph()
        assert g is not None

    def test_add_node(self):
        g = MeaningFieldGraph()
        g.add_node(MeaningNode("n1", "Node 1"))
        assert "n1" in g.nodes
        assert g.nodes["n1"].label == "Node 1"

    def test_add_node_with_attributes(self):
        g = MeaningFieldGraph()
        g.add_node(MeaningNode("n1", "Node", attributes={"domain": "test"}))
        assert "n1" in g.nodes

    def test_add_edge(self, field):
        g = MeaningFieldGraph()
        g.add_node(MeaningNode("X", "X"))
        g.add_node(MeaningNode("Y", "Y"))
        g.add_edge(MeaningEdge("X", "Y"))
        assert g.nodes["X"].label == "X"

    def test_topological_distance(self, field):
        dist = field.topological_distance("A", "B")
        assert isinstance(dist, (int, float))
        assert dist >= 0

    def test_shortest_distances(self, field):
        dists = field.shortest_distances_from("A")
        assert isinstance(dists, dict)
        assert "C" in dists

    def test_bfs_distances(self, field):
        dists = field.bfs_distances("A")
        assert isinstance(dists, dict)


# ═══════ TopologicalPhaseEngine ═══════

class TestTopologicalPhase:
    def test_create(self, field):
        e = TopologicalPhaseEngine(field, "A", "B")
        assert e is not None
        assert e.anchor_A == "A"
        assert e.anchor_B == "B"

    def test_hysteresis_default(self, field):
        e = TopologicalPhaseEngine(field, "A", "B")
        assert e.hysteresis == 0.15

    def test_hysteresis_custom(self, field):
        e = TopologicalPhaseEngine(field, "A", "B", hysteresis=0.3)
        assert e.hysteresis == 0.3


# ═══════ ConflictBasin ═══════

class TestConflictBasin:
    def test_create(self):
        b = ConflictBasin("sub", {"A", "B"}, {"boundary"})
        assert b.stable_subfield_name == "sub"
        assert b.basin_nodes == {"A", "B"}

    def test_with_anchor(self):
        b = ConflictBasin("sub", {"A"}, {"B"}, anchor_id="A")
        assert b.anchor_id == "A"


# ═══════ MoltingEngine ═══════

class TestMoltingEngine:
    def test_create_entity(self):
        e = MoltableEntity(name="rule_1")
        assert e.name == "rule_1"

    def test_entity_snapshot(self):
        e = MoltableEntity(name="rule_2")
        e.snapshot = {"key": "value"}
        assert e.snapshot == {"key": "value"}

    def test_entity_state_default(self):
        e = MoltableEntity(name="rule_3")
        # state may be None or a default dict
        assert hasattr(e, 'state')

    def test_entity_molt_history_initially_empty(self):
        e = MoltableEntity(name="rule_4")
        assert e.molt_history == []

    def test_cluster_create(self):
        c = MoltingCluster()
        assert c is not None

    def test_cluster_quorum_default(self):
        c = MoltingCluster()
        assert c.quorum_ratio == 0.5

    def test_cluster_register(self):
        c = MoltingCluster()
        entity = MoltableEntity(name="item_a")
        c.register(entity)
        assert "item_a" in c.entities

    def test_cluster_register_multiple(self):
        c = MoltingCluster()
        for name in ["a", "b", "c"]:
            c.register(MoltableEntity(name=name))
        assert len(c.entities) == 3

    def test_cluster_molt_requires_entity(self):
        c = MoltingCluster()
        entity = MoltableEntity(name="test")
        c.register(entity)
        result = c.cluster_molt(MoltMode.SKIN_SHED, transform_fns={})
        assert isinstance(result, dict)

    def test_molt_validator(self):
        v = MoltValidator()
        assert v is not None

    def test_molt_record(self):
        r = MoltRecord(
            molt_id="m001", agent_id="A1", mode=MoltMode.SKIN_SHED,
            start_time=100.0
        )
        assert r.molt_id == "m001"
        assert r.agent_id == "A1"
        assert r.mode == MoltMode.SKIN_SHED

    def test_molt_mode_values(self):
        modes = list(MoltMode)
        assert len(modes) >= 3
