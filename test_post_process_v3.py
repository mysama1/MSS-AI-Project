"""
MSS Post-Processing Engine v3.0 - Test Suite
Tests topology integration and backward compatibility
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from post_process_engine_v3 import (
    PostProcessEngine, FilterRule, FilterResult,
    RuleCategory, RulePriority,
    create_topology_aware_engine, filter_response,
    TOPOLOGY_AVAILABLE
)

from symbolic_engine import (
    MSSKnowledgeGraph, ConceptNode, RelationEdge,
    NodeType, RelationType
)


class TestPostProcessV3Basics(unittest.TestCase):
    """Test basic v3.0 functionality (backward compatible with v2.0)"""
    
    def setUp(self):
        self.engine = PostProcessEngine()
    
    def test_terminology_filter(self):
        """Test terminology replacement"""
        result = self.engine.filter("This is the ultimate solution.")
        self.assertIn("current best", result.text)
        self.assertIn("approach", result.text)
        self.assertTrue(result.had_changes)
    
    def test_assertion_dampening(self):
        """Test overconfidence dampening"""
        result = self.engine.filter("This never fails and is obviously correct.")
        self.assertIn("consistently performs", result.text)
        self.assertIn("apparently", result.text)
    
    def test_no_false_positives(self):
        """Test that normal text is not modified"""
        normal = "The cat sat on the mat."
        result = self.engine.filter(normal)
        self.assertEqual(result.text, normal)
        self.assertFalse(result.had_changes)
    
    def test_filter_result_structure(self):
        """Test FilterResult dataclass"""
        result = self.engine.filter("This is perfect.")
        self.assertIsInstance(result, FilterResult)
        self.assertGreaterEqual(result.rules_applied, 0)
        self.assertIsInstance(result.rules_matched, set)
        self.assertIsInstance(result.replacements, list)
        self.assertIsInstance(result.topology_warnings, list)  # v3.0 field
    
    def test_stats_tracking(self):
        """Test statistics tracking"""
        before = self.engine.stats["total_filters"]
        self.engine.filter("This is the ultimate solution.")
        after = self.engine.stats["total_filters"]
        self.assertEqual(after, before + 1)
    
    def test_rule_management(self):
        """Test enable/disable rules via rules dict"""
        self.engine.rules["ultimate_term"].enabled = False
        result = self.engine.filter("This is ultimate.")
        self.assertFalse(result.had_changes)  # Rule disabled
        
        self.engine.rules["ultimate_term"].enabled = True
        result2 = self.engine.filter("This is ultimate.")
        self.assertTrue(result2.had_changes)  # Rule re-enabled


class TestTopologyIntegration(unittest.TestCase):
    """Test topology-aware enhancements (v3.0)"""
    
    def setUp(self):
        self.engine = PostProcessEngine()
        
        if not TOPOLOGY_AVAILABLE:
            self.skipTest("Topology metrics not available")
        
        # Create test graph with structural issues
        self.graph = MSSKnowledgeGraph()
        
        # Component 1: A-B connected
        for nid in ["A", "B"]:
            node = ConceptNode(
                id=nid, name=nid,
                node_type=NodeType.CONCEPT,
                layer="L1",
                content=f"Content {nid}"
            )
            self.graph.add_node(node)
        
        self.graph.add_edge(RelationEdge("A", "B", RelationType.IMPLIES))
        
        # Component 2: C isolated (creates structural issue)
        node_c = ConceptNode(
            id="C", name="C",
            node_type=NodeType.CONCEPT,
            layer="L3",  # Different layer, no connection
            content="Isolated L3 content"
        )
        self.graph.add_node(node_c)
        
        from topology_metrics import TopologyMetricsEngine
        self.topo_engine = TopologyMetricsEngine(self.graph)
        self.engine.attach_topology_engine(self.topo_engine)
    
    def test_topology_attachment(self):
        """Test topology engine attachment"""
        self.assertTrue(self.engine.topology_enabled)
        self.assertIsNotNone(self.engine.topology_engine)
    
    def test_topology_warnings_generated(self):
        """Test that topology warnings are generated"""
        result = self.engine.filter("This is a complete solution.")
        
        # Should have topology warnings due to isolated node and layer gap
        self.assertGreater(len(result.topology_warnings), 0)
    
    def test_topology_warning_content(self):
        """Test topology warning content"""
        result = self.engine.filter("This is a complete solution.")
        
        # Check for specific warning types
        warning_text = " ".join(result.topology_warnings)
        
        # Should mention isolated nodes or layer gaps
        has_relevant_warning = (
            "isolated" in warning_text.lower() or
            "layer gap" in warning_text.lower() or
            "health" in warning_text.lower()
        )
        self.assertTrue(has_relevant_warning)
    
    def test_topology_injection_in_output(self):
        """Test that warnings are injected into output text"""
        result = self.engine.filter("This is a complete solution.")
        
        # Output should contain topology warnings
        self.assertIn("Structural Analysis", result.text)
        self.assertIn("[Topology Warning]", result.text)
    
    def test_detach_topology(self):
        """Test topology engine detachment"""
        self.engine.detach_topology_engine()
        self.assertFalse(self.engine.topology_enabled)
        self.assertIsNone(self.engine.topology_engine)
        
        # After detachment, no topology warnings
        result = self.engine.filter("This is a complete solution.")
        self.assertEqual(len(result.topology_warnings), 0)
        self.assertNotIn("Structural Analysis", result.text)


class TestTopologyRules(unittest.TestCase):
    """Test topology-specific rules"""
    
    def setUp(self):
        self.engine = PostProcessEngine()
    
    def test_bridge_edge_rule_exists(self):
        """Test bridge-edge reasoning rule exists"""
        rules = self.engine.get_rules(category=RuleCategory.TOPOLOGY)
        rule_ids = [r.id for r in rules]
        self.assertIn("topology_bridge_reasoning", rule_ids)
    
    def test_sparse_claim_rule_exists(self):
        """Test sparse region claim rule exists"""
        rules = self.engine.get_rules(category=RuleCategory.TOPOLOGY)
        rule_ids = [r.id for r in rules]
        self.assertIn("topology_sparse_claim", rule_ids)
    
    def test_layer_gap_rule_exists(self):
        """Test layer gap rule exists"""
        rules = self.engine.get_rules(category=RuleCategory.TOPOLOGY)
        rule_ids = [r.id for r in rules]
        self.assertIn("topology_layer_gap", rule_ids)
    
    def test_topology_rules_enabled_by_default(self):
        """Test topology rules are enabled by default"""
        rules = self.engine.get_rules(
            category=RuleCategory.TOPOLOGY,
            enabled_only=True
        )
        self.assertEqual(len(rules), 3)  # All 3 topology rules enabled


class TestFactoryFunction(unittest.TestCase):
    """Test topology-aware factory function"""
    
    def test_create_without_topology(self):
        """Test creating engine without topology"""
        engine = create_topology_aware_engine()
        self.assertIsInstance(engine, PostProcessEngine)
        self.assertFalse(engine.topology_enabled)
    
    def test_create_with_topology(self):
        """Test creating engine with topology"""
        if not TOPOLOGY_AVAILABLE:
            self.skipTest("Topology metrics not available")
        
        from topology_metrics import TopologyMetricsEngine
        
        graph = MSSKnowledgeGraph()
        topo = TopologyMetricsEngine(graph)
        
        engine = create_topology_aware_engine(topo)
        self.assertTrue(engine.topology_enabled)


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with v2.0"""
    
    def test_legacy_filter_response(self):
        """Test legacy filter_response function"""
        result = filter_response("This is the ultimate solution.")
        self.assertIn("current best", result)
        self.assertIn("approach", result)
    
    def test_rule_categories_preserved(self):
        """Test all v2.0 rule categories exist"""
        engine = PostProcessEngine()
        
        # v2.0 categories should exist
        for cat in [RuleCategory.TERMINOLOGY, RuleCategory.ASSERTION,
                    RuleCategory.STRUCTURE, RuleCategory.COMPLIANCE,
                    RuleCategory.FORMAT]:
            rules = engine.get_rules(category=cat)
            self.assertGreater(len(rules), 0, f"No rules in category {cat.name}")
    
    def test_export_import(self):
        """Test rule export/import"""
        engine = PostProcessEngine()
        exported = engine.export_rules()
        
        self.assertGreater(len(exported), 0)
        
        # Check topology rules are included
        topo_rules = [r for r in exported if r["category"] == "TOPOLOGY"]
        self.assertEqual(len(topo_rules), 3)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases"""
    
    def test_empty_string(self):
        """Test filtering empty string"""
        engine = PostProcessEngine()
        result = engine.filter("")
        self.assertEqual(result.text, "")
    
    def test_none_input(self):
        """Test filtering None raises exception"""
        engine = PostProcessEngine()
        with self.assertRaises(Exception):
            engine.filter(None)
    
    def test_topology_with_empty_graph(self):
        """Test topology analysis with empty graph"""
        if not TOPOLOGY_AVAILABLE:
            self.skipTest("Topology metrics not available")
        
        from topology_metrics import TopologyMetricsEngine
        
        graph = MSSKnowledgeGraph()
        topo = TopologyMetricsEngine(graph)
        
        engine = PostProcessEngine()
        engine.attach_topology_engine(topo)
        
        result = engine.filter("This is a complete solution.")
        # Should not crash, may or may not have warnings
        self.assertIsInstance(result.text, str)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestPostProcessV3Basics))
    suite.addTests(loader.loadTestsFromTestCase(TestTopologyIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestTopologyRules))
    suite.addTests(loader.loadTestsFromTestCase(TestFactoryFunction))
    suite.addTests(loader.loadTestsFromTestCase(TestBackwardCompatibility))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print(f"\n{'='*60}")
    print(f"Test Summary: {result.testsRun} tests run")
    print(f"Success: {result.wasSuccessful()}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"{'='*60}")
    
    sys.exit(0 if result.wasSuccessful() else 1)
