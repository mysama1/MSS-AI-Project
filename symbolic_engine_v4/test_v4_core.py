"""
Test suite for Symbolic Engine v4.0 Core
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from symbolic_engine_v4.core import (
    CSRGraph, ConceptNode, ConceptEdge,
    RelationType, NodeType, LayerTier
)
from symbolic_engine_v4.parser import JSONLParser

class TestCSRGraph(unittest.TestCase):
    """Test CSR Graph implementation"""

    def setUp(self):
        self.graph = CSRGraph(max_nodes=1000)

    def test_add_node(self):
        node = ConceptNode(id="test_001", title="Test Node", content="Test content")
        idx = self.graph.add_node(node)
        self.assertEqual(idx, 0)
        self.assertEqual(self.graph.node_count, 1)

    def test_add_edge(self):
        n1 = ConceptNode(id="A", title="Node A", content="Content A")
        n2 = ConceptNode(id="B", title="Node B", content="Content B")

        self.graph.add_node(n1)
        self.graph.add_node(n2)

        edge = ConceptEdge(source="A", target="B", relation=RelationType.IMPLIES)
        result = self.graph.add_edge(edge)

        self.assertTrue(result)
        self.assertEqual(self.graph.edge_count, 1)

    def test_get_neighbors(self):
        n1 = ConceptNode(id="A", title="Node A", content="Content A")
        n2 = ConceptNode(id="B", title="Node B", content="Content B")
        n3 = ConceptNode(id="C", title="Node C", content="Content C")

        self.graph.add_node(n1)
        self.graph.add_node(n2)
        self.graph.add_node(n3)

        self.graph.add_edge(ConceptEdge("A", "B", RelationType.IMPLIES))
        self.graph.add_edge(ConceptEdge("A", "C", RelationType.ANALOGOUS))

        neighbors = self.graph.get_neighbors("A")
        self.assertEqual(len(neighbors), 2)

    def test_node_types(self):
        axiom = ConceptNode(id="axiom_1", title="Axiom", content="Axiom content",
                           node_type=NodeType.AXIOM, layer=LayerTier.L1_CORE)
        heuristic = ConceptNode(id="heuristic_1", title="Heuristic", content="Heuristic content",
                               node_type=NodeType.HEURISTIC, layer=LayerTier.L3_HEURISTIC)

        self.graph.add_node(axiom)
        self.graph.add_node(heuristic)

        l1_nodes = self.graph.get_nodes_by_layer(LayerTier.L1_CORE)
        self.assertEqual(len(l1_nodes), 1)
        self.assertEqual(l1_nodes[0].id, "axiom_1")

class TestJSONLParser(unittest.TestCase):
    """Test JSONL Parser"""

    def setUp(self):
        self.parser = JSONLParser()

    def test_parse_node(self):
        data = {
            "id": "H001",
            "title": "Test Entry",
            "content": "Test content",
            "layer": "L1",
            "category": "test",
            "tags": ["test", "axiom"]
        }

        node = self.parser._parse_node(data)
        self.assertIsNotNone(node)
        self.assertEqual(node.id, "H001")
        self.assertEqual(node.layer, LayerTier.L1_CORE)

    def test_parse_directory(self):
        # Test with actual knowledge base directory
        kb_dir = r"C:\MSS-AI-Project\knowledge_base"
        if os.path.exists(kb_dir):
            nodes, edges = self.parser.parse_directory(kb_dir)
            self.assertGreater(len(nodes), 0)
            print(f"\nParsed {len(nodes)} nodes, {len(edges)} edges from {kb_dir}")

if __name__ == '__main__':
    unittest.main(verbosity=2)
