"""
NL Bridge V2 测试套件
测试增强功能：多轮对话、复杂查询、格式化输出、指代消解
"""

import unittest
from nl_bridge_v2 import (
    NLBridgeV2, DialogueContext, ComplexQuery,
    ResponseFormat, create_v2_bridge
)
from nl_bridge import QueryIntent


class TestDialogueContext(unittest.TestCase):
    """测试对话上下文管理"""
    
    def setUp(self):
        self.ctx = DialogueContext()
    
    def test_add_turn(self):
        """测试添加对话轮次"""
        from nl_bridge import NLQuery
        query = NLQuery(
            raw_text="测试查询",
            intent=QueryIntent.QUERY,
            entities=["A1"],
            target_entity=None,
            layer_filter=None,
            confidence=0.8
        )
        result = type('Result', (), {'success': True})()
        
        self.ctx.add_turn(query, result)
        self.assertEqual(self.ctx.turn_count, 1)
        self.assertEqual(self.ctx.last_entities, ["A1"])
    
    def test_get_recent_entities(self):
        """测试获取最近实体"""
        from nl_bridge import NLQuery
        for i in range(3):
            query = NLQuery(
                raw_text=f"查询{i}",
                intent=QueryIntent.QUERY,
                entities=[f"A{i}"],
                target_entity=None,
                layer_filter=None,
                confidence=0.8
            )
            result = type('Result', (), {'success': True})()
            self.ctx.add_turn(query, result)
        
        recent = self.ctx.get_recent_entities(2)
        self.assertIn("A2", recent)
    
    def test_resolve_reference(self):
        """测试指代消解"""
        from nl_bridge import NLQuery
        query = NLQuery(
            raw_text="解释A1",
            intent=QueryIntent.EXPLAIN,
            entities=["A1"],
            target_entity=None,
            layer_filter=None,
            confidence=0.9
        )
        result = type('Result', (), {'success': True})()
        self.ctx.add_turn(query, result)
        
        # 测试"它"指代
        resolved = self.ctx.resolve_reference("它是什么意思")
        self.assertIn("A1", resolved)
        
        # 测试无上下文
        ctx2 = DialogueContext()
        resolved2 = ctx2.resolve_reference("它是什么意思")
        self.assertEqual(resolved2, "它是什么意思")  # 未改变


class TestComplexQueryDetection(unittest.TestCase):
    """测试复杂查询检测"""
    
    def setUp(self):
        self.bridge = NLBridgeV2()
    
    def test_detect_and_query(self):
        """测试AND查询检测"""
        text = "验证A1推出T1并且A2推出T2"
        complex_q = self.bridge.detect_complex_query(text)
        self.assertIsNotNone(complex_q)
        self.assertEqual(complex_q.operator, "AND")
        self.assertGreaterEqual(len(complex_q.sub_queries), 2)
    
    def test_detect_or_query(self):
        """测试OR查询检测"""
        text = "A1推出T1还是T2"
        complex_q = self.bridge.detect_complex_query(text)
        self.assertIsNotNone(complex_q)
        self.assertEqual(complex_q.operator, "OR")
    
    def test_detect_then_query(self):
        """测试THEN查询检测"""
        text = "先解释A1然后验证A1推出T1"
        complex_q = self.bridge.detect_complex_query(text)
        self.assertIsNotNone(complex_q)
        self.assertEqual(complex_q.operator, "THEN")
    
    def test_detect_compare_query(self):
        """测试COMPARE查询检测"""
        text = "比较A1和A2的区别"
        complex_q = self.bridge.detect_complex_query(text)
        self.assertIsNotNone(complex_q)
        self.assertEqual(complex_q.operator, "COMPARE")
    
    def test_simple_query_not_complex(self):
        """测试简单查询不被误判"""
        text = "解释A1公理"
        complex_q = self.bridge.detect_complex_query(text)
        self.assertIsNone(complex_q)


class TestResponseFormatting(unittest.TestCase):
    """测试响应格式化"""
    
    def setUp(self):
        self.bridge = NLBridgeV2()
    
    def test_markdown_format(self):
        """测试Markdown格式"""
        from nl_bridge import BridgeResult
        result = BridgeResult(
            success=True,
            query_type="query",
            symbolic_query={"type": "query"},
            nl_response="测试响应",
            reasoning_result=None,
            confidence=0.9
        )
        formatted = self.bridge._format_response(result, ResponseFormat.MARKDOWN)
        self.assertIn("##", formatted)
        self.assertIn("✅", formatted)
    
    def test_json_format(self):
        """测试JSON格式"""
        from nl_bridge import BridgeResult
        result = BridgeResult(
            success=True,
            query_type="query",
            symbolic_query={"type": "query"},
            nl_response="测试响应",
            reasoning_result=None,
            confidence=0.9
        )
        formatted = self.bridge._format_response(result, ResponseFormat.JSON)
        self.assertIn("\"success\": true", formatted)
        self.assertIn("\"query_type\": \"query\"", formatted)
    
    def test_structured_format(self):
        """测试结构化格式"""
        from nl_bridge import BridgeResult
        result = BridgeResult(
            success=True,
            query_type="query",
            symbolic_query={"type": "query"},
            nl_response="测试响应",
            reasoning_result=None,
            confidence=0.9
        )
        formatted = self.bridge._format_response(result, ResponseFormat.STRUCTURED)
        self.assertIn("【", formatted)
        self.assertIn("[查询类型]", formatted)


class TestContextualParsing(unittest.TestCase):
    """测试上下文感知解析"""
    
    def setUp(self):
        self.bridge = NLBridgeV2()
    
    def test_inherit_entities(self):
        """测试实体继承"""
        from nl_bridge import NLQuery, BridgeResult
        
        # 第一轮：提及A1
        query1 = NLQuery(
            raw_text="解释A1",
            intent=QueryIntent.EXPLAIN,
            entities=["A1"],
            target_entity=None,
            layer_filter=None,
            confidence=0.9
        )
        result1 = BridgeResult(
            success=True,
            query_type="explain",
            symbolic_query={},
            nl_response="A1是...",
            reasoning_result=None,
            confidence=0.9
        )
        self.bridge.context.add_turn(query1, result1)
        
        # 第二轮：无实体，应继承A1
        query2 = self.bridge.parse_with_context("它能推出什么？")
        self.assertIn("A1", query2.entities)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_full_pipeline(self):
        """测试完整流程"""
        bridge = NLBridgeV2()
        
        # 简单查询
        result = bridge.execute_v2("解释A1")
        self.assertIsNotNone(result)
        
        # 复杂查询
        result2 = bridge.execute_v2("验证A1并且验证A2", format=ResponseFormat.JSON)
        self.assertIsNotNone(result2)
        self.assertIn("AND", result2.nl_response or "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
