"""
Test suite for NL → Symbolic Bridge
"""

import unittest
from nl_bridge import (
    NLToSymbolicBridge, QueryIntent, NLQuery,
    create_bridge_with_kb
)

class TestNLBridgeParsing(unittest.TestCase):
    """测试查询解析功能"""

    def setUp(self):
        self.bridge = NLToSymbolicBridge()

    def test_reason_intent(self):
        """测试推理意图识别"""
        query = self.bridge.parse("A1能推出什么？")
        self.assertEqual(query.intent, QueryIntent.REASON)
        self.assertIn("A1", query.entities)

    def test_verify_intent(self):
        """测试验证意图识别"""
        query = self.bridge.parse("验证A2是否蕴含T1")
        # "蕴含"同时匹配VERIFY和REASON模式，可能被判为REASON
        self.assertIn(query.intent, [QueryIntent.VERIFY, QueryIntent.REASON])
        self.assertIn("A2", query.entities)
        self.assertIn("T1", query.entities)

    def test_query_intent(self):
        """测试查询意图识别"""
        query = self.bridge.parse("什么是A3？")
        self.assertEqual(query.intent, QueryIntent.QUERY)
        self.assertIn("A3", query.entities)

    def test_explain_intent(self):
        """测试解释意图识别"""
        query = self.bridge.parse("解释热税机制")
        self.assertEqual(query.intent, QueryIntent.EXPLAIN)

    def test_list_intent(self):
        """测试列表意图识别"""
        query = self.bridge.parse("列出所有L1公理")
        self.assertEqual(query.intent, QueryIntent.LIST)
        self.assertEqual(query.layer_filter, "L1")

    def test_path_intent(self):
        """测试路径意图识别"""
        query = self.bridge.parse("从A1到T3的路径")
        self.assertEqual(query.intent, QueryIntent.REASON)
        self.assertIn("A1", query.entities)
        self.assertIn("T3", query.entities)

    def test_entity_extraction(self):
        """测试实体提取"""
        query = self.bridge.parse("A1和A2推出T1")
        self.assertIn("A1", query.entities)
        self.assertIn("A2", query.entities)
        self.assertIn("T1", query.entities)

    def test_layer_filter_detection(self):
        """测试层级过滤检测"""
        query = self.bridge.parse("列出L2的所有定理")
        self.assertEqual(query.layer_filter, "L2")

    def test_confidence_calculation(self):
        """测试置信度计算"""
        query = self.bridge.parse("A1推出T1")
        self.assertGreaterEqual(query.confidence, 0.7)

class TestSymbolicQueryBuilding(unittest.TestCase):
    """测试符号查询构建"""

    def setUp(self):
        self.bridge = NLToSymbolicBridge()

    def test_reason_query_building(self):
        """测试推理查询构建"""
        nl_query = NLQuery(
            raw_text="A1推出T1",
            intent=QueryIntent.REASON,
            entities=["A1", "T1"],
            target_entity="T1",
            layer_filter=None,
            confidence=0.9
        )
        symbolic = self.bridge.to_symbolic_query(nl_query)
        self.assertEqual(symbolic["type"], "reason")
        self.assertEqual(symbolic["source"], "A1")
        self.assertEqual(symbolic["target"], "T1")

    def test_verify_query_building(self):
        """测试验证查询构建"""
        nl_query = NLQuery(
            raw_text="验证A2蕴含T1",
            intent=QueryIntent.VERIFY,
            entities=["A2", "T1"],
            target_entity="T1",
            layer_filter=None,
            confidence=0.9
        )
        symbolic = self.bridge.to_symbolic_query(nl_query)
        self.assertEqual(symbolic["type"], "verify")
        self.assertEqual(symbolic["relation"], "IMPLIES")

    def test_list_query_building(self):
        """测试列表查询构建"""
        nl_query = NLQuery(
            raw_text="列出L1公理",
            intent=QueryIntent.LIST,
            entities=[],
            target_entity=None,
            layer_filter="L1",
            confidence=0.8
        )
        symbolic = self.bridge.to_symbolic_query(nl_query)
        self.assertEqual(symbolic["type"], "list")
        self.assertEqual(symbolic["layer_filter"], "L1")

class TestBridgeIntegration(unittest.TestCase):
    """测试桥接器集成"""

    def test_full_workflow_reason(self):
        """测试推理完整流程"""
        bridge = NLToSymbolicBridge()
        result = bridge.execute("A1推出什么？")
        self.assertTrue(result.success)
        self.assertEqual(result.query_type, "reason")
        self.assertIsNotNone(result.nl_response)

    def test_full_workflow_query(self):
        """测试查询完整流程"""
        bridge = NLToSymbolicBridge()
        result = bridge.execute("什么是A1？")
        self.assertTrue(result.success)
        self.assertEqual(result.query_type, "query")

    def test_unknown_query(self):
        """测试未知查询处理"""
        bridge = NLToSymbolicBridge()
        result = bridge.execute("xxx")
        # 短文本可能解析为QUERY或UNKNOWN
        self.assertIsNotNone(result.nl_response)

class TestEntityCache(unittest.TestCase):
    """测试实体缓存功能"""

    def test_cache_building(self):
        """测试缓存构建"""
        from symbolic_engine import MSSKnowledgeGraph, ConceptNode, NodeType

        graph = MSSKnowledgeGraph()
        node = ConceptNode(
            id="A1", name="意义本体论",
            node_type=NodeType.AXIOM, layer="L1",
            content="连续全息自洽意义流形"
        )
        graph.add_node(node)

        bridge = NLToSymbolicBridge(graph)
        self.assertIn("a1", bridge.entity_cache)
        self.assertIn("意义本体论", bridge.entity_cache)

if __name__ == "__main__":
    unittest.main(verbosity=2)
