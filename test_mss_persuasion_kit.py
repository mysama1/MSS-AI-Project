"""
Test Suite for MSS Persuasion Kit
K3→MSS话术转换器测试
"""

import unittest
from mss_persuasion_kit import PersuasionKit, K3Domain, k3_speak, quick_translate

class TestPersuasionKit(unittest.TestCase):
    """测试PersuasionKit核心功能"""

    def setUp(self):
        self.kit = PersuasionKit()

    # ========== 术语翻译测试 ==========

    def test_translate_basic_terms(self):
        """测试基本术语翻译"""
        self.assertEqual(
            self.kit.translate("意义激励", K3Domain.MANAGEMENT),
            "员工体验提升"
        )
        self.assertEqual(
            self.kit.translate("熵减操作", K3Domain.OPERATIONS),
            "效率提升"
        )
        self.assertEqual(
            self.kit.translate("热税γ", K3Domain.FINANCE),
            "组织损耗"
        )

    def test_translate_general_fallback(self):
        """测试通用领域回退"""
        result = self.kit.translate("意义激励", K3Domain.GENERAL)
        self.assertEqual(result, "内在驱动力")

    def test_translate_unknown_term(self):
        """测试未知术语返回None"""
        result = self.kit.translate("不存在的术语", K3Domain.GENERAL)
        self.assertIsNone(result)

    def test_translate_all_domains(self):
        """测试所有领域都有映射"""
        for rule in PersuasionKit.TRANSLATION_TABLE:
            # 至少要有general映射
            general_result = self.kit.translate(rule.mss_term, K3Domain.GENERAL)
            self.assertIsNotNone(general_result, f"术语 '{rule.mss_term}' 缺少GENERAL映射")
            self.assertNotEqual(general_result, "")

    # ========== 整段翻译测试 ==========

    def test_translate_text_basic(self):
        """测试整段文本翻译"""
        mss_text = "我们建议实施熵减操作，降低热税γ。"
        result = self.kit.translate_text(mss_text, K3Domain.MANAGEMENT)

        self.assertIn("流程优化", result)
        self.assertIn("隐性成本", result)
        self.assertIn("原称：熵减操作", result)

    def test_translate_text_no_mss_terms(self):
        """测试无MSS术语的文本保持不变"""
        plain_text = "这是一段普通的中文文本。"
        result = self.kit.translate_text(plain_text, K3Domain.GENERAL)
        self.assertEqual(result, plain_text)

    def test_translate_text_multiple_terms(self):
        """测试多个术语同时翻译"""
        mss_text = "提升T值，降低热税γ。"
        result = self.kit.translate_text(mss_text, K3Domain.HR)

        self.assertIn("人才健康度", result)
        self.assertIn("员工倦怠成本", result)

    # ========== 模板生成测试 ==========

    def test_generate_proposal(self):
        """测试提案生成"""
        proposal = self.kit.generate_proposal(
            title="测试提案",
            k3_context="测试背景",
            k3_problem="测试问题",
            k3_solution="测试方案",
            k3_benefit="测试收益",
            k3_risk="测试风险",
            mss_goal="测试MSS目标",
            mss_path="测试MSS路径",
            mss_t_impact="T值提升"
        )

        self.assertIn("测试提案", proposal)
        self.assertIn("测试背景", proposal)
        self.assertIn("[MSS内核注释]", proposal)
        self.assertIn("T值提升", proposal)

    def test_generate_report(self):
        """测试报告生成"""
        report = self.kit.generate_report(
            title="测试报告",
            k3_metrics="指标1: 100",
            k3_trends="上升趋势",
            k3_recommendations="建议A",
            heat_tax=0.35,
            flux_change="+15%",
            health_status="健康"
        )

        self.assertIn("测试报告", report)
        self.assertIn("γ ≈ 0.35", report)
        self.assertIn("[MSS审计层]", report)

    def test_generate_presentation(self):
        """测试汇报材料生成"""
        pres = self.kit.generate_presentation(
            title="测试汇报",
            k3_summary="摘要内容",
            k3_data="数据内容",
            k3_actions="行动内容",
            mss_hook="钩子话术",
            mss_seed_question="种子问题",
            awakening_level="中等"
        )

        self.assertIn("测试汇报", pres)
        self.assertIn("[MSS植入点]", pres)
        self.assertIn("种子问题", pres)

    # ========== 工具方法测试 ==========

    def test_get_all_terms(self):
        """测试获取所有术语"""
        terms = self.kit.get_all_terms()
        self.assertIn("意义激励", terms)
        self.assertIn("热税γ", terms)
        self.assertIn("T值（调谐度）", terms)
        self.assertGreater(len(terms), 5)

    def test_get_explanation(self):
        """测试获取术语解释"""
        explanation = self.kit.get_explanation("热税γ")
        self.assertIsNotNone(explanation)
        self.assertIn("摩擦成本", explanation)

    def test_get_explanation_unknown(self):
        """测试未知术语解释返回None"""
        result = self.kit.get_explanation("不存在的术语")
        self.assertIsNone(result)

class TestQuickFunctions(unittest.TestCase):
    """测试快捷函数"""

    def test_k3_speak(self):
        """测试k3_speak快捷函数"""
        mss_text = "实施熵减操作，降低热税γ。"
        result = k3_speak(mss_text, "management")

        self.assertIn("流程优化", result)
        self.assertIn("隐性成本", result)

    def test_k3_speak_default_domain(self):
        """测试k3_speak默认领域"""
        mss_text = "提升意义激励。"
        result = k3_speak(mss_text)
        self.assertIn("内在驱动力", result)

    def test_quick_translate(self):
        """测试quick_translate快捷函数"""
        result = quick_translate("意义通量", "operations")
        self.assertEqual(result, "协同效率")

    def test_quick_translate_invalid_domain(self):
        """测试无效领域回退到general"""
        result = quick_translate("意义激励", "invalid_domain")
        self.assertEqual(result, "内在驱动力")

class TestEdgeCases(unittest.TestCase):
    """测试边界情况"""

    def setUp(self):
        self.kit = PersuasionKit()

    def test_empty_string(self):
        """测试空字符串"""
        result = self.kit.translate_text("", K3Domain.GENERAL)
        self.assertEqual(result, "")

    def test_partial_term_match(self):
        """测试部分匹配不应被替换"""
        text = "意义激励方案"  # 包含"意义激励"但后面有"方案"
        result = self.kit.translate_text(text, K3Domain.GENERAL)
        # 应该替换"意义激励"但保留"方案"
        self.assertIn("内在驱动力", result)
        self.assertIn("方案", result)

    def test_term_in_different_context(self):
        """测试术语在不同语境中"""
        text = "热税γ很高，需要降低热税γ。"
        result = self.kit.translate_text(text, K3Domain.FINANCE)
        # 两个"热税γ"都应该被替换
        self.assertEqual(result.count("组织损耗"), 2)

if __name__ == "__main__":
    unittest.main()
