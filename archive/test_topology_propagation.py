"""
Test suite for topology_propagation.py
"""

import unittest
from topology_propagation import (
    TopologyPropagator, NodeStatus, PropagationStrategy,
    StatusChange
)
from symbolic_engine import (
    MSSKnowledgeGraph, ConceptNode, RelationEdge,
    NodeType, RelationType
)

class TestTopologyPropagation(unittest.TestCase):

    def setUp(self):
        """Create test graph"""
        self.graph = MSSKnowledgeGraph()

        nodes = [
            ConceptNode("A1", "Axiom 1", NodeType.AXIOM, "L1", "Test axiom", confidence=1.0),
            ConceptNode("A2", "Axiom 2", NodeType.AXIOM, "L1", "Test axiom 2", confidence=1.0),
            ConceptNode("T1", "Theorem 1", NodeType.THEOREM, "L2", "Derived", confidence=0.9),
            ConceptNode("T2", "Theorem 2", NodeType.THEOREM, "L2", "Derived 2", confidence=0.85),
            ConceptNode("H1", "Heuristic 1", NodeType.CONCEPT, "L3", "Heuristic", confidence=0.7),
        ]

        for n in nodes:
            self.graph.add_node(n)

        edges = [
            RelationEdge("A1", "T1", RelationType.IMPLIES, 1.0),
            RelationEdge("T1", "T2", RelationType.DERIVES_FROM, 0.9),
            RelationEdge("T2", "H1", RelationType.ANALOGOUS, 0.8),
        ]

        for e in edges:
            self.graph.add_edge(e)

        self.propagator = TopologyPropagator(self.graph)

    def test_initial_status(self):
        """Test all nodes start as VALID"""
        for nid in self.graph.nodes:
            self.assertEqual(self.propagator.get_status(nid), NodeStatus.VALID)

    def test_mark_stale(self):
        """Test marking node as STALE propagates correctly"""
        changed = self.propagator.mark_stale("A1", "Test")

        # A1, T1, T2, H1 should be STALE
        self.assertIn("T1", changed)
        self.assertIn("T2", changed)
        self.assertIn("H1", changed)

        self.assertEqual(self.propagator.get_status("A1"), NodeStatus.STALE)
        self.assertEqual(self.propagator.get_status("T1"), NodeStatus.STALE)
        self.assertEqual(self.propagator.get_status("H1"), NodeStatus.STALE)

    def test_l1_not_affected_by_downstream(self):
        """Test L1 nodes are not affected by downstream changes"""
        self.propagator.mark_stale("T2", "Test")

        # A1 should still be VALID
        self.assertEqual(self.propagator.get_status("A1"), NodeStatus.VALID)

    def test_verify_pass(self):
        """Test verification passing"""
        self.propagator.verify_node("T1", lambda nid: True)
        self.assertEqual(self.propagator.get_status("T1"), NodeStatus.VALID)

    def test_verify_fail_then_deprecate(self):
        """Test verification failing leads to deprecation"""
        # Fail 3 times
        for _ in range(3):
            self.propagator.verify_node("T1", lambda nid: False)

        self.assertEqual(self.propagator.get_status("T1"), NodeStatus.DEPRECATED)

    def test_layer_filter(self):
        """Test propagation with layer filter"""
        result = self.propagator.propagate(
            "A1",
            strategy=PropagationStrategy.IMMEDIATE,
            layer_filter={"L2"}  # Only propagate to L2
        )

        # Should only affect T1 and T2 (L2)
        self.assertIn("T1", result.changed_nodes)
        self.assertIn("T2", result.changed_nodes)
        self.assertNotIn("H1", result.changed_nodes)  # L3 excluded

    def test_get_stale_nodes(self):
        """Test getting stale nodes"""
        self.propagator.mark_stale("A1")
        stale = self.propagator.get_stale_nodes()
        self.assertIn("A1", stale)
        self.assertIn("T1", stale)

    def test_export_import_state(self):
        """Test state serialization"""
        self.propagator.mark_stale("A1")
        state = self.propagator.export_state()

        self.assertIn("status", state)
        self.assertIn("A1", state["status"])

        # Create new propagator and import
        new_prop = TopologyPropagator(self.graph)
        new_prop.import_state(state)

        self.assertEqual(new_prop.get_status("A1"), NodeStatus.STALE)

    def test_history_tracking(self):
        """Test change history is recorded"""
        self.propagator.mark_stale("A1", "Test reason")
        history = self.propagator.get_propagation_history(node_id="A1")

        self.assertTrue(len(history) > 0)
        self.assertEqual(history[-1].reason, "Test reason")

    def test_reset_node(self):
        """Test resetting node to VALID"""
        self.propagator.mark_stale("A1")
        self.propagator.reset_node("A1")

        self.assertEqual(self.propagator.get_status("A1"), NodeStatus.VALID)

if __name__ == "__main__":
    unittest.main(verbosity=2)
