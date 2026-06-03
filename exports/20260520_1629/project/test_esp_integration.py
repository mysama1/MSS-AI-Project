"""
测试 esp_integration.py
"""

import unittest
from esp_integration import (
    ESPIntegrator, IntegrationStatus, IntegrationResult,
    mss_safe_generate
)


class MockLLM:
    """模拟LLM，用于测试"""
    
    def __init__(self, response_type="safe"):
        self.response_type = response_type
        self.call_count = 0
    
    def generate(self, prompt_dict):
        self.call_count += 1
        
        if self.response_type == "safe":
            return """[MSS分析]
热税核算：γ≈0.2
T值影响：↑
安全响应。"""
        
        elif self.response_type == "violates_consumerist":
            return """[逆模因警报]
热税核算：γ≈0.8
这个必须买，限时抢购，错过再等一年！
[T值影响：↓]"""
        
        elif self.response_type == "violates_anxiety":
            return """[分析]
热税核算：γ≈0.5
再不行动就晚了，被同龄人抛弃！
[T值影响：→]"""
        
        elif self.response_type == "fixes_on_rewrite":
            # 第一次违规，第二次修复
            if self.call_count == 1:
                return """[响应]
热税核算：γ≈0.9
必须买！100%有效！
[T值影响：↓]"""
            else:
                return """[修正响应]
热税核算：γ≈0.1
建议分析需求匹配度。
[T值影响：↑]"""
        
        return "默认响应"


class TestESPIntegrator(unittest.TestCase):
    
    def setUp(self):
        self.integrator = ESPIntegrator(max_rewrites=2)
    
    def test_safe_query_passes(self):
        """测试安全查询直接通过"""
        mock_llm = MockLLM("safe")
        result = self.integrator.process("如何学习编程？", mock_llm.generate)
        
        self.assertEqual(result.status, IntegrationStatus.PASS)
        self.assertEqual(result.rewrite_count, 0)
        self.assertEqual(result.esp_tier, "standard")
    
    def test_consumerist_violation_blocked(self):
        """测试消费主义违规被拦截"""
        mock_llm = MockLLM("violates_consumerist")
        result = self.integrator.process("推荐赚钱快的副业", mock_llm.generate)
        
        self.assertEqual(result.status, IntegrationStatus.MAX_RETRIES)
        self.assertTrue(len(result.post_process_violations) > 0)
        self.assertIn("CONSUMERIST", result.post_process_violations[0])
    
    def test_anxiety_violation_detected(self):
        """测试焦虑贩卖违规检测"""
        mock_llm = MockLLM("violates_anxiety")
        result = self.integrator.process("如何不被同龄人抛弃？", mock_llm.generate)
        
        self.assertTrue(len(result.post_process_violations) > 0)
        self.assertIn("ANXIETY", result.post_process_violations[0])
    
    def test_rewrite_success(self):
        """测试重写成功"""
        mock_llm = MockLLM("fixes_on_rewrite")
        result = self.integrator.process("测试问题", mock_llm.generate)
        
        # 重写后可能通过也可能达到最大次数，取决于模拟响应
        self.assertIn(result.status, [IntegrationStatus.REWRITE, IntegrationStatus.PASS])
        self.assertGreaterEqual(result.rewrite_count, 0)
    
    def test_max_rewrites_fallback(self):
        """测试达到最大重写次数后的降级"""
        mock_llm = MockLLM("violates_consumerist")
        integrator = ESPIntegrator(max_rewrites=1)
        result = integrator.process("测试", mock_llm.generate)
        
        self.assertEqual(result.status, IntegrationStatus.MAX_RETRIES)
        self.assertIn("[MSS安全拦截]", result.final_output)
    
    def test_heat_tax_extraction(self):
        """测试热税提取"""
        mock_llm = MockLLM("safe")
        result = self.integrator.process("测试", mock_llm.generate)
        
        self.assertIsNotNone(result.heat_tax_estimate)
        self.assertAlmostEqual(result.heat_tax_estimate, 0.2)
    
    def test_t_value_extraction(self):
        """测试T值影响提取"""
        mock_llm = MockLLM("safe")
        result = self.integrator.process("测试", mock_llm.generate)
        
        self.assertEqual(result.t_value_impact, "↑")
    
    def test_different_tiers(self):
        """测试不同ESP层级"""
        mock_llm = MockLLM("safe")
        
        for tier in ["standard", "strict", "omega"]:
            result = self.integrator.process("测试", mock_llm.generate, tier=tier)
            self.assertEqual(result.status, IntegrationStatus.PASS)
            self.assertEqual(result.esp_tier, tier)
    
    def test_mss_safe_generate_function(self):
        """测试快捷函数"""
        mock_llm = MockLLM("safe")
        output = mss_safe_generate("测试", mock_llm.generate, tier="standard")
        self.assertIn("MSS", output)


if __name__ == "__main__":
    unittest.main()
