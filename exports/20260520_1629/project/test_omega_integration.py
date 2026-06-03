"""
test_omega_integration.py - Ω级裁定与mss_tactic_integrated集成测试
验证合规检查器正确集成到主系统
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mss_tactic_integrated import MSSTactic, Layer, ComplianceStatus


class TestOmegaIntegration(unittest.TestCase):
    """测试Ω级裁定与主系统集成"""
    
    @classmethod
    def setUpClass(cls):
        """初始化MSSTactic（使用模拟模型）"""
        # Mock Ollama to avoid actual model calls
        cls.ollama_patcher = patch('subprocess.run')
        cls.mock_run = cls.ollama_patcher.start()
        
        # Mock GPU check
        cls.gpu_patcher = patch('mss_tactic_integrated.MSSTactic._check_gpu_memory')
        cls.mock_gpu = cls.gpu_patcher.start()
        cls.mock_gpu.return_value = {"gpu_available": False, "total_mb": 0, "free_mb": 0}
        
        # Mock ModelManager to avoid Ollama dependency
        cls.model_patcher = patch('mss_tactic_integrated.ModelManager')
        cls.mock_model = cls.model_patcher.start()
        cls.mock_model.return_value = MagicMock()
        
        # Mock other dependencies
        cls.responder_patcher = patch('mss_tactic_integrated.ResponderAgent')
        cls.mock_responder = cls.responder_patcher.start()
        cls.mock_responder.return_value = MagicMock()
        
        cls.arbiter_patcher = patch('mss_tactic_integrated.ArbiterAgent')
        cls.mock_arbiter = cls.arbiter_patcher.start()
        cls.mock_arbiter.return_value = MagicMock()
        
        # Create tactic instance
        cls.tactic = MSSTactic(
            arbiter_model="qwen2.5:7b",
            responder_model="mss-ai-v1",
            max_retries=2,
            check_gpu=False
        )
    
    @classmethod
    def tearDownClass(cls):
        cls.ollama_patcher.stop()
        cls.gpu_patcher.stop()
        cls.model_patcher.stop()
        cls.responder_patcher.stop()
        cls.arbiter_patcher.stop()
    
    def test_omega_checker_initialized(self):
        """测试Ω级检查器已初始化"""
        self.assertIsNotNone(self.tactic.omega_checker)
        self.assertEqual(len(self.tactic.omega_checker.rules), 36)
    
    def test_omega_analyze_clean_text(self):
        """测试清洁文本分析"""
        text = "物理规则是意义博弈稳态在物理层的投影。"
        result = self.tactic.omega_analyze(text)
        
        self.assertTrue(result["compliant"])
        self.assertEqual(result["violation_count"], 0)
        self.assertEqual(result["recommendation"], "PASS")
        self.assertGreater(result["estimated_tuning"], 0.8)
    
    def test_omega_analyze_teleology(self):
        """测试强目的论检测"""
        text = "宇宙等待了138亿年就是为了等待我们诞生，人类是万物之灵。"
        result = self.tactic.omega_analyze(text)
        
        self.assertFalse(result["compliant"])
        self.assertGreater(result["violation_count"], 0)
        self.assertEqual(result["recommendation"], "REWRITE_REQUIRED")
        
        # 检查违规类型
        violations = result["violations"]
        teleology = [v for v in violations if v["violation_type"] == "STRONG_TELEOLOGY"]
        self.assertGreater(len(teleology), 0)
    
    def test_omega_analyze_k3_residuals(self):
        """测试K3残余检测"""
        text = "客观现实世界遵循物理定律，实验证明了真理。"
        result = self.tactic.omega_analyze(text)
        
        k3 = result["k3_residuals"]
        self.assertGreater(len(k3["objectivism"]), 0)
        self.assertGreater(len(k3["empiricism"]), 0)
    
    def test_omega_analyze_animal_consciousness(self):
        """测试动物意识混淆检测"""
        text = "动物也有自我意识和情感，和人类只有程度差异。"
        result = self.tactic.omega_analyze(text)
        
        violations = result["violations"]
        animal = [v for v in violations if v["violation_type"] == "ANIMAL_CONSCIOUSNESS_CONFUSION"]
        self.assertGreater(len(animal), 0)
    
    def test_omega_analyze_linguistic_reductionism(self):
        """测试语言学还原论检测"""
        text = "语言只是交流工具，文字只是记录符号。"
        result = self.tactic.omega_analyze(text)
        
        violations = result["violations"]
        ling = [v for v in violations if v["violation_type"] == "LINGUISTIC_REDUCTIONISM"]
        self.assertGreater(len(ling), 0)
    
    def test_omega_analyze_layer_summary(self):
        """测试层级摘要"""
        text = "测试文本"
        result = self.tactic.omega_analyze(text)
        
        summary = result["layer_summary"]
        self.assertIn("L1", summary)
        self.assertIn("L2", summary)
        self.assertIn("L3", summary)
        
        l1_summary = summary["L1"]
        self.assertEqual(l1_summary["rule_count"], 17)
    
    def test_omega_analyze_tuning_estimation(self):
        """测试调谐度估算"""
        # 高违规密度文本
        bad_text = "宇宙等待我们诞生。人类是万物之灵。物理规则是绝对的。"
        bad_result = self.tactic.omega_analyze(bad_text)
        
        # 清洁文本
        good_text = "物理规则是意义博弈稳态。人类文明是随机涌现。"
        good_result = self.tactic.omega_analyze(good_text)
        
        self.assertLess(bad_result["estimated_tuning"], good_result["estimated_tuning"])
    
    def test_generate_with_omega_violations(self):
        """测试generate方法处理Ω级违规"""
        # Mock arbiter to return PASS
        self.tactic.arbiter.check = MagicMock(return_value=MagicMock(
            compliance=ComplianceStatus.PASS,
            rewrite_needed=False,
            forbidden_words=[],
            analysis_report={"overall_score": 0.9}
        ))
        
        # Mock responder
        self.tactic.responder.respond = MagicMock(return_value="响应文本")
        
        # 测试带违规的输入
        result = self.tactic.generate("宇宙等待我们诞生")
        
        # 检查omega_violations字段存在
        self.assertIn("omega_violations", result)
        self.assertIn("omega_k3_residuals", result)
    
    def test_combined_rewrite_logic(self):
        """测试组合重写逻辑"""
        # 模拟arbiter需要重写
        self.tactic.arbiter.check = MagicMock(side_effect=[
            MagicMock(
                compliance=ComplianceStatus.PASS,
                rewrite_needed=True,
                rewrite_prompt="rewrite",
                forbidden_words=["test"],
                analysis_report={}
            ),
            MagicMock(
                compliance=ComplianceStatus.PASS,
                rewrite_needed=False,
                forbidden_words=[],
                analysis_report={"overall_score": 0.9}
            )
        ])
        
        self.tactic._rewrite = MagicMock(return_value="重写后文本")
        self.tactic.responder.respond = MagicMock(return_value="响应")
        
        result = self.tactic.generate("测试输入")
        
        # 验证重写字段
        self.assertIn("rewrites", result)
    
    def test_stats_tracking(self):
        """测试统计追踪"""
        initial_total = self.tactic.stats["total_requests"]
        
        self.tactic.arbiter.check = MagicMock(return_value=MagicMock(
            compliance=ComplianceStatus.PASS,
            rewrite_needed=False,
            forbidden_words=[],
            analysis_report={}
        ))
        self.tactic.responder.respond = MagicMock(return_value="响应")
        
        self.tactic.generate("测试")
        
        self.assertEqual(self.tactic.stats["total_requests"], initial_total + 1)


class TestOmegaEdgeCases(unittest.TestCase):
    """测试边界情况"""
    
    def test_empty_text(self):
        """测试空文本"""
        tactic = MSSTactic.__new__(MSSTactic)
        tactic.omega_checker = MagicMock()
        tactic.omega_checker.check_text.return_value = []
        tactic.omega_checker.check_k3_residuals.return_value = {}
        
        result = tactic.omega_analyze("")
        self.assertTrue(result["compliant"])
    
    def test_very_long_text(self):
        """测试长文本"""
        tactic = MSSTactic.__new__(MSSTactic)
        tactic.omega_checker = MagicMock()
        tactic.omega_checker.check_text.return_value = []
        tactic.omega_checker.check_k3_residuals.return_value = {}
        tactic.omega_checker.get_layer_summary.return_value = {"rule_count": 17}
        
        long_text = "物理规则是稳态。" * 100
        result = tactic.omega_analyze(long_text)
        self.assertTrue(result["compliant"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
