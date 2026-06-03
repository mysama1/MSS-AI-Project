"""
Test suite for KB-V3 Bridge
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kb_v3_bridge import KBV3Bridge, create_integrated_engine
from symbolic_engine_v3 import SymbolicEngineV3


class TestKBV3Bridge(unittest.TestCase):
    """Test KB-V3 Bridge integration"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.bridge = KBV3Bridge()
        cls.engine = cls.bridge.load_kb_to_v3()
    
    def test_kb_loaded(self):
        """Test that KB entries were loaded"""
        self.assertGreater(len(self.bridge.loader.entries), 0, "KB entries should be loaded")
        print(f"  [OK] Loaded {len(self.bridge.loader.entries)} KB entries")
    
    def test_graph_built(self):
        """Test that graph was built from KB"""
        stats = self.bridge.loader.to_graph().stats()
        self.assertGreater(stats['total_nodes'], 0, "Graph should have nodes")
        self.assertGreater(stats['total_edges'], 0, "Graph should have edges")
        print(f"  [OK] Graph: {stats['total_nodes']} nodes, {stats['total_edges']} edges")
    
    def test_engine_has_nodes(self):
        """Test that engine has nodes after merge"""
        self.assertGreater(len(self.engine.graph.nodes), 0, "Engine should have nodes")
        print(f"  [OK] Engine has {len(self.engine.graph.nodes)} nodes")
    
    def test_engine_has_edges(self):
        """Test that engine has edges after merge"""
        self.assertGreater(len(self.engine.graph.edges), 0, "Engine should have edges")
        print(f"  [OK] Engine has {len(self.engine.graph.edges)} edges")
    
    def test_l1_axioms_exist(self):
        """Test that L1 axioms exist in engine"""
        l1_nodes = [n for n in self.engine.graph.nodes.values() if n.layer == "L1"]
        self.assertGreater(len(l1_nodes), 0, "Should have L1 axioms")
        print(f"  [OK] Found {len(l1_nodes)} L1 axioms")
    
    def test_l2_theorems_exist(self):
        """Test that L2 theorems exist in engine"""
        l2_nodes = [n for n in self.engine.graph.nodes.values() if n.layer == "L2"]
        self.assertGreater(len(l2_nodes), 0, "Should have L2 theorems")
        print(f"  [OK] Found {len(l2_nodes)} L2 theorems")
    
    def test_l3_heuristics_exist(self):
        """Test that L3 heuristics exist in engine"""
        l3_nodes = [n for n in self.engine.graph.nodes.values() if n.layer == "L3"]
        self.assertGreater(len(l3_nodes), 0, "Should have L3 heuristics")
        print(f"  [OK] Found {len(l3_nodes)} L3 heuristics")
    
    def test_transitive_reasoner_rebuilt(self):
        """Test that transitive reasoner was rebuilt with merged graph"""
        self.assertIsNotNone(self.engine.transitive_reasoner, "Transitive reasoner should exist")
        self.assertEqual(
            self.engine.transitive_reasoner.graph,
            self.engine.graph,
            "Transitive reasoner should use engine graph"
        )
        print(f"  [OK] Transitive reasoner rebuilt with merged graph")
    
    def test_reasoning_works(self):
        """Test that reasoning works with KB data"""
        l1_nodes = [n for n in self.engine.graph.nodes.values() if n.layer == "L1"]
        l2_nodes = [n for n in self.engine.graph.nodes.values() if n.layer == "L2"]
        
        if l1_nodes and l2_nodes:
            result = self.engine.reason(l1_nodes[0].id, l2_nodes[0].id)
            self.assertIn(result.result.name, ["PROVEN", "DISPROVEN", "UNDETERMINED"])
            print(f"  [OK] Reasoning works: {l1_nodes[0].id} → {l2_nodes[0].id} = {result.result.name}")
        else:
            print("  [SKIP] Not enough nodes for reasoning test")
    
    def test_query_l1_to_l2_path(self):
        """Test L1 to L2 path query"""
        l1_nodes = [n for n in self.engine.graph.nodes.values() if n.layer == "L1"]
        l2_nodes = [n for n in self.engine.graph.nodes.values() if n.layer == "L2"]
        
        if l1_nodes and l2_nodes:
            result = self.bridge.query_l1_to_l2_path(l1_nodes[0].id, l2_nodes[0].id)
            self.assertIn("result", result)
            self.assertIn("certainty", result)
            print(f"  [OK] Path query works: {result['result']} (certainty: {result['certainty']:.2%})")
        else:
            print("  [SKIP] Not enough nodes for path query")
    
    def test_get_l1_axioms(self):
        """Test getting L1 axioms"""
        axioms = self.bridge.get_l1_axioms()
        self.assertIsInstance(axioms, list)
        print(f"  [OK] get_l1_axioms() returns {len(axioms)} axioms")
    
    def test_get_l2_theorems(self):
        """Test getting L2 theorems"""
        theorems = self.bridge.get_l2_theorems()
        self.assertIsInstance(theorems, list)
        print(f"  [OK] get_l2_theorems() returns {len(theorems)} theorems")
    
    def test_create_integrated_engine(self):
        """Test convenience function"""
        engine = create_integrated_engine()
        self.assertIsInstance(engine, SymbolicEngineV3)
        self.assertGreater(len(engine.graph.nodes), 0)
        print(f"  [OK] create_integrated_engine() works: {len(engine.graph.nodes)} nodes")


class TestKBV3BridgeEdgeCases(unittest.TestCase):
    """Test edge cases"""
    
    def test_empty_engine_merge(self):
        """Test merging into empty engine"""
        bridge = KBV3Bridge()
        empty_engine = SymbolicEngineV3()
        # Clear default nodes
        empty_engine.graph.nodes.clear()
        empty_engine.graph.edges.clear()
        empty_engine.graph._adjacency.clear()
        
        result = bridge.load_kb_to_v3(empty_engine)
        self.assertGreater(len(result.graph.nodes), 0)
        print(f"  [OK] Merge into empty engine works: {len(result.graph.nodes)} nodes")
    
    def test_query_without_load(self):
        """Test query before loading raises error"""
        bridge = KBV3Bridge()
        with self.assertRaises(RuntimeError):
            bridge.query_l1_to_l2_path("A1", "T1")
        print(f"  [OK] Query without load raises RuntimeError")


if __name__ == "__main__":
    print("=" * 60)
    print("KB-V3 Bridge Test Suite")
    print("=" * 60)
    
    # Run with verbosity
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors")
    print("=" * 60)
