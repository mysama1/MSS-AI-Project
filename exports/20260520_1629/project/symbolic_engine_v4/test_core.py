"""
核心模块测试
"""

import unittest
from core.types import ConceptNode, RelationEdge, NodeType, EdgeType
from core.graph import CSRGraph

class TestCSRGraph(unittest.TestCase):
    
    def setUp(self):
        self.graph = CSRGraph()
    
    def test_add_node(self):
        node = ConceptNode("n1", "测试概念", NodeType.CONCEPT, layer=2)
        self.assertTrue(self.graph.add_node(node))
        self.assertEqual(self.graph.node_count(), 1)
        
        # 重复添加
        self.assertFalse(self.graph.add_node(node))
    
    def test_add_edge(self):
        n1 = ConceptNode("n1", "概念A", NodeType.CONCEPT, layer=2)
        n2 = ConceptNode("n2", "概念B", NodeType.CONCEPT, layer=2)
        self.graph.add_node(n1)
        self.graph.add_node(n2)
        
        edge = RelationEdge("n1", "n2", EdgeType.IMPLIES, weight=0.8)
        self.assertTrue(self.graph.add_edge(edge))
        self.assertEqual(self.graph.edge_count(), 1)
    
    def test_get_neighbors(self):
        n1 = ConceptNode("n1", "A", NodeType.CONCEPT, layer=2)
        n2 = ConceptNode("n2", "B", NodeType.CONCEPT, layer=2)
        n3 = ConceptNode("n3", "C", NodeType.CONCEPT, layer=2)
        
        for n in [n1, n2, n3]:
            self.graph.add_node(n)
        
        self.graph.add_edge(RelationEdge("n1", "n2", EdgeType.IMPLIES))
        self.graph.add_edge(RelationEdge("n1", "n3", EdgeType.IMPLIES))
        
        neighbors = self.graph.get_neighbors("n1")
        self.assertEqual(len(neighbors), 2)
    
    def test_bidirectional_edge(self):
        n1 = ConceptNode("n1", "A", NodeType.CONCEPT, layer=2)
        n2 = ConceptNode("n2", "B", NodeType.CONCEPT, layer=2)
        
        for n in [n1, n2]:
            self.graph.add_node(n)
        
        edge = RelationEdge("n1", "n2", EdgeType.EQUIVALENT, bidirectional=True)
        self.graph.add_edge(edge)
        
        # 双向边应该创建两条有向边
        self.assertEqual(self.graph.edge_count(), 2)
    
    def test_stats(self):
        n1 = ConceptNode("n1", "A", NodeType.AXIOM, layer=1)
        n2 = ConceptNode("n2", "B", NodeType.THEOREM, layer=2)
        
        for n in [n1, n2]:
            self.graph.add_node(n)
        
        self.graph.add_edge(RelationEdge("n1", "n2", EdgeType.IMPLIES))
        
        stats = self.graph.get_stats()
        self.assertEqual(stats["nodes"], 2)
        self.assertEqual(stats["edges"], 1)
        self.assertIn("axiom", stats["node_types"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
