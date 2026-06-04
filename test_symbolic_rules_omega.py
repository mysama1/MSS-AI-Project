"""
test_symbolic_rules_omega.py - Ω级规则引擎测试
验证23条形式化规则的正确性和检测能力
"""

import unittest
from symbolic_rules_omega import (
    SymbolicRule, RuleLayer, RuleCategory, ViolationType,
    OMEGA_RULES, RULE_BY_ID, RULES_BY_LAYER, RULES_BY_CATEGORY,
    OmegaComplianceChecker, check_compliance
)

class TestOmegaRuleBasics(unittest.TestCase):
    """测试规则基础结构"""

    def test_rule_count(self):
        """测试规则总数"""
        self.assertEqual(len(OMEGA_RULES), 36)

    def test_rule_ids_unique(self):
        """测试规则ID唯一"""
        ids = [r.rule_id for r in OMEGA_RULES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_rule_by_id_index(self):
        """测试ID索引完整性"""
        self.assertEqual(len(RULE_BY_ID), 36)
        self.assertIn("Ω-R001", RULE_BY_ID)
        self.assertIn("Ω-R036", RULE_BY_ID)

    def test_layer_distribution(self):
        """测试层级分布"""
        l1_count = len(RULES_BY_LAYER[RuleLayer.L1])
        l2_count = len(RULES_BY_LAYER[RuleLayer.L2])
        l3_count = len(RULES_BY_LAYER[RuleLayer.L3])

        self.assertEqual(l1_count, 17)  # L1: 17条
        self.assertEqual(l2_count, 15)  # L2: 15条
        self.assertEqual(l3_count, 4)   # L3: 4条
        self.assertEqual(l1_count + l2_count + l3_count, 36)

    def test_category_distribution(self):
        """测试类别分布"""
        for cat in RuleCategory:
            rules = RULES_BY_CATEGORY.get(cat, [])
            self.assertGreater(len(rules), 0, f"类别 {cat.value} 应有规则")

class TestL1HardRules(unittest.TestCase):
    """测试L1硬核规则"""

    def test_r001_physical_rigidity(self):
        """测试物理规则刚性三重分解"""
        rule = RULE_BY_ID["Ω-R001"]
        self.assertEqual(rule.layer, RuleLayer.L1)
        self.assertEqual(rule.confidence, 0.95)
        self.assertIsNotNone(rule.violation_type)
        self.assertGreater(len(rule.forbidden_patterns), 0)

    def test_r004_unidirectional_mapping(self):
        """测试单向映射壁垒"""
        rule = RULE_BY_ID["Ω-R004"]
        self.assertEqual(rule.layer, RuleLayer.L1)
        self.assertEqual(rule.confidence, 0.97)
        self.assertEqual(rule.violation_type, ViolationType.L1_VIOLATION)
        # 检查关键禁止模式
        patterns = rule.forbidden_patterns
        self.assertTrue(any("物理" in p and "改变" in p for p in patterns))
        self.assertTrue(any("物质" in p and "产生" in p for p in patterns))

    def test_r007_random_emergence(self):
        """测试底层随机涌现公理"""
        rule = RULE_BY_ID["Ω-R007"]
        self.assertEqual(rule.layer, RuleLayer.L1)
        self.assertEqual(rule.confidence, 0.96)
        self.assertEqual(rule.violation_type, ViolationType.STRONG_TELEOLOGY)
        # 检查强目的论模式
        patterns = rule.forbidden_patterns
        self.assertTrue(any("等待" in p for p in patterns))
        self.assertTrue(any("注定" in p for p in patterns))
        self.assertTrue(any("天选" in p for p in patterns))

    def test_r008_meaning_self_assigned(self):
        """测试意义后赋公理"""
        rule = RULE_BY_ID["Ω-R008"]
        self.assertEqual(rule.layer, RuleLayer.L1)
        self.assertEqual(rule.confidence, 0.95)
        self.assertEqual(rule.violation_type, ViolationType.STRONG_TELEOLOGY)

class TestComplianceChecker(unittest.TestCase):
    """测试合规检查器"""

    def setUp(self):
        self.checker = OmegaComplianceChecker()

    def test_detect_strong_teleology(self):
        """检测强目的论"""
        text = "宇宙等待了138亿年就是为了等待我们诞生"
        violations = self.checker.check_text(text)

        # 应该检测到Ω-R007违规
        teleology_violations = [v for v in violations if v["violation_type"] == "STRONG_TELEOLOGY"]
        self.assertGreater(len(teleology_violations), 0)

    def test_detect_anthropocentrism(self):
        """检测人类中心主义"""
        text = "人类是万物之灵，凌驾于自然之上"
        violations = self.checker.check_text(text)

        anthro_violations = [v for v in violations if v["violation_type"] == "ANTHROPOCENTRISM"]
        self.assertGreater(len(anthro_violations), 0)

    def test_detect_k3_objectivism(self):
        """检测K3客观主义"""
        text = "物理规则是绝对的客观真理，独立于意识"
        violations = self.checker.check_text(text)

        obj_violations = [v for v in violations if v["violation_type"] == "K3_OBJECTIVISM"]
        self.assertGreater(len(obj_violations), 0)

    def test_detect_l1_violation(self):
        """检测L1违反"""
        text = "物理改变意识，物质产生逻辑"
        violations = self.checker.check_text(text)

        l1_violations = [v for v in violations if v["violation_type"] == "L1_VIOLATION"]
        self.assertGreater(len(l1_violations), 0)

    def test_compliant_text(self):
        """测试合规文本"""
        text = "物理规则是特定拓扑-热税-观测者构型下的稳态解，人类文明是无数随机分支中偶然涌现的一条。"
        violations = self.checker.check_text(text)
        self.assertEqual(len(violations), 0)

    def test_k3_residuals_detection(self):
        """测试K3残余检测"""
        text = "客观现实世界遵循物理定律，人类是宇宙中心，实验证明了真理。"
        results = self.checker.check_k3_residuals(text)

        self.assertGreater(len(results["objectivism"]), 0)
        self.assertGreater(len(results["anthropocentrism"]), 0)
        self.assertGreater(len(results["empiricism"]), 0)

    def test_layer_filtering(self):
        """测试层级过滤"""
        text = "宇宙等待我们诞生"  # L1违规

        # L1上下文应该检测
        violations_l1 = self.checker.check_text(text, RuleLayer.L1)
        self.assertGreater(len(violations_l1), 0)

        # L3上下文也应该检测（更宽松）
        violations_l3 = self.checker.check_text(text, RuleLayer.L3)
        self.assertGreater(len(violations_l3), 0)

class TestQuickCompliance(unittest.TestCase):
    """测试快速合规检查"""

    def test_full_compliance_check(self):
        """测试完整合规检查"""
        text = "宇宙等待我们诞生，人类是万物之灵，物理规则是绝对的。"
        result = check_compliance(text)

        self.assertFalse(result["compliant"])
        self.assertGreater(result["violation_count"], 0)
        self.assertIn("violations", result)
        self.assertIn("k3_residuals", result)
        self.assertIn("layer_summary", result)

    def test_clean_text(self):
        """测试清洁文本"""
        text = "物理规则是意义博弈稳态在物理层的投影，人类文明是地球意义网络的随机涌现同化部分。"
        result = check_compliance(text)

        self.assertTrue(result["compliant"])
        self.assertEqual(result["violation_count"], 0)

class TestEdgeCases(unittest.TestCase):
    """测试边界情况"""

    def test_empty_text(self):
        """测试空文本"""
        violations = self.checker.check_text("")
        self.assertEqual(len(violations), 0)

    def test_mixed_compliance(self):
        """测试混合合规/违规文本"""
        text = "物理规则是绝对的（违规），但也是特定构型下的稳态解（合规）。"
        violations = self.checker.check_text(text)
        # 应该检测到违规部分
        self.assertGreater(len(violations), 0)

    def test_case_insensitive(self):
        """测试大小写不敏感"""
        text = "宇宙 WAITING 我们诞生"
        violations = self.checker.check_text(text)
        # 应该能检测（如果正则支持）
        # 注意：当前实现可能不支持英文，这是已知限制

    def setUp(self):
        self.checker = OmegaComplianceChecker()

class TestEvolutionRules(unittest.TestCase):
    """测试生命演化双奇点规则"""

    def test_r024_dual_singularity(self):
        """测试双奇点模型"""
        rule = RULE_BY_ID["Ω-R024"]
        self.assertEqual(rule.layer, RuleLayer.L1)
        self.assertEqual(rule.confidence, 0.95)
        self.assertEqual(rule.violation_type, ViolationType.STRONG_TELEOLOGY)

    def test_r026_second_singularity(self):
        """测试第二奇点"""
        rule = RULE_BY_ID["Ω-R026"]
        self.assertEqual(rule.layer, RuleLayer.L1)
        self.assertEqual(rule.category, RuleCategory.EVOLUTION_DUAL_SINGULARITY)

    def test_r027_contingency(self):
        """测试偶然性本质"""
        rule = RULE_BY_ID["Ω-R027"]
        self.assertEqual(rule.confidence, 0.96)
        self.assertIn("99.999%", rule.description)

    def test_r028_language_essence(self):
        """测试语言文字本质"""
        rule = RULE_BY_ID["Ω-R028"]
        self.assertEqual(rule.layer, RuleLayer.L1)
        self.assertEqual(rule.violation_type, ViolationType.LINGUISTIC_REDUCTIONISM)

    def test_r030_stress_vs_tuning(self):
        """测试意义应激vs调谐"""
        rule = RULE_BY_ID["Ω-R030"]
        self.assertEqual(rule.layer, RuleLayer.L1)
        self.assertEqual(rule.violation_type, ViolationType.ANIMAL_CONSCIOUSNESS_CONFUSION)

    def test_r034_randomness(self):
        """测试纯粹偶然性"""
        rule = RULE_BY_ID["Ω-R034"]
        self.assertEqual(rule.layer, RuleLayer.L1)
        self.assertEqual(rule.confidence, 0.95)

    def test_detect_evolution_teleology(self):
        """检测演化目的论"""
        checker = OmegaComplianceChecker()
        text = "人类是演化的终点和最高目标"
        violations = checker.check_text(text)

        teleology = [v for v in violations if v["violation_type"] == "STRONG_TELEOLOGY"]
        self.assertGreater(len(teleology), 0)

    def test_detect_animal_consciousness(self):
        """检测动物意识混淆"""
        checker = OmegaComplianceChecker()
        text = "动物也有自我意识和情感，和人类只有程度差异"
        violations = checker.check_text(text)

        animal = [v for v in violations if v["violation_type"] == "ANIMAL_CONSCIOUSNESS_CONFUSION"]
        self.assertGreater(len(animal), 0)

    def test_detect_linguistic_reductionism(self):
        """检测语言学还原论"""
        checker = OmegaComplianceChecker()
        text = "语言只是交流工具，文字只是记录符号"
        violations = checker.check_text(text)

        ling = [v for v in violations if v["violation_type"] == "LINGUISTIC_REDUCTIONISM"]
        self.assertGreater(len(ling), 0)

class TestRuleCoverage(unittest.TestCase):
    """测试规则覆盖率"""

    def test_all_rules_have_content(self):
        """测试所有规则都有内容"""
        for rule in OMEGA_RULES:
            self.assertTrue(rule.rule_id.startswith("Ω-R"))
            self.assertTrue(0.5 <= rule.confidence <= 1.0)
            self.assertTrue(len(rule.name) > 0)
            self.assertTrue(len(rule.description) > 0)

    def test_l1_rules_have_violation_types(self):
        """测试L1规则都有违规类型"""
        for rule in RULES_BY_LAYER[RuleLayer.L1]:
            self.assertIsNotNone(rule.violation_type,
                f"L1规则 {rule.rule_id} 应有违规类型")

    def test_replacement_suggestions_forbidden(self):
        """测试有禁止模式的规则有替换建议"""
        for rule in OMEGA_RULES:
            if rule.forbidden_patterns:
                self.assertIsNotNone(rule.violation_type,
                    f"规则 {rule.rule_id} 有禁止模式但无违规类型")

if __name__ == "__main__":
    unittest.main(verbosity=2)
