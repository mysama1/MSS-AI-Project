"""
Tests for L1 IMPLIES Connection Completion
"""

import unittest
import sys
import os

sys.path.insert(0, r'C:\MSS-AI-Project')

from l1_implies_completion import L1ImpliesCompleter
from symbolic_engine import RelationType


class TestL1ImpliesCompletion(unittest.TestCase):
    """Test L1 IMPLIES connection completion"""
    
    @classmethod
    def setUpClass(cls):
        cls.completer = L1ImpliesCompleter(r"C:\MSS-AI-Project\knowledge_base")
        cls.completer.load()
        cls.new_edges = cls.completer.complete()
    
    def test_load_success(self):
        """KB loaded successfully"""
        self.assertEqual(len(self.completer.l1_nodes), 100)
    
    def test_edges_added(self):
        """New edges were added"""
        self.assertGreater(len(self.new_edges), 0)
        print(f"New edges added: {len(self.new_edges)}")
    
    def test_all_edges_are_implies(self):
        """All new edges are IMPLIES type"""
        for edge in self.new_edges:
            self.assertEqual(edge.relation, RelationType.IMPLIES)
    
    def test_l1_to_l1_only(self):
        """All edges connect L1 to L1"""
        l1_ids = set(self.completer.l1_nodes.keys())
        for edge in self.new_edges:
            self.assertIn(edge.source, l1_ids)
            self.assertIn(edge.target, l1_ids)
    
    def test_connectivity_improved(self):
        """L1 connectivity improved"""
        stats = self.completer.get_stats()
        self.assertGreater(stats["l1_to_l1_implies"], 0)
        self.assertGreater(stats["connected_l1"], 0)
        print(f"Connected L1: {stats['connected_l1']}/100")
    
    def test_isolation_reduced(self):
        """Most L1 nodes are now connected"""
        stats = self.completer.get_stats()
        self.assertLess(stats["isolated_l1"], 10)
        print(f"Isolated L1: {stats['isolated_l1']}/100")
    
    def test_dependency_edges_exist(self):
        """Dependency-based edges exist"""
        dep_edges = [e for e in self.new_edges 
                     if e.evidence.startswith("dependency_ref")]
        self.assertGreater(len(dep_edges), 0)
        print(f"Dependency edges: {len(dep_edges)}")
    
    def test_prefix_chain_edges_exist(self):
        """Prefix chain edges exist"""
        chain_edges = [e for e in self.new_edges 
                       if e.evidence.startswith("prefix_chain")]
        self.assertGreater(len(chain_edges), 0)
        print(f"Prefix chain edges: {len(chain_edges)}")
    
    def test_core_axiom_edges_exist(self):
        """Core axiom match edges exist"""
        core_edges = [e for e in self.new_edges 
                      if e.evidence.startswith("core_axiom_match")]
        self.assertGreater(len(core_edges), 0)
        print(f"Core axiom edges: {len(core_edges)}")
    
    def test_edge_strength_valid(self):
        """All edges have valid strength"""
        for edge in self.new_edges:
            self.assertGreaterEqual(edge.strength, 0.0)
            self.assertLessEqual(edge.strength, 1.0)
    
    def test_export_file_created(self):
        """Export file was created"""
        export_path = r"C:\MSS-AI-Project\knowledge_base\l1_implies_completion.jsonl"
        self.assertTrue(os.path.exists(export_path))
        
        # Count lines
        with open(export_path, 'r', encoding='utf-8') as f:
            lines = [l for l in f if l.strip()]
        self.assertEqual(len(lines), len(self.new_edges))
    
    def test_no_duplicate_edges(self):
        """No duplicate edges added"""
        edge_set = set()
        for edge in self.new_edges:
            key = (edge.source, edge.target, edge.relation.name)
            self.assertNotIn(key, edge_set, f"Duplicate edge: {key}")
            edge_set.add(key)
    
    def test_axiom_chain_integrity(self):
        """AXIOM-001 to AXIOM-006 chain exists"""
        axiom_edges = [(e.source, e.target) for e in self.new_edges
                       if e.source.startswith("AXIOM-") and e.target.startswith("AXIOM-")]
        
        # Check forward chain
        chain = [("AXIOM-001", "AXIOM-002"), ("AXIOM-002", "AXIOM-003"),
                 ("AXIOM-003", "AXIOM-004"), ("AXIOM-004", "AXIOM-005"),
                 ("AXIOM-005", "AXIOM-006")]
        for src, tgt in chain:
            self.assertIn((src, tgt), axiom_edges, f"Missing chain edge: {src}->{tgt}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
